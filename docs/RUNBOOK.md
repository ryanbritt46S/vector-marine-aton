# Runbook

## Is it working?

```bash
curl -s "https://aton.vectormarine.us/meta.json?key=YOUR_KEY" | python3 -c 'import json,sys; m=json.load(sys.stdin); print(m["run"], m["data_date"], m["counts"]["aids"], "aids", m["counts"]["by_status"])'
```

`run` should be today's (UTC). The app says "Coast Guard data not updated for N days" after 72 hours without a
run; the last build keeps being served meanwhile.

## The daily job failed

GitHub emails whoever last changed `.github/workflows/aton.yml`. Open the run (Actions → buoys-and-lights):

| Symptom in the log | Cause | What to do |
|---|---|---|
| `FAILED: no complete NAVCEN download for <date>` (step "Get today's NAVCEN copies") | The Worker's copy at 10:20 and its retry at 10:40 both failed, or the Worker isn't deployed with its crons | Cloudflare → Workers & Pages → vm-aton → Logs (or Settings → Triggers → past cron events): the error names the file and the answer (`HTTP 5xx`, timeout: NAVCEN down, nothing to do, tomorrow catches up; `HTTP 403` on every file: NAVCEN now refuses Cloudflare too, see "If NAVCEN blocks the Worker" below). To publish today anyway: build and publish from a Mac (below) |
| `FAILED: raw/<date>/… is N bytes, the mirror wrote M` | A copy in R2 was cut short or replaced | Run the workflow again; if it repeats, delete `raw/<date>/` in the bucket and build from a Mac today |
| `FAILED: https://navcen…: HTTP 5xx` / timeouts | (A local or Mac run) NAVCEN down or slow (each file is tried 4 times over ~30 s) | Nothing: tomorrow's run catches up; the published build stays. Or run it again by hand later |
| `FAILED: no Light List for district N` | The Light List files were renamed or moved | Look at the NAVCEN MSI page's `_fileNames.txt` (it lists `["lightListD01",10,…]`) and `pipeline/vmaton/build.py read_light_lists` |
| `FAILED: district N: only … aids in the Light List` | A file came back short (under `min_aids_per_district`, 3000) | Usually NAVCEN mid-update: run again later |
| `FAILED: … is in fileIndexNew.json but not there` | The index and the files disagree for a moment | Run again later |
| `REFUSED: district N: … aids, was …` | Far fewer aids than the last published build (under 80%) | An outage: nothing, the published build stays. A real change (the Coast Guard split or renumbered a district): check it, then run the Build step once with `--allow-shrink` |
| `not a Light List file: missing columns` | The CSV's columns changed | `pipeline/vmaton/lightlist.py`; tell the team |
| `Refusing …` in publish | A SAMPLE build reached publish | Shouldn't happen in Actions; check the workflow wasn't edited to pass `--sample` |
| R2 `AccessDenied` | Token expired / wrong bucket | New token (SETUP step 2), update the three secrets |

Run it again by hand: Actions → buoys-and-lights → Run workflow (it builds from today's copy; the `date` box
builds from another day's copy still in `raw/`, kept 30 days).

The Worker's copy writes these to its log (Workers & Pages → vm-aton → Logs), once per cron:
`{"dir":"raw/<date>","files":N,"light_list_parts":{…},…}` when done, `{"skipped":"raw/<date> is already
complete"}` for the 10:40 retry after a good 10:20, and the error (the file and its answer) otherwise.

### Build and publish from a Mac

Works whenever the Worker's copy doesn't (NAVCEN answers a home connection). R2 credentials in the shell as for
publish (the three `R2_*` variables, typed into the shell, never pasted into a chat):

```bash
cd ~/Projects/vector-marine-aton
.venv/bin/python3 pipeline/run_aton.py --out build/site
.venv/bin/python3 pipeline/publish.py --src build/site --dry-run
.venv/bin/python3 pipeline/publish.py --src build/site
```

### If NAVCEN blocks the Worker

Every file `HTTP 403` in the Worker's log, day after day. Register a machine that NAVCEN answers as a GitHub
self-hosted runner, set `runs-on: self-hosted` in `aton.yml`, and drop back to the plain download: remove the
"Get today's NAVCEN copies" step and `--raw raw`. Tell the team; the Worker's crons can then be removed.

## A user says an aid is wrong

1. Tap it: the card says the data date and the status's date and code.
2. Compare with the Coast Guard's own: the Light List (`navcen.uscg.gov`, Light List by number) and the Local
   Notice to Mariners. We show what they publish; a position or status they haven't updated is theirs to update.
3. If ours differs from the Coast Guard's file: rebuild locally from the same day's files
   (`python3 pipeline/tools/fetch_raw.py --out raw --date YYYY-MM-DD` gets a day from the last 30, then
   `RAW=raw bash local.sh`; or `bash local.sh` the same day) and look at that aid in the preview. A wrong symbol is
   `pipeline/vmaton/classify.py` (add a case for it in `sample.py` CASES); a wrong match is `match.py`.
4. A status code with no plain words shows as the Coast Guard wrote it: add it to `STATUS_CODES` in
   `words.py`, `aton.js` and `words.dart` (same words) and `docs/DATA.md`.

## Costs

R2 ~15 MB published + ~15 MB a day in `raw/` kept 30 days (~0.5 GB; free tier 10 GB). Worker: one cron run a
day (~45 fetches, a few seconds) on the account's Workers Paid plan; requests only read tiles and files. GitHub
Actions a minute a day.
