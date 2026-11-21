#!/bin/bash
# PreToolUse (Edit|Write|NotebookEdit).
# 1. In every phase, block edits to .claude/project-phase. It is the switch of
#    this guard, and only the user changes it.
# 2. While the project is in the documentation phase, block creating or editing
#    project files outside docs/, .claude/, .github/ and a few root files.
# Exit 2 blocks the call; the reason on stderr goes back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Resolve the project root and the target to real absolute paths before
# comparing them, so that ".." or a symlink cannot make a file outside the
# allowed directories look as if it were inside one. Three lines come back:
# the root, the target (empty if the call names no file), and 1 if the target
# is the phase marker.
resolved=$(printf '%s' "$input" | python3 -c '
import json, os, sys
root = os.path.realpath(sys.argv[1])
target, is_marker = "", 0
try:
    t = json.load(sys.stdin).get("tool_input", {})
    name = t.get("file_path") or t.get("notebook_path") or ""
    if name:
        target = os.path.realpath(os.path.join(root, name))
        marker = os.path.join(root, ".claude", "project-phase")
        try:
            is_marker = int(os.path.samefile(target, marker))
        except OSError:
            is_marker = int(target == marker)
except Exception:
    target, is_marker = "", 0
print(root)
print(target)
print(is_marker)
' "$ROOT")
{ IFS= read -r ROOT; IFS= read -r file; IFS= read -r is_marker; } <<< "$resolved"
[ -n "$file" ] || exit 0

if [ "$is_marker" = "1" ]; then
  echo "Only the user changes .claude/project-phase. Do not edit it, and do not change it through Bash either. If the user has said clearly that the phase changes, ask them to change the content of the file themselves." >&2
  exit 2
fi

phase=$(tr -d '[:space:]' < "$ROOT/.claude/project-phase" 2>/dev/null)
[ "$phase" = "docs" ] || exit 0

case "$file" in
  "$ROOT"/docs/*|"$ROOT"/.claude/*|"$ROOT"/.github/*|"$ROOT"/CLAUDE.md|"$ROOT"/CLAUDE.local.md|"$ROOT"/README.md|"$ROOT"/.gitignore|"$ROOT"/.gitattributes)
    exit 0 ;;
  "$ROOT"/*)
    echo "The project is in the documentation phase (.claude/project-phase = docs): do not create or edit files outside docs/, .claude/, .github/ and CLAUDE.md yet. If the user has just said clearly that implementation starts, ask them to change the content of .claude/project-phase to code." >&2
    exit 2 ;;
  *)
    exit 0 ;;
esac
