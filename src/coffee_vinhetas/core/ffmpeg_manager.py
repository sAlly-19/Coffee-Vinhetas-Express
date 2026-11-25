"""Localização, validação e sondagem de áudio com FFmpeg / FFprobe."""

from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional

from .constants import subprocess_kwargs
from .logging_setup import LOGGER
from .models import AudioInfo, FFmpegStatus


class FFmpegManager:
    """Localiza, valida e executa utilitários FFmpeg/FFprobe sem janelas de console."""

    def __init__(self, custom_dir: str = "") -> None:
        self.custom_dir = custom_dir
        self._status = FFmpegStatus(available=False)

    @property
    def status(self) -> FFmpegStatus:
        return self._status

    def _candidate_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        if getattr(sys, "frozen", False):
            dirs.append(Path(sys.executable).resolve().parent)
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                dirs.append(Path(meipass))
        else:
            # Raiz do projeto (onde fica main.py) e diretório atual de execução
            dirs.append(Path(__file__).resolve().parents[3])
            dirs.append(Path.cwd())

        if self.custom_dir:
            custom_path = Path(self.custom_dir)
            dirs.append(custom_path)
            if (custom_path / "bin").is_dir():
                dirs.append(custom_path / "bin")
        return dirs

    def _find_binary(self, base_name: str) -> Optional[Path]:
        exe_names = [f"{base_name}.exe", base_name] if sys.platform == "win32" else [base_name]
        for folder in self._candidate_dirs():
            if not folder.is_dir():
                continue
            for exe_name in exe_names:
                candidate = folder / exe_name
                if candidate.is_file():
                    return candidate
        which_hit = shutil.which(base_name)
        return Path(which_hit) if which_hit else None

    def _verify_executable(self, exe_path: Path) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                [str(exe_path), "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                **subprocess_kwargs(),
            )
            if proc.returncode != 0:
                return False, proc.stderr.strip() or f"Código de retorno {proc.returncode}"
            first_line = (proc.stdout or "").splitlines()[0] if proc.stdout else "Disponível"
            return True, first_line.strip()
        except Exception as exc:
            return False, str(exc)

    def detect(self, custom_dir: Optional[str] = None) -> FFmpegStatus:
        if custom_dir is not None:
            self.custom_dir = custom_dir

        ffmpeg_path = self._find_binary("ffmpeg")
        ffprobe_path = self._find_binary("ffprobe")

        if not ffmpeg_path or not ffprobe_path:
            missing = []
            if not ffmpeg_path:
                missing.append("ffmpeg")
            if not ffprobe_path:
                missing.append("ffprobe")
            self._status = FFmpegStatus(
                available=False,
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                error=f"Executáveis não encontrados: {', '.join(missing)}.",
            )
            return self._status

        ok_ff, msg_ff = self._verify_executable(ffmpeg_path)
        ok_fp, msg_fp = self._verify_executable(ffprobe_path)

        if not ok_ff or not ok_fp:
            errs = []
            if not ok_ff:
                errs.append(f"ffmpeg: {msg_ff}")
            if not ok_fp:
                errs.append(f"ffprobe: {msg_fp}")
            self._status = FFmpegStatus(
                available=False,
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                error=" | ".join(errs),
            )
            return self._status

        self._status = FFmpegStatus(
            available=True,
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            ffmpeg_version=msg_ff,
            ffprobe_version=msg_fp,
        )
        LOGGER.info("FFmpeg detectado: %s | FFprobe: %s", ffmpeg_path, ffprobe_path)
        return self._status

    def major_version(self) -> int:
        ver = self._status.ffmpeg_version or ""
        if "version" in ver:
            tail = ver.split("version", 1)[1].strip().lstrip("nN")
            digits = ""
            for ch in tail:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                return int(digits)
        return 7

    def filter_complex_args(self, filter_graph: str, script_file: Path) -> list[str]:
        """Seleciona passagem direta ou arquivo de filtro compatível com FFmpeg <=6 e >=7."""
        if len(filter_graph) <= 8000:
            return ["-filter_complex", filter_graph]
        script_file.write_text(filter_graph, encoding="utf-8")
        flag = "-/filter_complex" if self.major_version() >= 7 else "-filter_complex_script"
        return [flag, str(script_file)]

    def probe_audio(self, file_path: Path) -> AudioInfo:
        if not self._status.available or not self._status.ffprobe_path:
            return AudioInfo(path=file_path, valid=False, error="FFprobe indisponível.")
        if not file_path.is_file():
            return AudioInfo(path=file_path, valid=False, error="Arquivo não encontrado.")

        cmd = [
            str(self._status.ffprobe_path),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-select_streams",
            "a:0",
            str(file_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                **subprocess_kwargs(),
            )
            if proc.returncode != 0:
                return AudioInfo(path=file_path, valid=False, error="Arquivo ilegível ou corrompido.")
            data = json.loads(proc.stdout or "{}")
        except Exception as exc:
            return AudioInfo(path=file_path, valid=False, error=f"Falha ao analisar arquivo: {exc}")

        streams = data.get("streams") or []
        fmt = data.get("format") or {}
        if not streams:
            return AudioInfo(path=file_path, valid=False, error="Nenhuma trilha de áudio válida encontrada.")

        stream = streams[0]
        duration = self._safe_float(stream.get("duration")) or self._safe_float(fmt.get("duration"))
        sample_rate = self._safe_int(stream.get("sample_rate"))
        channels = self._safe_int(stream.get("channels")) or 2
        bit_rate = self._safe_int(stream.get("bit_rate")) or self._safe_int(fmt.get("bit_rate"))
        codec_name = str(stream.get("codec_name") or "").upper()
        format_name = file_path.suffix.lstrip(".").upper() or str(fmt.get("format_name") or "").upper()

        if duration <= 0:
            return AudioInfo(path=file_path, valid=False, error="Duração de áudio inválida ou arquivo corrompido.")

        return AudioInfo(
            path=file_path,
            duration=duration,
            sample_rate=sample_rate or 44100,
            channels=channels,
            codec_name=codec_name,
            format_name=format_name,
            bit_rate=bit_rate,
            size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            active_start=0.0,
            active_end=duration,
            valid=True,
        )

    def extract_waveform_peaks(
        self,
        file_path: Path,
        duration: float,
        num_buckets: int = 240,
    ) -> tuple[list[float], float, float, float]:
        """Decodifica PCM 4 kHz em streaming para calcular picos da waveform, nível RMS e janela ativa."""
        if not self._status.available or not self._status.ffmpeg_path:
            return [], -18.0, 0.0, duration

        analysis_sr = 4000
        cmd = [
            str(self._status.ffmpeg_path),
            "-v",
            "error",
            "-i",
            str(file_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(analysis_sr),
            "-f",
            "s16le",
            "pipe:1",
        ]

        expected_samples = max(num_buckets, int(math.ceil(max(0.1, duration) * analysis_sr)))
        samples_per_bucket = max(1, expected_samples // num_buckets)

        peaks: list[float] = []
        bucket_peak = 0
        bucket_count = 0
        sum_sq = 0.0
        total_samples = 0

        silence_thresh = int(32768 * (10.0 ** (-45.0 / 20.0)))
        first_active_sample: Optional[int] = None
        last_active_sample: Optional[int] = None

        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **subprocess_kwargs(),
            ) as proc:
                assert proc.stdout is not None
                remainder = b""
                while True:
                    chunk = proc.stdout.read(16384)
                    if not chunk:
                        break
                    data = remainder + chunk
                    even_len = len(data) & ~1
                    remainder = data[even_len:]
                    if even_len == 0:
                        continue

                    samples = array("h")
                    samples.frombytes(data[:even_len])
                    if sys.byteorder != "little":
                        samples.byteswap()

                    for val in samples:
                        abs_val = -val if val < 0 else val
                        if abs_val > bucket_peak:
                            bucket_peak = abs_val
                        if abs_val >= silence_thresh:
                            if first_active_sample is None:
                                first_active_sample = total_samples
                            last_active_sample = total_samples
                        norm = val / 32768.0
                        sum_sq += norm * norm
                        total_samples += 1
                        bucket_count += 1
                        if bucket_count >= samples_per_bucket:
                            peaks.append(min(1.0, bucket_peak / 32768.0))
                            bucket_peak = 0
                            bucket_count = 0

                if bucket_count > 0:
                    peaks.append(min(1.0, bucket_peak / 32768.0))
                proc.wait(timeout=10)
        except Exception as exc:
            LOGGER.warning("Falha ao calcular waveform de %s: %s", file_path.name, exc)
            return [], -18.0, 0.0, duration

        if not peaks:
            return [], -18.0, 0.0, duration

        resampled = self._resample_peaks(peaks, num_buckets)
        max_peak = max(resampled) if resampled else 0.0
        if max_peak > 0.005:
            scale = min(16.0, 0.94 / max_peak)
            resampled = [min(1.0, p * scale) for p in resampled]

        rms = math.sqrt(sum_sq / max(1, total_samples))
        mean_db = 20.0 * math.log10(max(1e-5, rms))

        if first_active_sample is not None and last_active_sample is not None and last_active_sample > first_active_sample:
            act_start = max(0.0, (first_active_sample / analysis_sr) - 0.03)
            act_end = min(duration, (last_active_sample / analysis_sr) + 0.05)
            if act_end - act_start < 0.15:
                act_start, act_end = 0.0, duration
        else:
            act_start, act_end = 0.0, duration

        return resampled, mean_db, act_start, act_end

    @staticmethod
    def _resample_peaks(peaks: list[float], target_len: int) -> list[float]:
        if len(peaks) == target_len or not peaks:
            return peaks
        out: list[float] = []
        ratio = len(peaks) / float(target_len)
        for i in range(target_len):
            start = int(i * ratio)
            end = max(start + 1, int((i + 1) * ratio))
            out.append(max(peaks[start:end]))
        return out

    @staticmethod
    def _safe_float(val: object) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _safe_int(val: object) -> int:
        try:
            return int(val) if val is not None else 0
        except (TypeError, ValueError):
            return 0
