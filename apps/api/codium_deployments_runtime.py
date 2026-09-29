# ========== RUNTIME ISPORUKE ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak.
# Testovi ga menjaju kroz `app.dependency_overrides`, ne kroz ovaj modul.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.deployments.models import DeployKind
from core.domains.codium.deployments.providers.local_docker import (
    LocalDockerProvider,
)
from core.domains.codium.deployments.providers.local_folder import (
    LocalFolderProvider,
)
from core.domains.codium.deployments.repository import (
    DeploymentRepository,
    DeployTargetRepository,
)
from core.domains.codium.deployments.service import DeploymentService
from core.domains.codium.paths import codium_paths
from core.domains.codium.pipelines.repository import RunRepository
from core.domains.codium.runtime import codium_database_path

_service: DeploymentService | None = None


def _database_path() -> Path:
    """Poslovna baza. Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def get_service() -> DeploymentService:
    global _service
    if _service is None:
        baza = _database_path()
        _service = DeploymentService(
            targets=DeployTargetRepository(baza),
            deployments=DeploymentRepository(baza),
            # `ssh_host` stoji u `DeployKind` ali nema provajdera u ovoj
            # verziji — servis ga odbija urednom greskom, ne KeyError-om.
            providers={
                DeployKind.LOCAL_FOLDER: LocalFolderProvider(),
                DeployKind.LOCAL_DOCKER: LocalDockerProvider(),
            },
            runs=RunRepository(baza),
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            approvals=codium_security_runtime.get_approvals(),
            artifacts_dir=codium_paths.artifacts,
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
