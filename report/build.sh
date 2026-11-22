#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$DIR/build"
mkdir -p "$BUILD/images"

cat \
  "$DIR/00-bia.md" \
  <(printf '\n\n') \
  "$DIR/01-khao-sat.md" \
  <(printf '\n\n') \
  "$DIR/02-phan-tich-thiet-ke.md" \
  <(printf '\n\n') \
  "$DIR/03-xay-dung.md" \
  <(printf '\n\n') \
  "$DIR/04-kiem-thu.md" \
  > "$BUILD/bao-cao.raw.md"

awk -v dir="$DIR" '/<!-- *include: *([^ ]+) *-->/ {
  match($0, /<!-- *include: *([^ ]+) *-->/, m);
  f = dir "/" m[1];
  while ((getline line < f) > 0) print line;
  close(f);
  next
} { print }' "$BUILD/bao-cao.raw.md" > "$BUILD/bao-cao.md"
rm -f "$BUILD/bao-cao.raw.md"

rm -f "$BUILD/images/"*.png
cp "$DIR/images/"*.png "$BUILD/images/"
cp "$DIR/fit-images.lua" "$DIR/ptit-layout.lua" "$DIR/reference.docx" "$BUILD/"

MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$BUILD:/work" \
  -w /work \
  pandoc/core:3.8 \
  bao-cao.md \
  --from=markdown+pipe_tables+table_captions+raw_html+fenced_code_blocks+backtick_code_blocks \
  --to=docx \
  --lua-filter=fit-images.lua \
  --lua-filter=ptit-layout.lua \
  --reference-doc=reference.docx \
  -o bao-cao.docx

if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$DIR/scripts/polish_docx.ps1" -DocxPath "$BUILD/bao-cao.docx" -AssetsDir "$DIR/assets"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$DIR/scripts/update_toc_word.ps1" -DocxPath "$BUILD/bao-cao.docx"
fi

echo "Done -> $BUILD/bao-cao.docx"
