# ========== TEST: CODIUM ASISTENT API ==========
# Endpointi zovu `get_agent_dep(...)` direktno (ne kroz `Depends`), pa se
# lažni agent ubacuje monkeypatch-om `codium_assistant_runtime.get_agent` —
# `app.dependency_overrides` tu ne bi imao efekta.
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api import codium_assistant_runtime
from apps.api.routers import codium_assistant
from core.cell.assistant.agent import AgentResult


class _FakeAgent:
    def handle(self, message):
        return AgentResult(kind="answer", intent="list_repos", reply="Evo.", sources=["alfa"])

    def confirm(self, token):
        return {"synced": True}

    def refute(self, log_id=None):
        return True


def _client(monkeypatch):
    monkeypatch.setattr(codium_assistant_runtime, "get_agent", lambda persona_id="opsti": _FakeAgent())
    app = FastAPI()
    app.include_router(codium_assistant.router)
    return TestClient(app)


def test_command(monkeypatch):
    r = _client(monkeypatch).post("/api/v1/codium/assistant/command", json={"message": "listaj repoe"})
    assert r.status_code == 200
    assert r.json()["sources"] == ["alfa"]


def test_confirm(monkeypatch):
    r = _client(monkeypatch).post("/api/v1/codium/assistant/confirm", json={"token": "t"})
    assert r.status_code == 200
    assert r.json()["synced"] is True


def test_refute(monkeypatch):
    r = _client(monkeypatch).post("/api/v1/codium/assistant/refute", json={})
    assert r.status_code == 200
    assert r.json()["refuted"] is True


def test_get_agent_shares_confirm_store_across_calls_and_personas():
    """Regresija: token izdat u /command mora da ga nađe /confirm u SLEDEĆEM
    zahtevu. `get_agent()` pravi nov AssistantAgent po pozivu (persona,
    izvršioci), ali ConfirmStore mora biti isti primerak — inače je token
    uvek nepoznat i /confirm uvek vraća 400 (nezavisno od persone)."""

    prvi = codium_assistant_runtime.get_agent("opsti")
    drugi = codium_assistant_runtime.get_agent("opsti")
    treci = codium_assistant_runtime.get_agent("graditelj")
    assert prvi._confirm is drugi._confirm
    assert prvi._confirm is treci._confirm


def test_get_agent_shares_interaction_log_across_personas():
    """Regresija: /command upisuje predlog pod izabranom personom, ali
    /refute i /confirm grade agenta bez znanja koja je persona bila aktivna.
    Ako je InteractionLog po personi, refute/confirm vide samo dnevnik
    persone "opsti" i log_id iz drugih persona se nikad ne pronađe — zato
    dnevnik mora biti deljen (jedan primerak), isto kao ConfirmStore."""

    assert (
        codium_assistant_runtime.get_agent("opsti")._log
        is codium_assistant_runtime.get_agent("graditelj")._log
    )
