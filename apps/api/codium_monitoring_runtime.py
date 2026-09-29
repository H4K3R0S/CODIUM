# ========== RUNTIME MERENJA ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak. Ovde stoji
# i sakupljac: pozadinski zadatak mora da bude JEDAN po procesu, inace bi dva
# merila isto i pisala duple uzorke.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_infrastructure_runtime, codium_security_runtime
from core.domains.codium.monitoring.collector import MetricCollector
from core.domains.codium.monitoring.repository import (
    AlertRepository,
    AlertRuleRepository,
    SampleRepository,
)
from core.domains.codium.monitoring.service import MonitoringService
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.system.file_monitor.scan_notification import (
    NullNotifier,
    OsToastNotifier,
)

_service: MonitoringService | None = None
_collector: MetricCollector | None = None


def _database_path() -> Path:
    return codium_database_path()


def _ops_database_path() -> Path:
    return codium_ops_database_path()


def get_service() -> MonitoringService:
    global _service
    if _service is None:
        poslovna = _database_path()
        operativna = _ops_database_path()
        _service = MonitoringService(
            samples=SampleRepository(operativna),
            rules=AlertRuleRepository(poslovna),
            alerts=AlertRepository(poslovna),
            infrastructure=codium_infrastructure_runtime.get_service(),
            audit=codium_security_runtime.get_audit(),
            # Alarm koji niko ne vidi nije alarm — ide u OS notifikaciju, kao
            # i obavestenja o diskovima. Bez backend-a degradira u tisinu.
            notifier=_notifier(),
        )
    return _service


def _notifier():
    try:
        return OsToastNotifier()
    except Exception:  # noqa: BLE001 - odsustvo toast-a nije razlog za pad
        return NullNotifier()


def get_collector() -> MetricCollector:
    """Pozadinski sakupljac. Pravi se pri prvom trazenju, ne pri uvozu."""

    global _collector
    if _collector is None:
        servis = get_service()
        _collector = MetricCollector(
            collect=servis.collect_once,
            maintain=servis.maintain,
            on_error=lambda greska: print(
                f"CORE upozorenje: krug merenja nije uspeo: {greska}"),
        )
    return _collector


def reset() -> None:
    """Zaboravi napravljene primerke (koristi se u testovima)."""
    global _service, _collector
    _service = None
    _collector = None
