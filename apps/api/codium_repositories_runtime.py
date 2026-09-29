# ========== RUNTIME REPOZITORIJUMA ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak.
# Testovi ga menjaju kroz `app.dependency_overrides`, ne kroz ovaj modul.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.repositories.providers.local_git import LocalGitProvider
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.repositories.service import RepositoryService
from core.domains.codium.repository import CodiumRepository
from core.domains.codium.runtime import codium_database_path

_service: RepositoryService | None = None


def _database_path() -> Path:
    """Poslovna baza. Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def get_service() -> RepositoryService:
    global _service
    if _service is None:
        baza = _database_path()
        _service = RepositoryService(
            repos=RepositoryRepository(baza),
            provider=LocalGitProvider(),
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            projects=CodiumRepository(baza),
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
