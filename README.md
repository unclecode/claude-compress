# Claude Code /compress Command

Compress Claude Code chat sessions to preserve key information while reducing size.

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/unclecode/claude-compress/main/install.sh | bash
```

Or with gh cli:
```bash
gh repo clone unclecode/claude-compress && cd claude-compress && ./install.sh
```

## Requirements

- `ANTHROPIC_API_KEY` environment variable set
- Python 3.8+ (uses only built-in modules, no pip dependencies)

## Usage

In any Claude Code session:
```
/compress
```

This will:
1. Detect your current chat session
2. Extract all messages
3. Compress long messages to ~30% of original size
4. Save output to current directory as `chat_compressed_<timestamp>.txt`

## Manual Installation

```bash
# Copy script
mkdir -p ~/.claude/scripts
cp compress_chat.py ~/.claude/scripts/
chmod +x ~/.claude/scripts/compress_chat.py

# Copy command
mkdir -p ~/.claude/commands
cp compress.md ~/.claude/commands/
```

## Options

Run the script directly with custom options:

```bash
python3 ~/.claude/scripts/compress_chat.py --cwd "$(pwd)" \
  --target 30 \        # Target compression % (default: 30)
  --min-length 1000 \  # Only compress lines >= this length (default: 1000)
  --min-output 500 \   # Exclude lines < this from output (default: 500)
  --batch-size 5 \     # API batch size (default: 5)
  --workers 2          # Concurrent workers (default: 2)
```

## How It Works

1. Detects current project from working directory
2. Finds most recent session in `~/.claude/projects/<project>/`
3. Extracts messages (user, assistant, tool results)
4. Compresses long messages using Claude Haiku API
5. Preserves all file paths, commands, numbers, and technical details
6. Outputs single-line compressed messages with `|` separators
