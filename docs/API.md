# API: what the vm-aton Worker serves

`https://aton.vectormarine.us` (Worker `vm-aton`, bucket `vm-aton`). Every request needs an API key
(`X-API-Key: …` header, or `?key=…`), the same keys as the tiles Worker; `/health` doesn't. GET and HEAD only.
ETag + `If-None-Match` → 304. CORS: `ALLOWED_ORIGINS`.

| Path | What | Cache |
|---|---|---|
| `/meta.json` | When the data is from, counts, the tiles' and icons' versions | 5 min, never at the edge |
| `/style.json` | The overlay's sources and layers (MapLibre style fragment); `{base}` filled in with this Worker (plus `?key=` when the request had one) | 5 min |
| `/aton.json` | TileJSON 3.0.0: `tiles` = this Worker's tile URL with `?v=<version>` (and `&key=` when the request had one) | 5 min |
| `/aton/{z}/{x}/{y}.mvt` | One vector tile out of `aton.pmtiles` (range reads); 204 where there are no aids or outside z6–14 | with the current `?v=`: 30 days, immutable; else 5 min. At the edge, keyed by version |
| `/icons/<sym>.png`, `<sym>@2x.png`, `<sym>@3x.png` | One symbol | 1 day, at the edge |
| `/icons/icons.json` | Every symbol and its files | 5 min |
| `/health` | `ok` | |

Anything else is 404 (never `uploads.json` or other keys). `PUBLIC_URL` (optional var) replaces the request's
own address in `style.json` and `aton.json` (`worker/dev_local.sh` sets it: `wrangler dev` rewrites the host).

**This is a contract with installed apps.** Only add fields and routes. Anything that would break an app needs
`version: 2` in a new `meta.json` the old apps don't read, both sides updated, and this file.

## meta.json

```jsonc
{
  "version": 1, "layer": "aton", "sample": false, "title": "Buoys & lights",
  "generated_at": "2026-10-19T10:20:00Z", "run": "20261019T1020Z",
  "data_date": "2026-10-19",            // the newest of the two below (New York date)
  "light_list_date": "2026-10-19",      // the Light List files' Last-Modified
  "notices_date": "2026-10-19",         // fileIndexNew.json's timestamps of the notice files
  "stale_after_hours": 72,              // "Coast Guard data not updated for N days" past this
  "attribution": "Aids to navigation: U.S. Coast Guard Light List and Local Notice to Mariners (NAVCEN)",
  "note": "Not for navigation. …",
  "districts": {"1": {"name": "First District: …", "aids": 9218, "light_list_parts": 10}, "5": {…}, "7": {…}},
  "counts": {
    "aids": 32445, "listed": 32421, "unlisted": 24, "skipped_no_position": 0,
    "by_kind": {"buoy": 7985, …}, "by_sym": {"can-g": 3311, …},
    "by_status": {"missing": 1654, "fault": 773, "temporary": 209},
    "notices": {"nationwide": 4787, "in_area": 2699, "matched_by_number": 2669, "matched_by_name": 2,
                "unmatched": 28, "matched_far": 2, "corrected_in_area": 79,
                "parts": {"discFedAid_": 3, "discPriAid_": 3, "tmpChange_": 1}}
  },
  "tiles": {"file": "aton.pmtiles", "layer": "aton", "minzoom": 6, "maxzoom": 14,
            "version": "61c602a61b8f",  // SHA-256 of the tiles (12 hex): same aids, same version
            "bytes": 12853938, "tiles": 17886, "bounds": [w, s, e, n]},
  "icons": {"file": "icons/icons.json", "version": "c57dd93a222b", "count": 63},
  "style": "style.json",
  "source": "https://navcen.uscg.gov/sites/default/files/msi/",
  "sources": [{"file": "lightListD01_1.csv", "bytes": 279634, "modified": "2026-10-19T15:26:00Z"}, …]
}
```

## The tiles (aton.pmtiles, layer `aton`)

PMTiles v3, MVT, gzip, z6–14 (MapLibre over-zooms past 14), extent 4096, one point per aid. Properties (empty
ones are left out):

