# Data sources, coverage, licence and limits

## The source: USCG NAVCEN "MSI Products"

Everything comes from the files the Coast Guard Navigation Center's Maritime Safety Information page uses
itself: `https://navcen.uscg.gov/sites/default/files/msi/<file>`. Public, no key, no account. The job downloads
about 15 MB a day (one copy of each file).

| File | What | Parts |
|---|---|---|
| `fileIndexNew.json` | How many numbered parts each notice product has right now, and when it was updated: `{"discFedAid_": {"counter": 3, "timestamp": 1792422920}, …}` | 1 |
| `lightListD01_{n}.csv`, `lightListD05_{n}.csv`, `lightListD07_{n}.csv` | The Light List of districts 1, 5 and 7, corrected weekly | **Not in the index.** The job asks for n = 1, 2, … until one isn't there (at most 40). On Oct 19, 2026: 10, 9 and 15 (the page's own `_fileNames.txt` says the same) |
| `discFedAid_{n}.geojson`, `discPriAid_{n}.geojson` | Current discrepancies of federal and private aids, nationwide | from the index (3 and 3) |
| `tmpChange_{n}.geojson` | Current temporary changes, nationwide | from the index (1) |
| `discFedAidCor_`, `discPriAidCor_`, `tmpChangeCor_` | Corrected / closed items | only counted (`meta.json` `corrected_in_area`) |

Not used: `buoys_*.geojson` (Western Rivers), bridges, safety zones, marine events and the other MSI layers.

### The Light List CSV

Read with Python's `csv` module: quoted fields hold commas and doubled quotes (`"NW on pile worded "" Danger
Shoal""."`). The export also leaves runs of spaces where commas were ("Tom's Rivers  New Jersey"); the job
collapses them. Columns used:

| Column | Use |
|---|---|
| `ATU` | District (1, 5, 7) |
| `LIGHT_LIST_NUMBER` | Light List number (`900`, `5400.1`, `603.03`). 11 numbers were listed twice on Oct 19, 2026 (e.g. 5-16545, 7-947.4): both rows are kept, ids `-2` |
| `NAME` | Name; the aid's number is taken from its end (`… Buoy 2M` → `2M`) |
| `AID_TYPE` | `FD` federal / `PA` private |
| `DESCRIPTION_TYPE` | `DBN` daybeacon (12,789), `ULB` unlighted buoy (7,977), `LT` light (6,125), `LB` lighted buoy (4,559), `RF`/`RR` range front/rear (653), `LTMA` major light (159), `VAIS` virtual AIS (87), `SSIG` sound signal (25), `DLT` directional light (18), `RFDB`/`RRDB` range daybeacons (12), `RACN` racon (9), `BBL` articulated light (8) |
| `COLOR` | `R`, `G`, `Y`, `WO`, `W`, `RW`, `RGR`, `GRG`, `WBu`, `BW`, `BRB`, … (`N/A` and empty for 4,000: then the structure text decides) |
| `STRUCTURE_REMARK` | "Red nun.", "Green can.", "SG on pile.", "TR-TY on pile.", "Red and white stripes with red spherical topmark.", "White can with orange bands and diamond worded REEF." |
| `LIGHT_CHAR`, `LIGHT_NOM_RANGE`, `LIGHT_FOCAL_PLANE` | "Fl G 4s", nominal range (NM), height (ft) |
| `DECIMAL_LONGITUDE`, `DECIMAL_LATITUDE` | Position (else `ASSIGNED_LONGITUDE`/`LATITUDE` as `074-04-36.444W`) |
| `REMARK`, `HWATERWAY_NAME`, `AID_SUBTYPE` | Remarks, waterway, `FX` fixed / `FL` floating |

### The notices (GeoJSON)

Properties used: `ATU`, `LLNR` (a number; sometimes `36826.700000000004` for 36826.7, or null), `NAME`,
`DISCREP_STATUS` / `TC_STATUS` (codes joined with `/`), `CREATE_DATE` (ms since 1970, UTC; shown as the New York
date), `BNM_NUM`, `DESCRIPTION_TYPE`, `COLOR`, `AID_TYPE`, `DECIMAL_LONGITUDE`/`LATITUDE`, `LNM_UID`.

**Which notices**: those with `ATU` 1, 5 or 7. A notice without a district counts when it's inside the Light
List's box. (A box alone would take in Lake Ontario, Lake Erie and the Ohio River at Pittsburgh, which belong to
districts 9 and 8.)

**Matching**: district + Light List number (the nearest of the two rows when a number is listed twice), else
the same name (any case) in the same district within 300 m. A notice that matches nothing is shown as its own
aid at the notice's position, with a symbol from its own type and colour, and its card says it's not in the
Light List. Several notices on one aid: the worst decides the ring; the card lists them all.

On Oct 19, 2026: 4,787 notices nationwide, 2,699 in districts 1, 5 and 7; 2,669 matched by number, 2 by name,
28 matched nothing (24 aids: some notices are the same aid twice); 2 matched by number are more than 300 m from
the Light List position (the Light List position is used). 79 corrected items not shown.

