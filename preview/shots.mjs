// Screenshots of the preview at fixed places, for docs/img and for checking the symbols by eye.
//   SITE_DIR=../build/site FONTS_DIR=... CHROME=/path/to/chrome node shots.mjs [out dir]   (default ../docs/img)
// Needs a build of the real data (bash local.sh builds one) and Chrome or Chromium.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const OUT = resolve(process.argv[2] || join(here, "../docs/img"));
const SITE_DIR = resolve(process.env.SITE_DIR || join(here, "../build/site"));
const CHROME = process.env.CHROME || ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/chromium", "/usr/bin/google-chrome"].find(existsSync);

const EXTRA = process.env.EXTRA ? JSON.parse(process.env.EXTRA) : null;   // [{name, at:[lon,lat,z]}] for checks
export const VIEWS = EXTRA || [
  { name: "barnegat-inlet", at: [-74.085, 39.758, 14.5] },
  { name: "barnegat-inlet-card", at: [-74.072, 39.749, 14.5], aid: "5-900" },
  { name: "manasquan-inlet", at: [-74.03, 40.10, 14.5] },
  { name: "little-egg-inlet", at: [-74.297, 39.482, 13.5] },
  { name: "little-egg-inlet-card", at: [-74.283, 39.474, 13.5], aid: "5-1105" },
  { name: "new-york-harbor-entrance", at: [-74.03, 40.48, 12] },
  { name: "miami-government-cut", at: [-80.13, 25.76, 13] },
];

async function main() {
  const { chromium } = await import("playwright-core");
  mkdirSync(OUT, { recursive: true });
  const port = 8950 + Math.floor(Math.random() * 40);
  const server = spawn(process.execPath, [join(here, "serve.mjs")], { env: { ...process.env, PORT: String(port), SITE_DIR }, stdio: "pipe" });
  await new Promise(r => server.stdout.once("data", r));
  const browser = await chromium.launch({ executablePath: CHROME,
    args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  try {
    const only = process.env.ONLY ? process.env.ONLY.split(",") : null;
    for (const v of VIEWS.filter(v => !only || only.includes(v.name))) {
      const page = await browser.newPage({ viewport: { width: 1320, height: 720 }, deviceScaleFactor: 1.5 });
      page.on("pageerror", e => console.error(v.name, e.message));
      await page.goto(`http://localhost:${port}/?on=1&wide=1&at=${v.at.join(",")}${v.aid ? `&aid=${v.aid}` : ""}`);
      await page.waitForFunction(() => window.__aton?.ready(), null, { timeout: 30000 });
      await page.waitForFunction(() => window.__map.areTilesLoaded() && window.__map.loaded(), null, { timeout: 30000 });
      if (v.aid) await page.waitForFunction(id => document.getElementById("card").dataset.id === id, v.aid, { timeout: 20000 });
      await page.waitForTimeout(600);
      const file = join(OUT, `${v.name}.png`);
      await page.locator("#phone").screenshot({ path: file });
      console.log(file);
      await page.close();
    }
  } finally {
    await browser.close();
    server.kill();
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main().catch(e => { console.error(e); process.exit(1); });
