# ========== ROUTER: MERENJE (CODIUM) ==========
# Rute nose `actor="human"`. `/series` uvek vraca vec sazete kante — sirovi
# uzorci za sedam dana su desetine hiljada redova koje grafikon ne ume da
# nacrta ni da iskoristi.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_monitoring import (
    AlertResponse,
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AlertRulesResponse,
    AlertRuleUpdateRequest,
    AlertsResponse,
    CollectResponse,
    OverviewResponse,
    RuleDeletedResponse,
    SeriesPointResponse,
    SeriesResponse,
    ServiceOverviewResponse,
)
from core.domains.codium.monitoring.models import AlertRule
from core.domains.codium.monitoring.service import (
    MonitoringError,
    MonitoringService,
    RuleNotFound,
)

router = APIRouter(
    prefix="/api/v1/codium/monitoring",
    tags=["CODIUM Merenje"],
)

COVEK = "human"

# Kanta se bira po duzini perioda, ne po zelji pozivaoca: dan u minutnim
# kantama je 1440 tacaka, a nijedan grafikon toliko ne prikazuje.
KANTE = ("minute", "5min", "hour", "day")


def get_service() -> MonitoringService:
    from apps.api import codium_monitoring_runtime
    return codium_monitoring_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, RuleNotFound):
        return HTTPException(status_code=404, detail=str(greska))
    if isinstance(greska, (MonitoringError, ValueError)):
        return HTTPException(status_code=400, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _pravilo_u_odgovor(pravilo) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=pravilo.id, service_id=pravilo.service_id, metric=str(pravilo.metric),
        comparison=str(pravilo.comparison), threshold=pravilo.threshold,
        for_samples=pravilo.for_samples, enabled=pravilo.enabled,
        created_at=pravilo.created_at,
    )


def _alarm_u_odgovor(alarm) -> AlertResponse:
    return AlertResponse(
        id=alarm.id, rule_id=alarm.rule_id, state=str(alarm.state),
        value=alarm.value, started_at=alarm.started_at,
        resolved_at=alarm.resolved_at,
    )


# ----------          PREGLED          ----------

@router.get("/overview", response_model=OverviewResponse)
def pregled(servis: MonitoringService = Depends(get_service)) -> OverviewResponse:
    return OverviewResponse(services=[
        ServiceOverviewResponse(
            service_id=s.service_id, name=s.name, kind=s.kind, state=s.state,
            up=s.up, latency_ms=s.latency_ms, cpu_percent=s.cpu_percent,
            memory_mb=s.memory_mb, uptime_24h=s.uptime_24h,
            firing_alerts=s.firing_alerts,
        )
        for s in servis.overview()
    ])


@router.get("/series", response_model=SeriesResponse)
def red(service_id: int = Query(...), metric: str = Query(...),
        bucket: str = Query(default="hour"),
        since: str | None = Query(default=None),
        until: str | None = Query(default=None),
        limit: int = Query(default=500, ge=1, le=2000),
        servis: MonitoringService = Depends(get_service)) -> SeriesResponse:
    if bucket not in KANTE:
        raise HTTPException(
            status_code=400,
            detail=f"Nepoznata velicina kante: {bucket}. "
                   f"Dozvoljeno: {', '.join(KANTE)}.")
    try:
        tacke = servis.series(service_id=service_id, metric=metric,
                              bucket=bucket, since=since, until=until,
                              limit=limit)
    except Exception as greska:
        raise _prevedi(greska) from greska

    return SeriesResponse(
        service_id=service_id, metric=metric, bucket=bucket,
        points=[SeriesPointResponse(bucket=t.bucket, value=t.value,
                                    samples=t.samples) for t in tacke],
    )


@router.post("/collect", response_model=CollectResponse)
def izmeri(servis: MonitoringService = Depends(get_service)) -> CollectResponse:
    """Rucno merenje odmah — za proveru pravila, bez cekanja na sakupljac."""

    try:
        return CollectResponse(samples=servis.collect_once())
    except Exception as greska:
        raise _prevedi(greska) from greska


# ----------          PRAVILA          ----------

@router.get("/rules", response_model=AlertRulesResponse)
def pravila(service_id: int | None = Query(default=None),
            servis: MonitoringService = Depends(get_service),
            ) -> AlertRulesResponse:
    return AlertRulesResponse(rules=[
        _pravilo_u_odgovor(p) for p in servis.rules(service_id)
    ])


@router.post("/rules", response_model=AlertRuleResponse)
def novo_pravilo(zahtev: AlertRuleCreateRequest,
                 servis: MonitoringService = Depends(get_service),
                 ) -> AlertRuleResponse:
    try:
        return _pravilo_u_odgovor(servis.create_rule(
            AlertRule(service_id=zahtev.service_id, metric=zahtev.metric,
                      comparison=zahtev.comparison, threshold=zahtev.threshold,
                      for_samples=zahtev.for_samples, enabled=zahtev.enabled),
            actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
def izmeni_pravilo(rule_id: int, zahtev: AlertRuleUpdateRequest,
                   servis: MonitoringService = Depends(get_service),
                   ) -> AlertRuleResponse:
    try:
        return _pravilo_u_odgovor(servis.update_rule(
            rule_id, comparison=zahtev.comparison, threshold=zahtev.threshold,
            for_samples=zahtev.for_samples, enabled=zahtev.enabled,
            actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.delete("/rules/{rule_id}", response_model=RuleDeletedResponse)
def obrisi_pravilo(rule_id: int,
                   servis: MonitoringService = Depends(get_service),
                   ) -> RuleDeletedResponse:
    try:
        servis.delete_rule(rule_id, actor=COVEK)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return RuleDeletedResponse()


# ----------          ALARMI          ----------

@router.get("/alerts", response_model=AlertsResponse)
def alarmi(state: str | None = Query(default=None),
           limit: int = Query(default=50, ge=1, le=500),
           servis: MonitoringService = Depends(get_service)) -> AlertsResponse:
    return AlertsResponse(alerts=[
        _alarm_u_odgovor(a) for a in servis.alerts(state, limit)
    ])
