import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import worker from "../src/index.js";

// A stand-in for the R2 bucket binding: get (whole or a byte range), head. The files are a SAMPLE build
// (test/fixtures/, written by pipeline/tools/make_parity.py).
const FX = fileURLToPath(new URL("./fixtures/", import.meta.url));
const read = f => new Uint8Array(readFileSync(FX + f));
function bucket(files) {
  return {
    calls: [],
    async get(key, opts = {}) {
      this.calls.push(["get", key, opts.range ? `${opts.range.offset}+${opts.range.length}` : ""]);
      const b = files[key];
      if (!b) return null;
      const part = opts.range ? b.slice(opts.range.offset, opts.range.offset + opts.range.length) : b;
      return { key, size: b.length, etag: `e-${key}`, httpEtag: `"e-${key}"`, body: new Response(part).body,
               async arrayBuffer() { return part.buffer.slice(part.byteOffset, part.byteOffset + part.byteLength); },
               async text() { return new TextDecoder().decode(part); } };
    },
    async head(key) {
      this.calls.push(["head", key]);
      const b = files[key];
      return b ? { key, size: b.length, etag: `e-${key}`, httpEtag: `"e-${key}"` } : null;
    },
  };
}

const FILES = {
  "aton.pmtiles": read("aton.pmtiles"),
  "meta.json": read("meta.json"),
  "style.json": read("style.json"),
  "icons/icons.json": read("icons/icons.json"),
  "icons/lb-g@2x.png": read("icons/lb-g@2x.png"),
  "icons/badge-missing.png": read("icons/badge-missing.png"),
  "uploads.json": new TextEncoder().encode("{}"),
};
const META = JSON.parse(new TextDecoder().decode(FILES["meta.json"]));
const VERSION = META.tiles.version;
const env = (over = {}) => ({ API_KEYS: "ios:k1,android:k2", ATON: bucket(FILES), ...over });
const call = (path, init = {}, e = env()) => worker.fetch(new Request(`https://aton.example${path}`, init), e, { waitUntil() {} });

// the tile holding a point, like the pipeline (512-px tiles, same x/y as 256-px tiles)
function tileOf(lon, lat, z) {
  const n = 2 ** z, s = Math.sin(lat * Math.PI / 180);
  return [Math.floor((lon + 180) / 360 * n), Math.floor((0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n)];
}

test("health needs no key", async () => {
  const r = await call("/health");
  assert.equal(r.status, 200);
  assert.equal(await r.text(), "ok");
});

test("keys: missing, wrong, query, header, plain list, public", async () => {
  assert.equal((await call("/meta.json")).status, 401);
  assert.equal((await call("/meta.json?key=nope")).status, 401);
  assert.equal((await call("/meta.json?key=k1")).status, 200);
  assert.equal((await call("/meta.json", { headers: { "X-API-Key": "k2" } })).status, 200);
  assert.equal((await call("/meta.json?key=k3", {}, env({ API_KEYS: "k3, k4" }))).status, 200);
  assert.equal((await call("/meta.json?key=ios:k1")).status, 401);
  assert.equal((await call("/meta.json", {}, env({ API_KEYS: "" }))).status, 200);
  assert.equal((await call("/aton/0/0/0.mvt")).status, 401);
  assert.equal((await call("/icons/lb-g@2x.png")).status, 401);
});

test("meta: json, short cache, etag, 304", async () => {
  const r = await call("/meta.json?key=k1");
  assert.equal(r.headers.get("Content-Type"), "application/json; charset=utf-8");
  assert.equal(r.headers.get("Cache-Control"), "public, max-age=300");
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), "*");
  assert.deepEqual(await r.json(), META);
  const r2 = await call("/meta.json?key=k1", { headers: { "If-None-Match": `W/${r.headers.get("ETag")}` } });
  assert.equal(r2.status, 304);
});

