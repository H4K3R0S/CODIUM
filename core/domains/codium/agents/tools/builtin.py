# ==========          ALATI PRVOG REZA          ==========
# Svaki alat je tanak omotac oko servisa koji vec postoji. Zastitu putanje ne
# pise nijedan od njih: `CodiumExplorer._safe` je vec brani, a dve provere
# znace dva mesta na kojima se gresi.
from __future__ import annotations

from core.domains.codium.agents.tools.registry import ToolRegistry, ToolSpec
from core.domains.codium.explorer import CodiumExplorer
from core.domains.codium.models import NoteCreate, TaskCreate
from core.domains.codium.pipelines.service import PipelineService
from core.domains.codium.repositories.providers.base import GitError
from core.domains.codium.repositories.service import RepositoryService
from core.domains.codium.service import CodiumService

# Koliko pogodaka pretrage se vraca modelu. Vise od ovoga je zid teksta u
# kojem se ni covek ni model ne snalaze.
MAX_POGODAKA = 40

# Isti gornji limit koji ruta koristi za `/commits` — alat ne sme da trazi
# vise nego sto bi covek mogao kroz API.
MAX_LOG_LIMIT = 500


def search_code(explorer: CodiumExplorer, query: str,
                *, limit: int = MAX_POGODAKA) -> str:
    """Trazi niz po linijama celog stabla projekta.

    Jedini alat sa nesto novog koda: obilazak ide kroz explorer, pa i ovde
    vazi njegova ignore lista i njegova zabrana izlaska iz korena.
    """

    trazeno = (query or "").strip()
    if not trazeno:
        return "Prazan upit."

    pogoci: list[str] = []

    def obidji(rel: str) -> None:
        if len(pogoci) >= limit:
            return
        for node in explorer.list_dir(rel):
            if len(pogoci) >= limit:
                return
            if node.is_dir:
                obidji(node.path)
                continue
            sadrzaj = explorer.read_file(node.path)
            # Binarno i preveliko explorer ne ucitava; nema sta da se trazi.
            if sadrzaj.binary or sadrzaj.truncated:
                continue
            for broj, linija in enumerate(sadrzaj.content.splitlines(), start=1):
                if trazeno in linija:
                    pogoci.append(f"{node.path}:{broj}: {linija.strip()}")
                    if len(pogoci) >= limit:
                        return

    obidji("")
    if not pogoci:
        # Prazan string bi model procitao kao gresku alata.
        return f"Nema pogotka za `{trazeno}`."
    return "\n".join(pogoci)


