# ========== AUTOMATIZACIJA (E10) ==========
# Spaja dogadjaje koje podsistemi vec proizvode sa akcijama koje vec umeju da
# se izvrse. Namerno poslednja u AI bloku: automatizacija nad podsistemom koji
# nije stabilan samo umnozava kvarove.
#
# Kao i kod `infrastructure` i `monitoring`, ovde stoje samo moduli bez teskih
# zavisnosti. `bus.py` posebno: njega uvoze pipeline, isporuka i merenje da bi
# objavili dogadjaj, pa svaki tezi uvoz ovde zatvorio bi krug kroz pola domena.
from core.domains.codium.automations.bus import EventBus, event_bus, publish
from core.domains.codium.automations.conditions import (
    ConditionError,
    evaluate,
    matches,
    parse,
)
from core.domains.codium.automations.models import (
    MAKS_DUBINA,
    POLJA_DOGADJAJA,
    Action,
    ActionName,
    AutomationRun,
    Event,
    EventName,
    Rule,
    RunStatus,
    TestResult,
)

__all__ = [
    "MAKS_DUBINA", "POLJA_DOGADJAJA", "Action", "ActionName", "AutomationRun",
    "ConditionError", "Event", "EventBus", "EventName", "Rule", "RunStatus",
    "TestResult", "evaluate", "event_bus", "matches", "parse", "publish",
]
