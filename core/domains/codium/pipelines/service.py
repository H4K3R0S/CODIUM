# ========== SERVIS PIPELINE-A ==========
# Jedino mesto u fazi koje zove kapiju i dnevnik. Motor ne zna za dozvole,
# SQL sloj ne zna za pravila.
from __future__ import annotations

from pathlib import Path

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.automations import bus
from core.domains.codium.paths import codium_paths
from core.domains.codium.pipelines import artifacts
from core.domains.codium.pipelines.definition import parse
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.models import (
    Pipeline,
    PipelineRun,
    RunLogLine,
    RunStatus,
    RunStep,
)
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.repositories.repository import RepositoryRepository
from core.security.scope_gate import ALLOW, ScopeGate

# Za koliko poslednjih pokretanja po pipeline-u se cuva pun log.
ZADRZI_POKRETANJA = 50


class PipelineError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class PipelineNotFound(PipelineError):
    """Trazen pipeline ne postoji."""


class RunNotFound(PipelineError):
    """Trazeno pokretanje ne postoji."""


class RepositoryMissing(PipelineError):
    """Koren repozitorijuma vise ne postoji na disku."""


class RunDenied(PipelineError):
    """Kapija nije dozvolila pokretanje."""


class PipelineService:
    """Definicije, pokretanja i log."""

    def __init__(self, *, pipelines: PipelineRepository, runs: RunRepository,
                 logs: RunLogRepository, runner: PipelineRunner,
                 gate: ScopeGate, audit: AuditRepository,
                 repositories: RepositoryRepository,
                 keep_runs: int = ZADRZI_POKRETANJA,
                 artifacts_dir: Path | None = None,
                 keep_artifacts: int = artifacts.ZADRZI_ARTEFAKATA) -> None:
        self._pipelines = pipelines
        self._runs = runs
        self._logs = logs
        self._runner = runner
        self._gate = gate
        self._audit = audit
        self._repositories = repositories
        self._keep_runs = keep_runs
        self._artifacts_dir = artifacts_dir or codium_paths.artifacts
        self._keep_artifacts = keep_artifacts

    # ----------          DEFINICIJE          ----------

    def create(self, repository_id: int, definition_text: str,
               actor: str = "human") -> Pipeline:
        koren = self._koren(repository_id, mora_da_postoji=False)
        definicija = parse(definition_text, root=koren)
        upisan = self._pipelines.add(Pipeline(
            repository_id=repository_id, name=definicija.name,
            definition=definition_text,
        ))
        self._trag(actor, "pipeline.write", f"pipeline:{upisan.id}", ALLOW,
                   "ok", "nov pipeline")
        return upisan

    def update(self, pipeline_id: int, definition_text: str,
               actor: str = "human") -> Pipeline:
        postojeci = self._nadji(pipeline_id)
        koren = self._koren(postojeci.repository_id, mora_da_postoji=False)
        definicija = parse(definition_text, root=koren)
        izmenjen = self._pipelines.update_definition(
            pipeline_id, definicija.name, definition_text,
        )
        self._trag(actor, "pipeline.write", f"pipeline:{pipeline_id}", ALLOW,
                   "ok", "izmenjena definicija")
        return izmenjen

    def delete(self, pipeline_id: int, actor: str = "human") -> None:
        self._nadji(pipeline_id)
        self._pipelines.delete(pipeline_id)
        self._trag(actor, "pipeline.write", f"pipeline:{pipeline_id}", ALLOW,
                   "ok", "obrisan pipeline")

    def list(self, repository_id: int | None = None) -> list[Pipeline]:
        return self._pipelines.list(repository_id)

    # ----------          POKRETANJE          ----------

    def run(self, pipeline_id: int, actor: str = "human",
            trigger: str = "manual") -> PipelineRun:
        """Pokrece pipeline. Ne ceka kraj — vraca pokretanje odmah."""

        pipeline = self._nadji(pipeline_id)
        cilj = f"pipeline:{pipeline_id}"

        odluka = self._gate.check(actor=actor, action="pipeline.run", target=cilj)
        if odluka.verdict != ALLOW:
            self._trag(actor, "pipeline.run", cilj, odluka.verdict, "blocked",
                       odluka.reason)
            raise RunDenied(odluka.reason)

        koren = self._koren(pipeline.repository_id, mora_da_postoji=True)
        definicija = parse(pipeline.definition, root=koren)

        pokretanje = self._runs.create(
            PipelineRun(pipeline_id=pipeline_id, trigger=trigger),
            [korak.name for korak in definicija.steps],
        )
        self._runner.start(pokretanje.id, definicija, koren)
        self._trag(actor, "pipeline.run", cilj, odluka.verdict, "ok",
                   f"run {pokretanje.id}")
        return pokretanje

    def bind_loop(self, loop) -> None:
        """Prosledi runner-u petlju API procesa (vidi `PipelineRunner.bind_loop`)."""

        self._runner.bind_loop(loop)

    def cancel(self, run_id: int, actor: str = "human") -> bool:
        self._nadji_pokretanje(run_id)
        otkazano = self._runner.cancel(run_id)
        self._trag(actor, "pipeline.cancel", f"run:{run_id}", ALLOW,
                   "ok" if otkazano else "blocked",
                   "otkazano" if otkazano else "pokretanje vise ne radi")
        return otkazano

    # ----------          CITANJE          ----------

    def run_detail(self, run_id: int) -> tuple[PipelineRun, list[RunStep]]:
        pokretanje = self._nadji_pokretanje(run_id)
        return (pokretanje, self._runs.steps(run_id))

    def run_history(self, pipeline_id: int | None = None,
                    status: str | None = None,
                    limit: int = 50) -> list[PipelineRun]:
        return self._runs.list(pipeline_id, status, limit)

    def logs(self, run_id: int, after_seq: int = 0) -> list[RunLogLine]:
        self._nadji_pokretanje(run_id)
        return self._logs.read(run_id, after_seq)

    # ----------          ODRZAVANJE          ----------

    def recover_stale(self) -> int:
        """Zaostala pokretanja posle restarta prelaze u `failed`.

        Bez ovoga pokretanje prekinuto gasenjem aplikacije zauvek visi u
        „radi", pa se u istoriji ne razlikuje od onog koje jos traje.
        """

        zaostala = self._runs.stale_running()
        for run_id in zaostala:
            self._runs.mark_run_finished(run_id, RunStatus.FAILED, None,
                                         "aplikacija zatvorena")
        return len(zaostala)

    def prune_logs(self, pipeline_id: int) -> None:
        """Brise log pokretanjima izvan poslednjih `keep_runs`."""

        stari = self._runs.older_run_ids(pipeline_id, self._keep_runs)
        self._logs.delete_for_runs(stari)

    def prune_artifacts(self, pipeline_id: int) -> int:
        """Brise pakete pokretanjima izvan poslednjih `keep_artifacts`."""

        stari = self._runs.older_run_ids(pipeline_id, self._keep_artifacts)
        return artifacts.prune(artifacts_dir=self._artifacts_dir,
                               stale_run_ids=stari)

    def after_run_finished(self, run_id: int, status: str) -> None:
        """Sve sto se radi cim jedno pokretanje zavrsi.

        Jedno mesto umesto tri iste zatvorene funkcije po pozivaocu (runtime
        i dva testa su ranije svaki nosili svoju kopiju).

        Pakovanje je namerno sinhrono, u istoj petlji u kojoj motor radi:
        artefakt mora da postoji pre nego sto pokretanje postane vidljivo kao
        uspesno, inace bi „Isporuci" nudio pokretanje ciji paket jos nastaje.
        Cena je da veliki `dist/` na trenutak drzi petlju.
        """

        pokretanje = self._runs.get(run_id)
        if pokretanje is None:
            return
        if status == RunStatus.SUCCESS:
            self._spakuj_artefakt(pokretanje)
        self.prune_logs(pokretanje.pipeline_id)
        self.prune_artifacts(pokretanje.pipeline_id)

        # Dogadjaj ide TEK sada, posle pakovanja artefakta: pravilo koje na
        # uspesno pokretanje odmah isporucuje mora da zatekne paket, ne da ga
        # ceka. Objavljivanje je sinhrono, ali pretplatnik koji pukne ne moze
        # da obori pokretanje (vidi `EventBus.publish`).
        bus.publish("pipeline.run.finished", {
            "run_id": pokretanje.id,
            "pipeline_id": pokretanje.pipeline_id,
            "status": str(status),
            "exit_code": pokretanje.exit_code,
            "duration_seconds": self._trajanje(pokretanje),
        })

    @staticmethod
    def _trajanje(pokretanje: PipelineRun) -> float | None:
        """Trajanje u sekundama, ili None ako pokretanje nema oba vremena."""

        if not pokretanje.started_at or not pokretanje.finished_at:
            return None
        from datetime import datetime

        try:
            pocetak = datetime.fromisoformat(pokretanje.started_at)
            kraj = datetime.fromisoformat(pokretanje.finished_at)
        except ValueError:
            return None
        return round((kraj - pocetak).total_seconds(), 1)

    def artifact_for(self, run_id: int) -> Path | None:
        """Putanja paketa jednog pokretanja, ili None ako ga nema."""

        putanja = artifacts.artifact_path(self._artifacts_dir, run_id)
        return putanja if putanja.is_file() else None

    def _spakuj_artefakt(self, pokretanje: PipelineRun) -> None:
        """Pakuje ono sto je definicija oznacila kao artefakt.

        Neuspeh pakovanja NE obara pokretanje — koraci su stvarno prosli.
        Ostaje trag u dnevniku, a pokretanje jednostavno nema sta da isporuci.
        """

        pipeline = self._pipelines.get(pokretanje.pipeline_id)
        if pipeline is None:
            return
        try:
            koren = self._koren(pipeline.repository_id, mora_da_postoji=True)
            definicija = parse(pipeline.definition, root=koren)
        except (PipelineError, ValueError) as greska:
            self._trag("system", "pipeline.artifact", f"run:{pokretanje.id}",
                       ALLOW, "failed", str(greska))
            return

        if definicija.artifact is None or koren is None:
            return

        try:
            artifacts.pack(
                run_id=pokretanje.id,
                source=koren / definicija.artifact.path,
                artifacts_dir=self._artifacts_dir,
            )
        except (artifacts.ArtifactError, OSError) as greska:
            self._trag("system", "pipeline.artifact", f"run:{pokretanje.id}",
                       ALLOW, "failed", str(greska))
            return

        self._trag("system", "pipeline.artifact", f"run:{pokretanje.id}",
                   ALLOW, "ok", definicija.artifact.path)

    # ----------          POMOCNO          ----------

    def _nadji(self, pipeline_id: int) -> Pipeline:
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            raise PipelineNotFound(f"Pipeline {pipeline_id} ne postoji.")
        return pipeline

    def _nadji_pokretanje(self, run_id: int) -> PipelineRun:
        pokretanje = self._runs.get(run_id)
        if pokretanje is None:
            raise RunNotFound(f"Pokretanje {run_id} ne postoji.")
        return pokretanje

    def _koren(self, repository_id: int, *, mora_da_postoji: bool) -> Path | None:
        repo = self._repositories.get(repository_id)
        if repo is None:
            raise RepositoryMissing(f"Repozitorijum {repository_id} ne postoji.")
        koren = Path(repo.local_path)
        if koren.is_dir():
            return koren
        if mora_da_postoji:
            raise RepositoryMissing(
                f"Putanja repozitorijuma vise ne postoji: {repo.local_path}",
            )
        # Snimanje definicije sme i kad koren trenutno nije dostupan;
        # tada se `working_dir` ne proverava.
        return None

    def _trag(self, actor: str, action: str, target: str, verdict: str,
              outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=verdict,
            outcome=outcome, detail=detail,
        ))


class PruningRunStore:
    """`RunStore` koji posle kraja pokretanja preda rec servisu.

    Kraj pokretanja zna motor, a pakovanje artefakta i zadrzavanje su posao
    servisa. Ovaj omotac spaja to dvoje, bez rasporedjivaca i bez posla pri
    startu. `on_finished` prima i status, jer se artefakt pakuje samo posle
    uspeha — bez statusa bi omotac morao ponovo da cita red iz baze.
    """

    def __init__(self, runs: RunRepository, on_finished) -> None:
        self._runs = runs
        self._on_finished = on_finished

    def mark_run_started(self, run_id: int) -> None:
        self._runs.mark_run_started(run_id)

    def mark_run_finished(self, run_id: int, status: str,
                          exit_code: int | None, detail: str = "") -> None:
        self._runs.mark_run_finished(run_id, status, exit_code, detail)
        self._on_finished(run_id, status)

    def mark_step_started(self, run_id: int, idx: int) -> None:
        self._runs.mark_step_started(run_id, idx)

    def mark_step_finished(self, run_id: int, idx: int, status: str,
                           exit_code: int | None = None) -> None:
        self._runs.mark_step_finished(run_id, idx, status, exit_code)
