# ========== RUNTIME INFRASTRUKTURE ==========
# Rute traze servis kroz `Depends`, pa im ovde stoji jedan primerak. Servis
# drzi kes zivog stanja u memoriji, pa mora da bude JEDAN po procesu — dva bi
# imala dve predstave o tome sta trenutno radi.
from __future__ import annotations

from pathlib import Path

from apps.api import codium_security_runtime
from core.domains.codium.infrastructure.models import ServiceKind
from core.domains.codium.infrastructure.providers.local_docker import (
    LocalDockerProvider,
)
from core.domains.codium.infrastructure.providers.local_process import (
    LocalProcessProvider,
)
from core.domains.codium.infrastructure.providers.port_probe import (
    PortProbeProvider,
)
from core.domains.codium.infrastructure.repository import (
    NodeRepository,
    ServiceRepository,
)
from core.domains.codium.infrastructure.service import InfrastructureService
from core.domains.codium.runtime import codium_database_path

_service: InfrastructureService | None = None


def _database_path() -> Path:
    """Poslovna baza. Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def get_service() -> InfrastructureService:
    global _service
    if _service is None:
        baza = _database_path()
        _service = InfrastructureService(
            nodes=NodeRepository(baza),
            services=ServiceRepository(baza),
            providers={
                # `LocalProcessProvider` bez svog registra — uzima deljeni,
                # isti koji drzi i F7 Preview, pa se procesi ne dupliraju.
                ServiceKind.LOCAL_PROCESS: LocalProcessProvider(),
                ServiceKind.LOCAL_DOCKER: LocalDockerProvider(),
                ServiceKind.PORT_PROBE: PortProbeProvider(),
            },
            gate=codium_security_runtime.get_scope_gate(),
            audit=codium_security_runtime.get_audit(),
            approvals=codium_security_runtime.get_approvals(),
        )
    return _service


def reset() -> None:
    """Zaboravi napravljen primerak (koristi se u testovima)."""
    global _service
    _service = None
