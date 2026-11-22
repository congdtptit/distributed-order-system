#!/bin/bash
# Xuất báo cáo ra Word: report/build/bao-cao.docx.
#   1. ghép các file theo thứ tự của mẫu, thay mỗi dòng <!-- include: X --> bằng nội dung file X;
#   2. vẽ từng sơ đồ Mermaid thành PNG (minlag/mermaid-cli), mỗi sơ đồ một lần chạy;
#   3. chuyển sang .docx (pandoc/core).
# Cả hai công cụ chạy trong Docker, không cài gì lên máy.
set -euo pipefail
cd "$(dirname "$0")"

MERMAID=minlag/mermaid-cli:11.12.0
PANDOC=pandoc/core:3.8
PARTS=(00-bia.md 01-khao-sat.md 02-phan-tich-thiet-ke.md 03-xay-dung.md 04-kiem-thu.md)

user=(-u "$(id -u):$(id -g)")
# Diagrams kept as their own files (diagrams/*.mmd) are drawn one at a time into images/, so
# that the Markdown shows them too: the ELK layout of the HLD hangs when drawn together with
# every other diagram of the report.
for diagram in diagrams/*.mmd; do
  name=$(basename "$diagram" .mmd)
  docker run --rm "${user[@]}" -v "$PWD:/data" "$MERMAID" \
    -i "diagrams/$name.mmd" -o "images/$name.png" -b white -s 2 >/dev/null
done

rm -rf build && mkdir -p build
cp -r images build/   # the screenshots of Part III and the diagrams drawn above
cp fit-images.lua build/
# Join the parts; replace each <!-- include: X --> by file X, and each Mermaid block by an image
# of it, writing the block to build/diagram-<n>.mmd.
for part in "${PARTS[@]}"; do
  cat "$part"
  printf '\n\n'
done | awk '
  /^<!-- include: .* -->$/ {
    file = $0; sub(/^<!-- include: /, "", file); sub(/ -->$/, "", file)
    while ((getline line < file) > 0) print line
    close(file); next
  }
  { print }
' | awk '
  /^```mermaid$/ { n++; out = sprintf("build/diagram-%d.mmd", n); inside = 1; next }
  inside && /^```$/ { close(out); printf "![](diagram-%d.png)\n", n; inside = 0; next }
  inside { print > out; next }
  { print }
' > build/bao-cao.md

# One mermaid-cli run per diagram: drawing them all in one browser page now and then hangs.
for diagram in build/diagram-*.mmd; do
  name=$(basename "$diagram" .mmd)
  for attempt in 1 2; do
    if docker run --rm "${user[@]}" -v "$PWD/build:/data" "$MERMAID" \
      -i "$name.mmd" -o "$name.png" -b white -s 2 >/dev/null 2>&1; then
      break
    fi
    [ "$attempt" = 2 ] && { echo "could not draw $diagram" >&2; exit 1; }
  done
done

reference=()
[ -f reference.docx ] && cp reference.docx build/ && reference=(--reference-doc=reference.docx)
docker run --rm "${user[@]}" -v "$PWD/build:/data" "$PANDOC" \
  bao-cao.md -o bao-cao.docx --toc --toc-depth=3 --resource-path=. --lua-filter=fit-images.lua \
  ${reference[@]+"${reference[@]}"}

echo "report/build/bao-cao.docx"
