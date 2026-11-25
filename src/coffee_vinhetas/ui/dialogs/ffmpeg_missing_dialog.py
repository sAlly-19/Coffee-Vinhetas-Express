"""Diálogo de orientação quando FFmpeg/FFprobe não são encontrados."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.constants import COLOR_TEXT, COLOR_WARNING
from ..theme import apply_windows_dark_titlebar


class FFmpegMissingDialog(QDialog):
    """Orienta o usuário quando FFmpeg/FFprobe não foram localizados."""

    def __init__(self, error_msg: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FFmpeg / FFprobe não encontrados")
        self.setMinimumWidth(500)
        self.selected_dir: str = ""
        self._dark_applied = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        title = QLabel("É necessário configurar o FFmpeg e o FFprobe para processar áudio.")
        title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLOR_WARNING};")
        title.setWordWrap(True)
        layout.addWidget(title)

        detail = QLabel(
            f"Detalhe: {error_msg}\n\n"
            "Como resolver no Windows:\n"
            "1. Instale via terminal: winget install Gyan.FFmpeg\n"
            "   (ou copie ffmpeg.exe e ffprobe.exe para a pasta do aplicativo)\n"
            "2. Ou selecione manualmente a pasta onde estão ffmpeg.exe e ffprobe.exe."
        )
        detail.setWordWrap(True)
        detail.setStyleSheet(f"color: {COLOR_TEXT};")
        layout.addWidget(detail)

        row = QHBoxLayout()
        pick_btn = QPushButton("Selecionar pasta do FFmpeg...")
        pick_btn.clicked.connect(self._pick_folder)
        close_btn = QPushButton("Continuar sem FFmpeg")
        close_btn.clicked.connect(self.reject)
        row.addWidget(pick_btn)
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_applied:
            self._dark_applied = True
            apply_windows_dark_titlebar(self)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta com ffmpeg.exe e ffprobe.exe")
        if folder:
            self.selected_dir = folder
            self.accept()
