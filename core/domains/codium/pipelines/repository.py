# ========== SQL SLOJ PIPELINE-A ==========
# Samo redovi. Kapija, dnevnik i pokretanje procesa su u servisu i motoru.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineRun,
    RunStatus,
    RunStep,
    StepStatus,
)
from core.domains.codium.runtime import codium_database_path

_PIPELINE_KOLONE = ("id, repository_id, name, definition, enabled, "
                    "created_at, updated_at")
_RUN_KOLONE = ("id, pipeline_id, status, trigger, commit_sha, branch, "
               "exit_code, detail, started_at, finished_at, created_at")
_STEP_KOLONE = ("id, run_id, idx, name, status, exit_code, started_at, "
                "finished_at")


def _u_pipeline(row) -> Pipeline:
    return Pipeline(id=row[0], repository_id=row[1], name=row[2],
                    definition=row[3], enabled=bool(row[4]),
                    created_at=row[5], updated_at=row[6])


def _u_run(row) -> PipelineRun:
    return PipelineRun(id=row[0], pipeline_id=row[1], status=row[2],
                       trigger=row[3], commit_sha=row[4], branch=row[5],
                       exit_code=row[6], detail=row[7], started_at=row[8],
                       finished_at=row[9], created_at=row[10])


def _u_step(row) -> RunStep:
    return RunStep(id=row[0], run_id=row[1], idx=row[2], name=row[3],
                   status=row[4], exit_code=row[5], started_at=row[6],
                   finished_at=row[7])


class PipelineRepository:
    """Definicije pipeline-a."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def add(self, pipeline: Pipeline) -> Pipeline:
        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_pipelines (repository_id, name, definition, "
                "enabled) VALUES (?, ?, ?, ?)",
                (pipeline.repository_id, pipeline.name, pipeline.definition,
                 int(pipeline.enabled)),
            )
            novi_id = kursor.lastrowid
        return self.get(novi_id)

    def list(self, repository_id: int | None = None) -> list[Pipeline]:
        uslov = " WHERE repository_id = ?" if repository_id is not None else ""
        parametri = (repository_id,) if repository_id is not None else ()
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines{uslov} "
                "ORDER BY id",
                parametri,
            ).fetchall()
        return [_u_pipeline(red) for red in redovi]

    def get(self, pipeline_id: int) -> Pipeline | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines WHERE id = ?",
                (pipeline_id,),
            ).fetchone()
        return _u_pipeline(red) if red else None

    def get_by_name(self, repository_id: int, name: str) -> Pipeline | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_PIPELINE_KOLONE} FROM codium_pipelines "
                "WHERE repository_id = ? AND name = ?",
                (repository_id, name),
            ).fetchone()
        return _u_pipeline(red) if red else None

    def update_definition(self, pipeline_id: int, name: str,
                          definition: str) -> Pipeline:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipelines SET name = ?, definition = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, definition, pipeline_id),
            )
        return self.get(pipeline_id)

    def delete(self, pipeline_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute("DELETE FROM codium_pipelines WHERE id = ?",
                         (pipeline_id,))


class RunRepository:
    """Pokretanja i njihovi koraci."""

    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or codium_database_path()

    def create(self, run: PipelineRun, step_names: list[str]) -> PipelineRun:
        """Upisuje pokretanje i sve njegove korake u stanju `queued`."""

        with core_database_connection(self._database_path) as veza:
            kursor = veza.execute(
                "INSERT INTO codium_pipeline_runs (pipeline_id, status, "
                "trigger, commit_sha, branch) VALUES (?, ?, ?, ?, ?)",
                (run.pipeline_id, str(run.status), run.trigger,
                 run.commit_sha, run.branch),
            )
            novi_id = kursor.lastrowid
            veza.executemany(
                "INSERT INTO codium_run_steps (run_id, idx, name) "
                "VALUES (?, ?, ?)",
                [(novi_id, redni, ime) for redni, ime in enumerate(step_names)],
            )
        return self.get(novi_id)

    def get(self, run_id: int) -> PipelineRun | None:
        with core_database_connection(self._database_path) as veza:
            red = veza.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_pipeline_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return _u_run(red) if red else None

    def list(self, pipeline_id: int | None = None, status: str | None = None,
             limit: int = 50) -> list[PipelineRun]:
        uslovi: list[str] = []
        parametri: list[object] = []
        if pipeline_id is not None:
            uslovi.append("pipeline_id = ?")
            parametri.append(pipeline_id)
        if status is not None:
            uslovi.append("status = ?")
            parametri.append(str(status))
        where = f" WHERE {' AND '.join(uslovi)}" if uslovi else ""
        parametri.append(limit)

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_RUN_KOLONE} FROM codium_pipeline_runs{where} "
                "ORDER BY id DESC LIMIT ?",
                tuple(parametri),
            ).fetchall()
        return [_u_run(red) for red in redovi]

    def steps(self, run_id: int) -> list[RunStep]:
        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                f"SELECT {_STEP_KOLONE} FROM codium_run_steps "
                "WHERE run_id = ? ORDER BY idx",
                (run_id,),
            ).fetchall()
        return [_u_step(red) for red in redovi]

    # ----------          OZNACAVANJE STANJA          ----------

    def mark_run_started(self, run_id: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipeline_runs SET status = ?, "
                "started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(RunStatus.RUNNING), run_id),
            )

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_pipeline_runs SET status = ?, exit_code = ?, "
                "detail = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(status), exit_code, detail, run_id),
            )

    def mark_step_started(self, run_id: int, idx: int) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_run_steps SET status = ?, "
                "started_at = CURRENT_TIMESTAMP WHERE run_id = ? AND idx = ?",
                (str(StepStatus.RUNNING), run_id, idx),
            )

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None:
        with core_database_connection(self._database_path) as veza:
            veza.execute(
                "UPDATE codium_run_steps SET status = ?, exit_code = ?, "
                "finished_at = CURRENT_TIMESTAMP WHERE run_id = ? AND idx = ?",
                (str(status), exit_code, run_id, idx),
            )

    # ----------          ODRZAVANJE          ----------

    def stale_running(self) -> list[int]:
        """Pokretanja zatecena u `running` — posle restarta su zaostala."""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id FROM codium_pipeline_runs WHERE status = ? "
                "ORDER BY id",
                (str(RunStatus.RUNNING),),
            ).fetchall()
        return [red[0] for red in redovi]

    def older_run_ids(self, pipeline_id: int, keep: int) -> list[int]:
        """Pokretanja izvan poslednjih `keep` za taj pipeline."""

        with core_database_connection(self._database_path) as veza:
            redovi = veza.execute(
                "SELECT id FROM codium_pipeline_runs WHERE pipeline_id = ? "
                "AND id NOT IN (SELECT id FROM codium_pipeline_runs "
                "WHERE pipeline_id = ? ORDER BY id DESC LIMIT ?)",
                (pipeline_id, pipeline_id, keep),
            ).fetchall()
        return [red[0] for red in redovi]
