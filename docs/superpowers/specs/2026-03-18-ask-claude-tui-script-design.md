# ask-claude: TUI Script Design

**Date:** 2026-03-18
**Status:** Approved

---

## Overview

A single-file Python script that exposes the Anthropic Claude API directly in the terminal. Supports both single-shot queries and an interactive REPL. Installed via a `curl | sh` command and configured through environment variables.

---

## Repository

`~/Workspaces/rockmanjoe64/ask-claude/` (GitHub: `rockmanjoe64/ask-claude`)

---

## File Structure

```
ask-claude/
├── ask-claude            # Shell wrapper (executable, symlinked to ~/.local/bin/)
├── ask-claude.py         # Python script with PEP 723 inline dependencies
├── install.sh            # Installer script (served via raw.githubusercontent.com)
├── README.md
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-18-ask-claude-tui-script-design.md
```

---

## Components

### 1. Shell Wrapper (`ask-claude`)

A thin bash script that sources the user config and delegates to `uv run`.

```bash
#!/usr/bin/env bash
[ -f "$HOME/.config/ask-claude/config" ] && source "$HOME/.config/ask-claude/config"
uv run "$(dirname "$(realpath "$0")")/ask-claude.py" "$@"
```

- Sourcing config here ensures env vars are available even if not exported in the user's shell profile
- Symlinked to `~/.local/bin/ask-claude` during installation

### 2. Python Script (`ask-claude.py`)

**Dependencies (PEP 723 inline metadata):**
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "rich"]
# ///
```

`uv run` reads this block and installs dependencies into an isolated cache on first run. No virtualenv or manual `pip install` required.

#### Mode Detection

| Invocation | Behavior |
|---|---|
| `ask-claude "some prompt"` | Single-shot: send prompt, print response, exit |
| `ask-claude -m plain "prompt"` | Single-shot with output mode override |
| `ask-claude` | Interactive REPL |
| `ask-claude -m stream` | Interactive REPL with output mode override |

Mode is determined by whether a positional argument (the prompt) is provided after flag parsing.

#### CLI Flags

| Flag | Description |
|---|---|
| `--mode`, `-m` | Override output mode: `plain`, `stream`, or `stream+markdown` |

#### Environment Variables

All use the `ASK_CLAUDE_` prefix to avoid conflicts with Claude Code (`CLAUDE_CODE_*`) and the Anthropic SDK defaults.

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_API_KEY` | *(required)* | Anthropic API key. Exits with a clear error message if missing. |
| `ASK_CLAUDE_MODEL` | `claude-sonnet-4-6` | Model ID to use |
| `ASK_CLAUDE_SYSTEM` | *(none)* | System prompt applied to every session |
| `ASK_CLAUDE_MAX_TOKENS` | `8096` | Maximum tokens per response |
| `ASK_CLAUDE_OUTPUT` | `stream+markdown` | Default output mode |

#### Output Mode Resolution

Priority order (highest wins):
1. CLI flag (`--mode` / `-m`)
2. `ASK_CLAUDE_OUTPUT` environment variable
3. Default: `stream+markdown`

#### Output Modes

| Mode | Behavior |
|---|---|
| `plain` | Buffer full response, print as plain text |
| `stream` | Stream tokens to stdout as they arrive |
| `stream+markdown` | Stream tokens, render final output with `rich` markdown (bold, code blocks, tables, etc.) |

#### REPL Behavior

- Maintains full conversation history across turns (all prior messages sent with each API call, as the Anthropic API is stateless)
- Displays a `You: ` prompt indicator
- Exits cleanly on: `exit`, `quit`, Ctrl+C, Ctrl+D

### 3. Installer (`install.sh`)

**Install command:**
```bash
curl -sSf https://raw.githubusercontent.com/rockmanjoe64/ask-claude/main/install.sh | sh
```

**Installer steps:**

1. Print a summary of all actions that will be taken and prompt the user for confirmation before proceeding
2. Check prerequisites: `uv`, `curl`, `git` — exit with installation instructions if any are missing
3. Clone the repo to `~/.local/share/ask-claude/`
4. Prompt interactively for:
   - `ASK_CLAUDE_API_KEY` (required)
   - `ASK_CLAUDE_MODEL` (optional, shows default)
   - `ASK_CLAUDE_SYSTEM` (optional)
   - `ASK_CLAUDE_OUTPUT` (optional, shows default)
5. Write `~/.config/ask-claude/config` with the collected exports
6. Symlink `~/.local/share/ask-claude/ask-claude` → `~/.local/bin/ask-claude`
7. Detect the user's shell (bash → `~/.bashrc`, zsh → `~/.zshrc`, fish → `~/.config/fish/config.fish`) and append a single `source ~/.config/ask-claude/config` line
8. Print a success message with usage examples

---

## Data Flow

```
User input
    │
    ▼
ask-claude (shell wrapper)
    │  sources ~/.config/ask-claude/config
    │  forwards all args
    ▼
ask-claude.py
    │  parses --mode / -m flag
    │  reads ASK_CLAUDE_* env vars
    │  determines mode: single-shot or REPL
    │
    ├─ single-shot ──► build message ──► POST /v1/messages ──► render output ──► exit
    │
    └─ REPL loop:
         read "You: " input
              │
              ▼
         append to history[]
              │
              ▼
         POST /v1/messages (full history)
              │
              ▼
         render output (plain / stream / stream+markdown)
              │
              ▼
         append assistant response to history[]
              │
              └─► repeat until exit/quit/Ctrl+C/Ctrl+D
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `ASK_CLAUDE_API_KEY` not set | Exit with message: `Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.` |
| API authentication error | Print Anthropic error message, exit with non-zero code |
| API rate limit / server error | Print error message and exit (no silent retry) |
| Invalid `--mode` value | Exit with message listing valid options |
| Ctrl+C / Ctrl+D in REPL | Print newline + `Goodbye.`, exit cleanly |

---

## Installation Artifacts

| Path | Description |
|---|---|
| `~/.local/share/ask-claude/` | Cloned repository |
| `~/.local/bin/ask-claude` | Symlink to shell wrapper |
| `~/.config/ask-claude/config` | User configuration (env var exports) |
| `~/.bashrc` / `~/.zshrc` / etc. | One appended `source` line |

---

## Out of Scope

- AWS Bedrock support (direct Anthropic API only)
- Conversation persistence across REPL sessions
- Image/file input
- Multiple named profiles
- `pyproject.toml`-based dependency management (deferred until script grows in complexity)
