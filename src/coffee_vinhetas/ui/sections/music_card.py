"""Cartão 2 — Selecionar Pasta com as Músicas (fiel à imagem de referência)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.constants import (
    COLOR_AMBER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    OUTPUT_DIR_NAME,
    format_duration,
)
from ...core.models import AudioInfo
from ..icons import render_svg_pixmap
from ..widgets import AudioDropZone


class MusicCard(QFrame):
    """Cartão 2. Selecionar Pasta com as Músicas com resumo limpo e atalho para a fila."""

    select_folder_requested = Signal()
    files_dropped = Signal(list)
    manage_queue_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(9)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("folder", 18, COLOR_AMBER))
        title = QLabel("2. Selecionar Pasta com as Músicas")
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT};")
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        layout.addLayout(hdr)

        self.drop_zone = AudioDropZone(
            "Arraste e solte uma pasta ou múltiplos arquivos",
            "ou clique para selecionar",
            "folder",
        )
        self.drop_zone.setToolTip("Arraste uma pasta ou vários arquivos. A pasta COM_VINHETA é ignorada automaticamente.")
        self.drop_zone.clicked.connect(self.select_folder_requested.emit)
        self.drop_zone.files_dropped.connect(self.files_dropped.emit)
        layout.addWidget(self.drop_zone)

        # Cartão de resumo da pasta / arquivos
        summary_box = QFrame()
        summary_box.setObjectName("InnerCard")
        sb_lay = QHBoxLayout(summary_box)
        sb_lay.setContentsMargins(10, 7, 10, 7)
        sb_lay.setSpacing(10)

        folder_ico = QLabel()
        folder_ico.setPixmap(render_svg_pixmap("folder", 28, COLOR_AMBER))
        folder_ico.setFixedSize(32, 32)
        folder_ico.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self.path_lbl = QLabel("Nenhuma pasta selecionada")
        self.path_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT};")
        self.path_lbl.setWordWrap(False)

        self.count_lbl = QLabel(f"Saída automática em {OUTPUT_DIR_NAME}")
        self.count_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLOR_TEXT_DIM};")

        text_col.addWidget(self.path_lbl)
        text_col.addWidget(self.count_lbl)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(22, 22)

        sb_lay.addWidget(folder_ico)
        sb_lay.addLayout(text_col, 1)
        sb_lay.addWidget(self.status_dot)
        layout.addWidget(summary_box)

        # Rodapé de formatos + link para gerenciar fila na aba Processo
        footer = QHBoxLayout()
        footer.setSpacing(6)
        fmt_ico = QLabel()
        fmt_ico.setPixmap(render_svg_pixmap("music", 14, COLOR_TEXT_DIM))
        fmt_lbl = QLabel("Formatos: MP3, WAV, OGG, M4A, FLAC")
        fmt_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")

        self.manage_btn = QPushButton("Gerenciar fila →")
        self.manage_btn.setObjectName("LinkBtn")
        self.manage_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.manage_btn.setToolTip("Abrir a aba Processo para adicionar/remover faixas individuais.")
        self.manage_btn.clicked.connect(self.manage_queue_requested.emit)

        footer.addWidget(fmt_ico)
        footer.addWidget(fmt_lbl)
        footer.addStretch(1)
        footer.addWidget(self.manage_btn)
        layout.addLayout(footer)

    def set_scanning(self) -> None:
        self.count_lbl.setText("Analisando arquivos...")
        self.count_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLOR_AMBER};")

    def update_summary(
        self,
        items: list[AudioInfo],
        ignored_count: int,
        selected_folder: Optional[Path],
        output_dir: Optional[Path],
    ) -> None:
        n = len(items)
        if n == 0:
            self.path_lbl.setText("Nenhuma pasta selecionada")
            self.path_lbl.setToolTip("")
            self.count_lbl.setText(
                f"{ignored_count} arquivo(s) ignorado(s)" if ignored_count > 0 else f"Saída automática em {OUTPUT_DIR_NAME}"
            )
            self.count_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLOR_TEXT_DIM};")
            self.status_dot.clear()
            return

        origin = str(selected_folder) if selected_folder else f"{len({m.path.parent for m in items})} origem(ns) selecionada(s)"
        fm = QFontMetrics(self.path_lbl.font())
        max_w = max(210, self.path_lbl.width() if self.path_lbl.width() > 60 else 310)
        self.path_lbl.setText(fm.elidedText(origin, Qt.TextElideMode.ElideMiddle, max_w))
        self.path_lbl.setToolTip(f"Origem: {origin}\nDestino: {output_dir}")

        total_dur = sum(m.duration for m in items if m.duration > 0)
        parts = [f"{n} arquivo encontrado" if n == 1 else f"{n} arquivos encontrados"]
        if total_dur > 0:
            parts.append(format_duration(total_dur))
        if ignored_count > 0:
            parts.append(f"{ignored_count} ignorado(s)")
        self.count_lbl.setText("  •  ".join(parts))
        self.count_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #4BE373;")
        self.status_dot.setPixmap(render_svg_pixmap("check", 20, "#38D964"))

    def set_locked(self, locked: bool) -> None:
        self.drop_zone.setEnabled(not locked)
