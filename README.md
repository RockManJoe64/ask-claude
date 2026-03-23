# askclaude

<img src="images/Ask-Claude-Mascot.png" width="256" height="256" alt="Ask Claude Mascot">

Query Claude from your terminal — single-shot or interactive REPL.

## Install

```sh
curl -sSf https://raw.githubusercontent.com/rockmanjoe64/ask-claude/main/install.sh | sh
```

Requires: [uv](https://docs.astral.sh/uv/), `git`, `curl`

## Usage

```sh
# Single-shot
askclaude "explain closures in one paragraph"

# Interactive REPL
askclaude

# Override output mode
askclaude -m plain "summarise this"
askclaude --mode stream
```

Type `/exit` or `/quit` to leave the REPL. Ctrl+C and Ctrl+D also work.

## Configuration

Set in `~/.config/askclaude/config` (created by the installer):

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_PROVIDER` | `anthropic` | Provider: `anthropic` (Anthropic API) or `bedrock` (AWS Bedrock) |
| `ASK_CLAUDE_API_KEY` | *(required for anthropic)* | Your Anthropic API key |
| `ASK_CLAUDE_MODEL` | `sonnet` | Model tier: `sonnet`, `opus`, or `haiku` |
| `ASK_CLAUDE_SYSTEM` | *(none)* | System prompt for every session |
| `ASK_CLAUDE_MAX_TOKENS` | `8096` | Max tokens per response |
| `ASK_CLAUDE_OUTPUT` | `stream+markdown` | Output mode: `plain`, `stream`, `stream+markdown` |

### Model tiers

Set `ASK_CLAUDE_MODEL` to a tier name — `askclaude` resolves it to the correct provider-specific model ID automatically:

| Tier | Anthropic API | AWS Bedrock |
|---|---|---|
| `sonnet` | `claude-sonnet-4-6` | `us.anthropic.claude-sonnet-4-6` |
| `opus` | `claude-opus-4-6` | `us.anthropic.claude-opus-4-6-v1` |
| `haiku` | `claude-haiku-4-5-20251001` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

You can also set a raw model ID directly if you need a specific version.

## AWS Bedrock

askclaude supports AWS Bedrock as an alternative to the direct Anthropic API. Bedrock authenticates using [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-how.html).

### Setup via installer

Run `install.sh` and select `bedrock` at the provider prompt. The installer will ask for your Bedrock API key and AWS region, then write the config automatically.

### Manual setup

Add the following to `~/.config/askclaude/config`:

```sh
export ASK_CLAUDE_PROVIDER="bedrock"
export ASK_CLAUDE_BEDROCK_API_KEY="your-bedrock-api-key"
export ASK_CLAUDE_AWS_REGION="us-west-2"
export ASK_CLAUDE_MODEL="sonnet"
```

### Bedrock-specific variables

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_BEDROCK_API_KEY` | *(required for bedrock)* | Your Amazon Bedrock API key |
| `ASK_CLAUDE_AWS_REGION` | `us-west-2` | AWS region. Also reads `AWS_REGION` and `AWS_DEFAULT_REGION` as fallbacks |

## Output Modes

| Mode | Behaviour |
|---|---|
| `plain` | Buffer response, print as plain text |
| `stream` | Print tokens as they arrive |
| `stream+markdown` | Stream tokens, re-render with rich markdown formatting |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (handles Python and dependency management automatically)
