/**
 * mirror.js - the daily copy of the Coast Guard's files (NAVCEN MSI) into the vm-aton bucket, run by this Worker's
 * Cron Trigger (wrangler.toml). NAVCEN refuses GitHub's machines (HTTP 403, seen Oct 19, 2026) but answers
 * Cloudflare's, so the download happens here and the GitHub Action builds from the copy
 * (pipeline/tools/fetch_raw.py, then run_aton.py --raw). Nothing here is served: raw/ has no route.
 *
 *   raw/<YYYY-MM-DD>/fileIndexNew.json, lightListD01_1.csv ..., discFedAid_1.geojson ...   (UTC date)
 *   raw/<YYYY-MM-DD>/_complete.json    written LAST, only when every file is there and looks right
 *
 * The same rules as the pipeline's own download (pipeline/vmaton/sources.py HttpSource + build.py):
 *   - a 404 means "not there": that's how the Light List parts are counted (the index doesn't list them)
 *   - anything else is tried again after 2, 6 and 18 s, then the run fails (no _complete.json: nothing is built)
 *   - a notice part the index lists must be there; a corrected-notices part may be missing (count_corrected skips)
 *   - more than LIGHT_LIST_MAX_PARTS parts of one district = something changed: fail, like read_light_lists
 * A run starts by clearing the day's folder, so a half-finished earlier try can't leave stale parts behind.
 * The second cron (a retry) does nothing if the day is already complete.
 *
 * The lists below must match pipeline/config/aton.json (test/mirror.test.mjs checks it).
 */
export const MSI = "https://navcen.uscg.gov/sites/default/files/msi/";
export const UA = "VectorMarine-aton/1.0 (+https://vectormarine.us; daily, one copy per file)";
export const DISTRICTS = [1, 5, 7];
export const NOTICE_PRODUCTS = ["discFedAid_", "discPriAid_", "tmpChange_"];
export const CORRECTED_PRODUCTS = ["discFedAidCor_", "discPriAidCor_", "tmpChangeCor_"];
export const LIGHT_LIST_MAX_PARTS = 40;
export const WAITS_MS = [2000, 6000, 18000];
export const COMPLETE = "_complete.json";
const LIGHT_LIST_HEADER = ["ATU", "LIGHT_LIST_NUMBER", "NAME"];   // the first columns of every Light List CSV

export const dayDir = t => "raw/" + new Date(t).toISOString().slice(0, 10);

/** Is this body the file we asked for (and not, say, an HTML challenge page sent with a 200)? */
export function looksRight(name, buf) {
  const head = new TextDecoder().decode(buf.slice(0, 4096)).replace(/^﻿/, "");
  if (name.endsWith(".csv")) {
    const cols = head.split(/\r?\n/, 1)[0].split(",").map(s => s.trim().replace(/^"|"$/g, ""));
    return LIGHT_LIST_HEADER.every((c, i) => cols[i] === c) ? null : "not a Light List CSV (unexpected first line)";
  }
  if (name.endsWith(".json") || name.endsWith(".geojson")) {
    try {
      const v = JSON.parse(new TextDecoder().decode(buf).replace(/^﻿/, ""));
      if (name.endsWith(".geojson") && !Array.isArray(v && v.features)) return "not GeoJSON (no features)";
      if (v === null || typeof v !== "object") return "not a JSON object";
      return null;
    } catch {
      return "not valid JSON";
    }
  }
  return null;
}

/**
 * One file: NAVCEN -> R2. Returns the bytes, or null for a 404. Throws after the retries.
 * deps: { fetch, sleep } (tests replace them).
 */
export async function grab(env, dir, name, files, deps) {
  let last = "";
  for (const wait of [...WAITS_MS, null]) {
    try {
      const r = await deps.fetch(MSI + name, { headers: { "User-Agent": UA, "Accept": "*/*" } });
      if (r.status === 404) return null;
      if (r.ok) {
        const buf = await r.arrayBuffer();
        const bad = looksRight(name, buf);
        if (!bad) {
          const lastModified = r.headers.get("Last-Modified") || "";
          await env.ATON.put(`${dir}/${name}`, buf, { customMetadata: { lastModified } });
          files.push({ name, bytes: buf.byteLength, lastModified });
          return buf;
        }
        last = `HTTP ${r.status} but ${bad}`;
      } else {
        last = `HTTP ${r.status}`;
      }
    } catch (e) {
      last = String(e && e.message || e);
    }
    if (wait === null) break;
    await deps.sleep(wait);
  }
  throw new Error(`${MSI}${name}: ${last}`);
}

async function clearDir(env, dir) {
  let cursor;
  do {
    const list = await env.ATON.list({ prefix: `${dir}/`, cursor });
    const keys = list.objects.map(o => o.key);
    if (keys.length) await env.ATON.delete(keys);
    cursor = list.truncated ? list.cursor : undefined;
  } while (cursor);
}

/** The whole day: returns the _complete.json record, or { skipped } when the day is already complete. */
export async function mirror(env, when, deps) {
  const dir = dayDir(when);
  if (await env.ATON.head(`${dir}/${COMPLETE}`)) return { skipped: `${dir} is already complete` };
  await clearDir(env, dir);
  const files = [];
  const idx = await grab(env, dir, "fileIndexNew.json", files, deps);
  if (!idx) throw new Error("fileIndexNew.json not found (404)");
  const index = JSON.parse(new TextDecoder().decode(idx).replace(/^﻿/, ""));
  const count = p => Number((index[p] || {}).counter) || 0;
  const notices = {};
  for (const p of NOTICE_PRODUCTS) {
    notices[p] = count(p);
    for (let i = 1; i <= count(p); i++)
      if (!await grab(env, dir, `${p}${i}.geojson`, files, deps))
        throw new Error(`${p}${i}.geojson is in fileIndexNew.json but not there`);
  }
  for (const p of CORRECTED_PRODUCTS)
    for (let i = 1; i <= count(p); i++)
      await grab(env, dir, `${p}${i}.geojson`, files, deps);      // a missing one is skipped, as in the build
  const lightList = {};
  for (const d of DISTRICTS) {
    const dd = String(d).padStart(2, "0");
    let n = 0;
    for (;;) {
      if (n >= LIGHT_LIST_MAX_PARTS)
        throw new Error(`district ${d}: more than ${LIGHT_LIST_MAX_PARTS} Light List parts; check the source`);
      if (!await grab(env, dir, `lightListD${dd}_${n + 1}.csv`, files, deps)) break;
      n++;
    }
    if (!n) throw new Error(`no Light List for district ${d} (lightListD${dd}_1.csv not found)`);
    lightList[d] = n;
  }
  const done = { at: new Date(deps.now ? deps.now() : Date.now()).toISOString(), dir, light_list_parts: lightList,
                 notice_parts: notices, files };
  await env.ATON.put(`${dir}/${COMPLETE}`, JSON.stringify(done, null, 1),
                     { httpMetadata: { contentType: "application/json" } });
  return done;
}

export const realDeps = { fetch: (u, i) => fetch(u, i), sleep: ms => new Promise(r => setTimeout(r, ms)) };