### Status codes

| Code | Words | Ring |
|---|---|---|
| `MISSING` | Missing | red |
| `OFF STATION`, `OFF STA` | Off station | red |
| `STRUCT DEST` | Structure destroyed | red |
| `STRUCT MISSING` | Structure missing | red |
| `SINKING` | Sinking | red |
| `ADRIFT` | Adrift | red |
| `HAZ NAV` | Hazard to navigation | red |
| `LT EXT` | Light out | amber |
| `LT IMCH` | Light not showing as listed (improperly characterized) | amber |
| `REDUCED INT` | Light at reduced intensity | amber |
| `NIGHT LT BURNING DAY` | Light burning in daytime | amber |
| `MSLD SIG` | Misleading signal | amber |
| `STRUCT DMGD`, `BUOY DMGD` | Structure damaged, Buoy damaged | amber |
| `LEANING` | Leaning | amber |
| `DAYMK MISSING`, `DAYMK DMGD`, `DAYMK IMCH` | Daymark missing / damaged / not as listed | amber |
| `DBD DEST`, `DBD DMGD` | Dayboard destroyed / damaged | amber |
| `TMK MISSING` | Topmark missing | amber |
| `VEGETATION` | Hidden by vegetation | amber |
| `SS INOP`, `SS IMCH` | Sound signal not working / not as listed | amber |
| `RAC INOP` | Racon not working | amber |
| `AIS INOP`, `AIS IMCH` | AIS not working / not as listed | amber |
| `RBN IMCH` | Radiobeacon not as listed | amber |
| `OTHER DISC AIDS IN AREA` | Other aids nearby also reported | amber |
| `Status Unreported` | Status not reported | amber |
| `TRLB`, `TRUB`, `TRLT`, `TRDBN`, `TRSAIS` | Temporarily replaced by a lighted buoy / an unlighted buoy / a light / a daybeacon / a synthetic AIS aid | grey |
| `DISCONTINUED`, `DISCONTINUED FOR DREDGING` | Discontinued (for dredging) | grey |
| `RELOCATED`, `RELOCATED FOR DREDGING` | Relocated (for dredging) | grey |
| `ESTABLISHED` | Temporarily established | grey |
| `Other` (temporary change) | Temporary change | grey |
| anything else | the Coast Guard's own text | amber (discrepancy) / grey (temporary change) |

On Oct 19, 2026, in districts 1, 5 and 7: 1,654 aids with a red ring, 773 amber, 209 grey.

## Coverage

Coast Guard districts 1 (Maine to northern New Jersey, Lake Champlain, the Hudson), 5 (New Jersey to North
Carolina, Chesapeake Bay) and 7 (South Carolina to Florida, Puerto Rico, US Virgin Islands): 32,421 aids in the
Light List on Oct 19, 2026 (9,218 / 8,880 / 14,323), plus 24 aids only a notice knows.

## Update cadence

The job runs daily at 10:20 UTC (6:20 AM New York in summer). The notices change every day; the Light List
weekly. `meta.json` gives the data's date (`data_date`) and when the job ran (`generated_at`); the app says
"Coast Guard data not updated for N days" after 72 hours without a run, and keeps showing the last build.

## Licence

The Light List and the Local Notice to Mariners are works of the US Government: public domain (17 U.S.C. § 105).
Credit, as a courtesy and so users know the source: "Aids to navigation: U.S. Coast Guard Light List and Local
Notice to Mariners (NAVCEN)". The symbols are our own drawings (not NOAA or IHO chart artwork).

The preview's optional rough land (`pipeline/tools/make_coast.py`) uses GSHHG (LGPL) from the `basemap-data-hires`
package. It's never published, never in the app, and it's only shown zoomed out.

## Server load and storage

- One download of each file a day (~15 MB), from GitHub Actions.
- R2: `aton.pmtiles` (12.9 MB on Oct 19, 2026; 17,886 tiles), 190 icon files (0.9 MB), three JSON files. The
  files are replaced each day (same names; the tile URLs carry the version).
- Worker: reads tiles by range (the archive's directory is cached per isolate and re-checked once a minute),
  serves files; free tier. Tiles of the current version are cached at Cloudflare's edge.
- Phone: a few KB of JSON when switched on, the symbols once per icons version (~200 KB at 3x), then only the
  tiles in view (mostly under 5 KB; the busiest about 20 KB).

## What the layer can and can't tell you

- **Not for navigation.** It's a planning aid: the official sources are the Light List, the Local Notice to
  Mariners and the chart.
- Positions are the Light List's **assigned** positions. Buoys move: "Position of buoy frequently shifts" is in
  many remarks, and inlets' buoys are moved after storms and surveys, often before the Light List says so.
- A notice is only as current as the Coast Guard's file. A buoy reported missing this morning may not be in the
  file yet; one replaced yesterday may still show missing.
- Seasonal changes ("Replaced by nun from Nov. 1 to May 1") are in the remarks, not in the symbol.
- Light sectors, range lines, bearings and fog signal details are in the remarks, not drawn.
