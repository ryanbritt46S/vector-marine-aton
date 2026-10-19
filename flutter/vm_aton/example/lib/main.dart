// How the Buoys & lights overlay plugs into the Vector Marine map screen (a sketch to copy from, written
// against maplibre_gl 0.22+).
//
//   flutter run --dart-define=BATHY_KEY=your_app_key
//
// Local test, nothing on Cloudflare: `bash local.sh` at the repo root, then `bash local_app.sh` in another
// tab (it does all of the below). By hand: `bash setup_local.sh` here once, then
//   iOS Simulator:     flutter run --dart-define=ATON_URL=http://localhost:8787
//   Android emulator:  flutter run --dart-define=ATON_URL=http://10.0.2.2:8787
//   Phone on Wi-Fi:    the address local.sh prints (your Mac's name.local or IP), port 8787
// (add --dart-define=BATHY_KEY=... too so the Vector Marine chart loads underneath).
import 'dart:io' show Directory;

import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:vm_aton/vm_aton.dart';

const _key = String.fromEnvironment('BATHY_KEY');
const _tiles = 'https://tiles.vectormarine.us';
const _aton = String.fromEnvironment('ATON_URL', defaultValue: VmAton.defaultBaseUrl);

// Without a key, a plain demo map so the overlay can still be tried (it has no "vm-overlays" anchor: the
// overlay then goes on top).
const _demoStyle = 'https://demotiles.maplibre.org/style.json';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // In the app: cacheDir: await getApplicationCacheDirectory() (path_provider), so the overlay still draws
  // offline. Here: the system temp folder.
  VmAton.init(baseUrl: _aton, apiKey: _key, cacheDir: Directory.systemTemp);
  runApp(const MaterialApp(debugShowCheckedModeBanner: false, home: MapScreen()));
}

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});
  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final _aton = AtonController();
  AtonMapLibre? _layer;

  @override
  void dispose() {
    _layer?.dispose();
    _aton.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Stack(children: [
          MapLibreMap(
            styleString: _key.isEmpty ? _demoStyle : '$_tiles/styles/bathy-combo.json?key=$_key',
            initialCameraPosition: const CameraPosition(target: LatLng(39.758, -74.085), zoom: 13.5),
            onMapCreated: (c) => _layer = AtonMapLibre.attach(_aton, c,
                onFeatureTapped: (f) => showAtonCard(context, f, _aton)),
            onStyleLoadedCallback: () => _layer?.onStyleLoaded(),
            onMapClick: (point, latLng) async {
              final f = await _layer?.tap(point, latLng);
              if (f == null) debugPrint('not an aid: pass the tap to the other overlays');
            },
          ),
          Positioned(
            left: 10,
            top: MediaQuery.paddingOf(context).top + 10,
            right: 120,
            child: AtonNote(controller: _aton),
          ),
          Positioned(
            right: 10,
            top: MediaQuery.paddingOf(context).top + 6,
            child: ListenableBuilder(
              listenable: _aton,
              builder: (context, _) => FilledButton.tonal(
                onPressed: _aton.toggle,
                child: Text(_aton.enabled ? 'Buoys & lights: on' : 'Overlays'),
              ),
            ),
          ),
        ]),
      );
}
