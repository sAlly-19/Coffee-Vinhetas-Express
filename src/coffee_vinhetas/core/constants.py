"""Constantes de domínio, paleta Coffee Design System e utilitários puros."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import os
from pathlib import Path
import subprocess
import sys

APP_NAME = "Coffee Vinhetas Express"
APP_SUBTITLE = "Processador de áudio de alta velocidade com Ducking automático"
APP_AUTHOR = "Café - Sistemas & Softwares"
APP_ORG = "CoffeeAudioTools"
APP_VERSION = "1.0.0"

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac")
OUTPUT_DIR_NAME = "COM_VINHETA"

COLOR_BG = "#140E0A"
COLOR_SURFACE = "#1E1611"
COLOR_ELEVATED = "#2A1F18"
COLOR_BORDER = "#493628"
COLOR_TEXT = "#F7EDE2"
COLOR_TEXT_DIM = "#B3A192"
COLOR_AMBER = "#DF9B57"
COLOR_AMBER_HOVER = "#F2B872"
COLOR_GREEN = "#23B24D"
COLOR_GREEN_HOVER = "#1E9C42"
COLOR_ERROR = "#E57373"
COLOR_WARNING = "#E8B863"

CREATE_NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class ExportQuality(str, Enum):
    MP3_320 = "mp3_320"
    MP3_256 = "mp3_256"
    AAC_256 = "aac_256"
    WAV_PCM = "wav_pcm"
    FLAC = "flac"


class DuckingMode(str, Enum):
    ENVELOPE = "envelope"
    SIDECHAIN = "sidechain"


class ConflictPolicy(str, Enum):
    ASK = "ask"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    SKIP = "skip"


@dataclass(frozen=True)
class ExportPreset:
    key: ExportQuality
    label: str
    extension: str
    muxer: str
    codec_args: tuple[str, ...]
    lossless: bool


EXPORT_PRESETS: dict[ExportQuality, ExportPreset] = {
    ExportQuality.MP3_320: ExportPreset(
        key=ExportQuality.MP3_320,
        label="MP3 — 320 kbps",
        extension=".mp3",
        muxer="mp3",
        codec_args=("-c:a", "libmp3lame", "-b:a", "320k", "-id3v2_version", "3"),
        lossless=False,
    ),
    ExportQuality.MP3_256: ExportPreset(
        key=ExportQuality.MP3_256,
        label="MP3 — 256 kbps",
        extension=".mp3",
        muxer="mp3",
        codec_args=("-c:a", "libmp3lame", "-b:a", "256k", "-id3v2_version", "3"),
        lossless=False,
    ),
    ExportQuality.AAC_256: ExportPreset(
        key=ExportQuality.AAC_256,
        label="AAC — 256 kbps (.m4a)",
        extension=".m4a",
        muxer="ipod",
        codec_args=("-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart"),
        lossless=False,
    ),
    ExportQuality.WAV_PCM: ExportPreset(
        key=ExportQuality.WAV_PCM,
        label="WAV — PCM sem perdas",
        extension=".wav",
        muxer="wav",
        codec_args=("-c:a", "pcm_s16le"),
        lossless=True,
    ),
    ExportQuality.FLAC: ExportPreset(
        key=ExportQuality.FLAC,
        label="FLAC — sem perdas",
        extension=".flac",
        muxer="flac",
        codec_args=("-c:a", "flac", "-compression_level", "5"),
        lossless=True,
    ),
}

PARALLEL_OPTIONS: list[tuple[str, int]] = [
    ("Automático", 0),
    ("1 arquivo simultâneo", 1),
    ("2 arquivos simultâneos", 2),
    ("4 arquivos simultâneos", 4),
    ("8 arquivos simultâneos", 8),
]


def format_duration(seconds: float) -> str:
    if seconds <= 0 or math.isnan(seconds) or math.isinf(seconds):
        return "00:00"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_sample_rate(hz: int) -> str:
    if hz <= 0:
        return "—"
    if hz % 1000 == 0:
        return f"{hz // 1000} kHz"
    return f"{hz / 1000:.1f} kHz"


def is_supported_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_inside_output_dir(path: Path) -> bool:
    return any(part.upper() == OUTPUT_DIR_NAME for part in path.parts)


def resolve_auto_concurrency() -> tuple[int, int]:
    """Retorna (processos_ffmpeg_simultaneos, threads_por_processo)."""
    cpus = os.cpu_count() or 4
    if cpus <= 2:
        workers = 1
    elif cpus <= 4:
        workers = 2
    elif cpus <= 8:
        workers = 4
    else:
        workers = min(6, max(4, cpus // 2))
    threads_per_proc = max(1, min(4, cpus // workers))
    return workers, threads_per_proc


def resolve_concurrency(limit: int) -> tuple[int, int]:
    cpus = os.cpu_count() or 4
    if limit <= 0:
        return resolve_auto_concurrency()
    workers = max(1, min(limit, 8))
    threads_per_proc = max(1, min(4, cpus // workers))
    return workers, threads_per_proc


def subprocess_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def get_asset_path(filename: str) -> Path:
    """Retorna o caminho de um asset visual em execução Python ou empacotada via PyInstaller."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / "coffee_vinhetas" / "assets" / filename
            if candidate.is_file():
                return candidate
    return Path(__file__).resolve().parents[1] / "assets" / filename
