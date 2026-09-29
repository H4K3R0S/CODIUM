# ========== ROUTER: CODIUM (razvoj softvera) ==========
# Izlaže CodiumService: projekti, klijenti, taskovi i beleške.
# Tok: GUI -> ovaj router -> service -> repository -> SQLite (codium.db).
from __future__ import annotations

from enum import Enum
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas.codium import (
    AgendaItemResponse,
    AgendaResponse,
    BrainFileContentResponse,
    BrainInfoResponse,
    ClientCreateRequest,
    ClientResponse,
    ClientsResponse,
    ClientUpdateRequest,
    DevlogEntryRequest,
    DevlogEntryResponse,
    DevlogIndexResponse,
    DevServerStatusResponse,
    NoteCreateRequest,
    NoteResponse,
    NotesResponse,
    NoteUpdateRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectsResponse,
    ProjectUpdateRequest,
    TaskCreateRequest,
    TaskResponse,
    TasksResponse,
    TaskUpdateRequest,
)
from core.domains.codium import (
    ClientCreate,
    ClientUpdate,
    CodiumBrainService,
    CodiumRepository,
    CodiumService,
    DevlogEntryInput,
    DevServerError,
    NoteCreate,
    NoteImportance,
    NoteSource,
    NoteStatus,
    NoteUpdate,
    Priority,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    ProjectVisibility,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
    codium_dev_server,
)

router = APIRouter(
    prefix="/api/v1/codium",
    tags=["Codium"],
)


def get_service() -> CodiumService:
    return CodiumService(CodiumRepository())


def get_brain_service() -> CodiumBrainService:
    return CodiumBrainService(CodiumRepository())


_EnumT = TypeVar("_EnumT", bound=Enum)


def _parse_enum(
    enum_cls: type[_EnumT], value: str | None, field: str,
) -> _EnumT | None:
    """Pretvara string u enum ili vraća 422 sa jasnom porukom."""

    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=f"Nepoznata vrednost za {field}: {value}",
        ) from error


# ==========          PROJEKTI          ==========

@router.get("/projects", response_model=ProjectsResponse)
def list_projects(
    visibility: str | None = None,
    service: CodiumService = Depends(get_service),
) -> ProjectsResponse:
    """Svi projekti; opciono filtrirani po vidljivosti (client|private)."""

    scope = _parse_enum(ProjectVisibility, visibility, "visibility")
    projects = service.list_projects(scope)
    return ProjectsResponse(
        count=len(projects),
        projects=[ProjectResponse.from_domain(p) for p in projects],
    )


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    service: CodiumService = Depends(get_service),
) -> ProjectResponse:
    """Dodaje nov projekat (slug se izvodi iz imena ako nije zadat)."""

    visibility = _parse_enum(
        ProjectVisibility, payload.visibility, "visibility",
    ) or ProjectVisibility.PRIVATE
    priority = _parse_enum(
        Priority, payload.priority, "priority",
    ) or Priority.NORMAL

    created = service.create_project(
        ProjectCreate(
            name=payload.name,
            type=payload.type,
            visibility=visibility,
            client_id=payload.client_id,
            local_path=payload.local_path,
            repository_url=payload.repository_url,
            stack=payload.stack,
            priority=priority,
            deadline_at=payload.deadline_at,
            dev_command=payload.dev_command,
            dev_port=payload.dev_port,
            preview_url=payload.preview_url,
            slug=payload.slug,
        )
    )
    return ProjectResponse.from_domain(created)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    service: CodiumService = Depends(get_service),
) -> ProjectResponse:
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekat ne postoji.")
    return ProjectResponse.from_domain(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    service: CodiumService = Depends(get_service),
) -> ProjectResponse:
    change = ProjectUpdate(
        name=payload.name,
        type=payload.type,
        visibility=_parse_enum(
            ProjectVisibility, payload.visibility, "visibility",
        ),
        status=_parse_enum(ProjectStatus, payload.status, "status"),
        client_id=payload.client_id,
        local_path=payload.local_path,
        project_brain_path=payload.project_brain_path,
        repository_url=payload.repository_url,
        live_url=payload.live_url,
        staging_url=payload.staging_url,
        preview_url=payload.preview_url,
        stack=payload.stack,
        priority=_parse_enum(Priority, payload.priority, "priority"),
        dev_command=payload.dev_command,
        dev_port=payload.dev_port,
        started_at=payload.started_at,
        deadline_at=payload.deadline_at,
        last_opened_at=payload.last_opened_at,
    )
    updated = service.update_project(project_id, change)
    if updated is None:
        raise HTTPException(status_code=404, detail="Projekat ne postoji.")
    return ProjectResponse.from_domain(updated)


