"""Testes dos workers Qt: varredura, prévia, lote paralelo e cancelamento."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from coffee_vinhetas.core import OUTPUT_DIR_NAME, FFmpegManager, MixConfig, TrackTask
from coffee_vinhetas.workers import BatchWorker, MusicScanWorker, PreviewWorker


class WorkersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.mgr = FFmpegManager()
        cls.status = cls.mgr.detect()
        if not cls.status.available:
            raise unittest.SkipTest("FFmpeg indisponível.")

        cls.tmp = Path(tempfile.mkdtemp(prefix="coffee_workers_"))
        cls.music_dir = cls.tmp / "Músicas"
        cls.music_dir.mkdir()
        cls.music_mp3 = cls.music_dir / "Track 01 — Café.mp3"
        cls.jingle_wav = cls.tmp / "Vinheta.wav"
        cls.corrupt_mp3 = cls.music_dir / "Corrompido.mp3"

        ff = str(cls.status.ffmpeg_path)
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=14", "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", str(cls.music_mp3)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=3", "-ac", "2", "-ar", "48000", str(cls.jingle_wav)],
            check=True,
            capture_output=True,
        )
        cls.corrupt_mp3.write_bytes(b"BAD_MP3_HEADER")
        cls.jingle_info = cls.mgr.probe_audio(cls.jingle_wav)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_preview_worker_dynamic_duration(self) -> None:
        music_info = self.mgr.probe_audio(self.music_mp3)
        res = {}
        loop = QEventLoop()
        pw = PreviewWorker(self.mgr, music_info, self.jingle_info, MixConfig(entry_time_sec=4, duck_percent=75))
        pw.preview_ready.connect(lambda p, d: (res.update(path=p, desc=d), loop.quit()))
        pw.preview_failed.connect(lambda e: (res.update(err=e), loop.quit()))
        pw.start()
        QTimer.singleShot(15000, loop.quit)
        loop.exec()
        pw.wait(2000)

        self.assertIn("path", res, res)
        prev_path = Path(res["path"])
        try:
            self.assertTrue(prev_path.exists())
            self.assertGreaterEqual(self.mgr.probe_audio(prev_path).duration, 9.5)
        finally:
            prev_path.unlink(missing_ok=True)

    def test_batch_worker_resilience_and_scan_exclusion(self) -> None:
        out_dir = self.music_dir / OUTPUT_DIR_NAME
        tasks = [
            TrackTask(self.music_mp3, out_dir / "Track 01 — Café.mp3", 14.0, 44100),
            TrackTask(self.corrupt_mp3, out_dir / "Corrompido.mp3", 0.0, 44100),
        ]
        res = {}
        loop = QEventLoop()
        bw = BatchWorker(self.mgr, tasks, self.jingle_info, MixConfig(entry_time_sec=3, parallel_limit=2), out_dir)
        bw.batch_completed.connect(lambda s: (res.update(summary=s), loop.quit()))
        bw.start()
        QTimer.singleShot(20000, loop.quit)
        loop.exec()
        bw.wait(2000)

        summary = res["summary"]
        self.assertEqual(summary.succeeded, 1)
        self.assertEqual(summary.failed, 1)
        self.assertFalse(summary.cancelled)
        self.assertEqual(list(out_dir.glob(".tmp_coffee_*")), [])

        scan_res = {}
        loop2 = QEventLoop()
        sw = MusicScanWorker(self.mgr, [self.music_dir], True, set())
        sw.scan_finished.connect(lambda infos, ign, warn: (scan_res.update(infos=infos, ign=ign), loop2.quit()))
        sw.start()
        QTimer.singleShot(10000, loop2.quit)
        loop2.exec()
        sw.wait(2000)

        paths = [i.path for i in scan_res["infos"]]
        self.assertTrue(all(OUTPUT_DIR_NAME not in p.parts for p in paths))
        self.assertEqual(len(paths), 1)
        self.assertEqual(scan_res["ign"], 1)

    def test_batch_worker_cancellation_cleans_temp_files(self) -> None:
        out_dir = self.tmp / "cancel_out"
        tasks = [TrackTask(self.music_mp3, out_dir / f"cancel_{i}.mp3", 14.0, 44100) for i in range(12)]
        res = {}
        cancelled_once = [False]
        loop = QEventLoop()
        bw = BatchWorker(self.mgr, tasks, self.jingle_info, MixConfig(entry_time_sec=3, parallel_limit=2), out_dir)

        def _on_prog(*_args) -> None:
            if not cancelled_once[0]:
                cancelled_once[0] = True
                bw.request_cancel()

        bw.progress_updated.connect(_on_prog)
        bw.batch_completed.connect(lambda s: (res.update(summary=s), loop.quit()))
        bw.start()
        QTimer.singleShot(15000, loop.quit)
        loop.exec()
        bw.wait(3000)

        self.assertTrue(res["summary"].cancelled)
        self.assertEqual(list(out_dir.glob(".tmp_coffee_*")), [])


if __name__ == "__main__":
    unittest.main()
