"""Registar zavisnosti CODIUM domena (ćelije).

Svaka ćelija se sama opisuje: ovo je jedno mesto istine o tome šta CODIUM
domenu treba da radi — Python paketi, Node okruženje i spoljni alati koje
razvojni radni prostor stvarno koristi (git za repozitorijume, docker za
isporuku/infrastrukturu, Monaco/terminal/docking GUI paketi). Registar
koristi "doktor" skripta (`scripts/check_dependencies.py`) i API koji GUI-ju
daje zdravstveni status ćelije.

Ovo NIJE "CORE iznad domena" — takav nadsloj više ne postoji. Svaki domen
(CODIUM, FILMIUM, …) nosi sopstveni registar samo sa onim što stvarno koristi;
zato ovde nema FILMIUM medijskih alata (ffprobe, mpv, prevodilac titlova).
CODIUM uz lokalnu Ollamu koristi i online AI SDK-ove (anthropic, openai) uz
keyring za bezbedno čuvanje API ključeva.
"""

import importlib.util
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# Platforma: na Linux/Kali install hintovi idu preko apt/pip, ne winget-a.
_IS_WINDOWS = sys.platform.startswith("win")


def _hint(windows: str, linux: str) -> str:
    """Vrati install hint prikladan trenutnom OS-u (Windows vs Linux)."""

    return windows if _IS_WINDOWS else linux


def _installer_for(windows: "DependencyInstaller", linux: "DependencyInstaller") -> "DependencyInstaller":
    """Auto-instaler prikladan trenutnom OS-u. Windows nosi winget/.ps1/portable;
    na Linux-u sistemski alati idu preko `apt`, koji aplikacija NE pokreće kao
    root — zato NONE (INSTALL dugme se sakrije), a tačna komanda stoji u
    `install_hint`-u za kopiranje. Domen prvo detektuje OS preko `_IS_WINDOWS`."""
    return windows if _IS_WINDOWS else linux


# ==========          VRSTE I NIVOI          ==========

class DependencyKind(StrEnum):
    """Odakle dolazi zavisnost i kako se proverava."""

    PYTHON = "python"
    NODE = "node"
    NPM = "npm"
    SYSTEM = "system"


class DependencySeverity(StrEnum):
    """Koliko je zavisnost bitna za rad sistema."""

    CRITICAL = "critical"    # bez ovoga backend/GUI ne rade
    IMPORTANT = "important"  # sistem radi, ali neka funkcija nedostaje
    OPTIONAL = "optional"    # lepo je imati, nije nužno


class DependencyInstaller(StrEnum):
    """Kako se zavisnost automatski instalira preko INSTALL dugmeta."""

    PIP = "pip"                    # Python paket preko pip-a
    NPM = "npm"                    # GUI paket preko `npm install` u apps/gui
    WINGET = "winget"              # Windows paket preko winget-a
    PORTABLE_ZIP = "portable_zip"  # download release zip + raspakuj u bin/
    NONE = "none"                  # nema automatske instalacije


# ==========          MODEL ZAVISNOSTI          ==========

@dataclass(frozen=True)
class Dependency:
    """Jedna zavisnost i način na koji se proverava/instalira."""

    key: str
    label: str
    kind: DependencyKind
    severity: DependencySeverity
    # Python: ime za import; NPM: ime paketa iz package.json;
    # Node/System: ime izvršnog fajla na PATH-u.
    probe: str
    purpose: str
    install_hint: str
    installer: DependencyInstaller = DependencyInstaller.NONE
    # Ako je zadato, koristi se umesto provere po `kind` (npr. VLC/mpv).
    probe_fn: Callable[[], bool] | None = None


@dataclass(frozen=True)
class DependencyStatus:
    """Rezultat provere jedne zavisnosti."""

    dependency: Dependency
    installed: bool


# ==========          POSEBNE PROVERE          ==========