# ==========          DEV SERVER (lokalni host)          ==========

@router.post(
    "/projects/{project_id}/dev/start",
    response_model=DevServerStatusResponse,
)
def start_dev_server(
    project_id: int,
    service: CodiumService = Depends(get_service),
) -> DevServerStatusResponse:
    """Pokreće lokalni dev server projekta (komanda + local_path iz baze)."""

    project = _require_project(project_id, service)
    try:
        status = codium_dev_server.start(
            project_id, project.dev_command, project.local_path,
        )
    except DevServerError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return DevServerStatusResponse.from_status(status, project.preview_url)


@router.post(
    "/projects/{project_id}/dev/stop",
    response_model=DevServerStatusResponse,
)
def stop_dev_server(
    project_id: int,
    service: CodiumService = Depends(get_service),
) -> DevServerStatusResponse:
    """Gasi lokalni dev server projekta."""

    project = _require_project(project_id, service)
    status = codium_dev_server.stop(project_id)
    return DevServerStatusResponse.from_status(status, project.preview_url)


@router.get(
    "/projects/{project_id}/dev/status",
    response_model=DevServerStatusResponse,
)
def dev_server_status(
    project_id: int,
    service: CodiumService = Depends(get_service),
) -> DevServerStatusResponse:
    """Stanje lokalnog dev servera projekta (radi/pid/komanda + preview URL)."""

    project = _require_project(project_id, service)
    status = codium_dev_server.status(project_id)
    return DevServerStatusResponse.from_status(status, project.preview_url)


# ==========          KLIJENTI          ==========

@router.get("/clients", response_model=ClientsResponse)
def list_clients(
    service: CodiumService = Depends(get_service),
) -> ClientsResponse:
    clients = service.list_clients()
    return ClientsResponse(
        count=len(clients),
        clients=[ClientResponse.from_domain(c) for c in clients],
    )


@router.post("/clients", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreateRequest,
    service: CodiumService = Depends(get_service),
) -> ClientResponse:
    created = service.create_client(
        ClientCreate(
            name=payload.name,
            company_name=payload.company_name,
            type=payload.type,
            email=payload.email,
            phone=payload.phone,
            website=payload.website,
            notes=payload.notes,
        )
    )
    return ClientResponse.from_domain(created)


