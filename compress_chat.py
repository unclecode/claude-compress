#!/usr/bin/env python3
"""
Compress Claude Code chat sessions.

Detects current chat from CWD, extracts messages, compresses with Claude API,
and saves to the current project directory.

No external dependencies - uses built-in urllib for API calls.

Usage:
    python compress_chat.py --cwd /path/to/project
    python compress_chat.py --cwd "$(pwd)" --target 30 --min-length 500
"""
import argparse
import json
import os
import sys
import concurrent.futures
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ============================================================================
# SYSTEM PROMPT FOR COMPRESSION
# ============================================================================

SYSTEM_PROMPT_TEMPLATE = """You are an expert text compressor. Your task is to compress verbose text to approximately {target_pct}% of its original length while preserving ALL informational content.

<critical_constraints>
- OUTPUT MUST BE SHORTER THAN INPUT. Never exceed input length.
- If input is already concise, return it unchanged or slightly shorter.
- NEVER expand, reconstruct, complete, or add context to truncated content.
- NEVER explain what content means - just compress it.
- If you see "...[truncated]", do NOT try to complete it.
</critical_constraints>

<rules>
1. PRESERVE all data points, numbers, percentages, formulas, code snippets, URLs, names, and technical terms exactly
2. REMOVE redundant explanations, verbose introductions, repeated concepts, filler phrases
3. USE shorthand: "approximately" → "~", "percentage" → "%", "for example" → "e.g.", "that is" → "i.e."
4. COMBINE related sentences into dense compound statements
5. REPLACE verbose descriptions with concise equivalents
6. KEEP all proper nouns, repository names, file paths, API endpoints unchanged
7. OUTPUT must be a SINGLE LINE with no line breaks
8. USE "|" as section separator for readability
9. TARGET length: {target_low}%-{target_high}% of original character count
10. INFORMATION TEST: I(X|compressed) = I(X|original) - any query about the content should be answerable from compressed version
</rules>

<critical_preserve>
ALWAYS preserve these EXACTLY as they appear - never abbreviate or modify:
- File paths: /Users/..., ./src/..., etc.
- File names: paper_runner.py, config.yaml, etc.
- Code changes: function names, variable names, line numbers, diffs
- CLI commands: python ..., git ..., npm ..., bash commands
- API keys, secrets, environment variables: ANTHROPIC_API_KEY, etc.
- API endpoints: /v1/messages, {{"type": "fundingHistory"}}, etc.
- URLs: https://github.com/..., etc.
- Configuration values: port numbers, thresholds, multipliers
- Error messages and stack traces (abbreviated but key info kept)
- Git branches, commit hashes
- Package names and versions
</critical_preserve>

<compression_techniques>
- "The reason this works is because" → "Works because:"
- "You can do this by" → "Method:"
- "This is important because" → remove, keep the fact
- "Let me explain how" → remove entirely
- "In other words" → remove, keep one version
- Markdown headers → inline labels with ":"
- Bullet lists → semicolon-separated items
- Code blocks → inline with backticks
- Tables → key:value pairs
</compression_techniques>

<output_format>
Return ONLY the compressed text as a single line. No explanations, no metadata, no character counts. Just the compressed content.
</output_format>"""


# ============================================================================
# SESSION DETECTION
# ============================================================================

def get_project_folder_name(cwd: str) -> str:
    """Convert CWD to Claude project folder name format."""
    # /Users/foo/bar -> -Users-foo-bar
    return cwd.replace('/', '-')


def find_current_session(cwd: str) -> tuple[str, str]:
    """Find the current/most recent session JSONL for the given CWD.

    Returns: (session_path, session_id)
    """
    claude_projects = Path.home() / '.claude' / 'projects'
    project_folder = get_project_folder_name(cwd)
    project_path = claude_projects / project_folder

    if not project_path.exists():
        raise FileNotFoundError(f"No Claude project found for: {cwd}\nExpected: {project_path}")

    # Find all .jsonl files and get the most recently modified
    jsonl_files = list(project_path.glob('*.jsonl'))
    if not jsonl_files:
        raise FileNotFoundError(f"No session files found in: {project_path}")

    # Sort by modification time, most recent first
    jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    current_session = jsonl_files[0]
    session_id = current_session.stem

    return str(current_session), session_id


# ============================================================================
# MESSAGE EXTRACTION
# ============================================================================