def npm_package_installed(
    package: str,
    gui_root: Path | None = None,
) -> bool:
    """Proverava da li je npm paket raspakovan u `apps/gui/node_modules`.

    npm paket nije izvršni fajl na PATH-u, nego folder sa svojim
    `package.json`. Zato se ne sme proveravati preko `shutil.which`.

    Args:
        package: Ime paketa iz `package.json`, uključujući scope
            (npr. `monaco-editor` ili `@xterm/xterm`).
        gui_root: Opcioni koren GUI aplikacije. Koristi se u testovima.
    """

    if gui_root is None:
        from core.foundation.paths import core_paths

        gui_root = core_paths.apps / "gui"

    # Scoped ime (`@xterm/xterm`) se prirodno razrešava u ugnežđen folder.
    manifest = gui_root / "node_modules" / Path(package) / "package.json"

    return manifest.is_file()


# ==========          REGISTAR ZAVISNOSTI          ==========

DOMAIN_DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        key="fastapi",
        label="FastAPI",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.CRITICAL,
        probe="fastapi",
        purpose="Backend API sloj CORE sistema.",
        install_hint="python -m pip install -r requirements.txt",
    ),
    Dependency(
        key="uvicorn",
        label="Uvicorn",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.CRITICAL,
        probe="uvicorn",
        purpose="ASGI server koji pokreće backend.",
        install_hint="python -m pip install -r requirements.txt",
    ),
    Dependency(
        key="python-multipart",
        label="python-multipart",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.CRITICAL,
        probe="multipart",
        purpose="Upload fajlova i form podaci u FastAPI rutama.",
        install_hint="python -m pip install python-multipart",
    ),
    Dependency(
        key="node",
        label="Node.js",
        kind=DependencyKind.NODE,
        severity=DependencySeverity.IMPORTANT,
        probe="node",
        purpose="Pokretanje i build GUI-ja (Vite/Tauri).",
        install_hint=_hint("Instaliraj Node.js LTS sa https://nodejs.org", "sudo apt install -y nodejs npm"),
    ),
    Dependency(
        key="git",
        label="Git",
        kind=DependencyKind.SYSTEM,
        severity=DependencySeverity.IMPORTANT,
        probe="git",
        purpose="Čitanje istorije i razlike u CODIUM Repositories.",
        install_hint=_hint("winget install Git.Git", "sudo apt install -y git"),
        installer=_installer_for(DependencyInstaller.WINGET, DependencyInstaller.NONE),
    ),
    Dependency(
        key="docker",
        label="Docker",
        kind=DependencyKind.SYSTEM,
        severity=DependencySeverity.IMPORTANT,
        probe="docker",
        purpose=(
            "Isporuka u kontejner (Deployments), popis i upravljanje "
            "kontejnerima (Infrastructure) i merenje njihove potrošnje "
            "(Monitoring)."
        ),
        install_hint=_hint("winget install Docker.DockerDesktop", "sudo apt install -y docker.io"),
        installer=_installer_for(DependencyInstaller.WINGET, DependencyInstaller.NONE),
    ),
    Dependency(
        key="watchdog",
        label="watchdog",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="watchdog",
        purpose="Automatsko praćenje foldera (System Layer nadzor diska).",
        install_hint="python -m pip install watchdog",
    ),
    Dependency(
        key="psutil",
        label="psutil",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="psutil",
        purpose="Detekcija priključenih diskova (USB) u System Layer-u.",
        install_hint="python -m pip install psutil",
    ),
    Dependency(
        key="psycopg",
        label="psycopg",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="psycopg",
        purpose="PostgreSQL drajver za RAG/pretragu koda (core/rag, HybridRetriever).",
        install_hint="python -m pip install 'psycopg[binary]'",
    ),
    Dependency(
        key="pgvector",
        label="pgvector",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="pgvector",
        purpose="Vektorski tipovi za semantičku pretragu koda u RAG sloju.",
        install_hint="python -m pip install pgvector",
    ),
    Dependency(
        key="pillow",
        label="Pillow",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="PIL",
        purpose="Obrada slika (posteri, thumbnail-ovi, dimenzije).",
        install_hint="python -m pip install Pillow",
        installer=DependencyInstaller.PIP,
    ),
    Dependency(
        key="monaco-editor",
        label="Monaco Editor",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.IMPORTANT,
        probe="monaco-editor",
        purpose="Motor uređivača koda u CODIUM workspace-u.",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="monaco-editor-react",
        label="@monaco-editor/react",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.IMPORTANT,
        probe="@monaco-editor/react",
        purpose="React omotač koji montira Monaco u CODIUM editor panel.",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="xterm",
        label="@xterm/xterm",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.IMPORTANT,
        probe="@xterm/xterm",
        purpose="Renderer integrisanog terminala (PTY sesije).",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="xterm-addon-fit",
        label="@xterm/addon-fit",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.IMPORTANT,
        probe="@xterm/addon-fit",
        purpose="Uklapanje terminala u veličinu panela pri promeni dimenzija.",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="xterm-addon-search",
        label="@xterm/addon-search",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.OPTIONAL,
        probe="@xterm/addon-search",
        purpose="Pretraga kroz ispis terminala.",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="dockview",
        label="dockview-react",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.IMPORTANT,
        probe="dockview-react",
        purpose="Docking paneli (OBS-stil raspored u CODIUM workspace-u).",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="tauri-plugin-global-shortcut",
        label="@tauri-apps/plugin-global-shortcut",
        kind=DependencyKind.NPM,
        severity=DependencySeverity.OPTIONAL,
        probe="@tauri-apps/plugin-global-shortcut",
        purpose="Globalna prečica za snimak ekrana (Alat: Snimak).",
        install_hint="npm install (u apps/gui)",
        installer=DependencyInstaller.NPM,
    ),
    Dependency(
        key="keyring",
        label="keyring",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="keyring",
        purpose="Bezbedno čuvanje API ključeva u OS keychain-u (Credential Manager).",
        install_hint="python -m pip install keyring",
        installer=DependencyInstaller.PIP,
    ),
    Dependency(
        key="anthropic",
        label="anthropic SDK",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="anthropic",
        purpose="Zvanični klijent za Claude modele (CODIUM AI chat).",
        install_hint="python -m pip install anthropic",
        installer=DependencyInstaller.PIP,
    ),
    Dependency(
        key="openai",
        label="openai SDK",
        kind=DependencyKind.PYTHON,
        severity=DependencySeverity.IMPORTANT,
        probe="openai",
        purpose="Zvanični klijent za GPT modele (CODIUM AI konektori).",
        install_hint="python -m pip install openai",
        installer=DependencyInstaller.PIP,
    ),
)

