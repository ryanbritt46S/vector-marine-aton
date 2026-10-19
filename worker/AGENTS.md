# worker/: the vm-aton Worker

Read the root `AGENTS.md` first. A Cloudflare Worker that serves what the daily job puts in the `vm-aton` R2
bucket. It does no processing on purpose (Workers Free has ~10 ms of CPU per request): it reads tiles out of
`aton.pmtiles` with range requests and hands out files.

## Files

| File | What |
|---|---|
| `src/index.js` | Routes, API key check, tiles from the PMTiles archive (`pmtiles` npm package, `R2Source`), TileJSON, style with this Worker's address, ETag/304, edge cache, CORS |
| `test/worker.test.mjs` | Node tests with a stand-in bucket on a SAMPLE build (`test/fixtures/`, written by `pipeline/tools/make_parity.py`: never edit) |
| `wrangler.toml` | Name, custom domain `aton.vectormarine.us`, R2 binding `ATON` -> bucket `vm-aton` |
| `dev_local.sh` + `seed_local.mjs` | Run it locally with `wrangler dev` on a local copy of R2 seeded from `build/site` |

## Rules for changes here

- Routes are a contract with installed apps (`docs/API.md`): `/meta.json`, `/style.json`, `/aton.json`,
  `/aton/{z}/{x}/{y}.mvt`, `/icons/<sym>[@2x|@3x].png`, `/icons/icons.json`, `/health`. Only add routes; never
  change or remove one without a new `meta.json` version.
- The key is checked before anything else, including the edge cache. Cached copies are stored without the key.
- `meta.json`, `style.json`, `aton.json` and `icons.json` are never edge-cached (they change daily). Tiles are
  edge-cached under the archive's version; a tile URL with the current `?v=` is immutable.
- One runtime dependency, `pmtiles` (reads the archive). No fetches to other servers, no KV/D1 writes.
- Deploys and `wrangler secret put` are run by a person (`docs/SETUP.md`).

## Testing

```bash
cd worker
npm install
npm test
```
