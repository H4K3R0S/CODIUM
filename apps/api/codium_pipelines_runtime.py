# ========== RUNTIME PIPELINE-A ==========
# `PipelineRunner` je JEDAN primerak po procesu: pokretanja koja traju zive
# u njemu, pa ga `reset()` iz testa ne sme uzeti olako.
from __future__ import annotations

import asyncio
from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.pipelines.log_repository import RunLogRepository
from core.domains.codium.pipelines.repository import PipelineRepository, RunRepository
from core.domains.codium.pipelines.runner import PipelineRunner
from core.domains.codium.pipelines.service import PipelineService, PruningRunStore
from core.domains.codium.pipelines.sinks import BatchingLogSink
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)

_service: PipelineService | None = None
# Petlja API procesa, upamcena za runner nastao PRE nje ili posle nje — vidi
# `bind_loop`.
_bound_loop: asyncio.AbstractEventLoop | None = None


def _database_path() -> Path:
    return codium_database_path()


def _ops_database_path() -> Path:
    return codium_ops_database_path()


def get_service() -> PipelineService:
    global _service
    if _service is None:
        poslovna = _database_path()
        operativna = _ops_database_path()
        runs = RunRepository(poslovna)
        logovi = RunLogRepository(operativna)

        def posle_kraja(run_id: int, status: str) -> None:
            """Pakovanje artefakta i zadrzavanje, cim pokretanje zavrsi."""
            if _service is not None:
                _service.after_run_finished(run_id, status)

        _service = PipelineService(
            pipelines=PipelineRepository(poslovna),
            runs=runs,
            logs=logovi,
            runner=PipelineRunner(PruningRunStore(runs, posle_kraja),
                                  BatchingLogSink(logovi)),
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            repositories=RepositoryRepository(poslovna),
        )
        if _bound_loop is not None:
            _service.bind_loop(_bound_loop)
    return _service


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Upamti petlju API procesa da nit agenta moze da zakaze pokretanje na nju.

    Namerno NE pravi servis kao nusprodukt: `get_service()` inace dotakne
    pravu bazu (zato i postoji `PYTEST_CURRENT_TEST` straza u
    `_recover_stale_pipeline_runs`), a samo pamcenje petlje tu bazu ne dira.
    Ako servis vec postoji, petlja se odmah prosledi njegovom runner-u; ako
    ne, ceka u `_bound_loop` i primeni se cim `get_service()` napravi servis.
    """

    global _bound_loop
    _bound_loop = loop
    if _service is not None:
        _service.bind_loop(loop)


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service, _bound_loop
    _service = None
    _bound_loop = None