test("style: the source points back at this Worker, with the key when it came in the URL", async () => {
  const s = await (await call("/style.json?key=k1")).json();
  assert.equal(s.sources["vm-aton"].url, "https://aton.example/aton.json?key=k1");
  assert.deepEqual(s.layers.map(l => l.id), ["vm-aton-status", "vm-aton-symbols", "vm-aton-labels"]);
  const h = await (await call("/style.json", { headers: { "X-API-Key": "k1" } })).json();
  assert.equal(h.sources["vm-aton"].url, "https://aton.example/aton.json");
  const local = await (await call("/style.json", {}, env({ API_KEYS: "", PUBLIC_URL: "http://localhost:8787/" }))).json();
  assert.equal(local.sources["vm-aton"].url, "http://localhost:8787/aton.json");
});

test("TileJSON: tiles here, with the version and the key", async () => {
  const tj = await (await call("/aton.json?key=k2")).json();
  assert.equal(tj.tilejson, "3.0.0");
  assert.equal(tj.version, VERSION);
  assert.deepEqual(tj.tiles, [`https://aton.example/aton/{z}/{x}/{y}.mvt?v=${VERSION}&key=k2`]);
  assert.equal(tj.minzoom, 6);
  assert.equal(tj.maxzoom, 14);
  assert.equal(tj.vector_layers[0].id, "aton");
  assert.ok(tj.vector_layers[0].fields.sym);
  assert.match(tj.attribution, /Coast Guard/);
});

test("tiles: a real tile from the archive, immutable for the current version; 204 where there are no aids", async () => {
  const [x, y] = tileOf(-74.02, 39.66, 14);                   // the SAMPLE district 5 aids start here
  const r = await call(`/aton/14/${x}/${y}.mvt?v=${VERSION}&key=k1`);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Content-Type"), "application/x-protobuf");
  assert.equal(r.headers.get("Cache-Control"), "public, max-age=2592000, immutable");
  const body = new Uint8Array(await r.arrayBuffer());
  assert.ok(body.length > 50);
  assert.notEqual(body[0], 0x1f);                              // already decompressed (Cloudflare compresses on the way out)
  assert.ok(new TextDecoder().decode(body).includes("SAMPLE"));
  assert.ok(new TextDecoder().decode(body).includes("aton"));
  const old = await call(`/aton/14/${x}/${y}.mvt?v=old&key=k1`);
  assert.equal(old.headers.get("Cache-Control"), "public, max-age=300");
  const etag = r.headers.get("ETag");
  assert.equal((await call(`/aton/14/${x}/${y}.mvt?key=k1`, { headers: { "If-None-Match": etag } })).status, 304);
  const empty = await call(`/aton/14/0/0.mvt?key=k1`);
  assert.equal(empty.status, 204);
  assert.equal((await call(`/aton/3/0/0.mvt?key=k1`)).status, 204);          // under minzoom
  assert.equal((await call(`/aton/2/4/0.mvt?key=k1`)).status, 404);          // x out of range
  assert.equal((await call(`/aton/14/${x}/${y}.pbf?key=k1`)).status, 404);
});

test("no archive yet: 404, not an error", async () => {
  const e = env({ ATON: bucket({ "meta.json": FILES["meta.json"] }) });
  assert.equal((await call(`/aton/14/1/1.mvt?key=k1`, {}, e)).status, 404);
  assert.equal((await call(`/aton.json?key=k1`, {}, e)).status, 404);
});

test("icons: png with a day's cache, the manifest", async () => {
  const r = await call("/icons/lb-g@2x.png?key=k1");
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Content-Type"), "image/png");
  assert.equal(r.headers.get("Cache-Control"), "public, max-age=86400");
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), FILES["icons/lb-g@2x.png"]);
  assert.equal((await call("/icons/badge-missing.png?key=k1")).status, 200);
  const m = await (await call("/icons/icons.json?key=k1")).json();
  assert.ok(m.icons["lb-g"].files["2"]);
  assert.equal((await call("/icons/nope.png?key=k1")).status, 404);
});

