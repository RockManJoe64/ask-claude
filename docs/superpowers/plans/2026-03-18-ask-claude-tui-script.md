# ask-claude TUI Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-file Python CLI tool that lets users query Claude via the Anthropic API in single-shot or interactive REPL mode, installed via a `curl | sh` command.

**Architecture:** One Python script (`ask-claude.py`) with PEP 723 inline dependencies, fronted by a thin bash wrapper (`ask-claude`) that sources user config. A separate `install.sh` handles cloning, config generation, symlinking, and shell rc patching.

**Tech Stack:** Python 3.11+, `uv` (script runner), `anthropic` SDK, `rich` (markdown rendering), bash (wrapper + installer)

---

## File Map

| File | Responsibility |
|---|---|
| `ask-claude.py` | All Python logic: config, arg parsing, API calls, output rendering, REPL loop |
| `ask-claude` | Bash wrapper: sources config, delegates to `uv run ask-claude.py` |
| `install.sh` | Installer: prereq checks, clone/pull, config prompts, symlink, rc patching |
| `README.md` | Usage documentation |
| `tests/test_ask_claude.py` | Unit tests (run via `uv run --with pytest --with pytest-mock pytest`) |

---

## Task 1: Scaffold — Shell Wrapper + Python Skeleton + .gitignore

**Files:**
- Create: `ask-claude` (shell wrapper)
- Create: `ask-claude.py` (Python skeleton)
- Create: `.gitignore`

- [ ] **Step 1: Create the shell wrapper `ask-claude`**

```bash
#!/usr/bin/env bash
set -euo pipefail
[ -f "$HOME/.config/ask-claude/config" ] && source "$HOME/.config/ask-claude/config"
uv run "$(dirname "$(realpath "$0")")/ask-claude.py" "$@"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x ask-claude
```

- [ ] **Step 3: Create the Python skeleton `ask-claude.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "rich"]
# ///

"""ask-claude: Query Claude from your terminal."""


def main() -> None:
    pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.uv/
.venv/
```

- [ ] **Step 5: Verify `uv run ask-claude.py` exits cleanly**

Run: `uv run ask-claude.py`
Expected: no output, exit code 0

- [ ] **Step 6: Commit**

```bash
git add ask-claude ask-claude.py .gitignore
git commit -m "feat: scaffold shell wrapper and Python skeleton"
```

---

## Task 2: Config Loading

**Files:**
- Modify: `ask-claude.py`
- Create: `tests/test_ask_claude.py`

Config is loaded from `ASK_CLAUDE_*` environment variables. The API key is required; all others have defaults.

- [ ] **Step 1: Write failing tests**

Create `tests/test_ask_claude.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "config"
```
Expected: `AttributeError: module 'ask_claude' has no attribute 'load_config'`

- [ ] **Step 3: Implement `load_config()` in `ask-claude.py`**

```python
import os
import sys


def load_config() -> dict:
    api_key = os.environ.get("ASK_CLAUDE_API_KEY")
    if not api_key:
        print(
            "Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.",
            file=sys.stderr,
        )
        sys.exit(1)
    return {
        "api_key": api_key,
        "model": os.environ.get("ASK_CLAUDE_MODEL", "claude-sonnet-4-6"),
        "system": os.environ.get("ASK_CLAUDE_SYSTEM") or None,
        "max_tokens": int(os.environ.get("ASK_CLAUDE_MAX_TOKENS", "8096")),
        "output": os.environ.get("ASK_CLAUDE_OUTPUT", "stream+markdown"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "config"
```
Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: add config loading from ASK_CLAUDE_* env vars"
```

---

## Task 3: CLI Argument Parsing

**Files:**
- Modify: `ask-claude.py`
- Modify: `tests/test_ask_claude.py`

Parse `--mode`/`-m` and an optional positional prompt. Mode detection: prompt present → single-shot, no prompt → REPL.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ask_claude.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "args or mode"
```
Expected: `AttributeError: module has no attribute 'parse_args'`

- [ ] **Step 3: Implement `parse_args()` and `resolve_output_mode()` in `ask-claude.py`**

