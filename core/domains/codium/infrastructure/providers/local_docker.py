# ========== PROVAJDER: LOKALNI DOCKER ==========
# `docker ps`, `start`, `stop`, `restart`, `logs` preko `docker` CLI-ja.
# Komande idu kroz ubrizganog izvrsioca (`core.domains.codium.command`), pa se
# ceo provajder testira bez instaliranog Docker-a.
#
# Ovo je pogled na kontejnere koji VEC postoje; pravljenje kontejnera je posao
# E4 isporuke. Zato ovde nema `run` ni `build` — samo potezi nad zatecenim.
from __future__ import annotations

from core.domains.codium.command import (
    ROK_KRATKO,
    CommandError,
    CommandRunner,
    ToolMissing,
    run_command,
)
from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    Service,
    ServiceKind,
    ServiceState,
    ServiceStatus,
)
from core.domains.codium.infrastructure.providers.base import (
    InfraError,
    ServiceConfigError,
)

# Razdvajac koji ime kontejnera ne moze da sadrzi.
_POLJE = "\x1f"
_PS_FORMAT = f"--format={{{{.Names}}}}{_POLJE}{{{{.State}}}}{_POLJE}{{{{.Image}}}}{_POLJE}{{{{.Ports}}}}"

# Stanja koja `docker ps` prijavljuje, prevedena na nasa tri.
_STANJA = {
    "running": ServiceState.RUNNING,
    "restarting": ServiceState.RUNNING,
    "created": ServiceState.STOPPED,
    "exited": ServiceState.STOPPED,
    "paused": ServiceState.STOPPED,
    "dead": ServiceState.ERROR,
}


class LocalDockerProvider:
    """Kontejneri na ovoj masini."""

    kind = ServiceKind.LOCAL_DOCKER

    def __init__(self, runner: CommandRunner = run_command) -> None:
        self._run = runner

    # ----------          PROVERE          ----------

    def validate(self, service: Service) -> None:
        if not service.config.get("container", "").strip():
            raise ServiceConfigError("Servis trazi polje `container` (ime).")

    # ----------          POPIS          ----------

    def discover(self, node: Node) -> list[DiscoveredService]:
        """Svi kontejneri na masini, i pokrenuti i zaustavljeni.

        `-a` je namerno: kontejner koji je trenutno ugasen je i dalje nesto
        sto covek hoce da vidi i upali, a bez njega bi popis zavisio od toga
        sta je slucajno radilo u trenutku klika.
        """

        redovi = self._izvrsi(["docker", "ps", "-a", _PS_FORMAT]).output
        nadjeni: list[DiscoveredService] = []
        for red in redovi.splitlines():
            if not red.strip():
                continue
            delovi = red.split(_POLJE)
            if len(delovi) < 2:
                continue
            ime, stanje = delovi[0].strip(), delovi[1].strip().lower()
            slika = delovi[2].strip() if len(delovi) > 2 else ""
            portovi = delovi[3].strip() if len(delovi) > 3 else ""
            nadjeni.append(DiscoveredService(
                name=ime,
                kind=ServiceKind.LOCAL_DOCKER,
                config={"container": ime},
                state=_STANJA.get(stanje, ServiceState.UNKNOWN),
                detail=" · ".join(deo for deo in (slika, portovi) if deo),
            ))
        return nadjeni

    # ----------          STANJE          ----------

    def status(self, service: Service) -> ServiceStatus:
        self.validate(service)
        ime = service.config["container"]
        try:
            ishod = self._run(
                ["docker", "inspect", "-f", "{{.State.Status}}", ime],
                timeout=ROK_KRATKO,
            )
        except ToolMissing as greska:
            return ServiceStatus(ServiceState.ERROR, None, str(greska))
        except CommandError as greska:
            # Alat postoji ali ne odgovara — najcesce ugasen Docker Desktop.
            # „Instaliraj Docker" i „upali Docker" su dva razlicita saveta.
            return ServiceStatus(
                ServiceState.ERROR, None,
                f"Docker ne odgovara (da li je pokrenut?): {greska}")

        if ishod.exit_code != 0:
            # Kontejner ne postoji (obrisan van CODIUM-a) — to nije kvar
            # sistema nego stanje sveta, pa ne ide kao `error`.
            return ServiceStatus(ServiceState.UNKNOWN, None,
                                 ishod.output.strip()[:200])

        stanje = ishod.output.strip().lower()
        return ServiceStatus(_STANJA.get(stanje, ServiceState.UNKNOWN), None,
                             stanje)

    # ----------          POTEZI          ----------

    def start(self, service: Service) -> None:
        self._potez(service, "start")

    def stop(self, service: Service) -> None:
        self._potez(service, "stop")

    def restart(self, service: Service) -> None:
        self._potez(service, "restart")

    def logs(self, service: Service, lines: int) -> list[str]:
        self.validate(service)
        ishod = self._izvrsi([
            "docker", "logs", "--tail", str(lines), service.config["container"],
        ])
        return ishod.output.splitlines()

    # ----------          POMOCNO          ----------

    def _potez(self, service: Service, komanda: str) -> None:
        self.validate(service)
        self._izvrsi(["docker", komanda, service.config["container"]])

    def _izvrsi(self, args: list[str], timeout: int = ROK_KRATKO):
        """Pokrece komandu i pretvara i nenulti kod i cutanje alata u gresku."""

        try:
            ishod = self._run(args, timeout=timeout)
        except CommandError as greska:
            raise InfraError(str(greska)) from greska
        if ishod.exit_code != 0:
            raise InfraError(
                f"`{' '.join(args)}` je vratila kod {ishod.exit_code}: "
                f"{ishod.output.strip()[:300]}")
        return ishod
