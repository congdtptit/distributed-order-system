import { execFileSync, spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const IMAGES_DIR = path.resolve(__dirname, "../images");

const CHROME_CANDIDATES = [
  "C:\\Users\\thanh\\AppData\\Local\\ms-playwright\\chromium-1228\\chrome-win64\\chrome.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

function findChrome() {
  for (const p of CHROME_CANDIDATES) {
    if (fs.existsSync(p)) return p;
  }
  throw new Error("Could not find Chrome/Chromium/Edge binary");
}

async function waitForWsUrl(port) {
  for (let i = 0; i < 60; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await res.json();
      const page = targets.find((t) => t.type === "page");
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
    } catch {
      // Browser not ready yet
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("Timed out waiting for Chromium DevTools endpoint");
}

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 0;
    this.pending = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve);
      this.ws.addEventListener("error", reject);
    });
    this.ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    });
  }
  async send(method, params = {}) {
    await this.ready;
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    this.ws.close();
  }
}

export const BASE_CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #ffffff;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
    color: #0f172a;
    -webkit-font-smoothing: antialiased;
  }
  #canvas {
    display: inline-block;
    background: #ffffff;
    padding: 20px 24px;
  }
  .mono {
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 0.92em;
  }
`;

export function wrapHtml(body, width = 1120) {
  return `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<style>${BASE_CSS}</style>
</head>
<body>
  <div id="canvas"><div style="width:${width}px">${body}</div></div>
</body>
</html>`;
}

export async function renderDiagrams(diagrams) {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "report-chrome-"));
  const port = 9333 + Math.floor(Math.random() * 500);
  const chrome = spawn(
    findChrome(),
    [
      "--headless=new",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "about:blank",
    ],
    { stdio: "ignore" }
  );

  try {
    const wsUrl = await waitForWsUrl(port);
    const cdp = new CDP(wsUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    for (const d of diagrams) {
      const tmpHtml = path.join(userDataDir, `${d.name}.html`);
      fs.writeFileSync(tmpHtml, wrapHtml(d.body, d.width ?? 1120), "utf8");
      const fileUrl = `file:///${tmpHtml.replace(/\\/g, "/")}`;
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: (d.width ?? 1120) + 120,
        height: 1800,
        deviceScaleFactor: d.scale ?? 2,
        mobile: false,
      });
      await cdp.send("Page.navigate", { url: fileUrl });
      await new Promise((r) => setTimeout(r, 150));

      const evalRes = await cdp.send("Runtime.evaluate", {
        expression: `(() => {
          const el = document.getElementById('canvas');
          const r = el.getBoundingClientRect();
          return { x: r.left, y: r.top, width: Math.ceil(r.width), height: Math.ceil(r.height) };
        })()`,
        returnByValue: true,
      });
      const rect = evalRes.result.value;
      const shot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        clip: { x: rect.x, y: rect.y, width: rect.width, height: rect.height, scale: 1 },
      });
      const outPath = path.join(IMAGES_DIR, `${d.name}.png`);
      fs.writeFileSync(outPath, Buffer.from(shot.data, "base64"));
      console.log(`Rendered ${d.name}.png (${rect.width}x${rect.height} @${d.scale ?? 2}x)`);
    }
    cdp.close();
  } finally {
    chrome.kill();
    setTimeout(() => {
      try {
        fs.rmSync(userDataDir, { recursive: true, force: true });
      } catch {
        // ignore cleanup race on Windows
      }
    }, 300);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const target = process.argv[2];
  const { DIAGRAMS } = await import("./diagrams_spec.mjs");
  const list = target ? DIAGRAMS.filter((d) => d.name === target) : DIAGRAMS;
  if (list.length === 0) {
    console.error("No matching diagram:", target);
    process.exit(1);
  }
  await renderDiagrams(list);
}
