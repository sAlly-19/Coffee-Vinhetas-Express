"""Diálogo detalhado com status individual por faixa após processamento em lote."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import COLOR_ERROR, COLOR_GREEN, COLOR_TEXT, COLOR_WARNING
from ...core.logging_setup import LOG_FILE_PATH
from ...core.models import BatchSummary, TaskStatus
from ..theme import apply_windows_dark_titlebar


class BatchDetailsDialog(QDialog):
    """Tabela detalhada de resultados individuais e mensagens de diagnóstico."""

    def __init__(self, summary: BatchSummary, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detalhes do processamento")
        self.resize(780, 480)
        self._dark_applied = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        hdr = QLabel(
            f"Total: {summary.total}  •  Concluídos: {summary.succeeded}  •  "
            f"Falhas: {summary.failed}  •  Cancelados/Ignorados: {summary.skipped_or_cancelled}  •  "
            f"Tempo: {summary.elapsed_sec:.1f}s"
        )
        hdr.setStyleSheet(f"color: {COLOR_TEXT}; font-weight: 600;")
        layout.addWidget(hdr)

        table = QTableWidget(len(summary.results), 4)
        table.setHorizontalHeaderLabels(["Arquivo de origem", "Status", "Duração / Saída", "Observação"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for row_idx, res in enumerate(summary.results):
            src_item = QTableWidgetItem(res.source_path.name)
            src_item.setToolTip(str(res.source_path))

            st_item = QTableWidgetItem(res.status.value)
            if res.status == TaskStatus.SUCCESS:
                st_item.setForeground(QColor(COLOR_GREEN))
            elif res.status == TaskStatus.FAILED:
                st_item.setForeground(QColor(COLOR_ERROR))
            else:
                st_item.setForeground(QColor(COLOR_WARNING))

            out_text = f"{res.elapsed_sec:.1f}s • {res.output_path.name}" if res.output_path else f"{res.elapsed_sec:.1f}s"
            out_item = QTableWidgetItem(out_text)
            if res.output_path:
                out_item.setToolTip(str(res.output_path))

            msg_item = QTableWidgetItem(res.message or res.warning)
            msg_item.setToolTip(res.message or res.warning)

            table.setItem(row_idx, 0, src_item)
            table.setItem(row_idx, 1, st_item)
            table.setItem(row_idx, 2, out_item)
            table.setItem(row_idx, 3, msg_item)

        layout.addWidget(table, 1)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Abrir pasta de destino")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(summary.output_dir))))
        log_btn = QPushButton("Abrir log")
        log_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE_PATH))))
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(open_btn)
        btn_row.addWidget(log_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_applied:
            self._dark_applied = True
            apply_windows_dark_titlebar(self)
