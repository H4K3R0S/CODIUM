# ========== ŠEME: dnevnik i pravila dozvola ==========
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.domains.codium.audit import ActivityItem, Approval, AuditEntry
from core.security.scope_gate import ScopeRule

# ==========          DNEVNIK          ==========

class AuditEntryResponse(BaseModel):
    id: int | None
    at: str
    actor: str
    action: str
    target: str
    verdict: str
    outcome: str
    detail: str
    project_id: int | None

    @classmethod
    def from_domain(cls, entry: AuditEntry) -> AuditEntryResponse:
        return cls(
            id=entry.id, at=entry.at, actor=entry.actor, action=entry.action,
            target=entry.target, verdict=entry.verdict, outcome=entry.outcome,
            detail=entry.detail, project_id=entry.project_id,
        )


class AuditLogResponse(BaseModel):
    count: int
    entries: list[AuditEntryResponse]


# ==========          PRAVILA DOZVOLA          ==========

class ScopeRuleResponse(BaseModel):
    id: int | None
    actor: str
    action: str
    target: str
    verdict: str
    note: str

    @classmethod
    def from_domain(cls, rule: ScopeRule) -> ScopeRuleResponse:
        return cls(
            id=rule.id, actor=rule.actor, action=rule.action,
            target=rule.target, verdict=rule.verdict, note=rule.note,
        )


class ScopeRulesResponse(BaseModel):
    count: int
    rules: list[ScopeRuleResponse]


class ScopeRuleRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    target: str = "*"
    # Skup vrednosti stoji i u šemi baze; ovde puca ranije i sa jasnijom
    # porukom, pre nego što upit uopšte krene.
    verdict: Literal["allow", "deny", "needs_approval"]
    note: str = ""


class ScopeRuleDeletedResponse(BaseModel):
    ok: bool
    id: int


# ==========          VREMENSKA LINIJA          ==========

class ActivityItemResponse(BaseModel):
    at: str
    kind: str
    title: str
    meta: str
    outcome: str
    verdict: str
    project_id: int | None
    cost_usd: float

    @classmethod
    def from_domain(cls, item: ActivityItem) -> ActivityItemResponse:
        return cls(
            at=item.at, kind=item.kind, title=item.title, meta=item.meta,
            outcome=item.outcome, verdict=item.verdict,
            project_id=item.project_id, cost_usd=item.cost_usd,
        )


class ActivityResponse(BaseModel):
    count: int
    items: list[ActivityItemResponse]


# ==========          ODOBRENJA          ==========

class ApprovalResponse(BaseModel):
    id: int
    actor: str
    action: str
    target: str
    payload: str
    status: str
    note: str
    requested_at: str
    decided_at: str | None

    @classmethod
    def from_domain(cls, approval: Approval) -> ApprovalResponse:
        return cls(
            id=approval.id, actor=approval.actor, action=approval.action,
            target=approval.target, payload=approval.payload,
            status=approval.status, note=approval.note,
            requested_at=approval.requested_at, decided_at=approval.decided_at,
        )


class ApprovalsResponse(BaseModel):
    count: int
    approvals: list[ApprovalResponse]


class ApprovalDecisionRequest(BaseModel):
    note: str = ""
