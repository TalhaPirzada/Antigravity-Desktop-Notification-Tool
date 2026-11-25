#!/usr/bin/env bash
# macOS & Linux Installer for Antigravity Desktop Notifier
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
CLI_BIN="$DIR/bin/agy-notify"

chmod +x "$CLI_BIN"

# Ensure macOS applet launcher is executable
if [ -f "$DIR/bin/Antigravity Notifier.app/Contents/MacOS/agy-launcher" ]; then
    chmod +x "$DIR/bin/Antigravity Notifier.app/Contents/MacOS/agy-launcher"
fi

OS="$(uname -s)"
echo "=========================================================="
echo "Installing Antigravity Desktop Notifier ($OS)"
echo "=========================================================="

# Create ~/.local/bin if not exists and symlink
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
ln -sf "$CLI_BIN" "$LOCAL_BIN/agy-notify"

if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo "[INFO] Ensure '$LOCAL_BIN' is in your PATH in ~/.zshrc or ~/.bashrc:"
    echo "       export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Install hooks into Antigravity global configuration
echo ""
echo "[INFO] Registering Antigravity lifecycle hooks..."
"$CLI_BIN" install

echo ""
echo "[INFO] Running system diagnostics..."
"$CLI_BIN" doctor

echo ""
echo "[INFO] Testing notification..."
"$CLI_BIN" test complete

echo ""
echo "=========================================================="
echo "Installation complete. Antigravity lifecycle notifications"
echo "are now active."
echo "=========================================================="
