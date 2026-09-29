# ========== UPITI IZVESTAJA ==========
# Jedan imenovani upit po metrici. Cist SQL nad bazom, bez poslovne logike u
# Python-u gde SQL ume sam — agregacija preko devedeset dana ne treba da prodje
# kroz listu u memoriji.
#
# NIJEDAN upit ovde ne pise u bazu. Ako neki izvestaj ne moze bez medjutabele,
# to je znak da podatak fali u IZVORNOJ fazi i dopunjava se tamo. Ovo pravilo
# cuva E7 od pretvaranja u drugo skladiste.
#
# Dve baze, ne jedna: poslovni podaci (pokretanja, isporuke, alarmi) su u
# `codium.db`, a operativni saobracaj (uzorci merenja, potrosnja AI) u
# `codium_ops.db`. Fazni fajl pominje samo prvu; podela postoji od E1 i E6, pa
# upiti nose putanju baze koju citaju.
from __future__ import annotations

from pathlib import Path

from core.database import core_database_connection
from core.domains.codium.analytics.models import Point, Series


# Granica perioda se racuna iz UTC sadasnjosti, jer `CURRENT_TIMESTAMP` u
# SQLite-u pise UTC. Racunanje iz lokalnog datuma bi na svakoj vremenskoj zoni
# seklo period na pogresnom mestu.
def _od(days: int, now: str | None = None) -> str:
    osnova = f"'{now}'" if now else "'now'"
    return f"datetime({osnova}, '-{days} days')"


def _do(now: str | None = None) -> str:
    return f"datetime('{now}')" if now else "datetime('now')"


def _tacke(redovi) -> list[Point]:
    return [Point(x=str(red[0]), y=round(float(red[1]), 3)) for red in redovi]


# ==========          ISPORUKA (codium.db)          ==========

def pipeline_success_rate(db: Path, days: int, *, project_id: int | None = None,
                          now: str | None = None) -> tuple[list[Series], dict]:
    """Udeo uspesnih pokretanja po danu, i ukupno za period."""

    uslov, parametri = _filter_pipeline(project_id)
    with core_database_connection(db) as veza:
        po_danu = veza.execute(
            "SELECT date(r.created_at) AS dan, "
            "       AVG(CASE WHEN r.status = 'success' THEN 1.0 ELSE 0.0 END) "
            "FROM codium_pipeline_runs r "
            f"WHERE r.created_at >= {_od(days, now)} "
            f"  AND r.created_at <= {_do(now)} {uslov} "
            "GROUP BY dan ORDER BY dan",
            parametri,
        ).fetchall()

        zbir = veza.execute(
            "SELECT COUNT(*), "
            "       SUM(CASE WHEN r.status = 'success' THEN 1 ELSE 0 END) "
            "FROM codium_pipeline_runs r "
            f"WHERE r.created_at >= {_od(days, now)} "
            f"  AND r.created_at <= {_do(now)} {uslov}",
            parametri,
        ).fetchone()

    ukupno, uspesnih = (zbir[0] or 0), (zbir[1] or 0)
    return (
        [Series(label="udeo uspešnih", points=_tacke(po_danu))],
        {
            "runs": float(ukupno),
            "success": float(uspesnih),
            "success_rate": round(uspesnih / ukupno, 3) if ukupno else 0.0,
        },
    )


def pipeline_duration(db: Path, days: int, *, project_id: int | None = None,
                      now: str | None = None) -> tuple[list[Series], dict]:
    """Prosecno i najgore trajanje pokretanja, u sekundama, po danu.

    Trajanje se racuna samo za pokretanja koja su ZAVRSILA — ono koje jos radi
    nema trajanje, a uzimati mu razliku do sada znacilo bi meriti cekanje.
    """

    uslov, parametri = _filter_pipeline(project_id)
    with core_database_connection(db) as veza:
        redovi = veza.execute(
            "SELECT date(r.created_at) AS dan, "
            "       AVG(strftime('%s', r.finished_at) - strftime('%s', r.started_at)), "
            "       MAX(strftime('%s', r.finished_at) - strftime('%s', r.started_at)) "
            "FROM codium_pipeline_runs r "
            f"WHERE r.created_at >= {_od(days, now)} "
            f"  AND r.created_at <= {_do(now)} "
            "  AND r.started_at IS NOT NULL AND r.finished_at IS NOT NULL "
            f"{uslov} GROUP BY dan ORDER BY dan",
            parametri,
        ).fetchall()

    prosek = [Point(str(r[0]), round(float(r[1] or 0), 1)) for r in redovi]
    najgore = [Point(str(r[0]), round(float(r[2] or 0), 1)) for r in redovi]
    svi = [t.y for t in prosek]
    return (
        [Series("prosek (s)", prosek), Series("najgore (s)", najgore)],
        {
            "avg_seconds": round(sum(svi) / len(svi), 1) if svi else 0.0,
            "worst_seconds": max((t.y for t in najgore), default=0.0),
        },
    )


