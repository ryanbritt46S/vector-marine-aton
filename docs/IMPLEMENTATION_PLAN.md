# Implementation plan: Buoys & lights

What's left to ship Buoys & lights, as work packages (WPs) a developer can take one at a time with an AI
assistant. Each has an owner, what it needs first, the steps, how to tell it's done, and a kickoff prompt to
paste into the assistant. Behaviour to keep: `SPEC.md`. Device tests: `QA_CHECKLIST.md`. Accounts and deploy:
`SETUP.md`. This feature is independent of the other map layers: its own repo, package, Worker and bucket.

## Using this with an AI assistant

- Open this repo (or, for WP4, the app repo) in your assistant. Claude Code reads `CLAUDE.md` → `AGENTS.md`;
  Cursor and Codex read `AGENTS.md`; Copilot reads `.github/copilot-instructions.md`. In the app repo, first
  paste `docs/ai/APP_REPO_CONTEXT.md` into its `AGENTS.md`/`CLAUDE.md`.
- One WP per branch and session. Paste the kickoff prompt, let the assistant plan, then review its diff.
- `bash check.sh` must pass before a WP is done. A person ticks the "Done when" list, not the assistant.
- Let the assistant prepare deploy and secret commands, but run them yourself; never paste secrets into a chat.
- If the assistant proposes changing what users are told, a data source, or a status word, stop: that's a
  decision for a person (root `AGENTS.md`, rules 1–4).

| WP | What | Owner | Needs |
|---|---|---|---|
| 0 | Get oriented: run everything locally | Everyone | — |
| 1 | Compile the Flutter package; run the example on devices | Mobile | 0 |
| 2 | Create the bucket and token; deploy the Worker | Backend | 0 |
| 3 | Enable the daily job (GitHub Action) | Backend | 2 |
| 4 | Add Buoys & lights to the app's Overlays menu | Mobile | 1 (3 for live data) |
| 5 | QA and a check by skippers who run these waters | QA + skippers | 3, 4 |
| 6 | Operations handover | Backend + data owner | 3 |

WP1 and WP2 can run in parallel.

---

## WP0 · Get oriented

**Owner:** everyone · **Needs:** nothing

1. Read `README.md`, `AGENTS.md`, then skim `docs/SPEC.md`, `docs/API.md` and `docs/DATA.md`.
2. `bash local.sh` (Node 18+, Python 3; no account). It downloads the Coast Guard's files, builds the coast and
   opens the preview on Barnegat Inlet: switch the overlay on, zoom in and out, tap a buoy, find a red ring
   (Little Egg Inlet Lighted Buoy 2), compare an inlet with the NOAA chart.
3. `bash check.sh` (the Flutter step is skipped without Flutter).

Done when:
- [ ] `check.sh` passes on your machine.
- [ ] You've compared one inlet's aids in the preview with the Coast Guard Light List and the NOAA chart.

Kickoff prompt:
```text
Read AGENTS.md, README.md, docs/SPEC.md, docs/API.md and docs/DATA.md in this repo. Then explain back to me,
in under 300 words: what the daily job downloads and writes, how notices are matched to aids, what the Worker
does, what the app downloads and when, and the rules in AGENTS.md I must not break. Then run `bash check.sh` and
tell me the result. Don't change any files.
```

## WP1 · Compile the Flutter package; run the example on devices

**Owner:** mobile · **Needs:** WP0, Flutter 3.41.x, Xcode and/or Android Studio

The package was written without a Flutter SDK in reach: **it has not been compiled yet.** Its words mirror
`preview/aton.js` and `pipeline/vmaton/words.py` (one parity fixture for all three), and its tests (words,
controller, widgets) are ready to run.

1. `cd flutter/vm_aton && flutter pub get && flutter analyze && flutter test`. Fix what the analyzer or a test
   reports, changing only what the error needs (`flutter/vm_aton/AGENTS.md`).
2. Check the three maplibre_gl details listed in `flutter/vm_aton/AGENTS.md` ("To check first on a device"):
   `SymbolLayerProperties.fromJson`, the symbols' size from the @2x/@3x PNGs, and the tap's pixels.
3. `bash local.sh` in one tab, `bash local_app.sh` (iOS Simulator) or `bash local_app.sh android` in another.
4. On the example app: Overlays → Buoys & lights; zoom 6 → 16; the rings; tap a buoy (the card); airplane mode
   and relaunch (the layer still draws from the cache).
5. When it's green, make CI's Flutter job blocking: delete `continue-on-error` in `.github/workflows/check.yml`.

Done when:
- [ ] `flutter analyze` clean and `flutter test` green (incl. `words_test.dart`: the Dart words equal the Python).
- [ ] The example app matches the preview at Barnegat, Little Egg and Miami on iOS and Android (same symbols,
      sizes within ~15%, same card).

Kickoff prompt:
```text
Read AGENTS.md and flutter/vm_aton/AGENTS.md. Run `flutter pub get`, `flutter analyze` and `flutter test` in
flutter/vm_aton and fix what they report with the smallest possible changes. Don't change public API or words
(words_test.dart pins them). If a maplibre_gl call has a different name or signature in the version pub picked
(in particular SymbolLayerProperties.fromJson), adapt the call and tell me which. Show me each change before
the next.
```

