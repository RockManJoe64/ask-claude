# AWS Bedrock Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AWS Bedrock as an alternative provider selectable via `ASK_CLAUDE_PROVIDER=bedrock`, authenticating with a Bedrock API key stored as `ASK_CLAUDE_BEDROCK_API_KEY`.

**Architecture:** Provider selection lives in `load_config()`. A new `build_client(config)` function constructs either `anthropic.Anthropic` (direct) or `anthropic.AnthropicBedrock` (bedrock) based on `config["provider"]`. For Bedrock, `build_client` sets `AWS_BEARER_TOKEN_BEDROCK` from `config["bedrock_api_key"]` before creating the client so boto3's credential chain picks it up. Everything downstream (rendering, REPL, single-shot) is unchanged.

**Tech Stack:** Python 3.11+, `anthropic[bedrock]` (adds boto3), `rich`, `uv` (PEP 723 runner), `sh` (installer)

---

## Context for Implementers

- `ask-claude.py` is a single-file Python script run via `uv run`. It uses PEP 723 inline metadata to declare dependencies.
- All imports of `anthropic` and `rich` are **lazy** (inside functions) — this is intentional for testability. Tests mock these modules via `sys.modules` injection before calling functions.
- The test file is `tests/test_ask_claude.py`. Run tests with: `uv run --with pytest --with pytest-mock pytest tests/ -v`
- `install.sh` uses `read -r VAR < /dev/tty` for all interactive prompts (required because the script can be piped via `curl | sh`, which sets stdin to the script itself).
- The config file written by the installer is `~/.config/ask-claude/config` — a shell script with `export` statements, sourced by the shell wrapper.

---

## Task 1: Extend `load_config()` for provider and Bedrock credentials

**Files:**
- Modify: `ask-claude.py` (the `load_config` function, roughly lines 17–31)
- Modify: `tests/test_ask_claude.py` (add new tests after existing `load_config` tests)

### What changes

`load_config()` gains three new env vars:
- `ASK_CLAUDE_PROVIDER` — `"direct"` (default) or `"bedrock"`; exit with error if any other value
- `ASK_CLAUDE_BEDROCK_API_KEY` — required when provider is `bedrock`
- `ASK_CLAUDE_AWS_REGION` — optional; resolved with priority: `ASK_CLAUDE_AWS_REGION` → `AWS_REGION` → `AWS_DEFAULT_REGION` → `"us-west-2"`

Model default is now provider-specific:
- `direct` → `"claude-sonnet-4-6"`
- `bedrock` → `"us.anthropic.claude-sonnet-4-6"`

The returned config dict gains three new keys: `provider`, `bedrock_api_key`, `aws_region`.

---

- [ ] **Step 1: Write failing tests for provider config**

Add these tests to `tests/test_ask_claude.py` after the existing `test_load_config_custom_values` test:

```python
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
    assert config["model"] == "us.anthropic.claude-sonnet-4-6"


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run --with pytest pytest tests/test_ask_claude.py::test_load_config_provider_defaults_to_direct tests/test_ask_claude.py::test_load_config_invalid_provider_exits tests/test_ask_claude.py::test_load_config_bedrock_reads_bedrock_api_key tests/test_ask_claude.py::test_load_config_bedrock_missing_key_exits tests/test_ask_claude.py::test_load_config_direct_default_model tests/test_ask_claude.py::test_load_config_bedrock_default_model tests/test_ask_claude.py::test_load_config_region_ask_claude_aws_region_wins tests/test_ask_claude.py::test_load_config_region_falls_back_to_aws_region tests/test_ask_claude.py::test_load_config_region_falls_back_to_aws_default_region tests/test_ask_claude.py::test_load_config_region_defaults_to_us_west_2 -v
```

