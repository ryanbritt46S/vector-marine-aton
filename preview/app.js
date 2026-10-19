// app.js - Buoys & lights as the app shows it, on the real files from the Worker (or serve.mjs, which runs the
// Worker's code on build/site): the overlay's style.json source and layers, the symbols from icons.json, the tap
// card, the data date and "Not for navigation".
// URL options: ?api=http://localhost:8787 (default: this server), ?key=..., ?base=plain|osm|vm, ?on=1,
// ?at=lon,lat,zoom, ?aid=<id> (open that aid's card once it's on screen), ?now=2026-10-19T16:00:00Z (a fixed clock),
// ?wide=1 (a tablet-sized frame, for screenshots).
import * as A from "./aton.js";

const $ = id => document.getElementById(id);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode: fine */ } },
};
const params = new URLSearchParams(location.search);
const API = (params.get("api") || store.get("vm.aton.api") || location.origin).replace(/\/+$/, "");
const KEY = params.get("key") ?? store.get("vm.key") ?? "";
const BASE = params.get("base") || "plain";
const CHART = "https://tiles.vectormarine.us";
const LAYERS = ["vm-aton-status", "vm-aton-symbols", "vm-aton-labels"];

const S = { on: false, meta: null, style: null, icons: null, error: null, ready: false, card: null,
            nowMs: params.get("now") ? Date.parse(params.get("now")) : null, images: [] };
const nowMs = () => S.nowMs ?? Date.now();
const url = path => `${API}/${path}${KEY ? `${path.includes("?") ? "&" : "?"}key=${encodeURIComponent(KEY)}` : ""}`;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ratio = () => (devicePixelRatio >= 2.5 ? 3 : devicePixelRatio >= 1.5 ? 2 : 1);

// ------------------------------------------------------------------------------------------------- map

function baseStyle() {
  if (BASE === "vm" && KEY) return `${CHART}/styles/bathy-combo.json?key=${encodeURIComponent(KEY)}`;
  const layers = [{ id: "water", type: "background", paint: { "background-color": "#d3e5ef" } }];
  // rough land (GSHHG, pipeline/tools/make_coast.py) when serve.mjs has it: the preview only
  const sources = { land: { type: "geojson", data: `${location.origin}/coast.geojson` } };
  // GSHHG is 100-200 m off and has no small inlets: shown only zoomed out, where that doesn't mislead
  layers.push({ id: "land", type: "fill", source: "land", maxzoom: 13, filter: ["==", ["get", "level"], 1],
                paint: { "fill-color": "#efe8d8", "fill-outline-color": "#b8aa8c", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 12.3, 1, 13, 0] } },
              { id: "lakes", type: "fill", source: "land", maxzoom: 13, filter: ["==", ["get", "level"], 2], paint: { "fill-color": "#d3e5ef" } });
  if (BASE === "osm") {
    sources.osm = { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256,
                    attribution: "© OpenStreetMap contributors", maxzoom: 19 };
    layers.push({ id: "osm", type: "raster", source: "osm", paint: { "raster-saturation": -0.6, "raster-opacity": 0.85 } });
  }
  // the app's map styles end with an invisible "vm-overlays" layer: overlays go under it (labels, buttons on top)
  layers.push({ id: "vm-overlays", type: "background", layout: { visibility: "none" }, paint: { "background-color": "#000" } });
  return { version: 8, glyphs: `${location.origin}/fonts/{fontstack}/{range}.pbf`, sources, layers };
}

const at = (params.get("at") || "").split(",").map(Number);
const map = new maplibregl.Map({ container: "map", style: baseStyle(),
  center: at.length === 3 && at.every(Number.isFinite) ? [at[0], at[1]] : [-74.1, 39.75],
  zoom: at.length === 3 && at.every(Number.isFinite) ? at[2] : 11, attributionControl: { compact: true }, fadeDuration: 0 });
