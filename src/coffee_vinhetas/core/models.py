"""Modelos de dados de áudio, configuração de mixagem e resultados de lote."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .constants import ConflictPolicy, DuckingMode, ExportQuality


@dataclass
class AudioInfo:
    path: Path
    duration: float = 0.0
    sample_rate: int = 0
    channels: int = 2
    codec_name: str = ""
    format_name: str = ""
    bit_rate: int = 0
    size_bytes: int = 0
    mean_volume_db: float = -18.0
    active_start: float = 0.0
    active_end: float = 0.0
    trim_start: float = 0.0
    trim_end: float = 0.0
    peaks: list[float] = field(default_factory=list)
    valid: bool = True
    error: str = ""

    @property
    def effective_trim_start(self) -> float:
        if self.duration <= 0:
            return 0.0
        return max(0.0, min(self.trim_start, max(0.0, self.duration - 0.1)))

    @property
    def effective_trim_end(self) -> float:
        if self.duration <= 0:
            return 0.0
        if self.trim_end <= 0 or self.trim_end > self.duration:
            return self.duration
        return max(self.effective_trim_start + 0.1, min(self.trim_end, self.duration))

    @property
    def effective_duration(self) -> float:
        if self.duration <= 0:
            return 0.0
        return max(0.1, self.effective_trim_end - self.effective_trim_start)

    @property
    def is_trimmed(self) -> bool:
        if self.duration <= 0:
            return False
        return self.effective_trim_start > 0.01 or self.effective_trim_end < (self.duration - 0.01)


@dataclass
class MixConfig:
    entry_time_sec: int = 15
    duck_percent: int = 75
    attack_ms: int = 150
    release_ms: int = 600
    repeat_enabled: bool = False
    repeat_interval_min: int = 5
    export_quality: ExportQuality = ExportQuality.MP3_320
    ducking_mode: DuckingMode = DuckingMode.ENVELOPE
    parallel_limit: int = 0  # 0 = Automático
    conflict_policy: ConflictPolicy = ConflictPolicy.ASK


@dataclass
class TrackTask:
    source_path: Path
    output_path: Path
    duration: float = 0.0
    sample_rate: int = 44100


class TaskStatus(str, Enum):
    SUCCESS = "Concluído"
    FAILED = "Falhou"
    SKIPPED = "Ignorado"
    CANCELLED = "Cancelado"


@dataclass
class TrackResult:
    source_path: Path
    output_path: Optional[Path]
    status: TaskStatus
    message: str = ""
    warning: str = ""
    elapsed_sec: float = 0.0
    insertions: int = 0


@dataclass
class BatchSummary:
    total: int
    succeeded: int
    failed: int
    skipped_or_cancelled: int
    elapsed_sec: float
    output_dir: Path
    cancelled: bool
    results: list[TrackResult] = field(default_factory=list)


@dataclass
class FFmpegStatus:
    available: bool
    ffmpeg_path: Optional[Path] = None
    ffprobe_path: Optional[Path] = None
    ffmpeg_version: str = ""
    ffprobe_version: str = ""
    error: str = ""
