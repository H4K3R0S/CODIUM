from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.cell.assistant.protocols import AssistantActionError
from core.domains.codium.assistant.executors import CodiumExecutors


@dataclass
class _Repo:
    id: int
    name: str


@dataclass
class _Pipe:
    id: int
    name: str


class _RepoSvc:
    def __init__(self):
        self.synced = None

    def list(self, project_id=None):
        return [(_Repo(1, "alfa"), object()), (_Repo(2, "beta"), object())]

    def status(self, repo_id):
        return {"branch": "main", "id": repo_id}

    def sync(self, repo_id, actor="human"):
        self.synced = (repo_id, actor)
        return True


class _PipeSvc:
    def __init__(self):
        self.ran = None

    def list(self, repository_id=None):
        return [_Pipe(10, "build"), _Pipe(11, "test")]

    def run(self, pipeline_id, actor="human", trigger="manual"):
        self.ran = (pipeline_id, actor)
        return object()


def _ex():
    return CodiumExecutors(_RepoSvc(), _PipeSvc())


def test_list_repos_vraca_imena():
    out = _ex().run("list_repos", {})
    assert out["sources"] == ["alfa", "beta"]


def test_list_pipelines_vraca_imena():
    out = _ex().run("list_pipelines", {})
    assert out["sources"] == ["build", "test"]


def test_open_repo_navigate():
    out = _ex().run("open", {"name": "beta"})
    assert out["kind"] == "navigate"
    assert "/codium/repositories?repo=2" in out["route"]


def test_open_second_brain_map_navigate():
    out = _ex().run("open_second_brain_map", {})
    assert out["kind"] == "navigate"
    assert out["route"] == "/second-brain?view=mapa"


def test_repo_status_razresi_ime():
    out = _ex().run("repo_status", {"name": "alfa"})
    assert out["kind"] == "answer"
    assert "main" in out["reply"]


def test_nepoznato_ime_je_action_error():
    with pytest.raises(AssistantActionError):
        _ex().run("repo_status", {"name": "nema"})


def test_sync_preview_pa_apply():
    ex = _ex()
    prev = ex.preview("sync_repo", {"name": "alfa"})
    assert prev["repo"] == "alfa"
    ex.apply("sync_repo", {"name": "alfa"})
    assert ex._repositories.synced[0] == 1


def test_run_pipeline_apply():
    ex = _ex()
    ex.preview("run_pipeline", {"name": "build"})
    ex.apply("run_pipeline", {"name": "build"})
    assert ex._pipelines.ran[0] == 10
