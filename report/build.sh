#!/bin/bash
# Xuất báo cáo ra Word: report/build/bao-cao.docx.
#   1. ghép các file theo thứ tự của mẫu, thay mỗi dòng <!-- include: X --> bằng nội dung file X;
#   2. vẽ các sơ đồ Mermaid thành PNG (minlag/mermaid-cli);
#   3. chuyển sang .docx (pandoc/core).
# Cả hai công cụ chạy trong Docker, không cài gì lên máy.
set -euo pipefail
cd "$(dirname "$0")"

MERMAID=minlag/mermaid-cli:11.12.0
PANDOC=pandoc/core:3.8
PARTS=(00-bia.md 01-khao-sat.md 02-phan-tich-thiet-ke.md 03-xay-dung.md 04-kiem-thu.md)

rm -rf build && mkdir -p build
for part in "${PARTS[@]}"; do
  awk '
    /^<!-- include: .* -->$/ {
      file = $0; sub(/^<!-- include: /, "", file); sub(/ -->$/, "", file)
      while ((getline line < file) > 0) print line
      close(file); next
    }
    { print }
  ' "$part"
  printf '\n\n'
done > build/bao-cao.md

user=(-u "$(id -u):$(id -g)")
docker run --rm "${user[@]}" -v "$PWD/build:/data" "$MERMAID" \
  -i bao-cao.md -o bao-cao.rendered.md -e png -b white -s 2 >/dev/null

reference=()
[ -f reference.docx ] && cp reference.docx build/ && reference=(--reference-doc=reference.docx)
docker run --rm "${user[@]}" -v "$PWD/build:/data" "$PANDOC" \
  bao-cao.rendered.md -o bao-cao.docx --toc --toc-depth=3 --resource-path=. ${reference[@]+"${reference[@]}"}

echo "report/build/bao-cao.docx"
