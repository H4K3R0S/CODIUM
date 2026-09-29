# ========== ROUTER: AUTOMATIZACIJA (CODIUM) ==========
# Rute nose `actor="human"` — pravila pise covek. Samo okidanje ide pod
# akterom `automation:<id>`, i to iz servisa, ne odavde.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_automations import (
    ActionPayload,
    ActionSpecResponse,
    ActionsResponse,
    AutomationRunResponse,
    AutomationRunsResponse,
    EventSpecResponse,
    EventsResponse,
    RuleCreateRequest,
    RuleDeletedResponse,
    RuleResponse,
    RulesResponse,
    RuleUpdateRequest,
    TestRequest,
    TestResponse,
)
from core.domains.codium.automations.actions import UnknownAction
from core.domains.codium.automations.models import Action, Rule
from core.domains.codium.automations.service import (
    AutomationError,
    AutomationService,
    InvalidRule,
    RuleNotFound,
    dostupne_akcije,
    dostupni_dogadjaji,
)

router = APIRouter(
    prefix="/api/v1/codium/automations",
    tags=["CODIUM Automatizacija"],
)

COVEK = "human"


def get_service() -> AutomationService:
    from apps.api import codium_automations_runtime
    return codium_automations_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, RuleNotFound):
        return HTTPException(status_code=404, detail=str(greska))
    if isinstance(greska, (InvalidRule, UnknownAction, ValueError)):
        return HTTPException(status_code=400, detail=str(greska))
    if isinstance(greska, AutomationError):
        return HTTPException(status_code=409, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _u_odgovor(pravilo, last_run_at: str | None = None) -> RuleResponse:
    return RuleResponse(
        id=pravilo.id, name=pravilo.name, event=str(pravilo.event),
        condition_expr=pravilo.condition_expr,
        actions=[ActionPayload(name=str(a.name), params=a.params)
                 for a in pravilo.actions],
        project_id=pravilo.project_id, enabled=pravilo.enabled,
        rate_limit_n=pravilo.rate_limit_n,
        rate_limit_seconds=pravilo.rate_limit_seconds,
        created_at=pravilo.created_at, updated_at=pravilo.updated_at,
        last_run_at=last_run_at,
    )


def _akcije(payload: list[ActionPayload]) -> list[Action]:
    return [Action(name=a.name, params=a.params) for a in payload]


# ----------          SPISKOVI          ----------

@router.get("/events", response_model=EventsResponse)
def dogadjaji() -> EventsResponse:
    """Dogadjaji i polja koja nose.

    Ekran po ovome nudi polja za uslov, umesto da covek pogadja imena.
    """

    return EventsResponse(events=[
        EventSpecResponse(name=d["name"], fields=d["fields"])
        for d in dostupni_dogadjaji()
    ])


@router.get("/actions", response_model=ActionsResponse)
def akcije() -> ActionsResponse:
    """Akcije i dozvole koje traze."""

    return ActionsResponse(actions=[
        ActionSpecResponse(**a) for a in dostupne_akcije()
    ])


# ----------          PRAVILA          ----------

@router.get("/", response_model=RulesResponse)
def pravila(event: str | None = Query(default=None),
            servis: AutomationService = Depends(get_service)) -> RulesResponse:
    return RulesResponse(rules=[
        _u_odgovor(p, servis.last_run_at(p.id)) for p in servis.rules(event)
    ])


@router.post("/", response_model=RuleResponse)
def novo_pravilo(zahtev: RuleCreateRequest,
                 servis: AutomationService = Depends(get_service),
                 ) -> RuleResponse:
    try:
        return _u_odgovor(servis.create_rule(
            Rule(name=zahtev.name, event=zahtev.event,
                 condition_expr=zahtev.condition_expr,
                 actions=_akcije(zahtev.actions),
                 project_id=zahtev.project_id, enabled=zahtev.enabled,
                 rate_limit_n=zahtev.rate_limit_n,
                 rate_limit_seconds=zahtev.rate_limit_seconds),
            actor=COVEK,
        ))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.patch("/{rule_id}", response_model=RuleResponse)
def izmeni(rule_id: int, zahtev: RuleUpdateRequest,
           servis: AutomationService = Depends(get_service)) -> RuleResponse:
    try:
        izmenjeno = servis.update_rule(
            rule_id, name=zahtev.name, condition_expr=zahtev.condition_expr,
            actions=_akcije(zahtev.actions), enabled=zahtev.enabled,
            rate_limit_n=zahtev.rate_limit_n,
            rate_limit_seconds=zahtev.rate_limit_seconds, actor=COVEK,
        )
        return _u_odgovor(izmenjeno, servis.last_run_at(rule_id))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.delete("/{rule_id}", response_model=RuleDeletedResponse)
def obrisi(rule_id: int,
           servis: AutomationService = Depends(get_service),
           ) -> RuleDeletedResponse:
    try:
        servis.delete_rule(rule_id, actor=COVEK)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return RuleDeletedResponse()


# ----------          PROBA          ----------

@router.post("/{rule_id}/test", response_model=TestResponse)
def probaj(rule_id: int, zahtev: TestRequest,
           servis: AutomationService = Depends(get_service)) -> TestResponse:
    """Proba nad izmisljenim dogadjajem. **NE IZVRSAVA AKCIJE.**

    Postoji da se pravilo proveri bez posledica — pravilo koje isporucuje ne
    sme da se proverava isporukom.
    """

    try:
        ishod = servis.test(rule_id, zahtev.payload)
    except Exception as greska:
        raise _prevedi(greska) from greska
    return TestResponse(matched=ishod.matched, reason=ishod.reason,
                        would_run=ishod.would_run)


# ----------          ISTORIJA          ----------

@router.get("/runs", response_model=AutomationRunsResponse)
def okidanja(rule_id: int | None = Query(default=None),
             limit: int = Query(default=50, ge=1, le=500),
             servis: AutomationService = Depends(get_service),
             ) -> AutomationRunsResponse:
    return AutomationRunsResponse(runs=[
        AutomationRunResponse(
            id=r.id, rule_id=r.rule_id, event_json=r.event_json,
            matched=r.matched, status=str(r.status), detail=r.detail, at=r.at)
        for r in servis.runs(rule_id, limit)
    ])
