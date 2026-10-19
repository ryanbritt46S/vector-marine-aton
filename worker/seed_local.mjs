// Copy a built site into wrangler's local R2 (the same storage `wrangler dev --persist-to` reads), in one
// process: much faster than one `wrangler r2 object put --local` per file.
//   node seed_local.mjs <site dir> <persist dir>      (dev_local.sh runs this)
import { Miniflare } from "miniflare";
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, relative } from "node:path";

const [dir, persist] = process.argv.slice(2);
if (!dir || !persist) { console.error("usage: node seed_local.mjs <site dir> <persist dir>"); process.exit(2); }
const TYPES = { ".png": "image/png", ".json": "application/json", ".pmtiles": "application/octet-stream" };
const typeOf = f => TYPES[f.slice(f.lastIndexOf("."))] || "application/octet-stream";
const bytes = f => { const b = readFileSync(f); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); };
const walk = d => existsSync(d) ? readdirSync(d).flatMap(n => statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]) : [];

const mf = new Miniflare({
  modules: true, script: "export default { fetch() { return new Response('') } }",
  r2Buckets: { ATON: "vm-aton" }, r2Persist: join(persist, "v3", "r2"),
});
try {
  const bucket = await mf.getR2Bucket("ATON");
  let put = 0, kept = 0;
  const files = [...walk(join(dir, "icons")), join(dir, "aton.pmtiles"), join(dir, "style.json")];
  for (const f of files) {
    const key = relative(dir, f).split("\\").join("/");
    const size = statSync(f).size;
    const have = await bucket.head(key);
    if (have && have.size === size && key.startsWith("icons/") && !key.endsWith(".json")) { kept++; continue; }
    await bucket.put(key, bytes(f), { httpMetadata: { contentType: typeOf(f) } });
    put++;
  }
  await bucket.put("meta.json", bytes(join(dir, "meta.json")), { httpMetadata: { contentType: "application/json" } });
  console.log(`Local R2: ${put} file(s) written, ${kept} icons already there, from ${dir}`);
} finally {
  await mf.dispose();
}
