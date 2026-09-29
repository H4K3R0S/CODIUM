# ========== SERVIS ISPORUKE ==========
# Jedino mesto u fazi koje zove kapiju, dnevnik i red odobrenja. Provajderi ne
# znaju za dozvole, SQL sloj ne zna za pravila.
#
# Osnovni princip cele faze: isporuka NEMA svoj build. Ulaz je uvek uspesno
# pokretanje iz E3 i paket koji je to pokretanje ostavilo — time je iskljuceno
# „radilo je kod mene", jer se isporucuje tacno ono sto je proslo korake.
from __future__ import annotations

import json
from pathlib import Path

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.audit.approvals import ApprovalRepository
from core.domains.codium.audit.models import Approval
from core.domains.codium.automations import bus
from core.domains.codium.deployments.models import (
    DeployKind,
    Deployment,
    DeployResult,
    DeployStatus,
    DeployTarget,
    HealthResult,
)
from core.domains.codium.deployments.providers.base import (
    DeployError,
    DeployProvider,
)
from core.domains.codium.deployments.repository import (
    DeploymentRepository,
    DeployTargetRepository,
)
from core.domains.codium.paths import codium_paths
from core.domains.codium.pipelines import artifacts
from core.domains.codium.pipelines.models import RunStatus
from core.domains.codium.pipelines.repository import RunRepository
from core.security.scope_gate import ALLOW, NEEDS_APPROVAL, ScopeGate

AKCIJA_ISPORUKA = "deploy.execute"
AKCIJA_POVRATAK = "deploy.rollback"
AKCIJA_UPIS = "deploy.write"


class DeploymentServiceError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class TargetNotFound(DeploymentServiceError):
    """Trazen cilj isporuke ne postoji."""


class DeploymentNotFound(DeploymentServiceError):
    """Trazena isporuka ne postoji."""


class UnknownProvider(DeploymentServiceError):
    """Za ovaj tip cilja nema provajdera u ovoj fazi."""


class RunNotDeployable(DeploymentServiceError):
    """Pokretanje ne moze da se isporuci — nije uspelo ili nema artefakt."""


class DeployDenied(DeploymentServiceError):
    """Kapija nije dozvolila isporuku."""


class ApprovalPending(DeploymentServiceError):
    """Isporuka ceka ljudsku odluku.

    Nije greska nego stanje: molba je upisana, cilj nije dodirnut. Nosi id
    isporuke i molbe da ekran moze da odvede coveka na red odobrenja.
    """

    def __init__(self, message: str, *, deployment_id: int,
                 approval_id: int) -> None:
        super().__init__(message)
        self.deployment_id = deployment_id
        self.approval_id = approval_id


