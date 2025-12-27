#!/bin/bash
# Install Claude Code /ccomp command and CLI
# Usage: curl -sSL https://raw.githubusercontent.com/unclecode/claude-compress/main/install.sh | bash

set -e

REPO_URL="https://raw.githubusercontent.com/unclecode/claude-compress/main"
CLAUDE_DIR="$HOME/.claude"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
COMMANDS_DIR="$CLAUDE_DIR/commands"
BIN_DIR="$CLAUDE_DIR/bin"

echo "Installing Claude Code /ccomp command and CLI..."

# Create directories
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$COMMANDS_DIR"
mkdir -p "$BIN_DIR"

# Download files
echo "Downloading ccomp_chat.py..."
curl -sSL "$REPO_URL/ccomp_chat.py" -o "$SCRIPTS_DIR/ccomp_chat.py"
chmod +x "$SCRIPTS_DIR/ccomp_chat.py"

echo "Downloading ccomp.md..."
curl -sSL "$REPO_URL/ccomp.md" -o "$COMMANDS_DIR/ccomp.md"

echo "Downloading ccomp CLI..."
curl -sSL "$REPO_URL/ccomp" -o "$BIN_DIR/ccomp"
chmod +x "$BIN_DIR/ccomp"

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
echo "  $SCRIPTS_DIR/ccomp_chat.py"
echo "  $COMMANDS_DIR/ccomp.md"
echo "  $BIN_DIR/ccomp"
echo ""
echo "Requirements:"
echo "  - ANTHROPIC_API_KEY environment variable must be set"
echo ""
echo "Usage:"
echo ""
echo "  In Claude Code:"
echo "    /ccomp"
echo "    /ccomp 50% focus on API calls"
echo ""
echo "  From terminal:"
echo "    ccomp"
echo "    ccomp --target 50 --focus \"keep API calls\""
echo "    ccomp --help"
echo ""
if [ "$PATH_ADDED" = true ]; then
    echo "NOTE: Restart your terminal or run 'source ~/.zshrc' (or ~/.bashrc)"
    echo "      for the 'ccomp' command to be available."
fi
echo ""
