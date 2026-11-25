"""Worker assíncrono para geração de prévia real com ducking."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import Optional
import uuid

from PySide6.QtCore import QObject, QThread, Signal

from ..core.audio_processor import AudioProcessor
from ..core.constants import format_duration, subprocess_kwargs
from ..core.ffmpeg_manager import FFmpegManager
from ..core.models import AudioInfo, MixConfig


class PreviewWorker(QThread):
    """Gera trecho temporário real com ducking para reprodução em QMediaPlayer."""

    preview_ready = Signal(str, str)  # temp_wav_path, description
    preview_failed = Signal(str)

    def __init__(
        self,
        ffmpeg_mgr: FFmpegManager,
        music_info: AudioInfo,
        jingle_info: AudioInfo,
        cfg: MixConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.ffmpeg_mgr = ffmpeg_mgr
        self.music_info = music_info
        self.jingle_info = jingle_info
        self.cfg = cfg
        self._proc: Optional[subprocess.Popen[str]] = None

    def cancel(self) -> None:
        self.requestInterruption()
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except OSError:
                pass

    def run(self) -> None:
        if not self.ffmpeg_mgr.status.available or not self.ffmpeg_mgr.status.ffmpeg_path:
            self.preview_failed.emit("FFmpeg indisponível para gerar a prévia.")
            return

        music_dur = self.music_info.duration
        jingle_dur = self.jingle_info.effective_duration
        entry = float(self.cfg.entry_time_sec)

        if music_dur < jingle_dur:
            self.preview_failed.emit(
                f"A faixa '{self.music_info.path.name}' ({format_duration(music_dur)}) é menor que a vinheta."
            )
            return

        if entry + jingle_dur > music_dur + 0.05:
            self.preview_failed.emit(
                f"A faixa '{self.music_info.path.name}' ({format_duration(music_dur)}) é menor que "
                f"o tempo de entrada ({int(entry)}s) + vinheta ({jingle_dur:.1f}s)."
            )
            return

        att_s = self.cfg.attack_ms / 1000.0
        rel_s = self.cfg.release_ms / 1000.0
        pre_roll = min(entry, max(2.0, att_s + 1.5))
        post_roll = max(2.5, rel_s + 1.5)

        preview_start = max(0.0, entry - pre_roll)
        preview_end = min(music_dur, entry + jingle_dur + post_roll)

        min_span = min(10.0, music_dur)
        if preview_end - preview_start < min_span:
            deficit = min_span - (preview_end - preview_start)
            expand_after = min(deficit, music_dur - preview_end)
            preview_end += expand_after
            deficit -= expand_after
            if deficit > 0:
                preview_start = max(0.0, preview_start - deficit)

        note = ""
        preview_len = preview_end - preview_start
        if preview_len > 90.0:
            preview_len = 90.0
            note = " (prévia limitada a 90s devido à duração extensa da vinheta)"

        relative_entry = entry - preview_start
        processor = AudioProcessor(self.ffmpeg_mgr)
        filter_graph = processor.build_filter_complex(
            insertion_times=[relative_entry],
            jingle_info=self.jingle_info,
            music_sample_rate=self.music_info.sample_rate or 44100,
            music_duration=preview_len,
            cfg=self.cfg,
        )

        token = uuid.uuid4().hex[:10]
        temp_wav = Path(tempfile.gettempdir()) / f"coffee_preview_{token}.wav"
        script_file = Path(tempfile.gettempdir()) / f"coffee_prev_fc_{token}.txt"

        try:
            fc_args = self.ffmpeg_mgr.filter_complex_args(filter_graph, script_file)
            cmd = [
                str(self.ffmpeg_mgr.status.ffmpeg_path),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{preview_start:.3f}",
                "-t",
                f"{preview_len:.3f}",
                "-i",
                str(self.music_info.path),
                "-i",
                str(self.jingle_info.path),
                *fc_args,
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(temp_wav),
            ]
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                **subprocess_kwargs(),
            )
            _, stderr = self._proc.communicate(timeout=45)
            if self.isInterruptionRequested():
                AudioProcessor.safe_unlink(temp_wav)
                return
            if self._proc.returncode != 0 or not temp_wav.is_file() or temp_wav.stat().st_size == 0:
                AudioProcessor.safe_unlink(temp_wav)
                self.preview_failed.emit(f"Erro ao gerar prévia: {stderr.strip() or 'falha no FFmpeg'}")
                return

            desc = (
                f"{self.music_info.path.name} • trecho {format_duration(preview_start)}–"
                f"{format_duration(preview_start + preview_len)} ({preview_len:.1f}s){note}"
            )
            self.preview_ready.emit(str(temp_wav), desc)
        except Exception as exc:
            AudioProcessor.safe_unlink(temp_wav)
            if not self.isInterruptionRequested():
                self.preview_failed.emit(f"Erro ao gerar prévia: {exc}")
        finally:
            AudioProcessor.safe_unlink(script_file)
            self._proc = None
