"""Janela principal frameless com sidebar de 5 abas e orquestração completa."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import (
    APP_AUTHOR,
    APP_NAME,
    EXPORT_PRESETS,
    LOGGER,
    OUTPUT_DIR_NAME,
    SUPPORTED_EXTENSIONS,
    AudioInfo,
    AudioProcessor,
    BatchSummary,
    ConflictPolicy,
    FFmpegManager,
    HistoryEntry,
    HistoryManager,
    MixConfig,
    SettingsManager,
    TrackTask,
    format_duration,
    is_inside_output_dir,
    is_supported_audio,
    resolve_concurrency,
)
from ..workers import BatchWorker, JingleAnalyzeWorker, MusicScanWorker, PreviewWorker
from .dialogs import BatchDetailsDialog, FFmpegMissingDialog, JingleTrimDialog
from .icons import make_svg_icon
from .pages import AboutPage, HistoryPage, ProcessPage, SettingsPage
from .sections import ExecutionCard, HeaderBar, JingleCard, MixingCard, MusicCard, SidebarNav


class MainWindow(QMainWindow):
    """Janela principal frameless que coordena a sidebar, páginas, players e workers."""

    PAGE_HOME = 0
    PAGE_PROCESS = 1
    PAGE_HISTORY = 2
    PAGE_SETTINGS = 3
    PAGE_ABOUT = 4

    def __init__(self, settings_mgr: SettingsManager) -> None:
        super().__init__()
        self.settings_mgr = settings_mgr
        self.history_mgr = HistoryManager()
        self.ffmpeg_mgr = FFmpegManager(settings_mgr.custom_ffmpeg_dir)
        self.mix_config = settings_mgr.load_mix_config()

        self.jingle_info: Optional[AudioInfo] = None
        self.music_items: list[AudioInfo] = []
        self.selected_music_folder: Optional[Path] = None
        self.ignored_count: int = 0
        self._recursive_scan: bool = settings_mgr.recursive_scan

        self._jingle_worker: Optional[JingleAnalyzeWorker] = None
        self._scan_worker: Optional[MusicScanWorker] = None
        self._preview_worker: Optional[PreviewWorker] = None
        self._batch_worker: Optional[BatchWorker] = None

        self._last_summary: Optional[BatchSummary] = None
        self._preview_temp_file: Optional[Path] = None
        self._preview_desc: str = ""

        # Players independentes (vinheta e prévia)
        self._jingle_audio = QAudioOutput(self)
        self._jingle_player = QMediaPlayer(self)
        self._jingle_player.setAudioOutput(self._jingle_audio)
        self._jingle_player.positionChanged.connect(self._on_jingle_pos_changed)
        self._jingle_player.playbackStateChanged.connect(self._on_jingle_state_changed)

        self._preview_audio = QAudioOutput(self)
        self._preview_player = QMediaPlayer(self)
        self._preview_player.setAudioOutput(self._preview_audio)
        self._preview_player.playbackStateChanged.connect(self._on_preview_state_changed)
        self._preview_player.errorOccurred.connect(self._on_preview_error)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_svg_icon("logo", 32))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(940, 660)
        self.resize(1040, 730)

        saved_geom = self.settings_mgr.load_window_geometry()
        if saved_geom is not None:
            self.restoreGeometry(saved_geom)

        self._build_ui()
        self._connect_signals()
        self._refresh_ffmpeg_status(show_dialog_if_missing=False)
        self._refresh_history()
        self._sync_mixing_feedback()
        self._restore_saved_paths()
        self._update_readiness_state()

    # ------------------------------------------------------------------
    # Montagem da moldura frameless, sidebar e 5 páginas
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        shell = QFrame()
        shell.setObjectName("WindowShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.sidebar = SidebarNav()

        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header_bar = HeaderBar()
        right_layout.addWidget(self.header_bar)

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(14, 4, 14, 10)

        # Página 0: Início (idêntica à referência visual)
        home_page = QWidget()
        home_lay = QVBoxLayout(home_page)
        home_lay.setContentsMargins(0, 0, 0, 0)
        home_lay.setSpacing(10)

        self.jingle_card = JingleCard()
        self.music_card = MusicCard()
        self.mixing_card = MixingCard(self.mix_config)
        self.execution_card = ExecutionCard()

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)
        top_row.addWidget(self.jingle_card, 1)
        top_row.addWidget(self.music_card, 1)

        home_lay.addLayout(top_row)
        home_lay.addWidget(self.mixing_card)
        home_lay.addWidget(self.execution_card)

        # Páginas 1..4: Processo, Histórico, Configurações, Sobre
        self.process_page = ProcessPage(recursive_initial=self._recursive_scan)
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(
            initial_cfg=self.mix_config,
            custom_ffmpeg_dir=self.settings_mgr.custom_ffmpeg_dir,
            recursive_scan=self._recursive_scan,
        )
        self.about_page = AboutPage()

        self.stack.addWidget(home_page)
        self.stack.addWidget(self.process_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.about_page)

        right_layout.addWidget(self.stack, 1)

        # Rodapé discreto com assinatura e alça de redimensionamento
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(16, 0, 4, 3)
        sig_lbl = QLabel(APP_AUTHOR)
        sig_lbl.setStyleSheet("font-size: 10px; color: #7E6B5C; font-weight: 600;")
        grip_row.addWidget(sig_lbl)
        grip_row.addStretch(1)
        grip = QSizeGrip(self)
        grip.setFixedSize(14, 14)
        grip_row.addWidget(grip)
        right_layout.addLayout(grip_row)

        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(right_col, 1)

        self.setCentralWidget(shell)

    def _connect_signals(self) -> None:
        self.sidebar.page_selected.connect(self.navigate_to)

        self.header_bar.minimize_requested.connect(self.showMinimized)
        self.header_bar.maximize_requested.connect(self._toggle_maximize)
        self.header_bar.close_requested.connect(self.close)
        self.header_bar.ffmpeg_clicked.connect(self._on_ffmpeg_badge_clicked)

        # Cartão 1 (Vinheta)
        self.jingle_card.pick_requested.connect(self._pick_jingle_file)
        self.jingle_card.files_dropped.connect(self._on_jingle_dropped)
        self.jingle_card.remove_requested.connect(self._clear_jingle)
        self.jingle_card.trim_requested.connect(self._open_jingle_trim_dialog)
        self.jingle_card.play_toggled.connect(self._toggle_jingle_playback)
        self.jingle_card.seek_requested.connect(self._seek_jingle)

        # Cartão 2 (Músicas) + Página Processo
        self.music_card.select_folder_requested.connect(self._pick_music_folder)
        self.music_card.files_dropped.connect(self._on_music_dropped)
        self.music_card.manage_queue_requested.connect(lambda: self.navigate_to(self.PAGE_PROCESS))

        self.process_page.add_files_requested.connect(self._pick_music_files)
        self.process_page.select_folder_requested.connect(self._pick_music_folder)
        self.process_page.clear_requested.connect(self._clear_music_queue)
        self.process_page.recursive_toggled.connect(self._on_recursive_toggled)
        self.process_page.item_removed.connect(self._remove_music_item)
        self.process_page.back_to_home_requested.connect(lambda: self.navigate_to(self.PAGE_HOME))

        # Mixagem + Configurações
        self.mixing_card.config_changed.connect(self._on_mix_config_changed)
        self.settings_page.settings_changed.connect(self._on_settings_page_changed)

        # Histórico + Sobre
        self.history_page.details_requested.connect(self._open_history_details)
        self.history_page.clear_history_requested.connect(self._clear_history)
        self.about_page.configure_ffmpeg_requested.connect(lambda: self.navigate_to(self.PAGE_SETTINGS))

        # Execução / Prévia
        self.execution_card.preview_clicked.connect(self._on_preview_clicked)
        self.execution_card.process_clicked.connect(self._on_process_clicked)
        self.execution_card.open_output_clicked.connect(self._open_output_folder)
        self.execution_card.details_clicked.connect(self._open_batch_details)

    @Slot(int)
    def navigate_to(self, page_index: int) -> None:
        self.stack.setCurrentIndex(page_index)
        self.sidebar.set_active_index(page_index)

    @Slot()
    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ------------------------------------------------------------------
    # FFmpeg, Histórico e Restauração Inicial
    # ------------------------------------------------------------------

    def _refresh_ffmpeg_status(self, show_dialog_if_missing: bool = False) -> None:
        st = self.ffmpeg_mgr.detect(self.settings_mgr.custom_ffmpeg_dir)
        self.header_bar.set_ffmpeg_available(st.available)
        self.about_page.update_ffmpeg_status(st)
        if not st.available and show_dialog_if_missing:
            dlg = FFmpegMissingDialog(st.error, self)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_dir:
                self.settings_mgr.custom_ffmpeg_dir = dlg.selected_dir
                self.settings_page.apply_values(
                    self.mix_config, self.settings_mgr.custom_ffmpeg_dir, self._recursive_scan
                )
                self._refresh_ffmpeg_status(show_dialog_if_missing=False)
        self._update_readiness_state()

    def _refresh_history(self) -> None:
        self.history_page.set_entries(self.history_mgr.load_entries())

    def _restore_saved_paths(self) -> None:
        last_jingle = self.settings_mgr.last_jingle_path
        if last_jingle:
            jp = Path(last_jingle)
            if is_supported_audio(jp):
                self._load_jingle(jp)

        last_folder = self.settings_mgr.last_music_folder
        if last_folder:
            fp = Path(last_folder)
            if fp.is_dir() and not is_inside_output_dir(fp):
                self.selected_music_folder = fp
                self._start_music_scan([fp], replace=True)

    # ------------------------------------------------------------------
    # Vinheta
    # ------------------------------------------------------------------

    @Slot()
    def _pick_jingle_file(self) -> None:
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        start_dir = str(Path(self.settings_mgr.last_jingle_path).parent) if self.settings_mgr.last_jingle_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar vinheta de áudio",
            start_dir,
            f"Arquivos de áudio ({exts});;Todos os arquivos (*.*)",
        )
        if file_path:
            self._load_jingle(Path(file_path))

    @Slot(list)
    def _on_jingle_dropped(self, paths: list[Path]) -> None:
        for p in paths:
            if is_supported_audio(p):
                self._load_jingle(p)
                return
        QMessageBox.warning(
            self,
            "Formato não suportado",
            f"Selecione um arquivo de áudio válido ({', '.join(SUPPORTED_EXTENSIONS)}).",
        )

    def _load_jingle(self, path: Path) -> None:
        if not self.ffmpeg_mgr.status.available:
            QMessageBox.warning(self, "FFmpeg necessário", "Configure o FFmpeg/FFprobe antes de carregar a vinheta.")
            return

        self._stop_jingle_playback()
        self.jingle_card.show_loading(path)

        if self._jingle_worker and self._jingle_worker.isRunning():
            self._jingle_worker.requestInterruption()
            self._jingle_worker.wait(1500)

        self._jingle_worker = JingleAnalyzeWorker(self.ffmpeg_mgr, path, self)
        self._jingle_worker.finished_analysis.connect(self._on_jingle_analyzed)
        self._jingle_worker.start()

    @Slot(object)
    def _on_jingle_analyzed(self, info: AudioInfo) -> None:
        if not info.valid:
            self.jingle_info = None
            self.jingle_card.show_empty()
            QMessageBox.warning(self, "Vinheta inválida", f"Não foi possível carregar '{info.path.name}':\n{info.error}")
            self._sync_mixing_feedback()
            self._update_readiness_state()
            return

        saved_t0, saved_t1 = self.settings_mgr.load_jingle_trim(str(info.path))
        if saved_t1 > saved_t0 and saved_t1 <= info.duration + 0.05:
            info.trim_start = max(0.0, saved_t0)
            info.trim_end = min(info.duration, saved_t1)

        self.jingle_info = info
        self.settings_mgr.last_jingle_path = str(info.path)
        self.jingle_card.show_jingle(info)
        self._sync_mixing_feedback()
        self._update_readiness_state()

    @Slot()
    def _open_jingle_trim_dialog(self) -> None:
        if not self.jingle_info or not self.jingle_info.valid:
            return
        self._stop_jingle_playback()
        dlg = JingleTrimDialog(self.jingle_info, self.ffmpeg_mgr, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.jingle_info.trim_start = dlg.trim_start
            self.jingle_info.trim_end = dlg.trim_end
            self.settings_mgr.save_jingle_trim(
                str(self.jingle_info.path), dlg.trim_start, dlg.trim_end
            )
            self.jingle_card.show_jingle(self.jingle_info)
            self._sync_mixing_feedback()
            self._update_readiness_state()

    @Slot()
    def _clear_jingle(self) -> None:
        self._stop_jingle_playback()
        self.jingle_info = None
        self.settings_mgr.last_jingle_path = ""
        self.settings_mgr.save_jingle_trim("", 0.0, 0.0)
        self.jingle_card.show_empty()
        self._sync_mixing_feedback()
        self._update_readiness_state()

    @Slot()
    def _toggle_jingle_playback(self) -> None:
        if not self.jingle_info:
            return
        if self._jingle_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._jingle_player.pause()
            return
        if self._jingle_player.source() != QUrl.fromLocalFile(str(self.jingle_info.path)):
            self._jingle_player.setSource(QUrl.fromLocalFile(str(self.jingle_info.path)))
        start_ms = int(self.jingle_info.effective_trim_start * 1000.0)
        end_ms = int(self.jingle_info.effective_trim_end * 1000.0)
        cur_ms = self._jingle_player.position()
        if cur_ms < start_ms or cur_ms >= max(start_ms + 50, end_ms - 50):
            self._jingle_player.setPosition(start_ms)
        self._jingle_audio.setVolume(0.9)
        self._jingle_player.play()

    def _stop_jingle_playback(self) -> None:
        self._jingle_player.stop()
        self._jingle_player.setSource(QUrl())
        if self.jingle_info:
            self.jingle_card.set_playback_state(
                False,
                self.jingle_info.effective_trim_start,
                self.jingle_info.duration,
                self.jingle_info.effective_trim_start,
                self.jingle_info.effective_duration,
            )

    @Slot(float)
    def _seek_jingle(self, frac: float) -> None:
        if not self.jingle_info or self.jingle_info.duration <= 0:
            return
        if self._jingle_player.source() != QUrl.fromLocalFile(str(self.jingle_info.path)):
            self._jingle_player.setSource(QUrl.fromLocalFile(str(self.jingle_info.path)))
        target_s = frac * self.jingle_info.duration
        target_s = max(self.jingle_info.effective_trim_start, min(self.jingle_info.effective_trim_end, target_s))
        self._jingle_player.setPosition(int(target_s * 1000.0))
        playing = self._jingle_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.jingle_card.set_playback_state(
            playing,
            target_s,
            self.jingle_info.duration,
            self.jingle_info.effective_trim_start,
            self.jingle_info.effective_duration,
        )

    @Slot(int)
    def _on_jingle_pos_changed(self, pos_ms: int) -> None:
        if not self.jingle_info or self.jingle_info.duration <= 0:
            return
        pos_s = pos_ms / 1000.0
        if self.jingle_info.is_trimmed and pos_s >= self.jingle_info.effective_trim_end:
            self._jingle_player.stop()
            return
        playing = self._jingle_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.jingle_card.set_playback_state(
            playing,
            pos_s,
            self.jingle_info.duration,
            self.jingle_info.effective_trim_start,
            self.jingle_info.effective_duration,
        )

    @Slot(QMediaPlayer.PlaybackState)
    def _on_jingle_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if not self.jingle_info:
            self.jingle_card.set_playback_state(playing, 0.0, 0.0)
            return
        pos = (
            self.jingle_info.effective_trim_start
            if state == QMediaPlayer.PlaybackState.StoppedState
            else (self._jingle_player.position() / 1000.0)
        )
        self.jingle_card.set_playback_state(
            playing,
            pos,
            self.jingle_info.duration,
            self.jingle_info.effective_trim_start,
            self.jingle_info.effective_duration,
        )

    # ------------------------------------------------------------------
    # Fila de músicas (Cartão 2 + Aba Processo)
    # ------------------------------------------------------------------

    @Slot()
    def _pick_music_folder(self) -> None:
        start_dir = self.settings_mgr.last_music_folder or ""
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta com as músicas", start_dir)
        if not folder:
            return
        fp = Path(folder)
        if is_inside_output_dir(fp):
            QMessageBox.information(
                self,
                "Pasta de saída",
                f"A pasta '{OUTPUT_DIR_NAME}' contém arquivos já processados e não é incluída como origem.",
            )
            return
        self.selected_music_folder = fp
        self.settings_mgr.last_music_folder = str(fp)
        self._start_music_scan([fp], replace=True)

    @Slot()
    def _pick_music_files(self) -> None:
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        start_dir = self.settings_mgr.last_music_folder or ""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar arquivos de áudio",
            start_dir,
            f"Arquivos de áudio ({exts});;Todos os arquivos (*.*)",
        )
        if files:
            self._start_music_scan([Path(f) for f in files], replace=False)

    @Slot(list)
    def _on_music_dropped(self, paths: list[Path]) -> None:
        if len(paths) == 1 and paths[0].is_dir() and not self.music_items:
            if not is_inside_output_dir(paths[0]):
                self.selected_music_folder = paths[0]
                self.settings_mgr.last_music_folder = str(paths[0])
                self._start_music_scan(paths, replace=True)
                return
        self._start_music_scan(paths, replace=False)

    @Slot(bool)
    def _on_recursive_toggled(self, checked: bool) -> None:
        self._recursive_scan = checked
        self.settings_mgr.recursive_scan = checked
        self.settings_page.apply_values(self.mix_config, self.settings_mgr.custom_ffmpeg_dir, checked)
        if self.selected_music_folder and self.selected_music_folder.is_dir():
            self._start_music_scan([self.selected_music_folder], replace=True)

    @Slot()
    def _clear_music_queue(self) -> None:
        self.music_items.clear()
        self.selected_music_folder = None
        self.ignored_count = 0
        self._refresh_music_ui()

    @Slot(object)
    def _remove_music_item(self, path: Path) -> None:
        self.music_items = [m for m in self.music_items if m.path != path]
        self._refresh_music_ui()

    def _start_music_scan(self, paths: list[Path], replace: bool) -> None:
        if replace:
            self.music_items.clear()
            self.ignored_count = 0
            self.music_card.update_summary([], 0, self.selected_music_folder, None)
            self.process_page.update_queue([], 0, None)

        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.requestInterruption()
            self._scan_worker.wait(1500)

        self.music_card.set_scanning()
        existing = {item.path.resolve() for item in self.music_items}

        self._scan_worker = MusicScanWorker(
            self.ffmpeg_mgr, paths, self._recursive_scan, existing, self
        )
        self._scan_worker.scan_finished.connect(self._on_music_scanned)
        self._scan_worker.start()

    @Slot(list, int, list)
    def _on_music_scanned(self, new_infos: list[AudioInfo], ignored: int, warnings: list[str]) -> None:
        self.ignored_count += ignored
        self.music_items.extend(new_infos)
        self._refresh_music_ui()
        if warnings:
            LOGGER.warning("Arquivos ignorados na varredura: %s", "; ".join(warnings[:10]))

    def _resolve_output_dir(self) -> Optional[Path]:
        if self.selected_music_folder and self.selected_music_folder.is_dir():
            return self.selected_music_folder / OUTPUT_DIR_NAME
        if not self.music_items:
            return None
        parents = [str(m.path.parent) for m in self.music_items]
        try:
            common = Path(os.path.commonpath(parents))
        except ValueError:
            common = self.music_items[0].path.parent
        return common / OUTPUT_DIR_NAME

    def _refresh_music_ui(self) -> None:
        out_dir = self._resolve_output_dir()
        self.music_card.update_summary(self.music_items, self.ignored_count, self.selected_music_folder, out_dir)
        self.process_page.update_queue(self.music_items, self.ignored_count, out_dir)
        self._sync_mixing_feedback()
        self._update_readiness_state()

    # ------------------------------------------------------------------
    # Mixagem, Configurações e Validação
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_mix_config_changed(self, cfg: MixConfig) -> None:
        self.mix_config = cfg
        self.settings_mgr.save_mix_config(cfg)
        self.settings_page.apply_values(cfg, self.settings_mgr.custom_ffmpeg_dir, self._recursive_scan)
        self._sync_mixing_feedback()
        self._update_readiness_state()

    @Slot(object, str, bool)
    def _on_settings_page_changed(self, cfg: MixConfig, custom_ffmpeg_dir: str, recursive_scan: bool) -> None:
        self.mix_config = cfg
        self.settings_mgr.save_mix_config(cfg)
        self.mixing_card.apply_config(cfg)

        if custom_ffmpeg_dir != self.settings_mgr.custom_ffmpeg_dir:
            self.settings_mgr.custom_ffmpeg_dir = custom_ffmpeg_dir
            self._refresh_ffmpeg_status(show_dialog_if_missing=False)

        if recursive_scan != self._recursive_scan:
            self._recursive_scan = recursive_scan
            self.settings_mgr.recursive_scan = recursive_scan
            self.process_page.recursive_chk.setChecked(recursive_scan)
            if self.selected_music_folder and self.selected_music_folder.is_dir():
                self._start_music_scan([self.selected_music_folder], replace=True)

        self._sync_mixing_feedback()
        self._update_readiness_state()

    def _has_repeat_conflict(self) -> bool:
        if not self.mix_config.repeat_enabled or not self.jingle_info:
            return False
        return (self.mix_config.repeat_interval_min * 60.0) <= self.jingle_info.effective_duration

    def _sync_mixing_feedback(self) -> None:
        j_dur = self.jingle_info.effective_duration if self.jingle_info else 12.0
        self.mixing_card.update_curve(j_dur)

        warnings: list[str] = []
        if self._has_repeat_conflict():
            warnings.append(
                f"Conflito: o intervalo de repetição ({self.mix_config.repeat_interval_min} min) é menor ou igual "
                f"à duração da vinheta ({format_duration(j_dur)})."
            )

        if self.jingle_info and self.music_items:
            eff_dur = self.jingle_info.effective_duration
            too_short = [
                m
                for m in self.music_items
                if m.duration > 0
                and (
                    m.duration < eff_dur
                    or self.mix_config.entry_time_sec + eff_dur > m.duration + 0.05
                )
            ]
            if too_short:
                warnings.append(
                    f"Aviso: {len(too_short)} faixa(s) é(são) menor(es) que entrada + vinheta e será(ão) ignorada(s)."
                )

        self.mixing_card.set_warning("  ".join(warnings))

        workers, _t_proc = resolve_concurrency(self.mix_config.parallel_limit)
        preset = EXPORT_PRESETS[self.mix_config.export_quality]
        mode_txt = "Auto" if self.mix_config.parallel_limit == 0 else "Manual"
        self.execution_card.set_concurrency_info(
            f"Paralelo ({mode_txt}): {workers} faixa(s) • {preset.label.split(' — ')[0]}"
        )

    def _update_readiness_state(self) -> None:
        running = self._batch_worker is not None and self._batch_worker.isRunning()
        reasons: list[str] = []
        if not self.ffmpeg_mgr.status.available:
            reasons.append("FFmpeg/FFprobe não encontrados")
        if not self.jingle_info or not self.jingle_info.valid:
            reasons.append("selecione uma vinheta válida")
        if not self.music_items:
            reasons.append("adicione músicas ou uma pasta")
        if self._has_repeat_conflict():
            reasons.append("ajuste o intervalo de repetição")

        can_run = len(reasons) == 0
        can_preview = (
            self.ffmpeg_mgr.status.available
            and self.jingle_info is not None
            and self.jingle_info.valid
            and len(self.music_items) > 0
            and not self._has_repeat_conflict()
        )
        self.execution_card.set_readiness(can_run, can_preview, running, reasons)

    # ------------------------------------------------------------------
    # Prévia real
    # ------------------------------------------------------------------

    @Slot()
    def _on_preview_clicked(self) -> None:
        if self._preview_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._stop_preview_playback()
            return

        if self._preview_worker and self._preview_worker.isRunning():
            self._preview_worker.cancel()
            self._preview_worker.wait(1500)
            self.execution_card.reset_preview_button()
            return

        if not self.jingle_info or not self.music_items:
            return

        eff_dur = self.jingle_info.effective_duration
        candidate = next(
            (
                m
                for m in self.music_items
                if m.duration <= 0
                or (self.mix_config.entry_time_sec + eff_dur <= m.duration + 0.05)
            ),
            self.music_items[0],
        )

        self._stop_preview_playback()
        self.execution_card.set_preview_generating(candidate.path.name)

        self._preview_worker = PreviewWorker(self.ffmpeg_mgr, candidate, self.jingle_info, self.mix_config, self)
        self._preview_worker.preview_ready.connect(self._on_preview_ready)
        self._preview_worker.preview_failed.connect(self._on_preview_failed)
        self._preview_worker.start()

    @Slot(str, str)
    def _on_preview_ready(self, temp_path: str, desc: str) -> None:
        self._cleanup_preview_file()
        self._preview_temp_file = Path(temp_path)
        self._preview_desc = desc
        self._preview_audio.setVolume(0.95)
        self._preview_player.setSource(QUrl.fromLocalFile(temp_path))
        self._preview_player.play()
        self.execution_card.set_preview_playing(desc)

    @Slot(str)
    def _on_preview_failed(self, err: str) -> None:
        self.execution_card.reset_preview_button()
        self._update_readiness_state()
        QMessageBox.warning(self, "Prévia indisponível", err)

    def _stop_preview_playback(self) -> None:
        self._preview_player.stop()
        self._preview_player.setSource(QUrl())
        self._cleanup_preview_file()
        self.execution_card.reset_preview_button()

    def _cleanup_preview_file(self) -> None:
        if self._preview_temp_file is not None:
            AudioProcessor.safe_unlink(self._preview_temp_file)
            self._preview_temp_file = None

    @Slot(QMediaPlayer.PlaybackState)
    def _on_preview_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.execution_card.set_preview_playing(self._preview_desc)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._preview_player.setSource(QUrl())
            self._cleanup_preview_file()
            self.execution_card.reset_preview_button()

    @Slot(QMediaPlayer.Error, str)
    def _on_preview_error(self, _err: QMediaPlayer.Error, err_str: str) -> None:
        self._stop_preview_playback()
        QMessageBox.warning(self, "Erro de reprodução", f"Não foi possível reproduzir a prévia: {err_str}")

    # ------------------------------------------------------------------
    # Lote paralelo e cancelamento
    # ------------------------------------------------------------------

    @Slot()
    def _on_process_clicked(self) -> None:
        if self._batch_worker and self._batch_worker.isRunning():
            self.execution_card.set_cancelling()
            self._batch_worker.request_cancel()
            return

        if not self.jingle_info or not self.music_items or not self.ffmpeg_mgr.status.available:
            return

        out_dir = self._resolve_output_dir()
        if out_dir is None:
            return

        tasks, skipped_existing = self._prepare_batch_tasks(out_dir)
        if tasks is None:
            return
        if not tasks:
            QMessageBox.information(
                self,
                "Nenhum arquivo para processar",
                f"Todos os {skipped_existing} arquivo(s) já existem na pasta de destino e foram pulados.",
            )
            return

        self._stop_jingle_playback()
        self._stop_preview_playback()
        self._set_inputs_locked(True)
        self.execution_card.start_batch_view(len(tasks))

        self._batch_worker = BatchWorker(
            ffmpeg_mgr=self.ffmpeg_mgr,
            tasks=tasks,
            jingle_info=self.jingle_info,
            cfg=self.mix_config,
            output_dir=out_dir,
            parent=self,
        )
        self._batch_worker.progress_updated.connect(self.execution_card.update_batch_progress)
        self._batch_worker.batch_completed.connect(self._on_batch_completed)
        self._batch_worker.start()
        self._update_readiness_state()

    def _prepare_batch_tasks(self, out_dir: Path) -> tuple[Optional[list[TrackTask]], int]:
        preset = EXPORT_PRESETS[self.mix_config.export_quality]
        policy = self.mix_config.conflict_policy

        existing_hits = sum(
            1 for item in self.music_items if (out_dir / f"{item.path.stem}{preset.extension}").exists()
        )

        if existing_hits > 0 and policy == ConflictPolicy.ASK:
            msg = QMessageBox(self)
            msg.setWindowTitle("Arquivos já existem no destino")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText(
                f"{existing_hits} arquivo(s) já existe(m) em '{out_dir}'.\n"
                "Como deseja proceder para evitar perda de arquivos?"
            )
            btn_rename = msg.addButton("Renomear novos", QMessageBox.ButtonRole.AcceptRole)
            btn_skip = msg.addButton("Pular existentes", QMessageBox.ButtonRole.ActionRole)
            btn_overwrite = msg.addButton("Sobrescrever", QMessageBox.ButtonRole.DestructiveRole)
            btn_cancel = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_rename)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_cancel:
                return None, 0
            if clicked == btn_rename:
                policy = ConflictPolicy.RENAME
            elif clicked == btn_skip:
                policy = ConflictPolicy.SKIP
            elif clicked == btn_overwrite:
                policy = ConflictPolicy.OVERWRITE

        reserved_names: set[str] = set()
        tasks: list[TrackTask] = []
        skipped = 0

        for item in self.music_items:
            base_stem = item.path.stem
            candidate = out_dir / f"{base_stem}{preset.extension}"

            if policy == ConflictPolicy.SKIP and candidate.exists() and candidate.name.lower() not in reserved_names:
                skipped += 1
                continue

            counter = 2
            while candidate.name.lower() in reserved_names or (
                policy == ConflictPolicy.RENAME and candidate.exists()
            ):
                candidate = out_dir / f"{base_stem} ({counter}){preset.extension}"
                counter += 1

            reserved_names.add(candidate.name.lower())
            tasks.append(
                TrackTask(
                    source_path=item.path,
                    output_path=candidate,
                    duration=item.duration,
                    sample_rate=item.sample_rate or 44100,
                )
            )

        return tasks, skipped

    @Slot(object)
    def _on_batch_completed(self, summary: BatchSummary) -> None:
        self._last_summary = summary
        self.history_mgr.add_summary(summary)
        self._refresh_history()
        self._set_inputs_locked(False)
        self.execution_card.show_batch_completed(summary)
        self._update_readiness_state()

    def _set_inputs_locked(self, locked: bool) -> None:
        self.jingle_card.set_locked(locked)
        self.music_card.set_locked(locked)
        self.mixing_card.set_locked(locked)
        self.process_page.set_locked(locked)
        self.settings_page.set_locked(locked)

    # ------------------------------------------------------------------
    # Histórico, FFmpeg badge e encerramento seguro
    # ------------------------------------------------------------------

    @Slot()
    def _on_ffmpeg_badge_clicked(self) -> None:
        if self.ffmpeg_mgr.status.available:
            self.navigate_to(self.PAGE_ABOUT)
        else:
            self._refresh_ffmpeg_status(show_dialog_if_missing=True)

    @Slot(object)
    def _open_history_details(self, entry: HistoryEntry) -> None:
        BatchDetailsDialog(entry.to_summary(), self).exec()

    @Slot()
    def _clear_history(self) -> None:
        self.history_mgr.clear()
        self._refresh_history()

    @Slot()
    def _open_output_folder(self) -> None:
        if self._last_summary and self._last_summary.output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_summary.output_dir)))

    @Slot()
    def _open_batch_details(self) -> None:
        if self._last_summary:
            BatchDetailsDialog(self._last_summary, self).exec()

    def closeEvent(self, event) -> None:
        if self._batch_worker and self._batch_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Processamento em andamento",
                "Há arquivos sendo processados no momento. Deseja cancelar e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._batch_worker.request_cancel()
            self._batch_worker.wait(5000)

        for worker in (self._jingle_worker, self._scan_worker, self._preview_worker):
            if worker and worker.isRunning():
                if isinstance(worker, PreviewWorker):
                    worker.cancel()
                else:
                    worker.requestInterruption()
                worker.wait(2000)

        self._stop_jingle_playback()
        self._stop_preview_playback()
        self.settings_mgr.save_window_geometry(self.saveGeometry())
        super().closeEvent(event)
