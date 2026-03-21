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
| `ASK_CLAUDE_PROVIDER` | `direct` | Provider: `direct` (Anthropic API) or `bedrock` (AWS Bedrock) |
| `ASK_CLAUDE_API_KEY` | *(required for direct)* | Your Anthropic API key |
| `ASK_CLAUDE_MODEL` | `claude-sonnet-4-6` | Model to use |
| `ASK_CLAUDE_SYSTEM` | *(none)* | System prompt for every session |
| `ASK_CLAUDE_MAX_TOKENS` | `8096` | Max tokens per response |
| `ASK_CLAUDE_OUTPUT` | `stream+markdown` | Output mode: `plain`, `stream`, `stream+markdown` |

## AWS Bedrock

ask-claude supports AWS Bedrock as an alternative to the direct Anthropic API. Bedrock authenticates using [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-how.html).

### Setup via installer

Run `install.sh` and select `bedrock` at the provider prompt. The installer will ask for your Bedrock API key and AWS region, then write the config automatically.

### Manual setup

Add the following to `~/.config/ask-claude/config`:

```sh
export ASK_CLAUDE_PROVIDER="bedrock"
export ASK_CLAUDE_BEDROCK_API_KEY="your-bedrock-api-key"
export ASK_CLAUDE_AWS_REGION="us-west-2"
export ASK_CLAUDE_MODEL="us.anthropic.claude-sonnet-4-6"
```

### Bedrock-specific variables

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_BEDROCK_API_KEY` | *(required for bedrock)* | Your Amazon Bedrock API key |
| `ASK_CLAUDE_AWS_REGION` | `us-west-2` | AWS region. Also reads `AWS_REGION` and `AWS_DEFAULT_REGION` as fallbacks |

### Bedrock model IDs

Bedrock uses different model IDs from the direct API. The default when `ASK_CLAUDE_PROVIDER=bedrock` is `anthropic.claude-sonnet-4-6`. Examples:

| Model | Bedrock model ID |
|---|---|
| Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` |
| Claude Opus 4.6 | `global.anthropic.claude-opus-4-6-v1` |
| Claude Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` |

See the [AWS Bedrock model IDs documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html) for the full list.

## Output Modes

| Mode | Behaviour |
|---|---|
| `plain` | Buffer response, print as plain text |
| `stream` | Print tokens as they arrive |
| `stream+markdown` | Stream tokens, re-render with rich markdown formatting |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (handles Python and dependency management automatically)
