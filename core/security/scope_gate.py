# ========== SCOPE GATE ==========
# Odlucuje PRE akcije da li akter sme da je izvede. CORE nivo, jer ce ga
# koristiti i drugi domeni, ne samo CODIUM.
#
# Gate ne zna za bazu: pravila prima kroz ubrizganu funkciju. Tako se ista
# odluka testira bez ijednog reda u SQLite-u, a pozivalac bira odakle pravila
# dolaze (baza, konfiguracija, test).
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

ALLOW = "allow"
DENY = "deny"
NEEDS_APPROVAL = "needs_approval"

# Podrazumevano ponasanje po glagolu akcije, kad nijedno pravilo ne pogadja.
#
# `call_online` je namerno `allow`: gate uvodi kontrolu nad postojecim chatom,
# a ne obara ga u trenutku spajanja. Ko hoce zabranu, upise pravilo.
_DEFAULTS: dict[str, str] = {
    "read": ALLOW,
    "list": ALLOW,
    "call_online": ALLOW,
    "write": NEEDS_APPROVAL,
    "push": NEEDS_APPROVAL,
    "run": NEEDS_APPROVAL,
    "execute": NEEDS_APPROVAL,
    "delete": DENY,
    "restart": DENY,
}

# Nepoznat glagol se odbija. Tiho dozvoljavanje nepoznate akcije je rupa koja
# se primeti tek kad nesto ode naopako.
_FALLBACK = DENY

# Akter koji ne prolazi kroz gate — on je taj koji odobrava.
HUMAN = "human"


@dataclass(frozen=True)
class ScopeRule:
    """Jedno pravilo dozvole."""

    actor: str
    action: str
    target: str = "*"
    verdict: str = DENY
    note: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Decision:
    """Odgovor gate-a, sa tragom odakle je odluka dosla."""

    verdict: str
    rule_id: int | None
    reason: str


def _matches(pattern: str, value: str) -> bool:
    """Poklapanje sa zvezdicom na kraju obrasca (`project:12/*`)."""
    if pattern in ("", "*"):
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def _specificity(pattern: str) -> int:
    """Koliko je obrazac odredjen — duzi tacan deo znaci precizniji obrazac."""
    if pattern in ("", "*"):
        return 0
    if pattern.endswith("*"):
        return len(pattern) - 1
    # Tacan pogodak je uvek precizniji od bilo kog obrasca sa zvezdicom.
    return len(pattern) + 1


class ScopeGate:
    """Odlucuje da li akter sme da izvede akciju nad ciljem."""

    def __init__(self, rules: Callable[[], list[ScopeRule]]) -> None:
        self._rules = rules

    def check(self, *, actor: str, action: str, target: str = "") -> Decision:
        if actor == HUMAN:
            return Decision(ALLOW, None, "covek ne prolazi kroz gate")

        pogodjena = [
            rule for rule in self._rules()
            if _matches(rule.actor, actor)
            and _matches(rule.action, action)
            and _matches(rule.target, target)
        ]
        if pogodjena:
            # Najspecificnije pravilo pobedjuje; cilj je najjaci kriterijum,
            # pa akter, pa akcija.
            najbolje = max(
                pogodjena,
                key=lambda r: (_specificity(r.target), _specificity(r.actor),
                               _specificity(r.action)),
            )
            razlog = najbolje.note or f"pravilo {najbolje.actor} {najbolje.action}"
            return Decision(najbolje.verdict, najbolje.id, razlog)

        glagol = action.rsplit(".", 1)[-1]
        verdikt = _DEFAULTS.get(glagol, _FALLBACK)
        return Decision(verdikt, None, f"podrazumevano za `{glagol}`")