@router.get("/clients/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    service: CodiumService = Depends(get_service),
) -> ClientResponse:
    client = service.get_client(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Klijent ne postoji.")
    return ClientResponse.from_domain(client)


@router.patch("/clients/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientUpdateRequest,
    service: CodiumService = Depends(get_service),
) -> ClientResponse:
    updated = service.update_client(
        client_id,
        ClientUpdate(
            name=payload.name,
            company_name=payload.company_name,
            type=payload.type,
            email=payload.email,
            phone=payload.phone,
            website=payload.website,
            notes=payload.notes,
        ),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Klijent ne postoji.")
    return ClientResponse.from_domain(updated)


# ==========          TASKOVI          ==========

@router.get("/tasks", response_model=TasksResponse)
def list_tasks(
    project_id: int | None = None,
    service: CodiumService = Depends(get_service),
) -> TasksResponse:
    """Taskovi; opciono filtrirani po projektu."""

    tasks = service.list_tasks(project_id)
    return TasksResponse(
        count=len(tasks),
        tasks=[TaskResponse.from_domain(t) for t in tasks],
    )


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreateRequest,
    service: CodiumService = Depends(get_service),
) -> TaskResponse:
    priority = _parse_enum(
        Priority, payload.priority, "priority",
    ) or Priority.NORMAL
    created = service.create_task(
        TaskCreate(
            title=payload.title,
            project_id=payload.project_id,
            description=payload.description,
            priority=priority,
            due_at=payload.due_at,
        )
    )
    return TaskResponse.from_domain(created)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    service: CodiumService = Depends(get_service),
) -> TaskResponse:
    change = TaskUpdate(
        title=payload.title,
        project_id=payload.project_id,
        description=payload.description,
        status=_parse_enum(TaskStatus, payload.status, "status"),
        priority=_parse_enum(Priority, payload.priority, "priority"),
        due_at=payload.due_at,
        completed_at=payload.completed_at,
    )
    updated = service.update_task(task_id, change)
    if updated is None:
        raise HTTPException(status_code=404, detail="Task ne postoji.")
    return TaskResponse.from_domain(updated)


# ==========          BELEŠKE          ==========

@router.get("/notes", response_model=NotesResponse)
def list_notes(
    project_id: int | None = None,
    inbox_only: bool = False,
    service: CodiumService = Depends(get_service),
) -> NotesResponse:
    """Beleške; po projektu, ili globalni inbox (inbox_only=true)."""

    notes = service.list_notes(project_id, inbox_only=inbox_only)
    return NotesResponse(
        count=len(notes),
        notes=[NoteResponse.from_domain(n) for n in notes],
    )


@router.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(
    payload: NoteCreateRequest,
    service: CodiumService = Depends(get_service),
) -> NoteResponse:
    """Dodaje belešku; bez projekta ide u globalni inbox (aktivni kontekst opcion)."""

    source = _parse_enum(
        NoteSource, payload.source, "source",
    ) or NoteSource.MANUAL
    importance = _parse_enum(
        NoteImportance, payload.importance, "importance",
    ) or NoteImportance.NORMAL

    created = service.create_note(
        NoteCreate(
            title=payload.title,
            body=payload.body,
            project_id=payload.project_id,
            client_id=payload.client_id,
            source=source,
            importance=importance,
            tags=payload.tags,
            reminder_at=payload.reminder_at,
        ),
        active_project_id=payload.active_project_id,
    )
    return NoteResponse.from_domain(created)


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: int,
    service: CodiumService = Depends(get_service),
) -> NoteResponse:
    note = service.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Beleška ne postoji.")
    return NoteResponse.from_domain(note)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    payload: NoteUpdateRequest,
    service: CodiumService = Depends(get_service),
) -> NoteResponse:
    change = NoteUpdate(
        title=payload.title,
        body=payload.body,
        project_id=payload.project_id,
        client_id=payload.client_id,
        source=_parse_enum(NoteSource, payload.source, "source"),
        importance=_parse_enum(
            NoteImportance, payload.importance, "importance",
        ),
        tags=payload.tags,
        reminder_at=payload.reminder_at,
        status=_parse_enum(NoteStatus, payload.status, "status"),
    )
    updated = service.update_note(note_id, change)
    if updated is None:
        raise HTTPException(status_code=404, detail="Beleška ne postoji.")
    return NoteResponse.from_domain(updated)


# ==========          AGENDA (rokovi + podsetnici)          ==========

