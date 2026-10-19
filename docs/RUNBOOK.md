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
| `FAILED: https://navcen…: HTTP 5xx` / timeouts | NAVCEN down or slow (each file is tried 4 times over ~30 s) | Nothing: tomorrow's run catches up; the published build stays. Or run it again by hand later |
| `FAILED: …: HTTP 403` on every file | NAVCEN refusing GitHub's addresses or our user agent | Try a run locally (`bash local.sh`). If it works there, tell the team: the job may need another user agent, or to run elsewhere |
| `FAILED: no Light List for district N` | The Light List files were renamed or moved | Look at the NAVCEN MSI page's `_fileNames.txt` (it lists `["lightListD01",10,…]`) and `pipeline/vmaton/build.py read_light_lists` |
| `FAILED: district N: only … aids in the Light List` | A file came back short (under `min_aids_per_district`, 3000) | Usually NAVCEN mid-update: run again later |
| `FAILED: … is in fileIndexNew.json but not there` | The index and the files disagree for a moment | Run again later |
| `REFUSED: district N: … aids, was …` | Far fewer aids than the last published build (under 80%) | An outage: nothing, the published build stays. A real change (the Coast Guard split or renumbered a district): check it, then run the Build step once with `--allow-shrink` |
| `not a Light List file: missing columns` | The CSV's columns changed | `pipeline/vmaton/lightlist.py`; tell the team |
| `Refusing …` in publish | A SAMPLE build reached publish | Shouldn't happen in Actions; check the workflow wasn't edited to pass `--sample` |
| R2 `AccessDenied` | Token expired / wrong bucket | New token (SETUP step 2), update the three secrets |

Run it again by hand: Actions → buoys-and-lights → Run workflow.

## A user says an aid is wrong

1. Tap it: the card says the data date and the status's date and code.
2. Compare with the Coast Guard's own: the Light List (`navcen.uscg.gov`, Light List by number) and the Local
   Notice to Mariners. We show what they publish; a position or status they haven't updated is theirs to update.
3. If ours differs from the Coast Guard's file: rebuild locally from the same day's files
   (`RAW=… bash local.sh`, or `bash local.sh` the same day) and look at that aid in the preview. A wrong symbol is
   `pipeline/vmaton/classify.py` (add a case for it in `sample.py` CASES); a wrong match is `match.py`.
4. A status code with no plain words shows as the Coast Guard wrote it: add it to `STATUS_CODES` in
   `words.py`, `aton.js` and `words.dart` (same words) and `docs/DATA.md`.

## Costs

R2 ~15 MB (free tier 10 GB), Worker free tier (it reads tiles and files), GitHub Actions a minute a day.
