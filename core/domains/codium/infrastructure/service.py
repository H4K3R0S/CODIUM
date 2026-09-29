# ========== SERVIS INFRASTRUKTURE ==========
# Jedino mesto u fazi koje zove kapiju, dnevnik i red odobrenja. Provajderi ne
# znaju za dozvole, SQL sloj ne zna za pravila.
#
# Zivo stanje se NE upisuje u bazu: cita se od provajdera i kesira u memoriji
# 5 sekundi. Istorija stanja je posao E6, u zasebnoj tabeli uzoraka — upisivati
# je ovde znacilo bi red po osvezavanju ekrana.
from __future__ import annotations

import json
import time
from collections.abc import Callable

from core.domains.codium.audit import AuditEntry, AuditRepository
from core.domains.codium.audit.approvals import ApprovalRepository
from core.domains.codium.audit.models import Approval
from core.domains.codium.automations import bus
from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    Service,
    ServiceState,
    ServiceStatus,
)
from core.domains.codium.infrastructure.providers.base import (
    InfraError,
    InfraProvider,
)
from core.domains.codium.infrastructure.repository import (
    NodeRepository,
    ServiceRepository,
)
from core.security.scope_gate import ALLOW, NEEDS_APPROVAL, ScopeGate

AKCIJA_START = "infra.start"
AKCIJA_STOP = "infra.stop"
AKCIJA_RESTART = "infra.restart"
AKCIJA_UPIS = "infra.write"

# Koliko dugo se zivo stanje smatra svezim. Ekran osvezava listu cesto, a
# svako citanje je podproces ili socket — bez kesa bi jedan otvoren ekran
# stalno cackao Docker.
KES_SEKUNDI = 5.0


class InfrastructureError(RuntimeError):
    """Zajednicki koren gresaka ovog servisa."""


class NodeNotFound(InfrastructureError):
    """Trazen node ne postoji."""


class ServiceNotFound(InfrastructureError):
    """Trazen servis ne postoji."""


class UnknownProvider(InfrastructureError):
    """Za ovaj tip servisa nema provajdera u ovoj fazi."""


class ActionDenied(InfrastructureError):
    """Kapija nije dozvolila potez."""


class ApprovalPending(InfrastructureError):
    """Potez ceka ljudsku odluku.

    Nije greska nego stanje: molba je upisana, servis nije dodirnut.
    """

    def __init__(self, message: str, *, approval_id: int) -> None:
        super().__init__(message)
        self.approval_id = approval_id


