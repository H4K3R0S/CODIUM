# ========== SEME: AUTOMATIZACIJA (CODIUM) ==========
from __future__ import annotations

from pydantic import BaseModel


class ActionPayload(BaseModel):
    """Jedna akcija u pravilu, sa svojim parametrima."""

    name: str
    params: dict = {}


class RuleCreateRequest(BaseModel):
    name: str
    event: str
    condition_expr: str = ""
    actions: list[ActionPayload] = []
    project_id: int | None = None
    enabled: bool = True
    rate_limit_n: int = 5
    rate_limit_seconds: int = 600


class RuleUpdateRequest(BaseModel):
    """Menja se sve osim dogadjaja.

    Pravilo koje promeni dogadjaj vise nije isto pravilo, a njegova istorija
    okidanja opisivala bi nesto drugo.
    """

    name: str
    condition_expr: str = ""
    actions: list[ActionPayload] = []
    enabled: bool = True
    rate_limit_n: int = 5
    rate_limit_seconds: int = 600


class RuleResponse(BaseModel):
    id: int
    name: str
    event: str
    condition_expr: str = ""
    actions: list[ActionPayload] = []
    project_id: int | None = None
    enabled: bool = True
    rate_limit_n: int = 5
    rate_limit_seconds: int = 600
    created_at: str = ""
    updated_at: str = ""
    # Popunjava router iz istorije okidanja — ekran ga pokazuje uz pravilo.
    last_run_at: str | None = None


class RulesResponse(BaseModel):
    rules: list[RuleResponse]


class RuleDeletedResponse(BaseModel):
    deleted: bool = True


class EventSpecResponse(BaseModel):
    name: str
    fields: list[str]


class EventsResponse(BaseModel):
    events: list[EventSpecResponse]


class ActionSpecResponse(BaseModel):
    name: str
    label: str
    description: str
    requires_approval: bool
    scope_action: str = ""
    params: list[str] = []


class ActionsResponse(BaseModel):
    actions: list[ActionSpecResponse]


class TestRequest(BaseModel):
    """Izmisljen dogadjaj nad kojim se pravilo proba."""

    payload: dict = {}


class TestResponse(BaseModel):
    """Ishod probe. Akcije NISU izvrsene."""

    matched: bool
    reason: str
    would_run: list[str] = []


class AutomationRunResponse(BaseModel):
    id: int
    rule_id: int
    event_json: str = "{}"
    matched: bool = True
    status: str
    detail: str = ""
    at: str = ""


class AutomationRunsResponse(BaseModel):
    runs: list[AutomationRunResponse]
