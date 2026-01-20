#!/bin/bash
# install.sh - Install email-notify plugin for Claude Code

set -e

PLUGIN_NAME="email-notify"
INSTALL_DIR="${HOME}/.claude/plugins/${PLUGIN_NAME}"
CONFIG_DIR="${HOME}/.claude-notify"

echo "=== Installing ${PLUGIN_NAME} plugin ==="

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy plugin files
echo "Copying plugin files..."
cp -r "${SCRIPT_DIR}/scripts" "$INSTALL_DIR/"
cp -r "${SCRIPT_DIR}/hooks" "$INSTALL_DIR/"
cp -r "${SCRIPT_DIR}/commands" "$INSTALL_DIR/"
cp -r "${SCRIPT_DIR}/.claude-plugin" "$INSTALL_DIR/"

# Set permissions
chmod +x "${INSTALL_DIR}/scripts/"*.sh 2>/dev/null || true
chmod +x "${INSTALL_DIR}/scripts/"*.py 2>/dev/null || true
chmod +x "${INSTALL_DIR}/hooks/scripts/"*.sh 2>/dev/null || true

echo ""
echo "=== Installation Complete ==="
echo "Plugin installed to: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo "  1. Generate Gmail App Password:"
echo "     Google Account -> Security -> 2-Step Verification -> App passwords"
echo ""
echo "  2. Configure the plugin:"
echo "     /notify-config --send your@gmail.com --auth xxxx-xxxx-xxxx-xxxx --recv notify@example.com"
echo ""
echo "  3. Enable notifications:"
echo "     /notify-on"
echo ""
echo "Note: Requires Ubuntu/Debian with sudo access for Postfix installation."
