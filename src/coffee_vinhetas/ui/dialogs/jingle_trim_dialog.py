"""Editor visual ampliado para recortar início e fim da vinheta."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.audio_processor import AudioProcessor
from ...core.constants import COLOR_AMBER, COLOR_GREEN, COLOR_TEXT, COLOR_TEXT_DIM, format_duration
from ...core.ffmpeg_manager import FFmpegManager
from ...core.models import AudioInfo
from ..icons import make_svg_icon, render_svg_pixmap
from ..theme import apply_windows_dark_titlebar
from ..widgets import WaveformWidget


class JingleTrimDialog(QDialog):
    """Permite recortar a vinheta visualmente com alças arrastáveis, detecção de silêncio e prévia."""

    def __init__(
        self,
        jingle_info: AudioInfo,
        ffmpeg_mgr: FFmpegManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Cortar Vinheta — {jingle_info.path.name}")
        self.setMinimumWidth(680)
        self._info = jingle_info
        self._ffmpeg_mgr = ffmpeg_mgr
        self._sync_guard = False
        self._dark_applied = False

        self.trim_start: float = jingle_info.effective_trim_start
        self.trim_end: float = jingle_info.effective_trim_end

        self._audio_out = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_out)
        self._player.positionChanged.connect(self._on_pos_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Cabeçalho
        hdr = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(render_svg_pixmap("scissors", 20, COLOR_AMBER))
        title = QLabel(f"Cortar Vinheta: {jingle_info.path.name}")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_TEXT};")
        self.dur_badge = QLabel("")
        self.dur_badge.setStyleSheet(
            "background-color: #2A1E15; color: #F5C384; border: 1px solid #6E4A2E; "
            "border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;"
        )
        hdr.addWidget(ico)
        hdr.addWidget(title, 1)
        hdr.addWidget(self.dur_badge)
        layout.addLayout(hdr)

        hint = QLabel(
            "Arraste as alças âmbar para definir onde a vinheta começa e termina. "
            "O arquivo original não é modificado; um micro-fade suave (20 ms) é aplicado nas bordas do corte."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM};")
        layout.addWidget(hint)

        # Waveform grande interativa
        self.waveform = WaveformWidget(interactive_trim=True)
        self.waveform.set_peaks(jingle_info.peaks)
        self.waveform.trim_changed.connect(self._on_waveform_trim_changed)
        self.waveform.seek_requested.connect(self._on_waveform_seek)
        layout.addWidget(self.waveform)

        # Controles numéricos + ferramentas rápidas
        ctrl_card = QFrame()
        ctrl_card.setObjectName("InnerCard")
        c_lay = QHBoxLayout(ctrl_card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(10)

        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, max(0.0, jingle_info.duration - 0.2))
        self.start_spin.setDecimals(2)
        self.start_spin.setSingleStep(0.10)
        self.start_spin.setSuffix(" s")
        self.start_spin.setFixedWidth(98)
        self.start_spin.valueChanged.connect(self._on_spins_changed)

        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0.2, max(0.2, jingle_info.duration))
        self.end_spin.setDecimals(2)
        self.end_spin.setSingleStep(0.10)
        self.end_spin.setSuffix(" s")
        self.end_spin.setFixedWidth(98)
        self.end_spin.valueChanged.connect(self._on_spins_changed)

        self.play_btn = QPushButton("Ouvir trecho")
        self.play_btn.setObjectName("PreviewBtn")
        self.play_btn.setIcon(make_svg_icon("play", 15, COLOR_AMBER))
        self.play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.play_btn.clicked.connect(self._toggle_play)

        auto_btn = QPushButton("Detectar silêncio")
        auto_btn.setObjectName("GhostBtn")
        auto_btn.setToolTip("Ajusta automaticamente início e fim aos trechos com áudio ativo da vinheta.")
        auto_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        auto_btn.clicked.connect(self._auto_detect_silence)

        reset_btn = QPushButton("Restaurar")
        reset_btn.setObjectName("GhostBtn")
        reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_btn.clicked.connect(self._reset_trim)

        c_lay.addWidget(QLabel("Início:"))
        c_lay.addWidget(self.start_spin)
        c_lay.addWidget(QLabel("Fim:"))
        c_lay.addWidget(self.end_spin)
        c_lay.addStretch(1)
        c_lay.addWidget(self.play_btn)
        c_lay.addWidget(auto_btn)
        c_lay.addWidget(reset_btn)
        layout.addWidget(ctrl_card)

        # Rodapé de ações
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.export_btn = QPushButton("Salvar vinheta cortada...")
        self.export_btn.setObjectName("GhostBtn")
        self.export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_btn.setToolTip("Exporta opcionalmente o trecho cortado como um novo arquivo de áudio.")
        self.export_btn.clicked.connect(self._export_trimmed)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)

        apply_btn = QPushButton("Aplicar corte")
        apply_btn.setObjectName("PrimaryGreenBtn")
        apply_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        apply_btn.clicked.connect(self.accept)
        apply_btn.setDefault(True)

        footer.addWidget(self.export_btn)
        footer.addStretch(1)
        footer.addWidget(cancel_btn)
        footer.addWidget(apply_btn)
        layout.addLayout(footer)

        self._sync_ui_from_values()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._dark_applied:
            self._dark_applied = True
            apply_windows_dark_titlebar(self)

    def _sync_ui_from_values(self) -> None:
        self._sync_guard = True
        try:
            self.start_spin.setValue(self.trim_start)
            self.end_spin.setValue(self.trim_end)
            dur = max(0.01, self._info.duration)
            self.waveform.set_trim_range(self.trim_start / dur, self.trim_end / dur)
            eff = max(0.0, self.trim_end - self.trim_start)
            self.dur_badge.setText(
                f"Trecho: {eff:.2f}s  ({format_duration(self.trim_start)} – {format_duration(self.trim_end)})"
            )
        finally:
            self._sync_guard = False

    def _on_waveform_trim_changed(self, s_frac: float, e_frac: float) -> None:
        if self._sync_guard:
            return
        self.trim_start = round(s_frac * self._info.duration, 2)
        self.trim_end = round(e_frac * self._info.duration, 2)
        if self.trim_end - self.trim_start < 0.2:
            self.trim_end = min(self._info.duration, self.trim_start + 0.2)
        self._sync_ui_from_values()

    def _on_spins_changed(self) -> None:
        if self._sync_guard:
            return
        s = self.start_spin.value()
        e = self.end_spin.value()
        if e - s < 0.2:
            if self.sender() is self.start_spin:
                e = min(self._info.duration, s + 0.2)
            else:
                s = max(0.0, e - 0.2)
        self.trim_start = round(s, 2)
        self.trim_end = round(e, 2)
        self._sync_ui_from_values()

    def _auto_detect_silence(self) -> None:
        act_s = max(0.0, self._info.active_start)
        act_e = min(self._info.duration, self._info.active_end)
        if act_e - act_s < 0.2:
            QMessageBox.information(
                self,
                "Detecção de silêncio",
                "Não foi encontrado silêncio relevante nas bordas para recortar automaticamente.",
            )
            return
        self.trim_start = round(act_s, 2)
        self.trim_end = round(act_e, 2)
        self._sync_ui_from_values()

    def _reset_trim(self) -> None:
        self.trim_start = 0.0
        self.trim_end = round(self._info.duration, 2)
        self._sync_ui_from_values()

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.stop()
            return
        if self._player.source() != QUrl.fromLocalFile(str(self._info.path)):
            self._player.setSource(QUrl.fromLocalFile(str(self._info.path)))
        self._audio_out.setVolume(0.95)
        self._player.setPosition(int(self.trim_start * 1000.0))
        self._player.play()

    def _on_waveform_seek(self, frac: float) -> None:
        pos_s = max(self.trim_start, min(self.trim_end - 0.05, frac * self._info.duration))
        if self._player.source() != QUrl.fromLocalFile(str(self._info.path)):
            self._player.setSource(QUrl.fromLocalFile(str(self._info.path)))
        self._player.setPosition(int(pos_s * 1000.0))
        self.waveform.set_progress(pos_s / max(0.01, self._info.duration))

    def _on_pos_changed(self, pos_ms: int) -> None:
        pos_s = pos_ms / 1000.0
        self.waveform.set_progress(pos_s / max(0.01, self._info.duration))
        if pos_s >= self.trim_end:
            self._player.stop()

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("Parar" if playing else "Ouvir trecho")
        self.play_btn.setIcon(make_svg_icon("stop" if playing else "play", 15, COLOR_AMBER))
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.waveform.set_progress(0.0)

    def _export_trimmed(self) -> None:
        default_name = f"{self._info.path.stem}_cortada{self._info.path.suffix or '.mp3'}"
        default_path = str(self._info.path.parent / default_name)
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar vinheta cortada",
            default_path,
            "MP3 (*.mp3);;WAV (*.wav);;FLAC (*.flac);;M4A (*.m4a)",
        )
        if not dest:
            return
        temp_info = replace(self._info, trim_start=self.trim_start, trim_end=self.trim_end)
        ok, msg = AudioProcessor(self._ffmpeg_mgr).export_trimmed_jingle(temp_info, Path(dest))
        if ok:
            QMessageBox.information(self, "Vinheta exportada", f"Vinheta cortada salva em:\n{msg}")
        else:
            QMessageBox.warning(self, "Falha ao exportar", f"Não foi possível salvar a vinheta cortada:\n{msg}")

    def closeEvent(self, event) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        super().closeEvent(event)

    def reject(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        super().reject()

    def accept(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        super().accept()
