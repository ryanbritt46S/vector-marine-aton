#!/usr/bin/env bash
# Run the Flutter example app (Buoys & lights overlay) against the local Worker that local.sh starts
# (run local.sh first, in another tab).
#
#   bash local_app.sh                  iOS Simulator
#   bash local_app.sh android          Android emulator (start one in Android Studio's Device Manager first)
#   bash local_app.sh iphone           an iPhone on this Wi-Fi (plugged in, set up for development in Xcode)
#   bash local_app.sh android-phone    an Android phone on this Wi-Fi (USB debugging on)
#   BATHY_KEY=yourkey bash local_app.sh    the Vector Marine chart underneath (else a plain demo map)
#
# Then: Overlays -> Buoys & lights, zoom in on an inlet, tap a buoy. The first run takes a few minutes (iOS pods /
# Android Gradle).
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
target="${1:-ios}"
usage() { sed -n '5,9p' "$0" | sed 's/^# //' >&2; }

command -v flutter >/dev/null || { echo "Flutter isn't installed: https://docs.flutter.dev/get-started/install" >&2; exit 1; }
curl -s -m 2 -o /dev/null http://localhost:8787/health \
  || { echo "The local Worker isn't running. In another terminal tab:  bash local.sh" >&2; exit 1; }

name="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
dev=()
case "$target" in
  ios) host=localhost ;;
  android) host=10.0.2.2; dev=(-d emulator) ;;
  iphone) host="$name.local" ;;
  android-phone)
    [ -n "$ip" ] || { echo "Couldn't find this Mac's Wi-Fi address (ipconfig getifaddr en0)." >&2; exit 1; }
    host="$ip" ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown target \"$target\"." >&2; usage; exit 1 ;;
esac

cd "$root/flutter/vm_aton/example"
if [ ! -d ios ] || [ ! -d android ]; then bash setup_local.sh; fi

if [ "$target" = ios ]; then
  # The iOS Simulator comes with Xcode (not the Command Line Tools).
  devdir="$(xcode-select -p 2>/dev/null || true)"
  if ! xcrun simctl help >/dev/null 2>&1; then
    cat >&2 <<EOF
The iOS Simulator needs Xcode, and this Mac's developer tools point to: ${devdir:-nothing}
  1. Install Xcode from the App Store and open it once (it offers to add the iOS simulator; say yes).
  2. Then run:  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
Or use an Android emulator instead:  bash local_app.sh android
EOF
    exit 1
  fi
  booted() { xcrun simctl list devices booted 2>/dev/null | grep -Eo '\([0-9A-F-]{36}\) \(Booted\)' | head -1 | cut -c2-37 || true; }
  if [ -z "$(booted)" ]; then
    phone="$(xcrun simctl list devices available 2>/dev/null | grep -E '^[[:space:]]+iPhone' | grep -Eo '[0-9A-F-]{36}' | head -1 || true)"
    if [ -z "$phone" ]; then
      echo "No iPhone simulator is installed. In Xcode: Settings > Components, add an iOS simulator, then try again." >&2
      exit 1
    fi
    echo "Starting an iPhone simulator..."
    xcrun simctl boot "$phone" 2>/dev/null || true
    open "$devdir/Applications/Simulator.app" 2>/dev/null || open -a Simulator 2>/dev/null || true
    for i in $(seq 1 90); do [ -n "$(booted)" ] && break; sleep 1; done
  fi
  udid="$(booted || true)"
  [ -n "$udid" ] || { echo "The iPhone simulator didn't start. Open Xcode > Open Developer Tool > Simulator, then try again." >&2; exit 1; }
  dev=(-d "$udid")
fi
if [ "$target" = android ] && ! flutter devices --machine 2>/dev/null | grep -q '"id": *"emulator-'; then
  echo "No Android emulator is running. Start one in Android Studio (Device Manager > the play button), then try again." >&2
  echo "From the terminal: flutter emulators   then   flutter emulators --launch <id>" >&2
  exit 1
fi

args=(--dart-define=ATON_URL="http://$host:8787")
shown="flutter run ${dev[*]+${dev[*]}} ${args[*]}"
if [ -n "${BATHY_KEY:-}" ]; then args+=(--dart-define=BATHY_KEY="$BATHY_KEY"); shown="$shown --dart-define=BATHY_KEY=…"; fi
echo "Note: with BATHY_KEY set the app sends it to the local Worker too; local.sh's Worker accepts any key."
echo "$shown"
echo
exec flutter run ${dev[@]+"${dev[@]}"} "${args[@]}"
