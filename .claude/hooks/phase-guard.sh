#!/bin/bash
# PreToolUse (Edit|Write|NotebookEdit).
# While the project is in the documentation phase, block creating or editing
# project files outside docs/, .claude/ and a few root files.
# Exit 2 blocks the call; the reason on stderr goes back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

phase=$(tr -d '[:space:]' < "$ROOT/.claude/project-phase" 2>/dev/null)
[ "$phase" = "docs" ] || exit 0

file=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    t = json.load(sys.stdin).get("tool_input", {})
    print(t.get("file_path") or t.get("notebook_path") or "")
except Exception:
    print("")
')
[ -n "$file" ] || exit 0
case "$file" in
  /*) ;;
  *) file="$ROOT/$file" ;;
esac

case "$file" in
  "$ROOT"/docs/*|"$ROOT"/.claude/*|"$ROOT"/CLAUDE.md|"$ROOT"/CLAUDE.local.md|"$ROOT"/README.md|"$ROOT"/.gitignore)
    exit 0 ;;
  "$ROOT"/*)
    echo "The project is in the documentation phase (.claude/project-phase = docs): do not create or edit files outside docs/, .claude/ and CLAUDE.md yet. If the user has just said clearly that implementation starts, ask them to change the content of .claude/project-phase to code." >&2
    exit 2 ;;
  *)
    exit 0 ;;
esac
