#!/usr/bin/env bash
# Run the vm-aton Worker on this computer against a LOCAL copy of R2. Nothing touches Cloudflare.
#
#   bash dev_local.sh                     the site from ../build/site (made by pipeline/run_aton.py)
#   bash dev_local.sh /path/to/site       any folder with meta.json, style.json, aton.pmtiles and icons/
#   bash dev_local.sh --fresh             empty the local R2 copy first
#   KEY=test bash dev_local.sh            require an API key, like production (?key=test or X-API-Key)
#   PORT=8787 (default)
#
# The same Worker code as production (src/index.js), run by wrangler dev; the files go into wrangler's local R2
# storage in .wrangler/state. Listens on all interfaces so a phone on the same Wi-Fi can reach it.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$here"

PORT="${PORT:-8787}"
STATE=".wrangler/state"
fresh=0
dir=""
for a in "$@"; do
  case "$a" in
    --fresh) fresh=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="../build/site"
if [ ! -f "$dir/meta.json" ]; then
  echo "Nothing built in $dir. From the repo root:  bash local.sh   (or: .venv/bin/python3 pipeline/run_aton.py --sample --out build/site-sample)" >&2
  exit 1
fi
dir="$(cd "$dir" && pwd)"

[ -d node_modules ] || npm install --silent
export WRANGLER_SEND_METRICS=false

if [ "$fresh" = 1 ]; then rm -rf "$STATE/v3/r2"; fi
mkdir -p "$STATE"
node seed_local.mjs "$dir" "$STATE"           # meta.json last

if [ -n "${KEY:-}" ]; then printf 'API_KEYS=local:%s\n' "$KEY" > .dev.vars; else printf 'API_KEYS=\n' > .dev.vars; fi

name="$(scutil --get LocalHostName 2>/dev/null || hostname -s 2>/dev/null || echo this-computer)"
ip="$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true)"
echo
echo "vm-aton Worker (local):     http://localhost:$PORT/health"
echo "  iPhone on this Wi-Fi:     http://$name.local:$PORT"
[ -n "$ip" ] && echo "  Android on this Wi-Fi:    http://$ip:$PORT     (Android emulator: http://10.0.2.2:$PORT)"
[ -n "${KEY:-}" ] && echo "  API key required: $KEY"
echo
# PUBLIC_URL: wrangler dev hands the Worker the custom domain as the request's host; style.json and aton.json
# must point back here instead (the app builds its tile URLs from its own base URL, so phones are fine too)
exec ./node_modules/.bin/wrangler dev --local --port "$PORT" --ip 0.0.0.0 --persist-to "$STATE" \
  --var "PUBLIC_URL:${PUBLIC_URL:-http://localhost:$PORT}"