class DeploymentService:
    """Ciljevi isporuke, isporuke i povratak unazad."""

    def __init__(self, *, targets: DeployTargetRepository,
                 deployments: DeploymentRepository,
                 providers: dict[str, DeployProvider],
                 runs: RunRepository, gate: ScopeGate, audit: AuditRepository,
                 approvals: ApprovalRepository,
                 artifacts_dir: Path | None = None) -> None:
        self._targets = targets
        self._deployments = deployments
        self._providers = providers
        self._runs = runs
        self._gate = gate
        self._audit = audit
        self._approvals = approvals
        self._artifacts_dir = artifacts_dir or codium_paths.artifacts

    # ----------          CILJEVI          ----------

    def create_target(self, target: DeployTarget,
                      actor: str = "human") -> DeployTarget:
        provajder = self._provajder(target.kind)
        provajder.validate(target)
        upisan = self._targets.add(target)
        self._trag(actor, AKCIJA_UPIS, f"target:{upisan.id}", ALLOW, "ok",
                   f"nov cilj ({target.kind})")
        return upisan

    def update_target(self, target_id: int, *, name: str,
                      config: dict[str, str], enabled: bool,
                      actor: str = "human") -> DeployTarget:
        postojeci = self._nadji_cilj(target_id)
        provajder = self._provajder(postojeci.kind)
        # Provera ide nad buducim stanjem, ne nad zatecenim — inace bi losa
        # konfiguracija prosla samo zato sto je stara bila dobra.
        provajder.validate(DeployTarget(
            name=name, kind=postojeci.kind, config=config,
            project_id=postojeci.project_id,
            connector_id=postojeci.connector_id, enabled=enabled,
        ))
        izmenjen = self._targets.update(target_id, name=name, config=config,
                                        enabled=enabled)
        self._trag(actor, AKCIJA_UPIS, f"target:{target_id}", ALLOW, "ok",
                   "izmenjen cilj")
        return izmenjen

    def delete_target(self, target_id: int, actor: str = "human") -> None:
        self._nadji_cilj(target_id)
        self._targets.delete(target_id)
        self._trag(actor, AKCIJA_UPIS, f"target:{target_id}", ALLOW, "ok",
                   "obrisan cilj")

    def list_targets(self, project_id: int | None = None) -> list[DeployTarget]:
        return self._targets.list(project_id)

    def health(self, target_id: int) -> HealthResult:
        cilj = self._nadji_cilj(target_id)
        return self._provajder(cilj.kind).health(cilj)

    # ----------          ISPORUKA          ----------

    def deploy(self, target_id: int, run_id: int,
               actor: str = "human") -> Deployment:
        """Isporucuje artefakt uspesnog pokretanja na cilj."""

        cilj = self._nadji_cilj(target_id)
        provajder = self._provajder(cilj.kind)
        pokretanje = self._proveri_pokretanje(run_id)
        paket = self._paket(run_id)

        isporuka = self._deployments.create(Deployment(
            target_id=target_id, run_id=run_id,
            commit_sha=pokretanje.commit_sha,
        ))

        odluka = self._gate.check(actor=actor, action=AKCIJA_ISPORUKA,
                                  target=f"target:{target_id}")
        if odluka.verdict != ALLOW:
            self._na_cekanje(isporuka, cilj, actor, AKCIJA_ISPORUKA, odluka,
                             {"run_id": run_id})

        return self._izvedi(
            isporuka, actor, AKCIJA_ISPORUKA, f"target:{target_id}",
            lambda: provajder.deploy(cilj, paket, run_id),
        )

    def rollback(self, deployment_id: int,
                 actor: str = "human") -> Deployment:
        """Vraca cilj na verziju zadate ranije isporuke."""

        ranija = self._nadji_isporuku(deployment_id)
        if ranija.status != DeployStatus.SUCCESS:
            raise DeploymentServiceError(
                f"Isporuka {deployment_id} nije bila uspesna — nema cemu da "
                "se vrati.")

        cilj = self._nadji_cilj(ranija.target_id)
        provajder = self._provajder(cilj.kind)
        # Paket sme da nedostaje: provajder koji ume bez njega (Docker cuva
        # sliku pod oznakom) nastavlja, ostali vrate `RollbackUnsupported`.
        paket = (self._paket(ranija.run_id, obavezan=False)
                 if ranija.run_id else None)

        trenutna = self._deployments.current(ranija.target_id)

        nova = self._deployments.create(Deployment(
            target_id=ranija.target_id, run_id=ranija.run_id,
            commit_sha=ranija.commit_sha,
            detail=f"povratak na isporuku {deployment_id}",
        ))

        odluka = self._gate.check(actor=actor, action=AKCIJA_POVRATAK,
                                  target=f"target:{ranija.target_id}")
        if odluka.verdict != ALLOW:
            self._na_cekanje(nova, cilj, actor, AKCIJA_POVRATAK, odluka,
                             {"rollback_to": deployment_id})

        izvedena = self._izvedi(
            nova, actor, AKCIJA_POVRATAK, f"target:{ranija.target_id}",
            lambda: provajder.rollback(cilj, ranija, paket),
        )

        # Isporuka koja je do maloprijasnje stajala na cilju vise ne stoji.
        # Radi se tek posle uspeha — neuspeo povratak nista nije promenio.
        if (izvedena.status == DeployStatus.SUCCESS and trenutna is not None
                and trenutna.id != nova.id):
            self._deployments.mark_rolled_back(trenutna.id)

        return izvedena

    # ----------          CITANJE          ----------

    def history(self, target_id: int | None = None,
                limit: int = 50) -> list[Deployment]:
        return self._deployments.list(target_id, limit)

    def current(self, target_id: int) -> Deployment | None:
        return self._deployments.current(target_id)

    def deployable_runs(self, limit: int = 30) -> list[int]:
        """Uspesna pokretanja koja stvarno imaju paket na disku.

        Ekran nudi bas ova pokretanja pod „Isporuci" — nuditi pokretanje bez
        paketa znacilo bi dugme koje uvek pada.
        """

        uspesna = self._runs.list(None, str(RunStatus.SUCCESS), limit)
        return [run.id for run in uspesna
                if artifacts.artifact_path(self._artifacts_dir, run.id).is_file()]

    # ----------          POMOCNO          ----------

    def _izvedi(self, isporuka: Deployment, actor: str, action: str,
                target: str, potez) -> Deployment:
        """Vodi jednu isporuku od `running` do zavrsnog stanja."""

        self._deployments.mark_started(isporuka.id)
        try:
            ishod: DeployResult = potez()
        except (DeployError, OSError) as greska:
            # `OSError` je tu namerno: disk bez mesta, zakljucan fajl ili
            # nedostatak prava su stanje masine, ne kvar CODIUM-a — isporuka
            # mora da zavrsi kao `failed`, ne da izbaci go izuzetak na ekran.
            self._deployments.mark_finished(
                isporuka.id, DeployStatus.FAILED, None, str(greska))
            self._trag(actor, action, target, ALLOW, "error", str(greska))
            pala = self._deployments.get(isporuka.id)
            # I neuspela isporuka je dogadjaj: pravilo koje javlja o kvaru
            # postoji bas zbog ovog slucaja.
            self._objavi(pala, actor)
            return pala

        self._deployments.mark_finished(
            isporuka.id, DeployStatus.SUCCESS, ishod.release_ref, ishod.detail)
        self._trag(actor, action, target, ALLOW, "ok",
                   f"isporuka {isporuka.id}: {ishod.detail}")
        zavrsena = self._deployments.get(isporuka.id)
        self._objavi(zavrsena, actor)
        return zavrsena

    def _objavi(self, isporuka: Deployment, actor: str) -> None:
        """Javlja da je isporuka zavrsila.

        `origin` nosi aktera: ako je isporuku pokrenula automatizacija, njeno
        pravilo ne sme da se upali na sopstvenu posledicu.
        """

        cilj = self._targets.get(isporuka.target_id)
        bus.publish("deployment.finished", {
            "deployment_id": isporuka.id,
            "target_id": isporuka.target_id,
            "target": cilj.name if cilj else "",
            "status": str(isporuka.status),
            "run_id": isporuka.run_id,
        }, origin=actor if actor.startswith("automation:") else "")

    def _na_cekanje(self, isporuka: Deployment, cilj: DeployTarget, actor: str,
                    action: str, odluka, payload: dict[str, object]) -> None:
        """Kapija nije dozvolila — upisuje molbu ili odbija, cilj se ne dira."""

        meta = f"target:{cilj.id}"
        if odluka.verdict != NEEDS_APPROVAL:
            self._deployments.mark_finished(
                isporuka.id, DeployStatus.FAILED, None, odluka.reason)
            self._trag(actor, action, meta, odluka.verdict, "blocked",
                       odluka.reason)
            raise DeployDenied(odluka.reason)

        molba = self._approvals.request(Approval(
            actor=actor, action=action, target=meta,
            payload=json.dumps({"deployment_id": isporuka.id, **payload},
                               ensure_ascii=False),
        ))
        self._trag(actor, action, meta, NEEDS_APPROVAL, "pending",
                   f"molba {molba.id}")
        raise ApprovalPending(
            f"Isporuka ceka odobrenje coveka (molba {molba.id}).",
            deployment_id=isporuka.id, approval_id=molba.id,
        )

    def _proveri_pokretanje(self, run_id: int):
        pokretanje = self._runs.get(run_id)
        if pokretanje is None:
            raise RunNotDeployable(f"Pokretanje {run_id} ne postoji.")
        if pokretanje.status != RunStatus.SUCCESS:
            raise RunNotDeployable(
                f"Pokretanje {run_id} nije uspelo ({pokretanje.status}) — "
                "isporucuje se samo ono sto je proslo korake.")
        return pokretanje

    def _paket(self, run_id: int, *, obavezan: bool = True) -> Path | None:
        putanja = artifacts.artifact_path(self._artifacts_dir, run_id)
        if putanja.is_file():
            return putanja
        if obavezan:
            raise RunNotDeployable(
                f"Pokretanje {run_id} nema artefakt — dodaj polje `artifact` u "
                "definiciju pipeline-a i pokreni ga ponovo.")
        return None

    def _provajder(self, kind: str) -> DeployProvider:
        provajder = self._providers.get(str(kind))
        if provajder is None:
            raise UnknownProvider(
                f"Za tip cilja `{kind}` nema provajdera u ovoj verziji.")
        return provajder

    def _nadji_cilj(self, target_id: int) -> DeployTarget:
        cilj = self._targets.get(target_id)
        if cilj is None:
            raise TargetNotFound(f"Cilj isporuke {target_id} ne postoji.")
        return cilj

    def _nadji_isporuku(self, deployment_id: int) -> Deployment:
        isporuka = self._deployments.get(deployment_id)
        if isporuka is None:
            raise DeploymentNotFound(f"Isporuka {deployment_id} ne postoji.")
        return isporuka

    def _trag(self, actor: str, action: str, target: str, verdict: str,
              outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=verdict,
            outcome=outcome, detail=detail,
        ))


# Tipovi koje ova faza stvarno ume da isporuci. `ssh_host` stoji u
# `DeployKind`, ali bez provajdera — servis ga odbija urednom greskom.
PODRZANI_TIPOVI = (DeployKind.LOCAL_FOLDER, DeployKind.LOCAL_DOCKER)
