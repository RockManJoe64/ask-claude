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
prompt(){ printf '%s' "$1"; read -r REPLY < /dev/tty; echo "$REPLY"; }

# --- summary ---
echo ""
echo "ask-claude installer"
echo "===================="
echo "This script will:"
echo "  1. Check prerequisites (uv, curl, git)"
echo "  2. Clone/update the repo to $INSTALL_DIR"
echo "  3. Prompt for your Anthropic API key and preferences"
echo "  4. Write $CONFIG_FILE"
echo "  5. Add $INSTALL_DIR to PATH"
echo "  6. Add 'source $CONFIG_FILE' to your shell rc file"
echo ""
printf 'Continue? [y/N] '
read -r CONFIRM < /dev/tty
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
mkdir -p "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Existing install found. Pulling latest changes..."
  git -C "$INSTALL_DIR" fetch origin
  git -C "$INSTALL_DIR" checkout main
  git -C "$INSTALL_DIR" pull --ff-only origin main
else
  info "Cloning repository..."
  git clone --branch main "$REPO_URL" "$INSTALL_DIR"
fi

# --- config prompts ---
echo ""
info "Configuration"

printf 'Anthropic API key (required): '
read -rs API_KEY < /dev/tty
echo "sk-***"
[ -z "$API_KEY" ] && err "API key is required."

printf 'Model [claude-sonnet-4-6]: '
read -r MODEL < /dev/tty
MODEL="${MODEL:-claude-sonnet-4-6}"

printf 'System prompt (optional, press Enter to skip): '
read -r SYSTEM < /dev/tty

printf 'Output mode — plain/stream/stream+markdown [stream+markdown]: '
read -r OUTPUT < /dev/tty
OUTPUT="${OUTPUT:-stream+markdown}"

# --- write config ---
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
# ask-claude configuration
# Edit this file to change defaults. Re-run install.sh to reconfigure.
export ASK_CLAUDE_API_KEY="$API_KEY"
export ASK_CLAUDE_MODEL="$MODEL"
export ASK_CLAUDE_OUTPUT="$OUTPUT"
export PATH="$INSTALL_DIR:\$PATH"
EOF
if [ -n "$SYSTEM" ]; then
  echo "export ASK_CLAUDE_SYSTEM=\"$SYSTEM\"" >> "$CONFIG_FILE"
fi
ok "Config written to $CONFIG_FILE"

# --- make executable + remove stale bin entry ---
chmod +x "$INSTALL_DIR/ask-claude"
if [ -f "$BIN_DIR/ask-claude" ] || [ -L "$BIN_DIR/ask-claude" ]; then
  rm -f "$BIN_DIR/ask-claude"
  info "Removed stale $BIN_DIR/ask-claude"
fi
ok "ask-claude is ready at $INSTALL_DIR/ask-claude"

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
