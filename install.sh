#!/bin/bash
# Install Claude Code /compress command
# Usage: curl -sSL https://raw.githubusercontent.com/unclecode/claude-compress/main/install.sh | bash

set -e

REPO_URL="https://raw.githubusercontent.com/unclecode/claude-compress/main"
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
COMMANDS_DIR="$CLAUDE_DIR/commands"

echo "Installing Claude Code /compress command..."

# Create directories
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$COMMANDS_DIR"

# Download files
echo "Downloading compress_chat.py..."
curl -sSL "$REPO_URL/compress_chat.py" -o "$SCRIPTS_DIR/compress_chat.py"
chmod +x "$SCRIPTS_DIR/compress_chat.py"

echo "Downloading compress.md..."
curl -sSL "$REPO_URL/compress.md" -o "$COMMANDS_DIR/compress.md"

echo ""
echo "Installation complete!"
echo ""
echo "Files installed:"
echo "  $SCRIPTS_DIR/compress_chat.py"
echo "  $COMMANDS_DIR/compress.md"
echo ""
echo "Requirements:"
echo "  - ANTHROPIC_API_KEY environment variable must be set"
echo ""
echo "Usage:"
echo "  In Claude Code, type: /compress"
echo ""
