/**
 * Crisp UML Activity Diagram generator (HTML + SVG -> high-DPI PNG via render_diagrams.mjs).
 * Uses solid black start circle, rounded step boxes, amber decision nodes, red error/reject boxes,
 * green success terminal steps, and concentric bullseye UML end circle.
 */

const NODE_THEMES = {
  action: { fill: "#f8fafc", stroke: "#334155", text: "#0f172a", bold: false },
  primary: { fill: "#eff6ff", stroke: "#1d4ed8", text: "#1e3a8a", bold: true },
  decision: { fill: "#fffbeb", stroke: "#d97706", text: "#92400e", bold: true },
  success: { fill: "#ecfdf5", stroke: "#059669", text: "#065f46", bold: true },
  error: { fill: "#fef2f2", stroke: "#dc2626", text: "#991b1b", bold: true },
  warn: { fill: "#fff7ed", stroke: "#ea580c", text: "#9a3412", bold: true },
  outbox: { fill: "#f5f3ff", stroke: "#7c3aed", text: "#5b21b6", bold: true },
};

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapLines(text, maxChars) {
  const rawLines = String(text).split("\n");
  const lines = [];
  for (const raw of rawLines) {
    const words = raw.trim().split(/\s+/);
    let cur = "";
    for (const w of words) {
      if (!cur) cur = w;
      else if (cur.length + 1 + w.length <= maxChars) cur += " " + w;
      else {
        lines.push(cur);
        cur = w;
      }
    }
    if (cur) lines.push(cur);
  }
  return lines;
}