## WP2 · Create the bucket and token; deploy the Worker

**Owner:** backend · **Needs:** WP0

1. `docs/SETUP.md` steps 2–3: the `vm-aton` bucket and a token scoped to it, `wrangler deploy`, `API_KEYS`
   (the same keys as the tiles Worker).
2. Check `/health` (200), `/meta.json` without a key (401), with a key (404 until WP3).

Done when:
- [ ] `https://aton.vectormarine.us/health` says ok; a request without a key is 401.

Kickoff prompt:
```text
Read AGENTS.md, worker/AGENTS.md, worker/wrangler.toml and docs/SETUP.md. Check wrangler.toml will work as
written (bucket binding, custom domain) and tell me anything that looks wrong before I deploy. Prepare the
commands for me to run; don't run deploys or add secrets yourself.
```

## WP3 · Enable the daily job

**Owner:** backend · **Needs:** WP2

1. `docs/SETUP.md` step 4: the three repository secrets, then Actions → buoys-and-lights → Run workflow
   (after the Worker's first daily copy of the NAVCEN files: `docs/SETUP.md` step 3).
2. Read the summary: aids per district (about 9,200 / 8,900 / 14,300), notices matched, statuses. Spot-check
   five aids with a status against the Local Notice to Mariners.

Done when:
- [ ] Three days of scheduled runs succeeded (about a minute each).
- [ ] `curl …/meta.json?key=…` shows today's `run`; the live preview (`?api=https://aton.vectormarine.us`) shows
      Barnegat on the real chart.

Kickoff prompt:
```text
Read AGENTS.md, pipeline/AGENTS.md, .github/workflows/aton.yml and docs/SETUP.md. Check the workflow will work
as written (secrets, the Worker's raw/ copy and fetch_raw.py, the shrink check reading the last meta.json from
R2, publish order) and tell me anything
that looks wrong before I run it. Then help me read the first run's summary.
```

## WP4 · Add Buoys & lights to the app's Overlays menu

**Owner:** mobile · **Needs:** WP1 (WP3 for live data)

1. Add the package; `VmAton.init(apiKey: <tiles key>, cacheDir: await getApplicationCacheDirectory())`.
2. Map screen: one `AtonController()`; `AtonMapLibre.attach(controller, mapController, below: <weather overlays'
   lowest layer>, onFeatureTapped: (f) => showAtonCard(context, f, controller))` in `onMapCreated`;
   `onStyleLoaded()` with the other overlays.
3. `onMapClick`: `await atonLayer.tap(point, latLng)`: non-null = handled (the card is open); null = pass to the
   other overlays.
4. Overlays menu: "Buoys & lights" switch bound to `controller.enabled` / `controller.toggle()`, subtitle "Coast
   Guard aids · outages from the Notice to Mariners". `AtonNote(controller: …)` while on (data date, SAMPLE,
   stale). Remember the switch with the app's other overlay settings.
5. Go through `SPEC.md` on a device.

Done when:
- [ ] Works on both platforms against production; matches `SPEC.md` and the preview.
- [ ] Switching it off leaves every other layer as it was; a style change brings it back.
- [ ] No request contains anything about the user (proxy check): only meta/style/icons and tiles.

Kickoff prompt:
```text
Read the AGENTS.md section I pasted from vector-marine-aton's docs/ai/APP_REPO_CONTEXT.md and docs/SPEC.md
(I'll paste it). Find the map screen, the Overlays menu, and how other overlays (vm_surveys, vm_traffic) are
wired. Propose the smallest change that adds Buoys & lights as described: the switch, the layer under the
weather overlays, the card on tap, the note line. Show me the plan before editing. No new map buttons, no
changes to map styles.
```

## WP5 · QA and a skippers' check

**Owner:** QA + skippers who run these waters · **Needs:** WP3, WP4

1. `docs/QA_CHECKLIST.md` on both platforms.
2. Skippers compare inlets they run (one per state if possible) with what they see on the water and with the
   NOAA chart: missing symbols, wrong shapes or colours, statuses that are stale or missing.

Done when:
- [ ] Checklist complete on both platforms; issues filed.
- [ ] A written note from the skippers for the release notes.

## WP6 · Operations handover

**Owner:** backend + whoever owns the data · **Needs:** WP3

1. Walk through `docs/RUNBOOK.md` with the person who'll get the failure emails.
2. Decide who adds plain words for new Coast Guard codes (they show raw until then).

Done when:
- [ ] Someone owns the daily job and has read the runbook.

## Backlog (not needed to ship)

- Light sectors and range lines drawn from the remarks.
- A "near me" list of aids with a status along a planned route (the trip planner).
- Push when an aid of a followed inlet goes missing (like Channel surveys' Follow).
- Districts 8 (Gulf), 9 (Great Lakes), 11/13/14/17 (West Coast, Hawaii, Alaska): config, sanity numbers, QA.
- Western Rivers buoys (`buoys_*.geojson`).