def failing_steps(db: Path, days: int, *, project_id: int | None = None,
                  now: str | None = None) -> tuple[list[Series], dict]:
    """Koji korak najcesce pada. Bez ovoga „pipeline pada“ nema adresu."""

    uslov, parametri = _filter_pipeline(project_id)
    with core_database_connection(db) as veza:
        redovi = veza.execute(
            "SELECT s.name, COUNT(*) AS palo "
            "FROM codium_run_steps s "
            "JOIN codium_pipeline_runs r ON r.id = s.run_id "
            "WHERE s.status = 'failed' "
            f"  AND r.created_at >= {_od(days, now)} "
            f"  AND r.created_at <= {_do(now)} {uslov} "
            "GROUP BY s.name ORDER BY palo DESC LIMIT 10",
            parametri,
        ).fetchall()

    tacke = _tacke(redovi)
    return ([Series("padova", tacke)],
            {"failures": float(sum(t.y for t in tacke))})


def deploy_frequency(db: Path, days: int, *, project_id: int | None = None,
                     now: str | None = None) -> tuple[list[Series], dict]:
    """Isporuke po danu, i udeo onih koje su vracene unazad."""

    with core_database_connection(db) as veza:
        po_danu = veza.execute(
            "SELECT date(created_at) AS dan, COUNT(*) "
            "FROM codium_deployments "
            f"WHERE created_at >= {_od(days, now)} AND created_at <= {_do(now)} "
            "GROUP BY dan ORDER BY dan"
        ).fetchall()

        zbir = veza.execute(
            "SELECT COUNT(*), "
            "       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), "
            "       SUM(CASE WHEN status = 'rolled_back' THEN 1 ELSE 0 END) "
            "FROM codium_deployments "
            f"WHERE created_at >= {_od(days, now)} AND created_at <= {_do(now)}"
        ).fetchone()

    ukupno = zbir[0] or 0
    vracenih = zbir[2] or 0
    return (
        [Series("isporuka", _tacke(po_danu))],
        {
            "deploys": float(ukupno),
            "success": float(zbir[1] or 0),
            "rolled_back": float(vracenih),
            "rollback_rate": round(vracenih / ukupno, 3) if ukupno else 0.0,
        },
    )


def _filter_pipeline(project_id: int | None) -> tuple[str, tuple]:
    """Suzenje po projektu ide preko repozitorijuma — pokretanje ga ne nosi."""

    if project_id is None:
        return ("", ())
    return (
        (" AND r.pipeline_id IN (SELECT p.id FROM codium_pipelines p "
        "   JOIN codium_repositories repo ON repo.id = p.repository_id "
        "   WHERE repo.project_id = ?)"),
        (project_id,),
    )


# ==========          RAD SISTEMA          ==========

def service_uptime(ops_db: Path, business_db: Path, days: int, *,
                   now: str | None = None) -> tuple[list[Series], dict]:
    """Dostupnost po servisu: udeo uzoraka u kojima je `up = 1`.

    Prosek nula i jedinica JESTE dostupnost, pa nema sta da se sabira posebno.
    Imena servisa dolaze iz druge baze, pa se spajaju u Python-u — jedan mali
    recnik je jeftiniji od `ATTACH`-a na svaki poziv.
    """

    with core_database_connection(ops_db) as veza:
        redovi = veza.execute(
            "SELECT service_id, AVG(value), COUNT(*) "
            "FROM codium_metric_samples "
            f"WHERE metric = 'up' AND at >= {_od(days, now)} "
            f"  AND at <= {_do(now)} AND service_id IS NOT NULL "
            "GROUP BY service_id ORDER BY service_id"
        ).fetchall()

    imena = _imena_servisa(business_db)
    tacke = [Point(imena.get(red[0], f"servis {red[0]}"), round(float(red[1]), 3))
             for red in redovi]
    uzoraka = sum(red[2] for red in redovi)
    prosek = (sum(t.y for t in tacke) / len(tacke)) if tacke else 0.0
    return ([Series("dostupnost", tacke)],
            {"services": float(len(tacke)), "samples": float(uzoraka),
             "avg_uptime": round(prosek, 3)})


