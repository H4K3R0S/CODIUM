# ========== SEME: IZVESTAJI (CODIUM) ==========
# Oblik odgovora je isti za SVAKI izvestaj. To nije estetika nego usteda: GUI
# ima jednu komponentu grafikona, a ne osam.
from __future__ import annotations

from pydantic import BaseModel


class PointResponse(BaseModel):
    """Jedna tacka. `x` je oznaka (dan, ime), `y` je broj."""

    x: str
    y: float


class SeriesResponse(BaseModel):
    label: str
    points: list[PointResponse]


class ReportResponse(BaseModel):
    """Jedinstven oblik odgovora svakog izvestaja.

    `totals` nosi brojeve koje plocica prikazuje bez grafikona; grafikon crta
    `series`. Ni jedno se ne izvodi iz drugog.
    """

    name: str
    period: str
    series: list[SeriesResponse]
    totals: dict[str, float]


class ReportSpecResponse(BaseModel):
    name: str
    label: str
    section: str
    description: str
    supports_project: bool = False


class ReportsResponse(BaseModel):
    """Sta sve ekran ume da pokaze, i sta koji izvestaj prima."""

    reports: list[ReportSpecResponse]
    periods: list[str]


class SummaryResponse(BaseModel):
    """Zbirna tabla: brojevi za period, uz iste za prethodni period."""

    period: str
    totals: dict[str, float]
