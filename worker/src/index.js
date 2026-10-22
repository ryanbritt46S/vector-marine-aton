/**
 * vm-aton - serves Buoys & lights (US Coast Guard aids to navigation) to the app from the vm-aton R2 bucket.
 *
 *   GET /health                      "ok" (no key)
 *   GET /meta.json                   when the data is from, counts, versions (small; the app reads it first)
 *   GET /style.json                  the overlay's MapLibre source + layers ("{base}" filled in with this Worker)
 *   GET /aton.json                   TileJSON; its tile URL carries the tiles' version (?v=) so a new build
 *                                    never mixes with cached tiles of the old one
 *   GET /aton/{z}/{x}/{y}.mvt        one vector tile, read from aton.pmtiles in R2 with range requests;
 *                                    204 where there are no aids
 *   GET /icons/<sym>[@2x|@3x].png    the symbols; /icons/icons.json lists them
 *
 * The files are written by the GitHub Action (pipeline/), not by this Worker: it only checks the API key, reads
 * tiles out of the archive and hands files out, so a failed data job never breaks the map (the last build stays).
 * scheduled() (Cron Trigger, wrangler.toml) copies the Coast Guard's files into raw/<date>/ for that Action,
 * because NAVCEN refuses GitHub's machines: src/mirror.js. raw/ has no route; nothing of it is served.
 * Its own Worker and bucket: nothing here can touch the chart (bathy-tiles) or other overlays.
 * PUBLIC_URL (optional var): the address to put in style.json and aton.json; default: the request's own
 * (wrangler dev rewrites that to the custom domain, so dev_local.sh sets it to http://localhost:<port>).
 * API keys: secret API_KEYS = "label:key,label:key" (same format and normally the same keys as the tiles
 * Worker). The app sends an X-API-Key header or ?key= (map tile URLs can't carry headers). Unset = public
 * (local testing only).
 */
import { PMTiles } from "pmtiles";
import { mirror, realDeps } from "./mirror.js";

const JSON_T = "application/json; charset=utf-8";
const MVT_T = "application/x-protobuf";
const PM_KEY = "aton.pmtiles";
const SHORT = "public, max-age=300";
const IMMUTABLE = "public, max-age=2592000, immutable";   // a tile of a given version never changes
const ICON = "public, max-age=86400";
const HEAD_TTL_MS = 60 * 1000;                            // re-check the archive's version at most once a minute

/** The archive in R2, read by byte ranges. */
export class R2Source {
  constructor(bucket, key) { this.bucket = bucket; this.key = key; }
  getKey() { return this.key; }
  async getBytes(offset, length) {
    const obj = await this.bucket.get(this.key, { range: { offset, length } });
    if (!obj) throw new Error(`not found: ${this.key}`);
    return { data: await obj.arrayBuffer(), etag: obj.etag };
  }
}

// one reader per bucket (per isolate), re-checked once a minute: a new upload is picked up within a minute
const readers = new WeakMap();
async function reader(env) {
  const had = readers.get(env.ATON);
  if (had && Date.now() - had.checked < HEAD_TTL_MS) return had;
  const head = await env.ATON.head(PM_KEY);
  if (!head) { readers.delete(env.ATON); return null; }
  if (had && had.etag === head.etag) { had.checked = Date.now(); return had; }
  const pm = new PMTiles(new R2Source(env.ATON, PM_KEY));
  const [header, metadata] = await Promise.all([pm.getHeader(), pm.getMetadata()]);
  const r = { pm, header, metadata: metadata || {}, etag: head.etag, version: (metadata && metadata.version) || head.etag, checked: Date.now() };
  readers.set(env.ATON, r);
  return r;
}

