# ========== SERVIS IZVESTAJA ==========
# Cita ono sto druge faze vec upisuju. NE PISE NISTA — ni jedan poziv odavde ne
# menja bazu. To je pravilo koje cuva E7 od pretvaranja u drugo skladiste.
#
# Zato ovde nema ni kapije ni dnevnika: citanje sopstvenih izvestaja nije potez
# nad sistemom, a upis u dnevnik pri svakom iscrtavanju ekrana bio bi buka koja
# zatrpava prave tragove.
from __future__ import annotations

from pathlib import Path

from core.domains.codium.analytics import queries
from core.domains.codium.analytics.cache import ReportCache
from core.domains.codium.analytics.models import (
    DANA,
    Period,
    Report,
    ReportSpec,
    Section,
    Series,
)
from core.domains.codium.repositories.providers.base import GitError
from core.domains.codium.repositories.providers.local_git import LocalGitProvider
from core.domains.codium.repositories.repository import RepositoryRepository
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)


class AnalyticsError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class UnknownReport(AnalyticsError):
    """Trazen izvestaj ne postoji."""


class UnknownPeriod(AnalyticsError):
    """Trazen period nije jedan od ponudjenih."""


# Sta sve ekran ume da pokaze. Spisak stoji na JEDNOM mestu — `/reports` ga
# cita odavde, pa se ne odrzava rucno na dva.
SPECIFIKACIJE: tuple[ReportSpec, ...] = (
    ReportSpec("commits_per_day", "Commit-i po danu", Section.RAZVOJ,
               "Koliko je commit-a napravljeno svakog dana, po repozitorijumu.",
               supports_project=True),
    ReportSpec("pipeline_success_rate", "Uspešnost pipeline-a", Section.ISPORUKA,
               "Udeo uspešnih pokretanja po danu.", supports_project=True),
    ReportSpec("pipeline_duration", "Trajanje pokretanja", Section.ISPORUKA,
               "Prosečno i najgore trajanje, u sekundama.",
               supports_project=True),
    ReportSpec("failing_steps", "Koraci koji padaju", Section.ISPORUKA,
               "Koji korak najčešće pada — da „pipeline pada“ dobije adresu.",
               supports_project=True),
    ReportSpec("deploy_frequency", "Učestalost isporuka", Section.ISPORUKA,
               "Isporuke po danu i udeo vraćenih unazad."),
    ReportSpec("service_uptime", "Dostupnost servisa", Section.SISTEM,
               "Udeo vremena u kojem je servis odgovarao."),
    ReportSpec("alerts_per_service", "Alarmi po servisu", Section.SISTEM,
               "Koliko alarma i koliko minuta u alarmu."),
    ReportSpec("ai_cost_by_model", "Trošak po modelu", Section.AI,
               "Pozivi, tokeni i trošak po modelu.", supports_project=True),
    ReportSpec("ai_local_vs_online", "Lokalno naspram plaćenog", Section.AI,
               "Koliko je poziva stvarno plaćeno.", supports_project=True),
)

_PO_IMENU = {spec.name: spec for spec in SPECIFIKACIJE}