Expected: all FAIL (functions don't support these yet)

- [ ] **Step 3: Implement the updated `load_config()`**

Replace the entire `load_config` function in `ask-claude.py` with:

```python
def load_config() -> dict:
    provider = os.environ.get("ASK_CLAUDE_PROVIDER", "direct")
    if provider not in ("direct", "bedrock"):
        print(
            "Error: ASK_CLAUDE_PROVIDER must be 'direct' or 'bedrock'.",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = None
    bedrock_api_key = None

    if provider == "direct":
        api_key = os.environ.get("ASK_CLAUDE_API_KEY")
        if not api_key:
            print(
                "Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        bedrock_api_key = os.environ.get("ASK_CLAUDE_BEDROCK_API_KEY")
        if not bedrock_api_key:
            print(
                "Error: ASK_CLAUDE_BEDROCK_API_KEY is not set. Run install.sh or set it manually.",
                file=sys.stderr,
            )
            sys.exit(1)

    default_model = (
        "claude-sonnet-4-6" if provider == "direct" else "anthropic.claude-sonnet-4-6"
    )
    aws_region = (
        os.environ.get("ASK_CLAUDE_AWS_REGION")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-west-2"
    )

    return {
        "provider": provider,
        "api_key": api_key,
        "bedrock_api_key": bedrock_api_key,
        "model": os.environ.get("ASK_CLAUDE_MODEL", default_model),
        "system": os.environ.get("ASK_CLAUDE_SYSTEM") or None,
        "max_tokens": int(os.environ.get("ASK_CLAUDE_MAX_TOKENS", "8096")),
        "output": os.environ.get("ASK_CLAUDE_OUTPUT", "stream+markdown"),
        "aws_region": aws_region,
    }
```

- [ ] **Step 4: Run all tests to verify new tests pass and existing tests still pass**

```bash
uv run --with pytest pytest tests/ -v
```

Expected: all PASS (the existing tests don't set `ASK_CLAUDE_PROVIDER` so they default to `direct` — existing behavior unchanged)

- [ ] **Step 5: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: extend load_config for provider and Bedrock credentials"
```

---

## Task 2: Add `build_client()` and wire into `run_single_shot` / `run_repl`

**Files:**
- Modify: `ask-claude.py` (PEP 723 header, new `build_client` function, update `run_single_shot` and `run_repl`)
- Modify: `tests/test_ask_claude.py` (new tests for `build_client`, update existing single-shot/REPL test configs)

### What changes

1. PEP 723 dep: `"anthropic"` → `"anthropic[bedrock]"` (adds boto3)
2. New `build_client(config)` function:
   - `direct`: returns `anthropic.Anthropic(api_key=config["api_key"])`
   - `bedrock`: sets `os.environ["AWS_BEARER_TOKEN_BEDROCK"]`, returns `anthropic.AnthropicBedrock(aws_region=config["aws_region"])`
3. `run_single_shot`: replace inline `import anthropic; client = anthropic.Anthropic(...)` with `import anthropic; client = build_client(config)`. The `import anthropic` stays to keep error types in scope for the `except` clause.
4. `run_repl`: replace `if client is None: import anthropic; client = anthropic.Anthropic(...)` with `import anthropic` at top of function + `if client is None: client = build_client(config)`.
5. Existing single-shot/REPL tests: add `"provider": "direct"`, `"bedrock_api_key": None`, `"aws_region": "us-west-2"` to every hardcoded `config` dict — required because `build_client` reads `config["provider"]`.

---

- [ ] **Step 1: Write failing tests for `build_client`**

Add these tests to `tests/test_ask_claude.py` after the region tests from Task 1:

```python
def test_build_client_direct_creates_anthropic_client(mod, monkeypatch):
    mock_anthropic = MagicMock()
    sys.modules["anthropic"] = mock_anthropic

    config = {
        "provider": "direct",
        "api_key": "test-key",
        "bedrock_api_key": None,
        "model": "claude-sonnet-4-6",
        "system": None,
        "max_tokens": 8096,
        "output": "plain",
        "aws_region": "us-west-2",
    }

    try:
        mod.build_client(config)
        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")
    finally:
        sys.modules.pop("anthropic", None)


def test_build_client_bedrock_creates_bedrock_client(mod, monkeypatch):
    mock_anthropic = MagicMock()
    sys.modules["anthropic"] = mock_anthropic

    config = {
        "provider": "bedrock",
        "api_key": None,
        "bedrock_api_key": "bedrock-key-123",
        "model": "anthropic.claude-sonnet-4-6",
        "system": None,
        "max_tokens": 8096,
        "output": "plain",
        "aws_region": "us-west-2",
    }

    try:
        mod.build_client(config)
        assert os.environ.get("AWS_BEARER_TOKEN_BEDROCK") == "bedrock-key-123"
        mock_anthropic.AnthropicBedrock.assert_called_once_with(aws_region="us-west-2")
    finally:
        sys.modules.pop("anthropic", None)
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
uv run --with pytest pytest tests/test_ask_claude.py::test_build_client_direct_creates_anthropic_client tests/test_ask_claude.py::test_build_client_bedrock_creates_bedrock_client -v
```

Expected: FAIL with `AttributeError: module 'ask_claude' has no attribute 'build_client'`

- [ ] **Step 3: Update PEP 723 dependency header in `ask-claude.py`**

Change line 3 from:
```python
# dependencies = ["anthropic", "rich"]
```
to:
```python
# dependencies = ["anthropic[bedrock]", "rich"]
```

- [ ] **Step 4: Add `build_client()` function to `ask-claude.py`**

Add this function after `resolve_output_mode` and before `_extract_text_events`:

```python
def build_client(config: dict):
    """Construct the appropriate Anthropic client based on provider."""
    import anthropic

    if config["provider"] == "direct":
        return anthropic.Anthropic(api_key=config["api_key"])
    else:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config["bedrock_api_key"]
        return anthropic.AnthropicBedrock(aws_region=config["aws_region"])
```

- [ ] **Step 5: Update `run_single_shot()` to use `build_client`**

Replace:
```python
def run_single_shot(prompt: str, config: dict, output_mode: str) -> None:
    import anthropic
    client = anthropic.Anthropic(api_key=config["api_key"])
```
with:
```python
def run_single_shot(prompt: str, config: dict, output_mode: str) -> None:
    import anthropic  # needed for error types in except clause
    client = build_client(config)
```

- [ ] **Step 6: Update `run_repl()` to use `build_client`**

Replace:
```python
def run_repl(config: dict, output_mode: str) -> None:
    history: list[dict] = []

    print("Claude REPL — type /exit or /quit to exit.\n")

    client = None

    while True:
        ...
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=config["api_key"])
```
with:
```python
def run_repl(config: dict, output_mode: str) -> None:
    import anthropic  # needed for error types in except clause
    history: list[dict] = []

    print("Claude REPL — type /exit or /quit to exit.\n")

    client = None

    while True:
        ...
        if client is None:
            client = build_client(config)
```

- [ ] **Step 7: Update existing test config dicts to add provider fields**

In `tests/test_ask_claude.py`, every hardcoded `config = { ... }` dict inside the single-shot and REPL tests needs three new keys. Find all occurrences and add:

```python
"provider": "direct",
"bedrock_api_key": None,
"aws_region": "us-west-2",
```

Affected tests (search for `config = {` in the file):
- `test_single_shot_calls_api_and_renders`
- `test_single_shot_passes_system_prompt`
- `test_repl_exits_on_slash_exit`
- `test_repl_exits_on_slash_quit`
- `test_repl_sends_history`
- `test_api_error_exits_cleanly`

Note: `test_api_error_exits_cleanly` also has a hardcoded `config` dict — it calls `run_single_shot` which reaches `build_client`. It must be updated too or it will fail with `KeyError: 'provider'`.

- [ ] **Step 8: Run all tests**

```bash
uv run --with pytest pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add ask-claude.py tests/test_ask_claude.py
git commit -m "feat: add build_client() for provider-based client construction"
```

---

## Task 3: Update `install.sh` for Bedrock provider flow

**Files:**
- Modify: `install.sh`

### What changes

1. The summary echo block at the top mentions provider selection.
2. New provider prompt inserted before API key prompts.
3. API key prompts are conditional: `direct` gets `ASK_CLAUDE_API_KEY`, `bedrock` gets `ASK_CLAUDE_BEDROCK_API_KEY` + `ASK_CLAUDE_AWS_REGION`.
4. The model prompt default is dynamically set from `$DEFAULT_MODEL` (provider-specific).
5. The config write block writes `ASK_CLAUDE_PROVIDER` and the appropriate key var.

This task has no automated tests — verify manually by running `bash install.sh` and checking the written config file.

---

- [ ] **Step 1: Update the summary echo block**

In `install.sh`, find the summary section:
```sh
echo "This script will:"
echo "  1. Check prerequisites (uv, curl, git)"
echo "  2. Clone/update the repo to $INSTALL_DIR"
echo "  3. Prompt for your Anthropic API key and preferences"
echo "  4. Write $CONFIG_FILE"
echo "  5. Add $INSTALL_DIR to PATH"
echo "  6. Add 'source $CONFIG_FILE' to your shell rc file"
```

Replace with:
```sh
echo "This script will:"
echo "  1. Check prerequisites (uv, curl, git)"
echo "  2. Clone/update the repo to $INSTALL_DIR"
echo "  3. Prompt for provider (direct/bedrock) and credentials"
echo "  4. Write $CONFIG_FILE"
echo "  5. Add $INSTALL_DIR to PATH"
echo "  6. Add 'source $CONFIG_FILE' to your shell rc file"
```

- [ ] **Step 2: Replace the config prompts section**

Find and replace the entire config prompts block (from `# --- config prompts ---` through the `OUTPUT` line) with:

```sh
# --- config prompts ---
echo ""
info "Configuration"

printf 'Provider [direct/bedrock] (direct): '
read -r PROVIDER < /dev/tty
PROVIDER="${PROVIDER:-direct}"
if [ "$PROVIDER" != "direct" ] && [ "$PROVIDER" != "bedrock" ]; then
  err "Provider must be 'direct' or 'bedrock'."
fi

if [ "$PROVIDER" = "direct" ]; then
  printf 'Anthropic API key (required): '
  read -rs API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$API_KEY" ] && err "API key is required."
  DEFAULT_MODEL="claude-sonnet-4-6"
else
  printf 'Bedrock API key (required): '
  read -rs BEDROCK_API_KEY < /dev/tty
  echo "sk-***"
  [ -z "$BEDROCK_API_KEY" ] && err "Bedrock API key is required."
  printf 'AWS region [us-west-2]: '
  read -r AWS_REGION < /dev/tty
  AWS_REGION="${AWS_REGION:-us-west-2}"
  DEFAULT_MODEL="us.anthropic.claude-sonnet-4-6"
fi

printf "Model [$DEFAULT_MODEL]: "
read -r MODEL < /dev/tty
MODEL="${MODEL:-$DEFAULT_MODEL}"

printf 'System prompt (optional, press Enter to skip): '
read -r SYSTEM < /dev/tty

printf 'Output mode — plain/stream/stream+markdown [stream+markdown]: '
read -r OUTPUT < /dev/tty
OUTPUT="${OUTPUT:-stream+markdown}"
```

- [ ] **Step 3: Replace the config write block**

Find and replace the config write block (from `# --- write config ---` through the `SYSTEM` conditional) with:

```sh
# --- write config ---
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
# ask-claude configuration
# Edit this file to change defaults. Re-run install.sh to reconfigure.
export ASK_CLAUDE_PROVIDER="$PROVIDER"
export ASK_CLAUDE_MODEL="$MODEL"
export ASK_CLAUDE_OUTPUT="$OUTPUT"
export PATH="$INSTALL_DIR:\$PATH"
EOF
if [ "$PROVIDER" = "direct" ]; then
  echo "export ASK_CLAUDE_API_KEY=\"$API_KEY\"" >> "$CONFIG_FILE"
else
  echo "export ASK_CLAUDE_BEDROCK_API_KEY=\"$BEDROCK_API_KEY\"" >> "$CONFIG_FILE"
  echo "export ASK_CLAUDE_AWS_REGION=\"$AWS_REGION\"" >> "$CONFIG_FILE"
fi
if [ -n "$SYSTEM" ]; then
  echo "export ASK_CLAUDE_SYSTEM=\"$SYSTEM\"" >> "$CONFIG_FILE"
fi
ok "Config written to $CONFIG_FILE"
```

- [ ] **Step 4: Verify the installer manually**

Run the installer against the local repo (not via curl) to test both provider paths:

```bash
# Test direct path
bash install.sh
# At the provider prompt, press Enter (accepts "direct")
# Enter a dummy API key, accept all other defaults
# Check the config: cat ~/.config/ask-claude/config
# Expected: ASK_CLAUDE_PROVIDER="direct", ASK_CLAUDE_API_KEY="..."

# Test bedrock path
bash install.sh
# At the provider prompt, type "bedrock"
# Enter a dummy Bedrock API key, accept region default (us-west-2)
# Check the config: cat ~/.config/ask-claude/config
# Expected: ASK_CLAUDE_PROVIDER="bedrock", ASK_CLAUDE_BEDROCK_API_KEY="...", ASK_CLAUDE_AWS_REGION="us-west-2"
```

- [ ] **Step 5: Run full test suite one more time to confirm nothing broken**

```bash
uv run --with pytest pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add install.sh
git commit -m "feat: update installer for Bedrock provider support"
```
