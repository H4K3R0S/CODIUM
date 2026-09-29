# ========== MODELI ISPORUKE ==========
# Oblici kroz koje podaci putuju od provider-a do baze i do ekrana.
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeployKind(StrEnum):
    """Tip cilja isporuke.

    `SSH_HOST` stoji upisan iako provider za njega ne postoji u ovoj fazi:
    unos u nabrajanju je jeftin, a bez njega bi kasniji provider trazio i
    migraciju i prepravku svake provere tipa.
    """

    LOCAL_FOLDER = "local_folder"
    LOCAL_DOCKER = "local_docker"
    SSH_HOST = "ssh_host"


class DeployStatus(StrEnum):
    """Stanje jedne isporuke.

    `PENDING` je isporuka koju je kapija poslala coveku na odobrenje —
    zatrazena je, a nista jos nije dodirnulo cilj.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class DeployTarget:
    """Red iz `codium_deploy_targets`.

    `config` je vec raspakovan recnik, ne JSON tekst — provider ga cita, a
    sloj koji ga je procitao iz baze je jedini koji zna za `config_json`.
    """

    name: str
    kind: str
    config: dict[str, str]
    project_id: int | None = None
    connector_id: int | None = None
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Deployment:
    """Red iz `codium_deployments`."""

    target_id: int
    run_id: int | None = None
    commit_sha: str | None = None
    status: str = DeployStatus.PENDING
    # Cime se vraca unazad: folder prethodne verzije ili oznaka slike.
    release_ref: str | None = None
    detail: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class DeployResult:
    """Sta je provider stvarno uradio.

    `release_ref` je jedini nacin da se kasnije vrati unazad — bez njega
    isporuka je jednosmerna, pa provider koji ga ne vrati priznaje da povratak
    ne podrzava.
    """

    release_ref: str | None
    detail: str = ""


@dataclass(frozen=True)
class HealthResult:
    """Odgovor na pitanje „da li je cilj tu i spreman".

    Nezdrav cilj nije greska sistema nego stanje sveta, pa se ne baca izuzetak.
    """

    healthy: bool
    detail: str = ""
