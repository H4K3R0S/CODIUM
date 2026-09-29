# ========== SQL SLOJ LOGA ==========
# Odvojen fajl jer je odvojena baza: `codium_ops.db` raste hiljadama redova
# po pokretanju i ne sme da zakljucava poslovnu bazu.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.pipelines.models import RunLogLine
from core.domains.codium.runtime import codium_ops_database_path


class RunLogRepository:
    """Upis i citanje redova loga."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_ops_database_path()

    def append(self, lines: list[RunLogLine]) -> None:
        """Upisuje seriju redova u jednoj transakciji."""

        if not lines:
            return
        with core_database_connection(self._database_path) as veza:
            veza.executemany(
                "INSERT INTO codium_run_logs (run_id, step_idx, seq, stream, "
                "line) VALUES (?, ?, ?, ?, ?)",
                [(red.run_id, red.step_idx, red.seq, red.stream, red.line)
                 for red in lines],
            )

    def read(self, run_id: int, after_seq: int = 0,
             limit: int = 1000) -> list[RunLogLine]:
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id, run_id, step_idx, seq, stream, line, at "
                "FROM codium_run_logs WHERE run_id = ? AND seq > ? "
                "ORDER BY seq LIMIT ?",
                (run_id, after_seq, limit),
            ).fetchall()
        return [
            RunLogLine(id=red[0], run_id=red[1], step_idx=red[2], seq=red[3],
                       stream=red[4], line=red[5], at=red[6])
            for red in redovi
        ]

    def delete_for_runs(self, run_ids: list[int]) -> None:
        if not run_ids:
            return
        mesta = ", ".join("?" for _ in run_ids)
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                f"DELETE FROM codium_run_logs WHERE run_id IN ({mesta})",
                tuple(run_ids),
            )
