// Local preview server for Buoys & lights.
//   npm install && npm start                  -> http://localhost:8790
//   SITE_DIR=/path/to/build/site npm start    (default: ../build/site, made by pipeline/run_aton.py)
//   FONTS_DIR=/path/to/fonts npm start        map label fonts (<Font_Name>/<range>.pbf); else MapLibre's demo fonts
//   COAST=/path/to/coast.geojson npm start    rough land under the overlay (default ../build/coast.geojson, if
//                                             pipeline/tools/make_coast.py made one); the preview only
//
// Serves the preview page and MapLibre from node_modules, and stands in for the vm-aton Worker by running the
// Worker's own code (../worker/src/index.js) on the built folder: same routes, same tiles out of aton.pmtiles,
// same answers. To go through `wrangler dev` instead: worker/dev_local.sh, then ?api=http://localhost:8787
import { createServer } from "node:http";
import { closeSync, existsSync, openSync, readFileSync, readSync, statSync, createReadStream } from "node:fs";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import worker from "../worker/src/index.js";

const here = fileURLToPath(new URL(".", import.meta.url));
const PORT = Number(process.env.PORT || 8790);
const SITE_DIR = resolve(process.env.SITE_DIR || join(here, "../build/site"));
const FONTS_DIR = process.env.FONTS_DIR ? resolve(process.env.FONTS_DIR) : "";
// optional rough land for the preview's plain background (pipeline/tools/make_coast.py); never in the app
const COAST = resolve(process.env.COAST || join(here, "../build/coast.geojson"));
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
  ".json": "application/json; charset=utf-8", ".png": "image/png", ".pbf": "application/x-protobuf" };
const VENDOR = {
  "/vendor/maplibre-gl.js": "node_modules/maplibre-gl/dist/maplibre-gl.js",
  "/vendor/maplibre-gl.css": "node_modules/maplibre-gl/dist/maplibre-gl.css",
};
const PAGES = { "/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/aton.js": "aton.js" };

/** The built folder as an R2 bucket (get with byte ranges, head), for the Worker's code. */
export function folderBucket(dir) {
  const file = key => {
    const f = normalize(join(dir, key));
    if (!f.startsWith(dir + sep)) return null;
    try { const st = statSync(f); return st.isFile() ? [f, st] : null; } catch { return null; }
  };
  const meta = (key, st) => ({ key, size: st.size, etag: `${st.size}-${st.mtimeMs | 0}`, httpEtag: `"${st.size}-${st.mtimeMs | 0}"` });
  return {
    async head(key) { const h = file(key); return h ? meta(key, h[1]) : null; },
    async get(key, opts = {}) {
      const h = file(key);
      if (!h) return null;
      const [f, st] = h;
      let bytes;
      if (opts.range) {
        const fd = openSync(f, "r");
        try {
          bytes = Buffer.alloc(Math.max(0, Math.min(opts.range.length, st.size - opts.range.offset)));
          readSync(fd, bytes, 0, bytes.length, opts.range.offset);
        } finally { closeSync(fd); }
      } else {
        bytes = readFileSync(f);
      }
      const u8 = new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      return { ...meta(key, st), body: u8,
               async arrayBuffer() { return u8.slice().buffer; }, async text() { return bytes.toString("utf-8"); } };
    },
  };
}

function send(res, status, body, type = "text/plain; charset=utf-8", extra = {}) {
  res.writeHead(status, { "Content-Type": type, "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store", ...extra });
  res.end(body);
}

function sendFile(req, res, path) {
  let st;
  try { st = statSync(path); } catch { return send(res, 404, "not found"); }
  if (!st.isFile()) return send(res, 404, "not found");
  res.writeHead(200, { "Content-Type": TYPES[extname(path)] || "application/octet-stream", "Content-Length": st.size,
    "Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache" });
  return req.method === "HEAD" ? res.end() : createReadStream(path).pipe(res);
}

const env = { ATON: folderBucket(SITE_DIR), API_KEYS: "", ALLOWED_ORIGINS: "*" };

createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || `localhost:${PORT}`}`);
  const p = url.pathname;
  if (PAGES[p]) return sendFile(req, res, join(here, PAGES[p]));
  if (VENDOR[p]) return sendFile(req, res, join(here, VENDOR[p]));
  if (p === "/coast.geojson") return existsSync(COAST) ? sendFile(req, res, COAST) : send(res, 404, "no coast.geojson (optional)");
  const fm = p.match(/^\/fonts\/([^/]{1,80})\/(\d{1,5}-\d{1,5})\.pbf$/);
  if (fm) {
    const stack = decodeURIComponent(fm[1]).split(",")[0].trim();
    const f = FONTS_DIR && [stack.replace(/ /g, "_"), stack].map(n => join(FONTS_DIR, n, `${fm[2]}.pbf`)).find(existsSync);
    if (f) return sendFile(req, res, f);
    // no local fonts: MapLibre's demo fonts (needs the internet; without it labels just don't draw)
    return send(res, 302, "", "text/plain", { Location: `https://demotiles.maplibre.org/font/${encodeURIComponent(stack)}/${fm[2]}.pbf` });
  }
  // everything else: the Worker's own code on the built folder
  try {
    const r = await worker.fetch(new Request(url, { method: req.method, headers: req.headers }), env, { waitUntil() {} });
    const headers = Object.fromEntries(r.headers);
    headers["Cache-Control"] = "no-cache";
    res.writeHead(r.status, headers);
    if (req.method === "HEAD" || !r.body) return res.end();
    res.end(Buffer.from(await r.arrayBuffer()));
  } catch (e) {
    send(res, 500, String(e && e.stack || e));
  }
}).listen(PORT, "0.0.0.0", () => {
  console.log(`Buoys & lights preview: http://localhost:${PORT}   (files from ${SITE_DIR})`);
});
