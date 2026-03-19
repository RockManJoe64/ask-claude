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
