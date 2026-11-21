#!/bin/bash
# Stop.
# Do not let a turn end while code changed since HEAD fails its checks:
#   backend/    pyright and the tier 1 and 2 tests of each changed module.
#               A change in backend/common/ (or the shared conftest.py) affects every
#               service, so it runs every module's tests.
#   frontend/   tsc --noEmit and the Vitest tests.
# Exit 2 blocks the stop; stderr goes back to Claude.
input=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

active=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    print(bool(json.load(sys.stdin).get("stop_hook_active", False)))
except Exception:
    print(False)
')
[ "$active" = "True" ] && exit 0

MODULES="common order-service inventory-service kitchen-service query-service"
running() {
  [ -n "$(docker compose -f "$ROOT/infra/compose.yaml" --profile dev ps -q --status running "$1" 2>/dev/null)" ]
}
fail=""

# ---------- frontend/ ----------
if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=all -- frontend 2>/dev/null)" ]; then
  if ! running frontend-dev; then
    fail="Files changed in frontend/, but the frontend-dev container is not running, so tsc and Vitest were not run. Start it with ./bin/frontend true and run them, or tell the user they were not run."
  else
    if ! out=$("$ROOT/bin/frontend" npx --no-install tsc --noEmit 2>&1); then
      fail="tsc reports errors in frontend/
$(printf '%s\n' "$out" | tail -n 40)"
    fi
    if ! out=$("$ROOT/bin/frontend" npx --no-install vitest run 2>&1); then
      fail="$fail
Vitest fails in frontend/
$(printf '%s\n' "$out" | tail -n 60)"
    fi
  fi
fi

# ---------- backend/ ----------
# Second path component of each changed .py file under backend/: a module, scripts or conftest.py.
changed=$(git -C "$ROOT" status --porcelain --untracked-files=all -- 'backend/*.py' 2>/dev/null \
  | sed -E 's/^.{3}//; s/.* -> //' | cut -d/ -f2 | sort -u)

check_dirs=""
test_dirs=""
for top in $changed; do
  case " $MODULES scripts conftest.py " in
    *" $top "*) check_dirs="$check_dirs $top" ;;
  esac
done
for top in $check_dirs; do
  if [ "$top" = "common" ] || [ "$top" = "conftest.py" ]; then
    test_dirs="$MODULES"
    break
  fi
  case " $MODULES " in
    *" $top "*) test_dirs="$test_dirs $top" ;;
  esac
done

if [ -n "$check_dirs" ] && ! running backend-dev; then
  fail="$fail
Python files changed in backend/:$check_dirs, but the backend-dev container is not running, so the type check and the tests were not run. Start it with ./bin/backend true and run them, or tell the user they were not run."
  check_dirs=""
  test_dirs=""
fi

# shellcheck disable=SC2086
if [ -n "$check_dirs" ] && ! out=$("$ROOT/bin/backend" uv run --no-sync pyright $check_dirs 2>&1); then
  fail="$fail
pyright reports errors in backend/:$check_dirs
$(printf '%s\n' "$out" | tail -n 40)"
fi
if [ -n "$test_dirs" ]; then
  targets=""
  for m in $test_dirs; do
    [ -d "$ROOT/backend/$m/tests" ] && targets="$targets $m/tests"
  done
  # shellcheck disable=SC2086
  if [ -n "$targets" ] && ! out=$("$ROOT/bin/backend" uv run --no-sync pytest -m "not tier3" -q -p no:cacheprovider $targets 2>&1); then
    fail="$fail
Tier 1 and 2 tests fail in backend/:$targets
$(printf '%s\n' "$out" | tail -n 60)"
  fi
fi

if [ -n "$fail" ]; then
  {
    echo "The changed code does not pass its checks. Fix it before ending the turn; if a failure needs the user's decision, say so in your reply."
    printf '%s\n' "$fail"
  } >&2
  exit 2
fi
exit 0
