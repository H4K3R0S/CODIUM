# ========== MODELI IZVESTAJA ==========
# Svi izvestaji vracaju ISTI oblik. To nije estetika nego usteda: jedinstven
# oblik znaci da GUI ima jednu komponentu grafikona, a ne osam.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Period(StrEnum):
    """Period izvestaja. Namerno malo izbora — svaki je jedan klik na ekranu."""

    D7 = "7d"
    D30 = "30d"
    D90 = "90d"


# Koliko dana nosi koji period. Sluzi i za racunanje PRETHODNOG perioda iste
# duzine, jer plocica pokazuje promenu u odnosu na njega.
DANA = {Period.D7: 7, Period.D30: 30, Period.D90: 90}


class Section(StrEnum):
    """Odeljak ekrana kojem izvestaj pripada."""

    RAZVOJ = "razvoj"
    ISPORUKA = "isporuka"
    SISTEM = "sistem"
    AI = "ai"


@dataclass(frozen=True)
class Point:
    """Jedna tacka. `x` je oznaka (dan, ime), `y` je broj."""

    x: str
    y: float


@dataclass(frozen=True)
class Series:
    """Jedna linija ili grupa stupaca, sa svojim imenom."""

    label: str
    points: list[Point] = field(default_factory=list)


@dataclass(frozen=True)
class Report:
    """Jedan izvestaj.

    `totals` nosi brojeve koje plocica prikazuje bez grafikona (zbir, prosek,
    udeo). Grafikon crta `series`; plocica cita `totals`. Ni jedno ne izvodi
    drugo, jer prosek preko kanti nije isto sto i prosek preko uzoraka.
    """

    name: str
    period: str
    series: list[Series] = field(default_factory=list)
    totals: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportSpec:
    """Opis izvestaja: sta radi i sta prima.

    Postoji da bi `/reports` mogao da kaze sta sve ume, bez da neko rucno
    odrzava spisak na dva mesta.
    """

    name: str
    label: str
    section: str
    description: str
    # Da li izvestaj uopste ume da suzi po projektu.
    supports_project: bool = False
