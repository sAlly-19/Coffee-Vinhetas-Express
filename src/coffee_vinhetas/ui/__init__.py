"""Camada de interface gráfica (Qt6/PySide6) do Coffee Vinhetas Express."""

from .main_window import MainWindow
from .theme import apply_windows_dark_titlebar, build_stylesheet

__all__ = ["MainWindow", "apply_windows_dark_titlebar", "build_stylesheet"]
