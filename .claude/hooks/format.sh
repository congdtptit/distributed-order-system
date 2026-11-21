#!/bin/bash
# PostToolUse (Edit|Write|MultiEdit).
# Formats a file right after Claude edits it:
#   backend/**/*.py                    ruff format, in backend-dev (bin/backend)
#   frontend/**/*.ts|tsx|js|json|css   Biome, in frontend-dev (bin/frontend)
# The edit has already happened, so this hook never blocks; exit 2 only
# passes a message back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

rel=$(printf '%s' "$input" | python3 -c '
import json, os, sys
root = os.path.realpath(sys.argv[1])
try:
    name = json.load(sys.stdin).get("tool_input", {}).get("file_path") or ""
except Exception:
    name = ""
target = os.path.realpath(os.path.join(root, name)) if name else ""
if target.startswith(root + os.sep):
    print(os.path.relpath(target, root))
' "$ROOT")
[ -n "$rel" ] || exit 0

case "$rel" in
  frontend/node_modules/*|frontend/src/api/generated/*) exit 0 ;;
  frontend/*.ts|frontend/*.tsx|frontend/*.js|frontend/*.json|frontend/*.css)
    service=frontend-dev; runner="$ROOT/bin/frontend"; cmd="npx --no-install biome format --write ${rel#frontend/}" ;;
  backend/*.py)
    service=backend-dev; runner="$ROOT/bin/backend"; cmd="uv run --no-sync ruff format --quiet ${rel#backend/}" ;;
  *) exit 0 ;;
esac

if [ -z "$(docker compose -f "$ROOT/infra/compose.yaml" --profile dev ps -q --status running "$service" 2>/dev/null)" ]; then
  echo "$rel was not formatted: the $service container is not running. Start it with $(basename "$runner") true (in bin/), then run: ${runner#"$ROOT"/} $cmd" >&2
  exit 2
fi

# shellcheck disable=SC2086
if ! out=$("$runner" $cmd 2>&1); then
  printf 'Formatting failed on %s:\n%s\n' "$rel" "$out" >&2
  exit 2
fi
exit 0
