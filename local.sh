#!/usr/bin/env bash
# Try Buoys & lights end to end on this computer. Nothing touches Cloudflare, R2 or the live map.
#
#   bash local.sh                 download the Coast Guard's files (NAVCEN, ~15 MB) and build the whole coast
#   RAW=/path/to/files bash local.sh   build from a folder with copies of the NAVCEN files instead
#   bash local.sh sample          made-up SAMPLE aids: no download, a quick look at the screens
#   REBUILD=1 bash local.sh       build again even if today's build is there
#   then, in another terminal tab:   bash local_app.sh   (the Flutter example app on a simulator or phone)
#
# No account is needed: the Light List and the Local Notice to Mariners files are public. A build takes about
# 30 s. Optional, for the preview only: a rough coastline (pip install basemap-data-hires, then
# .venv/bin/python3 pipeline/tools/make_coast.py) and local map fonts (FONTS_DIR=<folder of <Font_Name>/<range>.pbf>).
#
# What runs:  pipeline/run_aton.py   -> build/site (aton.pmtiles, icons/, style.json, meta.json)
#             worker/dev_local.sh    the real vm-aton Worker on :8787, with a local copy of R2
#             preview/serve.mjs      the app preview on :8790, reading from that Worker
# Ctrl-C stops both. Logs: .local-logs/
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
mode="${1:-real}"
logs="$root/.local-logs"
mkdir -p "$logs"

case "$mode" in
  -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
  sample|real) ;;
  *) echo "Usage: bash local.sh [sample|real]" >&2; exit 1 ;;
esac
command -v node >/dev/null && command -v npm >/dev/null \
  || { echo "Needs Node 18 or newer: https://nodejs.org (or: brew install node)" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Needs Python 3: https://www.python.org/downloads/" >&2; exit 1; }

# Python packages go in a private environment in this repo (.venv, git-ignored): Homebrew's Python refuses
# system-wide installs (PEP 668), and this keeps everything in one place.
venv="$root/.venv"
py="$venv/bin/python3"
if [ ! -x "$py" ]; then
  echo "Setting up a private Python environment (once): .venv"
  python3 -m venv "$venv" || { echo "Couldn't create $venv (python3 -m venv)." >&2; exit 1; }
fi
if ! "$py" -c "import PIL, mapbox_vector_tile, pmtiles, requests" 2>/dev/null; then
  echo "Installing Python packages into .venv (once, a minute)..."
  "$py" -m pip install --quiet --disable-pip-version-check -r "$root/pipeline/requirements-test.txt" \
    || { echo "Couldn't install the packages (needs internet for pypi.org)." >&2; exit 1; }
fi

out="$root/build/site"
[ "$mode" = sample ] && out="$root/build/site-sample"
today="$(TZ=America/New_York date +%Y-%m-%d)"
built="$("$py" -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["generated_at"][:10])' "$out/meta.json" 2>/dev/null || true)"
if [ "${REBUILD:-}" = 1 ] || [ "$built" != "$today" ]; then
  if [ "$mode" = sample ]; then
    echo "Building SAMPLE (made-up) aids..."
    "$py" "$root/pipeline/run_aton.py" --sample --out "$out"
  elif [ -n "${RAW:-}" ]; then
    echo "Building from the files in $RAW..."
    "$py" "$root/pipeline/run_aton.py" --out "$out" --raw "$RAW"
  else
    echo "Downloading the Light List and the Local Notice to Mariners files from NAVCEN (~15 MB) and building..."
    "$py" "$root/pipeline/run_aton.py" --out "$out"
  fi
fi

for port in 8787 8790; do
  if curl -s -m 1 -o /dev/null "http://localhost:$port/" 2>/dev/null; then
    echo "Port $port is already in use (an earlier local.sh, or another Vector Marine repo's local.sh, still running?). Stop it and try again." >&2; exit 1
  fi
done

stop() { rc=$?; trap - EXIT INT TERM; kill $(jobs -p) 2>/dev/null || true; wait 2>/dev/null || true; echo; echo "Stopped."; exit "$rc"; }
trap stop EXIT INT TERM

echo "Starting the local Worker (the first run installs packages)..."
bash "$root/worker/dev_local.sh" "$out" > "$logs/worker.log" 2>&1 &
(cd "$root/preview" && { [ -d node_modules ] || npm install --silent; } && { [ -d ../worker/node_modules ] || (cd ../worker && npm install --silent); } \
  && SITE_DIR="$out" PORT=8790 exec node serve.mjs) > "$logs/preview.log" 2>&1 &

up() { curl -s -m 2 -o /dev/null -w '%{http_code}' "$1" 2>/dev/null | grep -q 200; }
for i in $(seq 1 180); do
  if up http://localhost:8787/health && up http://localhost:8790/; then break; fi
  if [ "$(jobs -rp | wc -l | tr -d ' ')" -lt 2 ] || [ "$i" = 180 ]; then
    echo "Didn't start. Last lines of the logs:" >&2
    tail -n 15 "$logs/worker.log" "$logs/preview.log" >&2; exit 1
  fi
  sleep 1
done

at="-74.085,39.758,14"
[ "$mode" = sample ] && at="-74.0075,39.672,14"
url="http://localhost:8790/?api=http://localhost:8787&on=1&at=$at"
grep -E 'iPhone|Android' "$logs/worker.log" || true
cat <<MSG

Ready ($mode data). Open:  $url

  1. Barnegat Inlet: green lighted buoys and cans, red nuns, the jetty lights with their magenta flares.
  2. Zoom in to 14: the light characteristic and number beside each aid, like the chart (Fl G 2.5s "1").
  3. Rings: red = missing, off station or destroyed; amber = light out or damaged; grey dashed = temporary.
     Little Egg Inlet (?at=-74.297,39.482,13.5): Lighted Buoy 2 has been MISSING since Dec 2, 2025.
  4. Tap an aid: its card (Light List number, light, range, structure, remarks, status with its date).
  5. Zoom out: major lights from zoom 6, sea buoys from 8, the other lighted aids from 9, everything from 11.

For the Flutter example app on a simulator or phone, in another terminal tab:   bash local_app.sh
Ctrl-C here stops the Worker and the preview.
MSG
if [ "$(uname)" = Darwin ]; then open "$url"; fi
wait
