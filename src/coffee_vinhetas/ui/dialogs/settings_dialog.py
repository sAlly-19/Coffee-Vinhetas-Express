"""Diálogo de configurações avançadas."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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

from ...core.constants import COLOR_ERROR, COLOR_GREEN, ConflictPolicy, DuckingMode
from ...core.ffmpeg_manager import FFmpegManager
from ...core.logging_setup import LOG_FILE_PATH
from ...core.models import MixConfig
from ..theme import apply_windows_dark_titlebar


class SettingsDialog(QDialog):
    """Janela de configurações avançadas (Attack, Release, modo de ducking, FFmpeg e conflitos)."""

    def __init__(
        self,
        cfg: MixConfig,
        custom_ffmpeg_dir: str,
        recursive_scan: bool,
        ffmpeg_mgr: FFmpegManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurações avançadas")
        self.setMinimumWidth(520)
        self._ffmpeg_mgr = ffmpeg_mgr
        self._dark_applied = False

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        dsp_group = QGroupBox("Transições e motor de ducking")
        dsp_form = QGridLayout(dsp_group)
        dsp_form.setSpacing(10)

        self.attack_spin = QSpinBox()
        self.attack_spin.setRange(10, 2000)
        self.attack_spin.setSingleStep(25)
        self.attack_spin.setSuffix(" ms")
        self.attack_spin.setValue(cfg.attack_ms)
        self.attack_spin.setToolTip("Tempo de descida do volume da música ao iniciar a vinheta (padrão: 150 ms).")

        self.release_spin = QSpinBox()
        self.release_spin.setRange(50, 5000)
        self.release_spin.setSingleStep(50)
        self.release_spin.setSuffix(" ms")
        self.release_spin.setValue(cfg.release_ms)
        self.release_spin.setToolTip("Tempo de retorno gradual do volume da música após a vinheta (padrão: 600 ms).")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Envelope controlado (atenuação % exata — recomendado)", DuckingMode.ENVELOPE.value)
        self.mode_combo.addItem("Sidechain dinâmico (FFmpeg sidechaincompress)", DuckingMode.SIDECHAIN.value)
        idx_mode = self.mode_combo.findData(cfg.ducking_mode.value)
        if idx_mode >= 0:
            self.mode_combo.setCurrentIndex(idx_mode)

        dsp_form.addWidget(QLabel("Attack (descida):"), 0, 0)
        dsp_form.addWidget(self.attack_spin, 0, 1)
        dsp_form.addWidget(QLabel("Release (retorno):"), 1, 0)
        dsp_form.addWidget(self.release_spin, 1, 1)
        dsp_form.addWidget(QLabel("Método de ducking:"), 2, 0)
        dsp_form.addWidget(self.mode_combo, 2, 1)
        layout.addWidget(dsp_group)

        files_group = QGroupBox("Varredura e arquivos de saída")
        files_layout = QGridLayout(files_group)
        files_layout.setSpacing(10)

        self.recursive_check = QCheckBox("Buscar músicas em subpastas automaticamente")
        self.recursive_check.setChecked(recursive_scan)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItem("Perguntar antes de processar", ConflictPolicy.ASK.value)
        self.conflict_combo.addItem("Renomear automaticamente (ex: faixa (2).mp3)", ConflictPolicy.RENAME.value)
        self.conflict_combo.addItem("Pular arquivos que já existem na saída", ConflictPolicy.SKIP.value)
        self.conflict_combo.addItem("Sobrescrever arquivos existentes na saída", ConflictPolicy.OVERWRITE.value)
        idx_pol = self.conflict_combo.findData(cfg.conflict_policy.value)
        if idx_pol >= 0:
            self.conflict_combo.setCurrentIndex(idx_pol)

        files_layout.addWidget(self.recursive_check, 0, 0, 1, 2)
        files_layout.addWidget(QLabel("Se já existir na saída:"), 1, 0)
        files_layout.addWidget(self.conflict_combo, 1, 1)
        layout.addWidget(files_group)

        ff_group = QGroupBox("Localização do FFmpeg / FFprobe")
        ff_layout = QVBoxLayout(ff_group)
        ff_layout.setSpacing(8)

        row_ff = QHBoxLayout()
        self.ffmpeg_edit = QLineEdit(custom_ffmpeg_dir)
        self.ffmpeg_edit.setPlaceholderText("Automático (pasta do aplicativo ou PATH do Windows)")
        browse_btn = QPushButton("Procurar...")
        browse_btn.clicked.connect(self._browse_ffmpeg)
        clear_btn = QPushButton("Automático")
        clear_btn.clicked.connect(lambda: self.ffmpeg_edit.setText(""))
        row_ff.addWidget(self.ffmpeg_edit, 1)
        row_ff.addWidget(browse_btn)
        row_ff.addWidget(clear_btn)
        ff_layout.addLayout(row_ff)

        self.ff_status_label = QLabel()
        self.ff_status_label.setWordWrap(True)
        self._refresh_ffmpeg_preview()
        self.ffmpeg_edit.textChanged.connect(lambda _: self._refresh_ffmpeg_preview())
        ff_layout.addWidget(self.ff_status_label)
        layout.addWidget(ff_group)

        bottom_row = QHBoxLayout()
        logs_btn = QPushButton("Abrir pasta de logs")
        logs_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE_PATH.parent))))
        bottom_row.addWidget(logs_btn)
        bottom_row.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Salvar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom_row.addWidget(buttons)
        layout.addLayout(bottom_row)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_applied:
            self._dark_applied = True
            apply_windows_dark_titlebar(self)

    def _browse_ffmpeg(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta contendo ffmpeg.exe e ffprobe.exe")
        if folder:
            self.ffmpeg_edit.setText(folder)

    def _refresh_ffmpeg_preview(self) -> None:
        probe_mgr = FFmpegManager(self.ffmpeg_edit.text().strip())
        st = probe_mgr.detect()
        if st.available:
            self.ff_status_label.setText(f"Detectado: {st.ffmpeg_path}")
            self.ff_status_label.setStyleSheet(f"color: {COLOR_GREEN}; font-size: 11px;")
        else:
            self.ff_status_label.setText(st.error)
            self.ff_status_label.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 11px;")
