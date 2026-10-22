// The daily NAVCEN copy (src/mirror.js), with a stand-in bucket and a stand-in NAVCEN serving the real files
// cut for the pipeline's tests (pipeline/tests/fixtures/real/). No network.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import worker from "../src/index.js";
import * as M from "../src/mirror.js";

const REAL = fileURLToPath(new URL("../../pipeline/tests/fixtures/real/", import.meta.url));
const CFG = JSON.parse(readFileSync(fileURLToPath(new URL("../../pipeline/config/aton.json", import.meta.url)), "utf8"));
const NAVCEN = Object.fromEntries(readdirSync(REAL).map(f => [f, new Uint8Array(readFileSync(REAL + f))]));
const LM = "Mon, 19 Oct 2026 06:00:00 GMT";
const WHEN = Date.parse("2026-10-21T10:20:00Z");
const DIR = "raw/2026-10-21";

function bucket(start = {}) {
  const objs = new Map(Object.entries(start).map(([k, v]) => [k, { body: v, meta: {} }]));
  return {
    objs,
    async put(key, body, opts = {}) {
      const b = typeof body === "string" ? new TextEncoder().encode(body) : new Uint8Array(body);
      objs.set(key, { body: b, meta: opts.customMetadata || {} });
    },
    async head(key) { return objs.has(key) ? { key } : null; },
    async get(key) { const o = objs.get(key); return o ? { text: async () => new TextDecoder().decode(o.body) } : null; },
    async list({ prefix }) {
      return { objects: [...objs.keys()].filter(k => k.startsWith(prefix)).map(key => ({ key })), truncated: false };
    },
    async delete(keys) { for (const k of [].concat(keys)) objs.delete(k); },
  };
}

// a stand-in NAVCEN: the real files, 404 for anything else; `script` overrides answers per file name (a list is
// used up one by one, the last answer repeats)
function navcen(script = {}) {
  const asked = [];
  const deps = {
    asked,
    sleeps: [],
    sleep: async ms => { deps.sleeps.push(ms); },
    now: () => Date.parse("2026-10-21T10:21:00Z"),
    fetch: async (url, init) => {
      const name = url.slice(M.MSI.length);
      asked.push(name);
      assert.equal(init.headers["User-Agent"], M.UA);
      const s = script[name];
      if (s) {
        const a = s.length > 1 ? s.shift() : s[0];
        if (a instanceof Error) throw a;
        return new Response(a.body ?? null, { status: a.status, headers: a.headers });
      }
      const b = NAVCEN[name];
      return b ? new Response(b, { status: 200, headers: { "Last-Modified": LM } }) : new Response("nope", { status: 404 });
    },
  };
  return deps;
}

test("the lists match pipeline/config/aton.json", () => {
  assert.equal(M.MSI, CFG.base_url);
  assert.deepEqual(M.DISTRICTS, CFG.districts);
  assert.deepEqual(M.NOTICE_PRODUCTS, CFG.notice_products);
  assert.deepEqual(M.CORRECTED_PRODUCTS, CFG.corrected_products);
  assert.equal(M.LIGHT_LIST_MAX_PARTS, CFG.light_list_max_parts);
});

test("a full day: every file copied with its Last-Modified, parts probed until a 404, _complete.json last", async () => {
  const env = { ATON: bucket() };
  const deps = navcen();
  const r = await M.mirror(env, WHEN, deps);
  assert.equal(r.dir, DIR);
  assert.deepEqual(r.light_list_parts, { 1: 1, 5: 1, 7: 1 });
  assert.deepEqual(r.notice_parts, { discFedAid_: 1, discPriAid_: 1, tmpChange_: 1 });
  for (const f of Object.keys(NAVCEN)) {
    const o = env.ATON.objs.get(`${DIR}/${f}`);
    assert.ok(o, f);
    assert.deepEqual(o.body, NAVCEN[f]);
    assert.equal(o.meta.lastModified, LM);
  }
  assert.ok(deps.asked.includes("lightListD01_2.csv"));             // the probe that ended district 1
  assert.ok(!deps.asked.includes("discPriAidCor_1.geojson"));        // counter 0 in the index
  const keys = [...env.ATON.objs.keys()];
  assert.equal(keys[keys.length - 1], `${DIR}/_complete.json`);     // written last
  const done = JSON.parse(new TextDecoder().decode(env.ATON.objs.get(`${DIR}/_complete.json`).body));
  assert.equal(done.files.length, Object.keys(NAVCEN).length);
  assert.equal(done.at, "2026-10-21T10:21:00.000Z");
});

