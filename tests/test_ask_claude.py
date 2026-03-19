import os
import pytest
import importlib.util
import sys


def load_module():
    spec = importlib.util.spec_from_file_location("ask_claude", "ask-claude.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mod():
    return load_module()


def test_load_config_reads_api_key(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "test-key")
    config = mod.load_config()
    assert config["api_key"] == "test-key"


def test_load_config_defaults(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "test-key")
    monkeypatch.delenv("ASK_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("ASK_CLAUDE_SYSTEM", raising=False)
    monkeypatch.delenv("ASK_CLAUDE_MAX_TOKENS", raising=False)
    monkeypatch.delenv("ASK_CLAUDE_OUTPUT", raising=False)
    config = mod.load_config()
    assert config["model"] == "claude-sonnet-4-6"
    assert config["system"] is None
    assert config["max_tokens"] == 8096
    assert config["output"] == "stream+markdown"


def test_load_config_missing_api_key_exits(mod, monkeypatch):
    monkeypatch.delenv("ASK_CLAUDE_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.load_config()
    assert exc.value.code != 0


def test_load_config_custom_values(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    monkeypatch.setenv("ASK_CLAUDE_MODEL", "claude-opus-4-6")
    monkeypatch.setenv("ASK_CLAUDE_SYSTEM", "Be concise.")
    monkeypatch.setenv("ASK_CLAUDE_MAX_TOKENS", "1024")
    monkeypatch.setenv("ASK_CLAUDE_OUTPUT", "plain")
    config = mod.load_config()
    assert config["model"] == "claude-opus-4-6"
    assert config["system"] == "Be concise."
    assert config["max_tokens"] == 1024
    assert config["output"] == "plain"
