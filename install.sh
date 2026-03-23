#!/usr/bin/env sh
set -e

REPO_URL="https://github.com/rockmanjoe64/ask-claude.git"
INSTALL_DIR="$HOME/.local/share/askclaude"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/askclaude"
CONFIG_FILE="$CONFIG_DIR/config"

# --- helpers ---
info()  { printf '\033[0;34m[askclaude]\033[0m %s\n' "$1"; }
ok()    { printf '\033[0;32m[askclaude]\033[0m %s\n' "$1"; }
err()   { printf '\033[0;31m[askclaude]\033[0m %s\n' "$1" >&2; exit 1; }

# --- summary ---
echo ""
echo "askclaude installer"
echo "===================="
echo "This script will:"
echo "  1. Check prerequisites (uv, curl, git)"
echo "  2. Remove any previous ask-claude installation"
echo "  3. Clone/update the repo to $INSTALL_DIR"
echo "  4. Run interactive configuration via setup.py"
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

# --- clean up old ask-claude installation ---
OLD_INSTALL="$HOME/.local/share/ask-claude"
OLD_CONFIG="$HOME/.config/ask-claude"
if [ -d "$OLD_INSTALL" ]; then
  info "Removing old ask-claude installation at $OLD_INSTALL..."
  rm -rf "$OLD_INSTALL"
fi
if [ -d "$OLD_CONFIG" ]; then
  info "Removing old ask-claude config at $OLD_CONFIG..."
  rm -rf "$OLD_CONFIG"
fi
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.config/fish/config.fish"; do
  if [ -f "$rc" ] && grep -q "ask-claude" "$rc" 2>/dev/null; then
    sed -i '/ask-claude/d' "$rc"
    info "Removed old ask-claude entries from $rc"
  fi
done

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

# --- interactive config via setup.py ---
echo ""
uv run "$INSTALL_DIR/setup.py" --config-file "$CONFIG_FILE" --install-dir "$INSTALL_DIR"

# --- make executable + remove stale bin entry ---
chmod +x "$INSTALL_DIR/askclaude"
if [ -f "$BIN_DIR/askclaude" ] || [ -L "$BIN_DIR/askclaude" ]; then
  rm -f "$BIN_DIR/askclaude"
  info "Removed stale $BIN_DIR/askclaude"
fi
ok "askclaude is ready at $INSTALL_DIR/askclaude"

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
  echo "# askclaude" >> "$RC_FILE"
  echo "$SOURCE_LINE" >> "$RC_FILE"
  ok "Added source line to $RC_FILE"
fi

# --- done ---
echo ""
ok "Installation complete!"
echo ""
printf '\033[0;33m  ACTION REQUIRED — activate askclaude in this shell:\033[0m\n'
printf '\033[0;33m  source %s\033[0m\n' "$CONFIG_FILE"
echo ""
echo "  (New shells will activate automatically via your rc file.)"
echo ""
echo "  Usage:"
echo "    askclaude \"explain closures\"    # single-shot"
echo "    askclaude                        # interactive REPL"
echo "    askclaude -m plain \"hello\"      # override output mode"
echo ""
