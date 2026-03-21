# ask-claude: AWS Bedrock Support Design

**Date:** 2026-03-20
**Status:** Approved

---

## Overview

Add AWS Bedrock as an alternative provider to the existing direct Anthropic API. Provider is selected via an environment variable. The Bedrock path authenticates using Amazon Bedrock API keys (bearer tokens via `AWS_BEARER_TOKEN_BEDROCK`). Everything else — rendering, REPL, single-shot, output modes — is unchanged.

---

## Repository

`~/Workspaces/rockmanjoe64/ask-claude/` (GitHub: `rockmanjoe64/ask-claude`)

---

## New Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ASK_CLAUDE_PROVIDER` | `direct` | Provider to use: `direct` or `bedrock` |
| `ASK_CLAUDE_BEDROCK_API_KEY` | *(required when provider=bedrock)* | Bedrock API key, mapped to `AWS_BEARER_TOKEN_BEDROCK` at runtime |
| `ASK_CLAUDE_AWS_REGION` | *(see resolution order)* | AWS region for Bedrock requests |

### Region Resolution Order

1. `ASK_CLAUDE_AWS_REGION`
2. `AWS_REGION`
3. `AWS_DEFAULT_REGION`
4. `us-west-2` (hardcoded default)

### Model Default by Provider

`ASK_CLAUDE_MODEL` is shared across both providers. The default value changes based on the active provider:

| Provider | Default model |
|---|---|
| `direct` | `claude-sonnet-4-6` |
| `bedrock` | `us.anthropic.claude-sonnet-4-6` |

---

## Changes

### `ask-claude.py`

**PEP 723 dependencies:** Change `anthropic` to `anthropic[bedrock]` to pull in `boto3`, which is required for Bedrock credential resolution.

**`load_config()`:**
- Read `ASK_CLAUDE_PROVIDER` (default `direct`); exit with error if value is not `direct` or `bedrock`
- When provider is `direct`: require `ASK_CLAUDE_API_KEY` (existing behavior)
- When provider is `bedrock`: require `ASK_CLAUDE_BEDROCK_API_KEY`; resolve region using the priority order above
- Model default is provider-specific (see table above)
- Store `provider`, `bedrock_api_key`, and `aws_region` in the returned config dict

**New `build_client(config)` function:**
- When `config["provider"] == "direct"`: return `anthropic.Anthropic(api_key=config["api_key"])`
- When `config["provider"] == "bedrock"`: set `os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config["bedrock_api_key"]`, then return `anthropic.AnthropicBedrock(aws_region=config["aws_region"])`

**`run_single_shot()` and `run_repl()`:** Call `build_client(config)` instead of constructing `anthropic.Anthropic(...)` inline.

### `install.sh`

**New provider prompt** (before API key prompts):
```
Provider [direct/bedrock] (direct):
```

**If `direct` selected:** Existing flow unchanged — prompt for `ASK_CLAUDE_API_KEY`.

**If `bedrock` selected:** Skip `ASK_CLAUDE_API_KEY` prompt; instead prompt for:
- `ASK_CLAUDE_BEDROCK_API_KEY` (masked, same `read -rs` + `echo "sk-***"` pattern)
- `ASK_CLAUDE_AWS_REGION` (optional, shows default `us-west-2`). If the user leaves this blank, write `export ASK_CLAUDE_AWS_REGION="us-west-2"` to the config file explicitly — same pattern as other optional fields with defaults.

Both paths write `ASK_CLAUDE_PROVIDER` to the config file.

---

## Data Flow

```
load_config()
    │  reads ASK_CLAUDE_PROVIDER
    │  reads provider-specific credentials
    │  resolves model default + region
    ▼
build_client(config)
    ├─ direct  ──► anthropic.Anthropic(api_key=...)
    └─ bedrock ──► os.environ["AWS_BEARER_TOKEN_BEDROCK"] = key
                   anthropic.AnthropicBedrock(aws_region=...)
    ▼
run_single_shot() / run_repl()
    │  (unchanged — same streaming/rendering logic)
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| `ASK_CLAUDE_PROVIDER` is not `direct` or `bedrock` | Exit: `Error: ASK_CLAUDE_PROVIDER must be 'direct' or 'bedrock'.` |
| `ASK_CLAUDE_PROVIDER=direct` and `ASK_CLAUDE_API_KEY` not set | Exit: `Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.` (existing) |
| `ASK_CLAUDE_PROVIDER=bedrock` and `ASK_CLAUDE_BEDROCK_API_KEY` not set | Exit: `Error: ASK_CLAUDE_BEDROCK_API_KEY is not set. Run install.sh or set it manually.` |
| Bedrock auth failure (invalid/expired key) | Existing API error handler catches and exits with message |

---

## Out of Scope

- AWS SigV4 / IAM credential chain support (Bedrock API keys only)
- `ASK_CLAUDE_BEDROCK_MODEL` separate from `ASK_CLAUDE_MODEL`
- Model ID auto-translation between providers
- Bedrock-specific features (agents, data automation, bidirectional streaming)
