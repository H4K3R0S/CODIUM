# ========== SEME: MERENJE (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class ServiceOverviewResponse(BaseModel):
    """Poslednje poznato stanje jednog servisa, u jednom redu.

    Racuna se na serveru: racunati dostupnost u pregledacu znacilo bi poslati
    mu sve uzorke iz 24 sata.
    """

    service_id: int
    name: str
    kind: str
    state: str
    up: float | None = None
    latency_ms: float | None = None
    cpu_percent: float | None = None
    memory_mb: float | None = None
    uptime_24h: float | None = None
    firing_alerts: int = 0


class OverviewResponse(BaseModel):
    services: list[ServiceOverviewResponse]


class SeriesPointResponse(BaseModel):
    bucket: str
    value: float
    samples: int


class SeriesResponse(BaseModel):
    """Vec sazete kante — GUI ne dobija hiljade tacaka za grafikon od 400px."""

    service_id: int
    metric: str
    bucket: str
    points: list[SeriesPointResponse]


class AlertRuleCreateRequest(BaseModel):
    service_id: int
    metric: str
    comparison: str
    threshold: float
    for_samples: int = 2
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    """Menja se prag i uslov — ne i metrika ili servis.

    Pravilo koje promeni metriku vise nije isto pravilo, a alarmi vezani za
    njega opisivali bi merenje koje se vise ne radi.
    """

    comparison: str
    threshold: float
    for_samples: int = 2
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    id: int
    service_id: int | None = None
    metric: str
    comparison: str
    threshold: float
    for_samples: int
    enabled: bool
    created_at: str = ""


class AlertRulesResponse(BaseModel):
    rules: list[AlertRuleResponse]


class RuleDeletedResponse(BaseModel):
    deleted: bool = True


class AlertResponse(BaseModel):
    id: int
    rule_id: int
    state: str
    value: float | None = None
    started_at: str = ""
    resolved_at: str | None = None


class AlertsResponse(BaseModel):
    alerts: list[AlertResponse]


class CollectResponse(BaseModel):
    """Ishod rucnog merenja — za proveru pravila, bez cekanja na sakupljac."""

    samples: int
