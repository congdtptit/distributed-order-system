#!/bin/bash
# Stop.
# Do not let a turn end while the documents in docs/ disagree with each other.
# Exit 2 blocks the stop; stderr goes back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# If a Stop hook already blocked this turn once, let it through to avoid a loop.
active=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    print(bool(json.load(sys.stdin).get("stop_hook_active", False)))
except Exception:
    print(False)
')
[ "$active" = "True" ] && exit 0

out=$(python3 "$ROOT/.claude/skills/doc-check/scripts/check_docs.py" "$ROOT" 2>&1) && exit 0

{
  echo "The documents in docs/ disagree with each other. Bring them in line before ending the turn; if a mismatch needs the user's decision, say so in your reply."
  echo "$out"
} >&2
exit 2