test("HEAD reads only metadata", async () => {
  const e = env();
  const r = await call("/icons/lb-g@2x.png?key=k1", { method: "HEAD" }, e);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Content-Length"), String(FILES["icons/lb-g@2x.png"].length));
  assert.deepEqual(e.ATON.calls, [["head", "icons/lb-g@2x.png"]]);
});

test("only known paths: no traversal, no other keys", async () => {
  for (const p of ["/icons/../uploads.json", "/uploads.json", "/aton.pmtiles", "/icons/x.svg", "/icons/A.png",
                   "/icons/lb-g@4x.png", "/aton/1/2", "/", "/meta", "/style"]) {
    const r = await call(`${p}?key=k1`);
    assert.equal(r.status, 404, p);
  }
});

test("methods and CORS preflight", async () => {
  assert.equal((await call("/meta.json?key=k1", { method: "POST" })).status, 405);
  const r = await call("/meta.json", { method: "OPTIONS", headers: { Origin: "http://localhost:8790" } });
  assert.equal(r.status, 204);
  assert.match(r.headers.get("Access-Control-Allow-Headers"), /X-API-Key/);
  const e = env({ ALLOWED_ORIGINS: "https://app.example" });
  const ok = await call("/meta.json?key=k1", { headers: { Origin: "https://app.example" } }, e);
  assert.equal(ok.headers.get("Access-Control-Allow-Origin"), "https://app.example");
  const no = await call("/meta.json?key=k1", { headers: { Origin: "https://evil.example" } }, e);
  assert.equal(no.headers.get("Access-Control-Allow-Origin"), null);
});

test("edge cache: key checked first, one copy without the key, keyed by the tiles' version; meta never cached", async () => {
  const store = new Map();
  globalThis.caches = { default: {
    async match(req) { const r = store.get(req.url); return r ? r.clone() : undefined; },
    async put(req, res) { store.set(req.url, res); },
  } };
  try {
    const waits = [];
    const ctx = { waitUntil: p => waits.push(p) };
    const e = env();
    const [x, y] = tileOf(-74.02, 39.66, 14);
    const r1 = await worker.fetch(new Request(`https://aton.example/aton/14/${x}/${y}.mvt?v=${VERSION}&key=k1`), e, ctx);
    assert.equal(r1.status, 200);
    const first = new Uint8Array(await r1.arrayBuffer());
    await Promise.all(waits);
    assert.ok(store.has(`https://vm-aton.cache/aton/14/${x}/${y}.mvt?v=${VERSION}`));
    const before = e.ATON.calls.filter(c => c[0] === "get").length;
    const r2 = await worker.fetch(new Request(`https://aton.example/aton/14/${x}/${y}.mvt?v=${VERSION}&key=k2`), e, ctx);
    assert.equal(r2.status, 200);
    assert.equal(e.ATON.calls.filter(c => c[0] === "get").length, before);       // from the cache, no R2 read
    assert.deepEqual(new Uint8Array(await r2.arrayBuffer()), first);
    const r3 = await worker.fetch(new Request(`https://aton.example/aton/14/${x}/${y}.mvt?key=bad`), e, ctx);
    assert.equal(r3.status, 401);                                                // a cached tile still needs a good key
    await worker.fetch(new Request("https://aton.example/icons/lb-g@2x.png?key=k1"), e, ctx);
    await worker.fetch(new Request("https://aton.example/meta.json?key=k1"), e, ctx);
    await Promise.all(waits);
    assert.ok(store.has("https://vm-aton.cache/icons/lb-g@2x.png"));
    assert.ok(![...store.keys()].some(k => k.includes("meta.json")));
  } finally {
    delete globalThis.caches;
  }
});

test("a new archive is picked up (version from its metadata), reads are ranges", async () => {
  const e = env();
  await call(`/aton.json?key=k1`, {}, e);
  const gets = e.ATON.calls.filter(c => c[0] === "get" && c[1] === "aton.pmtiles");
  assert.ok(gets.length >= 1 && gets.every(c => c[2] !== ""), "range reads only");
});
