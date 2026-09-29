# ========== SEME: UPOTREBA KONEKTORA (CODIUM) ==========
# Nijedna sema ovde ne dodiruje tajne — konektor se pominje samo po id-ju.
from __future__ import annotations

from pydantic import BaseModel, Field


class UsageItemSchema(BaseModel):
    """Jedna stvar koja koristi konektor."""

    area: str
    id: int
    name: str
    # Naziv na srpskom za ekran; `area` ostaje masinski kljuc.
    label: str


class ConnectorUsageSchema(BaseModel):
    connector_id: int
    items: list[UsageItemSchema] = Field(default_factory=list)


class ConnectorUsageResponse(BaseModel):
    usage: list[ConnectorUsageSchema]
