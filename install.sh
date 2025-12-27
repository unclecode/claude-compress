#!/bin/bash
# Install Claude Code /compress command and CLI
# Usage: curl -sSL https://raw.githubusercontent.com/unclecode/claude-compress/main/install.sh | bash

set -e

REPO_URL="https://raw.githubusercontent.com/unclecode/claude-compress/main"
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
COMMANDS_DIR="$CLAUDE_DIR/commands"
BIN_DIR="$CLAUDE_DIR/bin"

echo "Installing Claude Code /compress command and CLI..."

# Create directories
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$COMMANDS_DIR"
mkdir -p "$BIN_DIR"

# Download files
echo "Downloading compress_chat.py..."
curl -sSL "$REPO_URL/compress_chat.py" -o "$SCRIPTS_DIR/compress_chat.py"
chmod +x "$SCRIPTS_DIR/compress_chat.py"

echo "Downloading compress.md..."
curl -sSL "$REPO_URL/compress.md" -o "$COMMANDS_DIR/compress.md"

echo "Downloading compress CLI..."
curl -sSL "$REPO_URL/compress" -o "$BIN_DIR/compress"
chmod +x "$BIN_DIR/compress"

# Add to PATH if not already there
add_to_path() {
    local rc_file="$1"
    local path_line="export PATH=\"\$HOME/.claude/bin:\$PATH\""

    if [ -f "$rc_file" ]; then
        if ! grep -q ".claude/bin" "$rc_file" 2>/dev/null; then
            echo "" >> "$rc_file"
            echo "# Claude Code CLI tools" >> "$rc_file"
            echo "$path_line" >> "$rc_file"
            echo "Added to PATH in $rc_file"
            return 0
        else
            echo "PATH already configured in $rc_file"
            return 1
        fi
    fi
    return 1
}

# Detect shell and update appropriate rc file
PATH_ADDED=false
if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ] || [ -f "$HOME/.zshrc" ]; then
    if add_to_path "$HOME/.zshrc"; then
        PATH_ADDED=true
    fi
fi

if [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ] || [ -f "$HOME/.bashrc" ]; then
    if add_to_path "$HOME/.bashrc"; then
        PATH_ADDED=true
    fi
fi

# Also try .profile for other shells
if [ "$PATH_ADDED" = false ] && [ -f "$HOME/.profile" ]; then
    add_to_path "$HOME/.profile"
fi

echo ""
echo "============================================"
echo "Installation complete!"
echo "============================================"
echo ""
echo "Files installed:"
echo "  $SCRIPTS_DIR/compress_chat.py"
echo "  $COMMANDS_DIR/compress.md"
echo "  $BIN_DIR/compress"
echo ""
echo "Requirements:"
echo "  - ANTHROPIC_API_KEY environment variable must be set"
echo ""
echo "Usage:"
echo ""
echo "  In Claude Code:"
echo "    /compress"
echo "    /compress 50% focus on API calls"
echo ""
echo "  From terminal:"
echo "    compress"
echo "    compress --target 50 --focus \"keep API calls\""
echo "    compress --help"
echo ""
if [ "$PATH_ADDED" = true ]; then
    echo "NOTE: Restart your terminal or run 'source ~/.zshrc' (or ~/.bashrc)"
    echo "      for the 'compress' command to be available."
fi
echo ""
