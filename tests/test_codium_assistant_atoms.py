from __future__ import annotations

from pathlib import Path

from core.cell.assistant.atoms import AtomLoader

_BASE = Path(__file__).resolve().parents[1] / ".ai" / "atomi" / "personas"
_IDS = ["opsti", "arhitekta", "graditelj", "recenzent", "dizajner", "menadzer",
        "debager", "pisac", "bezbednjak", "devops", "tester", "data-engineer"]


def test_svih_12_persona_postoji():
    for pid in _IDS:
        assert (_BASE / pid / "persona.md").is_file(), pid


def test_deljeni_katalog_ima_komande():
    loader = AtomLoader(_BASE / "opsti", shared_root=_BASE / "_shared")
    catalog = loader.command_catalog()
    for intent in ("list_repos", "sync_repo", "run_pipeline", "open"):
        assert intent in catalog
    assert "repo" in loader.tool("repo").body.lower()
    assert "pipeline" in loader.tool("pipeline").body.lower()


def test_persona_telo_iz_root():
    loader = AtomLoader(_BASE / "graditelj", shared_root=_BASE / "_shared")
    assert loader.persona().body.strip()
