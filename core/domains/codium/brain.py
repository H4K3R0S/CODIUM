# ========== CODIUM PROJECT BRAIN ==========
# Generisanje i čitanje `.codium/` foldera projekta: instrukcije + istorija rada.
# Projektni ekvivalent `.ai/` foldera. Format prost (Markdown) — čita ga danas
# Claude/Codex, kasnije lokalni CODIUM agent. Zato mora biti stabilan.
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from core.domains.codium.models import Project
from core.domains.codium.paths import codium_paths
from core.domains.codium.repository import CodiumRepository

# Fajlovi skeleta (ime → naslov sekcije za template). Redosled je bitan za prikaz.
BRAIN_FILES: tuple[tuple[str, str], ...] = (
    ("project.md", "Projekat"),
    ("instructions.md", "Instrukcije za AI"),
    ("architecture.md", "Arhitektura"),
    ("goals.md", "Ciljevi"),
    ("tasks.md", "Taskovi"),
    ("decisions.md", "Odluke (decision log)"),
    ("testing.md", "Testiranje"),
    ("security.md", "Bezbednost"),
    ("known-issues.md", "Poznati problemi"),
    ("handoff.md", "Predaja (handoff)"),
)

# Podfolderi skeleta.
BRAIN_DIRS: tuple[str, ...] = ("dev-log", "dev-log/entries", "design", "context", "assets")

# Dozvoljena imena za čitanje (sprečava izlazak iz foldera).
READABLE_FILES: frozenset[str] = frozenset(
    name for name, _ in BRAIN_FILES
) | {"dev-log/INDEX.md"}


@dataclass
class BrainFileView:
    """Jedan fajl skeleta i da li postoji na disku."""

    name: str
    exists: bool


@dataclass
class BrainInfo:
    """Stanje brain foldera jednog projekta."""

    project_id: int
    path: str
    exists: bool
    files: list[BrainFileView]


@dataclass
class DevlogEntryInput:
    """Unos u projektni dev-log (jedna izmena/sesija)."""

    cilj: str = ""
    uradjeno: str = ""
    testovi: str = ""
    sledece: str = ""
    napomene: str = ""
    executor: str = ""


