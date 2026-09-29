# ========== SEME: KATALOG MODELA (CORE nivo) ==========
# Isti oblik koriste CORE rute (globalna vidljivost) i domenske rute
# (efektivna vidljivost = CORE deny + domenski deny).
from __future__ import annotations

from pydantic import BaseModel, Field

from core.ai.providers import ModelInfo


class ModelInfoSchema(BaseModel):
    id: str
    label: str
    provider: str
    is_local: bool
    context_window: int
    price_in_per_mtok: float
    price_out_per_mtok: float
    size_gb: float | None
    oversized: bool
    available: bool
    unavailable_reason: str
    # Da li korisnik želi ovaj model u chat izborniku. Podrazumevano da;
    # isključeni modeli ostaju u katalogu da bi se mogli vratiti.
    enabled: bool = True
    # Red koji stoji umesto modela kad provajder ne odgovara.
    is_placeholder: bool = False
    # Model koji je CORE iskljucio za sve domene. Domen ga ne moze vratiti —
    # zato ga podesavanja domena prikazuju zakljucanog, sa objasnjenjem.
    disabled_globally: bool = False
    # Provajder cija se lista vodi ALLOW listom (OpenRouter, 300+ modela).
    # GUI ga po ovome izdvaja u zasebnu sekciju sa pretragom, umesto da mu
    # 300 redova ubaci u obican izbornik.
    needs_allowlist: bool = False

    @classmethod
    def from_domain(cls, item: ModelInfo, enabled: bool = True,
                    disabled_globally: bool = False,
                    needs_allowlist: bool = False) -> ModelInfoSchema:
        return cls(
            id=item.id,
            label=item.label,
            provider=item.provider,
            is_local=item.is_local,
            context_window=item.context_window,
            price_in_per_mtok=item.price_in_per_mtok,
            price_out_per_mtok=item.price_out_per_mtok,
            size_gb=item.size_gb,
            oversized=item.oversized,
            available=item.available,
            unavailable_reason=item.unavailable_reason,
            enabled=enabled,
            is_placeholder=item.is_placeholder,
            disabled_globally=disabled_globally,
            needs_allowlist=needs_allowlist,
        )


class ModelsResponse(BaseModel):
    models: list[ModelInfoSchema]


class ModelEnabledRequest(BaseModel):
    provider: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    enabled: bool
    # "global" vazi svuda; ostalo je id domena ("core", "codium"...).
    scope: str = Field(default="global", min_length=1)


class ModelEnabledResponse(BaseModel):
    provider: str
    model: str
    enabled: bool
    scope: str = "global"


class ModelScopeSchema(BaseModel):
    id: str
    label: str


class ModelScopesResponse(BaseModel):
    scopes: list[ModelScopeSchema]


