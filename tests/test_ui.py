"""Testes da camada de UI frameless, sidebar de 5 abas, configurações e histórico."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from coffee_vinhetas.app import CoffeeVinhetasApp
from coffee_vinhetas.core import (
    AudioInfo,
    BatchSummary,
    ExportQuality,
    FFmpegStatus,
    HistoryManager,
    TaskStatus,
    TrackResult,
)
from coffee_vinhetas.ui.dialogs import AboutDialog, BatchDetailsDialog, JingleTrimDialog, SettingsDialog


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app_wrapper = CoffeeVinhetasApp([])
        if QApplication.instance() is not None:
            QApplication.instance().setQuitOnLastWindowClosed(False)
        cls.win = cls.app_wrapper.window
        cls.orig_saved = cls.win.settings_mgr.load_mix_config()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.win.settings_mgr.save_mix_config(cls.orig_saved)
        cls.win.close()

    def test_sidebar_navigation_across_all_five_pages(self) -> None:
        for idx in range(5):
            self.win.navigate_to(idx)
            self.assertEqual(self.win.stack.currentIndex(), idx)
        self.win.navigate_to(0)

    def test_mixing_and_settings_page_sync_and_persistence(self) -> None:
        mixing = self.win.mixing_card
        mixing.entry_spin.setValue(250)
        self.assertEqual(mixing.entry_slider.value(), 120)
        mixing.entry_slider.setValue(42)
        self.assertEqual(mixing.entry_spin.value(), 42)
        mixing.duck_slider.setValue(60)
        self.assertEqual(mixing.duck_spin.value(), 60)

        self.win.settings_page.quality_combo.setCurrentIndex(1)
        self.assertEqual(self.win.mix_config.export_quality, ExportQuality.MP3_256)
        self.assertEqual(self.win.settings_mgr.load_mix_config().export_quality, ExportQuality.MP3_256)

    def test_history_manager_roundtrip(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="coffee_hist_"))
        try:
            hm = HistoryManager(tmp / "history.json")
            summary = BatchSummary(
                total=2,
                succeeded=2,
                failed=0,
                skipped_or_cancelled=0,
                elapsed_sec=3.4,
                output_dir=tmp,
                cancelled=False,
                results=[TrackResult(tmp / "a.mp3", tmp / "out.mp3", TaskStatus.SUCCESS, "1 inserção")],
            )
            hm.add_summary(summary)
            loaded = hm.load_entries()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].succeeded, 2)
            self.assertEqual(len(loaded[0].to_summary().results), 1)
            hm.clear()
            self.assertEqual(hm.load_entries(), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_custom_widgets_and_dialogs_render(self) -> None:
        self.win.jingle_card.waveform.set_peaks([0.2, 0.8, 0.5, 0.9, 0.3] * 24)
        self.assertFalse(self.win.jingle_card.waveform.grab().isNull())
        self.assertFalse(self.win.mixing_card.duck_curve.grab().isNull())

        sdlg = SettingsDialog(self.orig_saved, "", False, self.win.ffmpeg_mgr, self.win)
        adlg = AboutDialog(FFmpegStatus(available=False, error="Teste"), self.win)
        ddlg = BatchDetailsDialog(
            BatchSummary(total=0, succeeded=0, failed=0, skipped_or_cancelled=0, elapsed_sec=0.0, output_dir=Path("."), cancelled=False),
            self.win,
        )
        self.assertEqual(sdlg.mode_combo.count(), 2)
        sdlg.close()
        adlg.close()
        ddlg.close()

    def test_jingle_trim_dialog_and_settings_persistence(self) -> None:
        info = AudioInfo(
            path=Path("AUD-20250322-WA0009.mp3"),
            duration=20.0,
            format_name="MP3",
            sample_rate=44100,
            bit_rate=320000,
            valid=True,
            peaks=[0.8] * 30 + [0.01] * 70,
            active_start=0.0,
            active_end=6.0,
        )
        dlg = JingleTrimDialog(info, self.win.ffmpeg_mgr, self.win)
        dlg.start_spin.setValue(1.5)
        dlg.end_spin.setValue(7.5)
        self.assertAlmostEqual(dlg.trim_start, 1.5, places=2)
        self.assertAlmostEqual(dlg.trim_end, 7.5, places=2)

        dlg._auto_detect_silence()
        self.assertAlmostEqual(dlg.trim_start, 0.0, places=2)
        self.assertAlmostEqual(dlg.trim_end, 6.0, places=2)

        dlg._reset_trim()
        self.assertAlmostEqual(dlg.trim_start, 0.0, places=2)
        self.assertAlmostEqual(dlg.trim_end, 20.0, places=2)
        self.assertFalse(dlg.grab().isNull())
        dlg.close()

        # Persistência do corte no SettingsManager (salva e restaura estado)
        prev_path = self.win.settings_mgr.last_jingle_path
        prev_trim = self.win.settings_mgr.load_jingle_trim(prev_path) if prev_path else (0.0, 0.0)
        try:
            self.win.settings_mgr.save_jingle_trim("C:/demo/jingle.mp3", 0.5, 6.2)
            self.assertEqual(self.win.settings_mgr.load_jingle_trim("C:/demo/jingle.mp3"), (0.5, 6.2))
            self.assertEqual(self.win.settings_mgr.load_jingle_trim("C:/demo/outro.mp3"), (0.0, 0.0))
        finally:
            self.win.settings_mgr.save_jingle_trim(prev_path, prev_trim[0], prev_trim[1])

        info.trim_start, info.trim_end = 0.0, 6.0
        self.win.jingle_card.show_jingle(info)
        self.assertIn("Corte: 00:06", self.win.jingle_card.meta_lbl.text())
        self.assertFalse(self.win.jingle_card.trim_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
