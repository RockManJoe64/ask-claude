# Installer Config Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When re-running `install.sh`, preserve previously entered configuration values by detecting an existing config file, sourcing it, and using current values as prompt defaults.

**Architecture:** At the start of the config prompts section, if `~/.config/ask-claude/config` exists, source it with `. "$CONFIG_FILE"`. This loads all `ASK_CLAUDE_*` values into the installer environment. Each prompt then uses the loaded value as its shell variable default. API key prompts branch on whether a key is already stored — if yes, allow empty input to mean "keep existing".

**Tech Stack:** POSIX sh (`install.sh` only — no Python changes, no test file changes)

---

## Context for Implementers

- `install.sh` is a POSIX sh script run via `sh` (not bash). Use `. file` not `source file`.
- All `read` calls use `< /dev/tty` — required because `curl | sh` sets stdin to the pipe.
- Masked input: `read -rs VAR < /dev/tty` suppresses echo; a follow-up `echo` prints confirmation.
- The config file (`~/.config/ask-claude/config`) is a shell script of `export VAR="value"` lines — safe to source with `. "$CONFIG_FILE"`.
- There are no automated tests for `install.sh`. Verification is manual (run the script and inspect output + written config).
- Run the Python test suite after to confirm nothing was accidentally broken: `uv run --with pytest pytest tests/ -v`

---

## Task 1: Update `install.sh` to preserve existing config values on re-install

**Files:**
- Modify: `install.sh`

---

### Step 1: Read the current file

Read `install.sh` in full before making any edits.

---

### Step 2: Insert "load existing config" block

Insert this block **between** the `info "Configuration"` line and the provider prompt (i.e., after line `info "Configuration"` and before `printf 'Provider...'`):

```sh
# --- load existing config (if present) ---
if [ -f "$CONFIG_FILE" ]; then
  . "$CONFIG_FILE"
  info "Existing configuration found — press Enter to keep current values."
fi
```

---

### Step 3: Update the provider prompt

Replace:
```sh
printf 'Provider [direct/bedrock] (direct): '
read -r PROVIDER < /dev/tty
PROVIDER="${PROVIDER:-direct}"
if [ "$PROVIDER" != "direct" ] && [ "$PROVIDER" != "bedrock" ]; then
  err "Provider must be 'direct' or 'bedrock'."
fi
```

With:
```sh
CURRENT_PROVIDER="${ASK_CLAUDE_PROVIDER:-direct}"
printf "Provider [direct/bedrock] ($CURRENT_PROVIDER): "
read -r PROVIDER < /dev/tty
PROVIDER="${PROVIDER:-$CURRENT_PROVIDER}"
if [ "$PROVIDER" != "direct" ] && [ "$PROVIDER" != "bedrock" ]; then
  err "Provider must be 'direct' or 'bedrock'."
fi
```

---

### Step 4: Update the direct API key prompt

Replace:
```sh
  printf 'Anthropic API key (required): '
  read -rs API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$API_KEY" ] && err "API key is required."
  DEFAULT_MODEL="claude-sonnet-4-6"
```

With:
```sh
  if [ -n "$ASK_CLAUDE_API_KEY" ]; then
    printf 'Anthropic API key (press Enter to keep existing): '
    read -rs API_KEY < /dev/tty
    if [ -n "$API_KEY" ]; then
      echo "sk-***"
    else
      echo ""
      API_KEY="$ASK_CLAUDE_API_KEY"
    fi
  else
    printf 'Anthropic API key (required): '
    read -rs API_KEY < /dev/tty
    echo "sk-***"
    [ -z "$API_KEY" ] && err "API key is required."
  fi
  DEFAULT_MODEL="claude-sonnet-4-6"
```

---

### Step 5: Update the Bedrock API key and region prompts

Replace:
```sh
  printf 'Bedrock API key (required): '
  read -rs BEDROCK_API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$BEDROCK_API_KEY" ] && err "Bedrock API key is required."
  printf 'AWS region [us-west-2]: '
  read -r AWS_REGION < /dev/tty
  AWS_REGION="${AWS_REGION:-us-west-2}"
  DEFAULT_MODEL="anthropic.claude-sonnet-4-6"
```

