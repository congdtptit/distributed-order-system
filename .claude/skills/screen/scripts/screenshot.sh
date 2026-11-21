#!/bin/bash
# Take one screenshot of a route of the web module with headless Chrome on
# the host machine.
#   screenshot.sh <route> <width>x<height> <output.png> [base url]
# Example:
#   screenshot.sh /kitchen 1024x768 /tmp/kitchen-tablet.png
# The base url defaults to the Vite dev server, http://localhost:5173.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "usage: $0 <route> <width>x<height> <output.png> [base url]" >&2
  exit 2
fi
route=$1
size=$2
out=$3
base=${4:-http://localhost:5173}

case "$size" in
  [0-9]*x[0-9]*) width=${size%x*}; height=${size#*x} ;;
  *) echo "size must look like 1280x800, got: $size" >&2; exit 2 ;;
esac

chrome=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome 2>/dev/null || true)" \
  "$(command -v chromium 2>/dev/null || true)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then chrome=$c; break; fi
done
if [ -z "$chrome" ]; then
  echo "No Chrome or Chromium found on this machine." >&2
  exit 1
fi

if ! curl -fs -o /dev/null --max-time 3 "$base"; then
  echo "Nothing answers at $base. Start the system first: docker compose up -d --wait" >&2
  exit 1
fi

mkdir -p "$(dirname "$out")"
"$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size="$width,$height" --virtual-time-budget=5000 \
  --screenshot="$out" "${base%/}$route" >/dev/null 2>&1
if [ ! -s "$out" ]; then
  echo "Chrome did not write $out" >&2
  exit 1
fi
echo "$out"
