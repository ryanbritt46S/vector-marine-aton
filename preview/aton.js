// aton.js - the words of Buoys & lights in JS: status codes in plain English, the light characteristic spelled
// out, kinds, dates, the tap card. The same functions as pipeline/vmaton/words.py (the reference) and
// flutter/vm_aton/lib/src/words.dart; test/aton.test.mjs checks them against the parity fixture
// (flutter/vm_aton/test/fixtures/words.json). No map code here.

export const RANK = { missing: 3, fault: 2, temporary: 1 };

export const SEVERITY_WORDS = {
  missing: "Missing, off station or destroyed",
  fault: "Light out or damaged",
  temporary: "Temporary change",
};

export const STATUS_CODES = {
  "MISSING": ["Missing", "missing"],
  "OFF STATION": ["Off station", "missing"],
  "OFF STA": ["Off station", "missing"],
  "STRUCT DEST": ["Structure destroyed", "missing"],
  "STRUCT MISSING": ["Structure missing", "missing"],
  "SINKING": ["Sinking", "missing"],
  "ADRIFT": ["Adrift", "missing"],
  "HAZ NAV": ["Hazard to navigation", "missing"],
  "LT EXT": ["Light out", "fault"],
  "LT IMCH": ["Light not showing as listed", "fault"],
  "REDUCED INT": ["Light at reduced intensity", "fault"],
  "NIGHT LT BURNING DAY": ["Light burning in daytime", "fault"],
  "MSLD SIG": ["Misleading signal", "fault"],
  "STRUCT DMGD": ["Structure damaged", "fault"],
  "BUOY DMGD": ["Buoy damaged", "fault"],
  "LEANING": ["Leaning", "fault"],
  "DAYMK MISSING": ["Daymark missing", "fault"],
  "DAYMK DMGD": ["Daymark damaged", "fault"],
  "DAYMK IMCH": ["Daymark not as listed", "fault"],
  "DBD DEST": ["Dayboard destroyed", "fault"],
  "DBD DMGD": ["Dayboard damaged", "fault"],
  "TMK MISSING": ["Topmark missing", "fault"],
  "VEGETATION": ["Hidden by vegetation", "fault"],
  "SS INOP": ["Sound signal not working", "fault"],
  "SS IMCH": ["Sound signal not as listed", "fault"],
  "RAC INOP": ["Racon not working", "fault"],
  "AIS INOP": ["AIS not working", "fault"],
  "AIS IMCH": ["AIS not as listed", "fault"],
  "RBN IMCH": ["Radiobeacon not as listed", "fault"],
  "OTHER DISC AIDS IN AREA": ["Other aids nearby also reported", "fault"],
  "STATUS UNREPORTED": ["Status not reported", "fault"],
  "TRLB": ["Temporarily replaced by a lighted buoy", "temporary"],
  "TRUB": ["Temporarily replaced by an unlighted buoy", "temporary"],
  "TRLT": ["Temporarily replaced by a light", "temporary"],
  "TRDBN": ["Temporarily replaced by a daybeacon", "temporary"],
  "TRSAIS": ["Temporarily replaced by a synthetic AIS aid", "temporary"],
  "DISCONTINUED": ["Discontinued", "temporary"],
  "DISCONTINUED FOR DREDGING": ["Discontinued for dredging", "temporary"],
  "RELOCATED": ["Relocated", "temporary"],
  "RELOCATED FOR DREDGING": ["Relocated for dredging", "temporary"],
  "ESTABLISHED": ["Temporarily established", "temporary"],
  "OTHER": ["Temporary change", "temporary"],
};
const DEFAULT_SEVERITY = { disc: "fault", tmp: "temporary" };

const squash = s => String(s).trim().replace(/\s+/g, " ");

/** 'LT IMCH/STRUCT DMGD' -> [['LT IMCH', 'Light not showing as listed', 'fault'], ...]; unknown codes kept raw. */
export function decodeCodes(raw, product = "disc") {
  const out = [];
  for (const part of String(raw ?? "").split("/")) {
    const code = squash(part);
    if (!code) continue;
    const hit = STATUS_CODES[code.toUpperCase()];
    out.push(hit ? [code, hit[0], hit[1]] : [code, code, DEFAULT_SEVERITY[product] || "fault"]);
  }
  return out;
}

/** ['Structure destroyed', 'Temporarily replaced …'] -> 'Structure destroyed; temporarily replaced …' */
export function joinWords(words) {
  const out = [];
  for (let w of words) {
    if (out.length && w.length > 1 && isUpper(w[0]) && isLower(w[1])) w = w[0].toLowerCase() + w.slice(1);
    out.push(w);
  }
  return out.join("; ");
}
const isUpper = c => c !== c.toLowerCase() && c === c.toUpperCase();
const isLower = c => c !== c.toUpperCase() && c === c.toLowerCase();

export function worst(severities) {
  let best = "";
  for (const s of severities) if ((RANK[s] || 0) > (RANK[best] || 0)) best = s;
  return best;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** '2025-12-02' -> 'Dec 2, 2025' */
export function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  return m ? `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}` : "";
}

