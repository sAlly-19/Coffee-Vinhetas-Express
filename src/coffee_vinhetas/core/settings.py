"""Persistência de preferências do usuário via QSettings."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtCore import QByteArray, QSettings

from .constants import APP_ORG, ConflictPolicy, DuckingMode, ExportQuality
from .models import MixConfig


class SettingsManager:
    """Gerencia preferências persistentes via QSettings."""

    def __init__(self) -> None:
        self._settings = QSettings(APP_ORG, "CoffeeVinhetasExpress")

    def load_mix_config(self) -> MixConfig:
        entry = self._int("mix/entry_time_sec", 15)
        duck = max(10, min(95, self._int("mix/duck_percent", 75)))
        attack = max(10, min(2000, self._int("mix/attack_ms", 150)))
        release = max(50, min(5000, self._int("mix/release_ms", 600)))
        repeat_en = self._bool("mix/repeat_enabled", False)
        repeat_min = max(1, min(120, self._int("mix/repeat_interval_min", 5)))
        parallel = self._int("mix/parallel_limit", 0)
        if parallel not in (0, 1, 2, 4, 8):
            parallel = 0

        quality = self._enum("mix/export_quality", ExportQuality, ExportQuality.MP3_320)
        mode = self._enum("mix/ducking_mode", DuckingMode, DuckingMode.ENVELOPE)
        policy = self._enum("mix/conflict_policy", ConflictPolicy, ConflictPolicy.ASK)

        return MixConfig(
            entry_time_sec=max(0, entry),
            duck_percent=duck,
            attack_ms=attack,
            release_ms=release,
            repeat_enabled=repeat_en,
            repeat_interval_min=repeat_min,
            export_quality=quality,
            ducking_mode=mode,
            parallel_limit=parallel,
            conflict_policy=policy,
        )

    def save_mix_config(self, cfg: MixConfig) -> None:
        self._settings.setValue("mix/entry_time_sec", cfg.entry_time_sec)
        self._settings.setValue("mix/duck_percent", cfg.duck_percent)
        self._settings.setValue("mix/attack_ms", cfg.attack_ms)
        self._settings.setValue("mix/release_ms", cfg.release_ms)
        self._settings.setValue("mix/repeat_enabled", cfg.repeat_enabled)
        self._settings.setValue("mix/repeat_interval_min", cfg.repeat_interval_min)
        self._settings.setValue("mix/export_quality", self._enum_value(cfg.export_quality))
        self._settings.setValue("mix/ducking_mode", self._enum_value(cfg.ducking_mode))
        self._settings.setValue("mix/parallel_limit", cfg.parallel_limit)
        self._settings.setValue("mix/conflict_policy", self._enum_value(cfg.conflict_policy))

    @property
    def last_jingle_path(self) -> str:
        return str(self._settings.value("paths/last_jingle", ""))

    @last_jingle_path.setter
    def last_jingle_path(self, value: str) -> None:
        self._settings.setValue("paths/last_jingle", value)

    def load_jingle_trim(self, jingle_path: str) -> tuple[float, float]:
        saved_path = str(self._settings.value("paths/last_jingle_trim_path", ""))
        if not jingle_path or saved_path != jingle_path:
            return 0.0, 0.0
        try:
            t_start = float(self._settings.value("paths/last_jingle_trim_start", 0.0))
            t_end = float(self._settings.value("paths/last_jingle_trim_end", 0.0))
            return max(0.0, t_start), max(0.0, t_end)
        except (TypeError, ValueError):
            return 0.0, 0.0

    def save_jingle_trim(self, jingle_path: str, trim_start: float, trim_end: float) -> None:
        self._settings.setValue("paths/last_jingle_trim_path", jingle_path)
        self._settings.setValue("paths/last_jingle_trim_start", float(trim_start))
        self._settings.setValue("paths/last_jingle_trim_end", float(trim_end))

    @property
    def last_music_folder(self) -> str:
        return str(self._settings.value("paths/last_music_folder", ""))

    @last_music_folder.setter
    def last_music_folder(self, value: str) -> None:
        self._settings.setValue("paths/last_music_folder", value)

    @property
    def recursive_scan(self) -> bool:
        return self._bool("paths/recursive_scan", False)

    @recursive_scan.setter
    def recursive_scan(self, value: bool) -> None:
        self._settings.setValue("paths/recursive_scan", value)

    @property
    def custom_ffmpeg_dir(self) -> str:
        return str(self._settings.value("paths/custom_ffmpeg_dir", ""))

    @custom_ffmpeg_dir.setter
    def custom_ffmpeg_dir(self, value: str) -> None:
        self._settings.setValue("paths/custom_ffmpeg_dir", value)

    def save_window_geometry(self, geometry: QByteArray) -> None:
        self._settings.setValue("window/geometry", geometry)

    def load_window_geometry(self) -> Optional[QByteArray]:
        val = self._settings.value("window/geometry")
        return val if isinstance(val, QByteArray) and not val.isEmpty() else None

    def _int(self, key: str, default: int) -> int:
        try:
            return int(self._settings.value(key, default))
        except (TypeError, ValueError):
            return default

    def _bool(self, key: str, default: bool) -> bool:
        val = self._settings.value(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "sim")
        return bool(val)

    def _enum(self, key: str, enum_cls: type[Enum], default: Enum):
        raw = str(self._settings.value(key, default.value))
        try:
            return enum_cls(raw)
        except ValueError:
            return default

    @staticmethod
    def _enum_value(val: object) -> str:
        return val.value if isinstance(val, Enum) else str(val)