```python
import argparse
from typing import Optional


VALID_MODES = ("plain", "stream", "stream+markdown")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ask-claude",
        description="Query Claude from your terminal.",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=VALID_MODES,
        default=None,
        help="Output mode: plain, stream, or stream+markdown",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Prompt for single-shot mode. Omit to start REPL.",
    )
    return parser.parse_args(argv)


def resolve_output_mode(cli_mode: Optional[str], env_mode: Optional[str]) -> str:
    return cli_mode or env_mode or "stream+markdown"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "args or mode"
```
Expected: 8 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: add CLI argument parsing and output mode resolution"
```

---

## Task 4: Output Rendering

**Files:**
- Modify: `ask-claude.py`
- Modify: `tests/test_ask_claude.py`

Three rendering functions: `render_plain`, `render_stream`, `render_stream_markdown`. All accept a streaming response iterator from the Anthropic SDK.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ask_claude.py`:

```python
from unittest.mock import MagicMock, patch


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


def test_render_plain_returns_full_text(mod):
    events = make_stream_events(["Hello", ", ", "world"])
    result = mod.render_plain(iter(events))
    assert result == "Hello, world"


def test_render_stream_prints_tokens(mod, capsys):
    events = make_stream_events(["Hi", " there"])
    mod.render_stream(iter(events))
    captured = capsys.readouterr()
    assert "Hi" in captured.out
    assert "there" in captured.out


def test_render_stream_markdown_returns_full_text(mod):
    events = make_stream_events(["**bold**"])
    with patch("rich.console.Console.print"):
        result = mod.render_stream_markdown(iter(events))
    assert result == "**bold**"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "render"
```
Expected: `AttributeError: module has no attribute 'render_plain'`

- [ ] **Step 3: Implement the three render functions in `ask-claude.py`**

```python
from typing import Iterator
from rich.console import Console
from rich.markdown import Markdown


def _extract_text_events(stream: Iterator) -> Iterator[str]:
    """Yield text strings from Anthropic streaming events."""
    for event in stream:
        if (
            event.type == "content_block_delta"
            and event.delta.type == "text_delta"
        ):
            yield event.delta.text


def render_plain(stream: Iterator) -> str:
    """Buffer all tokens, return and print as plain text."""
    full_text = "".join(_extract_text_events(stream))
    print(full_text)
    return full_text


def render_stream(stream: Iterator) -> str:
    """Print tokens to stdout as they arrive."""
    parts = []
    for token in _extract_text_events(stream):
        print(token, end="", flush=True)
        parts.append(token)
    print()  # trailing newline
    return "".join(parts)


def render_stream_markdown(stream: Iterator) -> str:
    """Stream tokens, then re-render full response with rich markdown."""
    parts = []
    for token in _extract_text_events(stream):
        print(token, end="", flush=True)
        parts.append(token)
    full_text = "".join(parts)
    print("\r", end="")  # return to start of line before re-render
    console = Console()
    console.print(Markdown(full_text))
    return full_text
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "render"
```
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: add plain, stream, and stream+markdown output renderers"
```

---

## Task 5: Single-Shot Mode

**Files:**
- Modify: `ask-claude.py`
- Modify: `tests/test_ask_claude.py`

Call the API with a single user message and render the response.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ask_claude.py`:

```python
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

    with patch("anthropic.Anthropic", return_value=mock_client):
        mod.run_single_shot("hello", config, output_mode="plain")

    mock_client.messages.stream.assert_called_once()
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["messages"][0]["content"] == "hello"
    assert call_kwargs["model"] == "claude-sonnet-4-6"


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

    with patch("anthropic.Anthropic", return_value=mock_client):
        mod.run_single_shot("hello", config, output_mode="plain")

    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["system"] == "Be brief."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "single_shot"
```
Expected: `AttributeError: module has no attribute 'run_single_shot'`

- [ ] **Step 3: Implement `run_single_shot()` in `ask-claude.py`**

```python
import anthropic


def run_single_shot(prompt: str, config: dict, output_mode: str) -> None:
    client = anthropic.Anthropic(api_key=config["api_key"])

    stream_kwargs = dict(
        model=config["model"],
        max_tokens=config["max_tokens"],
        messages=[{"role": "user", "content": prompt}],
    )
    if config["system"]:
        stream_kwargs["system"] = config["system"]

    with client.messages.stream(**stream_kwargs) as stream:
        if output_mode == "plain":
            render_plain(stream)
        elif output_mode == "stream":
            render_stream(stream)
        else:
            render_stream_markdown(stream)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "single_shot"
```
Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: implement single-shot mode"
```

---

## Task 6: REPL Mode

**Files:**
- Modify: `ask-claude.py`
- Modify: `tests/test_ask_claude.py`

Interactive loop with conversation history. `/exit`, `/quit`, Ctrl+C, and Ctrl+D all exit cleanly.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ask_claude.py`:

