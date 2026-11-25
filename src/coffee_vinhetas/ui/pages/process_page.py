"""Página Processo — gerenciamento completo da fila de arquivos e faixas."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import (
    COLOR_AMBER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    OUTPUT_DIR_NAME,
    format_duration,
    format_sample_rate,
)
from ...core.models import AudioInfo
from ..icons import render_svg_pixmap


class ProcessPage(QWidget):
    """Aba Processo: permite gerenciar arquivos individuais, adicionar/remover faixas e alternar subpastas."""

    add_files_requested = Signal()
    select_folder_requested = Signal()
    clear_requested = Signal()
    recursive_toggled = Signal(bool)
    item_removed = Signal(object)  # Path
    back_to_home_requested = Signal()

    def __init__(self, recursive_initial: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("sliders", 18, COLOR_AMBER))
        title = QLabel("Fila de Processamento")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT};")
        back_btn = QPushButton("← Voltar ao Início")
        back_btn.setObjectName("LinkBtn")
        back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back_btn.clicked.connect(self.back_to_home_requested.emit)
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        hdr.addWidget(back_btn)
        lay.addLayout(hdr)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.add_files_btn = QPushButton("Adicionar arquivos")
        self.add_files_btn.setObjectName("GhostBtn")
        self.add_files_btn.clicked.connect(self.add_files_requested.emit)

        self.select_folder_btn = QPushButton("Selecionar pasta")
        self.select_folder_btn.setObjectName("GhostBtn")
        self.select_folder_btn.clicked.connect(self.select_folder_requested.emit)

        self.clear_btn = QPushButton("Limpar fila")
        self.clear_btn.setObjectName("GhostBtn")
        self.clear_btn.clicked.connect(self.clear_requested.emit)

        self.recursive_chk = QCheckBox("Incluir subpastas")
        self.recursive_chk.setChecked(recursive_initial)
        self.recursive_chk.toggled.connect(self.recursive_toggled.emit)

        actions.addWidget(self.add_files_btn)
        actions.addWidget(self.select_folder_btn)
        actions.addWidget(self.clear_btn)
        actions.addStretch(1)
        actions.addWidget(self.recursive_chk)
        lay.addLayout(actions)

        self.summary_lbl = QLabel("Nenhum arquivo na fila.")
        self.summary_lbl.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_DIM};")
        self.summary_lbl.setWordWrap(True)
        lay.addWidget(self.summary_lbl)

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(False)
        lay.addWidget(self.queue_list, 1)

        outer.addWidget(card, 1)

    def update_queue(
        self,
        items: list[AudioInfo],
        ignored_count: int,
        output_dir: Optional[Path],
    ) -> None:
        self.queue_list.clear()
        for info in items:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 32))

            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(8, 3, 6, 3)
            row_l.setSpacing(8)

            name_lbl = QLabel(info.path.name)
            name_lbl.setToolTip(str(info.path))
            name_lbl.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 12px; font-weight: 600;")

            meta_parts = []
            if info.format_name:
                meta_parts.append(info.format_name)
            if info.sample_rate > 0:
                meta_parts.append(format_sample_rate(info.sample_rate))
            if info.duration > 0:
                meta_parts.append(format_duration(info.duration))
            meta_lbl = QLabel(" • ".join(meta_parts) if meta_parts else "—")
            meta_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px;")

            rm_btn = QToolButton()
            rm_btn.setText("×")
            rm_btn.setObjectName("RemoveItemBtn")
            rm_btn.setFixedSize(22, 22)
            rm_btn.setToolTip(f"Remover {info.path.name} da fila")
            rm_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            rm_btn.clicked.connect(lambda _=False, p=info.path: self.item_removed.emit(p))

            row_l.addWidget(name_lbl, 1)
            row_l.addWidget(meta_lbl)
            row_l.addWidget(rm_btn)

            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, row_w)

        n = len(items)
        if n == 0:
            self.summary_lbl.setText(
                f"Nenhum arquivo válido na fila ({ignored_count} ignorado(s))."
                if ignored_count > 0
                else f"Nenhum arquivo na fila. Saídas serão gravadas na pasta {OUTPUT_DIR_NAME}."
            )
            return

        total_dur = sum(m.duration for m in items if m.duration > 0)
        parts = [f"{n} arquivo(s) válido(s)"]
        if total_dur > 0:
            parts.append(f"Duração total: {format_duration(total_dur)}")
        if ignored_count > 0:
            parts.append(f"{ignored_count} ignorado(s)")
        if output_dir:
            parts.append(f"Destino: {output_dir}")
        self.summary_lbl.setText("  •  ".join(parts))

    def set_locked(self, locked: bool) -> None:
        for w in (self.add_files_btn, self.select_folder_btn, self.clear_btn, self.recursive_chk, self.queue_list):
            w.setEnabled(not locked)
