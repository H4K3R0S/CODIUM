# ========== EVIDENCIJA POTROSNJE ==========
# Upis svakog poziva modela u operativnu CODIUM bazu (`codium_ops.db`) i
# sazetak nad tim redovima.
#
# Trosak se racuna kroz `core.ai.pricing.cost_usd` U TRENUTKU UPISA i cuva kao
# broj. Cene se menjaju, pa bi naknadno racunanje iz tokena prepisalo istoriju.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.ai.pricing import cost_usd
from core.database import core_database_connection
from core.domains.codium.runtime import codium_ops_database_path

# ==========          SAZETAK          ==========

@dataclass(frozen=True)
class UsageSummary:
    """Zbir evidentiranih poziva: broj, tokeni i trošak u dolarima."""

    calls: int
    prompt_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class UsageCall:
    """Jedan evidentiran poziv modela — red iz `codium_ai_usage`."""

    at: str
    provider: str
    model: str
    project_id: int | None
    persona: str
    actor: str
    prompt_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: int
    ok: bool


# ==========          DONJA GRANICA PERIODA          ==========

def _pocetak_perioda(period: str) -> str:
    """
    Donja granica perioda kao UTC vremenska oznaka.

    Kolona `at` se puni sa CURRENT_TIMESTAMP, a to je UTC. Kad bi se granica
    izvela iz lokalnog datuma, red upisan u 01:30 po lokalnom vremenu ne bi
    ušao u period "day".
    """

    sada = datetime.now(timezone.utc)

    if period == "day":
        return sada.strftime("%Y-%m-%d 00:00:00")
    if period == "month":
        return sada.strftime("%Y-%m-01 00:00:00")

    raise ValueError(
        f"Nepoznat period: {period!r}. Dozvoljeni su 'day' i 'month'."
    )


# ==========          UPIS I SAZETAK          ==========

class UsageRecorder:
    """Evidentira pozive modela i vraća sažetak potrošnje."""

    def __init__(self, database_path: Path | None = None) -> None:
        # Default na operativnu bazu — bez ovoga bi None pao na core.db.
        self._database_path = database_path or codium_ops_database_path()

    def record(
        self, *, provider: str, model: str, project_id: int | None,
        persona: str, prompt_tokens: int, output_tokens: int,
        duration_ms: int, ok: bool, actor: str = "human",
    ) -> None:
        """Upisuje jedan poziv modela zajedno sa troškom u trenutku poziva."""

        trosak = cost_usd(model, prompt_tokens, output_tokens)
        with core_database_connection(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO codium_ai_usage (
                    provider, model, project_id, persona, actor,
                    prompt_tokens, output_tokens, cost_usd, duration_ms, ok
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider, model, project_id, persona, actor,
                    prompt_tokens, output_tokens, trosak, duration_ms,
                    1 if ok else 0,
                ),
            )

    def recent(self, *, limit: int = 20) -> list[UsageCall]:
        """Poslednji evidentirani pozivi, najnoviji prvi.

        Sluzi vremenskoj liniji aktivnosti; sazetak odgovara na drugo pitanje
        (koliko ukupno), pa mu se ne dodaje.
        """

        with core_database_connection(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT at, provider, model, project_id, persona, actor,
                       prompt_tokens, output_tokens, cost_usd, duration_ms, ok
                FROM codium_ai_usage
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            UsageCall(
                at=row["at"], provider=row["provider"], model=row["model"],
                project_id=row["project_id"], persona=row["persona"],
                actor=row["actor"], prompt_tokens=row["prompt_tokens"],
                output_tokens=row["output_tokens"],
                cost_usd=float(row["cost_usd"]),
                duration_ms=row["duration_ms"], ok=bool(row["ok"]),
            )
            for row in rows
        ]

    def summary(
        self, *, period: str | None = None, project_id: int | None = None,
    ) -> UsageSummary:
        """
        Sažetak evidentiranih poziva.

        Args:
            period: "day" ili "month"; None znači celo vreme. Nepoznata
                vrednost diže ValueError — tiho ignorisan filter je gori
                od greške.
            project_id: Opciono ograničenje na jedan projekat.
        """

        uslovi: list[str] = []
        parametri: list[object] = []

        if period is not None:
            uslovi.append("at >= ?")
            parametri.append(_pocetak_perioda(period))

        if project_id is not None:
            uslovi.append("project_id = ?")
            parametri.append(project_id)

        where = f" WHERE {' AND '.join(uslovi)}" if uslovi else ""

        with core_database_connection(self._database_path) as connection:
            row = connection.execute(
                # COALESCE: SUM bez redova vraća NULL, a sažetak mora nule.
                """
                SELECT COUNT(*) AS calls,
                       COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                       COALESCE(SUM(output_tokens), 0) AS output_tokens,
                       COALESCE(SUM(cost_usd), 0) AS cost_usd
                FROM codium_ai_usage
                """
                + where,
                tuple(parametri),
            ).fetchone()

        return UsageSummary(
            calls=row["calls"],
            prompt_tokens=row["prompt_tokens"],
            output_tokens=row["output_tokens"],
            cost_usd=float(row["cost_usd"]),
        )
