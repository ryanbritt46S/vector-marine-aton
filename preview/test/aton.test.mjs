// aton.js against the parity fixture written from the Python reference (pipeline/tools/make_parity.py ->
// flutter/vm_aton/test/fixtures/words.json). flutter/vm_aton/test/words_test.dart checks the same file.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as A from "../aton.js";

const FX = JSON.parse(readFileSync(new URL("../../flutter/vm_aton/test/fixtures/words.json", import.meta.url)));

test("status codes", () => {
  for (const c of FX.codes) assert.deepEqual(A.decodeCodes(c.raw, c.product), c.result, `${c.raw} (${c.product})`);
  for (const j of FX.join) assert.equal(A.joinWords(j.words), j.result);
  assert.deepEqual(A.SEVERITY_WORDS, FX.severity_words);
  assert.equal(A.worst(["temporary", "missing", "fault"]), "missing");
});

test("light characteristics, dates, kinds, numbers", () => {
  for (const l of FX.lights) assert.equal(A.lightWords(l.char), l.result, l.char);
  for (const d of FX.dates) assert.equal(A.fmtDate(d.date), d.result, d.date);
  for (const s of FX.status_lines) assert.equal(A.statusLine(s.text, s.since), s.result);
  for (const k of FX.kinds) assert.equal(A.kindWords(k.kind), k.result, k.kind);
  for (const n of FX.nums) assert.equal(A.num(n.value), n.result, String(n.value));
  for (const s of FX.stale) assert.equal(A.staleText(s.meta, s.now_ms), s.result, String(s.now_ms));
});

test("tap cards", () => {
  assert.ok(FX.cards.length > 100);
  for (const c of FX.cards) assert.deepEqual(A.card(c.props, c.data_date), c.result, c.props.id);
  // without the empty values (as they come out of a tile)
  for (const c of FX.cards) {
    const p = Object.fromEntries(Object.entries(c.props).filter(([, v]) => v !== null && v !== ""));
    assert.deepEqual(A.card(p, c.data_date), c.result, c.props.id);
  }
});