def extract_messages(jsonl_path: str) -> list[str]:
    """Extract user messages, tool results, and assistant text from JSONL."""
    messages = []
    idx = 0

    with open(jsonl_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get('type')

            # Skip metadata entries
            if entry_type == 'file-history-snapshot':
                continue

            message = entry.get('message', {})
            role = message.get('role')
            content = message.get('content')

            if not content:
                continue

            # Handle user messages
            if entry_type == 'user' and role == 'user':
                if isinstance(content, str):
                    idx += 1
                    messages.append(f"{idx}, [USER] {content}")
                elif isinstance(content, list):
                    for item in content:
                        if item.get('type') == 'tool_result':
                            tool_content = item.get('content', '')
                            if isinstance(tool_content, str):
                                if len(tool_content) > 500:
                                    tool_content = tool_content[:500] + '...[truncated]'
                                idx += 1
                                messages.append(f"{idx}, [TOOL_RESULT] {tool_content}")

            # Handle assistant messages
            elif entry_type == 'assistant' and role == 'assistant':
                if isinstance(content, list):
                    for item in content:
                        item_type = item.get('type')
                        if item_type == 'text':
                            text = item.get('text', '')
                            if text:
                                idx += 1
                                messages.append(f"{idx}, [ASSISTANT] {text}")
                        elif item_type == 'tool_use':
                            tool_name = item.get('name', 'unknown')
                            tool_input = item.get('input', {})
                            if tool_name == 'Bash':
                                cmd = tool_input.get('command', '')[:100]
                                idx += 1
                                messages.append(f"{idx}, [TOOL_USE:{tool_name}] {cmd}")
                            elif tool_name == 'Read':
                                path = tool_input.get('file_path', '')
                                idx += 1
                                messages.append(f"{idx}, [TOOL_USE:{tool_name}] {path}")
                            elif tool_name == 'Edit':
                                path = tool_input.get('file_path', '')
                                idx += 1
                                messages.append(f"{idx}, [TOOL_USE:{tool_name}] {path}")
                            else:
                                idx += 1
                                messages.append(f"{idx}, [TOOL_USE:{tool_name}]")

    return messages


# ============================================================================
# COMPRESSION
# ============================================================================

def get_system_prompt(target_pct: int = 50) -> str:
    """Generate system prompt with target compression percentage."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        target_pct=target_pct,
        target_low=max(target_pct - 5, 10),
        target_high=target_pct + 5
    )


def get_api_key() -> str:
    """Get Anthropic API key from environment or Claude credentials."""
    # Try environment variable first
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        return api_key

    # Try Claude credentials file
    creds_path = Path.home() / '.claude' / '.credentials.json'
    if creds_path.exists():
        try:
            with open(creds_path) as f:
                creds = json.load(f)
                if 'claudeAiOauth' in creds:
                    # OAuth token - won't work for API, need API key
                    pass
        except:
            pass

    raise ValueError("ANTHROPIC_API_KEY not found. Set it in environment.")


def call_claude_api(system: str, user_message: str, api_key: str) -> str:
    """Call Claude API using urllib (no dependencies)."""
    url = "https://api.anthropic.com/v1/messages"

    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 4096,
        "system": system,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['content'][0]['text']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"API Error {e.code}: {error_body}")


def compress_message(api_key: str, text: str, target_pct: int = 50) -> str:
    """Compress a single message using Claude API."""
    system = get_system_prompt(target_pct)
    input_len = len(text)
    user_msg = f"""Compress this text to ~{target_pct}% of its length ({input_len} chars → ~{int(input_len * target_pct / 100)} chars).

CRITICAL: Your output MUST be shorter than {input_len} chars. Never expand or add content.

Text to compress:
{text}"""
    return call_claude_api(system, user_msg, api_key)


def compress_batch(api_key: str, lines: list[tuple[int, str]],
                   max_workers: int = 2, target_pct: int = 50) -> dict[int, str]:
    """Compress multiple lines concurrently with retry logic."""
    import time
    results = {}

    def process_line(idx_line):
        idx, line = idx_line
        for attempt in range(3):
            try:
                compressed = compress_message(api_key, line, target_pct)
                return idx, compressed, None
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return idx, line, str(e)
        return idx, line, "Max retries exceeded"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_line, (idx, line)): idx for idx, line in lines}
        for future in concurrent.futures.as_completed(futures):
            idx, result, error = future.result()
            if error:
                print(f"  Line {idx+1}: Error - {error[:100]}")
            results[idx] = result

    return results


def process_messages(messages: list[str], output_path: str, api_key: str,
                     min_length: int = 500, min_output: int = 500,
                     target_pct: int = 30, batch_size: int = 5, max_workers: int = 2):
    """Process and compress messages."""
    import time

    total_lines = len(messages)
    results = [""] * total_lines
    stats = {"total": 0, "compressed": 0, "skipped_short": 0, "skipped_keep": 0}

    # Collect lines to compress
    to_compress = []
    for i, line in enumerate(messages):
        line = line.strip()
        if not line:
            results[i] = ""
            continue

        stats["total"] += 1

        # Check for [KEEP] prefix
        content_start = line.find(", ") + 2 if ", " in line else 0
        if line[content_start:].startswith("[KEEP]"):
            results[i] = line
            stats["skipped_keep"] += 1
            print(f"Line {i+1}: [KEEP] - skipping")
            continue

        # Skip short lines
        if len(line) < min_length:
            results[i] = line
            stats["skipped_short"] += 1
            continue

        to_compress.append((i, line))

    print(f"\n=== Processing {len(to_compress)} lines (of {stats['total']} total) ===")
    print(f"Target compression: {target_pct}%")
    print(f"Skipped: {stats['skipped_short']} short, {stats['skipped_keep']} [KEEP]")
    print(f"Batch size: {batch_size}, Workers: {max_workers}\n")

    # Process in batches
    for batch_start in range(0, len(to_compress), batch_size):
        batch = to_compress[batch_start:batch_start + batch_size]
        batch_end = min(batch_start + batch_size, len(to_compress))

        print(f"Batch {batch_start//batch_size + 1}: lines {batch_start+1}-{batch_end} of {len(to_compress)}")

        compressed_batch = compress_batch(api_key, batch, max_workers, target_pct)

        if batch_end < len(to_compress):
            time.sleep(1)

        for idx, compressed in compressed_batch.items():
            original_len = len(messages[idx].strip())
            compressed_len = len(compressed)
            ratio = compressed_len / original_len * 100
            results[idx] = compressed
            stats["compressed"] += 1
            print(f"  Line {idx+1}: {original_len} → {compressed_len} chars ({ratio:.1f}%)")

    # Filter and write output (exclude lines < min_output)
    filtered_results = [line for line in results if len(line) >= min_output]
    excluded_count = len([line for line in results if line and len(line) < min_output])

    with open(output_path, 'w') as f:
        for line in filtered_results:
            # Clean newlines for single-line output
            line_clean = line.replace('\n', ' ').replace('\r', '')
            f.write(line_clean + "\n")

    # Calculate stats
    original_total = sum(len(messages[i].strip()) for i, _ in to_compress) if to_compress else 0
    compressed_total = sum(len(results[i]) for i, _ in to_compress) if to_compress else 0
    overall_ratio = compressed_total / original_total * 100 if original_total > 0 else 0
    final_size = sum(len(line) for line in filtered_results)

    return {
        "total_lines": stats["total"],
        "compressed": stats["compressed"],
        "skipped_short": stats["skipped_short"],
        "skipped_keep": stats["skipped_keep"],
        "excluded": excluded_count,
        "final_lines": len(filtered_results),
        "original_chars": original_total,
        "compressed_chars": compressed_total,
        "compression_ratio": overall_ratio,
        "final_size": final_size
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Compress Claude Code chat sessions')
    parser.add_argument('--cwd', required=True, help='Current working directory of the chat')
    parser.add_argument('--target', type=int, default=30, help='Target compression percentage (default: 30)')
    parser.add_argument('--min-length', type=int, default=500, help='Minimum line length to compress (default: 500)')
    parser.add_argument('--min-output', type=int, default=500, help='Minimum line length in output (default: 500)')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for API calls (default: 5)')
    parser.add_argument('--workers', type=int, default=2, help='Concurrent workers (default: 2)')

    args = parser.parse_args()

    # Resolve CWD
    cwd = os.path.abspath(args.cwd)
    print(f"Project directory: {cwd}")

    # Find current session
    try:
        session_path, session_id = find_current_session(cwd)
        print(f"Session found: {session_id}")
        print(f"Session path: {session_path}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Get session file stats
    session_size = os.path.getsize(session_path)
    print(f"Session size: {session_size / 1024:.1f} KB")

    # Get API key
    try:
        api_key = get_api_key()
        print("API key found")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Extract messages
    print("\nExtracting messages...")
    messages = extract_messages(session_path)
    print(f"Extracted {len(messages)} messages")

    # Output path in the project directory (CWD)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"chat_compressed_{timestamp}.txt"
    output_path = os.path.join(cwd, output_filename)

    # Compress
    print(f"\nCompressing to {args.target}%...")
    stats = process_messages(
        messages=messages,
        output_path=output_path,
        api_key=api_key,
        min_length=args.min_length,
        min_output=args.min_output,
        target_pct=args.target,
        batch_size=args.batch_size,
        max_workers=args.workers
    )

    # Report
    print(f"\n{'='*60}")
    print("COMPRESSION COMPLETE")
    print(f"{'='*60}")
    print(f"Original session: {session_size / 1024:.1f} KB")
    print(f"Extracted lines: {stats['total_lines']}")
    print(f"Compressed: {stats['compressed']} lines")
    print(f"Final output: {stats['final_lines']} lines, {stats['final_size'] / 1024:.1f} KB")
    print(f"Compression ratio: {stats['compression_ratio']:.1f}%")
    print(f"\nOutput saved to: {output_path}")


if __name__ == '__main__':
    main()
