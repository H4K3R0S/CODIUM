# ========== PROTOKOL PROVAJDERA INFRASTRUKTURE ==========
# Tri provajdera u E5: `local_process`, `local_docker`, `port_probe`.
# `ssh_host` nije u ovoj fazi — protokol postoji da bi kasnije usao bez
# prepravke servisa i ekrana.
from __future__ import annotations

from typing import Protocol

from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    Service,
    ServiceStatus,
)


class InfraError(RuntimeError):
    """Potez nad servisom nije uspeo. Poruka kaze na cemu je stao."""


class ServiceConfigError(InfraError):
    """Konfiguracija servisa nije ispravna.

    Odvojeno od `InfraError` jer je to greska unosa (400), a ne kvar u radu
    (500) — servis sa losom konfiguracijom ne treba ni da se upise.
    """


class ActionUnsupported(InfraError):
    """Ovaj provajder ne ume ovaj potez.

    `port_probe` samo gleda; pokretanje tudjeg servisa koji CODIUM nije ni
    pokrenuo nije nesto sto se moze izmisliti.
    """


class InfraProvider(Protocol):
    """Sta provajder mora da ume."""

    kind: str

    def validate(self, service: Service) -> None:
        """Proverava konfiguraciju. Baca `ServiceConfigError` ako ne valja."""

    def discover(self, node: Node) -> list[DiscoveredService]:
        """Sta je zateceno na node-u. Ne upisuje nista — samo predlaze."""

    def status(self, service: Service) -> ServiceStatus: ...

    def start(self, service: Service) -> None: ...

    def stop(self, service: Service) -> None: ...

    def restart(self, service: Service) -> None: ...

    def logs(self, service: Service, lines: int) -> list[str]: ...