def alerts_per_service(business_db: Path, days: int, *,
                       now: str | None = None) -> tuple[list[Series], dict]:
    """Broj alarma po servisu i ukupno vreme provedeno u stanju `firing`.

    Alarm koji jos gori nema `resolved_at`, pa mu se trajanje racuna do sada —
    inace bi najduzi kvar bio i jedini koji se ne vidi.
    """

    with core_database_connection(business_db) as veza:
        redovi = veza.execute(
            "SELECT COALESCE(s.name, 'servis ' || r.service_id) AS ime, "
            "       COUNT(*), "
            "       SUM(strftime('%s', COALESCE(a.resolved_at, "
            f"                    {_do(now)})) - strftime('%s', a.started_at)) "
            "FROM codium_alerts a "
            "JOIN codium_alert_rules r ON r.id = a.rule_id "
            "LEFT JOIN codium_infra_services s ON s.id = r.service_id "
            f"WHERE a.started_at >= {_od(days, now)} "
            f"  AND a.started_at <= {_do(now)} "
            "GROUP BY ime ORDER BY COUNT(*) DESC LIMIT 20"
        ).fetchall()

    broj = [Point(str(r[0]), float(r[1])) for r in redovi]
    trajanje = [Point(str(r[0]), round(float(r[2] or 0) / 60, 1)) for r in redovi]
    return (
        [Series("alarma", broj), Series("minuta u alarmu", trajanje)],
        {
            "alerts": float(sum(t.y for t in broj)),
            "firing_minutes": round(sum(t.y for t in trajanje), 1),
        },
    )


def _imena_servisa(business_db: Path) -> dict[int, str]:
    with core_database_connection(business_db) as veza:
        return {
            red[0]: red[1]
            for red in veza.execute(
                "SELECT id, name FROM codium_infra_services").fetchall()
        }


# ==========          AI (codium_ops.db)          ==========

def ai_cost_by_model(ops_db: Path, days: int, *, project_id: int | None = None,
                     now: str | None = None) -> tuple[list[Series], dict]:
    """Pozivi, tokeni i trosak po modelu."""

    uslov = " AND project_id = ?" if project_id is not None else ""
    parametri = (project_id,) if project_id is not None else ()

    with core_database_connection(ops_db) as veza:
        redovi = veza.execute(
            "SELECT provider || '/' || model AS cilj, COUNT(*), "
            "       SUM(cost_usd), SUM(prompt_tokens + output_tokens) "
            "FROM codium_ai_usage "
            f"WHERE at >= {_od(days, now)} AND at <= {_do(now)}{uslov} "
            "GROUP BY cilj ORDER BY SUM(cost_usd) DESC, COUNT(*) DESC LIMIT 20",
            parametri,
        ).fetchall()

    poziva = [Point(str(r[0]), float(r[1])) for r in redovi]
    trosak = [Point(str(r[0]), round(float(r[2] or 0), 4)) for r in redovi]
    return (
        [Series("poziva", poziva), Series("trošak (USD)", trosak)],
        {
            "calls": float(sum(t.y for t in poziva)),
            "cost_usd": round(sum(t.y for t in trosak), 4),
            "tokens": float(sum(float(r[3] or 0) for r in redovi)),
        },
    )


def ai_local_vs_online(ops_db: Path, days: int, *, project_id: int | None = None,
                       now: str | None = None) -> tuple[list[Series], dict]:
    """Odnos lokalnih i placenih poziva — koliko je stvarno placeno.

    Podela ide po trosku, ne po imenu provajdera: lokalni model je onaj koji
    nista ne kosta, a spisak imena bi zastareo cim se doda nov provajder.
    """

    uslov = " AND project_id = ?" if project_id is not None else ""
    parametri = (project_id,) if project_id is not None else ()

    with core_database_connection(ops_db) as veza:
        redovi = veza.execute(
            "SELECT date(at) AS dan, "
            "       SUM(CASE WHEN cost_usd > 0 THEN 1 ELSE 0 END), "
            "       SUM(CASE WHEN cost_usd > 0 THEN 0 ELSE 1 END) "
            "FROM codium_ai_usage "
            f"WHERE at >= {_od(days, now)} AND at <= {_do(now)}{uslov} "
            "GROUP BY dan ORDER BY dan",
            parametri,
        ).fetchall()

    placeni = [Point(str(r[0]), float(r[1] or 0)) for r in redovi]
    lokalni = [Point(str(r[0]), float(r[2] or 0)) for r in redovi]
    ukupno_placenih = sum(t.y for t in placeni)
    ukupno = ukupno_placenih + sum(t.y for t in lokalni)
    return (
        [Series("plaćeni", placeni), Series("lokalni", lokalni)],
        {
            "paid": ukupno_placenih,
            "local": sum(t.y for t in lokalni),
            "paid_share": round(ukupno_placenih / ukupno, 3) if ukupno else 0.0,
        },
    )