```python
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

    with patch("anthropic.Anthropic", return_value=mock_client):
        mod.run_repl(config, output_mode="plain")

    mock_client.messages.stream.assert_called_once()
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["messages"][0] == {"role": "user", "content": "hello"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "repl"
```
Expected: `AttributeError: module has no attribute 'run_repl'`

- [ ] **Step 3: Implement `run_repl()` in `ask-claude.py`**

```python
def run_repl(config: dict, output_mode: str) -> None:
    client = anthropic.Anthropic(api_key=config["api_key"])
    history: list[dict] = []

    print("Claude REPL — type /exit or /quit to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input in ("/exit", "/quit"):
            print("Goodbye.")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        stream_kwargs = dict(
            model=config["model"],
            max_tokens=config["max_tokens"],
            messages=history,
        )
        if config["system"]:
            stream_kwargs["system"] = config["system"]

        with client.messages.stream(**stream_kwargs) as stream:
            if output_mode == "plain":
                response_text = render_plain(stream)
            elif output_mode == "stream":
                response_text = render_stream(stream)
            else:
                response_text = render_stream_markdown(stream)

        history.append({"role": "assistant", "content": response_text})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "repl"
```
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: implement interactive REPL mode with conversation history"
```

---

## Task 7: Error Handling + Wire Up `main()`

**Files:**
- Modify: `ask-claude.py`
- Modify: `tests/test_ask_claude.py`

Wrap API calls in error handlers. Wire `main()` to call `load_config()`, `parse_args()`, `resolve_output_mode()`, and dispatch to the correct mode.

- [ ] **Step 1: Write failing tests for error handling**

Add to `tests/test_ask_claude.py`:

```python
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
    monkeypatch.setenv("ASK_CLAUDE_API_KEY", "bad-key")

    mock_client = MagicMock()
    mock_client.messages.stream.side_effect = anthropic.AuthenticationError(
        message="Invalid API key", response=MagicMock(), body={}
    )

    config = {
        "api_key": "bad-key", "model": "claude-sonnet-4-6",
        "system": None, "max_tokens": 8096, "output": "plain",
    }

    with patch("anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(SystemExit) as exc:
            mod.run_single_shot("hello", config, output_mode="plain")
    assert exc.value.code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest --with pytest-mock pytest tests/test_ask_claude.py -v -k "main or api_error"
```
Expected: failures on missing `main` dispatch logic and missing error handling

- [ ] **Step 3: Add error handling wrappers and wire up `main()` in `ask-claude.py`**

Replace `run_single_shot`, `run_repl`, and `main()` with these complete implementations:

```python
def _handle_api_error(e: Exception) -> None:
    print(f"\nError: {e}", file=sys.stderr)
    sys.exit(1)


def run_single_shot(prompt: str, config: dict, output_mode: str) -> None:
    client = anthropic.Anthropic(api_key=config["api_key"])

    stream_kwargs = dict(
        model=config["model"],
        max_tokens=config["max_tokens"],
        messages=[{"role": "user", "content": prompt}],
    )
    if config["system"]:
        stream_kwargs["system"] = config["system"]

    try:
        with client.messages.stream(**stream_kwargs) as stream:
            if output_mode == "plain":
                render_plain(stream)
            elif output_mode == "stream":
                render_stream(stream)
            else:
                render_stream_markdown(stream)
    except anthropic.AuthenticationError as e:
        _handle_api_error(e)
    except anthropic.APIStatusError as e:
        _handle_api_error(e)


def run_repl(config: dict, output_mode: str) -> None:
    client = anthropic.Anthropic(api_key=config["api_key"])
    history: list[dict] = []

    print("Claude REPL — type /exit or /quit to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input in ("/exit", "/quit"):
            print("Goodbye.")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        stream_kwargs = dict(
            model=config["model"],
            max_tokens=config["max_tokens"],
            messages=history,
        )
        if config["system"]:
            stream_kwargs["system"] = config["system"]

        try:
            with client.messages.stream(**stream_kwargs) as stream:
                if output_mode == "plain":
                    response_text = render_plain(stream)
                elif output_mode == "stream":
                    response_text = render_stream(stream)
                else:
                    response_text = render_stream_markdown(stream)
        except anthropic.AuthenticationError as e:
            _handle_api_error(e)
        except anthropic.APIStatusError as e:
            _handle_api_error(e)

        history.append({"role": "assistant", "content": response_text})


def main() -> None:
    config = load_config()
    args = parse_args()
    output_mode = resolve_output_mode(args.mode, config["output"])

    if args.prompt:
        run_single_shot(args.prompt, config, output_mode)
    else:
        run_repl(config, output_mode)
```

- [ ] **Step 4: Run the full test suite**

```bash
uv run --with pytest --with pytest-mock pytest tests/ -v
```
Expected: all tests PASSED

- [ ] **Step 5: Smoke test manually**

```bash
ASK_CLAUDE_API_KEY=your-key uv run ask-claude.py "say hello in one word"
```
Expected: Claude responds with a single word

- [ ] **Step 6: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: add error handling and wire up main()"
```

---

## Task 8: Installer (`install.sh`)

**Files:**
- Create: `install.sh`

Full installer: prereq checks, clone/pull, interactive config prompts, config file write, symlink, rc patching.

- [ ] **Step 1: Create `install.sh`**

```bash
#!/usr/bin/env sh
set -e

REPO_URL="https://github.com/rockmanjoe64/ask-claude.git"
INSTALL_DIR="$HOME/.local/share/ask-claude"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/ask-claude"
CONFIG_FILE="$CONFIG_DIR/config"

# --- helpers ---
info()  { printf '\033[0;34m[ask-claude]\033[0m %s\n' "$1"; }
ok()    { printf '\033[0;32m[ask-claude]\033[0m %s\n' "$1"; }
err()   { printf '\033[0;31m[ask-claude]\033[0m %s\n' "$1" >&2; exit 1; }
prompt(){ printf '%s' "$1"; read -r REPLY; echo "$REPLY"; }

# --- summary ---
echo ""
echo "ask-claude installer"
echo "===================="
echo "This script will:"
echo "  1. Check prerequisites (uv, curl, git)"
echo "  2. Clone/update the repo to $INSTALL_DIR"
echo "  3. Prompt for your Anthropic API key and preferences"
echo "  4. Write $CONFIG_FILE"
echo "  5. Symlink ask-claude to $BIN_DIR/ask-claude"
echo "  6. Add 'source $CONFIG_FILE' to your shell rc file"
echo ""
printf 'Continue? [y/N] '
read -r CONFIRM
case "$CONFIRM" in
  y|Y|yes|Yes) ;;
  *) echo "Aborted."; exit 0 ;;
esac
echo ""

# --- prereqs ---
for cmd in uv curl git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "Required tool '$cmd' is not installed. Please install it and re-run."
  fi
done
info "Prerequisites OK."

# --- clone or pull ---
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Existing install found. Pulling latest changes..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Cloning repository..."
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

# --- config prompts ---
echo ""
info "Configuration"

printf 'Anthropic API key (required): '
read -r API_KEY
[ -z "$API_KEY" ] && err "API key is required."

printf 'Model [claude-sonnet-4-6]: '
read -r MODEL
MODEL="${MODEL:-claude-sonnet-4-6}"

printf 'System prompt (optional, press Enter to skip): '
read -r SYSTEM

printf 'Output mode — plain/stream/stream+markdown [stream+markdown]: '
read -r OUTPUT
OUTPUT="${OUTPUT:-stream+markdown}"

# --- write config ---
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
# ask-claude configuration
# Edit this file to change defaults. Re-run install.sh to reconfigure.
export ASK_CLAUDE_API_KEY="$API_KEY"
export ASK_CLAUDE_MODEL="$MODEL"
export ASK_CLAUDE_OUTPUT="$OUTPUT"
EOF
if [ -n "$SYSTEM" ]; then
  echo "export ASK_CLAUDE_SYSTEM=\"$SYSTEM\"" >> "$CONFIG_FILE"
fi
ok "Config written to $CONFIG_FILE"

# --- symlink ---
mkdir -p "$BIN_DIR"
chmod +x "$INSTALL_DIR/ask-claude"
ln -sf "$INSTALL_DIR/ask-claude" "$BIN_DIR/ask-claude"
ok "Symlinked ask-claude to $BIN_DIR/ask-claude"

# --- shell rc patching ---
SOURCE_LINE="source \"$CONFIG_FILE\""

detect_rc() {
  case "${SHELL:-}" in
    */zsh)  echo "$HOME/.zshrc" ;;
    */fish) echo "$HOME/.config/fish/config.fish" ;;
    *)      echo "$HOME/.bashrc" ;;
  esac
}

RC_FILE="$(detect_rc)"
if [ -f "$RC_FILE" ] && grep -qF "$CONFIG_FILE" "$RC_FILE" 2>/dev/null; then
  info "Shell rc already configured ($RC_FILE). Skipping."
else
  echo "" >> "$RC_FILE"
  echo "# ask-claude" >> "$RC_FILE"
  echo "$SOURCE_LINE" >> "$RC_FILE"
  ok "Added source line to $RC_FILE"
fi

# --- done ---
echo ""
ok "Installation complete!"
echo ""
echo "  Restart your shell or run:  source $CONFIG_FILE"
echo ""
echo "  Usage:"
echo "    ask-claude \"explain closures\"    # single-shot"
echo "    ask-claude                        # interactive REPL"
echo "    ask-claude -m plain \"hello\"      # override output mode"
echo ""
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Dry-run test — verify prereq check works**

```bash
# Temporarily rename uv to simulate missing prereq
sh -c 'PATH="" sh install.sh' || echo "exit code: $?"
```
Expected: `Required tool 'uv' is not installed` error message

- [ ] **Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add curl-pipe-sh installer"
```

---

## Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# ask-claude

Query Claude from your terminal — single-shot or interactive REPL.

## Install

```sh
curl -sSf https://raw.githubusercontent.com/rockmanjoe64/ask-claude/main/install.sh | sh
```

Requires: [uv](https://docs.astral.sh/uv/), `git`, `curl`

## Usage

```sh
# Single-shot
ask-claude "explain closures in one paragraph"

# Interactive REPL
ask-claude

# Override output mode
ask-claude -m plain "summarise this"
ask-claude --mode stream
```

Type `/exit` or `/quit` to leave the REPL. Ctrl+C and Ctrl+D also work.

## Configuration

Set in `~/.config/ask-claude/config` (created by the installer):

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_API_KEY` | *(required)* | Your Anthropic API key |
| `ASK_CLAUDE_MODEL` | `claude-sonnet-4-6` | Model to use |
| `ASK_CLAUDE_SYSTEM` | *(none)* | System prompt for every session |
| `ASK_CLAUDE_MAX_TOKENS` | `8096` | Max tokens per response |
| `ASK_CLAUDE_OUTPUT` | `stream+markdown` | Output mode: `plain`, `stream`, `stream+markdown` |

## Output Modes

| Mode | Behaviour |
|---|---|
| `plain` | Buffer response, print as plain text |
| `stream` | Print tokens as they arrive |
| `stream+markdown` | Stream tokens, re-render with rich markdown formatting |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (handles Python and dependency management automatically)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install and usage instructions"
```

---

## Task 10: Final Verification

- [ ] **Step 1: Run the full test suite one final time**

```bash
uv run --with pytest --with pytest-mock pytest tests/ -v
```
Expected: all tests PASSED

- [ ] **Step 2: Verify the script runs end-to-end in single-shot mode**

```bash
ASK_CLAUDE_API_KEY=your-key uv run ask-claude.py "say exactly: hello"
```
Expected: `hello` (or similar)

- [ ] **Step 3: Verify REPL starts and exits cleanly**

```bash
echo "/exit" | ASK_CLAUDE_API_KEY=your-key uv run ask-claude.py
```
Expected: `Claude REPL — type /exit or /quit to exit.` then `Goodbye.`

- [ ] **Step 4: Verify error message on missing API key**

```bash
uv run ask-claude.py "hello" 2>&1 || true
```
Expected: `Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.`

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: final verification fixes" # only if changes were made
```
