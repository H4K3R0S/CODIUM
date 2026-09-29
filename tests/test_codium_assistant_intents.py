from core.domains.codium.assistant.intents import CODIUM_INTENTS


def test_komande_prisutne():
    assert set(CODIUM_INTENTS) == {
        "list_repos", "list_pipelines", "repo_status", "sync_repo", "run_pipeline", "open",
        "open_second_brain_map"}
    assert CODIUM_INTENTS["sync_repo"].is_write is True
    assert CODIUM_INTENTS["run_pipeline"].is_write is True
    assert CODIUM_INTENTS["open"].is_navigate is True
    assert CODIUM_INTENTS["open_second_brain_map"].is_navigate is True
    assert CODIUM_INTENTS["open_second_brain_map"].is_write is False
    assert CODIUM_INTENTS["open_second_brain_map"].required_params == ()
    assert CODIUM_INTENTS["list_repos"].is_write is False