class CodiumBrainService:
    """Generiše i čita `.codium/` folder projekta (instrukcije + dev-log)."""

    def __init__(self, repository: CodiumRepository) -> None:
        self._repository = repository

    # ==========          PUTANJA          ==========

    def brain_dir(self, project: Project) -> Path:
        """
        Aktivna lokacija brain foldera.

        - Ako projekat ima `local_path` → `<local_path>/.codium/`.
        - Inače → registry `data/codium/projects/<id>/brain/`.
        """

        if project.local_path:
            return Path(project.local_path) / ".codium"
        return codium_paths.project_registry_brain(project.id)

    # ==========          GENERISANJE          ==========

    def generate(self, project: Project) -> BrainInfo:
        """
        Pravi skelet `.codium/` foldera; ne prepisuje postojeće fajlove.

        `project.md` se popunjava iz baze (samo ako fali). Ostali fajlovi
        dobijaju template sa naslovima sekcija. Putanja se pamti u
        `Project.project_brain_path`.
        """

        base = self.brain_dir(project)
        base.mkdir(parents=True, exist_ok=True)
        for sub in BRAIN_DIRS:
            (base / sub).mkdir(parents=True, exist_ok=True)

        # Fajlovi skeleta — piše samo ono što fali.
        for name, heading in BRAIN_FILES:
            target = base / name
            if target.exists():
                continue
            if name == "project.md":
                target.write_text(self._project_markdown(project), encoding="utf-8")
            else:
                target.write_text(
                    self._template_markdown(heading), encoding="utf-8",
                )

        index = base / "dev-log" / "INDEX.md"
        if not index.exists():
            index.write_text(self._devlog_index_header(project), encoding="utf-8")

        # Zapamti putanju u bazi (ako se promenila).
        path_str = str(base)
        if project.project_brain_path != path_str:
            from core.domains.codium.models import ProjectUpdate

            self._repository.update_project(
                project.id, ProjectUpdate(project_brain_path=path_str),
            )

        return self.info(project)

    def info(self, project: Project) -> BrainInfo:
        """Vraća stanje brain foldera (postoji li, koji fajlovi postoje)."""

        base = self.brain_dir(project)
        files = [
            BrainFileView(name=name, exists=(base / name).exists())
            for name, _ in BRAIN_FILES
        ]
        return BrainInfo(
            project_id=project.id,
            path=str(base),
            exists=base.exists(),
            files=files,
        )

    # ==========          ČITANJE          ==========

    def read_file(self, project: Project, name: str) -> str | None:
        """Čita jedan dozvoljen brain fajl; None ako ne postoji/nije dozvoljen."""

        if name not in READABLE_FILES:
            return None
        target = self.brain_dir(project) / name
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8")

    # ==========          DEV-LOG          ==========

    def add_devlog_entry(
        self, project: Project, entry: DevlogEntryInput,
    ) -> str:
        """
        Dodaje dev-log unos za današnji datum i osigurava red u INDEX.md.

        Ako fajl za datum već postoji, dopisuje novi blok (Sesija N). Vraća
        naziv fajla unosa (`entries/GGGG-MM-DD.md`).
        """

        base = self.brain_dir(project)
        entries_dir = base / "dev-log" / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()  # noqa: DTZ011
        entry_file = entries_dir / f"{today}.md"

        if entry_file.exists():
            existing = entry_file.read_text(encoding="utf-8")
            session = existing.count("## Sesija") + 2
            block = self._devlog_block(entry, session)
            entry_file.write_text(existing.rstrip() + "\n\n" + block, encoding="utf-8")
        else:
            entry_file.write_text(
                f"# {today}\n\n" + self._devlog_block(entry, session=1),
                encoding="utf-8",
            )

        self._ensure_index_row(base, today)
        return f"entries/{today}.md"

    def read_devlog_index(self, project: Project) -> str | None:
        """Sadržaj `dev-log/INDEX.md` (ili None ako brain nije generisan)."""

        return self.read_file(project, "dev-log/INDEX.md")

    # ==========          TEMPLATE-I          ==========

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _project_markdown(self, project: Project) -> str:
        client = (
            self._repository.get_client(project.client_id)
            if project.client_id is not None
            else None
        )
        client_line = client.name if client is not None else "—"
        return (
            f"# {project.name}\n\n"
            f"- **Slug:** {project.slug}\n"
            f"- **Tip:** {project.type or '—'}\n"
            f"- **Vidljivost:** {project.visibility.value}\n"
            f"- **Status:** {project.status.value}\n"
            f"- **Prioritet:** {project.priority.value}\n"
            f"- **Klijent:** {client_line}\n"
            f"- **Lokalna putanja:** {project.local_path or '—'}\n"
            f"- **Repozitorijum:** {project.repository_url or '—'}\n"
            f"- **Live:** {project.live_url or '—'}\n"
            f"- **Staging:** {project.staging_url or '—'}\n"
            f"- **Stack:** {project.stack or '—'}\n"
            f"- **Rok:** {project.deadline_at or '—'}\n\n"
            "## Opis\n\n"
            "_Dopuni opis projekta._\n"
        )

    @staticmethod
    def _template_markdown(heading: str) -> str:
        return f"# {heading}\n\n_Dopuni sekciju._\n"

    @staticmethod
    def _devlog_index_header(project: Project) -> str:
        return (
            f"# DEV-LOG — {project.name}\n\n"
            "> Dnevnik rada na projektu. Svaki unos = fajl u "
            "`entries/GGGG-MM-DD.md`. Najnovije prvo.\n\n"
            "## Unosi (najnovije prvo)\n\n"
            "| Datum | Fajl |\n"
            "|---|---|\n"
        )

    @staticmethod
    def _devlog_block(entry: DevlogEntryInput, session: int) -> str:
        head = "" if session == 1 else f"## Sesija {session}\n\n"
        return (
            f"{head}"
            f"Cilj: {entry.cilj or '—'}\n"
            f"Urađeno: {entry.uradjeno or '—'}\n"
            f"Testovi/provera: {entry.testovi or '—'}\n"
            f"Sledeće: {entry.sledece or '—'}\n"
            f"Napomene: {entry.napomene or '—'}\n"
            f"Executor/model: {entry.executor or '—'}\n"
        )

    @staticmethod
    def _ensure_index_row(base: Path, day: str) -> None:
        """Ubacuje red za datum u INDEX tabelu (ako ga još nema)."""

        index = base / "dev-log" / "INDEX.md"
        row = f"| {day} | [entries/{day}.md](entries/{day}.md) |"
        if index.exists():
            content = index.read_text(encoding="utf-8")
            if row in content:
                return
            lines = content.rstrip().split("\n")
        else:
            lines = ["# DEV-LOG", "", "| Datum | Fajl |", "|---|---|"]
            content = "\n".join(lines)

        # Ubaci odmah ispod reda razdvajanja tabele (|---|---|).
        for i, line in enumerate(lines):
            if set(line.replace("|", "").strip()) <= {"-", " "} and "-" in line:
                lines.insert(i + 1, row)
                break
        else:
            lines.append(row)

        index.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "BRAIN_FILES",
    "BrainFileView",
    "BrainInfo",
    "CodiumBrainService",
    "DevlogEntryInput",
]
