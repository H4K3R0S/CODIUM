# ========== ROUTER: DNEVNIK I PRAVILA DOZVOLA (CODIUM) ==========
# Dnevnik ima samo citanje. Ne postoji ruta koja menja ili brise postojeci
# unos — to je poenta dnevnika, ne propust.
from __future__ import annotations

import json
import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas.codium_audit import (
    ActivityItemResponse,
    ActivityResponse,
    ApprovalDecisionRequest,
    ApprovalResponse,
    ApprovalsResponse,
    AuditEntryResponse,
    AuditLogResponse,
    ScopeRuleDeletedResponse,
    ScopeRuleRequest,
    ScopeRuleResponse,
    ScopeRulesResponse,
)
from core.domains.codium.agents import Agent, AgentRepository, AgentRun, RunRepository
from core.domains.codium.audit import (
    ActivityFeed,
    ApprovalRepository,
    AuditEntry,
    AuditRepository,
    ScopeRuleRepository,
)
from core.security.scope_gate import ScopeRule

router = APIRouter(
    prefix="/api/v1/codium/audit",
    tags=["CODIUM Dnevnik"],
)

_logger = logging.getLogger(__name__)


def get_audit() -> AuditRepository:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_audit()


def get_scope_rules() -> ScopeRuleRepository:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_scope_rules()


def get_activity_feed() -> ActivityFeed:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_activity_feed()


def get_approvals() -> ApprovalRepository:
    from apps.api import codium_security_runtime
    return codium_security_runtime.get_approvals()


# Odluka o molbi mora da nastavi pauziran posao agenta — ali dnevnik ne sme
# da zavisi od agentske masinerije pri ucitavanju modula (ona vuce
# provajdere modela i slicno). Uvoz `codium_agents_runtime` je zato unutar
# svake od ove tri funkcije, ne na vrhu fajla — dogadja se tek kad ruta
# stvarno treba nastavak, ne kad se modul ucita.

def get_agent_runs() -> RunRepository:
    from apps.api import codium_agents_runtime
    return codium_agents_runtime.get_runs()


def get_agent_repo() -> AgentRepository:
    from apps.api import codium_agents_runtime
    return codium_agents_runtime.get_agents()


ResumeHook = Callable[[Agent, AgentRun], None]


def get_resume_hook() -> ResumeHook:
    """Podrazumevani nastavak posla — pravi pokretac agenata, u novoj niti."""

    def _nastavi(agent: Agent, run: AgentRun) -> None:
        from apps.api import codium_agents_runtime
        codium_agents_runtime.get_runner().resume(agent, run)

    return _nastavi


# ==========          DNEVNIK          ==========

@router.get("/log", response_model=AuditLogResponse)
def get_log(
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    audit: AuditRepository = Depends(get_audit),
) -> AuditLogResponse:
    """Filtriran i straničen dnevnik akcija, najnovije prvo."""

    entries = audit.query(actor=actor, action=action, limit=limit, offset=offset)
    return AuditLogResponse(
        count=len(entries),
        entries=[AuditEntryResponse.from_domain(e) for e in entries],
    )


# ==========          PRAVILA DOZVOLA          ==========

@router.get("/rules", response_model=ScopeRulesResponse)
def list_rules(
    rules: ScopeRuleRepository = Depends(get_scope_rules),
) -> ScopeRulesResponse:
    """Pravila koja odlučuju šta akter sme."""

    svi = rules.list()
    return ScopeRulesResponse(
        count=len(svi),
        rules=[ScopeRuleResponse.from_domain(r) for r in svi],
    )


@router.post("/rules", response_model=ScopeRuleResponse)
def add_rule(
    payload: ScopeRuleRequest,
    rules: ScopeRuleRepository = Depends(get_scope_rules),
) -> ScopeRuleResponse:
    """Novo pravilo. Važi odmah — gate čita pravila u trenutku provere."""

    upisano = rules.add(ScopeRule(
        actor=payload.actor, action=payload.action, target=payload.target,
        verdict=payload.verdict, note=payload.note,
    ))
    return ScopeRuleResponse.from_domain(upisano)


@router.delete("/rules/{rule_id}", response_model=ScopeRuleDeletedResponse)
def delete_rule(
    rule_id: int,
    rules: ScopeRuleRepository = Depends(get_scope_rules),
) -> ScopeRuleDeletedResponse:
    """Briše pravilo. Brisanje nepostojećeg nije greška — ishod je isti."""

    rules.delete(rule_id)
    return ScopeRuleDeletedResponse(ok=True, id=rule_id)


# ==========          VREMENSKA LINIJA          ==========

