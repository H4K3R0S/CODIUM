"""Pozadinski instalater CORE zavisnosti.

Pokreće vetted PowerShell skriptu iz `scripts/install/` za dati dependency
`key`. Klijent NIKAD ne šalje komandu — samo ključ; komanda/skripta se bira
ovde po fiksnoj mapi (zaštita od injection-a). Radi jedan posao u jednom
trenutku (kao cron), sa statusom za polling iz GUI-ja.
"""

import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from core.foundation.dependencies import (
    CORE_DEPENDENCIES,
    DependencyInstaller,
)
from core.foundation.paths import core_paths

# ==========          MAPA SKRIPTI          ==========

# Samo ključevi sa automatskim installer-om (ne NONE) smeju da se instaliraju.
INSTALL_SCRIPTS: dict[str, str] = {
    "git": "git.ps1",
    "docker": "docker.ps1",
    "pillow": "pillow.ps1",
    "deep-translator": "deep_translator.ps1",
    "vlc": "vlc.ps1",
    "mpv": "mpv.ps1",
    # GUI paketi dele jednu skriptu: `npm install` bez argumenta usklađuje
    # ceo node_modules sa već upisanim package.json. Zato ime paketa nigde
    # ne putuje kao argument — ni sa klijenta, ni odavde.
    "monaco-editor": "npm_install.ps1",
    "monaco-editor-react": "npm_install.ps1",
    "xterm": "npm_install.ps1",
    "xterm-addon-fit": "npm_install.ps1",
    "xterm-addon-search": "npm_install.ps1",
    "dockview": "npm_install.ps1",
    "keyring": "keyring.ps1",
    "anthropic": "anthropic.ps1",
    "openai": "openai.ps1",
}

_MAX_LOG_LINES = 200


# ==========          MODEL POSLA          ==========

@dataclass
class InstallJob:
    """Snimak trenutnog install posla (u memoriji)."""

    key: str | None = None
    status: str = "idle"  # idle | running | done | error
    started_at: str | None = None
    returncode: int | None = None
    log: list[str] = field(default_factory=list)


_JOB = InstallJob()
_THREAD: threading.Thread | None = None
_LOCK = threading.Lock()


def _script_path(key: str) -> Path:
    filename = INSTALL_SCRIPTS[key]
    return core_paths.root / "scripts" / "install" / filename


def _run(key: str, script: Path) -> None:
    """Izvršava PowerShell skriptu i puni log/returncode."""

    try:
        proc = subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(core_paths.root),
        )

        for line in proc.stdout or []:
            _JOB.log.append(line.rstrip("\n"))
            del _JOB.log[:-_MAX_LOG_LINES]

        returncode = proc.wait()
        _JOB.returncode = returncode
        _JOB.status = "done" if returncode == 0 else "error"
    except Exception as error:  # noqa: BLE001 — prijavi bilo koji problem
        _JOB.log.append(f"GREŠKA: {error}")
        _JOB.status = "error"
        _JOB.returncode = -1
    finally:
        if _JOB.status == "done":
            import importlib

            importlib.invalidate_caches()


# ==========          JAVNI API          ==========

def start_install(key: str) -> InstallJob:
    """Pokreće instalaciju za dati ključ. Vraća početni snimak posla.

    Raises:
        KeyError: nepoznat ključ ili ključ bez automatskog installer-a.
        RuntimeError: već je pokrenut jedan install posao.
    """

    global _JOB, _THREAD

    dependency = next(
        (item for item in CORE_DEPENDENCIES if item.key == key),
        None,
    )
    if dependency is None or dependency.installer is DependencyInstaller.NONE:
        raise KeyError(key)
    if key not in INSTALL_SCRIPTS:
        raise KeyError(key)

    with _LOCK:
        if _JOB.status == "running":
            raise RuntimeError("Instalacija je već u toku.")

        _JOB = InstallJob(
            key=key,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            log=[],
        )
        _THREAD = threading.Thread(
            target=_run,
            args=(key, _script_path(key)),
            daemon=True,
        )
        _THREAD.start()

    return _JOB


def get_install_status() -> InstallJob:
    """Vraća trenutni snimak install posla."""

    return _JOB
