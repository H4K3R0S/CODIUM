# ========== INFRASTRUKTURA (E5) ==========
# Popis svega sto negde radi i sto CODIUM ume da upali, ugasi i proveri.
#
# Ovde stoje SAMO moduli bez teskih zavisnosti: modeli, registar procesa i
# provajderi. `service.py` i `repository.py` se namerno ne uvoze — oni vuku
# dnevnik i bazu, a `dev_server.py` (F7 Preview) uvozi registar procesa iz
# ovog paketa. Sa njima bi lanac isao
# `codium/__init__` -> `dev_server` -> ovaj paket -> `service` -> `audit` ->
# `core.ai.usage` -> `codium.runtime`, i zatvorio krug u pola uvoza.
# Ko treba servis, uzima ga iz `infrastructure.service`.
from core.domains.codium.infrastructure.models import (
    DiscoveredService,
    Node,
    NodeKind,
    Service,
    ServiceKind,
    ServiceState,
    ServiceStatus,
)
from core.domains.codium.infrastructure.process_registry import (
    ProcessError,
    ProcessInfo,
    ProcessRegistry,
    port_slusa,
    process_registry,
)
from core.domains.codium.infrastructure.providers.base import (
    ActionUnsupported,
    InfraError,
    InfraProvider,
    ServiceConfigError,
)
from core.domains.codium.infrastructure.providers.local_docker import (
    LocalDockerProvider,
)
from core.domains.codium.infrastructure.providers.local_process import (
    LocalProcessProvider,
)
from core.domains.codium.infrastructure.providers.port_probe import (
    PortProbeProvider,
)

__all__ = [
    "ActionUnsupported", "DiscoveredService", "InfraError", "InfraProvider",
    "LocalDockerProvider", "LocalProcessProvider", "Node", "NodeKind",
    "PortProbeProvider", "ProcessError", "ProcessInfo", "ProcessRegistry",
    "Service", "ServiceConfigError", "ServiceKind", "ServiceState",
    "ServiceStatus", "port_slusa", "process_registry",
]
