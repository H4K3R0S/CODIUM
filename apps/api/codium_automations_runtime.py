# ========== RUNTIME AUTOMATIZACIJE ==========
# Servis mora da bude JEDAN po procesu: on je pretplatnik na razglas, pa bi
# drugi primerak znacio da se svako pravilo upali dvaput.
from __future__ import annotations

from pathlib import Path

from apps.api import (
    codium_deployments_runtime,
    codium_infrastructure_runtime,
    codium_pipelines_runtime,
    codium_security_runtime,
)
from core.domains.codium.automations.actions import ActionContext
from core.domains.codium.automations.repository import (
    AutomationRunRepository,
    RuleRepository,
)
from core.domains.codium.automations.service import AutomationService
from core.domains.codium.runtime import codium_database_path
from core.foundation.paths import core_paths
from core.system.file_monitor.scan_notification import (
    NullNotifier,
    OsToastNotifier,
)

_service: AutomationService | None = None


def _database_path() -> Path:
    return codium_database_path()


def _notifier():
    try:
        return OsToastNotifier()
    except Exception:  # noqa: BLE001 - odsustvo toast-a nije razlog za pad
        return NullNotifier()


def get_service() -> AutomationService:
    global _service
    if _service is None:
        baza = _database_path()
        _service = AutomationService(
            rules=RuleRepository(baza),
            runs=AutomationRunRepository(baza),
            audit=codium_security_runtime.get_audit(),
            context=ActionContext(
                notifier=_notifier(),
                codium=_codium_service(),
                pipelines=codium_pipelines_runtime.get_service(),
                deployments=codium_deployments_runtime.get_service(),
                infrastructure=codium_infrastructure_runtime.get_service(),
                # Agenti se namerno ne vezuju u ovom rezu — vidi
                # `20-E10-automations.md` i dnevnicki unos.
                agents=None,
                dev_log_dir=core_paths.root / ".ai" / "dev-log" / "entries",
            ),
        )
    return _service


def _codium_service():
    """CODIUM servis (beleske, taskovi).

    Pravi se ovde jer sam `CodiumService` nema svoj runtime modul — router ga
    sklapa po zahtevu (`CodiumService(CodiumRepository())`). Automatizacija ga
    drzi jedan, uz ostale servise.
    """

    from core.domains.codium.repository import CodiumRepository
    from core.domains.codium.service import CodiumService

    return CodiumService(CodiumRepository(_database_path()))


def subscribe() -> None:
    """Vezuje servis na razglas. Poziva se jednom, pri startu API-ja."""

    get_service().subscribe()


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    if _service is not None:
        _service.unsubscribe()
    _service = None
