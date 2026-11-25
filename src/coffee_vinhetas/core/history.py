"""Persistência local do histórico real de lotes processados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from .logging_setup import LOGGER, get_app_data_dir
from .models import BatchSummary, TaskStatus, TrackResult


@dataclass
class HistoryEntry:
    timestamp: str
    total: int
    succeeded: int
    failed: int
    skipped_or_cancelled: int
    elapsed_sec: float
    output_dir: str
    cancelled: bool
    results: list[dict[str, object]] = field(default_factory=list)

    def to_summary(self) -> BatchSummary:
        track_results: list[TrackResult] = []
        for item in self.results:
            try:
                status = TaskStatus(str(item.get("status", TaskStatus.FAILED.value)))
            except ValueError:
                status = TaskStatus.FAILED
            out_raw = item.get("output_path")
            track_results.append(
                TrackResult(
                    source_path=Path(str(item.get("source_path", ""))),
                    output_path=Path(str(out_raw)) if out_raw else None,
                    status=status,
                    message=str(item.get("message", "")),
                    warning=str(item.get("warning", "")),
                    elapsed_sec=float(item.get("elapsed_sec", 0.0)),
                    insertions=int(item.get("insertions", 0)),
                )
            )
        return BatchSummary(
            total=self.total,
            succeeded=self.succeeded,
            failed=self.failed,
            skipped_or_cancelled=self.skipped_or_cancelled,
            elapsed_sec=self.elapsed_sec,
            output_dir=Path(self.output_dir),
            cancelled=self.cancelled,
            results=track_results,
        )


class HistoryManager:
    """Lê e grava execuções reais do lote em history.json."""

    MAX_ENTRIES = 50

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = file_path or (get_app_data_dir() / "history.json")

    def load_entries(self) -> list[HistoryEntry]:
        if not self.file_path.is_file():
            return []
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            entries: list[HistoryEntry] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                entries.append(
                    HistoryEntry(
                        timestamp=str(item.get("timestamp", "")),
                        total=int(item.get("total", 0)),
                        succeeded=int(item.get("succeeded", 0)),
                        failed=int(item.get("failed", 0)),
                        skipped_or_cancelled=int(item.get("skipped_or_cancelled", 0)),
                        elapsed_sec=float(item.get("elapsed_sec", 0.0)),
                        output_dir=str(item.get("output_dir", "")),
                        cancelled=bool(item.get("cancelled", False)),
                        results=list(item.get("results", [])),
                    )
                )
            return entries
        except Exception as exc:
            LOGGER.warning("Falha ao ler histórico local: %s", exc)
            return []

    def add_summary(self, summary: BatchSummary) -> HistoryEntry:
        entry = HistoryEntry(
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            total=summary.total,
            succeeded=summary.succeeded,
            failed=summary.failed,
            skipped_or_cancelled=summary.skipped_or_cancelled,
            elapsed_sec=round(summary.elapsed_sec, 2),
            output_dir=str(summary.output_dir),
            cancelled=summary.cancelled,
            results=[
                {
                    "source_path": str(r.source_path),
                    "output_path": str(r.output_path) if r.output_path else None,
                    "status": r.status.value,
                    "message": r.message,
                    "warning": r.warning,
                    "elapsed_sec": round(r.elapsed_sec, 2),
                    "insertions": r.insertions,
                }
                for r in summary.results
            ],
        )
        entries = self.load_entries()
        entries.insert(0, entry)
        self._save_entries(entries[: self.MAX_ENTRIES])
        return entry

    def clear(self) -> None:
        self._save_entries([])

    def _save_entries(self, entries: list[HistoryEntry]) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [
                {
                    "timestamp": e.timestamp,
                    "total": e.total,
                    "succeeded": e.succeeded,
                    "failed": e.failed,
                    "skipped_or_cancelled": e.skipped_or_cancelled,
                    "elapsed_sec": e.elapsed_sec,
                    "output_dir": e.output_dir,
                    "cancelled": e.cancelled,
                    "results": e.results,
                }
                for e in entries
            ]
            self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            LOGGER.warning("Falha ao salvar histórico local: %s", exc)
