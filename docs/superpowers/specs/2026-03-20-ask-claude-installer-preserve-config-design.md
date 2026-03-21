# ask-claude: Installer Config Preservation Design

**Date:** 2026-03-20
**Status:** Approved

---

## Overview

When re-running `install.sh`, preserve previously entered configuration values by detecting an existing config file, sourcing it, and using current values as prompt defaults. Users press Enter to keep any existing value or type a new one to replace it.

---

## Repository

`~/Workspaces/rockmanjoe64/ask-claude/` (GitHub: `rockmanjoe64/ask-claude`)

---

## Behavior

### New install (no existing config)

Identical to the current behavior. All prompts show hardcoded defaults.

### Re-install (existing config found)

At the start of the config prompts section, the installer sources the existing config file:

```sh
if [ -f "$CONFIG_FILE" ]; then
  . "$CONFIG_FILE"
  info "Existing configuration found — press Enter to keep current values."
fi
```

This loads all `ASK_CLAUDE_*` values into the installer's environment. Each prompt then uses the loaded value as its default.

---

## Prompt Defaults

### Non-secret fields

Each non-secret prompt uses the loaded env var as its default, falling back to the hardcoded default if unset:

| Prompt | New install default | Re-install default |
|---|---|---|
| Provider | `direct` | `$ASK_CLAUDE_PROVIDER` (or `direct`) |
| Model | provider-specific | `$ASK_CLAUDE_MODEL` (or provider-specific) |
| AWS region | `us-west-2` | `$ASK_CLAUDE_AWS_REGION` (or `us-west-2`) |
| Output mode | `stream+markdown` | `$ASK_CLAUDE_OUTPUT` (or `stream+markdown`) |
| System prompt | *(empty)* | `$ASK_CLAUDE_SYSTEM` (or empty) |

Example: if `ASK_CLAUDE_PROVIDER=bedrock` is in the existing config, the provider prompt shows `(bedrock)` and pressing Enter keeps it.

### API key fields (masked)

API keys cannot be displayed. Behavior depends on whether a key is already stored:

**Key already stored:**
```
Anthropic API key (press Enter to keep existing):
```
- Empty input → keep existing value (no echo)
- Non-empty input → replace with new value (echo `sk-***`)

**No key stored yet:**
```
Anthropic API key (required):
```
- Empty input → error, exit
- Non-empty input → store new value (echo `sk-***`)

This applies to both `ASK_CLAUDE_API_KEY` (direct) and `ASK_CLAUDE_BEDROCK_API_KEY` (bedrock).

### System prompt special case

The system prompt is optional. On re-install with an existing system prompt:
- Pressing Enter keeps the existing value
- Typing a new value replaces it
- To clear it, the user must edit `~/.config/ask-claude/config` manually (out of scope for the installer)

---

## Provider switching

If the user changes provider during re-install (e.g., `direct` → `bedrock`), the installer prompts for the new provider's credentials. The old provider's key is not written to the new config — it is naturally dropped. No cleanup of the old key is required.

---

## Changes

Only `install.sh` is modified. No changes to `ask-claude.py`, tests, or other files.

### 1. Source existing config before prompts

Insert before the config prompts section:

```sh
# --- load existing config (if present) ---
if [ -f "$CONFIG_FILE" ]; then
  . "$CONFIG_FILE"
  info "Existing configuration found — press Enter to keep current values."
fi
```

### 2. Update provider prompt default

```sh
CURRENT_PROVIDER="${ASK_CLAUDE_PROVIDER:-direct}"
printf "Provider [direct/bedrock] ($CURRENT_PROVIDER): "
read -r PROVIDER < /dev/tty
PROVIDER="${PROVIDER:-$CURRENT_PROVIDER}"
```

### 3. Update API key prompts

**Direct provider:**
```sh
if [ -n "$ASK_CLAUDE_API_KEY" ]; then
  printf 'Anthropic API key (press Enter to keep existing): '
  read -rs API_KEY < /dev/tty
  echo ""
  API_KEY="${API_KEY:-$ASK_CLAUDE_API_KEY}"
else
  printf 'Anthropic API key (required): '
  read -rs API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$API_KEY" ] && err "API key is required."
fi
```

**Bedrock provider:**
```sh
if [ -n "$ASK_CLAUDE_BEDROCK_API_KEY" ]; then
  printf 'Bedrock API key (press Enter to keep existing): '
  read -rs BEDROCK_API_KEY < /dev/tty
  echo ""
  BEDROCK_API_KEY="${BEDROCK_API_KEY:-$ASK_CLAUDE_BEDROCK_API_KEY}"
else
  printf 'Bedrock API key (required): '
  read -rs BEDROCK_API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$BEDROCK_API_KEY" ] && err "Bedrock API key is required."
fi
```

### 4. Update region, model, system prompt, and output mode prompts

Use loaded env vars as defaults:

```sh
# Region (bedrock only)
CURRENT_REGION="${ASK_CLAUDE_AWS_REGION:-us-west-2}"
printf "AWS region [$CURRENT_REGION]: "
read -r AWS_REGION < /dev/tty
AWS_REGION="${AWS_REGION:-$CURRENT_REGION}"

# Model
CURRENT_MODEL="${ASK_CLAUDE_MODEL:-$DEFAULT_MODEL}"
printf "Model [$CURRENT_MODEL]: "
read -r MODEL < /dev/tty
MODEL="${MODEL:-$CURRENT_MODEL}"

# System prompt
CURRENT_SYSTEM="${ASK_CLAUDE_SYSTEM:-}"
if [ -n "$CURRENT_SYSTEM" ]; then
  printf "System prompt (press Enter to keep existing): "
else
  printf 'System prompt (optional, press Enter to skip): '
fi
read -r SYSTEM < /dev/tty
SYSTEM="${SYSTEM:-$CURRENT_SYSTEM}"

# Output mode
CURRENT_OUTPUT="${ASK_CLAUDE_OUTPUT:-stream+markdown}"
printf "Output mode — plain/stream/stream+markdown [$CURRENT_OUTPUT]: "
read -r OUTPUT < /dev/tty
OUTPUT="${OUTPUT:-$CURRENT_OUTPUT}"
```

---

## Out of Scope

- Clearing the system prompt via the installer (users edit the config file directly)
- Migrating config format across installer versions
- Multiple named profiles
