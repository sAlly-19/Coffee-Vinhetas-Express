"""Página Sobre — identidade do aplicativo e diagnóstico real do FFmpeg."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.constants import (
    APP_AUTHOR,
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    COLOR_AMBER,
    COLOR_ERROR,
    COLOR_GREEN,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
)
from ...core.logging_setup import LOG_FILE_PATH
from ...core.models import FFmpegStatus
from ..icons import render_svg_pixmap


class AboutPage(QWidget):
    """Aba Sobre integrada à sidebar com status real do ambiente FFmpeg/FFprobe."""

    configure_ffmpeg_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(render_svg_pixmap("logo", 54))
        t_col = QVBoxLayout()
        t_lbl = QLabel(f"<b>{APP_NAME}</b>  <span style='color:{COLOR_AMBER};'>v{APP_VERSION}</span>")
        t_lbl.setStyleSheet(f"font-size: 18px; color: {COLOR_TEXT};")
        s_lbl = QLabel(APP_SUBTITLE)
        s_lbl.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_DIM};")
        a_lbl = QLabel(f"Desenvolvido por <b style='color:{COLOR_AMBER};'>{APP_AUTHOR}</b>")
        a_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")
        t_col.addWidget(t_lbl)
        t_col.addWidget(s_lbl)
        t_col.addWidget(a_lbl)
        hdr.addWidget(logo)
        hdr.addLayout(t_col, 1)
        lay.addLayout(hdr)

        desc = QLabel(
            "Aplicativo desktop 100% offline desenvolvido em Python, PySide6 (Qt6) e FFmpeg "
            "para inserção automatizada de vinhetas em músicas, podcasts, vinhetas de rádio e sets de DJ.\n\n"
            "• Processamento paralelo otimizado com controle seguro de cancelamento.\n"
            "• Ducking inteligente por envelope controlado ou sidechain calibrado.\n"
            "• Preservação integral dos arquivos originais — exportação exclusiva na subpasta COM_VINHETA.\n"
            "• Preservação de metadados musicais (artista, título, álbum) sem herdar tags da vinheta."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLOR_TEXT}; line-height: 1.45;")
        lay.addWidget(desc)

        ff_box = QFrame()
        ff_box.setObjectName("InnerCard")
        ff_lay = QVBoxLayout(ff_box)
        ff_lay.setContentsMargins(12, 10, 12, 10)
        ff_lay.setSpacing(6)

        self.ff_title_lbl = QLabel("Diagnóstico do FFmpeg / FFprobe")
        self.ff_title_lbl.setStyleSheet(f"font-weight: 700; color: {COLOR_AMBER};")
        self.ff_detail_lbl = QLabel("")
        self.ff_detail_lbl.setWordWrap(True)
        self.ff_detail_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ff_detail_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px;")
        ff_lay.addWidget(self.ff_title_lbl)
        ff_lay.addWidget(self.ff_detail_lbl)
        lay.addWidget(ff_box)

        btn_row = QHBoxLayout()
        cfg_btn = QPushButton("Configurar FFmpeg")
        cfg_btn.setObjectName("AmberBtn")
        cfg_btn.clicked.connect(self.configure_ffmpeg_requested.emit)

        logs_btn = QPushButton("Abrir pasta de logs")
        logs_btn.setObjectName("GhostBtn")
        logs_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE_PATH.parent))))

        btn_row.addWidget(cfg_btn)
        btn_row.addWidget(logs_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        lay.addStretch(1)

        outer.addWidget(card, 1)

    def update_ffmpeg_status(self, status: FFmpegStatus) -> None:
        if status.available:
            self.ff_title_lbl.setText("FFmpeg / FFprobe — Operacional")
            self.ff_title_lbl.setStyleSheet(f"font-weight: 700; color: {COLOR_GREEN};")
            self.ff_detail_lbl.setText(
                f"Versão: {status.ffmpeg_version}\n"
                f"FFmpeg: {status.ffmpeg_path}\n"
                f"FFprobe: {status.ffprobe_path}"
            )
        else:
            self.ff_title_lbl.setText("FFmpeg / FFprobe — Não encontrado")
            self.ff_title_lbl.setStyleSheet(f"font-weight: 700; color: {COLOR_ERROR};")
            self.ff_detail_lbl.setText(status.error or "Executáveis não localizados.")
