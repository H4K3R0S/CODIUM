# ========== VREMENSKA LINIJA AKTIVNOSTI ==========
# Spaja dva zapisa u jednu listu za dashboard: dnevnik dozvola (ko je sta
# trazio i sta je gate odgovorio) i evidenciju poziva modela (koji model,
# koliko je trajalo, koliko je kostalo).
#
# Zasto oba: dnevnik zna za odbijene akcije koje nikad nisu ni krenule, a
# evidencija zna sta se stvarno desilo kad su krenule. Ni jedan sam ne daje
# celu sliku.
from __future__ import annotations

from dataclasses import dataclass

from core.ai.usage import UsageCall, UsageRecorder
from core.domains.codium.audit.models import AuditEntry
from core.domains.codium.audit.repository import AuditRepository


@dataclass(frozen=True)
class ActivityItem:
    """Jedan red vremenske linije."""

    at: str
    kind: str            # "model" | "gate"
    title: str
    meta: str
    outcome: str         # "ok" | "error" | "blocked"
    verdict: str = ""    # popunjeno samo za `gate`
    project_id: int | None = None
    cost_usd: float = 0.0


def _trajanje(duration_ms: int) -> str:
    """Trajanje u citljivom obliku (ms ispod sekunde, inace sekunde)."""
    if duration_ms < 1000:
        return f"{duration_ms} ms"
    return f"{duration_ms / 1000:.1f} s"


def _od_poziva(call: UsageCall) -> ActivityItem:
    delovi = [call.provider, _trajanje(call.duration_ms)]
    if call.cost_usd > 0:
        # Cetiri decimale: poziv cesto kosta manje od centa, a nula umesto
        # iznosa bi izgledala kao da je poziv bio besplatan.
        delovi.append(f"${call.cost_usd:.4f}")
    return ActivityItem(
        at=call.at,
        kind="model",
        title=f"Odgovor modela {call.model}",
        meta=" · ".join(delovi),
        outcome="ok" if call.ok else "error",
        project_id=call.project_id,
        cost_usd=call.cost_usd,
    )


def _od_dnevnika(entry: AuditEntry) -> ActivityItem:
    cilj = f" · {entry.target}" if entry.target else ""
    return ActivityItem(
        at=entry.at,
        kind="gate",
        title=f"Odbijeno: {entry.action}",
        meta=f"{entry.actor}{cilj}" + (f" · {entry.detail}" if entry.detail else ""),
        outcome=entry.outcome,
        verdict=entry.verdict,
        project_id=entry.project_id,
    )


class ActivityFeed:
    """Poslednja dešavanja u domenu, iz oba operativna zapisa."""

    def __init__(self, audit: AuditRepository, usage: UsageRecorder) -> None:
        self._audit = audit
        self._usage = usage

    def recent(self, *, limit: int = 20) -> list[ActivityItem]:
        stavke = [_od_poziva(call) for call in self._usage.recent(limit=limit)]

        # Dozvoljena provera se ne prikazuje: uz svaki online poziv stoji i
        # `allow` red, a poziv vec ima svoju stavku sa modelom i troskom.
        # Dva reda o istoj stvari su sum, ne informacija. Odbijanje nema
        # svoj poziv, pa ga samo dnevnik i moze prijaviti.
        stavke.extend(
            _od_dnevnika(entry)
            for entry in self._audit.query(limit=limit)
            if entry.verdict != "allow"
        )

        stavke.sort(key=lambda item: item.at, reverse=True)
        return stavke[:limit]
