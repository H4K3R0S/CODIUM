# ========== MODELI MERENJA ==========
# Uzorak je jedna izmerena vrednost u jednom trenutku. Pravilo kaze sta se
# smatra kvarom, alarm je pravilo koje se upalilo.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Metric(StrEnum):
    """Sta se meri. Imena su stabilna — pravila ih pamte kao tekst."""

    UP = "up"
    LATENCY_MS = "latency_ms"
    CPU_PERCENT = "cpu_percent"
    MEMORY_MB = "memory_mb"
    HOST_CPU = "host_cpu"
    HOST_MEMORY = "host_memory"


class AlertState(StrEnum):
    """Stanje alarma.

    `OK` ne postoji kao red u bazi — alarm se upisuje tek kad se upali. Stoji
    u nabrajanju jer ga ocena pravila vraca kao „nema sta da se pali".
    """

    OK = "ok"
    FIRING = "firing"
    RESOLVED = "resolved"


class Comparison(StrEnum):
    """Kako se izmerena vrednost poredi sa pragom."""

    LT = "<"
    GT = ">"
    EQ = "=="


@dataclass(frozen=True)
class MetricSample:
    """Red iz `codium_metric_samples`."""

    metric: str
    value: float
    service_id: int | None = None
    node_id: int | None = None
    at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class ProbeResult:
    """Sta je jedna proba izmerila.

    Nosi vise uzoraka jer jedna proba cesto meri vise stvari odjednom: HTTP
    proba zna i da li odgovara i koliko je cekala.
    """

    samples: list[MetricSample] = field(default_factory=list)
    detail: str = ""


@dataclass(frozen=True)
class AlertRule:
    """Red iz `codium_alert_rules`.

    `for_samples` postoji da jedan promasen uzorak ne pali alarm — mreza
    zatreperi, servis ne padne.
    """

    metric: str
    comparison: str
    threshold: float
    service_id: int | None = None
    for_samples: int = 2
    enabled: bool = True
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Alert:
    """Red iz `codium_alerts`."""

    rule_id: int
    state: str = AlertState.FIRING
    value: float | None = None
    started_at: str = ""
    resolved_at: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class SeriesPoint:
    """Jedna kanta vremenskog reda.

    Grafikon od 400 piksela ne treba hiljadu tacaka, pa se uzorci sazimaju u
    kante jos u SQL-u — GUI dobija ono sto ume da nacrta.
    """

    bucket: str
    value: float
    samples: int
