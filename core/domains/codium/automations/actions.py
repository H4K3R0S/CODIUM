# ========== AKCIJE AUTOMATIZACIJE ==========
# Sta pravilo sme da uradi kad se upali.
#
# Opasne akcije NE dobijaju sopstveni put: zovu iste servise koje zove i covek
# (E3 pokretanje, E4 isporuka, E5 restart), samo sa akterom `automation:<id>`.
# Zato kapija iz E1 i dnevnik rade bez ijednog novog reda — i zato
# automatizacija po konstrukciji nema vise prava od agenta.
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.domains.codium.automations.models import ActionName, ActionSpec, Event

# Sta koja akcija radi i sta trazi. `/actions` cita bas ovaj spisak, pa ekran
# uz svaku akciju odmah pise da li trazi odobrenje — covek to vidi PRE nego
# sto snimi pravilo, ne tek kad se prvi put upali.
SPECIFIKACIJE: tuple[ActionSpec, ...] = (
    ActionSpec(ActionName.NOTIFY, "Obavesti",
               "Šalje CORE notifikaciju.", params=("message",)),
    ActionSpec(ActionName.WRITE_NOTE, "Zapiši belešku",
               "Beleška na projektu.", params=("title", "body", "project_id")),
    ActionSpec(ActionName.WRITE_DEV_LOG, "Upiši u dev-log",
               "Red u dnevnik automatizacija za današnji dan.",
               params=("message",)),
    ActionSpec(ActionName.CREATE_TASK, "Napravi task",
               "Task na projektu.", params=("title", "project_id")),
    ActionSpec(ActionName.RUN_PIPELINE, "Pokreni pipeline",
               "Pokreće pipeline iz E3.",
               scope_action="pipeline.run", params=("pipeline_id",)),
    ActionSpec(ActionName.DEPLOY, "Isporuči",
               "Isporuka artefakta iz E4.",
               scope_action="deploy.execute",
               params=("target_id", "run_id")),
    ActionSpec(ActionName.RESTART_SERVICE, "Restartuj servis",
               "Restart servisa iz E5.",
               scope_action="infra.restart", params=("service_id",)),
    ActionSpec(ActionName.AGENT_ANALYZE, "Pusti agenta",
               "Pokreće agenta iz E9 nad kontekstom događaja.",
               scope_action="agent.run", params=("agent", "task")),
)

_PO_IMENU = {spec.name: spec for spec in SPECIFIKACIJE}


class ActionError(RuntimeError):
    """Akcija nije uspela."""


class UnknownAction(ActionError):
    """Trazena akcija ne postoji."""


def spec(name: str) -> ActionSpec:
    nadjena = _PO_IMENU.get(name)
    if nadjena is None:
        raise UnknownAction(
            f"Nepoznata akcija: {name}. Dozvoljeno: {', '.join(_PO_IMENU)}.")
    return nadjena


def trazi_odobrenje(name: str) -> bool:
    """Da li akcija uopste prolazi kroz kapiju."""

    return bool(spec(name).scope_action)


@dataclass
class ActionContext:
    """Sve sto akcije mogu da pozovu. Svaka zavisnost je opciona.

    Opciona je namerno: test koji proverava jednu akciju ne treba da sastavi
    ceo domen, a runtime koji jos nema neki servis ne sme da obori ceo modul.
    Akcija bez svoje zavisnosti kaze da nije dostupna, umesto da pukne.
    """

    actor: str = "automation"
    notifier: object | None = None
    codium: object | None = None            # CodiumService (beleske, taskovi)
    pipelines: object | None = None         # PipelineService
    deployments: object | None = None       # DeploymentService
    infrastructure: object | None = None    # InfrastructureService
    agents: object | None = None            # pokretac agenta
    dev_log_dir: Path | None = None


def _tekst(params: dict, kljuc: str, podrazumevano: str = "") -> str:
    vrednost = params.get(kljuc, podrazumevano)
    return vrednost if isinstance(vrednost, str) else str(vrednost)


def _broj(params: dict, kljuc: str) -> int | None:
    vrednost = params.get(kljuc)
    if isinstance(vrednost, bool) or vrednost is None:
        return None
    try:
        return int(vrednost)
    except (TypeError, ValueError):
        return None


def _popuni(sablon: str, event: Event) -> str:
    """Zamenjuje `{polje}` vrednoscu iz dogadjaja.

    Namerno NIJE `str.format`: on bi na `{missing}` bacio `KeyError` i oborio
    akciju, a na `{obj.attr}` citao atribute objekta. Ovde nepoznato polje
    ostaje kako jeste, pa se u poruci vidi da nije stiglo.
    """

    ispis = sablon
    for kljuc, vrednost in event.payload.items():
        ispis = ispis.replace("{" + str(kljuc) + "}", str(vrednost))
    return ispis.replace("{event}", event.name)


# ==========          POJEDINACNE AKCIJE          ==========

def _notify(params: dict, event: Event, ctx: ActionContext) -> str:
    poruka = _popuni(_tekst(params, "message", f"CODIUM: {event.name}"), event)
    if ctx.notifier is None:
        return f"notifikacija preskocena (nema kanala): {poruka}"
    ctx.notifier.notify("CORE: automatizacija", poruka)
    return poruka


