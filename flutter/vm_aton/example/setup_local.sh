#!/usr/bin/env bash
# One time, before running the example app against the local Worker (local_app.sh at the repo root runs it):
# creates the example's ios/ and android/ folders and lets it use plain http to your Mac.
# Only the example app is changed; the Vector Marine app itself never needs this.
#   bash setup_local.sh
set -euo pipefail
cd "$(dirname "$0")"
command -v flutter >/dev/null || { echo "Flutter isn't installed: https://docs.flutter.dev/get-started/install" >&2; exit 1; }

had_test=0; [ -e test/widget_test.dart ] && had_test=1
if [ ! -d ios ] || [ ! -d android ]; then
  # Adds only the missing files: lib/main.dart and pubspec.yaml stay as they are.
  flutter create --platforms=ios,android --org us.vectormarine --project-name vm_aton_example .
fi
# flutter create adds a counter-app test that doesn't apply here.
if [ "$had_test" = 0 ] && [ -e test/widget_test.dart ]; then rm -f test/widget_test.dart; rmdir test 2>/dev/null || true; fi

# iOS: allow http to localhost and name.local (App Transport Security), and say why it uses the local network.
plist=ios/Runner/Info.plist
if [ -f "$plist" ] && command -v plutil >/dev/null; then
  has() { plutil -extract "$1" xml1 -o - "$plist" >/dev/null 2>&1; }
  has NSAppTransportSecurity || plutil -insert NSAppTransportSecurity -json '{}' "$plist"
  has NSAppTransportSecurity.NSAllowsLocalNetworking \
    || plutil -insert NSAppTransportSecurity.NSAllowsLocalNetworking -bool YES "$plist"
  has NSLocalNetworkUsageDescription \
    || plutil -insert NSLocalNetworkUsageDescription -string "Reads buoys and lights from the test server on your Mac." "$plist"
  echo "iOS: local http allowed (ios/Runner/Info.plist)"
fi

# Android: allow http (cleartext) in debug builds only.
dbg=android/app/src/debug/AndroidManifest.xml
if [ -f "$dbg" ] && ! grep -q usesCleartextTraffic "$dbg"; then
  perl -0pi -e 's#</manifest>#    <application android:usesCleartextTraffic="true" />\n</manifest>#' "$dbg"
  echo "Android: http allowed in debug builds ($dbg)"
fi

flutter pub get
echo
echo "Set up. Run the app with:  bash local_app.sh   (at the repo root, with bash local.sh running)"