# Back-compat alias: stari kod (npr. `core/foundation/installer.py`) i dalje
# uvozi `CORE_DEPENDENCIES`. Ime je zadržano da se ništa ne razbije, ali izvor
# istine je sada domenski `DOMAIN_DEPENDENCIES`.
CORE_DEPENDENCIES = DOMAIN_DEPENDENCIES


# ==========          PROVERA          ==========

def check_dependency(dependency: Dependency) -> bool:
    """Vraća True ako je zavisnost dostupna u trenutnom okruženju."""

    if dependency.probe_fn is not None:
        try:
            return dependency.probe_fn()
        except Exception:  # noqa: BLE001
            return False

    if dependency.kind is DependencyKind.PYTHON:
        try:
            return importlib.util.find_spec(dependency.probe) is not None
        except (ImportError, ValueError):
            return False

    if dependency.kind is DependencyKind.NPM:
        return npm_package_installed(dependency.probe)

    # Node i sistemski alati se traže kao izvršni fajl na PATH-u.
    return shutil.which(dependency.probe) is not None


def evaluate_dependencies(
    dependencies: tuple[Dependency, ...] = DOMAIN_DEPENDENCIES,
) -> tuple[DependencyStatus, ...]:
    """Proverava sve zavisnosti i vraća njihov status."""

    return tuple(
        DependencyStatus(
            dependency=dependency,
            installed=check_dependency(dependency),
        )
        for dependency in dependencies
    )


def overall_status(
    statuses: tuple[DependencyStatus, ...],
) -> str:
    """Sažima najveći nivo problema: "critical", "warning" ili "ok"."""

    missing = [status for status in statuses if not status.installed]

    if any(
        status.dependency.severity is DependencySeverity.CRITICAL
        for status in missing
    ):
        return "critical"

    if missing:
        return "warning"

    return "ok"
