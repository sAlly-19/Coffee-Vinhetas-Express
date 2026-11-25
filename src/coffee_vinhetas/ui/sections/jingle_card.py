"""Cartão 1 — Selecionar Arquivo da Vinheta (fiel à imagem de referência)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget

from ...core.constants import (
    COLOR_AMBER,
    COLOR_GREEN,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    format_duration,
    format_sample_rate,
)
from ...core.models import AudioInfo
from ..icons import make_svg_icon, render_svg_pixmap
from ..widgets import AudioDropZone, WaveformWidget


class JingleCard(QFrame):
    """Cartão 1. Selecionar Arquivo da Vinheta com dropzone, resumo e waveform real."""

    pick_requested = Signal()
    files_dropped = Signal(list)
    remove_requested = Signal()
    trim_requested = Signal()
    play_toggled = Signal()
    seek_requested = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(9)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("music", 18, COLOR_AMBER))
        title = QLabel("1. Selecionar Arquivo da Vinheta")
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT};")
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        layout.addLayout(hdr)

        self.drop_zone = AudioDropZone(
            "Arraste e solte o arquivo de áudio aqui",
            "ou clique para selecionar",
            "cloud_upload",
        )
        self.drop_zone.setToolTip("Formatos aceitos: MP3, WAV, OGG, M4A, FLAC e AAC.")
        self.drop_zone.clicked.connect(self.pick_requested.emit)
        self.drop_zone.files_dropped.connect(self.files_dropped.emit)
        layout.addWidget(self.drop_zone)

        # Cartão interno do arquivo selecionado
        self.file_box = QFrame()
        self.file_box.setObjectName("InnerCard")
        fb_lay = QHBoxLayout(self.file_box)
        fb_lay.setContentsMargins(10, 7, 10, 7)
        fb_lay.setSpacing(10)

        icon_box = QFrame()
        icon_box.setObjectName("FileIconBox")
        icon_box.setFixedSize(36, 36)
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ib_ico = QLabel()
        ib_ico.setPixmap(render_svg_pixmap("music", 18, "#FFE1BD"))
        ib_lay.addWidget(ib_ico)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(1)
        self.name_lbl = QLabel("Nenhuma vinheta selecionada")
        self.name_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT};")
        self.meta_lbl = QLabel("MP3 • WAV • OGG • M4A • FLAC • AAC")
        self.meta_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")
        meta_col.addWidget(self.name_lbl)
        meta_col.addWidget(self.meta_lbl)

        self.trim_btn = QPushButton("Cortar")
        self.trim_btn.setObjectName("GhostBtn")
        self.trim_btn.setIcon(make_svg_icon("scissors", 13, COLOR_AMBER))
        self.trim_btn.setToolTip("Cortar vinheta (remover silêncio ou definir início e fim)")
        self.trim_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.trim_btn.clicked.connect(self.trim_requested.emit)
        self.trim_btn.setVisible(False)

        self.remove_btn = QToolButton()
        self.remove_btn.setObjectName("RemoveItemBtn")
        self.remove_btn.setIcon(make_svg_icon("trash", 14, COLOR_TEXT_DIM))
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setToolTip("Remover vinheta selecionada")
        self.remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        self.remove_btn.setVisible(False)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(22, 22)

        fb_lay.addWidget(icon_box)
        fb_lay.addLayout(meta_col, 1)
        fb_lay.addWidget(self.trim_btn)
        fb_lay.addWidget(self.remove_btn)
        fb_lay.addWidget(self.status_dot)
        layout.addWidget(self.file_box)

        # Linha inferior: Play circular + Waveform real + Tempo
        wave_row = QHBoxLayout()
        wave_row.setSpacing(9)

        self.play_btn = QToolButton()
        self.play_btn.setObjectName("PlayCircleBtn")
        self.play_btn.setIcon(make_svg_icon("play", 15, COLOR_AMBER))
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.play_btn.setToolTip("Reproduzir ou pausar vinheta")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_toggled.emit)

        self.waveform = WaveformWidget()
        self.waveform.seek_requested.connect(self.seek_requested.emit)

        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM}; min-width: 74px;")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        wave_row.addWidget(self.play_btn)
        wave_row.addWidget(self.waveform, 1)
        wave_row.addWidget(self.time_lbl)
        layout.addLayout(wave_row)

    def show_loading(self, path: Path) -> None:
        self.name_lbl.setText(path.name)
        self.meta_lbl.setText("Analisando áudio...")
        self.status_dot.clear()
        self.trim_btn.setVisible(False)
        self.remove_btn.setVisible(False)
        self.play_btn.setEnabled(False)
        self.waveform.set_trim_range(0.0, 1.0)
        self.waveform.set_loading(True)

    def show_jingle(self, info: AudioInfo) -> None:
        self.name_lbl.setText(info.path.name)
        br_txt = f"  •  {info.bit_rate // 1000} kbps" if info.bit_rate > 0 else ""
        sr_txt = f"  •  {format_sample_rate(info.sample_rate)}" if info.sample_rate > 0 else ""
        if info.is_trimmed:
            trim_txt = f"  •  Corte: {format_duration(info.effective_duration)}"
            self.trim_btn.setStyleSheet(f"border-color: {COLOR_AMBER}; color: {COLOR_TEXT};")
            self.trim_btn.setToolTip(
                f"Corte ativo: {format_duration(info.effective_trim_start)} até {format_duration(info.effective_trim_end)} "
                f"(duração {format_duration(info.effective_duration)}). Clique para ajustar."
            )
        else:
            trim_txt = ""
            self.trim_btn.setStyleSheet("")
            self.trim_btn.setToolTip("Cortar vinheta (remover silêncio ou definir início e fim)")

        self.meta_lbl.setText(f"{info.format_name}{br_txt}{sr_txt}  •  {format_duration(info.duration)}{trim_txt}")
        self.time_lbl.setText(f"00:00 / {format_duration(info.effective_duration)}")
        self.status_dot.setPixmap(render_svg_pixmap("check", 20, "#38D964"))
        self.trim_btn.setVisible(True)
        self.remove_btn.setVisible(True)
        self.play_btn.setEnabled(True)
        self.waveform.set_peaks(info.peaks)
        if info.duration > 0 and info.is_trimmed:
            self.waveform.set_trim_range(
                info.effective_trim_start / info.duration,
                info.effective_trim_end / info.duration,
            )
            self.waveform.set_progress(info.effective_trim_start / info.duration)
        else:
            self.waveform.set_trim_range(0.0, 1.0)
            self.waveform.set_progress(0.0)

    def show_empty(self) -> None:
        self.name_lbl.setText("Nenhuma vinheta selecionada")
        self.meta_lbl.setText("MP3 • WAV • OGG • M4A • FLAC • AAC")
        self.time_lbl.setText("00:00 / 00:00")
        self.status_dot.clear()
        self.trim_btn.setVisible(False)
        self.trim_btn.setStyleSheet("")
        self.remove_btn.setVisible(False)
        self.play_btn.setEnabled(False)
        self.waveform.set_trim_range(0.0, 1.0)
        self.waveform.clear()

    def set_playback_state(
        self,
        playing: bool,
        pos_sec: float = 0.0,
        total_sec: float = 0.0,
        trim_start: float = 0.0,
        effective_dur: float = 0.0,
    ) -> None:
        self.play_btn.setIcon(make_svg_icon("pause" if playing else "play", 15, COLOR_AMBER))
        if total_sec > 0:
            self.waveform.set_progress(min(1.0, max(0.0, pos_sec / total_sec)))
            if effective_dur > 0:
                rel = max(0.0, min(effective_dur, pos_sec - trim_start))
                self.time_lbl.setText(f"{format_duration(rel)} / {format_duration(effective_dur)}")
            else:
                self.time_lbl.setText(f"{format_duration(pos_sec)} / {format_duration(total_sec)}")

    def set_locked(self, locked: bool) -> None:
        self.drop_zone.setEnabled(not locked)
        self.trim_btn.setEnabled(not locked)
        self.remove_btn.setEnabled(not locked)