class AnalyticsService:
    """Izvestaji nad podacima ostalih faza."""

    def __init__(self, *, database_path: Path | None = None,
                 ops_database_path: Path | None = None,
                 repositories: RepositoryRepository | None = None,
                 git: LocalGitProvider | None = None,
                 cache: ReportCache | None = None,
                 now: str | None = None) -> None:
        self._db = database_path or codium_database_path()
        self._ops = ops_database_path or codium_ops_database_path()
        self._repos = repositories or RepositoryRepository(self._db)
        self._git = git or LocalGitProvider()
        # `is not None`, ne `or`: `ReportCache` definise `__len__`, pa je PRAZAN
        # kes falsy — `cache or ReportCache()` bi ubrizgan kes tiho zamenio
        # novim, i svaki poziv bi promasio. Uhvaceno testom isteka kesa.
        self._cache = cache if cache is not None else ReportCache()
        # Fiksirano „sada“ za testove; u radu je None, pa SQL koristi `now`.
        self._now = now

    # ----------          JAVNO          ----------

    def specs(self) -> tuple[ReportSpec, ...]:
        return SPECIFIKACIJE

    def report(self, name: str, period: str = Period.D30,
               project_id: int | None = None) -> Report:
        """Jedan izvestaj. Rezultat se kesira po imenu, periodu i filteru."""

        spec = _PO_IMENU.get(name)
        if spec is None:
            raise UnknownReport(
                f"Nepoznat izvestaj: {name}. "
                f"Dozvoljeno: {', '.join(_PO_IMENU)}.")

        dana = self._dana(period)
        # Filter koji izvestaj ne podrzava se ODBACUJE, ne prosledjuje: inace
        # bi kes vratio isti rezultat pod dva kljuca, a covek mislio da je
        # suzenje radilo.
        filter_projekta = project_id if spec.supports_project else None
        kljuc = f"{name}|{period}|{filter_projekta}"

        return self._cache.get_or_compute(
            kljuc, lambda: self._izracunaj(name, period, dana, filter_projekta))

    def summary(self, period: str = Period.D30) -> dict[str, float]:
        """Zbirna tabla: brojevi za period i promena u odnosu na prethodni.

        Prethodni period je JEDNAKE duzine, odmah pre ovog — zato se poredi
        „poslednjih 7 dana“ sa „7 dana pre njih“, a ne sa proizvoljnim rasponom.
        """

        dana = self._dana(period)
        kljuc = f"__summary__|{period}"
        return self._cache.get_or_compute(
            kljuc, lambda: self._izracunaj_zbir(period, dana))

    # ----------          RACUNANJE          ----------

    def _izracunaj(self, name: str, period: str, dana: int,
                   project_id: int | None) -> Report:
        serije, ukupno = self._pozovi(name, dana, project_id)
        return Report(name=name, period=period, series=serije, totals=ukupno)

    def _pozovi(self, name: str, dana: int,
                project_id: int | None) -> tuple[list[Series], dict]:
        if name == "commits_per_day":
            return self._commits(dana, project_id)
        if name == "service_uptime":
            return queries.service_uptime(self._ops, self._db, dana,
                                          now=self._now)
        if name == "alerts_per_service":
            return queries.alerts_per_service(self._db, dana, now=self._now)
        if name in ("ai_cost_by_model", "ai_local_vs_online"):
            posao = getattr(queries, name)
            return posao(self._ops, dana, project_id=project_id, now=self._now)

        posao = getattr(queries, name)
        return posao(self._db, dana, project_id=project_id, now=self._now)

    def _izracunaj_zbir(self, period: str, dana: int) -> dict[str, float]:
        """Kljucni brojevi za period, uz iste brojeve za prethodni period."""

        _, pipeline_sada = queries.pipeline_success_rate(self._db, dana,
                                                         now=self._now)
        _, deploy_sada = queries.deploy_frequency(self._db, dana, now=self._now)
        _, ai_sada = queries.ai_cost_by_model(self._ops, dana, now=self._now)
        _, up_sada = queries.service_uptime(self._ops, self._db, dana,
                                            now=self._now)

        # Prethodni period: isti upiti, ali pomereni za `dana` unazad. Racuna
        # se preko dvostrukog perioda minus tekuci, jer upiti primaju samo
        # „koliko dana unazad“ — bez toga bi svaki morao i gornju granicu.
        _, pipeline_pre = self._prethodni(
            lambda d: queries.pipeline_success_rate(self._db, d, now=self._now),
            dana, pipeline_sada, ("runs", "success"))
        _, deploy_pre = self._prethodni(
            lambda d: queries.deploy_frequency(self._db, d, now=self._now),
            dana, deploy_sada, ("deploys", "rolled_back"))
        _, ai_pre = self._prethodni(
            lambda d: queries.ai_cost_by_model(self._ops, d, now=self._now),
            dana, ai_sada, ("calls", "cost_usd"))

        return {
            "period_days": float(dana),
            "runs": pipeline_sada["runs"],
            "runs_prev": pipeline_pre["runs"],
            "success_rate": pipeline_sada["success_rate"],
            "deploys": deploy_sada["deploys"],
            "deploys_prev": deploy_pre["deploys"],
            "rollback_rate": deploy_sada["rollback_rate"],
            "ai_calls": ai_sada["calls"],
            "ai_calls_prev": ai_pre["calls"],
            "ai_cost_usd": ai_sada["cost_usd"],
            "ai_cost_usd_prev": ai_pre["cost_usd"],
            "avg_uptime": up_sada["avg_uptime"],
        }

    def _prethodni(self, posao, dana: int, tekuci: dict,
                   polja: tuple[str, ...]) -> tuple[None, dict]:
        """Vrednosti za period PRE tekuceg, izvedene oduzimanjem.

        Upit za dvostruki period vraca zbir oba; tekuci se oduzme i ostaje
        prethodni. Tako svaki upit ostaje sa jednim parametrom („koliko dana
        unazad"), umesto da svi dobiju i gornju granicu zbog jedne plocice.
        """

        _, dvostruko = posao(dana * 2)
        return (None, {polje: round(dvostruko.get(polje, 0.0)
                                    - tekuci.get(polje, 0.0), 4)
                       for polje in polja})

    # ----------          GIT          ----------

    def _commits(self, dana: int,
                 project_id: int | None) -> tuple[list[Series], dict]:
        """Commit-i po danu, po repozitorijumu.

        Commit-i NISU u bazi — E2 ih namerno ne kopira („git im je vec baza“),
        pa se ovde citaju kroz `GitProvider`. Zato je bas ovaj izvestaj
        najskuplji: jedan podproces po repozitorijumu. Kes od 60 s postoji
        pre svega zbog njega.
        """

        serije: list[Series] = []
        ukupno = 0
        for repo in self._repos.list(project_id):
            try:
                commit_i = self._git.log(repo.local_path, "", 500, 0)
            except (GitError, OSError):
                # Repozitorijum kojeg vise nema na disku preskace se — jedan
                # nestao folder ne sme da obori ceo izvestaj.
                continue

            po_danu: dict[str, int] = {}
            for commit in commit_i:
                dan = (commit.date or "")[:10]
                if dan:
                    po_danu[dan] = po_danu.get(dan, 0) + 1

            granica = self._granica(dana)
            tacke = [queries.Point(dan, float(broj))
                     for dan, broj in sorted(po_danu.items())
                     if dan >= granica]
            if tacke:
                serije.append(Series(label=repo.name, points=tacke))
                ukupno += int(sum(t.y for t in tacke))

        aktivnih_dana = len({t.x for s in serije for t in s.points})
        return (serije, {"commits": float(ukupno),
                         "active_days": float(aktivnih_dana),
                         "repositories": float(len(serije))})

    def _granica(self, dana: int) -> str:
        """Datum od kojeg se commit-i broje (`GGGG-MM-DD`)."""

        from datetime import UTC, datetime, timedelta

        osnova = (datetime.fromisoformat(self._now).replace(tzinfo=UTC)
                  if self._now else datetime.now(UTC))
        return (osnova - timedelta(days=dana)).date().isoformat()

    # ----------          POMOCNO          ----------

    def _dana(self, period: str) -> int:
        dana = DANA.get(period)
        if dana is None:
            raise UnknownPeriod(
                f"Nepoznat period: {period}. "
                f"Dozvoljeno: {', '.join(DANA)}.")
        return dana