With:
```sh
  if [ -n "$ASK_CLAUDE_BEDROCK_API_KEY" ]; then
    printf 'Bedrock API key (press Enter to keep existing): '
    read -rs BEDROCK_API_KEY < /dev/tty
    if [ -n "$BEDROCK_API_KEY" ]; then
      echo "sk-***"
    else
      echo ""
      BEDROCK_API_KEY="$ASK_CLAUDE_BEDROCK_API_KEY"
    fi
  else
    printf 'Bedrock API key (required): '
    read -rs BEDROCK_API_KEY < /dev/tty
    echo "sk-***"
    [ -z "$BEDROCK_API_KEY" ] && err "Bedrock API key is required."
  fi
  CURRENT_REGION="${ASK_CLAUDE_AWS_REGION:-us-west-2}"
  printf "AWS region [$CURRENT_REGION]: "
  read -r AWS_REGION < /dev/tty
  AWS_REGION="${AWS_REGION:-$CURRENT_REGION}"
  DEFAULT_MODEL="us.anthropic.claude-sonnet-4-6"
```

---

### Step 6: Update the model, system prompt, and output mode prompts

Replace:
```sh
printf "Model [$DEFAULT_MODEL]: "
read -r MODEL < /dev/tty
MODEL="${MODEL:-$DEFAULT_MODEL}"

printf 'System prompt (optional, press Enter to skip): '
read -r SYSTEM < /dev/tty

printf 'Output mode — plain/stream/stream+markdown [stream+markdown]: '
read -r OUTPUT < /dev/tty
OUTPUT="${OUTPUT:-stream+markdown}"
```

With:
```sh
CURRENT_MODEL="${ASK_CLAUDE_MODEL:-$DEFAULT_MODEL}"
printf "Model [$CURRENT_MODEL]: "
read -r MODEL < /dev/tty
MODEL="${MODEL:-$CURRENT_MODEL}"

CURRENT_SYSTEM="${ASK_CLAUDE_SYSTEM:-}"
if [ -n "$CURRENT_SYSTEM" ]; then
  printf 'System prompt (press Enter to keep existing): '
else
  printf 'System prompt (optional, press Enter to skip): '
fi
read -r SYSTEM < /dev/tty
SYSTEM="${SYSTEM:-$CURRENT_SYSTEM}"

CURRENT_OUTPUT="${ASK_CLAUDE_OUTPUT:-stream+markdown}"
printf "Output mode — plain/stream/stream+markdown [$CURRENT_OUTPUT]: "
read -r OUTPUT < /dev/tty
OUTPUT="${OUTPUT:-$CURRENT_OUTPUT}"
```

---

### Step 7: Verify the full diff looks correct

Review `install.sh` in full to confirm:
- The `. "$CONFIG_FILE"` block is in the right position (after `info "Configuration"`, before provider prompt)
- No stray variable names or missing quotes
- The `DEFAULT_MODEL` for bedrock reads `us.anthropic.claude-sonnet-4-6` (this already matches the current `install.sh` — no change needed here)

---

### Step 8: Manual verification — new install path

Run the installer and simulate a fresh install (no existing config):

```bash
# Back up existing config first
cp ~/.config/ask-claude/config ~/.config/ask-claude/config.bak

# Remove config to simulate fresh install
rm ~/.config/ask-claude/config

bash install.sh
```

Expected behavior:
- No "Existing configuration found" message
- Provider prompt shows `(direct)` default
- API key prompt says `(required)`, fails on empty input
- After completing: `cat ~/.config/ask-claude/config` shows all expected exports

Restore backup:
```bash
cp ~/.config/ask-claude/config.bak ~/.config/ask-claude/config
```

---

### Step 9: Manual verification — re-install path

Run the installer with an existing config:

```bash
bash install.sh
```

Expected behavior:
- "Existing configuration found — press Enter to keep current values." message shown
- Provider prompt shows current provider as default
- API key prompt says `(press Enter to keep existing)` — pressing Enter keeps existing key silently
- Model prompt shows current model as default
- Pressing Enter on every prompt produces an identical config to the original

Verify:
```bash
cat ~/.config/ask-claude/config
# Should match the original values
```

---

### Step 10: Run Python test suite

Confirm no Python code was accidentally affected:

```bash
uv run --with pytest pytest tests/ -v
```

Expected: all 35 tests pass.

---

### Step 11: Commit

```bash
git add install.sh
git commit -m "feat: preserve existing config values on re-install"
```
