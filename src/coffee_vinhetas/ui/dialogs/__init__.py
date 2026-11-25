"""Diálogos modais do aplicativo."""

from .about_dialog import AboutDialog
from .batch_details_dialog import BatchDetailsDialog
from .ffmpeg_missing_dialog import FFmpegMissingDialog
from .jingle_trim_dialog import JingleTrimDialog
from .settings_dialog import SettingsDialog

__all__ = [
    "AboutDialog",
    "BatchDetailsDialog",
    "FFmpegMissingDialog",
    "JingleTrimDialog",
    "SettingsDialog",
]
