# flutter/vm_aton/: the Flutter package

Read the root `AGENTS.md` first. Everything the app shows for Buoys & lights. Written without a Flutter SDK in
reach: **not yet compiled**. Work package 1 is `flutter analyze` + `flutter test` on Flutter 3.41.x and a run of
`example/` on a device.

## Files

| File | What |
|---|---|
| `lib/vm_aton.dart` | Public exports |
| `lib/src/config.dart` | `VmAton.init({baseUrl, apiKey, cacheDir, cache, client})`, `VmAton.instance.api` |
| `lib/src/api.dart` | `AtonApi`: meta/style/icons.json with ETag (the last copy kept on the phone for offline), symbols per icons version, `tileUrl(version)`; `DirectoryCache` |
| `lib/src/models.dart` | `AtonMeta`, `AtonStyle` (`AtonSourceDef`, `AtonLayerDef`), `AtonIcons`, `AtonFeature` (one aid's tile properties) |
| `lib/src/words.dart` | Status codes in plain English, light characteristic spelled out, kinds, dates, `cardFor`, `staleText` (**same as** `pipeline/vmaton/words.py` and `preview/aton.js`) |
| `lib/src/controller.dart` | `AtonController` (ChangeNotifier): on/off, meta + style + icons, the symbols at the screen's pixel ratio, `tileUrl`, `noteLine`, `staleLine` |
| `lib/src/maplibre.dart` | `AtonMapLibre.attach(controller, map, below:, onFeatureTapped:)`: images, the two vector sources, the three symbol layers from style.json, under `vm-overlays`; `onStyleLoaded()`, `tap()`, `lowestLayerId` |
| `lib/src/widgets.dart` | `AtonCard` / `AtonCard.of`, `showAtonCard` (bottom sheet), `AtonNote` (data date, SAMPLE, stale) |
| `test/` | words (parity fixture from Python, the same file the preview's test reads), controller + API on a SAMPLE site, widgets |
| `example/` | Bare host app: Overlays button, the layer, the card (`--dart-define=ATON_URL=…`, `BATHY_KEY=…`) |

## Public API (what the app uses; keep it stable)

`VmAton.init(...)`, `AtonController()` (`toggle`, `start`, `stop`, `refresh`, `enabled`, `meta`, `error`,
`noteLine`, `staleLine`), `AtonMapLibre.attach(controller, map, below:, onFeatureTapped:)` with
`onStyleLoaded()`, `tap()`, `lowestLayerId`, `dispose()`, `AtonCard` / `AtonCard.of`, `showAtonCard`,
`AtonNote`, `AtonFeature`.

## If the analyzer or a newer Flutter reports problems

- Change only what the error needs. Don't refactor, rename public API or reword while fixing.
- `words.dart` is pinned by `words_test.dart` (the parity fixture from Python, also read by the preview's
  test): if a fix changes a word, the fix is wrong.
- maplibre_gl calls used: `addImage(name, bytes)`, `addSource(id, VectorSourceProperties(tiles:, minzoom:,
  maxzoom:, attribution:))`, `addSymbolLayer(sourceId, layerId, SymbolLayerProperties.fromJson(...),
  sourceLayer:, belowLayerId:, minzoom:, maxzoom:, filter:, enableInteraction: false)`, `removeLayer`,
  `removeSource`, `getLayerIds`, `queryRenderedFeaturesInRect`, `toScreenLocation`. If the app's maplibre_gl
  version names one differently, adapt the call and say so in the commit.
- **To check first on a device** (written from the maplibre_gl sources, never run):
  1. `SymbolLayerProperties.fromJson` takes the style spec's names (`icon-image`, `text-field`, …) and the
     expressions as lists. If it doesn't exist in the app's version, build the properties by hand from
     `AtonLayerDef.layout` / `paint` (the same keys, camelCased).
  2. `addImage` with the @2x / @3x PNG shows the symbol at its designed size (48 points canvas, about 13 points
     wide at zoom 14) on both platforms. If it shows 2-3x too small or large, the platform isn't reading the
     PNG at device density: pass the 1x PNG and scale `icon-size`, or the reverse.
  3. `toScreenLocation` returns the same kind of pixels as `onMapClick`'s point (Android physical, iOS points);
     `tap()` compares them.
- `setLayerProperties` sends unset properties as null and the platforms reset them: this package never calls
  it. A change (new tiles version, style change) removes and re-adds the source and layers instead.
- Layers are added with `enableInteraction: false`: an interactive layer swallows the tap before
  `onMapClick`, and maplibre_gl's own `onFeatureTapped` reports only a feature id. `tap()` finds the aid with
  `queryRenderedFeaturesInRect` and calls this package's `onFeatureTapped` with all its properties.
- maplibre_gl has no `removeImage`: the symbols stay registered (under `vm-aton-…`) after switching off.
- Prefer forms that work from Flutter 3.19 to the current stable (no `Color.withValues`, no `toARGB32`).

## Rules for changes here

- Words come from fixed templates (`words.dart`), the same as `pipeline/vmaton/words.py` and `preview/aton.js`.
- The look comes from `style.json` (the job writes it; the preview uses the same file): don't hard-code
  layer properties here.
- Nothing about the user leaves the phone: the tap is handled on the phone, no position or analytics is sent.
  The only requests are meta/style/icons (when switched on, then hourly) and the map tiles.
- Layers go under the style's `vm-overlays` anchor and under [below] (the weather overlays). No map buttons.
- Show `AtonNote` (data date, "Not for navigation") while the layer is on, and the attribution from meta.json.

## Testing

```bash
cd flutter/vm_aton
flutter pub get
flutter analyze
flutter test
```
On a device: `bash local.sh` at the repo root, then `bash local_app.sh` (or `android`), then
`docs/QA_CHECKLIST.md`.
