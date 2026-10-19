# vm_aton

Buoys & lights for the Vector Marine map: every US Coast Guard aid to navigation from Maine to Florida and
Puerto Rico, drawn with our own chart-like symbols, with the outages and temporary changes from the Local
Notice to Mariners as red, amber and grey rings, and a card for each aid.

```dart
VmAton.init(apiKey: key, cacheDir: await getApplicationCacheDirectory());

final aton = AtonController();                        // aton.toggle() from Overlays -> Buoys & lights

MapLibreMap(
  onMapCreated: (c) => layer = AtonMapLibre.attach(aton, c,
      below: () => weatherLowest,                       // stay under the weather overlays
      onFeatureTapped: (f) => showAtonCard(context, f, aton)),
  onStyleLoadedCallback: () => layer?.onStyleLoaded(),
  onMapClick: (p, ll) async {
    final f = await layer?.tap(p, ll);                  // null: not for this layer
  },
);
AtonNote(controller: aton);                             // "Coast Guard data of Oct 19, 2026 · Not for navigation"
```

`example/lib/main.dart` is a complete host screen. Behaviour: `../../docs/SPEC.md`; app wiring:
`../../docs/ai/APP_REPO_CONTEXT.md`. Not for navigation.
