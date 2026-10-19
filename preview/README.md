# Preview

Buoys & lights as the app shows it, as a web page on the real files: a phone frame with the Overlays switch, the
symbols and status rings from `style.json` and `icons.json`, the tap card and the data-date line; a side panel
says what's in the current build and shows every symbol.

```bash
cd worker && npm install && cd ../preview
npm install
npm start
```

Opens on http://localhost:8790 with the files in `../build/site` (what `bash local.sh` builds). `serve.mjs`
runs the **Worker's own code** (`../worker/src/index.js`) on that folder, so the preview reads tiles out of
`aton.pmtiles` exactly as production does. For the made-up SAMPLE site: `SITE_DIR=../build/site-sample npm
start`. URL options: `?api=` another server (the local Worker `http://localhost:8787`, or
`https://aton.vectormarine.us` with `?key=`), `?base=osm|vm` (OpenStreetMap or the Vector Marine chart
underneath; `vm` needs the key), `?on=1`, `?at=lon,lat,zoom`, `?aid=5-1105` (open that aid's card),
`?now=2026-10-19T16:00:00Z` (a fixed clock), `?wide=1` (a tablet-sized frame).

Optional, preview only: `FONTS_DIR=…` serves map fonts from a local folder (`<Font_Name>/<range>.pbf`; else
MapLibre's demo fonts, which need the internet), and `build/coast.geojson` (`pipeline/tools/make_coast.py`) a
rough land shown zoomed out.

| File | What |
|---|---|
| `aton.js` | The words: status codes, light characteristic, kinds, dates, the card. The same as `pipeline/vmaton/words.py` and `flutter/vm_aton/lib/src/words.dart` |
| `app.js` | The map, the overlay from `style.json`, the card |
| `serve.mjs` | Serves the page and runs the Worker's code on the built folder |
| `shots.mjs` | The screenshots in `../docs/img/` (`npm run shots`; Chrome or Chromium) |
| `test/aton.test.mjs` | `aton.js` against the parity fixture (the Dart tests read the same file) |
| `test/preview.test.mjs` | Drives the page in headless Chrome on a built site (fonts blocked on purpose: the symbols must still draw); `ATON_URL=http://localhost:8787` goes through the Worker |
