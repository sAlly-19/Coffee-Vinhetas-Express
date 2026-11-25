"""Página Histórico — execuções reais anteriores salvas localmente."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import COLOR_AMBER, COLOR_ERROR, COLOR_GREEN, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_WARNING
from ...core.history import HistoryEntry
from ..icons import render_svg_pixmap


class HistoryPage(QWidget):
    """Aba Histórico: exibe execuções reais concluídas com abertura de pasta e detalhes."""

    details_requested = Signal(object)  # HistoryEntry
    clear_history_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._entries: list[HistoryEntry] = []

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
        ico.setPixmap(render_svg_pixmap("history", 18, COLOR_AMBER))
        title = QLabel("Histórico de Processamentos")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT};")

        self.clear_btn = QPushButton("Limpar histórico")
        self.clear_btn.setObjectName("GhostBtn")
        self.clear_btn.clicked.connect(self.clear_history_requested.emit)

        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        hdr.addWidget(self.clear_btn)
        lay.addLayout(hdr)

        self.empty_lbl = QLabel("Nenhum processamento registrado ainda. Após concluir um lote, ele aparecerá aqui.")
        self.empty_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 12px;")
        lay.addWidget(self.empty_lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Data / Hora", "Resultado", "Tempo", "Pasta de destino", "Ações"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table, 1)

        outer.addWidget(card, 1)

    def set_entries(self, entries: list[HistoryEntry]) -> None:
        self._entries = entries
        self.empty_lbl.setVisible(len(entries) == 0)
        self.table.setRowCount(len(entries))

        for row_idx, entry in enumerate(entries):
            self.table.setRowHeight(row_idx, 36)
            ts_item = QTableWidgetItem(entry.timestamp)

            status_txt = f"{entry.succeeded}/{entry.total} OK"
            if entry.failed > 0:
                status_txt += f" • {entry.failed} erro(s)"
            if entry.cancelled:
                status_txt += " (cancelado)"
            st_item = QTableWidgetItem(status_txt)
            if entry.cancelled:
                st_item.setForeground(QColor(COLOR_WARNING))
            elif entry.failed > 0 and entry.succeeded == 0:
                st_item.setForeground(QColor(COLOR_ERROR))
            else:
                st_item.setForeground(QColor(COLOR_GREEN))

            time_item = QTableWidgetItem(f"{entry.elapsed_sec:.1f}s")
            dir_item = QTableWidgetItem(entry.output_dir)
            dir_item.setToolTip(entry.output_dir)

            self.table.setItem(row_idx, 0, ts_item)
            self.table.setItem(row_idx, 1, st_item)
            self.table.setItem(row_idx, 2, time_item)
            self.table.setItem(row_idx, 3, dir_item)

            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(4, 2, 4, 2)
            act_l.setSpacing(6)

            det_btn = QPushButton("Detalhes")
            det_btn.setObjectName("GhostBtn")
            det_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            det_btn.clicked.connect(lambda _=False, e=entry: self.details_requested.emit(e))

            open_btn = QPushButton("Pasta")
            open_btn.setObjectName("GhostBtn")
            open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_btn.clicked.connect(lambda _=False, p=entry.output_dir: self._open_dir(p))

            act_l.addWidget(det_btn)
            act_l.addWidget(open_btn)
            self.table.setCellWidget(row_idx, 4, act_w)

    @staticmethod
    def _open_dir(folder: str) -> None:
        p = Path(folder)
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
