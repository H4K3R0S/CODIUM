# ========== MODELI CODIUM ==========
# Domenski tipovi razvoja softvera: projekat, klijent, task i beleška.
# v0.1 minimalni set (4 entiteta). Goal/Contact/ProjectLink/ProjectAsset kasnije.
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ---------- enumeracije ----------

class ProjectVisibility(str, Enum):
    """Razdvaja plaćeni klijentski rad od privatne laboratorije u istoj bazi."""

    CLIENT = "client"       # firma/klijent/plaćen projekat
    PRIVATE = "private"     # privatna aplikacija, CORE nadogradnja, eksperiment


class ProjectStatus(str, Enum):
    """Životni ciklus projekta."""

    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Stanje jednog taska u projektu."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(str, Enum):
    """Prioritet (zajednički za projekat i task)."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NoteSource(str, Enum):
    """Mesto nastanka beleške (koristi aktivni kontekst za auto-popunu)."""

    MANUAL = "manual"
    CHAT = "chat"
    AI = "ai"
    EMAIL = "email"
    PREVIEW = "preview"
    TASK = "task"
    ROADMAP = "roadmap"
    MEETING = "meeting"


class NoteImportance(str, Enum):
    """Važnost beleške."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NoteStatus(str, Enum):
    """Stanje beleške."""

    ACTIVE = "active"
    DONE = "done"
    ARCHIVED = "archived"


# ---------- PROJECT ----------

@dataclass
class Project:
    """Jedan razvojni projekat u CODIUM bazi (klijentski ili privatni)."""

    id: int
    name: str
    slug: str
    type: str
    visibility: ProjectVisibility
    status: ProjectStatus
    local_path: str | None
    project_brain_path: str | None
    client_id: int | None
    repository_url: str | None
    live_url: str | None
    staging_url: str | None
    preview_url: str | None
    stack: str
    priority: Priority
    dev_command: str
    dev_port: int | None
    started_at: str | None
    deadline_at: str | None
    last_opened_at: str | None
    created_at: str
    updated_at: str


@dataclass
class ProjectCreate:
    """Novi projekat iz „Dodaj projekat" forme."""

    name: str
    type: str = ""
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE
    client_id: int | None = None
    local_path: str | None = None
    repository_url: str | None = None
    stack: str = ""
    priority: Priority = Priority.NORMAL
    deadline_at: str | None = None
    dev_command: str = ""
    dev_port: int | None = None
    preview_url: str | None = None
    slug: str | None = None       # ako je None, izvodi se iz imena


@dataclass
class ProjectUpdate:
    """Delimična izmena projekta (samo prosleđena polja se menjaju)."""

    name: str | None = None
    type: str | None = None
    visibility: ProjectVisibility | None = None
    status: ProjectStatus | None = None
    client_id: int | None = None
    local_path: str | None = None
    project_brain_path: str | None = None
    repository_url: str | None = None
    live_url: str | None = None
    staging_url: str | None = None
    preview_url: str | None = None
    stack: str | None = None
    priority: Priority | None = None
    dev_command: str | None = None
    dev_port: int | None = None
    started_at: str | None = None
    deadline_at: str | None = None
    last_opened_at: str | None = None


# ---------- CLIENT ----------

@dataclass
class Client:
    """Firma ili klijent za koje se radi projekat."""

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


@dataclass
class ClientCreate:
    """Novi klijent."""

    name: str
    company_name: str = ""
    type: str = ""
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str = ""


@dataclass
class ClientUpdate:
    """Delimična izmena klijenta."""

    name: str | None = None
    company_name: str | None = None
    type: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str | None = None


# ---------- TASK ----------

@dataclass
class Task:
    """Zadatak vezan za projekat."""

    id: int
    project_id: int | None
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    due_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str


@dataclass
class TaskCreate:
    """Novi task."""

    title: str
    project_id: int | None = None
    description: str = ""
    priority: Priority = Priority.NORMAL
    due_at: str | None = None


@dataclass
class TaskUpdate:
    """Delimična izmena taska."""

    title: str | None = None
    project_id: int | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_at: str | None = None
    completed_at: str | None = None


# ---------- NOTE ----------

@dataclass
class Note:
    """Beleška; može biti vezana za projekat i/ili klijenta, ili globalni inbox."""

    id: int
    project_id: int | None
    client_id: int | None
    title: str
    body: str
    source: NoteSource
    importance: NoteImportance
    tags: str
    reminder_at: str | None
    status: NoteStatus
    created_at: str
    updated_at: str


@dataclass
class NoteCreate:
    """Nova beleška. Bez project_id ide u globalni CODIUM inbox."""

    title: str
    body: str = ""
    project_id: int | None = None
    client_id: int | None = None
    source: NoteSource = NoteSource.MANUAL
    importance: NoteImportance = NoteImportance.NORMAL
    tags: str = ""
    reminder_at: str | None = None


@dataclass
class NoteUpdate:
    """Delimična izmena beleške."""

    title: str | None = None
    body: str | None = None
    project_id: int | None = None
    client_id: int | None = None
    source: NoteSource | None = None
    importance: NoteImportance | None = None
    tags: str | None = None
    reminder_at: str | None = None
    status: NoteStatus | None = None


# ---------- AGENDA (F8: rokovi + podsetnici) ----------

@dataclass
class AgendaItem:
    """
    Jedinstvena stavka kalendara/podsetnika. Izvodi se iz taska (`due_at`),
    beleške (`reminder_at`) ili projekta (`deadline_at`) — nije zaseban red u
    bazi. `kind` označava poreklo, `at` je ISO trenutak po kome se sortira.
    """

    kind: str                # "task" | "note" | "project"
    ref_id: int              # id izvornog entiteta
    title: str
    at: str                  # ISO datum/vreme (due_at / reminder_at / deadline_at)
    overdue: bool            # rok prošao, a stavka nije završena
    project_id: int | None
    client_id: int | None
    status: str              # status izvornog entiteta (za prikaz/boju)
    priority: str | None     # prioritet gde postoji (task/projekat)


# ---------- MODEL PREF (Faza 1 AI provajdera) ----------

@dataclass(frozen=True)
class ModelPref:
    """Zapamćen izbor modela za par (projekat, persona)."""

    id: int
    project_id: int | None
    persona: str
    model: str
    provider: str
    updated_at: str
