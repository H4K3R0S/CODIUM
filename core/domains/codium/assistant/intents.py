# ========== CODIUM INTENTI (allowlist) ==========
from __future__ import annotations

from core.cell.assistant.intents import IntentSpec

# `needs_entity=False` svuda: CODIUM ima dva tipa entiteta (repo, pipeline) koje
# izvršilac razrešava IZNUTRA po imenu (`params["name"]`), pa se K `entity_key`
# (jedan tip) ne koristi; „nije nađeno" ide kroz AssistantActionError.
CODIUM_INTENTS: dict[str, IntentSpec] = {
    "list_repos": IntentSpec("list_repos", is_write=False, is_navigate=False,
                             needs_entity=False, tool="repo", required_params=()),
    "list_pipelines": IntentSpec("list_pipelines", is_write=False, is_navigate=False,
                                 needs_entity=False, tool="pipeline", required_params=()),
    "repo_status": IntentSpec("repo_status", is_write=False, is_navigate=False,
                              needs_entity=False, tool="repo", required_params=("name",)),
    "sync_repo": IntentSpec("sync_repo", is_write=True, is_navigate=False,
                            needs_entity=False, tool="repo", required_params=("name",)),
    "run_pipeline": IntentSpec("run_pipeline", is_write=True, is_navigate=False,
                               needs_entity=False, tool="pipeline", required_params=("name",)),
    "open": IntentSpec("open", is_write=False, is_navigate=True,
                       needs_entity=False, tool="repo", required_params=("name",)),
    "open_second_brain_map": IntentSpec("open_second_brain_map", is_write=False, is_navigate=True,
                                        needs_entity=False, tool="repo", required_params=()),
}
