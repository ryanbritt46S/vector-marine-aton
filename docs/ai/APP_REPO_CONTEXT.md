# Context for the app repo (paste into its AGENTS.md / CLAUDE.md while wiring Buoys & lights)

The app uses the `vm_aton` Flutter package (repo `vector-marine-aton`, folder `flutter/vm_aton`) for the
**Buoys & lights** overlay: every US Coast Guard aid to navigation from Maine to Florida and Puerto Rico, with
the Local Notice to Mariners' outages, from the vm-aton Worker (`https://aton.vectormarine.us`). It's
independent of the other overlays' packages.

- Add the package (path or git dependency). It depends on `http` and `maplibre_gl` (>=0.20 <0.28); keep the
  app's maplibre_gl version.
- Init once at startup with the key the app already uses for `tiles.vectormarine.us` (from the backend), and a
  cache folder so the overlay draws offline: `VmAton.init(apiKey: key, cacheDir: await
  getApplicationCacheDirectory())` (path_provider).
- Map screen: one `AtonController()`. In `onMapCreated`: `AtonMapLibre.attach(controller, mapController, below:
  () => <lowest layer id of the weather overlays>, onFeatureTapped: (f) => showAtonCard(context, f,
  controller))`. `onStyleLoaded()` from `onStyleLoadedCallback` with the other overlays; `dispose()` both.
- Taps: in `onMapClick`, `final f = await atonLayer.tap(point, latLng)`. Non-null means it was an aid (the card
  is showing). Only when it's null, pass the tap to other overlays. Never send the tapped position anywhere.
- Overlays menu: "Buoys & lights" (subtitle "Coast Guard aids · outages from the Notice to Mariners") bound to
  `controller.enabled` / `controller.toggle()`. No new map buttons.
- While on: `AtonNote(controller: controller)` near the map's edge (data date, "Not for navigation", SAMPLE and
  stale lines), and `controller.meta?.attribution` with the map's attribution.
- The layers go under the style's `vm-overlays` anchor; the package reads its layers from the Worker's
  `style.json`. Don't touch map styles, the bathymetry, relief or contour layers.
- Not for navigation.