class InfrastructureService:
    """Node-ovi, registar servisa i potezi nad njima."""

    def __init__(self, *, nodes: NodeRepository, services: ServiceRepository,
                 providers: dict[str, InfraProvider], gate: ScopeGate,
                 audit: AuditRepository, approvals: ApprovalRepository,
                 clock: Callable[[], float] = time.monotonic,
                 cache_seconds: float = KES_SEKUNDI) -> None:
        self._nodes = nodes
        self._services = services
        self._providers = providers
        self._gate = gate
        self._audit = audit
        self._approvals = approvals
        self._clock = clock
        self._cache_seconds = cache_seconds
        self._cache: dict[int, tuple[float, ServiceStatus]] = {}

    # ----------          NODE-OVI          ----------

    def nodes(self) -> list[Node]:
        return self._nodes.list()

    def create_node(self, node: Node, actor: str = "human") -> Node:
        upisan = self._nodes.add(node)
        self._trag(actor, AKCIJA_UPIS, f"node:{upisan.id}", ALLOW, "ok",
                   f"nov node ({node.kind})")
        return upisan

    # ----------          REGISTAR SERVISA          ----------

    def services(self, node_id: int | None = None,
                 project_id: int | None = None) -> list[Service]:
        return self._services.list(node_id, project_id)

    def create_service(self, service: Service, actor: str = "human") -> Service:
        self._nadji_node(service.node_id)
        self._provajder(service.kind).validate(service)
        upisan = self._services.add(service)
        self._trag(actor, AKCIJA_UPIS, f"service:{upisan.id}", ALLOW, "ok",
                   f"nov servis ({service.kind})")
        return upisan

    def update_service(self, service_id: int, *, name: str,
                       config: dict[str, str], project_id: int | None,
                       auto_start: bool, actor: str = "human") -> Service:
        postojeci = self._nadji_servis(service_id)
        # Provera ide nad buducim stanjem, ne nad zatecenim — inace bi losa
        # konfiguracija prosla samo zato sto je stara bila dobra.
        self._provajder(postojeci.kind).validate(Service(
            node_id=postojeci.node_id, name=name, kind=postojeci.kind,
            config=config, project_id=project_id, auto_start=auto_start,
            id=service_id,
        ))
        izmenjen = self._services.update(service_id, name=name, config=config,
                                         project_id=project_id,
                                         auto_start=auto_start)
        self._cache.pop(service_id, None)
        self._trag(actor, AKCIJA_UPIS, f"service:{service_id}", ALLOW, "ok",
                   "izmenjen servis")
        return izmenjen

    def delete_service(self, service_id: int, actor: str = "human") -> None:
        """Uklanja servis iz registra.

        NE gasi ga: brisanje zapisa je zaborav, ne potez nad masinom. Ko hoce
        i jedno i drugo, prvo zaustavi pa obrise.
        """

        self._nadji_servis(service_id)
        self._services.delete(service_id)
        self._cache.pop(service_id, None)
        self._trag(actor, AKCIJA_UPIS, f"service:{service_id}", ALLOW, "ok",
                   "servis uklonjen iz registra")

    # ----------          ZIVO STANJE          ----------

    def status(self, service: Service) -> ServiceStatus:
        """Stanje servisa, sa kesom od `cache_seconds`."""

        zapamceno = self._cache.get(service.id)
        sada = self._clock()
        if zapamceno is not None and sada - zapamceno[0] < self._cache_seconds:
            return zapamceno[1]

        try:
            stanje = self._provajder(service.kind).status(service)
        except (InfraError, UnknownProvider) as greska:
            # Kvar u citanju stanja jednog servisa ne sme da obori ceo spisak.
            stanje = ServiceStatus(ServiceState.ERROR, None, str(greska))

        self._cache[service.id] = (sada, stanje)
        return stanje

    def discover(self, node_id: int) -> list[DiscoveredService]:
        """Pita svaki provajder sta je zatekao. NE upisuje nista.

        Masina puna tudjih kontejnera ne sme sama sebe da upise u registar —
        covek bira sta ulazi.
        """

        node = self._nadji_node(node_id)
        postojeci = {
            (s.kind, json.dumps(s.config, sort_keys=True))
            for s in self._services.list(node_id)
        }

        nadjeni: list[DiscoveredService] = []
        for provajder in self._providers.values():
            try:
                predlozi = provajder.discover(node)
            except InfraError:
                # Provajder koji ne moze da odgovori (nema Docker-a na masini)
                # preskace se — ostali i dalje imaju sta da kazu.
                continue
            for predlog in predlozi:
                kljuc = (predlog.kind, json.dumps(predlog.config, sort_keys=True))
                nadjeni.append(DiscoveredService(
                    name=predlog.name, kind=predlog.kind, config=predlog.config,
                    state=predlog.state, detail=predlog.detail,
                    already_registered=kljuc in postojeci,
                ))
        return nadjeni

    def logs(self, service_id: int, lines: int = 200) -> list[str]:
        servis = self._nadji_servis(service_id)
        try:
            return self._provajder(servis.kind).logs(servis, lines)
        except InfraError as greska:
            raise InfrastructureError(str(greska)) from greska

    # ----------          POTEZI          ----------

    def start(self, service_id: int, actor: str = "human") -> ServiceStatus:
        return self._potez(service_id, AKCIJA_START, actor,
                           lambda p, s: p.start(s))

    def stop(self, service_id: int, actor: str = "human") -> ServiceStatus:
        return self._potez(service_id, AKCIJA_STOP, actor,
                           lambda p, s: p.stop(s))

    def restart(self, service_id: int, actor: str = "human") -> ServiceStatus:
        return self._potez(service_id, AKCIJA_RESTART, actor,
                           lambda p, s: p.restart(s))

    # ----------          POMOCNO          ----------

    def _potez(self, service_id: int, action: str, actor: str,
               izvrsi) -> ServiceStatus:
        servis = self._nadji_servis(service_id)
        provajder = self._provajder(servis.kind)
        cilj = f"service:{service_id}"

        odluka = self._gate.check(actor=actor, action=action, target=cilj)
        if odluka.verdict != ALLOW:
            self._na_cekanje(actor, action, cilj, odluka)

        try:
            izvrsi(provajder, servis)
        except InfraError as greska:
            self._trag(actor, action, cilj, ALLOW, "error", str(greska))
            raise InfrastructureError(str(greska)) from greska

        # Kes se odbacuje odmah: stanje se upravo promenilo naredbom, pa bi
        # sledeci pogled do pet sekundi pokazivao ono sto vise ne vazi.
        # Staro stanje se cita PRE odbacivanja — posle njega ga vise nema.
        staro = self._cache.get(service_id)
        self._cache.pop(service_id, None)
        stanje = self.status(servis)
        self._trag(actor, action, cilj, ALLOW, "ok", str(stanje.state))

        staro_ime = str(staro[1].state) if staro is not None else ""
        if staro_ime != str(stanje.state):
            bus.publish("service.state.changed", {
                "service_id": service_id,
                "service": servis.name,
                "old_state": staro_ime,
                "new_state": str(stanje.state),
            }, origin=actor if actor.startswith("automation:") else "")

        return stanje

    def _na_cekanje(self, actor: str, action: str, target: str, odluka) -> None:
        """Kapija nije dozvolila — upisuje molbu ili odbija, servis se ne dira."""

        if odluka.verdict != NEEDS_APPROVAL:
            self._trag(actor, action, target, odluka.verdict, "blocked",
                       odluka.reason)
            raise ActionDenied(odluka.reason)

        molba = self._approvals.request(Approval(
            actor=actor, action=action, target=target,
            payload=json.dumps({"service": target}, ensure_ascii=False),
        ))
        self._trag(actor, action, target, NEEDS_APPROVAL, "pending",
                   f"molba {molba.id}")
        raise ApprovalPending(
            f"Potez ceka odobrenje coveka (molba {molba.id}).",
            approval_id=molba.id,
        )

    def _provajder(self, kind: str) -> InfraProvider:
        provajder = self._providers.get(str(kind))
        if provajder is None:
            raise UnknownProvider(
                f"Za tip servisa `{kind}` nema provajdera u ovoj verziji.")
        return provajder

    def _nadji_node(self, node_id: int) -> Node:
        node = self._nodes.get(node_id)
        if node is None:
            raise NodeNotFound(f"Node {node_id} ne postoji.")
        return node

    def _nadji_servis(self, service_id: int) -> Service:
        servis = self._services.get(service_id)
        if servis is None:
            raise ServiceNotFound(f"Servis {service_id} ne postoji.")
        return servis

    def _trag(self, actor: str, action: str, target: str, verdict: str,
              outcome: str, detail: str) -> None:
        self._audit.record(AuditEntry(
            actor=actor, action=action, target=target, verdict=verdict,
            outcome=outcome, detail=detail,
        ))
