# ========== ŠEME CODIUM ==========
from __future__ import annotations

from pydantic import BaseModel, Field

from core.domains.codium.brain import BrainInfo
from core.domains.codium.dev_server import DevServerStatus
from core.domains.codium.models import (
    AgendaItem,
    Client,
    Note,
    Project,
    Task,
)

# ==========          PROJEKAT          ==========

class ProjectResponse(BaseModel):
    id: int
    name: str
    slug: str
    type: str
    visibility: str
    status: str
    local_path: str | None
    project_brain_path: str | None
    client_id: int | None
    repository_url: str | None
    live_url: str | None
    staging_url: str | None
    preview_url: str | None
    stack: str
    priority: str
    dev_command: str
    dev_port: int | None
    started_at: str | None
    deadline_at: str | None
    last_opened_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, project: Project) -> ProjectResponse:
        return cls(
            id=project.id, name=project.name, slug=project.slug,
            type=project.type, visibility=project.visibility.value,
            status=project.status.value, local_path=project.local_path,
            project_brain_path=project.project_brain_path,
            client_id=project.client_id,
            repository_url=project.repository_url, live_url=project.live_url,
            staging_url=project.staging_url, preview_url=project.preview_url,
            stack=project.stack, priority=project.priority.value,
            dev_command=project.dev_command, dev_port=project.dev_port,
            started_at=project.started_at, deadline_at=project.deadline_at,
            last_opened_at=project.last_opened_at,
            created_at=project.created_at, updated_at=project.updated_at,
        )


class ProjectsResponse(BaseModel):
    count: int
    projects: list[ProjectResponse]


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = ""
    visibility: str = "private"
    client_id: int | None = None
    local_path: str | None = None
    repository_url: str | None = None
    stack: str = ""
    priority: str = "normal"
    deadline_at: str | None = None
    dev_command: str = ""
    dev_port: int | None = None
    preview_url: str | None = None
    slug: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    type: str | None = None
    visibility: str | None = None
    status: str | None = None
    client_id: int | None = None
    local_path: str | None = None
    project_brain_path: str | None = None
    repository_url: str | None = None
    live_url: str | None = None
    staging_url: str | None = None
    preview_url: str | None = None
    stack: str | None = None
    priority: str | None = None
    dev_command: str | None = None
    dev_port: int | None = None
    started_at: str | None = None
    deadline_at: str | None = None
    last_opened_at: str | None = None


# ==========          DEV SERVER (lokalni host)          ==========

class DevServerStatusResponse(BaseModel):
    project_id: int
    running: bool
    pid: int | None
    command: str | None
    preview_url: str | None

    @classmethod
    def from_status(
        cls, status: DevServerStatus, preview_url: str | None,
    ) -> DevServerStatusResponse:
        return cls(
            project_id=status.project_id, running=status.running,
            pid=status.pid, command=status.command, preview_url=preview_url,
        )


# ==========          KLIJENT          ==========

class ClientResponse(BaseModel):
    id: int
    name: str
    company_name: str
    type: str
    email: str | None
    phone: str | None
    website: str | None
    notes: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, client: Client) -> ClientResponse:
        return cls(
            id=client.id, name=client.name,
            company_name=client.company_name, type=client.type,
            email=client.email, phone=client.phone, website=client.website,
            notes=client.notes, created_at=client.created_at,
            updated_at=client.updated_at,
        )


class ClientsResponse(BaseModel):
    count: int
    clients: list[ClientResponse]


class ClientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    company_name: str = ""
    type: str = ""
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str = ""


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    company_name: str | None = None
    type: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str | None = None


# ==========          TASK          ==========

class TaskResponse(BaseModel):
    id: int
    project_id: int | None
    title: str
    description: str
    status: str
    priority: str
    due_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, task: Task) -> TaskResponse:
        return cls(
            id=task.id, project_id=task.project_id, title=task.title,
            description=task.description, status=task.status.value,
            priority=task.priority.value, due_at=task.due_at,
            completed_at=task.completed_at, created_at=task.created_at,
            updated_at=task.updated_at,
        )


