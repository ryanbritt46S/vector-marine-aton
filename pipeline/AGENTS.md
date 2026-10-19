# pipeline/: the daily Buoys & lights job

Read the root `AGENTS.md` first. Python 3.10+; runs daily in GitHub Actions (`.github/workflows/aton.yml`)
and locally through `local.sh`. No account needed (the Coast Guard's NAVCEN files are public). Pure-Python
wheels only: no GDAL, no tippecanoe.

## Files

| File | What |
|---|---|
| `run_aton.py` | CLI: download (or `--raw DIR`, or `--sample`), build `build/site`, refuse a short build against the last published `meta.json` (`--allow-shrink`), print a summary |
| `publish.py` | Upload `uploads.json`'s files to R2 (icons, `aton.pmtiles`, `style.json`, `meta.json` last); refuses sample data; `--dry-run` |
| `config/aton.json` | Districts, NAVCEN URL, products, sanity thresholds, zoom rules, attribution |
| `vmaton/sources.py` | `HttpSource` (NAVCEN, retries, 404 = not there) and `DirSource` (`--raw`, tests) |
| `vmaton/lightlist.py` | The Light List CSV (csv module), `Aid`, LLNR normalising, DMS, ids for duplicates |
| `vmaton/notices.py` | Discrepancies and temporary changes (GeoJSON) → `Notice` |
| `vmaton/words.py` | Status codes → words + severity, light characteristic in words, kinds, the card (**the reference** for `preview/aton.js` and `words.dart`) |
| `vmaton/classify.py` | `SYMBOLS`, `classify()`: which symbol and kind each aid gets |
| `vmaton/match.py` | Notices onto aids (number, else name within 300 m), aids for unmatched notices, the status summary |
| `vmaton/tiles.py` | minzoom and rank, thinning below z11, MVT encoding, the PMTiles file and its version |
| `vmaton/icons.py` | The symbols, drawn with Pillow at 1x/2x/3x, and `icons.json` |
| `vmaton/style.py` | `style.json` (sources and layers) |
| `vmaton/build.py` | `run()`: the whole job, `meta.json`, `uploads.json` |
| `vmaton/sample.py` | Made-up files (SAMPLE) for tests and `--sample`; `CASES` = one aid per symbol |
| `tools/make_parity.py` | Writes `flutter/vm_aton/test/fixtures/` and `worker/test/fixtures/` (run by `check.sh`) |
| `tools/make_fixture.py` | Cuts `tests/fixtures/real/` from a full download (NJ inlets, NY harbor entrance, Miami); not run by `check.sh` |
| `tools/make_coast.py` | Optional rough land for the preview only (GSHHG via `basemap-data-hires`) |
| `tests/` | pytest; `bash check.sh` runs them |

## Rules for changes here

- **The Coast Guard's data, as published.** Never move an aid, drop one that has a position, or guess a status.
  An unknown code is shown raw. A notice that matches nothing is shown at its own position (`listed: false`).
- Read the CSV with the `csv` module (quoted commas, doubled quotes). Keep both rows of a number listed twice.
- **Never publish a short build**: the shrink check (`shrink_ratio`, `min_aids_per_district`) stays. A missing
  part that `fileIndexNew.json` lists is an error, not "no notices".
- Light List parts aren't in `fileIndexNew.json`: probe `lightList{DD}_{n}.csv` until a 404 (cap 40).
- The output must be the same for the same input (the tiles' version is a hash of them): no timestamps or random
  order inside tiles; sorted ids.
- New symbol: add it to `SYMBOLS`, draw it in `icons.py`, add a case to `sample.py` `CASES` (the tests check
  every symbol has one), and look at the screenshots.
- Any change to `words.py` changes the fixtures: run `bash check.sh`, commit them, and make the same change in
  `preview/aton.js` and `flutter/vm_aton/lib/src/words.dart`.

## Testing

```bash
python3 -m venv .venv
.venv/bin/pip install -r pipeline/requirements-test.txt
cd pipeline
../.venv/bin/python3 -m pytest -q
```