export function buildActivityDiagram({ name, title, cols = [240, 320, 240], colGap = 72, rowGap = 34, nodes, edges }) {
  const padX = 28;
  const padY = 24;
  const titleH = title ? 36 : 0;

  // Compute column center X coordinates
  const colStarts = [];
  let curX = padX;
  for (let c = 0; c < cols.length; c++) {
    colStarts.push(curX);
    curX += cols[c] + (c < cols.length - 1 ? colGap : 0);
  }
  const maxViaX = Math.max(0, ...edges.map((e) => e.viaX ?? 0));
  const totalW = Math.max(curX + padX, maxViaX ? maxViaX + padX : 0);

  // Measure every node's width & height
  const measured = new Map();
  const rowHeights = new Map();

  for (const n of nodes) {
    const colW = cols[Math.floor(n.col)] ?? 260;
    const w = n.w ?? (n.type === "start" || n.type === "end" ? 30 : Math.min(colW, n.maxW ?? colW));
    let h;
    let lines = [];
    if (n.type === "start" || n.type === "end") {
      h = 30;
    } else {
      const approxChars = Math.max(16, Math.floor((w - 24) / 6.7));
      lines = wrapLines(n.label, approxChars);
      h = Math.max(40, lines.length * 17 + 18);
    }
    const cx =
      n.col % 1 === 0
        ? colStarts[n.col] + cols[n.col] / 2
        : colStarts[Math.floor(n.col)] + (cols[Math.floor(n.col)] + colGap + cols[Math.ceil(n.col)]) / 2;

    const item = { ...n, w, h, cx, lines };
    measured.set(n.id, item);
    rowHeights.set(n.row, Math.max(rowHeights.get(n.row) ?? 0, h));
  }

  // Compute row Y coordinates
  const rowsSorted = [...rowHeights.keys()].sort((a, b) => a - b);
  const rowTops = new Map();
  let curY = padY + titleH;
  for (const r of rowsSorted) {
    rowTops.set(r, curY);
    curY += rowHeights.get(r) + rowGap;
  }
  const totalH = curY - rowGap + padY;

  for (const item of measured.values()) {
    const rh = rowHeights.get(item.row);
    const rt = rowTops.get(item.row);
    item.cy = rt + rh / 2;
    item.x = item.cx - item.w / 2;
    item.y = item.cy - item.h / 2;
  }

  function anchor(item, side) {
    switch (side) {
      case "t": return { x: item.cx, y: item.y };
      case "b": return { x: item.cx, y: item.y + item.h };
      case "l": return { x: item.x, y: item.cy };
      case "r": return { x: item.x + item.w, y: item.cy };
      default: return { x: item.cx, y: item.y + item.h };
    }
  }

  // Draw edges first
  const edgeSvgs = [];
  for (const e of edges) {
    const fromNode = measured.get(e.from);
    const toNode = measured.get(e.to);
    if (!fromNode || !toNode) throw new Error(`Missing edge node in ${name}: ${e.from} -> ${e.to}`);

    const fs = e.fromSide ?? "b";
    const ts = e.toSide ?? "t";
    const p1 = anchor(fromNode, fs);
    const p2 = anchor(toNode, ts);
    const color = e.color ?? "#475569";

    let d;
    let lx;
    let ly;
    if (e.viaX !== undefined) {
      if (Math.abs(e.viaX - p2.x) < 1) {
        d = `M ${p1.x},${p1.y} L ${e.viaX},${p1.y} L ${p2.x},${p2.y}`;
      } else {
        d = `M ${p1.x},${p1.y} L ${e.viaX},${p1.y} L ${e.viaX},${p2.y} L ${p2.x},${p2.y}`;
      }
      lx = (p1.x + e.viaX) / 2;
      ly = p1.y;
    } else if (e.viaY !== undefined) {
      d = `M ${p1.x},${p1.y} L ${p1.x},${e.viaY} L ${p2.x},${e.viaY} L ${p2.x},${p2.y}`;
      lx = (p1.x + p2.x) / 2;
      ly = e.viaY;
    } else if (Math.abs(p1.x - p2.x) < 1 && (fs === "b" || fs === "t")) {
      d = `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`;
      lx = p1.x;
      ly = (p1.y + p2.y) / 2;
    } else if ((fs === "r" || fs === "l") && (ts === "t" || ts === "b")) {
      d = `M ${p1.x},${p1.y} L ${p2.x},${p1.y} L ${p2.x},${p2.y}`;
      lx = (p1.x + p2.x) / 2;
      ly = p1.y;
    } else if ((fs === "b" || fs === "t") && (ts === "l" || ts === "r")) {
      d = `M ${p1.x},${p1.y} L ${p1.x},${p2.y} L ${p2.x},${p2.y}`;
      lx = (p1.x + p2.x) / 2;
      ly = p2.y;
    } else if ((fs === "r" || fs === "l") && (ts === "l" || ts === "r")) {
      const mx = (p1.x + p2.x) / 2;
      d = `M ${p1.x},${p1.y} L ${mx},${p1.y} L ${mx},${p2.y} L ${p2.x},${p2.y}`;
      lx = mx;
      ly = (p1.y + p2.y) / 2;
    } else {
      const my = (p1.y + p2.y) / 2;
      d = `M ${p1.x},${p1.y} L ${p1.x},${my} L ${p2.x},${my} L ${p2.x},${p2.y}`;
      lx = (p1.x + p2.x) / 2;
      ly = my;
    }

    if (e.lx !== undefined) lx = e.lx;
    if (e.ly !== undefined) ly = e.ly;

    const dash = e.dashed ? `stroke-dasharray="5,4"` : "";
    edgeSvgs.push(
      `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round" ${dash} marker-end="url(#actArr_${color.replace("#", "")})"/>`
    );

    if (e.label) {
      const tw = Math.max(36, e.label.length * 6.5 + 14);
      const pillFill = e.pillFill ?? "#ffffff";
      const pillStroke = e.pillStroke ?? "#cbd5e1";
      const pillText = e.pillText ?? "#1e293b";
      edgeSvgs.push(`
        <rect x="${lx - tw / 2}" y="${ly - 10}" width="${tw}" height="20" rx="6" fill="${pillFill}" stroke="${pillStroke}" stroke-width="1.1"/>
        <text x="${lx}" y="${ly + 4}" text-anchor="middle" font-size="10.8" font-weight="700" fill="${pillText}">${esc(e.label)}</text>
      `);
    }
  }

  // Unique arrow markers per color
  const colors = new Set(["#475569", ...edges.map((e) => e.color ?? "#475569")]);
  const markers = [...colors]
    .map(
      (c) =>
        `<marker id="actArr_${c.replace("#", "")}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,1 L7,4 L0,7 Z" fill="${c}"/>
        </marker>`
    )
    .join("");

  // Draw nodes
  const nodeSvgs = [];
  for (const item of measured.values()) {
    if (item.type === "start") {
      nodeSvgs.push(`<circle cx="${item.cx}" cy="${item.cy}" r="11" fill="#0f172a"/>`);
    } else if (item.type === "end") {
      nodeSvgs.push(`
        <circle cx="${item.cx}" cy="${item.cy}" r="13" fill="#ffffff" stroke="#0f172a" stroke-width="2.2"/>
        <circle cx="${item.cx}" cy="${item.cy}" r="7.5" fill="#0f172a"/>
      `);
    } else {
      const theme = NODE_THEMES[item.type ?? "action"] ?? NODE_THEMES.action;
      const rx = item.type === "decision" ? 18 : 9;
      const lineH = 16.5;
      const startY = item.cy - ((item.lines.length - 1) * lineH) / 2 + 4.5;
      const textEls = item.lines
        .map(
          (line, idx) =>
            `<text x="${item.cx}" y="${startY + idx * lineH}" text-anchor="middle" font-size="12" font-weight="${
              theme.bold ? 650 : 500
            }" fill="${theme.text}">${esc(line)}</text>`
        )
        .join("");

      nodeSvgs.push(`
        <rect x="${item.x}" y="${item.y}" width="${item.w}" height="${item.h}" rx="${rx}" fill="${theme.fill}" stroke="${theme.stroke}" stroke-width="1.7"/>
        ${textEls}
      `);
    }
  }

  const titleSvg = title
    ? `<text x="${totalW / 2}" y="${padY + 14}" text-anchor="middle" font-size="14" font-weight="700" fill="#0f172a">${esc(title)}</text>`
    : "";

  return {
    name,
    width: totalW + 4,
    scale: 2,
    body: `
      <div style="border:1.5px solid #cbd5e1;border-radius:12px;background:#ffffff;overflow:hidden;">
        <svg width="${totalW}" height="${totalH}" viewBox="0 0 ${totalW} ${totalH}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:'Segoe UI',Arial,sans-serif;">
          <defs>${markers}</defs>
          ${titleSvg}
          ${edgeSvgs.join("")}
          ${nodeSvgs.join("")}
        </svg>
      </div>
    `,
  };
}
