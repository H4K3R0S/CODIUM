# ========== ROUTER: UPOTREBA KONEKTORA (CODIUM) ==========
# Sami konektori zive u CORE-u (`/api/v1/core/ai/connectors`) jer ih dele svi
# domeni. Ovde stoji samo ono sto CORE ne sme da zna: KO ih u CODIUM-u koristi.
#
# Postoji zbog brisanja. Konektor obrisan bez upozorenja ostavlja deploy cilj
# koji vise nema pristup i infra node koji ne odgovara, a covek to sazna tek na
# sledecoj isporuci.
from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.schemas.codium_integrations import (
    ConnectorUsageResponse,
    ConnectorUsageSchema,
    UsageItemSchema,
)
from core.domains.codium.deployments.service import DeploymentService
from core.domains.codium.infrastructure.service import InfrastructureService

router = APIRouter(
    prefix="/api/v1/codium/integrations",
    tags=["CODIUM Integracije"],
)


def get_deployments() -> DeploymentService:
    from apps.api import codium_deployments_runtime
    return codium_deployments_runtime.get_service()


def get_infrastructure() -> InfrastructureService:
    from apps.api import codium_infrastructure_runtime
    return codium_infrastructure_runtime.get_service()


@router.get("/usage", response_model=ConnectorUsageResponse)
def upotreba(
    deployments: DeploymentService = Depends(get_deployments),
    infrastructure: InfrastructureService = Depends(get_infrastructure),
) -> ConnectorUsageResponse:
    """Koji CODIUM podsistemi koriste koji konektor.

    Kljuc je id konektora; ekran po njemu zna sta da napise pre brisanja.
    """

    po_konektoru: dict[int, ConnectorUsageSchema] = {}

    def unos(connector_id: int) -> ConnectorUsageSchema:
        return po_konektoru.setdefault(
            connector_id, ConnectorUsageSchema(connector_id=connector_id))

    for cilj in deployments.list_targets():
        if cilj.connector_id is not None:
            unos(cilj.connector_id).items.append(UsageItemSchema(
                area="deployments", id=cilj.id, name=cilj.name,
                label="Cilj isporuke"))

    for node in infrastructure.nodes():
        if node.connector_id is not None:
            unos(node.connector_id).items.append(UsageItemSchema(
                area="infrastructure", id=node.id, name=node.name,
                label="Node"))

    return ConnectorUsageResponse(usage=list(po_konektoru.values()))
