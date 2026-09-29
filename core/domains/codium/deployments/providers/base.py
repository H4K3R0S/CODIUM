# ========== PROTOKOL PROVAJDERA ISPORUKE ==========
# Dva provajdera u ovoj fazi: `local_folder` i `local_docker`. Protokol
# postoji da bi `ssh_host` kasnije usao bez prepravke servisa i ekrana —
# kredencijal bi tada dosao iz E0 konektora.
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.domains.codium.deployments.models import (
    Deployment,
    DeployResult,
    DeployTarget,
    HealthResult,
)


class DeployError(RuntimeError):
    """Isporuka nije uspela. Poruka kaze na cemu je stala."""


class TargetConfigError(DeployError):
    """Konfiguracija cilja nije ispravna.

    Odvojeno od `DeployError` jer je to greska unosa (400), a ne kvar u
    isporuci (500) — cilj sa losom konfiguracijom ne treba ni da se snimi.
    """


class RollbackUnsupported(DeployError):
    """Provider ne ume da vrati unazad ovu isporuku."""


class DeployProvider(Protocol):
    """Sta provider mora da ume."""

    kind: str

    def validate(self, target: DeployTarget) -> None:
        """Proverava konfiguraciju cilja. Baca `TargetConfigError` ako ne valja."""

    def deploy(self, target: DeployTarget, artifact_path: Path,
               run_id: int | None) -> DeployResult:
        """Isporucuje spakovan artefakt na cilj."""

    def rollback(self, target: DeployTarget, previous: Deployment,
                 artifact_path: Path | None) -> DeployResult:
        """Vraca cilj na zadatu raniju isporuku.

        `artifact_path` je paket te isporuke, ili None ako ga zadrzavanje vec
        pojelo. Provider koji ume da se vrati bez paketa (Docker cuva sliku
        pod oznakom) sme da ga zanemari; onaj kome je paket jedini izvor
        istine baca `RollbackUnsupported`.
        """

    def health(self, target: DeployTarget) -> HealthResult:
        """Kaze da li je cilj dostupan i spreman."""
