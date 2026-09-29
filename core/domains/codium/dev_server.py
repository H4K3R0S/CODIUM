# ========== CODIUM DEV SERVER (lokalni host) ==========
# Pokreće/gasi lokalni dev server projekta (npr. "npm run dev") kao dete-proces
# u local_path-u projekta. Namena: projekat sam diže svoj lokalni host, preview
# se veže na njegov URL.
#
# Od E5 ovo više nije sopstveni registar procesa nego tanak omotač oko
# `infrastructure.process_registry` — isti registar koji koristi i ekran
# Infrastructure. Dva registra bi značila dve predstave o tome šta trenutno
# radi na mašini: Preview bi video svoj proces, Infrastructure ne bi.
#
# Javni oblik (`CodiumDevServer`, `DevServerStatus`, `DevServerError`,
# `dev_server_url`) namerno je ostao isti — F7 Preview i njegov API se ne diraju.
from __future__ import annotations

from dataclasses import dataclass

from core.domains.codium.infrastructure.process_registry import (
    ProcessError,
    ProcessRegistry,
    process_registry,
)

# Prefiks ključa u zajedničkom registru. Postoji da se `projekat:3` i
# `servis:3` (E5) nikad ne bi sudarili u istom rečniku.
_KLJUC = "project"


def dev_server_url(port: int, host: str = "localhost") -> str:
    """Izvodi preview URL lokalnog hosta iz porta."""

    return f"http://{host}:{port}"


@dataclass
class DevServerStatus:
    """Stanje dev servera jednog projekta."""

    project_id: int
    running: bool
    pid: int | None
    command: str | None


class DevServerError(Exception):
    """Greška pri pokretanju/gašenju dev servera (nedostaje komanda/putanja)."""


class CodiumDevServer:
    """
    Dev-server procesi po projektu. Jedan projekat = najviše jedan aktivan
    proces; ponovno pokretanje dok radi vraća postojeće stanje.

    Komanda se izvršava kroz shell (na Windows-u tako se razrešava npm.cmd i
    slično). To je korisnikova sopstvena, konfigurisana komanda na njegovoj
    mašini za lokalni razvoj.
    """

    def __init__(self, registry: ProcessRegistry | None = None) -> None:
        # Podrazumevano deljeni registar; test sme da ubaci svoj.
        self._registry = registry or process_registry

    def _key(self, project_id: int) -> str:
        return f"{_KLJUC}:{project_id}"

    # ==========          POKRETANJE          ==========

    def start(
        self, project_id: int, command: str, cwd: str | None,
    ) -> DevServerStatus:
        """Pokreće dev server projekta ako već ne radi."""

        try:
            info = self._registry.start(self._key(project_id), command, cwd)
        except ProcessError as greska:
            # Poruke ostaju one koje je F7 oduvek prikazivao — razlog je isti,
            # samo je provera sada u zajedničkom registru.
            if not command.strip():
                raise DevServerError(
                    "Dev komanda nije zadata za ovaj projekat.") from greska
            raise DevServerError(
                "Lokalna putanja projekta (local_path) ne postoji.") from greska

        return DevServerStatus(project_id, info.running, info.pid, info.command)

    # ==========          GAŠENJE          ==========

    def stop(self, project_id: int) -> DevServerStatus:
        """Gasi dev server projekta (i njegovo stablo procesa)."""

        self._registry.stop(self._key(project_id))
        return DevServerStatus(project_id, False, None, None)

    # ==========          STATUS          ==========

    def status(self, project_id: int) -> DevServerStatus:
        info = self._registry.info(self._key(project_id))
        return DevServerStatus(project_id, info.running, info.pid, info.command)


# Jedan proces = jedan API server; deljeni pogled na dev-server procese.
codium_dev_server = CodiumDevServer()
