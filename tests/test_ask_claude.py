import os
import pytest
import importlib.util
import sys
from unittest.mock import MagicMock, patch


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


def test_parse_args_single_shot(mod):
    args = mod.parse_args(["hello world"])
    assert args.prompt == "hello world"
    assert args.mode is None


def test_parse_args_repl_no_args(mod):
    args = mod.parse_args([])
    assert args.prompt is None
    assert args.mode is None


def test_parse_args_mode_flag_short(mod):
    args = mod.parse_args(["-m", "plain", "hello"])
    assert args.mode == "plain"
    assert args.prompt == "hello"


def test_parse_args_mode_flag_long(mod):
    args = mod.parse_args(["--mode", "stream"])
    assert args.mode == "stream"
    assert args.prompt is None


def test_parse_args_invalid_mode_exits(mod):
    with pytest.raises(SystemExit):
        mod.parse_args(["--mode", "invalid"])


def test_resolve_output_mode_cli_wins(mod):
    assert mod.resolve_output_mode("plain", "stream+markdown") == "plain"


def test_resolve_output_mode_env_fallback(mod):
    assert mod.resolve_output_mode(None, "stream") == "stream"


def test_resolve_output_mode_default(mod):
    assert mod.resolve_output_mode(None, None) == "stream+markdown"


def make_stream_events(texts):
    """Build a list of mock Anthropic streaming text delta events."""
    events = []
    for text in texts:
        event = MagicMock()
        event.type = "content_block_delta"
        event.delta = MagicMock()
        event.delta.type = "text_delta"
        event.delta.text = text
        events.append(event)
    return events


def test_render_plain_returns_full_text(mod, capsys):
    events = make_stream_events(["Hello", ", ", "world"])
    result = mod.render_plain(iter(events))
    assert result == "Hello, world"
    captured = capsys.readouterr()
    assert "Hello, world" in captured.out


def test_render_stream_prints_tokens(mod, capsys):
    events = make_stream_events(["Hi", " there"])
    mod.render_stream(iter(events))
    captured = capsys.readouterr()
    assert "Hi" in captured.out
    assert "there" in captured.out


def test_render_stream_markdown_returns_full_text(mod, monkeypatch):
    events = make_stream_events(["**bold**"])
    mock_print = MagicMock()

    # Mock Console locally since it's lazily imported
    import sys
    mock_console_module = MagicMock()
    mock_console_class = MagicMock()
    mock_console_class.return_value.print = mock_print
    mock_console_module.Console = mock_console_class

    mock_markdown = MagicMock()

    # Pre-emptively mock rich in sys.modules before the function is called
    sys.modules["rich"] = MagicMock()
    sys.modules["rich.console"] = mock_console_module
    sys.modules["rich.markdown"] = MagicMock()
    sys.modules["rich.markdown"].Markdown = mock_markdown

    try:
        result = mod.render_stream_markdown(iter(events))
        assert result == "**bold**"
    finally:
        # Clean up
        sys.modules.pop("rich", None)
        sys.modules.pop("rich.console", None)
        sys.modules.pop("rich.markdown", None)


def test_single_shot_calls_api_and_renders(mod, monkeypatch):
    mock_stream = MagicMock()
    mock_stream.__iter__ = MagicMock(return_value=iter(make_stream_events(["Hi"])))
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    config = {
        "api_key": "key",
        "model": "claude-sonnet-4-6",
        "system": None,
        "max_tokens": 8096,
        "output": "plain",
    }

    # Mock anthropic module locally since it's lazily imported
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    # Pre-emptively mock anthropic in sys.modules before the function is called
    sys.modules["anthropic"] = mock_anthropic

    try:
        mod.run_single_shot("hello", config, output_mode="plain")
        mock_client.messages.stream.assert_called_once()
        call_kwargs = mock_client.messages.stream.call_args.kwargs
        assert call_kwargs["messages"][0]["content"] == "hello"
        assert call_kwargs["model"] == "claude-sonnet-4-6"
    finally:
        # Clean up
        sys.modules.pop("anthropic", None)


def test_single_shot_passes_system_prompt(mod, monkeypatch):
    mock_stream = MagicMock()
    mock_stream.__iter__ = MagicMock(return_value=iter([]))
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    config = {
        "api_key": "key",
        "model": "claude-sonnet-4-6",
        "system": "Be brief.",
        "max_tokens": 8096,
        "output": "plain",
    }

    # Mock anthropic module locally since it's lazily imported
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    # Pre-emptively mock anthropic in sys.modules before the function is called
    sys.modules["anthropic"] = mock_anthropic

    try:
        mod.run_single_shot("hello", config, output_mode="plain")
        call_kwargs = mock_client.messages.stream.call_args.kwargs
        assert call_kwargs["system"] == "Be brief."
    finally:
        # Clean up
        sys.modules.pop("anthropic", None)