export default {
  /** Cron Trigger: today's copy of the NAVCEN files (src/mirror.js). A throw marks the run failed in the logs. */
  async scheduled(event, env, ctx) {
    const r = await mirror(env, event.scheduledTime, realDeps);
    console.log(JSON.stringify(r.skipped ? r : { dir: r.dir, files: r.files.length, light_list_parts: r.light_list_parts,
                                                 notice_parts: r.notice_parts }));
  },
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const cors = corsHeaders(req, env);
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: { ...cors, "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "If-None-Match, X-API-Key", "Access-Control-Max-Age": "86400" } });
    }
    if (req.method !== "GET" && req.method !== "HEAD") return text("method not allowed", 405, cors);
    const path = url.pathname.replace(/\/+$/, "");
    if (path === "/health") return text("ok", 200, cors);

    if (!keyOk(req, url, env)) return json({ error: "missing or invalid API key" }, 401, cors);

    try {
      if (path === "/meta.json") return await object(req, env, ctx, "meta.json", cors, { "Content-Type": JSON_T, "Cache-Control": SHORT }, false);
      const base = (env.PUBLIC_URL || url.origin).replace(/\/+$/, "");
      if (path === "/style.json") return await style(req, url, base, env, cors);
      if (path === "/aton.json") return await tileJson(url, base, env, cors);
      let m = path.match(/^\/aton\/(\d{1,2})\/(\d{1,9})\/(\d{1,9})\.mvt$/);
      if (m) return await tile(req, url, env, ctx, +m[1], +m[2], +m[3], cors);
      m = path.match(/^\/icons\/([a-z0-9-]{1,40}(?:@[23]x)?\.png)$/);
      if (m) return await object(req, env, ctx, `icons/${m[1]}`, cors, { "Content-Type": "image/png", "Cache-Control": ICON }, true);
      if (path === "/icons/icons.json") return await object(req, env, ctx, "icons/icons.json", cors, { "Content-Type": JSON_T, "Cache-Control": SHORT }, false);
    } catch (e) {
      return json({ error: "unavailable", detail: String(e && e.message || e) }, 503, cors);
    }
    return text("not found", 404, cors);
  },
};

/** The key the request came with, for URLs this Worker hands out (browsers and map tile URLs can't send headers). */
function keyParam(url) {
  const k = url.searchParams.get("key");
  return k ? `key=${encodeURIComponent(k)}` : "";
}

async function style(req, url, base, env, cors) {
  const obj = await env.ATON.get("style.json");
  if (!obj) return text("not found", 404, cors);
  const k = keyParam(url);
  const body = (await obj.text()).split("{base}/aton.json").join(`${base}/aton.json${k ? `?${k}` : ""}`).split("{base}").join(base);
  return new Response(req.method === "HEAD" ? null : body, { status: 200, headers: { ...cors, "Content-Type": JSON_T, "Cache-Control": SHORT } });
}

async function tileJson(url, base, env, cors) {
  const r = await reader(env);
  if (!r) return json({ error: "no tiles published yet" }, 404, cors);
  const h = r.header, md = r.metadata;
  const qs = [`v=${encodeURIComponent(r.version)}`, keyParam(url)].filter(Boolean).join("&");
  return json({
    tilejson: "3.0.0", name: "Buoys & lights", description: md.description || "", attribution: md.attribution || "",
    version: r.version, scheme: "xyz", format: "pbf",
    tiles: [`${base}/aton/{z}/{x}/{y}.mvt?${qs}`],
    minzoom: h.minZoom, maxzoom: h.maxZoom,
    bounds: [h.minLon, h.minLat, h.maxLon, h.maxLat],
    center: [h.centerLon, h.centerLat, h.centerZoom],
    vector_layers: md.vector_layers || [{ id: "aton", fields: {} }],
  }, 200, cors, { "Cache-Control": SHORT });
}