window.__map = map;
if (params.get("wide") === "1") { $("phone").classList.add("wide"); map.resize(); }
// the attribution folded to its (i) button, like the app's map: the credit is in the note line and the card
map.on("idle", () => document.querySelector(".maplibregl-compact-show")?.classList.remove("maplibregl-compact-show"));
const anchor = () => (map.getLayer("vm-overlays") ? "vm-overlays" : undefined);

async function getJSON(path) {
  const r = await fetch(url(path), { cache: "no-cache" });
  if (!r.ok) throw new Error(r.status === 401 ? "the server wants an API key (401)" : `HTTP ${r.status} for ${path}`);
  return r.json();
}

async function loadImage(path) {
  const r = await fetch(url(path));
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`);
  return createImageBitmap(await r.blob());
}

/** meta.json, style.json and icons.json (the app keeps the last copy for offline). */
async function load() {
  try {
    const [meta, style, icons] = await Promise.all([getJSON("meta.json"), getJSON("style.json"), getJSON("icons/icons.json")]);
    if (meta.version !== 1) throw new Error(`meta version ${meta.version} is newer than this preview`);
    Object.assign(S, { meta, style, icons, error: null });
  } catch (e) {
    S.error = String(e.message || e);
  }
  info();
}

async function addOverlay() {
  if (!S.on || !S.style || !S.icons || map.getSource("vm-aton")) return;
  const r = ratio(), prefix = S.icons.prefix;
  await Promise.all(Object.entries(S.icons.icons).map(async ([sym, ic]) => {
    const img = await loadImage(ic.files[String(r)]);
    if (!map.hasImage(prefix + sym)) map.addImage(prefix + sym, img, { pixelRatio: r });
    S.images.push(prefix + sym);
  }));
  if (!S.on || map.getSource("vm-aton")) return;
  for (const [id, src] of Object.entries(S.style.sources)) map.addSource(id, src);
  for (const l of S.style.layers) map.addLayer(l, anchor());
  S.ready = true;
  render();
}

function removeOverlay() {
  for (const id of [...LAYERS].reverse()) if (map.getLayer(id)) map.removeLayer(id);
  for (const id of Object.keys(S.style?.sources || {})) if (map.getSource(id)) map.removeSource(id);
  for (const n of S.images) if (map.hasImage(n)) map.removeImage(n);
  S.images = [];
  S.ready = false;
}

async function setOn(on) {
  S.on = on;
  $("atonSwitch").setAttribute("aria-checked", String(on));
  if (!on) { removeOverlay(); closeCard(); render(); return; }
  if (!S.meta) await load();
  if (map.isStyleLoaded()) await addOverlay(); else map.once("load", addOverlay);
  render();
}

// ------------------------------------------------------------------------------------------------ taps

function nearest(point, feats) {
  let best = null, bd = Infinity;
  for (const f of feats) {
    const p = map.project(f.geometry.coordinates);
    const d = (p.x - point.x) ** 2 + (p.y - point.y) ** 2 - (f.properties.rank || 0) * 1e-3;
    if (d < bd) { bd = d; best = f; }
  }
  return best;
}

map.on("click", e => {
  if (!S.ready) return;
  const b = 14;
  const feats = map.queryRenderedFeatures([[e.point.x - b, e.point.y - b], [e.point.x + b, e.point.y + b]],
    { layers: LAYERS.filter(id => map.getLayer(id)) });
  const f = feats.length ? nearest(e.point, feats) : null;
  if (f) openCard(f.properties); else closeCard();
});

function openCard(props) {
  S.card = props;
  const c = A.card(props, S.meta?.data_date);
  const icon = S.icons?.icons?.[props.sym]?.files?.["2"];
  $("cardBody").innerHTML = `
    <div class="c-title">${icon ? `<img alt="" src="${esc(url(icon))}">` : ""}<span>${esc(c.title)}</span></div>
    <div class="c-sub">${esc(c.subtitle)}</div>
    ${c.status ? `<div class="c-status ${esc(props.status)}">${esc(c.status)}<small>${esc(c.status_note)}</small></div>` : ""}
    <dl class="c-rows">${c.rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    ${c.unlisted ? `<div class="c-unlisted">${esc(c.unlisted)}</div>` : ""}
    <div class="c-foot">${esc(c.footer)}</div>`;
  $("card").classList.add("on");
  $("card").dataset.seq = String(Number($("card").dataset.seq || 0) + 1);
  $("card").dataset.id = props.id;
}

function closeCard() {
  S.card = null;
  $("card").classList.remove("on");
  $("card").dataset.seq = String(Number($("card").dataset.seq || 0) + 1);
  delete $("card").dataset.id;
}
$("cardClose").onclick = closeCard;

/** The card of an aid by id, once its tile is loaded (?aid=, tests). */
function openById(id) {
  const f = map.querySourceFeatures("vm-aton", { sourceLayer: "aton", filter: ["==", ["get", "id"], id] })[0];
  if (f) openCard(f.properties);
  return !!f;
}

// ---------------------------------------------------------------------------------------------- panels

function render() {
  const m = S.meta;
  $("sampleBanner").style.display = S.on && m?.sample ? "block" : "none";
  const stale = S.on ? A.staleText(m, nowMs()) : "";
  $("staleBanner").style.display = stale ? "block" : "none";
  $("staleBanner").textContent = stale;
  $("note").classList.toggle("on", S.on && !!m);
  if (m) $("note").textContent = `Buoys & lights · Coast Guard data of ${A.fmtDate(m.data_date)} · Not for navigation`;
}

function info() {
  const m = S.meta;
  if (S.error) { $("info").innerHTML = `<p class="err">${esc(S.error)}</p>`; return; }
  if (!m) return;
  const c = m.counts;
  $("info").innerHTML = `
    <h2>This build</h2>
    <table class="stats">
      <tr><td>Data of</td><td>${esc(A.fmtDate(m.data_date))}${m.sample ? " (SAMPLE)" : ""}</td></tr>
      <tr><td>Aids</td><td>${c.aids.toLocaleString("en-US")} (${Object.entries(m.districts).map(([d, v]) => `D${d} ${v.aids.toLocaleString("en-US")}`).join(", ")})</td></tr>
      <tr><td>With a status</td><td>${["missing", "fault", "temporary"].map(s => `${c.by_status[s]} ${s}`).join(", ")}</td></tr>
      <tr><td>Notices</td><td>${c.notices.in_area} in these districts, ${c.notices.unmatched} not in the Light List</td></tr>
      <tr><td>Tiles</td><td>${(m.tiles.bytes / 1e6).toFixed(1)} MB, version ${esc(m.tiles.version)}</td></tr>
    </table>`;
  const ic = S.icons?.icons || {};
  const img = sym => (ic[sym] ? `<img alt="" src="${esc(url(ic[sym].files["2"]))}">` : "");
  $("rings").innerHTML = ["missing", "fault", "temporary"].map(s =>
    `<div>${img(`badge-${s}`)}<span>${esc(A.SEVERITY_WORDS[s])}</span></div>`).join("");
  $("legend").innerHTML = Object.entries(ic).filter(([s]) => !s.startsWith("badge-") && (c.by_sym[s] || m.sample))
    .map(([s, v]) => `<div title="${esc(v.title)}">${img(s)}<span>${esc(v.title.split(" (")[0])} <small>${c.by_sym[s] || 0}</small></span></div>`).join("");
}

$("overlaysBtn").onclick = () => {
  const open = !$("sheet").classList.contains("open");
  $("sheet").classList.toggle("open", open);
  $("overlaysBtn").setAttribute("aria-expanded", String(open));
};
$("atonSwitch").onclick = () => setOn(!S.on);

window.__aton = { S, A, ready: () => S.ready, openById, openCard, closeCard };

if (params.get("on") === "1") {
  setOn(true).then(() => {
    const aid = params.get("aid");
    if (!aid) return;
    const tryOpen = () => { if (!openById(aid)) map.once("idle", tryOpen); };
    map.once("idle", tryOpen);
  });
} else {
  load();
}
