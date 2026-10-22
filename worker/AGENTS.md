# worker/: the vm-aton Worker

Read the root `AGENTS.md` first. A Cloudflare Worker that serves what the daily job puts in the `vm-aton` R2
bucket. It does no processing on purpose: it reads tiles out of `aton.pmtiles` with range requests and hands
out files. One other job, once a day on a Cron Trigger: copy the Coast Guard's files into the bucket's `raw/`
(`src/mirror.js`), because NAVCEN refuses GitHub's machines and answers Cloudflare's.

## Files

| File | What |
|---|---|
| `src/index.js` | Routes, API key check, tiles from the PMTiles archive (`pmtiles` npm package, `R2Source`), TileJSON, style with this Worker's address, ETag/304, edge cache, CORS |
| `src/mirror.js` | The daily NAVCEN copy, run by `scheduled()` (crons in `wrangler.toml`: 10:20 UTC, retry 10:40): the day's files into `raw/<YYYY-MM-DD>/` with their Last-Modified, `_complete.json` written last. Same rules as the pipeline's download (404 = not there, retries 2/6/18 s, Light List parts probed up to 40, a listed notice part must be there). Its lists must match `pipeline/config/aton.json` |
| `test/mirror.test.mjs` | The mirror with a stand-in NAVCEN serving `pipeline/tests/fixtures/real/` and a stand-in bucket; also that `raw/` isn't served |
| `test/worker.test.mjs` | Node tests with a stand-in bucket on a SAMPLE build (`test/fixtures/`, written by `pipeline/tools/make_parity.py`: never edit) |
| `wrangler.toml` | Name, custom domain `aton.vectormarine.us`, R2 binding `ATON` -> bucket `vm-aton`, the mirror's crons |
| `dev_local.sh` + `seed_local.mjs` | Run it locally with `wrangler dev` on a local copy of R2 seeded from `build/site` |

## Rules for changes here

- Routes are a contract with installed apps (`docs/API.md`): `/meta.json`, `/style.json`, `/aton.json`,
  `/aton/{z}/{x}/{y}.mvt`, `/icons/<sym>[@2x|@3x].png`, `/icons/icons.json`, `/health`. Only add routes; never
  change or remove one without a new `meta.json` version.
- The key is checked before anything else, including the edge cache. Cached copies are stored without the key.
- `meta.json`, `style.json`, `aton.json` and `icons.json` are never edge-cached (they change daily). Tiles are
  edge-cached under the archive's version; a tile URL with the current `?v=` is immutable.
- One runtime dependency, `pmtiles` (reads the archive). No KV/D1 writes. The only fetch to another server is
  the scheduled NAVCEN copy in `mirror.js` (to `navcen.uscg.gov` only); the fetch handler never fetches.
- `raw/` is never served: no route reads it (`test/mirror.test.mjs` checks). The routes stay as listed above.
- The mirror never changes what it copies: the files go into `raw/` byte for byte. It writes `_complete.json`
  only when every file is there and looks like what it should be (CSV header, JSON); otherwise it throws and
  the day isn't built. Keep its lists in step with `pipeline/config/aton.json`.
- Deploys and `wrangler secret put` are run by a person (`docs/SETUP.md`).

## Testing

```bash
cd worker
npm install
npm test
```
