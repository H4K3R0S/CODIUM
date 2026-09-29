# ========== CODIUM: DODATNI PAKETI ĆELIJE ==========
# Moduli van core/apps koje CODIUM ćelija mora da nosi u celini (okvir ih čita
# preko `core/cell/build.py::domain_extra_packages`). Svaki je STVARAN nalaz iz
# uvoza CODIUM routera/runtime-a, ne pretpostavka:
# - `core/security/scope_gate.py` (+ prazan `core/security/__init__.py`):
#   `codium_security_runtime`, `codium_ai` i `codium_audit` uvoze
#   `core.security.scope_gate.ScopeGate/ALLOW`. Modul je self-contained (samo
#   stdlib) — ne vuče `core.security.secrets` (koji ćelija NE sme da nosi;
#   ostaje na crnoj listi `_FORBIDDEN_MODULES`).
# - `core/ai/usage.py` (+ `core/ai/pricing.py`): `codium_security_runtime` i
#   `codium_assistant_runtime` vode evidenciju poziva modela (`UsageRecorder`);
#   `usage` uvozi `pricing` i `core.domains.codium.runtime` (domen ćelije, pa
#   NIJE strani uvoz). Zato su po-domenski (ne kernel): u kalima/imperium ćeliji
#   bi `usage`-ov uvoz `core.domains.codium` bio strani domen.
# AI apstrakcije koje CODIUM asistent (assistant_service `CodiumAssistant`) i
# ćelijski `codium_assistant_runtime` override traže: sloj rutera modela i
# BEZBEDNI provajderi. `providers/__init__.py` se u ćeliji ZAMENJUJE trimovanom
# verzijom (cell_overrides) koja re-exportuje samo `base` + `ollama` — bez
# anthropic/openai/openrouter (online, vuku `core.integrations`/`secrets`).
# `apps/api/schemas/core_models.py` nose sheme `codium_ai` (ModelInfoSchema…);
# on uvozi samo `core.ai.providers.ModelInfo` (iz trimovanog __init__) + pydantic.
CELL_EXTRA = (
    "core/security/__init__.py",
    "core/security/scope_gate.py",
    "core/ai/pricing.py",
    "core/ai/usage.py",
    "core/ai/model_router.py",
    "core/ai/providers/base.py",
    "core/ai/providers/ollama.py",
    "core/ai/providers/__init__.py",
    "apps/api/schemas/core_models.py",
)
