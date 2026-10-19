# QA checklist (on a phone, before a release)

Run with production data (`VmAton.init(apiKey: …)`) on one iPhone and one Android phone. Compare with the
preview (`preview/`, `?api=https://aton.vectormarine.us&key=…&base=vm`) where something looks off: the preview
is the reference. Screenshots of the real data: `docs/img/`.

## Switching on and off

- [ ] Overlays → Buoys & lights on: symbols appear; the note line says "Coast Guard data of <date> · Not for
      navigation".
- [ ] Off: every symbol, ring and label goes; other overlays untouched; the chart unchanged.
- [ ] Change the map style while on: everything comes back on the new style.
- [ ] The overlay sits under the weather overlays and under the chart's labels (`vm-overlays`).
- [ ] No new buttons on the map.

## Symbols and zooms

- [ ] Zoom 6–7: only major lights (e.g. Barnegat, Montauk Point, Cape Henlopen…).
- [ ] Zoom 8: sea buoys and safe water marks appear; zoom 9: the other lighted buoys and lights; zoom 11:
      everything (cans, nuns, daybeacons, private aids).
- [ ] Barnegat Inlet: green lighted buoys 1 and 9 (Fl G 2.5s), red nun 2, green can 3, red lighted buoy 4, the
      breakwater lights 6 and 7, the white-and-orange danger buoys A and B. Same places as the NOAA chart.
- [ ] Symbols the right size: a can about the size of the chart's at zoom 14; not blurry (the right @2x/@3x).
- [ ] From zoom 14: labels like `Fl G 2.5s` / `"1"` beside lighted aids, `"2"` beside unlighted ones; labels never
      hide a symbol.
- [ ] Safe water (red-white with red topmark), preferred channel (banded), isolated danger (black-red), special
      purpose (yellow), regulatory (white-orange with a diamond/circle/square), daybeacons (green square, red
      triangle), ranges (red-white board + flare), racon (magenta ring), virtual AIS (magenta diamond V).

## Status

- [ ] Little Egg Inlet Lighted Buoy 2 (while it's still reported missing): faded symbol, red ring with "!".
- [ ] An aid with its light out: amber ring. A discontinued or relocated aid: grey dashed ring.
- [ ] The ring's aid shows at its zoom even where neighbours are thinned out.

## Card

- [ ] Tap a buoy: name, "Lighted buoy · Light List 900 · Federal aid", light spelled out, range, structure,
      remarks, waterway, district, "Coast Guard data of … Not for navigation."
- [ ] Tap a missing aid: "MISSING since Dec 2, 2025", "Local Notice to Mariners… Coast Guard code: MISSING."
- [ ] Tap where there's no aid: no card; the tap goes to the other overlays.
- [ ] Two aids close together: the one under the finger opens.

## Data and offline

- [ ] Airplane mode, relaunch, switch on: the layer draws from the last copy (symbols + cached tiles); the note
      line still shows the date.
- [ ] With the job stopped for 3 days (or a test server with an old `meta.json`): "Coast Guard data not updated
      for 3 days".
- [ ] A proxy shows only `meta.json`, `style.json`, `icons/…` and tiles (`/aton/{z}/{x}/{y}.mvt?v=…&key=…`):
      nothing about the phone's position or what was tapped.
