"""Diálogo de informações sobre o aplicativo e ambiente FFmpeg."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.constants import APP_AUTHOR, APP_NAME, APP_SUBTITLE, APP_VERSION, COLOR_AMBER, COLOR_TEXT, COLOR_TEXT_DIM
from ...core.models import FFmpegStatus
from ..icons import render_svg_pixmap
from ..theme import apply_windows_dark_titlebar


class AboutDialog(QDialog):
    """Informações sobre o aplicativo, fluxo e ambiente FFmpeg real."""

    def __init__(self, ff_status: FFmpegStatus, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Sobre — {APP_NAME}")
        self.setMinimumWidth(470)
        self._dark_applied = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(render_svg_pixmap("logo", 44))
        title_box = QVBoxLayout()
        t = QLabel(f"<b>{APP_NAME}</b>  v{APP_VERSION}")
        t.setStyleSheet(f"font-size: 16px; color: {COLOR_TEXT};")
        s = QLabel(APP_SUBTITLE)
        s.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        a = QLabel(f"Desenvolvido por <b style='color:{COLOR_AMBER};'>{APP_AUTHOR}</b>")
        a.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")
        title_box.addWidget(t)
        title_box.addWidget(s)
        title_box.addWidget(a)
        header.addWidget(logo)
        header.addLayout(title_box, 1)
        layout.addLayout(header)

        info = QLabel(
            "Processador offline de alta velocidade para inserção automática de vinhetas em "
            "músicas, podcasts e sets de DJ, com ducking suave e preservação dos arquivos originais.\n\n"
            "• Nenhuma mídia é enviada para serviços externos.\n"
            "• Saídas são gravadas exclusivamente na subpasta COM_VINHETA."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLOR_TEXT}; line-height: 1.4;")
        layout.addWidget(info)

        ff_box = QFrame()
        ff_box.setObjectName("InnerCard")
        ff_lay = QVBoxLayout(ff_box)
        if ff_status.available:
            ff_text = (
                f"<b>FFmpeg:</b> {ff_status.ffmpeg_version}<br>"
                f"<b>Caminho:</b> {ff_status.ffmpeg_path}<br>"
                f"<b>FFprobe:</b> {ff_status.ffprobe_path}"
            )
        else:
            ff_text = f"<b>FFmpeg indisponível:</b> {ff_status.error}"
        ff_lbl = QLabel(ff_text)
        ff_lbl.setWordWrap(True)
        ff_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ff_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px;")
        ff_lay.addWidget(ff_lbl)
        layout.addWidget(ff_box)

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_applied:
            self._dark_applied = True
            apply_windows_dark_titlebar(self)
