"""Página Configurações — formato de exportação, paralelismo, DSP e FFmpeg."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import (
    COLOR_AMBER,
    COLOR_ERROR,
    COLOR_GREEN,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    EXPORT_PRESETS,
    PARALLEL_OPTIONS,
    ConflictPolicy,
    DuckingMode,
    ExportQuality,
)
from ...core.ffmpeg_manager import FFmpegManager
from ...core.logging_setup import LOG_FILE_PATH
from ...core.models import MixConfig
from ..icons import render_svg_pixmap


class SettingsPage(QWidget):
    """Aba Configurações integrada para saída, paralelismo, attack/release, conflitos e FFmpeg."""

    settings_changed = Signal(object, str, bool)  # MixConfig, custom_ffmpeg_dir, recursive_scan

    def __init__(
        self,
        initial_cfg: MixConfig,
        custom_ffmpeg_dir: str,
        recursive_scan: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._cfg = initial_cfg
        self._sync_guard = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("settings", 18, COLOR_AMBER))
        title = QLabel("Configurações de Exportação, Desempenho e Áudio")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT};")
        hdr.addWidget(ico)
        hdr.addWidget(title)
        hdr.addStretch(1)
        lay.addLayout(hdr)

        # Grupo 1: Exportação e Paralelismo
        exp_group = QGroupBox("Qualidade de exportação e processamento paralelo")
        exp_grid = QGridLayout(exp_group)
        exp_grid.setSpacing(10)

        self.quality_combo = QComboBox()
        for preset in EXPORT_PRESETS.values():
            self.quality_combo.addItem(preset.label, preset.key.value)
        self.quality_combo.currentIndexChanged.connect(self._emit_all)

        self.parallel_combo = QComboBox()
        for label, val in PARALLEL_OPTIONS:
            self.parallel_combo.addItem(label, val)
        self.parallel_combo.currentIndexChanged.connect(self._emit_all)

        note_lbl = QLabel(
            "Nota: converter um arquivo originalmente comprimido (ex.: MP3) para WAV ou FLAC não restaura qualidade perdida."
        )
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")

        exp_grid.addWidget(QLabel("Formato de saída:"), 0, 0)
        exp_grid.addWidget(self.quality_combo, 0, 1)
        exp_grid.addWidget(QLabel("Processamento paralelo:"), 0, 2)
        exp_grid.addWidget(self.parallel_combo, 0, 3)
        exp_grid.addWidget(note_lbl, 1, 0, 1, 4)
        lay.addWidget(exp_group)

        # Grupo 2: DSP Avançado (Attack, Release, Ducking Mode)
        dsp_group = QGroupBox("Transições de ducking (Attack / Release)")
        dsp_grid = QGridLayout(dsp_group)
        dsp_grid.setSpacing(10)

        self.attack_spin = QSpinBox()
        self.attack_spin.setRange(10, 2000)
        self.attack_spin.setSingleStep(25)
        self.attack_spin.setSuffix(" ms")
        self.attack_spin.valueChanged.connect(self._emit_all)

        self.release_spin = QSpinBox()
        self.release_spin.setRange(50, 5000)
        self.release_spin.setSingleStep(50)
        self.release_spin.setSuffix(" ms")
        self.release_spin.valueChanged.connect(self._emit_all)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Envelope controlado (atenuação % exata — recomendado)", DuckingMode.ENVELOPE.value)
        self.mode_combo.addItem("Sidechain dinâmico (FFmpeg sidechaincompress)", DuckingMode.SIDECHAIN.value)
        self.mode_combo.currentIndexChanged.connect(self._emit_all)

        dsp_grid.addWidget(QLabel("Attack (descida):"), 0, 0)
        dsp_grid.addWidget(self.attack_spin, 0, 1)
        dsp_grid.addWidget(QLabel("Release (retorno):"), 0, 2)
        dsp_grid.addWidget(self.release_spin, 0, 3)
        dsp_grid.addWidget(QLabel("Método de ducking:"), 1, 0)
        dsp_grid.addWidget(self.mode_combo, 1, 1, 1, 3)
        lay.addWidget(dsp_group)

        # Grupo 3: Arquivos e Conflitos
        files_group = QGroupBox("Arquivos, subpastas e conflitos na pasta COM_VINHETA")
        files_grid = QGridLayout(files_group)
        files_grid.setSpacing(10)

        self.recursive_chk = QCheckBox("Incluir subpastas ao selecionar uma pasta de músicas")
        self.recursive_chk.toggled.connect(self._emit_all)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Perguntar antes de processar", ConflictPolicy.ASK.value)
        self.conflict_combo.addItem("Renomear automaticamente (ex.: faixa (2).mp3)", ConflictPolicy.RENAME.value)
        self.conflict_combo.addItem("Pular arquivos existentes", ConflictPolicy.SKIP.value)
        self.conflict_combo.addItem("Sobrescrever arquivos existentes", ConflictPolicy.OVERWRITE.value)
        self.conflict_combo.currentIndexChanged.connect(self._emit_all)

        files_grid.addWidget(self.recursive_chk, 0, 0, 1, 2)
        files_grid.addWidget(QLabel("Se o arquivo já existir:"), 1, 0)
        files_grid.addWidget(self.conflict_combo, 1, 1)
        lay.addWidget(files_group)

        # Grupo 4: FFmpeg / FFprobe e Logs
        ff_group = QGroupBox("Motor FFmpeg / FFprobe e diagnóstico")
        ff_lay = QVBoxLayout(ff_group)
        ff_lay.setSpacing(8)

        ff_row = QHBoxLayout()
        self.ffmpeg_edit = QLineEdit()
        self.ffmpeg_edit.setPlaceholderText("Automático (pasta do aplicativo ou PATH do Windows)")
        self.ffmpeg_edit.editingFinished.connect(self._emit_all)

        browse_btn = QPushButton("Procurar...")
        browse_btn.setObjectName("GhostBtn")
        browse_btn.clicked.connect(self._browse_ffmpeg)

        auto_btn = QPushButton("Automático")
        auto_btn.setObjectName("GhostBtn")
        auto_btn.clicked.connect(self._reset_ffmpeg_auto)

        logs_btn = QPushButton("Abrir logs")
        logs_btn.setObjectName("GhostBtn")
        logs_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE_PATH.parent))))

        ff_row.addWidget(self.ffmpeg_edit, 1)
        ff_row.addWidget(browse_btn)
        ff_row.addWidget(auto_btn)
        ff_row.addWidget(logs_btn)
        ff_lay.addLayout(ff_row)

        self.ff_status_lbl = QLabel("")
        self.ff_status_lbl.setWordWrap(True)
        ff_lay.addWidget(self.ff_status_lbl)
        lay.addWidget(ff_group)

        lay.addStretch(1)
        outer.addWidget(card, 1)

        self.apply_values(initial_cfg, custom_ffmpeg_dir, recursive_scan)

    def apply_values(self, cfg: MixConfig, custom_ffmpeg_dir: str, recursive_scan: bool) -> None:
        self._cfg = cfg
        self._sync_guard = True
        try:
            q_idx = self.quality_combo.findData(cfg.export_quality.value)
            if q_idx >= 0:
                self.quality_combo.setCurrentIndex(q_idx)
            p_idx = self.parallel_combo.findData(cfg.parallel_limit)
            if p_idx >= 0:
                self.parallel_combo.setCurrentIndex(p_idx)
            self.attack_spin.setValue(cfg.attack_ms)
            self.release_spin.setValue(cfg.release_ms)
            m_idx = self.mode_combo.findData(cfg.ducking_mode.value)
            if m_idx >= 0:
                self.mode_combo.setCurrentIndex(m_idx)
            c_idx = self.conflict_combo.findData(cfg.conflict_policy.value)
            if c_idx >= 0:
                self.conflict_combo.setCurrentIndex(c_idx)
            self.recursive_chk.setChecked(recursive_scan)
            self.ffmpeg_edit.setText(custom_ffmpeg_dir)
        finally:
            self._sync_guard = False
        self._refresh_ffmpeg_preview()

    def set_locked(self, locked: bool) -> None:
        for w in (
            self.quality_combo,
            self.parallel_combo,
            self.attack_spin,
            self.release_spin,
            self.mode_combo,
            self.recursive_chk,
            self.conflict_combo,
            self.ffmpeg_edit,
        ):
            w.setEnabled(not locked)

    def _browse_ffmpeg(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta contendo ffmpeg.exe e ffprobe.exe")
        if folder:
            self.ffmpeg_edit.setText(folder)
            self._emit_all()

    def _reset_ffmpeg_auto(self) -> None:
        self.ffmpeg_edit.setText("")
        self._emit_all()

    def _refresh_ffmpeg_preview(self) -> None:
        probe = FFmpegManager(self.ffmpeg_edit.text().strip())
        st = probe.detect()
        if st.available:
            self.ff_status_lbl.setText(f"FFmpeg ativo: {st.ffmpeg_path}")
            self.ff_status_lbl.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 11px;")
        else:
            self.ff_status_lbl.setText(st.error)
            self.ff_status_lbl.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 11px;")

    def _emit_all(self) -> None:
        if self._sync_guard:
            return
        self._cfg.export_quality = ExportQuality(self.quality_combo.currentData())
        self._cfg.parallel_limit = int(self.parallel_combo.currentData())
        self._cfg.attack_ms = self.attack_spin.value()
        self._cfg.release_ms = self.release_spin.value()
        self._cfg.ducking_mode = DuckingMode(self.mode_combo.currentData())
        self._cfg.conflict_policy = ConflictPolicy(self.conflict_combo.currentData())
        self._refresh_ffmpeg_preview()
        self.settings_changed.emit(self._cfg, self.ffmpeg_edit.text().strip(), self.recursive_chk.isChecked())
