# ========== CODIUM IZVRŠIOCI ==========
# Mapira namere na RepositoryService/PipelineService. Ime entiteta se razrešava
# u id iznutra; nenađeno/višesmisleno → AssistantActionError (agent ga hvata).
from __future__ import annotations

from typing import Any

from core.cell.assistant.protocols import AssistantActionError

# GUI nema `/codium/repos/:id` (detalj), samo listu `/codium/repositories`.
# Id nosimo kao query parametar da bi i dalje bio dostupan primaocu rute.
REPO_ROUTE = "/codium/repositories?repo={id}"
# Second Brain MAPS mapa (ZAKON domenski agenti §5: GUI ekran = agent zna da ga otvori).
SECOND_BRAIN_MAP_ROUTE = "/second-brain?view=mapa"


class CodiumExecutors:
    """Izvršioci CODIUM Asistenta (repo + pipeline komande)."""

    def __init__(self, repositories: Any, pipelines: Any) -> None:
        self._repositories = repositories
        self._pipelines = pipelines

    # ---------- razrešavanje imena ----------

    def _repo_id(self, name: str) -> int:
        ime = (name or "").strip().lower()
        pogodci = [r for r, _ in self._repositories.list() if r.name.lower() == ime]
        if len(pogodci) != 1:
            raise AssistantActionError("Nema tacno jednog repozitorijuma.")
        return pogodci[0].id

    def _pipeline_id(self, name: str) -> int:
        ime = (name or "").strip().lower()
        pogodci = [p for p in self._pipelines.list() if p.name.lower() == ime]
        if len(pogodci) != 1:
            raise AssistantActionError("Nema tacno jednog pipeline-a.")
        return pogodci[0].id

    # ---------- run (čitanje / navigacija) ----------

    def run(self, intent_name: str, params: dict) -> dict:
        if intent_name == "list_repos":
            return {"kind": "answer", "sources": [r.name for r, _ in self._repositories.list()]}
        if intent_name == "list_pipelines":
            return {"kind": "answer", "sources": [p.name for p in self._pipelines.list()]}
        if intent_name == "repo_status":
            repo_id = self._repo_id(params["name"])
            stanje = self._repositories.status(repo_id)
            return {"kind": "answer", "reply": f"Status repoa: {stanje}"}
        if intent_name == "open":
            repo_id = self._repo_id(params["name"])
            return {"kind": "navigate", "repo_id": repo_id,
                    "route": REPO_ROUTE.format(id=repo_id)}
        if intent_name == "open_second_brain_map":
            return {"kind": "navigate", "route": SECOND_BRAIN_MAP_ROUTE}
        raise AssistantActionError(f"Nepoznata namera: {intent_name}")

    # ---------- preview / apply (upisi) ----------

    def preview(self, intent_name: str, params: dict) -> dict:
        if intent_name == "sync_repo":
            self._repo_id(params["name"])  # razreši ili digni
            return {"repo": params["name"], "akcija": "sync"}
        if intent_name == "run_pipeline":
            self._pipeline_id(params["name"])
            return {"pipeline": params["name"], "akcija": "run"}
        raise AssistantActionError(f"Nepoznat upis: {intent_name}")

    def apply(self, intent_name: str, params: dict) -> dict:
        if intent_name == "sync_repo":
            repo_id = self._repo_id(params["name"])
            self._repositories.sync(repo_id, actor="assistant")
            return {
                "kind": "answer",
                "reply": f"Sinhronizovan repozitorijum: {params['name']}",
                "synced": True,
                "repo": params["name"],
            }
        if intent_name == "run_pipeline":
            pipeline_id = self._pipeline_id(params["name"])
            self._pipelines.run(pipeline_id, actor="assistant")
            return {
                "kind": "answer",
                "reply": f"Pokrenut pipeline: {params['name']}",
                "started": True,
                "pipeline": params["name"],
            }
        raise AssistantActionError(f"Nepoznat upis: {intent_name}")
