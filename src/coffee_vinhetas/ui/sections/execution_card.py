"""Cartão Execução, Prévia e Progresso — fiel à imagem de referência."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ...core.constants import (
    COLOR_AMBER,
    COLOR_ERROR,
    COLOR_GREEN,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_WARNING,
    format_duration,
)
from ...core.models import BatchSummary
from ..icons import make_svg_icon, render_svg_pixmap


class ExecutionCard(QFrame):
    """Painel inferior de execução, prévia real, progresso e resumo pós-lote."""

    preview_clicked = Signal()
    process_clicked = Signal()
    open_output_clicked = Signal()
    details_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 12)
        lay.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("play_circle", 18, COLOR_AMBER))
        title = QLabel("Execução, Prévia e Progresso")
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT};")
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        lay.addLayout(hdr)

        # Barra de progresso espessa + percentual grande à direita
        prog_row = QHBoxLayout()
        prog_row.setSpacing(12)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(16)

        self.progress_pct_lbl = QLabel("0%")
        self.progress_pct_lbl.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {COLOR_TEXT}; min-width: 46px;")
        self.progress_pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        prog_row.addWidget(self.progress_bar, 1)
        prog_row.addWidget(self.progress_pct_lbl)
        lay.addLayout(prog_row)

        # Linha de status real + indicador real de paralelismo/formato à direita
        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        gear_ico = QLabel()
        gear_ico.setPixmap(render_svg_pixmap("settings", 15, COLOR_TEXT_DIM))
        self.status_lbl = QLabel("Pronto para processar.")
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLOR_TEXT};")

        cpu_ico = QLabel()
        cpu_ico.setPixmap(render_svg_pixmap("cpu", 16, "#5CE07B"))
        self.concurrency_lbl = QLabel("")
        self.concurrency_lbl.setStyleSheet("font-size: 11px; color: #7EE897; font-weight: 600;")

        status_row.addWidget(gear_ico)
        status_row.addWidget(self.status_lbl, 1)
        status_row.addWidget(cpu_ico)
        status_row.addWidget(self.concurrency_lbl)
        lay.addLayout(status_row)

        # Botões principais grandes
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self.preview_btn = QPushButton("  OUVIR PRÉVIA")
        self.preview_btn.setObjectName("PreviewBtn")
        self.preview_btn.setIcon(make_svg_icon("play_circle", 20, COLOR_AMBER))
        self.preview_btn.setIconSize(QSize(20, 20))
        self.preview_btn.setMinimumHeight(44)
        self.preview_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.preview_btn.clicked.connect(self.preview_clicked.emit)

        self.process_btn = QPushButton("  PROCESSAR TUDO AGORA  »")
        self.process_btn.setObjectName("PrimaryGreenBtn")
        self.process_btn.setIcon(make_svg_icon("settings", 19, "#FFFFFF"))
        self.process_btn.setIconSize(QSize(19, 19))
        self.process_btn.setMinimumHeight(44)
        self.process_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.process_btn.clicked.connect(self.process_clicked.emit)

        btn_row.addWidget(self.preview_btn, 10)
        btn_row.addWidget(self.process_btn, 13)
        lay.addLayout(btn_row)

        # Faixa discreta de conclusão pós-lote
        self.result_box = QFrame()
        self.result_box.setObjectName("InnerCard")
        res_lay = QHBoxLayout(self.result_box)
        res_lay.setContentsMargins(10, 7, 10, 7)
        res_lay.setSpacing(10)

        self.result_lbl = QLabel("")
        self.result_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT};")
        self.result_lbl.setWordWrap(True)

        self.open_out_btn = QPushButton("ABRIR PASTA")
        self.open_out_btn.setObjectName("AmberBtn")
        self.open_out_btn.clicked.connect(self.open_output_clicked.emit)

        self.details_btn = QPushButton("VER DETALHES")
        self.details_btn.setObjectName("GhostBtn")
        self.details_btn.clicked.connect(self.details_clicked.emit)

        res_lay.addWidget(self.result_lbl, 1)
        res_lay.addWidget(self.open_out_btn)
        res_lay.addWidget(self.details_btn)
        self.result_box.setVisible(False)
        lay.addWidget(self.result_box)

    def set_concurrency_info(self, text: str) -> None:
        self.concurrency_lbl.setText(text)

    def set_readiness(self, can_run: bool, can_preview: bool, running: bool, reasons: list[str]) -> None:
        if running:
            self.preview_btn.setEnabled(False)
            self.process_btn.setEnabled(True)
            return

        self.process_btn.setEnabled(can_run)
        self.preview_btn.setEnabled(can_preview)
        if can_run:
            if self.status_lbl.text().startswith("Para iniciar:"):
                self.status_lbl.setText("Pronto para processar.")
        else:
            self.status_lbl.setText("Para iniciar: " + "; ".join(reasons) + ".")

    def set_preview_generating(self, track_name: str) -> None:
        self.preview_btn.setText("  GERANDO PRÉVIA...")
        self.preview_btn.setIcon(make_svg_icon("stop", 18, COLOR_AMBER))
        self.status_lbl.setText(f"Gerando prévia com ducking para {track_name}...")

    def set_preview_playing(self, desc: str) -> None:
        self.preview_btn.setText("  PARAR PRÉVIA")
        self.preview_btn.setIcon(make_svg_icon("stop", 18, COLOR_ERROR))
        self.status_lbl.setText(f"Reproduzindo prévia: {desc}")

    def reset_preview_button(self) -> None:
        self.preview_btn.setText("  OUVIR PRÉVIA")
        self.preview_btn.setIcon(make_svg_icon("play_circle", 20, COLOR_AMBER))

    def start_batch_view(self, total_tasks: int) -> None:
        self.result_box.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_pct_lbl.setText("0%")
        self.status_lbl.setText(f"Processando: 0 de {total_tasks} faixas...")
        self._set_process_button_style("CancelRedBtn", "  CANCELAR PROCESSAMENTO", "stop")

    def set_cancelling(self) -> None:
        self.process_btn.setEnabled(False)
        self.process_btn.setText("  CANCELANDO...")
        self.status_lbl.setText("Cancelando processamento com segurança...")

    def update_batch_progress(
        self,
        pct: float,
        done: int,
        total: int,
        active: int,
        errors: int,
        current_file: str,
        elapsed: float,
        eta: float,
    ) -> None:
        self.progress_bar.setValue(int(round(pct * 10)))
        self.progress_pct_lbl.setText(f"{int(round(pct))}%")
        eta_str = f" • Restante est.: {format_duration(eta)}" if eta >= 0 else ""
        self.status_lbl.setText(
            f"Processando: {done} de {total} faixas ({active} em execução • {errors} erros{eta_str})"
        )

    def show_batch_completed(self, summary: BatchSummary) -> None:
        self._set_process_button_style("PrimaryGreenBtn", "  PROCESSAR TUDO AGORA  »", "settings")

        if not summary.cancelled:
            self.progress_bar.setValue(1000)
            self.progress_pct_lbl.setText("100%")
            self.status_lbl.setText(
                f"Concluído: {summary.succeeded} de {summary.total} faixas em {summary.elapsed_sec:.1f}s"
            )
            prefix = f'<b style="color:{COLOR_GREEN};">Processamento concluído</b>'
        else:
            self.status_lbl.setText(
                f"Cancelado: {summary.succeeded} concluído(s) preservados ({summary.elapsed_sec:.1f}s)"
            )
            prefix = f'<b style="color:{COLOR_WARNING};">Processamento cancelado</b>'

        self.result_lbl.setText(
            f"{prefix} — {summary.succeeded} OK • {summary.failed} falhas • "
            f"{summary.skipped_or_cancelled} ignorados/cancelados • Destino: {summary.output_dir}"
        )
        self.result_box.setVisible(True)

    def _set_process_button_style(self, obj_name: str, text: str, icon_name: str) -> None:
        self.process_btn.setObjectName(obj_name)
        self.process_btn.setText(text)
        self.process_btn.setIcon(make_svg_icon(icon_name, 19, "#FFFFFF"))
        self.process_btn.style().unpolish(self.process_btn)
        self.process_btn.style().polish(self.process_btn)
