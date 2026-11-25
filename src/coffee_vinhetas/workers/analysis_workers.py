"""Workers assíncronos de análise da vinheta e varredura da fila de músicas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from ..core.constants import is_inside_output_dir, is_supported_audio
from ..core.ffmpeg_manager import FFmpegManager
from ..core.models import AudioInfo


class JingleAnalyzeWorker(QThread):
    """Analisa a vinheta e gera picos reais da forma de onda fora da thread principal."""

    finished_analysis = Signal(object)  # AudioInfo

    def __init__(self, ffmpeg_mgr: FFmpegManager, path: Path, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.ffmpeg_mgr = ffmpeg_mgr
        self.path = path

    def run(self) -> None:
        info = self.ffmpeg_mgr.probe_audio(self.path)
        if info.valid:
            peaks, mean_db, act_start, act_end = self.ffmpeg_mgr.extract_waveform_peaks(
                self.path, info.duration, num_buckets=240
            )
            info.peaks = peaks
            info.mean_volume_db = mean_db
            info.active_start = act_start
            info.active_end = act_end
        self.finished_analysis.emit(info)


class MusicScanWorker(QThread):
    """Sonda metadados básicos dos arquivos de música em segundo plano sem travar a UI."""

    scan_finished = Signal(list, int, list)  # list[AudioInfo], ignored_count, warnings

    def __init__(
        self,
        ffmpeg_mgr: FFmpegManager,
        paths: list[Path],
        recursive: bool,
        existing_paths: set[Path],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.ffmpeg_mgr = ffmpeg_mgr
        self.paths = paths
        self.recursive = recursive
        self.existing_paths = existing_paths

    def run(self) -> None:
        discovered: list[Path] = []
        seen: set[Path] = set(self.existing_paths)
        ignored = 0

        for item in self.paths:
            if self.isInterruptionRequested():
                break
            try:
                resolved = item.resolve()
            except OSError:
                ignored += 1
                continue

            if resolved.is_dir():
                if is_inside_output_dir(resolved):
                    continue
                iterator = resolved.rglob("*") if self.recursive else resolved.iterdir()
                for child in sorted(iterator):
                    if self.isInterruptionRequested():
                        break
                    if not child.is_file() or is_inside_output_dir(child):
                        continue
                    try:
                        c_res = child.resolve()
                    except OSError:
                        ignored += 1
                        continue
                    if is_supported_audio(c_res):
                        if c_res not in seen:
                            seen.add(c_res)
                            discovered.append(c_res)
                    else:
                        ignored += 1
            elif resolved.is_file():
                if is_inside_output_dir(resolved):
                    ignored += 1
                    continue
                if is_supported_audio(resolved):
                    if resolved not in seen:
                        seen.add(resolved)
                        discovered.append(resolved)
                else:
                    ignored += 1
            else:
                ignored += 1

        infos: list[AudioInfo] = []
        warnings: list[str] = []

        if discovered and self.ffmpeg_mgr.status.available:
            with ThreadPoolExecutor(max_workers=min(4, max(1, len(discovered)))) as pool:
                for info in pool.map(self.ffmpeg_mgr.probe_audio, discovered):
                    if self.isInterruptionRequested():
                        break
                    if info.valid:
                        infos.append(info)
                    else:
                        ignored += 1
                        warnings.append(f"{info.path.name}: {info.error}")
        else:
            for p in discovered:
                infos.append(AudioInfo(path=p, valid=True))

        self.scan_finished.emit(infos, ignored, warnings)