/** One tile. Kept at Cloudflare's edge keyed by the archive's version (not the API key: every app shares it). */
async function tile(req, url, env, ctx, z, x, y, cors) {
  if (z > 30 || x >= 2 ** z || y >= 2 ** z) return text("not found", 404, cors);
  const r = await reader(env);
  if (!r) return text("no tiles published yet", 404, cors);
  const current = url.searchParams.get("v") === r.version;
  const etag = `"${r.version}-${z}-${x}-${y}"`;
  const headers = { "Content-Type": MVT_T, "Cache-Control": current ? IMMUTABLE : SHORT, "ETag": etag };
  const inm = req.headers.get("If-None-Match");
  if (inm && etagMatch(inm, etag)) return new Response(null, { status: 304, headers: { ...cors, ...headers } });
  const cache = typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = cache ? new Request(`https://vm-aton.cache/aton/${z}/${x}/${y}.mvt?v=${r.version}`) : null;
  if (cache) {
    const hit = await cache.match(cacheKey);
    if (hit) return withCors(new Response(req.method === "HEAD" ? null : hit.body, { status: 200, headers: { ...Object.fromEntries(hit.headers), ...headers } }), cors);
  }
  const h = r.header;
  const t = z < h.minZoom || z > h.maxZoom ? null : await r.pm.getZxy(z, x, y);
  if (!t || !t.data || t.data.byteLength === 0) {
    return new Response(null, { status: 204, headers: { ...cors, "Cache-Control": headers["Cache-Control"], "ETag": etag } });
  }
  const res = new Response(t.data, { status: 200, headers: { ...headers, "Content-Length": String(t.data.byteLength) } });
  if (cache && ctx && ctx.waitUntil) ctx.waitUntil(cache.put(cacheKey, res.clone()).catch(() => {}));
  return withCors(req.method === "HEAD" ? new Response(null, res) : res, cors);
}

/** One R2 object, with ETag / 304; with edge=true also kept in Cloudflare's edge cache, without the API key. */
async function object(req, env, ctx, key, cors, headers, edge) {
  const head = req.method === "HEAD";
  const cache = edge && !head && typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = cache ? new Request(`https://vm-aton.cache/${key}`) : null;
  if (cache) {
    const hit = await cache.match(cacheKey);
    if (hit) return withCors(notModified(req, hit) || hit, cors);
  }
  const obj = head ? await env.ATON.head(key) : await env.ATON.get(key);
  if (!obj) return text("not found", 404, cors);
  const inm = req.headers.get("If-None-Match");
  if (inm && etagMatch(inm, obj.httpEtag)) {
    return new Response(null, { status: 304, headers: { ...cors, ...headers, "ETag": obj.httpEtag } });
  }
  const res = new Response(head ? null : obj.body, { status: 200, headers: { ...headers, "ETag": obj.httpEtag, "Content-Length": String(obj.size) } });
  if (cache && ctx && ctx.waitUntil) ctx.waitUntil(cache.put(cacheKey, res.clone()).catch(() => {}));
  return withCors(res, cors);
}

function etagMatch(inm, etag) {
  return inm.split(",").map(t => t.trim().replace(/^W\//, "")).includes(etag);
}

function notModified(req, res) {
  const inm = req.headers.get("If-None-Match");
  const etag = res.headers.get("ETag");
  if (!inm || !etag || !etagMatch(inm, etag)) return null;
  const h = new Headers(res.headers);
  h.delete("Content-Length");
  return new Response(null, { status: 304, headers: h });
}

function withCors(res, cors) {
  const h = new Headers(res.headers);
  for (const [k, v] of Object.entries(cors)) h.set(k, v);
  return new Response(res.body, { status: res.status, headers: h });
}

export function keyOk(req, url, env) {
  const raw = (env.API_KEYS || "").trim();
  if (!raw) return true;                                   // no keys configured: public (local testing)
  const given = url.searchParams.get("key") || req.headers.get("X-API-Key") || "";
  if (!given) return false;
  let ok = false;
  for (const item of raw.split(",")) {
    const k = item.includes(":") ? item.slice(item.indexOf(":") + 1).trim() : item.trim();
    if (k && same(k, given)) ok = true;                   // check them all: no early exit
  }
  return ok;
}

function same(a, b) {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

export function corsHeaders(req, env) {
  const allowed = (env.ALLOWED_ORIGINS || "*").split(",").map(s => s.trim()).filter(Boolean);
  const origin = req.headers.get("Origin") || "";
  const allow = allowed.includes("*") ? "*" : (allowed.includes(origin) ? origin : "");
  const h = { "Access-Control-Expose-Headers": "Content-Length, ETag" };
  if (allow) h["Access-Control-Allow-Origin"] = allow;
  if (allow !== "*") h["Vary"] = "Origin";
  return h;
}

const text = (s, status, cors) => new Response(s, { status, headers: { ...cors, "Content-Type": "text/plain; charset=utf-8" } });
const json = (o, status, cors, extra = {}) => new Response(JSON.stringify(o), { status, headers: { ...cors, "Content-Type": JSON_T, ...extra } });
