# ========== MODELI AUTOMATIZACIJE ==========
# Pravilo ima tri dela: KADA (dogadjaj), AKO (uslov), ONDA (akcije).
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EventName(StrEnum):
    """Dogadjaji koje podsistemi objavljuju.

    Imena su stabilna — pravila ih pamte kao tekst u bazi, pa preimenovanje
    tiho gasi svako pravilo koje je slusalo staro ime.
    """

    COMMIT_DETECTED = "repo.commit.detected"
    BRANCH_CHANGED = "repo.branch.changed"
    RUN_FINISHED = "pipeline.run.finished"
    DEPLOYMENT_FINISHED = "deployment.finished"
    SERVICE_STATE_CHANGED = "service.state.changed"
    ALERT_FIRED = "alert.fired"
    ALERT_RESOLVED = "alert.resolved"
    SCHEDULE_TICK = "schedule.tick"


# Koja polja koji dogadjaj nosi. Ekran po ovome nudi polja za uslov, umesto da
# covek pogadja imena; `/events` cita bas ovaj recnik.
POLJA_DOGADJAJA: dict[str, tuple[str, ...]] = {
    EventName.COMMIT_DETECTED: ("repository_id", "repository", "branch", "sha",
                                "author"),
    EventName.BRANCH_CHANGED: ("repository_id", "repository", "old_branch",
                               "new_branch"),
    EventName.RUN_FINISHED: ("run_id", "pipeline_id", "status", "exit_code",
                             "duration_seconds"),
    EventName.DEPLOYMENT_FINISHED: ("deployment_id", "target_id", "target",
                                    "status", "run_id"),
    EventName.SERVICE_STATE_CHANGED: ("service_id", "service", "old_state",
                                      "new_state"),
    EventName.ALERT_FIRED: ("alert_id", "rule_id", "service_id", "metric",
                            "value"),
    EventName.ALERT_RESOLVED: ("alert_id", "rule_id", "service_id", "metric"),
    EventName.SCHEDULE_TICK: ("cron", "at"),
}


class ActionName(StrEnum):
    """Sta pravilo sme da uradi."""

    NOTIFY = "notify"
    WRITE_NOTE = "write_note"
    WRITE_DEV_LOG = "write_dev_log"
    CREATE_TASK = "create_task"
    RUN_PIPELINE = "run_pipeline"
    DEPLOY = "deploy"
    RESTART_SERVICE = "restart_service"
    AGENT_ANALYZE = "agent_analyze"


class RunStatus(StrEnum):
    """Ishod jednog okidanja pravila.

    `SKIPPED` i `RATE_LIMITED` nisu isto: prvo znaci da uslov nije prosao
    (pravilo radi kako treba), drugo da je pravilo ugaseno jer se otelo.
    """

    DONE = "done"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


# Najveca dubina lanca: dogadjaj -> akcija -> dogadjaj -> ... Dalje se ne ide.
MAKS_DUBINA = 3


@dataclass(frozen=True)
class Event:
    """Jedan dogadjaj na razglasu.

    `origin` nosi poreklo: prazno za dogadjaj iz sveta, `automation:<id>` za
    onaj koji je proizvela akcija. Bez toga pravilo pali samo sebe.

    `depth` raste kroz lanac; na `MAKS_DUBINA` se prosledjivanje zaustavlja.
    """

    name: str
    payload: dict = field(default_factory=dict)
    origin: str = ""
    depth: int = 0


@dataclass(frozen=True)
class Action:
    """Jedna akcija u pravilu, sa svojim parametrima."""

    name: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    """Red iz `codium_automation_rules`."""

    name: str
    event: str
    condition_expr: str = ""
    actions: list[Action] = field(default_factory=list)
    project_id: int | None = None
    enabled: bool = True
    rate_limit_n: int = 5
    rate_limit_seconds: int = 600
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class AutomationRun:
    """Red iz `codium_automation_runs` — trag jednog okidanja."""

    rule_id: int
    event_json: str = "{}"
    matched: bool = True
    status: str = RunStatus.DONE
    detail: str = ""
    at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class ActionSpec:
    """Opis akcije: sta radi i da li trazi odobrenje.

    Ekran po ovome uz svaku akciju odmah pise da li trazi odobrenje — covek to
    vidi PRE nego sto snimi pravilo, ne tek kad se prvi put upali.
    """

    name: str
    label: str
    description: str
    # Glagol koji kapija proverava; prazno znaci da akcija ne dira sistem.
    scope_action: str = ""
    params: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestResult:
    """Ishod probe pravila nad izmisljenim dogadjajem. NISTA ne izvrsava."""

    matched: bool
    reason: str
    would_run: list[str] = field(default_factory=list)
