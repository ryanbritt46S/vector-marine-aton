// Browser test of the preview on a built site: the overlay on and off, the symbols and status rings on the
// map, a tap card with the same words as aton.js, the data date and "Not for navigation".
//   SITE_DIR=../build/site-sample CHROME=/path/to/chrome node --test test/preview.test.mjs
//   ATON_URL=http://localhost:8787 ...   read through a running vm-aton Worker (worker/dev_local.sh)
// Skipped when nothing is built (.venv/bin/python3 pipeline/run_aton.py --sample --out build/site-sample) or no Chrome.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import * as A from "../aton.js";

const here = fileURLToPath(new URL("..", import.meta.url));
const SITE_DIR = process.env.SITE_DIR || join(here, "../build/site-sample");
const ATON_URL = process.env.ATON_URL || "";
const CHROME = process.env.CHROME || ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/chromium", "/usr/bin/google-chrome"].find(existsSync);
const skip = !existsSync(join(SITE_DIR, "meta.json")) ? `nothing built at ${SITE_DIR} (.venv/bin/python3 pipeline/run_aton.py --sample --out build/site-sample)`
  : !CHROME ? "no Chrome found (set CHROME=...)" : false;

async function open(extra = "") {
  const { chromium } = await import("playwright-core");
  const port = 8900 + Math.floor(Math.random() * 90);
  const server = spawn(process.execPath, [join(here, "serve.mjs")], { env: { ...process.env, PORT: String(port), SITE_DIR, COAST: "/nonexistent" }, stdio: "pipe" });
  await new Promise(r => server.stdout.once("data", r));
  const browser = await chromium.launch({ executablePath: CHROME, args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: { width: 1100, height: 880 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  // MapLibre logs the font loads this test aborts on purpose (as "Error" or a one-letter minified error name)
  page.on("console", m => { if (m.type() === "error" && !/Failed to (load resource|fetch)|coast\.geojson|404|^Error$|^[A-Za-z]{1,2}$|net::/.test(m.text())) errors.push(m.text()); });
  // no outside network in tests, and no fonts: labels don't draw, and the symbols must still be there
  await page.route(/demotiles\.maplibre\.org|tile\.openstreetmap\.org|\/fonts\//, r => r.abort());
  const api = ATON_URL ? `&api=${encodeURIComponent(ATON_URL)}` : "";
  await page.goto(`http://localhost:${port}/?x=1${api}${extra}`);
  return { page, errors, close: async () => { await browser.close(); server.kill(); } };
}

async function tapAt(page, lon, lat) {
  const box = await page.locator("#map").boundingBox();
  const p = await page.evaluate(([x, y]) => window.__map.project([x, y]), [lon, lat]);
  const seq = await page.evaluate(() => Number(document.getElementById("card").dataset.seq || 0));
  await page.mouse.click(box.x + p.x, box.y + p.y - 6);              // on the symbol, just above its position
  await page.waitForFunction(s => Number(document.getElementById("card").dataset.seq || 0) > s, seq, { timeout: 5000 });
  return page.evaluate(() => document.getElementById("card").classList.contains("on") ? document.getElementById("cardBody").innerText : null);
}

test("buoys & lights: on, symbols, rings, tap card, off", { skip, timeout: 180000 }, async () => {
  const meta = JSON.parse(readFileSync(join(SITE_DIR, "meta.json")));
  const icons = JSON.parse(readFileSync(join(SITE_DIR, "icons/icons.json")));
  const { page, errors, close } = await open(`&at=-74.0075,39.672,14.5&now=${encodeURIComponent(meta.generated_at)}`);
  try {
    await page.click("#overlaysBtn");
    await page.click("#atonSwitch");
    await page.click("#overlaysBtn");                                    // close the menu: it covers the map
    await page.waitForFunction(() => window.__aton?.ready() && window.__map.getLayer("vm-aton-symbols"), null, { timeout: 20000 });
    await page.waitForFunction(() => window.__map.areTilesLoaded() && window.__map.loaded(), null, { timeout: 20000 });

    // under the style's vm-overlays anchor, in the style.json order; every icon added
    const order = await page.evaluate(() => window.__map.getStyle().layers.map(l => l.id));
    assert.deepEqual(order.slice(-4), ["vm-aton-status", "vm-aton-symbols", "vm-aton-labels", "vm-overlays"]);
    const missing = await page.evaluate(names => names.filter(n => !window.__map.hasImage(n)), Object.keys(icons.icons).map(s => icons.prefix + s));
    assert.deepEqual(missing, []);
    assert.equal(await page.isVisible("#sampleBanner"), !!meta.sample);
    assert.match(await page.textContent("#note"), new RegExp(`Coast Guard data of ${A.fmtDate(meta.data_date)} · Not for navigation`));

    // the rendered aids: every one has a symbol we drew; status aids carry a ring
    const feats = await page.evaluate(() => window.__map.queryRenderedFeatures({ layers: ["vm-aton-symbols"] }).map(f => f.properties));
    assert.ok(feats.length >= 8, `${feats.length} aids on screen`);
    for (const p of feats) assert.ok(icons.icons[p.sym], p.sym);
    const rings = await page.evaluate(() => window.__map.queryRenderedFeatures({ layers: ["vm-aton-status"] }).map(f => f.properties.id));
    const withStatus = feats.filter(p => p.status).map(p => p.id);
    assert.ok(withStatus.length >= 1);
    assert.deepEqual([...new Set(rings)].sort(), [...new Set(withStatus)].sort());

    // tap the missing lighted buoy: the card has aton.js's words
    const lb2 = await page.evaluate(() => window.__map.querySourceFeatures("vm-aton", { sourceLayer: "aton",
      filter: ["==", ["get", "name"], "SAMPLE Lighted Buoy 2"] }).map(f => ({ p: f.properties, c: f.geometry.coordinates }))
      .find(f => f.p.district === 5));
    assert.ok(lb2, "SAMPLE Lighted Buoy 2 in the tiles");
    const txt = await tapAt(page, lb2.c[0], lb2.c[1]);
    const want = A.card(lb2.p, meta.data_date);
    assert.ok(txt.includes(want.title), txt);
    assert.ok(txt.includes(want.status) && /^MISSING.* since /.test(want.status), txt);
    for (const [k, v] of want.rows) assert.ok(txt.includes(v), `${k}: ${v}`);
    assert.match(txt, /Not for navigation/);
    assert.equal(await page.getAttribute("#card", "data-id"), lb2.p.id);

    // a tap on open water closes it
    const box = await page.locator("#map").boundingBox();
    const seq = await page.evaluate(() => Number(document.getElementById("card").dataset.seq || 0));
    await page.mouse.click(box.x + 24, box.y + 160);                     // above the card, away from the aids
    await page.waitForFunction(s => Number(document.getElementById("card").dataset.seq || 0) > s, seq, { timeout: 5000 });
    assert.equal(await page.isVisible("#card"), false);

    // off: every layer, the source and the images go; the base style is untouched
    await page.click("#overlaysBtn");
    await page.click("#atonSwitch");
    const left = await page.evaluate(() => ({ layers: window.__map.getStyle().layers.map(l => l.id),
      source: !!window.__map.getSource("vm-aton") || !!window.__map.getSource("vm-aton-text"), images: window.__map.listImages().filter(n => n.startsWith("vm-aton-")).length }));
    assert.deepEqual(left, { layers: order.filter(id => !id.startsWith("vm-aton-")), source: false, images: 0 });
    assert.equal(await page.isVisible("#note"), false);
    assert.deepEqual(errors, []);
  } finally {
    await close();
  }
});
