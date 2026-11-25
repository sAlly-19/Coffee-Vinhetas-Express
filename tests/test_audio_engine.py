"""Testes do motor FFmpegManager e AudioProcessor (DSP, formatos e metadados)."""

from __future__ import annotations

from array import array
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import wave

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from coffee_vinhetas.core import (
    AudioProcessor,
    DuckingMode,
    ExportQuality,
    FFmpegManager,
    MixConfig,
    TaskStatus,
    TrackTask,
)


def _rms_window(wav_path: Path, t_start: float, t_end: float) -> float:
    with wave.open(str(wav_path), "rb") as w:
        sr = w.getframerate()
        i0 = int(t_start * sr)
        i1 = int(t_end * sr)
        w.setpos(max(0, min(i0, w.getnframes())))
        raw = w.readframes(max(0, i1 - i0))
    samples = array("h")
    samples.frombytes(raw)
    if not samples:
        return 0.0
    return math.sqrt(sum((s / 32768.0) ** 2 for s in samples) / len(samples))


class AudioEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mgr = FFmpegManager()
        cls.status = cls.mgr.detect()
        if not cls.status.available:
            raise unittest.SkipTest(f"FFmpeg indisponível: {cls.status.error}")

        cls.tmp = Path(tempfile.mkdtemp(prefix="coffee_unit_"))
        cls.music_dir = cls.tmp / "Músicas Café & Mixes"
        cls.music_dir.mkdir()
        cls.music_wav = cls.music_dir / "Faixa Ação — 01.wav"
        cls.music_mp3 = cls.music_dir / "Faixa Especial — Café.mp3"
        cls.jingle_wav = cls.tmp / "Vinheta Oficial — Café.wav"
        cls.silent_jingle_wav = cls.tmp / "Vinheta Silêncio.wav"

        ff = str(cls.status.ffmpeg_path)
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=14", "-af", "volume=2.0", "-ac", "2", "-ar", "44100", str(cls.music_wav)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ff, "-y", "-i", str(cls.music_wav), "-metadata", "artist=DJ Café Brasil", "-c:a", "libmp3lame", "-b:a", "192k", str(cls.music_mp3)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=3", "-af", "volume=2.5", "-ac", "2", "-ar", "48000", "-metadata", "artist=METADATA_VINHETA_ERRADA", str(cls.jingle_wav)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=3", "-af", "volume=0.008", "-ac", "2", "-ar", "44100", str(cls.silent_jingle_wav)],
            check=True,
            capture_output=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_probe_and_waveform_peaks(self) -> None:
        info = self.mgr.probe_audio(self.jingle_wav)
        self.assertTrue(info.valid)
        self.assertAlmostEqual(info.duration, 3.0, delta=0.1)
        peaks, _, _, _ = self.mgr.extract_waveform_peaks(self.jingle_wav, info.duration, num_buckets=120)
        self.assertEqual(len(peaks), 120)
        self.assertGreater(max(peaks), 0.5)

    def test_envelope_ducking_exactness_and_restore(self) -> None:
        sj = self.mgr.probe_audio(self.silent_jingle_wav)
        sj.active_start, sj.active_end = 0.0, sj.duration
        proc = AudioProcessor(self.mgr)
        out_wav = self.tmp / "out_env.wav"
        res = proc.process_file(
            TrackTask(self.music_wav, out_wav, 14.0, 44100),
            sj,
            MixConfig(entry_time_sec=4, duck_percent=75, attack_ms=150, release_ms=600, export_quality=ExportQuality.WAV_PCM),
            2,
            threading.Event(),
            lambda _p: None,
            lambda _p: None,
            lambda _f: None,
        )
        self.assertEqual(res.status, TaskStatus.SUCCESS, res.message)
        r_pre = _rms_window(out_wav, 1.0, 3.0)
        r_duck = _rms_window(out_wav, 4.3, 6.7)
        r_post = _rms_window(out_wav, 8.2, 12.0)
        self.assertTrue(0.22 <= (r_duck / r_pre) <= 0.28)
        self.assertTrue(0.95 <= (r_post / r_pre) <= 1.05)
        self.assertAlmostEqual(self.mgr.probe_audio(out_wav).duration, 14.0, delta=0.05)

    def test_sidechain_mode_preserves_duration_and_restores(self) -> None:
        ji = self.mgr.probe_audio(self.jingle_wav)
        _, mean_db, a0, a1 = self.mgr.extract_waveform_peaks(self.jingle_wav, ji.duration, 120)
        ji.mean_volume_db, ji.active_start, ji.active_end = mean_db, a0, a1
        proc = AudioProcessor(self.mgr)
        out_wav = self.tmp / "out_sc.wav"
        res = proc.process_file(
            TrackTask(self.music_wav, out_wav, 14.0, 44100),
            ji,
            MixConfig(entry_time_sec=4, duck_percent=75, ducking_mode=DuckingMode.SIDECHAIN, export_quality=ExportQuality.WAV_PCM),
            2,
            threading.Event(),
            lambda _p: None,
            lambda _p: None,
            lambda _f: None,
        )
        self.assertEqual(res.status, TaskStatus.SUCCESS, res.message)
        self.assertAlmostEqual(self.mgr.probe_audio(out_wav).duration, 14.0, delta=0.05)
        r_pre = _rms_window(out_wav, 1.0, 3.0)
        r_post = _rms_window(out_wav, 8.5, 12.0)
        self.assertTrue(0.95 <= (r_post / r_pre) <= 1.05)

    def test_mp3_and_flac_export_metadata_and_original_intact(self) -> None:
        ji = self.mgr.probe_audio(self.jingle_wav)
        proc = AudioProcessor(self.mgr)
        orig_hash = hashlib.sha256(self.music_mp3.read_bytes()).hexdigest()

        for quality, ext in [(ExportQuality.MP3_320, ".mp3"), (ExportQuality.FLAC, ".flac")]:
            out_f = self.tmp / f"export_{quality.value}{ext}"
            res = proc.process_file(
                TrackTask(self.music_mp3, out_f, 14.0, 44100),
                ji,
                MixConfig(entry_time_sec=3, duck_percent=75, export_quality=quality),
                2,
                threading.Event(),
                lambda _p: None,
                lambda _p: None,
                lambda _f: None,
            )
            self.assertEqual(res.status, TaskStatus.SUCCESS, res.message)
            dec = subprocess.run(
                [str(self.status.ffmpeg_path), "-v", "error", "-i", str(out_f), "-f", "null", "-"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(dec.returncode, 0)
            self.assertEqual(dec.stderr.strip(), "")

            meta_p = subprocess.run(
                [str(self.status.ffprobe_path), "-v", "quiet", "-print_format", "json", "-show_format", str(out_f)],
                capture_output=True,
                text=True,
            )
            tags = {k.lower(): v for k, v in json.loads(meta_p.stdout)["format"].get("tags", {}).items()}
            self.assertEqual(tags.get("artist"), "DJ Café Brasil")

        self.assertEqual(hashlib.sha256(self.music_mp3.read_bytes()).hexdigest(), orig_hash)

    def test_insertion_times_and_large_filter_graph(self) -> None:
        times_rep, warn = AudioProcessor.compute_insertion_times(650.0, 10.0, 15.0, True, 5)
        self.assertEqual(times_rep, [15.0, 315.0, 615.0])
        self.assertEqual(warn, "")

        times_short, warn_short = AudioProcessor.compute_insertion_times(10.0, 3.0, 15.0, False, 5)
        self.assertEqual(times_short, [])
        self.assertIn("insuficiente", warn_short.lower())

        proc = AudioProcessor(self.mgr)
        ji = self.mgr.probe_audio(self.jingle_wav)
        long_graph = proc.build_filter_complex([float(i * 10 + 1) for i in range(60)], ji, 44100, 14.0, MixConfig())
        self.assertGreater(len(long_graph), 8000)
        fc_args = self.mgr.filter_complex_args(long_graph, self.tmp / "long_fc.txt")
        self.assertEqual(fc_args[0], "-/filter_complex" if self.mgr.major_version() >= 7 else "-filter_complex_script")

    def test_trimmed_jingle_processing_and_export(self) -> None:
        sj = self.mgr.probe_audio(self.silent_jingle_wav)
        sj.active_start, sj.active_end = 0.0, sj.duration
        sj.trim_start, sj.trim_end = 0.5, 2.0
        self.assertTrue(sj.is_trimmed)
        self.assertAlmostEqual(sj.effective_duration, 1.5, delta=0.01)

        orig_hash = hashlib.sha256(self.silent_jingle_wav.read_bytes()).hexdigest()
        proc = AudioProcessor(self.mgr)
        out_wav = self.tmp / "out_trimmed_mix.wav"
        res = proc.process_file(
            TrackTask(self.music_wav, out_wav, 14.0, 44100),
            sj,
            MixConfig(entry_time_sec=4, duck_percent=75, attack_ms=100, release_ms=300, export_quality=ExportQuality.WAV_PCM),
            2,
            threading.Event(),
            lambda _p: None,
            lambda _p: None,
            lambda _f: None,
        )
        self.assertEqual(res.status, TaskStatus.SUCCESS, res.message)
        r_pre = _rms_window(out_wav, 1.0, 3.0)
        r_duck = _rms_window(out_wav, 4.2, 5.3)
        r_post_early = _rms_window(out_wav, 6.2, 7.5)
        self.assertTrue(0.20 <= (r_duck / r_pre) <= 0.30)
        self.assertTrue(0.95 <= (r_post_early / r_pre) <= 1.05)

        exported_wav = self.tmp / "vinheta_cortada.wav"
        ok, err = proc.export_trimmed_jingle(sj, exported_wav)
        self.assertTrue(ok, err)
        exp_info = self.mgr.probe_audio(exported_wav)
        self.assertTrue(exp_info.valid)
        self.assertAlmostEqual(exp_info.duration, 1.5, delta=0.08)
        self.assertEqual(hashlib.sha256(self.silent_jingle_wav.read_bytes()).hexdigest(), orig_hash)


if __name__ == "__main__":
    unittest.main()
