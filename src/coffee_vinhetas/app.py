"""Inicialização e ciclo de vida do aplicativo Coffee Vinhetas Express."""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .core import APP_NAME, APP_ORG, LOGGER, SettingsManager
from .ui import MainWindow, build_stylesheet


class CoffeeVinhetasApp:
    """Configura QApplication, tema Coffee Design System e janela principal."""

    def __init__(self, argv: Optional[list[str]] = None) -> None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(argv if argv is not None else sys.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setOrganizationName(APP_ORG)
        self.app.setFont(QFont("Segoe UI", 9))
        self.app.setStyleSheet(build_stylesheet())

        self.settings_mgr = SettingsManager()
        self.window = MainWindow(self.settings_mgr)

    def run(self) -> int:
        self.window.show()
        if not self.window.ffmpeg_mgr.status.available:
            QTimer.singleShot(
                250, lambda: self.window._refresh_ffmpeg_status(show_dialog_if_missing=True)
            )
        return self.app.exec()


def main() -> int:
    try:
        application = CoffeeVinhetasApp()
        return application.run()
    except Exception:
        LOGGER.exception("Erro fatal ao iniciar o Coffee Vinhetas Express.")
        return 1
