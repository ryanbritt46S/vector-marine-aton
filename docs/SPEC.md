# Spec: Buoys & lights in the app

Every US Coast Guard aid to navigation from Maine to Florida and Puerto Rico, with what the Coast Guard has
reported wrong with them, so a skipper can see the marks of an inlet or a channel and know, before going, that
the sea buoy is missing or a light is out. The preview (`bash local.sh`) is the reference rendering; the
Flutter package must behave the same. Screenshots of the real data: `docs/img/`.

## Where it lives

- **Overlays → Buoys & lights**: one switch, subtitle "Coast Guard aids · outages from the Notice to
  Mariners". No map buttons. Under the style's `vm-overlays` anchor and under the weather overlays (`below:`).
  Off removes every layer and source it added. Re-added after every style change.
- Its own package (`vm_aton`), Worker (`aton.vectormarine.us`) and bucket (`vm-aton`): it doesn't depend on, or
  change, any other feature.

## On the map

Three symbol layers from `style.json`, in this order (bottom to top): `vm-aton-status` (rings),
`vm-aton-symbols`, `vm-aton-labels`. Symbols never hide each other or anything else (`icon-allow-overlap`,
`icon-ignore-placement`); the more important aid is drawn on top (`symbol-sort-key` = rank). Size: 0.5 at
zoom 6, 0.6 at 9, 0.72 at 11, 0.9 at 13, 1.05 at 14, 1.3 at 16 (1 = the 48-point symbol frame: a can is about
11 points wide).

| Zoom | What shows |
|---|---|
| 6+ | Major lights (nominal range 10 NM or more, or listed as a major light) |
| 8+ | Safe water marks and federal sea buoys (lighted, nominal range 6 NM or more) |
| 9+ | Every other federal lighted buoy and light: minor lights, ranges, directional and articulated lights |
| 11+ | Everything: unlighted buoys, daybeacons, private aids, racons, virtual AIS aids, sound signals |
| 14+ | The label beside each aid: light characteristic and number, `Fl G 4s` / `"3"` (red when it has a status) |

Below zoom 11 one aid per cell of 32 (z6–7), 24 (z8–9) or 20 (z10) screen pixels is kept, the most important
first. An aid with a status is never thinned out: it shows from its own zoom on.

### Symbols (`sym`, `pipeline/vmaton/classify.py`, drawn by `icons.py`)

Our own drawings, chart-like: buoys lean to the right on their position circle; daybeacons stand on a post;
lights are a magenta flare from a dot. Not NOAA or IHO artwork.

| Family | Symbols | Chosen when |
|---|---|---|
| Unlighted buoys | `can-g` `can-r` `can-y` `can-w`, `nun-r` `nun-g` `nun-y`, `can-grg` `nun-rgr` (preferred channel), `sphere-rw` `pillar-rw` (safe water, red topmark), `sphere-y`, `pillar-brb` (isolated danger), `mooring` (white, blue band), `buoy-other` | `ULB`; shape from the structure text ("nun", "can", "sphere", "spar"), else green/yellow/white = can, red = nun, red-white = pillar; colour from `COLOR`, else the structure text |
| Regulatory buoys | `reg-danger` (orange diamond), `reg-control` (circle), `reg-info` (square), `reg-exclusion` (diamond with cross), `reg-plain` | white and orange (`WO`); the mark from the structure text ("diamond", "circle", "square", "cross"/"keep out"), else from the words (danger, rock, shoal… / speed, no wake, zone…) |
| Lighted buoys | `lb-g` `lb-r` `lb-y` `lb-w` `lb-rw` `lb-rgr` `lb-grg` `lb-brb` `lb-wo` `lb-other`: a pillar in the buoy's colours with a magenta flare | `LB`; colour from `COLOR`, else the structure text, else the light |
| Daybeacons | `db-sq-g` (SG) `db-sq-r` `db-sq-y` `db-sq-w`, `db-tri-r` (TR) `db-tri-g` `db-tri-y` `db-tri-w`, `db-jn-g` (JG) `db-jn-r` (JR), `db-dia-w` `db-dia-r` `db-dia-g` `db-dia-y` `db-dia-b` (N…, no lateral meaning), `db-reg` (white board, orange diamond), `db-range` (KRW), `db-rw` (MR), `db-other` | `DBN`, `RFDB`, `RRDB`; the dayboard code at the start of the structure text ("SG-SY on pile." → SG); `NW` worded or white-and-orange → `db-reg`; without a code, by colour |
| Lights | `light-r` `light-g` `light-w` `light-y` (dot in the light's colour + flare), `light-major` (bigger flare, magenta ring), `range-front` `range-rear` (red-white board + flare) | `LT`, `DLT`, `BBL` (colour = the light's first colour); `LTMA` or range ≥ 10 NM → major; `RF` / `RR` |
| Signals | `racon` (magenta ring), `vais` (magenta diamond with V), `sound` (magenta arcs), `other` | `RACN`, `VAIS`, `SSIG`, anything else |

