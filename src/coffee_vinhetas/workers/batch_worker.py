"""Worker coordenador de processamento paralelo em lote com cancelamento seguro."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import subprocess
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from ..core.audio_processor import AudioProcessor
from ..core.constants import resolve_concurrency
from ..core.ffmpeg_manager import FFmpegManager
from ..core.logging_setup import LOGGER
from ..core.models import AudioInfo, BatchSummary, MixConfig, TaskStatus, TrackResult, TrackTask


class BatchWorker(QThread):
    """Coordena ThreadPoolExecutor com processos FFmpeg independentes e cancelamento seguro."""

    progress_updated = Signal(float, int, int, int, int, str, float, float)
    batch_completed = Signal(object)  # BatchSummary

    def __init__(
        self,
        ffmpeg_mgr: FFmpegManager,
        tasks: list[TrackTask],
        jingle_info: AudioInfo,
        cfg: MixConfig,
        output_dir: Path,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.ffmpeg_mgr = ffmpeg_mgr
        self.tasks = tasks
        self.jingle_info = jingle_info
        self.cfg = cfg
        self.output_dir = output_dir

        self._cancel_event = threading.Event()
        self._state_lock = threading.Lock()
        self._active_procs: set[subprocess.Popen[str]] = set()
        self._task_progress: dict[int, float] = {i: 0.0 for i in range(len(tasks))}
        self._active_indices: set[int] = set()
        self._completed_count = 0
        self._error_count = 0
        self._current_file = ""

    def request_cancel(self) -> None:
        self._cancel_event.set()
        with self._state_lock:
            procs = list(self._active_procs)
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass

        def _force_kill_later() -> None:
            time.sleep(1.2)
            for p in procs:
                if p.poll() is None:
                    try:
                        p.kill()
                    except OSError:
                        pass

        threading.Thread(target=_force_kill_later, daemon=True).start()

    def _register_proc(self, proc: subprocess.Popen[str]) -> None:
        with self._state_lock:
            self._active_procs.add(proc)

    def _unregister_proc(self, proc: subprocess.Popen[str]) -> None:
        with self._state_lock:
            self._active_procs.discard(proc)

    def _compute_weights(self) -> list[float]:
        known = [t.duration for t in self.tasks if t.duration > 0]
        fallback_weight = (sum(known) / len(known)) if known else 1.0
        return [t.duration if t.duration > 0 else fallback_weight for t in self.tasks]

    def _emit_snapshot(self, weights: list[float], total_weight: float, start_ts: float) -> None:
        with self._state_lock:
            weighted_done = sum(weights[i] * self._task_progress[i] for i in range(len(self.tasks)))
            pct = (weighted_done / total_weight * 100.0) if total_weight > 0 else 0.0
            pct = max(0.0, min(100.0, pct))
            done = self._completed_count
            active = len(self._active_indices)
            errors = self._error_count
            cur_file = self._current_file

        elapsed = time.monotonic() - start_ts
        eta = -1.0
        if pct >= 3.0 and done >= 1 and elapsed >= 1.0:
            eta = max(0.0, elapsed * ((100.0 - pct) / pct))
        self.progress_updated.emit(pct, done, len(self.tasks), active, errors, cur_file, elapsed, eta)

    def run(self) -> None:
        start_ts = time.monotonic()
        workers, threads_per_proc = resolve_concurrency(self.cfg.parallel_limit)
        workers = min(workers, max(1, len(self.tasks)))
        processor = AudioProcessor(self.ffmpeg_mgr)

        weights = self._compute_weights()
        total_weight = sum(weights) or 1.0
        results: list[Optional[TrackResult]] = [None] * len(self.tasks)

        LOGGER.info(
            "Iniciando lote: %d arquivos | %d processos simultâneos | %d threads/FFmpeg | saída: %s",
            len(self.tasks),
            workers,
            threads_per_proc,
            self.output_dir,
        )

        def _run_one(idx: int, task: TrackTask) -> TrackResult:
            if self._cancel_event.is_set():
                return TrackResult(task.source_path, None, TaskStatus.CANCELLED, "Cancelado antes de iniciar.")
            with self._state_lock:
                self._active_indices.add(idx)
                self._current_file = task.source_path.name
            self._emit_snapshot(weights, total_weight, start_ts)

            last_emit = [0.0]

            def _on_progress(frac: float) -> None:
                with self._state_lock:
                    if frac > self._task_progress[idx]:
                        self._task_progress[idx] = frac
                now = time.monotonic()
                if now - last_emit[0] >= 0.12:
                    last_emit[0] = now
                    self._emit_snapshot(weights, total_weight, start_ts)

            res = processor.process_file(
                task=task,
                jingle_info=self.jingle_info,
                cfg=self.cfg,
                threads_per_proc=threads_per_proc,
                cancel_event=self._cancel_event,
                register_proc=self._register_proc,
                unregister_proc=self._unregister_proc,
                progress_cb=_on_progress,
            )

            with self._state_lock:
                self._active_indices.discard(idx)
                if res.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED):
                    self._task_progress[idx] = 1.0
                self._completed_count += 1
                if res.status == TaskStatus.FAILED:
                    self._error_count += 1
            self._emit_snapshot(weights, total_weight, start_ts)
            return res

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures: dict[Future[TrackResult], int] = {}
            for idx, task in enumerate(self.tasks):
                if self._cancel_event.is_set():
                    results[idx] = TrackResult(
                        task.source_path, None, TaskStatus.CANCELLED, "Cancelado antes de iniciar."
                    )
                    continue
                fut = pool.submit(_run_one, idx, task)
                futures[fut] = idx

            for fut, idx in futures.items():
                if self._cancel_event.is_set() and fut.cancel():
                    results[idx] = TrackResult(
                        self.tasks[idx].source_path, None, TaskStatus.CANCELLED, "Cancelado antes de iniciar."
                    )
                    continue
                try:
                    results[idx] = fut.result()
                except Exception as exc:
                    results[idx] = TrackResult(
                        self.tasks[idx].source_path, None, TaskStatus.FAILED, f"Erro no worker: {exc}"
                    )

        final_results = [
            r if r is not None else TrackResult(self.tasks[i].source_path, None, TaskStatus.CANCELLED, "Cancelado.")
            for i, r in enumerate(results)
        ]

        succeeded = sum(1 for r in final_results if r.status == TaskStatus.SUCCESS)
        failed = sum(1 for r in final_results if r.status == TaskStatus.FAILED)
        skipped_or_cancelled = sum(
            1 for r in final_results if r.status in (TaskStatus.SKIPPED, TaskStatus.CANCELLED)
        )
        elapsed_total = time.monotonic() - start_ts

        summary = BatchSummary(
            total=len(final_results),
            succeeded=succeeded,
            failed=failed,
            skipped_or_cancelled=skipped_or_cancelled,
            elapsed_sec=elapsed_total,
            output_dir=self.output_dir,
            cancelled=self._cancel_event.is_set(),
            results=final_results,
        )
        LOGGER.info(
            "Lote finalizado: total=%d, ok=%d, erros=%d, ignorados/cancelados=%d, tempo=%.2fs",
            summary.total,
            summary.succeeded,
            summary.failed,
            summary.skipped_or_cancelled,
            summary.elapsed_sec,
        )
        self.batch_completed.emit(summary)
