#!/bin/bash
# Chrome Hopping - installer for macOS
set -e

echo ""
echo "Chrome Hopping — installer"
echo "──────────────────────────"
echo ""

# Pick the best available Python (3.10+ required for rumps)
SYSTEM_PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$candidate" &>/dev/null; then
    SYSTEM_PYTHON=$(which "$candidate")
    break
  fi
done

# Fallback: check Homebrew paths directly
if [ -z "$SYSTEM_PYTHON" ]; then
  for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.12 /usr/local/bin/python3.11; do
    if [ -f "$candidate" ]; then
      SYSTEM_PYTHON="$candidate"
      break
    fi
  done
fi

if [ -z "$SYSTEM_PYTHON" ]; then
  echo "❌  Python 3.10 or newer not found."
  echo ""
  echo "    Install it with Homebrew:"
  echo "      brew install python@3.12"
  echo ""
  echo "    Then re-run this installer."
  exit 1
fi

echo "✓  Python found: $SYSTEM_PYTHON ($($SYSTEM_PYTHON --version))"

# Set up install directory and virtualenv
INSTALL_DIR="$HOME/.chrome-hopping"
mkdir -p "$INSTALL_DIR"

echo "→  Creating virtual environment..."
"$SYSTEM_PYTHON" -m venv "$INSTALL_DIR/venv"
echo "✓  Virtual environment created"

echo "→  Installing rumps..."
"$INSTALL_DIR/venv/bin/pip" install rumps --quiet
echo "✓  rumps installed"

# The Python we'll actually run is inside the venv
VENV_PYTHON="$INSTALL_DIR/venv/bin/python"

# Copy switcher.py
cp switcher.py "$INSTALL_DIR/switcher.py"
echo "✓  App installed to $INSTALL_DIR"

# Create a launchd plist so it starts on login
PLIST_PATH="$HOME/Library/LaunchAgents/com.chrome-hopping.plist"

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.chrome-hopping</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV_PYTHON</string>
    <string>$INSTALL_DIR/switcher.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>StandardErrorPath</key>
  <string>$INSTALL_DIR/error.log</string>
  <key>StandardOutPath</key>
  <string>$INSTALL_DIR/output.log</string>
</dict>
</plist>
PLIST

echo "✓  Login item registered"

# Load it now
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "✓  App started"

echo ""
echo "────────────────────────────────────"
echo "✅  Done! Look for the ⇄ icon in your menu bar."
echo ""
echo "Grant permissions if you haven't already:"
echo "  System Settings → Privacy & Security → Accessibility → add Terminal"
echo "  System Settings → Privacy & Security → Full Disk Access → add Terminal"
echo ""
echo "To uninstall:"
echo "  launchctl unload $PLIST_PATH"
echo "  rm -rf $INSTALL_DIR ~/.chrome-hopping-custom-names.json ~/.chrome-hopping-usage.json $PLIST_PATH"
echo ""