test("retry run: nothing is fetched when the day is already complete", async () => {
  const env = { ATON: bucket({ [`${DIR}/_complete.json`]: new Uint8Array([123, 125]) }) };
  const deps = navcen();
  const r = await M.mirror(env, WHEN, deps);
  assert.match(r.skipped, /already complete/);
  assert.equal(deps.asked.length, 0);
});

test("a stale part from an earlier failed try is cleared first", async () => {
  const env = { ATON: bucket({ [`${DIR}/lightListD01_2.csv`]: new Uint8Array([1]), "meta.json": new Uint8Array([2]) }) };
  await M.mirror(env, WHEN, navcen());
  assert.ok(!env.ATON.objs.has(`${DIR}/lightListD01_2.csv`));
  assert.ok(env.ATON.objs.has("meta.json"));                          // only the day's folder
});

test("a 503 is tried again (2, 6, 18 s); a 403 every time fails without _complete.json", async () => {
  const deps = navcen({ "lightListD05_1.csv": [{ status: 503 }, { status: 503 }, { status: 200, body: NAVCEN["lightListD05_1.csv"] }] });
  const env = { ATON: bucket() };
  await M.mirror(env, WHEN, deps);
  assert.deepEqual(deps.sleeps, [2000, 6000]);
  const env2 = { ATON: bucket() };
  const deps2 = navcen({ "fileIndexNew.json": [{ status: 403 }] });
  await assert.rejects(M.mirror(env2, WHEN, deps2), /fileIndexNew\.json: HTTP 403/);
  assert.equal(deps2.asked.length, 4);
  assert.ok(![...env2.ATON.objs.keys()].some(k => k.endsWith("_complete.json")));
});

test("a challenge page sent with a 200 is not accepted as the file", async () => {
  const html = "<!DOCTYPE html><html><head><title>Just a moment...</title></head></html>";
  const env = { ATON: bucket() };
  await assert.rejects(M.mirror(env, WHEN, navcen({ "lightListD07_1.csv": [{ status: 200, body: html }] })),
                       /lightListD07_1\.csv: HTTP 200 but not a Light List CSV/);
  await assert.rejects(M.mirror({ ATON: bucket() }, WHEN, navcen({ "discFedAid_1.geojson": [{ status: 200, body: html }] })),
                       /discFedAid_1\.geojson: HTTP 200 but not valid JSON/);
  assert.ok(![...env.ATON.objs.keys()].some(k => k.endsWith("_complete.json")));
});

test("a listed notice part that's missing fails; a missing corrected part is skipped", async () => {
  await assert.rejects(M.mirror({ ATON: bucket() }, WHEN, navcen({ "tmpChange_1.geojson": [{ status: 404 }] })),
                       /tmpChange_1\.geojson is in fileIndexNew\.json but not there/);
  const env = { ATON: bucket() };
  const r = await M.mirror(env, WHEN, navcen({ "discFedAidCor_1.geojson": [{ status: 404 }] }));
  assert.ok(env.ATON.objs.has(`${DIR}/_complete.json`));
  assert.ok(!r.files.some(f => f.name === "discFedAidCor_1.geojson"));
});

test("no Light List for a district, or more parts than allowed, fails", async () => {
  await assert.rejects(M.mirror({ ATON: bucket() }, WHEN, navcen({ "lightListD07_1.csv": [{ status: 404 }] })),
                       /no Light List for district 7/);
  const many = {};
  for (let i = 1; i <= 41; i++) many[`lightListD01_${i}.csv`] = [{ status: 200, body: NAVCEN["lightListD01_1.csv"] }];
  await assert.rejects(M.mirror({ ATON: bucket() }, WHEN, navcen(many)), /district 1: more than 40 Light List parts/);
});

test("the Worker's scheduled() handler is wired to the mirror", async () => {
  assert.equal(typeof worker.scheduled, "function");
  const env = { ATON: bucket({ [`${DIR}/_complete.json`]: new Uint8Array([123, 125]) }) };
  const log = console.log; const lines = [];
  console.log = (...a) => lines.push(a.join(" "));
  try { await worker.scheduled({ scheduledTime: WHEN, cron: "20 10 * * *" }, env, { waitUntil() {} }); }
  finally { console.log = log; }
  assert.match(lines.join("\n"), /already complete/);                // the complete day isn't fetched again
});

test("the fetch routes don't serve raw/", async () => {
  const env = { ATON: bucket({ [`${DIR}/fileIndexNew.json`]: NAVCEN["fileIndexNew.json"] }) };
  for (const p of [`/${DIR}/fileIndexNew.json`, "/raw/", `/icons/../${DIR}/fileIndexNew.json`]) {
    const r = await worker.fetch(new Request(`https://aton.example${p}?key=k`), { ...env, API_KEYS: "k" }, { waitUntil() {} });
    assert.equal(r.status, 404, p);
  }
});
