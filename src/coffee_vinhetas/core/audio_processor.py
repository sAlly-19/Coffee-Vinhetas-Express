"""Motor DSP de inserção de vinhetas, ducking inteligente e gravação segura."""

from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Callable, Optional
import uuid

from .constants import EXPORT_PRESETS, DuckingMode, format_duration, subprocess_kwargs
from .ffmpeg_manager import FFmpegManager
from .logging_setup import LOGGER
from .models import AudioInfo, MixConfig, TaskStatus, TrackResult, TrackTask


class AudioProcessor:
    """Constrói filter_complex de ducking preciso e executa FFmpeg com segurança."""

    def __init__(self, ffmpeg_mgr: FFmpegManager) -> None:
        self.ffmpeg_mgr = ffmpeg_mgr

    @staticmethod
    def compute_insertion_times(
        music_duration: float,
        jingle_duration: float,
        entry_time_sec: float,
        repeat_enabled: bool,
        repeat_interval_min: int,
    ) -> tuple[list[float], str]:
        """Retorna instantes de entrada válidos (sem cortar a vinheta) e possível aviso."""
        if music_duration <= 0 or jingle_duration <= 0:
            return [], "Duração inválida de áudio."

        if music_duration < jingle_duration:
            return [], (
                f"Música ({format_duration(music_duration)}) é menor que a vinheta "
                f"({format_duration(jingle_duration)}); ignorada para não truncar."
            )

        if entry_time_sec < 0:
            entry_time_sec = 0.0

        if entry_time_sec + jingle_duration > music_duration + 0.05:
            return [], (
                f"Música ({format_duration(music_duration)}) é insuficiente para inserir a vinheta "
                f"({format_duration(jingle_duration)}) aos {int(round(entry_time_sec))}s sem cortes."
            )

        times: list[float] = [float(entry_time_sec)]
        if repeat_enabled:
            interval_sec = max(1, repeat_interval_min) * 60.0
            if interval_sec <= jingle_duration:
                return [], (
                    f"Intervalo de repetição ({int(interval_sec)}s) menor ou igual à duração da vinheta "
                    f"({jingle_duration:.1f}s); ajustado para evitar sobreposição."
                )
            t = entry_time_sec + interval_sec
            while t + jingle_duration <= music_duration + 0.05:
                times.append(round(t, 4))
                t += interval_sec

        return times, ""

    @staticmethod
    def _balanced_sum(terms: list[str]) -> str:
        """Soma termos em árvore binária balanceada para manter profundidade O(log N) no av_expr."""
        if not terms:
            return "0"
        cur = list(terms)
        while len(cur) > 1:
            nxt: list[str] = []
            for i in range(0, len(cur), 2):
                if i + 1 < len(cur):
                    nxt.append(f"({cur[i]}+{cur[i + 1]})")
                else:
                    nxt.append(cur[i])
            cur = nxt
        return cur[0]

    @classmethod
    def build_envelope_expression(
        cls,
        insertion_times: list[float],
        jingle_info: AudioInfo,
        cfg: MixConfig,
        music_duration: float,
    ) -> str:
        """Gera expressão suave (cosseno elevado) garantindo atenuação percentual previsível."""
        target_gain = max(0.05, min(0.95, 1.0 - (cfg.duck_percent / 100.0)))
        depth = 1.0 - target_gain
        att = max(0.02, cfg.attack_ms / 1000.0)
        rel = max(0.05, cfg.release_ms / 1000.0)

        eff_dur = jingle_info.effective_duration
        if jingle_info.is_trimmed:
            t_start = jingle_info.effective_trim_start
            t_end = jingle_info.effective_trim_end
            act_start = max(0.0, min(eff_dur, jingle_info.active_start - t_start))
            act_end = max(0.0, min(eff_dur, jingle_info.active_end - t_start))
            if act_end - act_start < 0.15:
                act_start, act_end = 0.0, eff_dur
        else:
            act_start = max(0.0, jingle_info.active_start)
            act_end = min(eff_dur, jingle_info.active_end)
            if act_end <= act_start:
                act_start, act_end = 0.0, eff_dur

        window_terms: list[str] = []
        for t0 in insertion_times:
            w_start = t0 + act_start
            w_end = t0 + act_end

            if w_start >= att * 0.75:
                a = max(0.0, w_start - att * 0.75)
                b = min(w_end, a + att)
            else:
                a = max(0.0, w_start)
                b = min(w_end, a + att)

            c = max(b, w_end)
            d = min(music_duration + 0.5, c + rel)

            parts: list[str] = []
            if b - a > 0.002:
                parts.append(f"gte(t,{a:.4f})*lt(t,{b:.4f})*(0.5-0.5*cos(PI*(t-{a:.4f})/{(b - a):.4f}))")
            if c - b > 0.001:
                parts.append(f"gte(t,{b:.4f})*lt(t,{c:.4f})")
            if d - c > 0.002:
                parts.append(f"gte(t,{c:.4f})*lt(t,{d:.4f})*(0.5+0.5*cos(PI*(t-{c:.4f})/{(d - c):.4f}))")

            if parts:
                window_terms.append(f"({'+'.join(parts)})")

        if not window_terms:
            return "1"

        total_env = cls._balanced_sum(window_terms)
        return f"1-{depth:.4f}*min(1,{total_env})"

    @staticmethod
    def compute_sidechain_params(jingle_info: AudioInfo, cfg: MixConfig) -> tuple[float, float, float]:
        """Mapeia duck_percent para (threshold, ratio, level_sc) coerentes com o nível da vinheta."""
        target_gain = max(0.05, min(0.95, 1.0 - (cfg.duck_percent / 100.0)))
        reduction_db = -20.0 * math.log10(target_gain)

        jingle_db = max(-42.0, min(-3.0, jingle_info.mean_volume_db))
        level_sc = max(0.1, min(16.0, 10.0 ** ((-6.0 - jingle_db) / 20.0)))

        threshold_db = -24.0 if reduction_db <= 16.5 else -36.0
        excess_db = -6.0 - threshold_db
        desired_out_excess = max(0.4, excess_db - reduction_db)
        ratio = max(1.1, min(20.0, excess_db / desired_out_excess))
        threshold_lin = max(0.001, min(1.0, 10.0 ** (threshold_db / 20.0)))
        return threshold_lin, ratio, level_sc

    @staticmethod
    def _jingle_trim_filter_chain(jingle_info: AudioInfo) -> str:
        """Retorna cadeia atrim + micro-fade (20 ms) quando há corte configurado na vinheta."""
        if not jingle_info.is_trimmed:
            return ""
        t_start = jingle_info.effective_trim_start
        t_end = jingle_info.effective_trim_end
        eff_dur = jingle_info.effective_duration
        parts = [f"atrim=start={t_start:.4f}:end={t_end:.4f}", "asetpts=PTS-STARTPTS"]
        fade_s = min(0.02, eff_dur * 0.15)
        if t_start > 0.01 and fade_s >= 0.005:
            parts.append(f"afade=t=in:st=0:d={fade_s:.4f}")
        if t_end < jingle_info.duration - 0.01 and fade_s >= 0.005:
            fade_out_st = max(0.0, eff_dur - fade_s)
            parts.append(f"afade=t=out:st={fade_out_st:.4f}:d={fade_s:.4f}")
        return ",".join(parts) + ","

    def build_filter_complex(
        self,
        insertion_times: list[float],
        jingle_info: AudioInfo,
        music_sample_rate: int,
        music_duration: float,
        cfg: MixConfig,
    ) -> str:
        """Constrói o grafo filter_complex completo com controle de ganho e limitador de pico."""
        sr = music_sample_rate if music_sample_rate >= 8000 else 44100
        lines: list[str] = []
        trim_prefix = self._jingle_trim_filter_chain(jingle_info)

        if len(insertion_times) == 1:
            delay_ms = max(0, int(round(insertion_times[0] * 1000.0)))
            lines.append(
                f"[1:a]{trim_prefix}aresample={sr}:async=1:first_pts=0,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"adelay={delay_ms}:all=1[jingle_mix_in]"
            )
        else:
            n = len(insertion_times)
            splits = "".join(f"[js{i}]" for i in range(n))
            lines.append(
                f"[1:a]{trim_prefix}aresample={sr}:async=1:first_pts=0,"
                f"aformat=sample_fmts=fltp:channel_layouts=stereo,asplit={n}{splits}"
            )
            delayed_labels: list[str] = []
            for i, t_ins in enumerate(insertion_times):
                delay_ms = max(0, int(round(t_ins * 1000.0)))
                lbl = f"[jd{i}]"
                lines.append(f"[js{i}]adelay={delay_ms}:all=1{lbl}")
                delayed_labels.append(lbl)
            lines.append(
                f"{''.join(delayed_labels)}amix=inputs={n}:duration=longest:normalize=0[jingle_mix_in]"
            )

        if cfg.ducking_mode == DuckingMode.SIDECHAIN:
            threshold_lin, ratio, level_sc = self.compute_sidechain_params(jingle_info, cfg)
            lines.append("[jingle_mix_in]asplit=2[jingle_mix][jingle_sc_raw]")
            lines.append(f"[jingle_sc_raw]apad=whole_dur={music_duration + 0.5:.6f}[jingle_sc]")
            lines.append(
                f"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=async=1:first_pts=0[music_fmt]"
            )
            lines.append(
                f"[music_fmt][jingle_sc]sidechaincompress="
                f"threshold={threshold_lin:.6f}:ratio={ratio:.3f}:"
                f"attack={cfg.attack_ms}:release={cfg.release_ms}:"
                f"knee=2.82843:detection=rms:level_sc={level_sc:.4f}[ducked]"
            )
            jingle_for_mix = "[jingle_mix]"
        else:
            env_expr = self.build_envelope_expression(insertion_times, jingle_info, cfg, music_duration)
            lines.append(
                f"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"aresample=async=1:first_pts=0,asetnsamples=n=256,"
                f"volume=volume='{env_expr}':eval=frame[ducked]"
            )
            jingle_for_mix = "[jingle_mix_in]"

        lines.append(
            f"[ducked]{jingle_for_mix}amix=inputs=2:duration=first:normalize=0,"
            f"alimiter=limit=0.977:attack=5:release=50:level=false,"
            f"atrim=0:{music_duration:.6f},asetpts=PTS-STARTPTS[out]"
        )
        return ";\n".join(lines)

    def process_file(
        self,
        task: TrackTask,
        jingle_info: AudioInfo,
        cfg: MixConfig,
        threads_per_proc: int,
        cancel_event: threading.Event,
        register_proc: Callable[[subprocess.Popen[str]], None],
        unregister_proc: Callable[[subprocess.Popen[str]], None],
        progress_cb: Callable[[float], None],
    ) -> TrackResult:
        start_ts = time.monotonic()
        if cancel_event.is_set():
            return TrackResult(task.source_path, None, TaskStatus.CANCELLED, "Cancelado antes de iniciar.")

        if not self.ffmpeg_mgr.status.available or not self.ffmpeg_mgr.status.ffmpeg_path:
            return TrackResult(task.source_path, None, TaskStatus.FAILED, "FFmpeg não está disponível.")

        music_info = self.ffmpeg_mgr.probe_audio(task.source_path)
        if not music_info.valid:
            return TrackResult(task.source_path, None, TaskStatus.FAILED, music_info.error)

        insertion_times, warn_msg = self.compute_insertion_times(
            music_duration=music_info.duration,
            jingle_duration=jingle_info.effective_duration,
            entry_time_sec=float(cfg.entry_time_sec),
            repeat_enabled=cfg.repeat_enabled,
            repeat_interval_min=cfg.repeat_interval_min,
        )
        if not insertion_times:
            return TrackResult(
                source_path=task.source_path,
                output_path=None,
                status=TaskStatus.SKIPPED,
                message=warn_msg or "Não foi possível encaixar a vinheta nesta faixa.",
                warning=warn_msg,
                elapsed_sec=time.monotonic() - start_ts,
            )

        preset = EXPORT_PRESETS[cfg.export_quality]
        out_dir = task.output_path.parent
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            free_bytes = shutil.disk_usage(out_dir).free
            min_needed = max(2 * 1024 * 1024, int(music_info.duration * (500_000 if preset.lossless else 60_000)))
            if free_bytes < min_needed:
                return TrackResult(
                    task.source_path,
                    None,
                    TaskStatus.FAILED,
                    "Espaço em disco insuficiente na pasta de destino.",
                )
        except OSError as exc:
            return TrackResult(task.source_path, None, TaskStatus.FAILED, f"Erro ao preparar destino: {exc}")

        filter_graph = self.build_filter_complex(
            insertion_times=insertion_times,
            jingle_info=jingle_info,
            music_sample_rate=music_info.sample_rate,
            music_duration=music_info.duration,
            cfg=cfg,
        )

        temp_token = uuid.uuid4().hex[:10]
        temp_audio = out_dir / f".tmp_coffee_{temp_token}{preset.extension}"
        script_file = Path(tempfile.gettempdir()) / f"coffee_fc_{temp_token}.txt"

        proc: Optional[subprocess.Popen[str]] = None
        stderr_lines: list[str] = []

        try:
            fc_args = self.ffmpeg_mgr.filter_complex_args(filter_graph, script_file)
            cmd = [
                str(self.ffmpeg_mgr.status.ffmpeg_path),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostats",
                "-threads",
                str(threads_per_proc),
                "-i",
                str(task.source_path),
                "-i",
                str(jingle_info.path),
                *fc_args,
                "-map",
                "[out]",
                "-map_metadata",
                "0",
                "-ar",
                str(music_info.sample_rate),
                "-ac",
                "2",
                *preset.codec_args,
                "-f",
                preset.muxer,
                "-progress",
                "pipe:1",
                str(temp_audio),
            ]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **subprocess_kwargs(),
            )
            register_proc(proc)

            def _drain_stderr() -> None:
                assert proc is not None and proc.stderr is not None
                for line in proc.stderr:
                    clean = line.strip()
                    if clean:
                        stderr_lines.append(clean)

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            assert proc.stdout is not None
            for raw_line in proc.stdout:
                if cancel_event.is_set():
                    break
                line = raw_line.strip()
                if line.startswith("out_time_us="):
                    val = line.split("=", 1)[1].strip()
                    try:
                        us = int(val)
                        if us >= 0 and music_info.duration > 0:
                            frac = min(0.99, max(0.0, (us / 1_000_000.0) / music_info.duration))
                            progress_cb(frac)
                    except ValueError:
                        pass
                elif line == "progress=end":
                    progress_cb(1.0)

            rc = proc.wait()
            stderr_thread.join(timeout=2.0)

            if cancel_event.is_set():
                self.safe_unlink(temp_audio)
                return TrackResult(
                    task.source_path,
                    None,
                    TaskStatus.CANCELLED,
                    "Processamento cancelado pelo usuário.",
                    elapsed_sec=time.monotonic() - start_ts,
                )

            if rc != 0 or not temp_audio.is_file() or temp_audio.stat().st_size == 0:
                self.safe_unlink(temp_audio)
                err_detail = " | ".join(stderr_lines[-3:]) if stderr_lines else f"FFmpeg retornou código {rc}."
                return TrackResult(
                    task.source_path,
                    None,
                    TaskStatus.FAILED,
                    f"Falha na codificação: {err_detail}",
                    elapsed_sec=time.monotonic() - start_ts,
                )

            os.replace(temp_audio, task.output_path)
            progress_cb(1.0)

            return TrackResult(
                source_path=task.source_path,
                output_path=task.output_path,
                status=TaskStatus.SUCCESS,
                message=f"{len(insertion_times)} inserção(ões) aplicada(s).",
                elapsed_sec=time.monotonic() - start_ts,
                insertions=len(insertion_times),
            )
        except Exception as exc:
            self.safe_unlink(temp_audio)
            LOGGER.exception("Erro inesperado ao processar %s", task.source_path)
            return TrackResult(
                task.source_path,
                None,
                TaskStatus.FAILED,
                f"Erro inesperado: {exc}",
                elapsed_sec=time.monotonic() - start_ts,
            )
        finally:
            if proc is not None:
                unregister_proc(proc)
                for pipe in (proc.stdout, proc.stderr):
                    if pipe is not None:
                        try:
                            pipe.close()
                        except OSError:
                            pass
            self.safe_unlink(script_file)

    def export_trimmed_jingle(self, jingle_info: AudioInfo, dest_path: Path) -> tuple[bool, str]:
        """Exporta a vinheta recortada para um novo arquivo sem modificar o original."""
        if not self.ffmpeg_mgr.status.available or not self.ffmpeg_mgr.status.ffmpeg_path:
            return False, "FFmpeg indisponível."
        if jingle_info.path.resolve() == dest_path.resolve():
            return False, "Escolha um nome ou pasta diferente para preservar a vinheta original."

        ext = dest_path.suffix.lower()
        codec_map: dict[str, tuple[str, tuple[str, ...]]] = {
            ".mp3": ("mp3", ("-c:a", "libmp3lame", "-b:a", "320k", "-id3v2_version", "3")),
            ".wav": ("wav", ("-c:a", "pcm_s16le")),
            ".flac": ("flac", ("-c:a", "flac", "-compression_level", "5")),
            ".m4a": ("ipod", ("-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart")),
            ".ogg": ("ogg", ("-c:a", "libvorbis", "-q:a", "7")),
        }
        muxer, codec_args = codec_map.get(ext, ("mp3", ("-c:a", "libmp3lame", "-b:a", "320k")))
        trim_chain = self._jingle_trim_filter_chain(jingle_info).rstrip(",")

        temp_out = dest_path.parent / f".tmp_trim_{uuid.uuid4().hex[:8]}{dest_path.suffix}"
        cmd = [
            str(self.ffmpeg_mgr.status.ffmpeg_path),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(jingle_info.path),
        ]
        if trim_chain:
            cmd.extend(["-af", trim_chain])
        cmd.extend(["-map_metadata", "0", *codec_args, "-f", muxer, str(temp_out)])

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                **subprocess_kwargs(),
            )
            if proc.returncode != 0 or not temp_out.is_file() or temp_out.stat().st_size == 0:
                self.safe_unlink(temp_out)
                return False, proc.stderr.strip() or f"FFmpeg retornou código {proc.returncode}."
            os.replace(temp_out, dest_path)
            return True, str(dest_path)
        except Exception as exc:
            self.safe_unlink(temp_out)
            return False, str(exc)

    @staticmethod
    def safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
