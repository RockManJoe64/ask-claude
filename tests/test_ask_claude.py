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


def test_load_config_provider_defaults_to_direct(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    monkeypatch.delenv("ASK_CLAUDE_PROVIDER", raising=False)
    config = mod.load_config()
    assert config["provider"] == "direct"


def test_load_config_invalid_provider_exits(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "invalid")
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    with pytest.raises(SystemExit) as exc:
        mod.load_config()
    assert exc.value.code != 0


def test_load_config_bedrock_reads_bedrock_api_key(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "bedrock-key")
    monkeypatch.delenv("ASK_CLAUDE_API_KEY", raising=False)
    config = mod.load_config()
    assert config["bedrock_api_key"] == "bedrock-key"


def test_load_config_bedrock_missing_key_exits(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.delenv("ASK_CLAUDE_BEDROCK_API_KEY", raising=False)
    monkeypatch.delenv("ASK_CLAUDE_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.load_config()
    assert exc.value.code != 0


def test_load_config_direct_default_model(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "direct")
    monkeypatch.delenv("ASK_CLAUDE_MODEL", raising=False)
    config = mod.load_config()
    assert config["model"] == "claude-sonnet-4-6"


def test_load_config_bedrock_default_model(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "key")
    monkeypatch.delenv("ASK_CLAUDE_MODEL", raising=False)
    config = mod.load_config()
    assert config["model"] == "anthropic.claude-sonnet-4-6"


def test_load_config_region_ask_claude_aws_region_wins(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "key")
    monkeypatch.setenv("ASK_CLAUDE_AWS_REGION", "eu-west-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    config = mod.load_config()
    assert config["aws_region"] == "eu-west-1"


def test_load_config_region_falls_back_to_aws_region(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "key")
    monkeypatch.delenv("ASK_CLAUDE_AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    config = mod.load_config()
    assert config["aws_region"] == "ap-southeast-1"


def test_load_config_region_falls_back_to_aws_default_region(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "key")
    monkeypatch.delenv("ASK_CLAUDE_AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-central-1")
    config = mod.load_config()
    assert config["aws_region"] == "ca-central-1"


def test_load_config_region_defaults_to_us_west_2(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_PROVIDER", "bedrock")
    monkeypatch.setenv("ASK_CLAUDE_BEDROCK_API_KEY", "key")
    monkeypatch.delenv("ASK_CLAUDE_AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    config = mod.load_config()
    assert config["aws_region"] == "us-west-2"


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


def test_repl_exits_on_slash_exit(mod, monkeypatch):
    inputs = iter(["/exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    config = {
        "api_key": "key", "model": "claude-sonnet-4-6",
        "system": None, "max_tokens": 8096, "output": "plain",
    }
    # Should return without error
    mod.run_repl(config, output_mode="plain")


def test_repl_exits_on_slash_quit(mod, monkeypatch):
    inputs = iter(["/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    config = {
        "api_key": "key", "model": "claude-sonnet-4-6",
        "system": None, "max_tokens": 8096, "output": "plain",
    }
    mod.run_repl(config, output_mode="plain")


def test_repl_sends_history(mod, monkeypatch):
    mock_stream = MagicMock()
    mock_stream.__iter__ = MagicMock(return_value=iter(make_stream_events(["Hi"])))
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    # First turn sends a message, second turn exits
    call_count = 0
    def fake_input(_):
        nonlocal call_count
        call_count += 1
        return "hello" if call_count == 1 else "/exit"

    monkeypatch.setattr("builtins.input", fake_input)

    config = {
        "api_key": "key", "model": "claude-sonnet-4-6",
        "system": None, "max_tokens": 8096, "output": "plain",
    }

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    import sys
    sys.modules["anthropic"] = mock_anthropic
    try:
        mod.run_repl(config, output_mode="plain")
    finally:
        sys.modules.pop("anthropic", None)

    mock_client.messages.stream.assert_called_once()
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["messages"][0] == {"role": "user", "content": "hello"}


def test_main_single_shot_dispatches(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    monkeypatch.setattr("sys.argv", ["ask-claude", "hello"])

    called_with = {}
    def fake_single_shot(prompt, config, output_mode):
        called_with["prompt"] = prompt
        called_with["output_mode"] = output_mode

    monkeypatch.setattr(mod, "run_single_shot", fake_single_shot)
    mod.main()
    assert called_with["prompt"] == "hello"


def test_main_repl_dispatches(mod, monkeypatch):
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "key")
    monkeypatch.setattr("sys.argv", ["ask-claude"])

    called = {}
    def fake_repl(config, output_mode):
        called["yes"] = True

    monkeypatch.setattr(mod, "run_repl", fake_repl)
    mod.main()
    assert called.get("yes")


def test_api_error_exits_cleanly(mod, monkeypatch):
    import sys as _sys

    mock_auth_error_class = type("AuthenticationError", (Exception,), {})
    mock_api_status_error_class = type("APIStatusError", (Exception,), {})

    mock_stream_cm = MagicMock()
    mock_stream_cm.__enter__ = MagicMock(side_effect=mock_auth_error_class("Invalid API key"))
    mock_stream_cm.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_cm

    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_anthropic.AuthenticationError = mock_auth_error_class
    mock_anthropic.APIStatusError = mock_api_status_error_class

    _sys.modules["anthropic"] = mock_anthropic

    config = {
        "api_key": "bad-key", "model": "claude-sonnet-4-6",
        "system": None, "max_tokens": 8096, "output": "plain",
    }

    try:
        with pytest.raises(SystemExit) as exc:
            mod.run_single_shot("hello", config, output_mode="plain")
        assert exc.value.code != 0
    finally:
        _sys.modules.pop("anthropic", None)
