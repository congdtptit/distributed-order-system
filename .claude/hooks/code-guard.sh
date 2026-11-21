#!/bin/bash
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit).
# Blocks three edits that break a rule of the project:
#   1. Editing a migration file that is already committed. Applied migrations
#      are immutable; a change goes into a new numbered file.
#   2. New code that deletes rows of kitchen_orders, inventory_orders or
#      processed_events (prohibition 1 in section 9 of document 01; the
#      Inventory rules in .claude/rules/inventory.md).
#   3. New code that turns Kafka offset auto-commit on (section 13.3 of 01).
# Only .py and .sql files are checked, so the documents and this
# configuration can still quote the forbidden statements.
# Exit 2 blocks the call; the reason on stderr goes back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

printf '%s' "$input" | python3 -c '
import json, os, re, subprocess, sys

root = os.path.realpath(sys.argv[1])
try:
    t = json.load(sys.stdin).get("tool_input", {})
except Exception:
    sys.exit(0)
name = t.get("file_path") or t.get("notebook_path") or ""
if not name:
    sys.exit(0)
target = os.path.realpath(os.path.join(root, name))
if not target.startswith(root + os.sep):
    sys.exit(0)
rel = os.path.relpath(target, root)
if not rel.endswith((".py", ".sql")):
    sys.exit(0)

def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

parts = rel.split(os.sep)
if rel.endswith(".sql") and "migrations" in parts[:-1]:
    committed = subprocess.run(
        ["git", "-C", root, "cat-file", "-e", "HEAD:" + "/".join(parts)],
        capture_output=True,
    ).returncode == 0
    if committed:
        block(f"{rel} is already committed, so treat it as applied: do not edit it. "
              "Put the change in a new migration file with the next number.")

new_text = "\n".join(
    [t.get("content") or "", t.get("new_string") or "", t.get("new_source") or ""]
    + [e.get("new_string") or "" for e in t.get("edits") or []]
)

if re.search(r"\bDELETE\s+FROM\s+(kitchen_orders|inventory_orders|processed_events)\b",
             new_text, re.I):
    block("Rows of kitchen_orders, inventory_orders and processed_events are never deleted "
          "(prohibition 1 in section 9 of docs/01-business-spec.md). "
          "A test that needs a clean state uses a fresh database instead.")

if re.search(r"""["\x27]enable\.auto\.commit["\x27]\s*[:=,]\s*(True|["\x27]true["\x27])""",
             new_text, re.I):
    block("Kafka offset auto-commit stays off: the consumer commits the offset itself, "
          "after the DB commit (section 13.3 of docs/01-business-spec.md).")
' "$ROOT"
