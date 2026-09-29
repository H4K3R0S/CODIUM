# ========== SERVIS CODIUM ==========
# Poslovna logika CODIUM domena: kreiranje sa validacijom, jedinstveni slug
# projekta i aktivni kontekst za beleške (auto project_id/client_id/source).
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from core.domains.codium.dev_server import dev_server_url
from core.domains.codium.models import (
    AgendaItem,
    Client,
    ClientCreate,
    ClientUpdate,
    Note,
    NoteCreate,
    NoteSource,
    NoteStatus,
    NoteUpdate,
    Project,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    ProjectVisibility,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)
from core.domains.codium.repository import CodiumRepository


def _slugify(text: str) -> str:
    """Pretvara ime u slug (mala slova, crtice, bez posebnih znakova)."""

    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "projekat"


# Sortni podtekst za stavke agende bez razumljivog datuma — idu na kraj.
_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    """
    Tolerantno parsira ISO datum/vreme u aware UTC datetime.

    Prihvata pun timestamp ('...T..:..:..'), sa 'Z' sufiksom ili offsetom, i
    goli datum ('GGGG-MM-DD' → ponoć UTC). Naivne vrednosti se tretiraju kao
    UTC da bi poređenje i sortiranje bili konzistentni. Neparsivo → None.
    """

    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class CodiumService:
    """Poslovna logika CODIUM domena (projekti, klijenti, taskovi, beleške)."""

    def __init__(self, repository: CodiumRepository) -> None:
        self._repository = repository

    # ==========          PROJEKTI          ==========

    def create_project(self, project: ProjectCreate) -> Project:
        """Pravi projekat sa jedinstvenim slug-om; privatni projekat nema klijenta."""

        # Privatni projekat ne sme imati klijenta.
        if project.visibility is ProjectVisibility.PRIVATE:
            project.client_id = None

        # Lokalni host: iz porta se automatski izvodi preview URL (localhost:port),
        # da URL postoji već pri kreiranju i korisnik ga ne unosi ručno.
        if not project.preview_url and project.dev_port is not None:
            project.preview_url = dev_server_url(project.dev_port)

        base = project.slug if project.slug else _slugify(project.name)
        slug = self._unique_slug(_slugify(base))
        return self._repository.create_project(project, slug)

    def list_projects(
        self, visibility: ProjectVisibility | None = None,
    ) -> list[Project]:
        return self._repository.list_projects(visibility)

    def get_project(self, project_id: int) -> Project | None:
        return self._repository.get_project(project_id)

    def update_project(
        self, project_id: int, change: ProjectUpdate,
    ) -> Project | None:
        return self._repository.update_project(project_id, change)

    def _unique_slug(self, base: str) -> str:
        """Vraća slug koji se ne sudara; dodaje -2, -3, ... po potrebi."""

        if not self._repository.slug_exists(base):
            return base
        counter = 2
        while self._repository.slug_exists(f"{base}-{counter}"):
            counter += 1
        return f"{base}-{counter}"

    # ==========          KLIJENTI          ==========

    def create_client(self, client: ClientCreate) -> Client:
        return self._repository.create_client(client)

    def list_clients(self) -> list[Client]:
        return self._repository.list_clients()

    def get_client(self, client_id: int) -> Client | None:
        return self._repository.get_client(client_id)

    def update_client(
        self, client_id: int, change: ClientUpdate,
    ) -> Client | None:
        return self._repository.update_client(client_id, change)

    # ==========          TASKOVI          ==========

    def create_task(self, task: TaskCreate) -> Task:
        return self._repository.create_task(task)

    def list_tasks(self, project_id: int | None = None) -> list[Task]:
        return self._repository.list_tasks(project_id)

    def get_task(self, task_id: int) -> Task | None:
        return self._repository.get_task(task_id)

    def update_task(self, task_id: int, change: TaskUpdate) -> Task | None:
        """Menja task; prelazak na 'done' beleži trenutak završetka."""

        # Kad task prelazi u 'done' bez eksplicitnog vremena, upiši sadašnji trenutak.
        if change.status is TaskStatus.DONE and change.completed_at is None:
            change.completed_at = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
        return self._repository.update_task(task_id, change)

    # ==========          BELEŠKE          ==========

    def create_note(
        self,
        note: NoteCreate,
        active_project_id: int | None = None,
    ) -> Note:
        """
        Pravi belešku uz aktivni kontekst.

        Ako je zadat `active_project_id` (a beleška ga sama nema), beleška se
        vezuje za taj projekat. Ako projekat ima klijenta, `client_id` se
        auto-popunjava. Bez ikakvog projekta beleška ide u globalni inbox
        (`project_id` NULL).
        """

        if note.project_id is None and active_project_id is not None:
            note.project_id = active_project_id

        if note.project_id is not None and note.client_id is None:
            project = self._repository.get_project(note.project_id)
            if project is not None and project.client_id is not None:
                note.client_id = project.client_id

        return self._repository.create_note(note)

    def list_notes(
        self,
        project_id: int | None = None,
        *,
        inbox_only: bool = False,
    ) -> list[Note]:
        return self._repository.list_notes(project_id, inbox_only=inbox_only)

    def get_note(self, note_id: int) -> Note | None:
        return self._repository.get_note(note_id)

    def update_note(self, note_id: int, change: NoteUpdate) -> Note | None:
        return self._repository.update_note(note_id, change)

    # ==========          AGENDA (rokovi + podsetnici)          ==========

    def list_agenda(
        self,
        *,
        days_ahead: int = 14,
        include_overdue: bool = True,
        project_id: int | None = None,
        now: datetime | None = None,
    ) -> list[AgendaItem]:
        """
        Objedinjena agenda: rokovi taskova (`due_at`), podsetnici beleški
        (`reminder_at`) i rokovi projekata (`deadline_at`).

        Uzima stavke koje padaju u prozor [sada, sada + `days_ahead` dana].
        Ako je `include_overdue`, dodaje i one kojima je rok prošao a nisu
        završene. `project_id` sužava na jedan projekat. Sortirano po vremenu
        rastuće; probijeni rokovi (najstariji prvi) dolaze na vrh.
        """

        moment = now or datetime.now(timezone.utc)
        horizon = moment + timedelta(days=days_ahead)
        items: list[AgendaItem] = []

        def consider(item: AgendaItem, when: datetime | None) -> None:
            """Ubaci stavku ako je probijen rok (uz dozvolu) ili je u prozoru."""
            if when is None:
                return
            if when < moment:
                if include_overdue:
                    items.append(item)
                return
            if when <= horizon:
                items.append(item)

        # --- Taskovi sa rokom (preskoči završene) ---
        for task in self._repository.list_tasks(project_id):
            if task.due_at is None or task.status is TaskStatus.DONE:
                continue
            when = _parse_iso(task.due_at)
            consider(
                AgendaItem(
                    kind="task",
                    ref_id=task.id,
                    title=task.title,
                    at=task.due_at,
                    overdue=when is not None and when < moment,
                    project_id=task.project_id,
                    client_id=None,
                    status=task.status.value,
                    priority=task.priority.value,
                ),
                when,
            )

        # --- Beleške sa podsetnikom (samo aktivne) ---
        for note in self._repository.list_notes(project_id):
            if note.reminder_at is None or note.status is not NoteStatus.ACTIVE:
                continue
            when = _parse_iso(note.reminder_at)
            consider(
                AgendaItem(
                    kind="note",
                    ref_id=note.id,
                    title=note.title,
                    at=note.reminder_at,
                    overdue=when is not None and when < moment,
                    project_id=note.project_id,
                    client_id=note.client_id,
                    status=note.status.value,
                    priority=note.importance.value,
                ),
                when,
            )

        # --- Rokovi projekata (preskoči zatvorene) ---
        closed = {ProjectStatus.DONE, ProjectStatus.ARCHIVED}
        for project in self._repository.list_projects():
            if project_id is not None and project.id != project_id:
                continue
            if project.deadline_at is None or project.status in closed:
                continue
            when = _parse_iso(project.deadline_at)
            consider(
                AgendaItem(
                    kind="project",
                    ref_id=project.id,
                    title=project.name,
                    at=project.deadline_at,
                    overdue=when is not None and when < moment,
                    project_id=project.id,
                    client_id=project.client_id,
                    status=project.status.value,
                    priority=project.priority.value,
                ),
                when,
            )

        # Sort po stvarnom trenutku; neparsirane na kraj.
        items.sort(key=lambda item: _parse_iso(item.at) or _FAR_FUTURE)
        return items


__all__ = ["CodiumService", "NoteSource"]
