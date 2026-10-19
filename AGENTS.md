# AGENTS.md: Vector Marine buoys & lights

Context for AI coding assistants (Claude Code, Cursor, Codex, Copilot…) and the people working with them.
Read it before changing anything. Folder rules: `pipeline/AGENTS.md`, `worker/AGENTS.md`,
`flutter/vm_aton/AGENTS.md`. The work to do is in `docs/IMPLEMENTATION_PLAN.md`; the behaviour to keep is in
`docs/SPEC.md`; file formats in `docs/API.md`; data sources, coverage and limits in `docs/DATA.md`.

## What this is

**Buoys & lights**, an overlay for the Vector Marine fishing app's map (Flutter + MapLibre), switched on from
the app's **Overlays** menu: every US Coast Guard aid to navigation from Maine to Florida and Puerto Rico
(districts 1, 5, 7), drawn with our own chart-like symbols, with the Coast Guard's reported outages (missing,
off station, light out, destroyed, damaged…) and temporary changes (discontinued, relocated for dredging…)
as coloured rings, and a card per aid. Kept current daily from the Light List and the Local Notice to Mariners.

A feature on its own: own repo, Flutter package `vm_aton`, Worker `vm-aton` (aton.vectormarine.us), R2 bucket
`vm-aton`. It shares nothing with the other map layers.

Status: pipeline, Worker and preview built and tested (`bash check.sh`); checked on the real Coast Guard files
of Oct 19, 2026 (`docs/img/`). The Flutter package is written and has tests but **has not been compiled** yet.
Nothing is deployed. That's the team's work: `docs/IMPLEMENTATION_PLAN.md`.

## Repo map

```
pipeline/          daily job (Python): run_aton.py, publish.py, vmaton/, config/, tests/, tools/
worker/            Cloudflare Worker "vm-aton": tiles from aton.pmtiles in R2, API keys, edge cache
flutter/vm_aton/   Flutter package: AtonController, AtonMapLibre, AtonCard, AtonNote (+ example/)
preview/           the overlay as a web page on the real files; aton.js = the words in JS
docs/              IMPLEMENTATION_PLAN, SPEC, API, DATA, SETUP, RUNBOOK, QA_CHECKLIST, ai/APP_REPO_CONTEXT, img/
check.sh           every check;  local.sh: everything locally;  local_app.sh: the Flutter example against it
```

## Rules that must not be broken

1. **Only the Coast Guard's data.** Positions, lights, structures, remarks and statuses come from the Light
   List and the Local Notice to Mariners files as published; never move, invent, guess or "fix" an aid. A
   notice that matches no aid is shown at the notice's own position and its card says so. `--sample` data
   exists only for testing: it's labelled SAMPLE everywhere and `publish.py` refuses it.
2. **Say what it is.** The data date and "Not for navigation" are on the map while the layer is on and on every
   card; a status always carries its date ("MISSING since Dec 2, 2025") and the Coast Guard's own code.
   Unknown codes are shown as the Coast Guard wrote them, never guessed.
3. **Never publish a short build.** If a district has under 80% of the aids the last published `meta.json`
   had, the job stops (`--allow-shrink` is for a person who has checked why).
4. **One set of words in three languages.** `pipeline/vmaton/words.py` is the reference; `preview/aton.js`
   and `flutter/vm_aton/lib/src/words.dart` must give the same answers (parity fixture). Change all three,
   then `bash check.sh`.
5. **Never hand-edit generated files:** `flutter/vm_aton/test/fixtures/**` and `worker/test/fixtures/**`
   (from `pipeline/tools/make_parity.py`), and anything in `build/`.
6. **The file contract is fixed:** routes and files (`meta.json` `version: 1`, `style.json`, `aton.pmtiles`
   layer `aton` and its properties, `icons/icons.json`), `docs/API.md`. Installed apps depend on them. Only add
   fields; a breaking change needs a new `meta.json` version old apps ignore, both sides updated, and
   `docs/API.md`.
7. **Our own symbols.** Draw them (`pipeline/vmaton/icons.py`); never copy NOAA, IHO or anyone's chart artwork.
8. **Nothing about the user leaves the phone.** Taps are handled on the phone; no positions, analytics or
   logging of what's tapped. The only requests are meta/style/icons and map tiles.
9. **Credit the source** where the layer is shown: `meta.json` `attribution` ("Aids to navigation: U.S. Coast
   Guard Light List and Local Notice to Mariners (NAVCEN)").
10. **Free-tier budget.** The Worker only reads tiles and files (Workers Free: ~10 ms CPU per request). R2
    ~15 MB. GitHub Actions a minute a day. Don't add paid services without checking this.
11. **Stay out of the chart.** Overlays only, under the style's `vm-overlays` anchor (and under the weather
    overlays); never change the bathymetry tiles, relief, contours, palettes or map styles. No new map
    buttons: the switch lives in the app's Overlays menu.
12. **Secrets stay out of git:** R2 keys (GitHub secrets), `API_KEYS` (Wrangler secret), `worker/.dev.vars`.
    Never paste them into a chat.
13. **Deploys, secret changes and runs that publish are for a person.** Prepare the command; don't run it
    against production yourself.
14. **Not for navigation.** Keep that note wherever the layer is shown.

## Commands

From the repo root. These blocks have no `#` comments so they paste cleanly into zsh.

