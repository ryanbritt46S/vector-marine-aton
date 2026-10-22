# Setup: bucket, Worker, daily job

Once, in this order. About half an hour. Command blocks have no `#` comments, so they paste cleanly into zsh.
Secrets go into the dashboards and `wrangler secret put` prompts, never into files in the repo or a chat.
No account is needed for the data: the Coast Guard's files are public.

## 1. Try it locally

```bash
cd ~/Projects/vector-marine-aton
bash local.sh
```

Downloads the Coast Guard's files, builds the whole coast (about 30 s), starts the local Worker and the
preview, and opens it on Barnegat Inlet. `bash local.sh sample` is a quick look with made-up data.

## 2. R2 bucket and token

In the Cloudflare dashboard (same account as `tiles.vectormarine.us`):

1. **R2 → Create bucket** → name **`vm-aton`**, location Automatic.
2. **R2 → Manage R2 API Tokens → Create API token**: permissions **Object Read & Write**, bucket **vm-aton**
   only. Note the **Access Key ID**, the **Secret Access Key** (shown once) and your **Account ID** (R2 overview
   page). They're for GitHub in step 4.
3. **R2 → vm-aton → Settings → Object lifecycle rules → Add rule**: name `expire-raw`, prefix **`raw/`**,
   delete objects **30 days** after upload. That's the Worker's daily copy of the NAVCEN files (~15 MB a day);
   nothing else in the bucket has that prefix.

## 3. The Worker

```bash
cd ~/Projects/vector-marine-aton/worker
npm install
npx wrangler login
npx wrangler deploy
```

That creates `vm-aton`, bound to the bucket, on `https://aton.vectormarine.us` (the custom domain in
`wrangler.toml`; vectormarine.us is already on Cloudflare) and `https://vm-aton.<subdomain>.workers.dev`, and
its two Cron Triggers (10:20 and 10:40 UTC): the daily copy of the NAVCEN files into `raw/`, which the job in
step 4 builds from (NAVCEN refuses GitHub's machines). Cron Triggers need no extra setting; the account is on
Workers Paid. They show under Workers & Pages → vm-aton → Settings → Triggers.

API keys: the same keys as the tiles Worker. `api_keys.sh` keeps them in
`~/.config/vectormarine/bathy_api_keys` (one `label:key` per line); send the same list here:

```bash
cd ~/Projects/vector-marine-aton/worker
paste -sd, ~/.config/vectormarine/bathy_api_keys | npx wrangler secret put API_KEYS --name vm-aton
```

`api_keys.sh` only updates `bathy-tiles`: after adding or revoking a key there, run the line above again.

Check (should be `401`, then `404` until step 4 has run):

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://aton.vectormarine.us/meta.json
curl -s -o /dev/null -w '%{http_code}\n' "https://aton.vectormarine.us/meta.json?key=YOUR_KEY"
```

## 4. The daily job (GitHub Actions)

1. Push this repo to GitHub (private is fine; a run takes about a minute of the free allowance). The `check`
   workflow runs on every push; its `flutter` job may be red until the package is compiled (work package 1)
   and doesn't block anything.
2. **Settings → Secrets and variables → Actions → New repository secret**, three times:

| Secret | Value |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | from step 2 |
| `R2_SECRET_ACCESS_KEY` | from step 2 |

3. **Actions → buoys-and-lights → Run workflow**, after the Worker's first copy (10:20 UTC the day after step 3,
   or later that day; until then the first step says `no complete NAVCEN download`). The run's summary lists the
   aids per district, the notices and how they matched.
4. Check:

```bash
curl -s "https://aton.vectormarine.us/meta.json?key=YOUR_KEY" | head -c 400
```

From then on it runs daily at 10:50 UTC (6:50 AM New York in summer), after the Worker's copy. GitHub emails
failures to whoever last changed `.github/workflows/aton.yml`; the Worker's own errors are in its Logs.

## 5. See it on the live data

```bash
cd ~/Projects/vector-marine-aton/worker
npm install
cd ../preview
npm install
npm start
```

Open `http://localhost:8790/?api=https://aton.vectormarine.us&key=YOUR_KEY&on=1&base=vm`: production data on
the Vector Marine chart.

## 6. In the app

`VmAton.init(apiKey: key, cacheDir: await getApplicationCacheDirectory())` with the same key the app uses for
the tiles (from your backend), then `docs/ai/APP_REPO_CONTEXT.md` and work package 3 in
`docs/IMPLEMENTATION_PLAN.md`.