def build_tools(explorer: CodiumExplorer, service: CodiumService | None,
                project_id: int | None,
                repos: RepositoryService | None = None,
                pipelines: PipelineService | None = None) -> ToolRegistry:
    """Sklapa alate vezane za jedan projekat.

    `repos` je opcion: bez njega git alati stoje u registru ali kazu da
    repozitorijuma nema. Tako model dobija recenicu, a ne izuzetak.
    Isto vazi za `pipelines`.
    """

    # Najvise pokretanja koja se ispisuju modelu; vise je zid teksta.
    MAX_POKRETANJA = 10

    def _prvi_repo():
        """Repozitorijum projekta nad kojim git alati rade.

        Kad ih projekat ima vise, uzima se najstariji upis — `list` vraca
        redove sortirane po `id`. Alat to kaze u odgovoru, da model ne bi
        mislio da je video sve.
        """

        if repos is None:
            return None
        parovi = repos.list(project_id)
        return parovi[0][0] if parovi else None

    def alat_git_log(limit: int = 20) -> str:
        repo = _prvi_repo()
        if repo is None:
            return "Projekat nema registrovan repozitorijum."
        try:
            broj = int(limit)
        except (TypeError, ValueError):
            return f"`limit` mora da bude broj, dobijeno `{limit}`."
        broj = max(1, min(broj, MAX_LOG_LIMIT))
        commiti = repos.history(repo.id, limit=broj)
        if not commiti:
            return f"Repozitorijum `{repo.name}` nema commit-a."
        redovi = [f"{c.short_sha} {c.date[:10]} {c.author}: {c.subject}"
                  for c in commiti]
        return f"Repozitorijum `{repo.name}`:\n" + "\n".join(redovi)

    def alat_git_diff(a: str = "", b: str = "", path: str = "") -> str:
        repo = _prvi_repo()
        if repo is None:
            return "Projekat nema registrovan repozitorijum."
        if not a or not b:
            return "Nedostaje `a` ili `b` — razlika trazi dva ref-a."
        try:
            razlika = repos.diff(repo.id, a, b, path or None)
        except GitError as greska:
            return f"Zahtev odbijen: {greska}"
        return razlika or "Nema razlike izmedju ta dva ref-a."

    def alat_read_file(rel: str = "") -> str:
        sadrzaj = explorer.read_file(rel)
        if sadrzaj.binary:
            return f"Fajl `{rel}` je binaran i ne cita se."
        if sadrzaj.truncated:
            return f"Fajl `{rel}` je prevelik za citanje."
        return sadrzaj.content

    def alat_list_dir(rel: str = "") -> str:
        stavke = explorer.list_dir(rel)
        if not stavke:
            return f"Folder `{rel or '.'}` je prazan."
        return "\n".join(
            f"{node.path}/" if node.is_dir else f"{node.path} ({node.size} B)"
            for node in stavke
        )

    def alat_search_code(query: str = "", limit: int = MAX_POGODAKA) -> str:
        return search_code(explorer, query, limit=int(limit))

    def alat_write_note(title: str = "", body: str = "") -> str:
        beleska = service.create_note(
            NoteCreate(title=title, body=body, project_id=project_id),
            active_project_id=project_id,
        )
        return f"Beleska upisana (id {beleska.id})."

    def alat_create_task(title: str = "", description: str = "") -> str:
        task = service.create_task(
            TaskCreate(title=title, description=description,
                       project_id=project_id),
        )
        return f"Zadatak napravljen (id {task.id})."

    def alat_write_file(rel: str = "", content: str = "") -> str:
        node = explorer.write_file(rel, content)
        return f"Upisano u `{node.path}` ({node.size} B)."

    def _nadji_pipeline(name: str):
        """Pipeline po imenu, u okviru prvog repozitorijuma projekta."""

        if pipelines is None:
            return None
        trazeno = (name or "").strip()
        if not trazeno:
            return None
        repo = _prvi_repo()
        repo_id = repo.id if repo is not None else None
        for pipeline in pipelines.list(repo_id):
            if pipeline.name == trazeno:
                return pipeline
        return None

    def alat_run_pipeline(name: str = "") -> str:
        if pipelines is None:
            return "Pipeline servis nije dostupan."
        pipeline = _nadji_pipeline(name)
        if pipeline is None:
            return f"Nema pipeline-a po imenu `{name}`."
        pokretanje = pipelines.run(pipeline.id, actor="agent")
        # Kraj se NE ceka: petlja agenta ne sme da visi dvadeset minuta.
        # Ishod se cita kroz `list_pipeline_runs`.
        return (f"Pipeline `{pipeline.name}` pokrenut, run {pokretanje.id}, "
                f"status {pokretanje.status}. Ishod procitaj kroz "
                f"list_pipeline_runs.")

    def alat_list_pipeline_runs(name: str = "",
                                limit: int = MAX_POKRETANJA) -> str:
        if pipelines is None:
            return "Pipeline servis nije dostupan."
        pipeline = _nadji_pipeline(name)
        if pipeline is None:
            return f"Nema pipeline-a po imenu `{name}`."
        try:
            koliko = max(1, min(int(limit), MAX_POKRETANJA))
        except (TypeError, ValueError):
            koliko = MAX_POKRETANJA
        istorija = pipelines.run_history(pipeline.id, limit=koliko)
        if not istorija:
            return f"Pipeline `{pipeline.name}` jos nije pokretan."
        redovi = [
            f"run {r.id}: {r.status} (kod {r.exit_code}) {r.finished_at or ''}".strip()
            for r in istorija
        ]
        return f"Pipeline `{pipeline.name}`:\n" + "\n".join(redovi)

    return ToolRegistry([
        ToolSpec(
            name="read_file",
            description="Cita sadrzaj tekstualnog fajla projekta.",
            args={"rel": "relativna putanja fajla"},
            action="file.read",
            run=alat_read_file,
        ),
        ToolSpec(
            name="list_dir",
            description="Izlistava jedan nivo foldera projekta.",
            args={"rel": "relativna putanja foldera, prazno za koren"},
            action="file.read",
            run=alat_list_dir,
        ),
        ToolSpec(
            name="search_code",
            description="Trazi niz po linijama celog projekta.",
            args={"query": "niz koji se trazi",
                  "limit": "najvise pogodaka (podrazumevano 40)"},
            action="file.read",
            run=alat_search_code,
        ),
        ToolSpec(
            name="write_note",
            description="Upisuje belesku uz projekat.",
            args={"title": "naslov beleske", "body": "tekst beleske"},
            action="note.write",
            run=alat_write_note,
        ),
        ToolSpec(
            name="create_task",
            description="Pravi zadatak u agendi projekta.",
            args={"title": "naslov zadatka", "description": "opis"},
            action="task.write",
            run=alat_create_task,
        ),
        ToolSpec(
            name="write_file",
            description="Upisuje sadrzaj u postojeci fajl projekta.",
            args={"rel": "relativna putanja fajla", "content": "nov sadrzaj"},
            action="file.write",
            run=alat_write_file,
            # Molba za odobrenje nosi otisak ovog sadrzaja.
            writes_content=True,
        ),
        ToolSpec(
            name="git_log",
            description="Istorija commit-a repozitorijuma projekta.",
            args={"limit": "najvise commit-a (podrazumevano 20)"},
            action="repo.read",
            run=alat_git_log,
        ),
        ToolSpec(
            name="git_diff",
            description="Razlika izmedju dva ref-a u repozitorijumu projekta.",
            args={"a": "prvi ref", "b": "drugi ref",
                  "path": "opciona putanja, prazno za ceo repozitorijum"},
            action="repo.read",
            run=alat_git_diff,
        ),
        ToolSpec(
            name="run_pipeline",
            description="Pokrece pipeline projekta po imenu; ne ceka kraj.",
            args={"name": "ime pipeline-a"},
            action="pipeline.run",
            run=alat_run_pipeline,
        ),
        ToolSpec(
            name="list_pipeline_runs",
            description="Istorija pokretanja jednog pipeline-a.",
            args={"name": "ime pipeline-a",
                  "limit": "najvise pokretanja (podrazumevano 10)"},
            action="pipeline.read",
            run=alat_list_pipeline_runs,
        ),
    ])