/** ('Missing', '2025-12-02') -> 'MISSING since Dec 2, 2025' */
export function statusLine(text, since) {
  if (!text) return "";
  const d = fmtDate(since);
  return d ? `${text.toUpperCase()} since ${d}` : text.toUpperCase();
}

const LIGHT_KINDS = { F: "fixed", FL: "flashing", LFL: "long flashing", Q: "quick flashing", VQ: "very quick flashing",
  IQ: "interrupted quick flashing", ISO: "isophase", OC: "occulting", MO: "Morse code", FFL: "fixed and flashing" };
const COLOURS = { W: "white", R: "red", G: "green", Y: "yellow", BU: "blue" };
const LIGHT_RE = /^(AL\.?\s+)?(FFL|LFL|FL|VQ|IQ|Q|ISO|OC|MO|F)\s*(\([^()]{1,8}\))?\s*((?:(?:BU|W|R|G|Y)\s*)*)\s*(?:(\d{1,3}(?:\.\d{1,2})?)\s*S(?:EC)?)?$/;

export function andList(items) {
  return items.length <= 1 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** 5 -> '5', 2.5 -> '2.5' */
export function num(v) {
  if (v === null || v === undefined || v === "") return "";
  const f = Number(v);
  return Number.isInteger(f) ? String(f) : f.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

/** 'Fl G 4s' -> 'flashing green, every 4 s'; null when it can't be read. */
export function lightWords(char) {
  const s = squash(char ?? "").toUpperCase();
  if (!s) return null;
  const m = LIGHT_RE.exec(s);
  if (!m) return null;
  const [, alt, kind, group, cols, period] = m;
  const colours = (cols || "").match(/BU|W|R|G|Y/g) || [];
  if (!colours.length) return null;
  let k = LIGHT_KINDS[kind];
  if (group) {
    const g = group.replace(/ /g, "");
    if (kind === "MO") k = `Morse code ${g}`;
    else if (g.includes("+")) k = `composite group ${k} ${g}`;
    else k = `group ${k} ${g}`;
  }
  if (alt) k = `alternating ${k}`;
  let words = `${k} ${andList(colours.map(c => COLOURS[c]))}`;
  if (period) words += `, every ${num(period)} s`;
  return words;
}

export const KIND_WORDS = {
  major_light: "Major light", light: "Light", lighted_buoy: "Lighted buoy", buoy: "Buoy", daybeacon: "Daybeacon",
  range_light: "Range light", range_daybeacon: "Range daybeacon", directional_light: "Directional light",
  articulated_light: "Articulated light", racon: "Racon (radar beacon)", virtual_ais: "Virtual AIS aid",
  sound_signal: "Sound signal", other: "Aid to navigation",
};
export const kindWords = kind => KIND_WORDS[kind || ""] ?? KIND_WORDS.other;

const has = v => v !== null && v !== undefined && v !== "";
const str = v => (v === null || v === undefined ? "" : String(v)).trim();

/** The tap card from an aid's tile properties: {title, subtitle, status, status_note, rows, unlisted, footer}. */
export function card(p, dataDate = null) {
  const sub = [kindWords(p.kind)];
  if (p.llnr) sub.push(`Light List ${p.llnr}`);
  sub.push(p.private ? "Private aid" : "Federal aid");
  const status = statusLine(p.status_text, p.status_since);
  let note = "";
  if (p.status) {
    note = "Local Notice to Mariners";
    if (p.bnm) note += `, broadcast notice ${p.bnm}`;
    if (p.status_raw) note += `. Coast Guard code: ${p.status_raw}`;
    note += ".";
  }
  const rows = [];
  const char = str(p.char);
  if (char) {
    const w = lightWords(char);
    rows.push(["Light", w ? `${char} (${w})` : char]);
  }
  if (has(p.range)) rows.push(["Range", `${num(p.range)} NM`]);
  if (has(p.height)) rows.push(["Height", `${num(p.height)} ft`]);
  for (const [label, key] of [["Structure", "structure"], ["Remarks", "remark"], ["Waterway", "waterway"]]) {
    if (str(p[key])) rows.push([label, str(p[key])]);
  }
  if (p.district) rows.push(["District", `Coast Guard District ${p.district}`]);
  const listed = "listed" in p ? p.listed : true;
  const d = fmtDate(dataDate);
  return {
    title: p.name || "Aid to navigation", subtitle: sub.join(" · "), status, status_note: note, rows,
    unlisted: listed ? "" : "Not in the current Light List: shown where the notice puts it.",
    footer: (d ? `Coast Guard data of ${d}. ` : "") + "Not for navigation.",
  };
}

/** "Coast Guard data not updated for 3 days" when meta.json is older than stale_after_hours, else "". */
export function staleText(meta, nowMs) {
  if (!meta || !meta.generated_at) return "";
  const hours = (nowMs - Date.parse(meta.generated_at)) / 3600000;
  if (hours <= (meta.stale_after_hours || 72)) return "";
  const days = Math.floor(hours / 24);
  return `Coast Guard data not updated for ${days} day${days === 1 ? "" : "s"}`;
}
