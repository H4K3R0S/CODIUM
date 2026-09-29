# ========== ROUTER: IZVESTAJI (CODIUM) ==========
# Sve rute su citanje. Nijedna ne menja bazu, pa nema ni `actor` ni kapije —
# citanje sopstvenih izvestaja nije potez nad sistemom.
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from apps.api.schemas.codium_analytics import (
    PointResponse,
    ReportResponse,
    ReportSpecResponse,
    ReportsResponse,
    SeriesResponse,
    SummaryResponse,
)
from core.domains.codium.analytics.models import DANA, Period
from core.domains.codium.analytics.service import (
    AnalyticsError,
    AnalyticsService,
    UnknownPeriod,
    UnknownReport,
)

router = APIRouter(
    prefix="/api/v1/codium/analytics",
    tags=["CODIUM Izvestaji"],
)


def get_service() -> AnalyticsService:
    from apps.api import codium_analytics_runtime
    return codium_analytics_runtime.get_service()


def _prevedi(greska: Exception) -> HTTPException:
    if isinstance(greska, UnknownReport):
        return HTTPException(status_code=404, detail=str(greska))
    if isinstance(greska, (UnknownPeriod, AnalyticsError, ValueError)):
        return HTTPException(status_code=400, detail=str(greska))
    return HTTPException(status_code=500, detail=str(greska))


def _u_odgovor(izvestaj) -> ReportResponse:
    return ReportResponse(
        name=izvestaj.name,
        period=izvestaj.period,
        series=[
            SeriesResponse(
                label=s.label,
                points=[PointResponse(x=t.x, y=t.y) for t in s.points],
            )
            for s in izvestaj.series
        ],
        totals=izvestaj.totals,
    )


# ----------          SPISAK          ----------

@router.get("/reports", response_model=ReportsResponse)
def spisak(servis: AnalyticsService = Depends(get_service)) -> ReportsResponse:
    return ReportsResponse(
        reports=[
            ReportSpecResponse(name=s.name, label=s.label, section=str(s.section),
                               description=s.description,
                               supports_project=s.supports_project)
            for s in servis.specs()
        ],
        periods=[str(p) for p in DANA],
    )


# ----------          ZBIRNA TABLA          ----------

@router.get("/summary", response_model=SummaryResponse)
def zbir(period: str = Query(default=Period.D30),
         servis: AnalyticsService = Depends(get_service)) -> SummaryResponse:
    try:
        return SummaryResponse(period=period, totals=servis.summary(period))
    except Exception as greska:
        raise _prevedi(greska) from greska


# ----------          IZVESTAJ          ----------

@router.get("/reports/{name}", response_model=ReportResponse)
def izvestaj(name: str, period: str = Query(default=Period.D30),
             project_id: int | None = Query(default=None),
             servis: AnalyticsService = Depends(get_service)) -> ReportResponse:
    try:
        return _u_odgovor(servis.report(name, period, project_id))
    except Exception as greska:
        raise _prevedi(greska) from greska


@router.get("/export/{name}")
def izvoz(name: str, period: str = Query(default=Period.D30),
          project_id: int | None = Query(default=None),
          servis: AnalyticsService = Depends(get_service)) -> StreamingResponse:
    """Isti podaci kao JSON, u CSV-u.

    Jedan red po tacki, sa imenom serije u koloni — sirok oblik (kolona po
    seriji) bi za izvestaj sa dve serije razlicitih osa dao prazna polja, a
    ovako se svaki izvestaj izvozi istim kodom.
    """

    try:
        izvestaj = servis.report(name, period, project_id)
    except Exception as greska:
        raise _prevedi(greska) from greska

    bafer = io.StringIO()
    pisac = csv.writer(bafer, lineterminator="\n")
    pisac.writerow(["report", "period", "series", "x", "y"])
    for serija in izvestaj.series:
        for tacka in serija.points:
            pisac.writerow([izvestaj.name, izvestaj.period, serija.label,
                            tacka.x, tacka.y])

    bafer.seek(0)
    return StreamingResponse(
        iter([bafer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                f'attachment; filename="{name}-{period}.csv"',
        },
    )