def _write_note(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.codium is None:
        raise ActionError("Beleske nisu dostupne u ovom rasporedu.")

    from core.domains.codium.models import NoteCreate, NoteSource

    naslov = _popuni(_tekst(params, "title", f"Automatizacija: {event.name}"),
                     event)
    telo = _popuni(_tekst(params, "body"), event)
    beleska = ctx.codium.create_note(NoteCreate(
        title=naslov, body=telo, project_id=_broj(params, "project_id"),
        source=NoteSource.SYSTEM,
    ))
    return f"beleska {beleska.id}"


def _create_task(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.codium is None:
        raise ActionError("Taskovi nisu dostupni u ovom rasporedu.")

    from core.domains.codium.models import TaskCreate

    naslov = _popuni(_tekst(params, "title", f"Automatizacija: {event.name}"),
                     event)
    task = ctx.codium.create_task(TaskCreate(
        title=naslov, project_id=_broj(params, "project_id"),
        description=_popuni(_tekst(params, "description"), event),
    ))
    return f"task {task.id}"


def _write_dev_log(params: dict, event: Event, ctx: ActionContext) -> str:
    """Dopisuje red u dnevnik AUTOMATIZACIJA za danasnji dan.

    Namerno NE pise u covekov dnevnicki unos (`entries/GGGG-MM-DD.md`): taj
    fajl je kurirani tekst sa svojim redosledom i formatom, a masinski redovi
    umetnuti u njega pokvarili bi ga tise nego sto bi pomogli. Zato ide u
    zaseban fajl istog dana, sa jasnim imenom.
    """

    if ctx.dev_log_dir is None:
        raise ActionError("Putanja dev-loga nije zadata.")

    poruka = _popuni(_tekst(params, "message", event.name), event)
    dan = datetime.now(UTC).date().isoformat()
    fajl = Path(ctx.dev_log_dir) / f"{dan}-automations.md"
    fajl.parent.mkdir(parents=True, exist_ok=True)

    if not fajl.exists():
        fajl.write_text(
            f"# {dan} — automatizacije\n\n"
            "Redove ovde upisuje E10; covekov dnevnicki unos se ne dira.\n\n",
            encoding="utf-8")

    vreme = datetime.now(UTC).strftime("%H:%M")
    with fajl.open("a", encoding="utf-8") as izlaz:
        izlaz.write(f"- {vreme} · `{event.name}` — {poruka}\n")
    return f"upisano u {fajl.name}"


def _run_pipeline(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.pipelines is None:
        raise ActionError("Pipeline servis nije dostupan u ovom rasporedu.")

    pipeline_id = _broj(params, "pipeline_id") or _broj(event.payload,
                                                        "pipeline_id")
    if pipeline_id is None:
        raise ActionError("Akcija trazi `pipeline_id`.")

    pokretanje = ctx.pipelines.run(pipeline_id, actor=ctx.actor,
                                   trigger="automation")
    return f"pokretanje {pokretanje.id}"


def _deploy(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.deployments is None:
        raise ActionError("Isporuka nije dostupna u ovom rasporedu.")

    target_id = _broj(params, "target_id")
    run_id = _broj(params, "run_id") or _broj(event.payload, "run_id")
    if target_id is None or run_id is None:
        raise ActionError("Akcija trazi `target_id` i `run_id`.")

    isporuka = ctx.deployments.deploy(target_id, run_id, actor=ctx.actor)
    return f"isporuka {isporuka.id}"


def _restart_service(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.infrastructure is None:
        raise ActionError("Infrastruktura nije dostupna u ovom rasporedu.")

    service_id = _broj(params, "service_id") or _broj(event.payload,
                                                      "service_id")
    if service_id is None:
        raise ActionError("Akcija trazi `service_id`.")

    stanje = ctx.infrastructure.restart(service_id, actor=ctx.actor)
    return f"servis {service_id}: {stanje.state}"


def _agent_analyze(params: dict, event: Event, ctx: ActionContext) -> str:
    if ctx.agents is None:
        raise ActionError("Agenti nisu dostupni u ovom rasporedu.")

    agent = _tekst(params, "agent")
    if not agent:
        raise ActionError("Akcija trazi `agent`.")

    zadatak = _popuni(
        _tekst(params, "task", f"Analiziraj dogadjaj {event.name}."), event)
    run_id = ctx.agents.start(agent, zadatak, actor=ctx.actor)
    return f"posao agenta {run_id}"


IZVRSIOCI: dict[str, Callable[[dict, Event, ActionContext], str]] = {
    ActionName.NOTIFY: _notify,
    ActionName.WRITE_NOTE: _write_note,
    ActionName.WRITE_DEV_LOG: _write_dev_log,
    ActionName.CREATE_TASK: _create_task,
    ActionName.RUN_PIPELINE: _run_pipeline,
    ActionName.DEPLOY: _deploy,
    ActionName.RESTART_SERVICE: _restart_service,
    ActionName.AGENT_ANALYZE: _agent_analyze,
}


def execute(name: str, params: dict, event: Event, ctx: ActionContext) -> str:
    """Izvrsava jednu akciju i vraca kratak opis onoga sto se desilo."""

    spec(name)   # nepoznata akcija pada ovde, pre ijednog poteza
    return IZVRSIOCI[name](params, event, ctx)
