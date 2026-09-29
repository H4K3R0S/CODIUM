# ========== PROVAJDER: LOKALNI PROCES ==========
# Dev serveri i pozadinski procesi. Logika pokretanja i gasenja NIJE ovde
# napisana iznova — dolazi iz `process_registry`, istog koji koristi i F7
# Preview, pa Infrastructure vidi i procese koje je Preview digao.
#
# Stanje se utvrdjuje po dva izvora, jer nijedan sam nije dovoljan:
# registar zna samo procese koje je CODIUM pokrenuo (posle restarta aplikacije
# ne zna nista), a port zna samo da nesto slusa — ne i sta.
from __future__ import annotations

from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    Service,
    ServiceKind,
    ServiceState,
    ServiceStatus,
)
from core.domains.codium.infrastructure.process_registry import (
    ProcessError,
    ProcessRegistry,
    port_slusa,
    process_registry,
)
from core.domains.codium.infrastructure.providers.base import (
    InfraError,
    ServiceConfigError,
)


class LocalProcessProvider:
    """Servis koji je obican proces na ovoj masini."""

    kind = ServiceKind.LOCAL_PROCESS

    def __init__(self, registry: ProcessRegistry | None = None) -> None:
        self._registry = registry or process_registry

    # ----------          PROVERE          ----------

    def validate(self, service: Service) -> None:
        if not service.config.get("command", "").strip():
            raise ServiceConfigError("Servis trazi polje `command`.")
        if not service.config.get("cwd", "").strip():
            raise ServiceConfigError("Servis trazi polje `cwd` (radni folder).")
        port = service.config.get("port", "").strip()
        if port and not port.isdigit():
            raise ServiceConfigError(f"Polje `port` mora biti broj: {port}")

    def discover(self, node: Node) -> list[DiscoveredService]:
        """Nema sta da otkrije.

        Proces koji CODIUM nije pokrenuo ne moze da se prepozna kao „servis
        ovog projekta" — sve sto se o njemu zna je da nesto slusa na portu, a
        to je posao `port_probe`.
        """

        return []

    # ----------          STANJE          ----------

    def status(self, service: Service) -> ServiceStatus:
        info = self._registry.info(self._kljuc(service))
        if info.running:
            return ServiceStatus(ServiceState.RUNNING, info.pid,
                                 info.command or "")

        port = service.config.get("port", "").strip()
        if port.isdigit() and port_slusa(int(port)):
            # Nesto radi i drzi port, ali ga ovaj proces nije pokrenuo —
            # tipicno posle restarta aplikacije, ili je server pokrenut rukom.
            return ServiceStatus(
                ServiceState.RUNNING, None,
                f"port {port} slusa (proces nije pokrenut iz CODIUM-a)")

        return ServiceStatus(ServiceState.STOPPED)

    # ----------          POTEZI          ----------

    def start(self, service: Service) -> None:
        self.validate(service)
        try:
            self._registry.start(self._kljuc(service),
                                 service.config["command"],
                                 service.config["cwd"])
        except ProcessError as greska:
            raise InfraError(str(greska)) from greska

    def stop(self, service: Service) -> None:
        self._registry.stop(self._kljuc(service))

    def restart(self, service: Service) -> None:
        self.stop(service)
        self.start(service)

    def logs(self, service: Service, lines: int) -> list[str]:
        """Proces pise u svoju konzolu, ne u CODIUM.

        Hvatanje izlaza bi znacilo drzati citac po procesu i mesto gde se
        ispis cuva — to je posao E6, ne ovog reza.
        """

        return []

    # ----------          POMOCNO          ----------

    def _kljuc(self, service: Service) -> str:
        return f"service:{service.id}"