@router.get("/agenda", response_model=AgendaResponse)
def list_agenda(
    days_ahead: int = 14,
    include_overdue: bool = True,
    project_id: int | None = None,
    service: CodiumService = Depends(get_service),
) -> AgendaResponse:
    """
    Objedinjena agenda: rokovi taskova, podsetnici beleški i rokovi projekata
    u narednih `days_ahead` dana (+ probijeni rokovi ako `include_overdue`).
    """

    days = max(0, min(days_ahead, 365))
    items = service.list_agenda(
        days_ahead=days,
        include_overdue=include_overdue,
        project_id=project_id,
    )
    return AgendaResponse(
        count=len(items),
        days_ahead=days,
        include_overdue=include_overdue,
        items=[AgendaItemResponse.from_domain(i) for i in items],
    )


# ==========          PROJECT BRAIN (.codium/)          ==========

def _require_project(project_id: int, service: CodiumService):
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekat ne postoji.")
    return project


@router.get("/projects/{project_id}/brain", response_model=BrainInfoResponse)
def get_brain(
    project_id: int,
    service: CodiumService = Depends(get_service),
    brain: CodiumBrainService = Depends(get_brain_service),
) -> BrainInfoResponse:
    """Stanje `.codium/` foldera (postoji li, koji fajlovi postoje)."""

    project = _require_project(project_id, service)
    return BrainInfoResponse.from_domain(brain.info(project))


@router.post(
    "/projects/{project_id}/brain",
    response_model=BrainInfoResponse,
    status_code=201,
)
def generate_brain(
    project_id: int,
    service: CodiumService = Depends(get_service),
    brain: CodiumBrainService = Depends(get_brain_service),
) -> BrainInfoResponse:
    """Generiše skelet `.codium/` foldera (ne prepisuje postojeće fajlove)."""

    project = _require_project(project_id, service)
    return BrainInfoResponse.from_domain(brain.generate(project))


@router.get(
    "/projects/{project_id}/brain/file",
    response_model=BrainFileContentResponse,
)
def get_brain_file(
    project_id: int,
    name: str,
    service: CodiumService = Depends(get_service),
    brain: CodiumBrainService = Depends(get_brain_service),
) -> BrainFileContentResponse:
    """Sadržaj jednog dozvoljenog brain fajla (read-only)."""

    project = _require_project(project_id, service)
    content = brain.read_file(project, name)
    if content is None:
        raise HTTPException(
            status_code=404, detail=f"Brain fajl ne postoji: {name}",
        )
    return BrainFileContentResponse(name=name, content=content)


@router.get(
    "/projects/{project_id}/brain/devlog",
    response_model=DevlogIndexResponse,
)
def get_brain_devlog(
    project_id: int,
    service: CodiumService = Depends(get_service),
    brain: CodiumBrainService = Depends(get_brain_service),
) -> DevlogIndexResponse:
    """Sadržaj `dev-log/INDEX.md` projekta."""

    project = _require_project(project_id, service)
    content = brain.read_devlog_index(project)
    if content is None:
        raise HTTPException(
            status_code=404, detail="Dev-log još nije generisan.",
        )
    return DevlogIndexResponse(content=content)


@router.post(
    "/projects/{project_id}/brain/devlog",
    response_model=DevlogEntryResponse,
    status_code=201,
)
def add_brain_devlog(
    project_id: int,
    payload: DevlogEntryRequest,
    service: CodiumService = Depends(get_service),
    brain: CodiumBrainService = Depends(get_brain_service),
) -> DevlogEntryResponse:
    """Dodaje dev-log unos za današnji datum (generiše brain ako fali)."""

    project = _require_project(project_id, service)
    # Osiguraj da skelet postoji pre upisa.
    if not brain.info(project).exists:
        brain.generate(project)
    file = brain.add_devlog_entry(
        project,
        DevlogEntryInput(
            cilj=payload.cilj,
            uradjeno=payload.uradjeno,
            testovi=payload.testovi,
            sledece=payload.sledece,
            napomene=payload.napomene,
            executor=payload.executor,
        ),
    )
    return DevlogEntryResponse(file=file)


# ==========          EXPLORER (file tree)          ==========


# Pod-router: fajl-explorer (izdvojeno radi veličine).
from apps.api.routers import codium_files

router.include_router(codium_files.router)
