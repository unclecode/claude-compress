Compress the current chat session to preserve key information while reducing size.

Run the compression script (no external dependencies, uses built-in urllib):

```bash
python3 ~/.claude/scripts/compress_chat.py --cwd "$(pwd)" --target 30 --min-length 1000 --min-output 500
```

After running, report:
- Original session size
- Compressed output size and location
- Compression ratio achieved
