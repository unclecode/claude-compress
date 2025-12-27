Compress the current chat session to preserve key information while reducing size.

## Parsing Arguments

Parse the user's arguments to extract parameters:

1. **Percentage/Target**: Look for patterns like "50%", "use 50%", "target 50", "reduce to 40%"
   - Extract the number and pass as `--target N`
   - Default: 30

2. **Min length**: Look for "min length 1000", "minimum 500 chars"
   - Extract and pass as `--min-length N`
   - Default: 1000

3. **Focus guidelines**: Everything else that describes what to prioritize or ignore
   - Pass as `--focus "..."`

## Examples

| User types | Script gets |
|------------|-------------|
| `/compress` | `--target 30 --min-length 1000` |
| `/compress 50%` | `--target 50 --min-length 1000` |
| `/compress use 40% reduction` | `--target 40 --min-length 1000` |
| `/compress focus on API calls` | `--target 30 --focus "focus on API calls"` |
| `/compress 50% focus on code, ignore logs` | `--target 50 --focus "focus on code, ignore logs"` |
| `/compress target 25 min length 500` | `--target 25 --min-length 500` |

## Run Command

Build the command based on parsed arguments:

```bash
python3 ~/.claude/scripts/compress_chat.py --cwd "$(pwd)" --target <PARSED_TARGET> --min-length <PARSED_MIN_LENGTH> --min-output 500 <--focus "PARSED_FOCUS" if any>
```

After running, report:
- Original session size
- Compressed output size and location
- Compression ratio achieved
- Parameters used (target %, focus if any)
