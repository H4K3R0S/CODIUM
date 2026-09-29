# ========== REGISTAR POKRENUTIH PROCESA ==========
# Ono sto je do E5 zivelo samo u `dev_server.py`: pokreni komandu kao dete,
# zapamti je pod kljucem, ugasi je zajedno sa decom. Izdvojeno je ovde da bi
# F7 Preview i E5 infrastruktura delili JEDAN registar, a ne dva koja bi svaki
# imao svoju predstavu o tome sta trenutno radi na masini.
#
# Kljuc je tekst, ne broj: F7 vodi racun po projektu, E5 po servisu, i ta dva
# broja se ne smeju sudariti (`projekat:3` i `servis:3` nisu isto).
from __future__ import annotations

import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ProcessError(RuntimeError):
    """Proces nije mogao da se pokrene (nema komande ili putanje)."""


@dataclass(frozen=True)
class ProcessInfo:
    """Sta registar zna o jednom kljucu."""

    running: bool
    pid: int | None = None
    command: str | None = None


def port_slusa(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    """Da li neko sluša na ovom portu.

    Jedini nacin da se vidi tudji servis koji CODIUM nije pokrenuo — i jedina
    provera koja radi kad proces jeste ziv ali jos nije podigao server.
    """

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def terminate_tree(process: subprocess.Popen) -> None:
    """Obara proces i svu njegovu decu.

    Dev server obicno pokrene svoje pod-procese (npm -> node -> vite), pa
    gasiti samo dete znaci ostaviti unuke da rade i drze port.
    """

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


class ProcessRegistry:
    """Procesi koje je CODIUM pokrenuo, po kljucu.

    Jedan kljuc = najvise jedan aktivan proces; ponovno pokretanje dok radi
    vraca zatecen proces umesto da napravi drugi.
    """

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen] = {}
        self._commands: dict[str, str] = {}

    def start(self, key: str, command: str, cwd: str | None) -> ProcessInfo:
        """Pokrece komandu ako pod ovim kljucem vec nesto ne radi."""

        zatecen = self._processes.get(key)
        if zatecen is not None and zatecen.poll() is None:
            return self.info(key)

        if not command.strip():
            raise ProcessError("Komanda nije zadata.")

        radni = Path(cwd) if cwd else None
        if radni is None or not radni.is_dir():
            raise ProcessError(f"Radni folder ne postoji: {cwd}")

        creationflags = 0
        if sys.platform == "win32":
            # Nova grupa procesa — da gasenje moze da obori celo stablo.
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        proces = subprocess.Popen(  # nosec B602 - korisnikova dev-komanda, lokalno/namerno
            command,
            cwd=str(radni),
            shell=True,
            creationflags=creationflags,
        )
        self._processes[key] = proces
        self._commands[key] = command
        return self.info(key)

    def stop(self, key: str) -> ProcessInfo:
        """Gasi proces pod kljucem i njegovo stablo."""

        proces = self._processes.get(key)
        if proces is not None and proces.poll() is None:
            terminate_tree(proces)

        self._processes.pop(key, None)
        self._commands.pop(key, None)
        return ProcessInfo(running=False)

    def info(self, key: str) -> ProcessInfo:
        """Sta registar zna o ovom kljucu."""

        proces = self._processes.get(key)
        if proces is not None and proces.poll() is None:
            return ProcessInfo(running=True, pid=proces.pid,
                               command=self._commands.get(key))
        return ProcessInfo(running=False)


# Jedan proces = jedan API server; deljen registar za F7 Preview i E5.
process_registry = ProcessRegistry()