### Status rings (`vm-aton-status`, under the symbol)

| Ring | `status` | From the Coast Guard's codes |
|---|---|---|
| **Red**, with a red "!" disc; the symbol faded to half | `missing` | Missing, off station, structure destroyed or missing, sinking, adrift, hazard to navigation |
| **Amber**, with an amber "!" disc | `fault` | Light out, light not as listed, reduced intensity, structure/buoy/daymark/dayboard damaged, daymark or topmark missing, sound signal / racon / AIS not working, and any code not in our table |
| **Grey dashed**, with a grey "T" disc | `temporary` | Discontinued, relocated (for dredging), temporarily replaced by a lighted/unlighted buoy, light, daybeacon or synthetic AIS aid, temporarily established |

An aid with several notices gets the worst one's ring. The table of codes and words is in
`pipeline/vmaton/words.py` (`STATUS_CODES`); `docs/DATA.md` lists them.

## Tapping an aid (`AtonCard`)

A tap within about 15 points of an aid opens its card (the nearest aid; the more important one when they're
equally near). A tap elsewhere passes on to other overlays. The tap is handled on the phone.

- **Little Egg Inlet Lighted Buoy 2** (the name; "Aid to navigation" when there's none)
- "Lighted buoy · Light List 1105 · Federal aid" ("Private aid" for `AID_TYPE` PA)
- Status box (red / amber / grey edge): **MISSING since Dec 2, 2025** (the plain words in capitals, the date the
  first notice of the worst problem was created) and "Local Notice to Mariners, broadcast notice 0394LM. Coast
  Guard code: MISSING." Several problems: "LIGHT OUT; STRUCTURE DAMAGED since …".
- Rows, each only when there's a value:
  - Light: "Fl R 4s (flashing red, every 4 s)"; the characteristic alone when it can't be spelled out
  - Range: "5 NM" · Height: "15 ft" (focal plane)
  - Structure: "Green can." · Remarks: "Position of buoy frequently shifts with changing conditions."
  - Waterway: "Little Egg Inlet" · District: "Coast Guard District 5"
- An aid only a notice knows: "Not in the current Light List: shown where the notice puts it."
- Small print: "Coast Guard data of Oct 19, 2026. Not for navigation."

## Words

| Code | Words | Code | Words |
|---|---|---|---|
| MISSING | Missing | LT EXT | Light out |
| OFF STATION, OFF STA | Off station | LT IMCH | Light not showing as listed |
| STRUCT DEST | Structure destroyed | STRUCT DMGD | Structure damaged |
| HAZ NAV | Hazard to navigation | DAYMK MISSING | Daymark missing |
| TRLB | Temporarily replaced by a lighted buoy | TRUB | Temporarily replaced by an unlighted buoy |
| DISCONTINUED | Discontinued | RELOCATED FOR DREDGING | Relocated for dredging |

(All of them: `docs/DATA.md`.) Light characteristics: F fixed, Fl flashing, LFl long flashing, Q quick
flashing, VQ very quick flashing, IQ interrupted quick flashing, Iso isophase, Oc occulting, Mo (A) Morse code,
Al alternating; `(2)` group, `(2+1)` composite group; colours W white, R red, G green, Y yellow, Bu blue; "every
4 s". Kinds: Major light, Light, Lighted buoy, Buoy, Daybeacon, Range light, Range daybeacon, Directional light,
Articulated light, Racon (radar beacon), Virtual AIS aid, Sound signal, Aid to navigation.

## The note line (`AtonNote`)

While the layer is on: "Buoys & lights · Coast Guard data of Oct 19, 2026 · Not for navigation". Above it when
they apply: "SAMPLE DATA: made-up aids for testing", and "Coast Guard data not updated for N days" once
`meta.json` is older than `stale_after_hours` (72) on the phone's clock.

## Data and refresh

- Switched on: `meta.json`, `style.json`, `icons/icons.json` (ETags; a few KB), and the symbols once per icons
  version (63 small PNGs at the screen's pixel ratio, kept on the phone). Then `meta.json` every hour while on.
- The map fetches the tiles in view (`/aton/{z}/{x}/{y}.mvt?v=<version>`, a few KB each, at most ~20 KB), and
  keeps them in MapLibre's own cache. A new day's build has a new version: new tile URLs, no mixing.
- Offline: the last meta, style and symbols on the phone draw the layer with the tiles MapLibre has cached.
- If the map's fonts can't load, the labels go but the symbols and rings stay (the labels use their own source).

## Words never change silently

Every string above is in `pipeline/vmaton/words.py`, `preview/aton.js` and
`flutter/vm_aton/lib/src/words.dart`, checked against the same parity fixture. Change all three and this file
together.

## Credits

"Aids to navigation: U.S. Coast Guard Light List and Local Notice to Mariners (NAVCEN)" (`meta.json`
`attribution`), the data date, and "Not for navigation" wherever the layer is shown.
