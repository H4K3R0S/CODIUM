# ========== MODELI INFRASTRUKTURE ==========
# Dva nivoa: `Node` je mesto gde nesto radi, `Service` je jedna stvar koja
# tamo radi. Razdvojeni su da bi dodavanje udaljene masine kasnije bilo
# dodavanje reda, a ne prepravka modela.
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NodeKind(StrEnum):
    """Kakvo je mesto. `SSH` stoji upisan, ali provajder za njega nije u E5."""

    LOCAL = "local"
    SSH = "ssh"


class ServiceKind(StrEnum):
    """Cime se ovaj servis pokrece i prati."""

    LOCAL_PROCESS = "local_process"
    LOCAL_DOCKER = "local_docker"
    PORT_PROBE = "port_probe"


class ServiceState(StrEnum):
    """Zivo stanje servisa.

    `UNKNOWN` i `ERROR` nisu isto: `UNKNOWN` znaci da se ne moze utvrditi
    (nema ni PID-a ni porta da se pita), a `ERROR` da je pitanje postavljeno
    i da je odgovor bio kvar.
    """

    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass(frozen=True)
class Node:
    """Red iz `codium_infra_nodes`."""

    name: str
    kind: str = NodeKind.LOCAL
    connector_id: int | None = None
    created_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Service:
    """Red iz `codium_infra_services`.

    `config` je vec raspakovan recnik, ne JSON tekst — provajder ga cita, a
    sloj koji ga je procitao iz baze je jedini koji zna za `config_json`.
    """

    node_id: int
    name: str
    kind: str
    config: dict[str, str] = field(default_factory=dict)
    project_id: int | None = None
    auto_start: bool = False
    created_at: str = ""
    updated_at: str = ""
    id: int | None = None


@dataclass(frozen=True)
class DiscoveredService:
    """Sta je provajder zatekao na node-u.

    Namerno nije `Service`: predlog nije zapis. Covek bira sta ulazi u
    registar — masina puna tudjih kontejnera ne sme sama sebe da upise.
    """

    name: str
    kind: str
    config: dict[str, str] = field(default_factory=dict)
    state: str = ServiceState.UNKNOWN
    detail: str = ""
    # Da li je ovakav servis vec u registru — ekran po tome gasi cekiranje.
    already_registered: bool = False


@dataclass(frozen=True)
class ServiceStatus:
    """Zivo stanje jednog servisa, onako kako ga vidi provajder."""

    state: str
    pid: int | None = None
    detail: str = ""