@router.get("/activity", response_model=ActivityResponse)
def get_activity(
    limit: int = Query(default=20, ge=1, le=100),
    feed: ActivityFeed = Depends(get_activity_feed),
) -> ActivityResponse:
    """Poslednja dešavanja: odbijene akcije i pozivi modela, u jednoj liniji."""

    items = feed.recent(limit=limit)
    return ActivityResponse(
        count=len(items),
        items=[ActivityItemResponse.from_domain(i) for i in items],
    )


# ==========          ODOBRENJA          ==========

@router.get("/approvals", response_model=ApprovalsResponse)
def list_approvals(
    approvals: ApprovalRepository = Depends(get_approvals),
) -> ApprovalsResponse:
    """Molbe koje čekaju odluku, najnovija prva."""

    ceka = approvals.pending()
    return ApprovalsResponse(
        count=len(ceka),
        approvals=[ApprovalResponse.from_domain(a) for a in ceka],
    )


def _approval_content_hash(payload: str) -> str | None:
    """Vadi `content_hash` iz payload-a molbe, ako postoji.

    Payload je tekst iz baze i ne mora biti ispravan JSON — malformisan
    payload ne sme da obori odluku koja je vec prosla, samo ostaje bez
    otiska u detalju dnevnika.
    """

    try:
        podaci = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(podaci, dict):
        return None
    otisak = podaci.get("content_hash")
    return otisak if isinstance(otisak, str) else None


def _decide(approval_id: int, status: str, note: str,
            approvals: ApprovalRepository,
            audit: AuditRepository,
            agent_runs: RunRepository,
            agent_repo: AgentRepository,
            resume: ResumeHook) -> ApprovalResponse:
    """Zajedničko telo za odobri i odbij — razlikuje ih samo status."""

    odluceno = approvals.decide(approval_id, status, note)
    if odluceno is None:
        # Molba ne postoji ili je vec odlucena. Oba su sukob sa stanjem, ne
        # greska poziva: klijent je gledao zastareo spisak.
        raise HTTPException(status_code=409,
                            detail="Molba ne čeka odluku.")

    detalj = f"{status}: {odluceno.action} {odluceno.target}"
    if note:
        detalj += f" — napomena: {note}"
    otisak = _approval_content_hash(odluceno.payload)
    if otisak:
        detalj += f" — otisak sadržaja: {otisak}"

    try:
        audit.record(AuditEntry(
            actor="human", action="approval.decide",
            target=f"approval:{approval_id}", verdict="allow",
            outcome="ok", detail=detalj,
        ))
    except Exception:
        # Odluka je vec upisana u `codium_approvals` — ovaj upad ne sme da
        # javi klijentu da odluka nije prosla kad zapravo jeste. Gubitak
        # traga u dnevniku ostaje vidljiv samo ovde, u logu servera.
        _logger.warning(
            "Upis u dnevnik nije uspeo za odluku o molbi %s (status=%s); "
            "odluka je ipak upisana.", approval_id, status, exc_info=True,
        )

    try:
        posao = agent_runs.by_pending_approval(approval_id)
        if posao is not None:
            agent = agent_repo.get(posao.agent_id)
            if agent is not None:
                resume(agent, posao)
    except Exception:
        # Isti razlog kao gore: odluka je vec upisana i vazi bez obzira na
        # to da li je nastavak posla uspeo da krene.
        _logger.warning(
            "Nastavak posla nije uspeo za odluku o molbi %s (status=%s); "
            "odluka je ipak upisana.", approval_id, status, exc_info=True,
        )

    return ApprovalResponse.from_domain(odluceno)


@router.post("/approvals/{approval_id}/approve",
             response_model=ApprovalResponse)
def approve(
    approval_id: int,
    payload: ApprovalDecisionRequest | None = None,
    approvals: ApprovalRepository = Depends(get_approvals),
    audit: AuditRepository = Depends(get_audit),
    agent_runs: RunRepository = Depends(get_agent_runs),
    agent_repo: AgentRepository = Depends(get_agent_repo),
    resume: ResumeHook = Depends(get_resume_hook),
) -> ApprovalResponse:
    """Odobrava tačno taj potez. Sledeći isti potez pita ponovo."""

    return _decide(approval_id, "approved",
                   payload.note if payload else "", approvals, audit,
                   agent_runs, agent_repo, resume)


@router.post("/approvals/{approval_id}/reject",
             response_model=ApprovalResponse)
def reject(
    approval_id: int,
    payload: ApprovalDecisionRequest | None = None,
    approvals: ApprovalRepository = Depends(get_approvals),
    audit: AuditRepository = Depends(get_audit),
    agent_runs: RunRepository = Depends(get_agent_runs),
    agent_repo: AgentRepository = Depends(get_agent_repo),
    resume: ResumeHook = Depends(get_resume_hook),
) -> ApprovalResponse:
    """Odbija potez uz razlog koji ostaje zapisan."""

    return _decide(approval_id, "rejected",
                   payload.note if payload else "", approvals, audit,
                   agent_runs, agent_repo, resume)
