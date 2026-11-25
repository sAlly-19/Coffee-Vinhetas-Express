"""Cartão Configurações de Mixagem (Ducking) — limpo e fiel à referência."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import COLOR_AMBER, COLOR_TEXT, COLOR_TEXT_DIM, COLOR_WARNING
from ...core.models import MixConfig
from ..icons import render_svg_pixmap
from ..widgets import DuckingCurveWidget, ToggleSwitch


class MixingCard(QFrame):
    """Configurações principais de mixagem (3 controles + Curva de Atenuação luminosa)."""

    config_changed = Signal(object)  # MixConfig

    def __init__(self, initial_cfg: MixConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._cfg = initial_cfg
        self._sync_guard = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 11, 14, 12)
        outer.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("sliders", 18, COLOR_AMBER))
        title = QLabel("Configurações de Mixagem (Ducking)")
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLOR_TEXT};")
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        outer.addLayout(hdr)

        body = QHBoxLayout()
        body.setSpacing(14)

        # Coluna esquerda: os 3 controles principais com ícones âmbar
        controls_col = QVBoxLayout()
        controls_col.setSpacing(10)
        controls_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)

        # Linha 1: Entrar aos (segundos)
        clock_ico = QLabel()
        clock_ico.setPixmap(render_svg_pixmap("clock", 18, COLOR_AMBER))
        clock_ico.setFixedSize(20, 20)
        entry_lbl = QLabel("Entrar aos (segundos):")
        entry_lbl.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 12px;")

        self.entry_slider = QSlider(Qt.Orientation.Horizontal)
        self.entry_slider.setRange(0, 120)
        self.entry_slider.setToolTip("Instante inicial da vinheta (aceita valores acima de 120s no campo numérico).")

        self.entry_spin = QSpinBox()
        self.entry_spin.setRange(0, 86400)
        self.entry_spin.setSuffix(" s")
        self.entry_spin.setFixedWidth(86)

        self.entry_slider.valueChanged.connect(self._on_entry_slider_changed)
        self.entry_spin.valueChanged.connect(self._on_entry_spin_changed)

        e_ticks = QHBoxLayout()
        e_ticks.setContentsMargins(2, 0, 2, 8)
        e_min = QLabel("0 s")
        e_min.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        e_max = QLabel("120 s")
        e_max.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        e_ticks.addWidget(e_min)
        e_ticks.addStretch(1)
        e_ticks.addWidget(e_max)

        grid.addWidget(clock_ico, 0, 0)
        grid.addWidget(entry_lbl, 0, 1)
        grid.addWidget(self.entry_slider, 0, 2)
        grid.addWidget(self.entry_spin, 0, 3)
        grid.addLayout(e_ticks, 1, 2)

        # Linha 2: Redução do volume da música (Ducking %)
        spk_ico = QLabel()
        spk_ico.setPixmap(render_svg_pixmap("speaker", 18, COLOR_AMBER))
        spk_ico.setFixedSize(20, 20)
        duck_lbl = QLabel("Redução do volume da música\n(Ducking %):")
        duck_lbl.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 12px;")
        duck_lbl.setToolTip(
            "Reduz temporariamente o volume da música enquanto a vinheta é reproduzida, tornando a locução mais clara."
        )

        self.duck_slider = QSlider(Qt.Orientation.Horizontal)
        self.duck_slider.setRange(10, 95)

        self.duck_spin = QSpinBox()
        self.duck_spin.setRange(10, 95)
        self.duck_spin.setSuffix(" %")
        self.duck_spin.setFixedWidth(86)

        self.duck_slider.valueChanged.connect(self._on_duck_slider_changed)
        self.duck_spin.valueChanged.connect(self._on_duck_spin_changed)

        d_ticks = QHBoxLayout()
        d_ticks.setContentsMargins(2, 0, 2, 6)
        d_min = QLabel("10 %")
        d_min.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        d_max = QLabel("95 %")
        d_max.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        d_ticks.addWidget(d_min)
        d_ticks.addStretch(1)
        d_ticks.addWidget(d_max)

        grid.addWidget(spk_ico, 2, 0)
        grid.addWidget(duck_lbl, 2, 1)
        grid.addWidget(self.duck_slider, 2, 2)
        grid.addWidget(self.duck_spin, 2, 3)
        grid.addLayout(d_ticks, 3, 2)
        grid.setColumnStretch(2, 1)
        controls_col.addLayout(grid)

        # Linha 3: Repetir a cada X minutos (Opcional)
        rep_row = QHBoxLayout()
        rep_row.setSpacing(10)
        rep_ico = QLabel()
        rep_ico.setPixmap(render_svg_pixmap("repeat", 18, COLOR_AMBER))
        rep_ico.setFixedSize(20, 20)

        self.repeat_switch = ToggleSwitch(False)
        self.repeat_switch.toggled.connect(self._on_repeat_toggled)

        rep_lbl = QLabel("Repetir a cada X minutos (Opcional)")
        rep_lbl.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 12px;")

        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 120)
        self.repeat_spin.setSuffix(" min")
        self.repeat_spin.setFixedWidth(86)
        self.repeat_spin.valueChanged.connect(self._emit_mix_changed)

        rep_row.addWidget(rep_ico)
        rep_row.addWidget(self.repeat_switch)
        rep_row.addWidget(rep_lbl)
        rep_row.addStretch(1)
        rep_row.addWidget(self.repeat_spin)
        controls_col.addLayout(rep_row)

        self.warning_lbl = QLabel("")
        self.warning_lbl.setWordWrap(True)
        self.warning_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_WARNING};")
        self.warning_lbl.setVisible(False)
        controls_col.addWidget(self.warning_lbl)

        # Divisor vertical sutil
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #3E2D21; background-color: #3E2D21; max-width: 1px;")

        # Coluna direita: Curva de Atenuação (Ducking)
        curve_col = QVBoxLayout()
        curve_col.setSpacing(4)

        curve_hdr = QHBoxLayout()
        curve_hdr.setSpacing(6)
        c_ico = QLabel()
        c_ico.setPixmap(render_svg_pixmap("curve", 16, COLOR_AMBER))
        curve_title = QLabel("Curva de Atenuação (Ducking)")
        curve_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT};")
        curve_hdr.addWidget(c_ico)
        curve_hdr.addWidget(curve_title)
        curve_hdr.addStretch(1)

        self.duck_curve = DuckingCurveWidget()
        self.duck_curve.setToolTip("Representação ilustrativa dos parâmetros configurados (não é medição do áudio final).")

        curve_col.addLayout(curve_hdr)
        curve_col.addWidget(self.duck_curve, 1)

        body.addLayout(controls_col, 3)
        body.addWidget(sep)
        body.addLayout(curve_col, 2)
        outer.addLayout(body)

        self.apply_config(initial_cfg)

    def apply_config(self, cfg: MixConfig) -> None:
        self._cfg = cfg
        self._sync_guard = True
        try:
            self.entry_spin.setValue(cfg.entry_time_sec)
            self.entry_slider.setValue(min(120, cfg.entry_time_sec))
            self.duck_spin.setValue(cfg.duck_percent)
            self.duck_slider.setValue(cfg.duck_percent)
            self.repeat_switch.setChecked(cfg.repeat_enabled, emit_signal=False)
            self.repeat_spin.setValue(cfg.repeat_interval_min)
            self.repeat_spin.setEnabled(cfg.repeat_enabled)
        finally:
            self._sync_guard = False

    def update_curve(self, jingle_duration: float) -> None:
        self.duck_curve.update_params(
            duck_percent=self._cfg.duck_percent,
            attack_ms=self._cfg.attack_ms,
            release_ms=self._cfg.release_ms,
            entry_sec=self._cfg.entry_time_sec,
            jingle_sec=jingle_duration if jingle_duration > 0 else 12.0,
        )

    def set_warning(self, message: str) -> None:
        self.warning_lbl.setText(message)
        self.warning_lbl.setVisible(bool(message))

    def set_locked(self, locked: bool) -> None:
        for w in (
            self.entry_slider,
            self.entry_spin,
            self.duck_slider,
            self.duck_spin,
            self.repeat_switch,
        ):
            w.setEnabled(not locked)
        if not locked:
            self.repeat_spin.setEnabled(self._cfg.repeat_enabled)

    def _on_entry_slider_changed(self, value: int) -> None:
        if self._sync_guard:
            return
        self._sync_guard = True
        try:
            self.entry_spin.setValue(value)
        finally:
            self._sync_guard = False
        self._emit_mix_changed()

    def _on_entry_spin_changed(self, value: int) -> None:
        if self._sync_guard:
            return
        self._sync_guard = True
        try:
            self.entry_slider.setValue(min(120, value))
        finally:
            self._sync_guard = False
        self._emit_mix_changed()

    def _on_duck_slider_changed(self, value: int) -> None:
        if self._sync_guard:
            return
        self._sync_guard = True
        try:
            self.duck_spin.setValue(value)
        finally:
            self._sync_guard = False
        self._emit_mix_changed()

    def _on_duck_spin_changed(self, value: int) -> None:
        if self._sync_guard:
            return
        self._sync_guard = True
        try:
            self.duck_slider.setValue(value)
        finally:
            self._sync_guard = False
        self._emit_mix_changed()

    def _on_repeat_toggled(self, checked: bool) -> None:
        self.repeat_spin.setEnabled(checked)
        self._emit_mix_changed()

    def _emit_mix_changed(self) -> None:
        if self._sync_guard:
            return
        self._cfg.entry_time_sec = self.entry_spin.value()
        self._cfg.duck_percent = self.duck_spin.value()
        self._cfg.repeat_enabled = self.repeat_switch.isChecked()
        self._cfg.repeat_interval_min = self.repeat_spin.value()
        self.config_changed.emit(self._cfg)