class TasksResponse(BaseModel):
    count: int
    tasks: list[TaskResponse]


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    project_id: int | None = None
    description: str = ""
    priority: str = "normal"
    due_at: str | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    project_id: int | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_at: str | None = None
    completed_at: str | None = None


# ==========          BELEŠKA          ==========

class NoteResponse(BaseModel):
    id: int
    project_id: int | None
    client_id: int | None
    title: str
    body: str
    source: str
    importance: str
    tags: str
    reminder_at: str | None
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, note: Note) -> NoteResponse:
        return cls(
            id=note.id, project_id=note.project_id, client_id=note.client_id,
            title=note.title, body=note.body, source=note.source.value,
            importance=note.importance.value, tags=note.tags,
            reminder_at=note.reminder_at, status=note.status.value,
            created_at=note.created_at, updated_at=note.updated_at,
        )


class NotesResponse(BaseModel):
    count: int
    notes: list[NoteResponse]


class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    body: str = ""
    project_id: int | None = None
    client_id: int | None = None
    source: str = "manual"
    importance: str = "normal"
    tags: str = ""
    reminder_at: str | None = None
    # Aktivni projekat iz GUI konteksta; koristi se ako project_id nije zadat.
    active_project_id: int | None = None


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    project_id: int | None = None
    client_id: int | None = None
    source: str | None = None
    importance: str | None = None
    tags: str | None = None
    reminder_at: str | None = None
    status: str | None = None


# ==========          AGENDA (rokovi + podsetnici)          ==========

class AgendaItemResponse(BaseModel):
    kind: str
    ref_id: int
    title: str
    at: str
    overdue: bool
    project_id: int | None
    client_id: int | None
    status: str
    priority: str | None

    @classmethod
    def from_domain(cls, item: AgendaItem) -> AgendaItemResponse:
        return cls(
            kind=item.kind, ref_id=item.ref_id, title=item.title, at=item.at,
            overdue=item.overdue, project_id=item.project_id,
            client_id=item.client_id, status=item.status, priority=item.priority,
        )


class AgendaResponse(BaseModel):
    count: int
    days_ahead: int
    include_overdue: bool
    items: list[AgendaItemResponse]


# ==========          PROJECT BRAIN          ==========

class BrainFileResponse(BaseModel):
    name: str
    exists: bool


class BrainInfoResponse(BaseModel):
    project_id: int
    path: str
    exists: bool
    files: list[BrainFileResponse]

    @classmethod
    def from_domain(cls, info: BrainInfo) -> BrainInfoResponse:
        return cls(
            project_id=info.project_id,
            path=info.path,
            exists=info.exists,
            files=[
                BrainFileResponse(name=f.name, exists=f.exists)
                for f in info.files
            ],
        )


class BrainFileContentResponse(BaseModel):
    name: str
    content: str


class DevlogEntryRequest(BaseModel):
    cilj: str = ""
    uradjeno: str = ""
    testovi: str = ""
    sledece: str = ""
    napomene: str = ""
    executor: str = ""


class DevlogEntryResponse(BaseModel):
    file: str


class DevlogIndexResponse(BaseModel):
    content: str


# ==========          EXPLORER (file tree)          ==========

class FileNodeResponse(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int


class FileListResponse(BaseModel):
    path: str
    count: int
    nodes: list[FileNodeResponse]


class FileContentResponse(BaseModel):
    path: str
    content: str
    truncated: bool
    binary: bool


class FileCreateRequest(BaseModel):
    path: str = Field(..., min_length=1)
    kind: str = Field(..., pattern="^(file|dir)$")


class FileRenameRequest(BaseModel):
    path: str = Field(..., min_length=1)
    new_name: str = Field(..., min_length=1)


class FileWriteRequest(BaseModel):
    path: str = Field(..., min_length=1)
    content: str = ""


class FileTransferRequest(BaseModel):
    """Kopiranje/premeštanje: izvor + ciljni folder ("" = koren)."""

    path: str = Field(..., min_length=1)
    dest_dir: str = ""


class FileRevealRequest(BaseModel):
    path: str = Field(..., min_length=1)
