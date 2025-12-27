Compress the current chat session to preserve key information while reducing size.

Arguments (optional): Pass focus guidelines to prioritize or ignore specific topics.

Examples:
- `/compress` - compress with default settings
- `/compress focus on API implementation, ignore debugging steps`
- `/compress keep file paths and commands, remove explanations`

Run the compression script with any provided arguments as focus guidelines:

```bash
python3 ~/.claude/scripts/compress_chat.py --cwd "$(pwd)" --target 30 --min-length 1000 --min-output 500 $( [ -n "$ARGUMENTS" ] && echo "--focus \"$ARGUMENTS\"" )
```

If arguments were provided, pass them as --focus to the script.

After running, report:
- Original session size
- Compressed output size and location
- Compression ratio achieved
- Focus guidelines applied (if any)
