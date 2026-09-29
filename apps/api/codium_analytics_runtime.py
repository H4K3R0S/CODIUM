# ========== RUNTIME IZVESTAJA ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak. Ovde je i
# jedini kes izvestaja: dva primerka bi znacila dva kesa, pa bi „osvezi" na
# ekranu ponekad vratio stari broj.
from __future__ import annotations

from pathlib import Path

from core.domains.codium.analytics.service import AnalyticsService
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)

_service: AnalyticsService | None = None


def _database_path() -> Path:
    return codium_database_path()


def _ops_database_path() -> Path:
    return codium_ops_database_path()


def get_service() -> AnalyticsService:
    global _service
    if _service is None:
        _service = AnalyticsService(
            database_path=_database_path(),
            ops_database_path=_ops_database_path(),
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