| Command | Does |
|---|---|
| `bash check.sh` | Everything: pipeline tests, parity fixtures, Worker tests, preview tests (browser test on a sample build), `flutter analyze` + `flutter test` |
| `bash local.sh` | Download the Coast Guard files, build, local Worker on :8787, preview on :8790 (`sample` for made-up data, `RAW=dir` for local copies) |
| `bash local_app.sh` | The Flutter example app against the local Worker (`android`, `iphone`, `android-phone`) |
| `.venv/bin/python3 pipeline/run_aton.py --out build/site` | Just build (downloads) |
| `.venv/bin/python3 pipeline/run_aton.py --out build/site --raw DIR` | Build from copies of the NAVCEN files |
| `.venv/bin/python3 pipeline/run_aton.py --sample --out build/site-sample` | Build made-up SAMPLE data |
| `.venv/bin/python3 pipeline/tools/make_parity.py` | Regenerate the parity fixtures (`check.sh` does it too) |
| `cd preview && SITE_DIR=../build/site npm run shots` | The screenshots in `docs/img/` |
| `cd worker && npm test` | Worker tests |
| `cd preview && npm test` | aton.js tests (+ the browser test with `SITE_DIR=...`) |
| `cd flutter/vm_aton && flutter pub get && flutter analyze && flutter test` | The Flutter package |

## Definition of done

- `bash check.sh` passes (with Flutter installed when you touched `flutter/`). CI runs the same script and
  fails if a generated fixture wasn't regenerated and committed.
- New or changed behaviour has a test on the side you changed.
- Wording, format or behaviour changes are in `docs/SPEC.md` / `docs/API.md`.
- A change to symbols, zooms or the style: new screenshots (`npm run shots` in `preview/`), looked at.
- No generated file edited by hand, no secret committed, nothing in the chart touched.

## Where to change what

| To change | Edit | Then |
|---|---|---|
| Districts, zooms, thresholds, attribution, shrink ratio | `pipeline/config/aton.json` | `bash check.sh`; the next daily run uses it |
| How files are found and read (NAVCEN, parts, CSV, GeoJSON) | `pipeline/vmaton/sources.py`, `lightlist.py`, `notices.py`, `build.py` | pipeline tests; a real run (`bash local.sh`) |
| Which symbol an aid gets | `pipeline/vmaton/classify.py` (+ the case in `sample.py` CASES) | pipeline tests; screenshots |
| How symbols look | `pipeline/vmaton/icons.py` | screenshots, `docs/SPEC.md` |
| Layers, sizes, labels, rings | `pipeline/vmaton/style.py` | preview, screenshots, the app on a device |
| Which aids show at which zoom | `pipeline/vmaton/tiles.py`, `config/aton.json` `zoom` | pipeline tests; screenshots |
| Status words, light words, the card | `words.py`, `preview/aton.js`, `words.dart`, `docs/SPEC.md` | `bash check.sh` (fixtures) |
| Matching notices to aids | `pipeline/vmaton/match.py` | pipeline tests |
| What the Worker serves | `worker/src/index.js` | `worker/test/` |
| Map drawing in the app | `flutter/vm_aton/lib/src/maplibre.dart` | example app on a device, QA checklist |
| The card and the note line | `flutter/vm_aton/lib/src/widgets.dart` | widget tests; keep the preview in step |
| Schedule, secrets of the job | `.github/workflows/aton.yml`, `docs/SETUP.md` | run it by hand once |

## Glossary

| Term | Meaning |
|---|---|
| Aid (ATON) | An aid to navigation: buoy, daybeacon, light, range, racon, virtual AIS aid, sound signal |
| Light List | The Coast Guard's list of every aid, corrected weekly; `LIGHT_LIST_NUMBER` (LLNR) per district (ATU) |
| LNM | Local Notice to Mariners: the Coast Guard's weekly notices; NAVCEN publishes its current discrepancies and temporary changes as GeoJSON |
| Discrepancy | An aid not as listed: missing, off station, light out (`LT EXT`), destroyed (`STRUCT DEST`)… |
| Temporary change | A planned change: discontinued, relocated for dredging, temporarily replaced (`TRLB`, `TRUB`)… |
| Status | Our severity of an aid's notices: `missing` (red ring), `fault` (amber), `temporary` (grey dashed) |
| Unlisted | An aid only a notice knows (no Light List match): shown at the notice's position, `listed: false` |
| Major light | A light with a nominal range of 10 NM or more, or listed as a major light (`LTMA`) |
| sym | The symbol id of an aid (`lb-g`, `nun-r`, `db-sq-g`, …; `docs/SPEC.md` has the table) |
| Sample | Made-up data for testing (`--sample`); never published |

## Known gaps

- The Flutter package hasn't been compiled or run (work package 1); three maplibre_gl details to check first
  are in `flutter/vm_aton/AGENTS.md`.
- The daily job's download from NAVCEN couldn't be tried from where this was written (no internet there); the
  files' format was checked on copies downloaded on Oct 19, 2026.
- Western Rivers (`buoys_*.geojson`) and other districts are not included.
- If the map's fonts can't load (offline, nothing cached), the labels disappear; the symbols and rings don't
  (they're on their own source).
- Light sectors, ranges' lines and bearings are not drawn: the card has the Light List's remarks.

## Working here with an AI assistant

- Start each work package with its kickoff prompt in `docs/IMPLEMENTATION_PLAN.md`.
- Keep changes small and run `bash check.sh` before calling something done.
- If a task seems to need a data value, a new source, or a change in what users are told, stop and ask a person.
