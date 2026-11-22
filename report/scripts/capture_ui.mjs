import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const IMAGES_DIR = path.resolve(__dirname, "../images");
const BASE_URL = process.env.UI_URL || "http://localhost:5173";

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
      // ignore until ready
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

const SHOTS = [
  {
    name: "hinh-3-1-chi-nhanh",
    route: "/branch/POS01",
    prep: `(() => {
      const btns = [...document.querySelectorAll('button[aria-label^="Thêm một "]')].filter(b => !b.disabled);
      if (btns[0]) btns[0].click();
      if (btns[1]) btns[1].click();
    })()`,
  },
  { name: "hinh-3-2-bep", route: "/kitchen" },
  { name: "hinh-3-3-kho", route: "/inventory" },
  { name: "hinh-3-4-giam-sat", route: "/monitor" },
  { name: "hinh-3-5-quan-ly", route: "/reports" },
];

async function captureAll() {
  const chromePath = findChrome();
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "cap-ui-"));
  const port = 9229 + Math.floor(Math.random() * 400);

  const chrome = spawn(
    chromePath,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-sandbox",
      "--hide-scrollbars",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      "about:blank",
    ],
    { stdio: "ignore" }
  );

  try {
    const wsUrl = await waitForWsUrl(port);
    const cdp = new CDP(wsUrl);
    await cdp.send("Page.enable");

    for (const s of SHOTS) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: 1380,
        height: 900,
        deviceScaleFactor: 2,
        mobile: false,
      });
      await cdp.send("Page.navigate", { url: `${BASE_URL}${s.route}` });
      for (let w = 0; w < 25; w++) {
        await new Promise((r) => setTimeout(r, 250));
        const res = await cdp.send("Runtime.evaluate", {
          expression: `Boolean(document.querySelector('h1') && !document.querySelector('[role="progressbar"], .animate-pulse'))`,
          returnByValue: true,
        });
        if (res.result.value) break;
      }
      await new Promise((r) => setTimeout(r, 300));

      if (s.prep) {
        await cdp.send("Runtime.evaluate", { expression: s.prep });
        await new Promise((r) => setTimeout(r, 250));
      }

      const evalRes = await cdp.send("Runtime.evaluate", {
        expression: `(() => {
          const h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight, 760);
          return { width: 1380, height: Math.ceil(h) };
        })()`,
        returnByValue: true,
      });
      const size = evalRes.result.value;

      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: size.width,
        height: size.height,
        deviceScaleFactor: 2,
        mobile: false,
      });
      await new Promise((r) => setTimeout(r, 150));

      const shot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        clip: { x: 0, y: 0, width: size.width, height: size.height, scale: 1 },
      });
      const outPath = path.join(IMAGES_DIR, `${s.name}.png`);
      fs.writeFileSync(outPath, Buffer.from(shot.data, "base64"));
      console.log(`Captured ${s.name}.png (${size.width}x${size.height} @2x)`);
    }
    cdp.close();
  } finally {
    chrome.kill();
    setTimeout(() => {
      try {
        fs.rmSync(userDataDir, { recursive: true, force: true });
      } catch {
        // ignore cleanup race
      }
    }, 300);
  }
}

captureAll().catch((err) => {
  console.error(err);
  process.exit(1);
});
