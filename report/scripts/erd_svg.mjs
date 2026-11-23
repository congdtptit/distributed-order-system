/**
 * True Entity-Relationship Diagram (ERD) SVG generator matching PTIT / RMS style:
 * - Soft green entity boxes with bold header and PK / FK / UNI tags
 * - Purple diamond relationship nodes with labels
 * - Clean orthogonal lines and explicit 1 / N / 0..1 / M cardinality labels
 */

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function buildErdDiagram({ name, title, width = 1140, height = 700, entities, relations, notes = [] }) {
  const rowH = 19;
  const headH = 28;
  const padB = 8;

  const boxMap = new Map();
  const entitySvgs = [];

  for (const e of entities) {
    const w = e.w ?? 265;
    const h = headH + e.cols.length * rowH + padB;
    boxMap.set(e.id, { ...e, w, h, cx: e.x + w / 2, cy: e.y + h / 2 });

    const headerFill = e.infra ? "#f1f5f9" : "#dcfce7";
    const stroke = e.infra ? "#64748b" : "#15803d";
    const titleColor = e.infra ? "#1e293b" : "#14532d";

    const rows = e.cols
      .map(([colName, tag], idx) => {
        const y = e.y + headH + 14 + idx * rowH;
        const isPk = tag?.includes("PK");
        const isFk = tag?.includes("FK");
        const isUni = tag?.includes("UNI");
        const tagColor = isPk ? "#92400e" : isFk ? "#1d4ed8" : "#6d28d9";
        return `
          <text x="${e.x + 11}" y="${y}" font-size="11.5" font-family="'Consolas',monospace" font-weight="${isPk ? 700 : 500}" text-decoration="${isPk ? "underline" : "none"}" fill="#0f172a">${esc(colName)}</text>
          ${tag ? `<text x="${e.x + w - 11}" y="${y}" text-anchor="end" font-size="10.5" font-weight="700" fill="${tagColor}">${esc(tag)}</text>` : ""}
        `;
      })
      .join("");

    entitySvgs.push(`
      <g>
        <rect x="${e.x}" y="${e.y}" width="${w}" height="${h}" rx="7" fill="#ffffff" stroke="${stroke}" stroke-width="1.6"/>
        <path d="M ${e.x},${e.y + 7} Q ${e.x},${e.y} ${e.x + 7},${e.y} L ${e.x + w - 7},${e.y} Q ${e.x + w},${e.y} ${e.x + w},${e.y + 7} L ${e.x + w},${e.y + headH} L ${e.x},${e.y + headH} Z" fill="${headerFill}"/>
        <line x1="${e.x}" y1="${e.y + headH}" x2="${e.x + w}" y2="${e.y + headH}" stroke="${stroke}" stroke-width="1.3"/>
        <text x="${e.x + w / 2}" y="${e.y + 18.5}" text-anchor="middle" font-size="12.5" font-family="'Consolas',monospace" font-weight="700" fill="${titleColor}">${esc(e.id)}</text>
        ${rows}
      </g>
    `);
  }

  function sidePoint(box, side, offset = 0) {
    switch (side) {
      case "l": return { x: box.x, y: box.cy + offset };
      case "r": return { x: box.x + box.w, y: box.cy + offset };
      case "t": return { x: box.cx + offset, y: box.y };
      case "b": return { x: box.cx + offset, y: box.y + box.h };
      default: return { x: box.cx, y: box.cy };
    }
  }

  function cardOffset(p, side, dx = 0, dy = 0) {
    if (side === "r") return { x: p.x + 12 + dx, y: p.y - 6 + dy };
    if (side === "l") return { x: p.x - 14 + dx, y: p.y - 6 + dy };
    if (side === "t") return { x: p.x + 10 + dx, y: p.y - 8 + dy };
    return { x: p.x + 10 + dx, y: p.y + 15 + dy };
  }

  const relSvgs = [];
  for (const r of relations) {
    const b1 = boxMap.get(r.from);
    const b2 = boxMap.get(r.to);
    if (!b1 || !b2) throw new Error(`Missing ERD box in ${name}: ${r.from} / ${r.to}`);

    const p1 = sidePoint(b1, r.fromSide, r.fromOff ?? 0);
    const p2 = sidePoint(b2, r.toSide, r.toOff ?? 0);

    const dx = r.dx ?? (p1.x + p2.x) / 2;
    const dy = r.dy ?? (p1.y + p2.y) / 2;
    const dw = r.dw ?? 46;
    const dh = r.dh ?? 22;

    const dash = r.dashed ? `stroke-dasharray="5,4"` : "";
    const lineColor = r.dashed ? "#475569" : "#1e293b";

    // Route orthogonal path from p1 -> exact diamond vertex -> p2 (never piercing sloped sides)
    let path1;
    let path2;
    if (r.route === "hv") {
      path1 = `M ${p1.x},${p1.y} L ${dx},${p1.y} L ${dx},${dy}`;
      path2 = `M ${dx},${dy} L ${p2.x},${dy} L ${p2.x},${p2.y}`;
    } else if (r.route === "vh") {
      path1 = `M ${p1.x},${p1.y} L ${p1.x},${dy} L ${dx},${dy}`;
      path2 = `M ${dx},${dy} L ${dx},${p2.y} L ${p2.x},${p2.y}`;
    } else if (r.route === "u") {
      path1 = `M ${p1.x},${p1.y} L ${p1.x},${dy} L ${dx},${dy}`;
      path2 = `M ${dx},${dy} L ${p2.x},${dy} L ${p2.x},${p2.y}`;
    } else if ((r.fromSide === "r" && r.toSide === "l") || (r.fromSide === "l" && r.toSide === "r")) {
      const dir = r.fromSide === "r" ? 1 : -1;
      if (Math.abs(p1.y - dy) <= 1 && Math.abs(p2.y - dy) <= 1) {
        path1 = `M ${p1.x},${p1.y} L ${dx - dir * dw},${dy}`;
        path2 = `M ${dx + dir * dw},${dy} L ${p2.x},${p2.y}`;
      } else if (Math.abs(p1.y - dy) > dh + 8 && Math.abs(p2.y - dy) > dh + 8) {
        const s1 = p1.y > dy ? 1 : -1;
        const s2 = p2.y > dy ? 1 : -1;
        path1 = `M ${p1.x},${p1.y} L ${dx},${p1.y} L ${dx},${dy + s1 * dh}`;
        path2 = `M ${dx},${dy + s2 * dh} L ${dx},${p2.y} L ${p2.x},${p2.y}`;
      } else {
        const vL = dx - dir * dw;
        const vR = dx + dir * dw;
        const m1 = (p1.x + vL) / 2;
        const m2 = (vR + p2.x) / 2;
        path1 = `M ${p1.x},${p1.y} L ${m1},${p1.y} L ${m1},${dy} L ${vL},${dy}`;
        path2 = `M ${vR},${dy} L ${m2},${dy} L ${m2},${p2.y} L ${p2.x},${p2.y}`;
      }
    } else {
      path1 = `M ${p1.x},${p1.y} L ${dx},${p1.y} L ${dx},${dy}`;
      path2 = `M ${dx},${dy} L ${dx},${p2.y} L ${p2.x},${p2.y}`;
    }

    const c1 = cardOffset(p1, r.fromSide, r.c1x ?? 0, r.c1y ?? 0);
    const c2 = cardOffset(p2, r.toSide, r.c2x ?? 0, r.c2y ?? 0);

    relSvgs.push(`
      <g>
        <path d="${path1}" fill="none" stroke="${lineColor}" stroke-width="1.5" ${dash}/>
        <path d="${path2}" fill="none" stroke="${lineColor}" stroke-width="1.5" ${dash}/>
        <polygon points="${dx},${dy - dh} ${dx + dw},${dy} ${dx},${dy + dh} ${dx - dw},${dy}" fill="#f5f3ff" stroke="#6d28d9" stroke-width="1.5"/>
        <text x="${dx}" y="${dy + 4}" text-anchor="middle" font-size="11" font-weight="700" fill="#4c1d95">${esc(r.label)}</text>
        <text x="${c1.x}" y="${c1.y}" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${esc(r.cardFrom)}</text>
        <text x="${c2.x}" y="${c2.y}" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">${esc(r.cardTo)}</text>
      </g>
    `);
  }

  const noteSvg = notes
    .map(
      (n) =>
        `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h ?? 30}" rx="6" fill="#f8fafc" stroke="#cbd5e1"/>
         <text x="${n.x + 12}" y="${n.y + 19}" font-size="11.5" fill="#334155">${esc(n.text)}</text>`
    )
    .join("");

  return {
    name,
    width: width + 4,
    scale: 2,
    body: `
      <div style="border:1.5px solid #cbd5e1;border-radius:12px;background:#ffffff;overflow:hidden;">
        <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:'Segoe UI',Arial,sans-serif;">
          <text x="${width / 2}" y="28" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">${esc(title)}</text>
          ${relSvgs.join("")}
          ${entitySvgs.join("")}
          ${noteSvg}
        </svg>
      </div>
    `,
  };
}