| Property | Type | What |
|---|---|---|
| `id` | string | `<district>-<llnr>` (`5-900`); a number listed twice gets `-2`; an aid only a notice knows `<district>-n<notice id>` |
| `llnr` | string | Light List number (`900`, `5400.1`) |
| `name` | string | `Barnegat Inlet Lighted Buoy 1` |
| `sym` | string | Symbol id (`docs/SPEC.md`): the image is `vm-aton-<sym>` |
| `kind` | string | `major_light`, `light`, `lighted_buoy`, `buoy`, `daybeacon`, `range_light`, `range_daybeacon`, `directional_light`, `articulated_light`, `racon`, `virtual_ais`, `sound_signal`, `other` |
| `color` | string | The colour code (`G`, `R`, `RW`, `WO`, `RGR`…), from `COLOR` or the structure text |
| `char` | string | Light characteristic as listed (`Fl G 2.5s`) |
| `range` | number | Nominal range, NM |
| `height` | number | Focal plane height, ft |
| `structure`, `remark`, `waterway` | string | As listed |
| `private` | bool | `AID_TYPE` PA |
| `district` | number | 1, 5 or 7 |
| `status` | string | `missing`, `fault` or `temporary` (absent: no current notice) |
| `status_text` | string | Plain words: `Missing`, `Light out; structure damaged` |
| `status_since` | string | `2025-12-02`: when the first notice of the worst problem was created (New York date) |
| `status_raw` | string | The Coast Guard's codes, `; ` between notices (`STRUCT DEST/TRUB; RELOCATED FOR DREDGING`) |
| `bnm` | string | Broadcast notice number(s) |
| `num` | string | The aid's number from its name (`1`, `2M`, `BI`) |
| `label` | string | `Fl G 2.5s\n"1"` (what the z14+ label shows) |
| `rank` | number | Importance (drawing order, thinning; +100/+200/+300 with a status) |
| `listed` | bool | `false` only for an aid that's not in the Light List |

## style.json

```jsonc
{
  "version": 1, "id": "vm-aton", "name": "Buoys & lights", "anchor": "vm-overlays",
  "tiles_version": "61c602a61b8f", "icons_version": "c57dd93a222b", "image_prefix": "vm-aton-",
  "attribution": "…",
  "sources": {
    "vm-aton":      {"type": "vector", "url": "https://aton.vectormarine.us/aton.json", "minzoom": 6, "maxzoom": 14, "attribution": "…"},
    "vm-aton-text": {"type": "vector", "url": "https://aton.vectormarine.us/aton.json", "minzoom": 6, "maxzoom": 14}
  },
  "layers": [
    {"id": "vm-aton-status",  "type": "symbol", "source": "vm-aton", "source-layer": "aton", "filter": ["has", "status"],
     "layout": {"icon-image": ["concat", "vm-aton-badge-", ["get", "status"]], "icon-size": [...], ...}, "paint": {}},
    {"id": "vm-aton-symbols", "type": "symbol", "source": "vm-aton", "source-layer": "aton",
     "layout": {"icon-image": ["concat", "vm-aton-", ["get", "sym"]], ...}, "paint": {"icon-opacity": [...]}},
    {"id": "vm-aton-labels",  "type": "symbol", "source": "vm-aton-text", "source-layer": "aton", "minzoom": 14,
     "filter": ["has", "label"], "layout": {"text-field": ["get", "label"], "text-font": ["Noto Sans Regular"], ...}, "paint": {...}}
  ]
}
```

Add the layers in this order under `anchor`. The app builds its own tile URL (`AtonApi.tileUrl`) with the key
in it: native MapLibre can't send headers for tiles.

## icons/icons.json

```jsonc
{"version": "c57dd93a222b", "size": 48, "anchor": "center", "pixel_ratios": [1, 2, 3], "prefix": "vm-aton-",
 "icons": {"lb-g": {"title": "Green lighted buoy", "files": {"1": "icons/lb-g.png", "2": "icons/lb-g@2x.png", "3": "icons/lb-g@3x.png"}},
           …, "badge-missing": {…}, "badge-fault": {…}, "badge-temporary": {…}}}
```

Each PNG is 48 × 48 points (48, 96 or 144 pixels) with the aid's position at the centre. Add it as
`vm-aton-<sym>` at its pixel ratio.
