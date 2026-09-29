# ========== PROVAJDER: PROVERA PORTA ==========
# Najprostiji od tri: „nesto slusa na ovom portu". Za baze i tudje servise
# koje CODIUM ne pokrece — samo ih prati.
from __future__ import annotations

from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    Service,
    ServiceKind,
    ServiceState,
    ServiceStatus,
)
from core.domains.codium.infrastructure.process_registry import port_slusa
from core.domains.codium.infrastructure.providers.base import (
    ActionUnsupported,
    ServiceConfigError,
)


class PortProbeProvider:
    """Servis koji se samo posmatra."""

    kind = ServiceKind.PORT_PROBE

    # ----------          PROVERE          ----------

    def validate(self, service: Service) -> None:
        port = service.config.get("port", "").strip()
        if not port.isdigit():
            raise ServiceConfigError("Servis trazi polje `port` (broj).")
        if not 1 <= int(port) <= 65535:
            raise ServiceConfigError(f"Port je van opsega 1-65535: {port}")

    def discover(self, node: Node) -> list[DiscoveredService]:
        """Ne skenira portove.

        Skeniranje celog opsega bi bilo sporo, a na tudjoj mrezi i nepristojno
        — koji port prati, kaze covek.
        """

        return []

    # ----------          STANJE          ----------

    def status(self, service: Service) -> ServiceStatus:
        self.validate(service)
        port = int(service.config["port"])
        host = service.config.get("host", "127.0.0.1").strip() or "127.0.0.1"
        if port_slusa(port, host):
            return ServiceStatus(ServiceState.RUNNING, None,
                                 f"{host}:{port} slusa")
        return ServiceStatus(ServiceState.STOPPED, None,
                             f"{host}:{port} ne odgovara")

    # ----------          POTEZI          ----------

    def start(self, service: Service) -> None:
        raise ActionUnsupported(
            f"`{service.name}` se samo prati — CODIUM ga nije pokrenuo, pa ne "
            "zna ni cime bi ga pokrenuo.")

    def stop(self, service: Service) -> None:
        raise ActionUnsupported(
            f"`{service.name}` se samo prati — gasi se tamo gde je pokrenut.")

    def restart(self, service: Service) -> None:
        raise ActionUnsupported(f"`{service.name}` se samo prati.")

    def logs(self, service: Service, lines: int) -> list[str]:
        return []
