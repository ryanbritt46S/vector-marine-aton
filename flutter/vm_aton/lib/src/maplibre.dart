// maplibre.dart - Buoys & lights drawn on a maplibre_gl map, as an overlay (never part of the map style).
//
//   final aton = AtonController();
//   AtonMapLibre? _atonLayer;
//   MapLibreMap(
//     onMapCreated: (c) => _atonLayer = AtonMapLibre.attach(aton, c,
//         below: () => _warningsLayer?.lowestLayerId,                       // stay under the weather overlays
//         onFeatureTapped: (f) => showAtonCard(context, f, aton)),          // the card as a bottom sheet
//     onStyleLoadedCallback: () => _atonLayer?.onStyleLoaded(),            // re-add after every style change
//     onMapClick: (point, latLng) async {
//       final f = await _atonLayer?.tap(point, latLng);                    // null: not for this layer
//       if (f == null) { /* pass the tap to the other overlays */ }
//     },
//   )
//   // In dispose(): _atonLayer?.dispose(); aton.dispose();
//
// What it adds, all under the style's "vm-overlays" anchor (and under [below] when given), from style.json:
//   images  vm-aton-<sym> (the symbols, at the screen's pixel ratio) and vm-aton-badge-<status> (the rings)
//   sources vm-aton and vm-aton-text: the same vector tiles (layer "aton"); the labels have their own source so
//           that if the map's fonts can't load (offline, nothing cached) only the labels go, never the symbols
//   layers  vm-aton-status (rings), vm-aton-symbols, vm-aton-labels (Fl G 4s "3", zoom 14+)
// Switching off removes the layers and sources it added and nothing else. maplibre_gl has no removeImage: the
// symbols stay registered under their vm-aton- names (harmless, and re-used when switched on again).
import 'dart:async' show scheduleMicrotask;
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show TargetPlatform, debugPrint, defaultTargetPlatform;
import 'package:maplibre_gl/maplibre_gl.dart';

import 'controller.dart';
import 'models.dart';

class AtonMapLibre {
  AtonMapLibre._(this.map, this.controller, {this.below, this.onFeatureTapped}) {
    controller.addListener(_sync);
  }

  /// Connect [controller] to the map (from MapLibreMap.onMapCreated). [below]: a layer id this overlay must stay
  /// under (e.g. the weather overlays' lowest layer), or null. [onFeatureTapped]: called by [tap] with the aid
  /// under the finger (show [AtonCard] / [showAtonCard]).
  static AtonMapLibre attach(AtonController controller, MapLibreMapController map,
          {String? Function()? below, void Function(AtonFeature feature)? onFeatureTapped}) =>
      AtonMapLibre._(map, controller, below: below, onFeatureTapped: onFeatureTapped);

  static const anchorLayer = 'vm-overlays';

  final MapLibreMapController map;
  final AtonController controller;
  final String? Function()? below;
  final void Function(AtonFeature feature)? onFeatureTapped;

  bool _styleReady = false, _busy = false, _again = false;
  int _gen = 0;
  String? _anchor;

  /// What's on the map now: the tile URL it was added with (null: nothing added), and the images added to this style.
  String? _shownUrl;
  final Set<String> _images = {};
  String? _imagesVersion;
  final List<String> _layers = [], _sources = [];

  /// This overlay's lowest layer while it's on the map (for overlays that must stay under it).
  String? get lowestLayerId => _layers.isEmpty ? null : _layers.first;

  /// Call from MapLibreMap.onStyleLoadedCallback: a new style has none of our images, sources or layers.
  Future<void> onStyleLoaded() async {
    _gen++;
    _shownUrl = null;
    _images.clear();
    _imagesVersion = null;
    _layers.clear();
    _sources.clear();
    final ids = await map.getLayerIds();
    _anchor = ids.contains(anchorLayer) ? anchorLayer : null;
    _styleReady = true;
    await _sync();
  }

  Future<void> _sync() async {
    if (!_styleReady) return;
    if (_busy) {
      _again = true;
      return;
    }
    _busy = true;
    try {
      do {
        _again = false;
        await _apply();
      } while (_again);
    } catch (e) {
      debugPrint('vm_aton: layer: $e');
    } finally {
      _busy = false;
      if (_again) scheduleMicrotask(_sync);
    }
  }

  Future<String?> _belowId() async {
    final want = below?.call();
    if (want != null && (await map.getLayerIds()).contains(want)) return want;
    return _anchor;
  }

  Future<void> _apply() async {
    final c = controller;
    final url = c.tileUrl;
    if (!c.enabled || !c.ready || url == null) {
      await _remove();
      return;
    }
    final st = c.style!, ic = c.icons!;
    final key = '$url|${ic.version}';
    if (_shownUrl == key) return;
    await _remove(); // a new build of the tiles or new symbols: the source again with the new version in its URL
    final gen = _gen;
    if (_imagesVersion != ic.version) {
      _images.clear(); // addImage replaces an image of the same name
      _imagesVersion = ic.version;
    }
    // the symbols: each PNG at the screen's ratio (both platforms read it at device density)
    for (final e in c.images.entries) {
      final name = '${ic.prefix}${e.key}';
      if (_images.contains(name)) continue;
      await map.addImage(name, e.value);
      if (gen != _gen) return;
      _images.add(name);
    }
    final before = await _belowId();
    if (gen != _gen) return;
    try {
      for (final s in st.sources) {
        await map.addSource(s.id, VectorSourceProperties(tiles: [url], minzoom: s.minzoom, maxzoom: s.maxzoom,
            attribution: s.attribution));
        if (gen != _gen) return;
        _sources.add(s.id);
      }
      for (final l in st.layers) {
        if (l.type != 'symbol') continue; // all of the overlay's layers are symbol layers (style.json)
        // Not interactive: an interactive layer swallows the tap before onMapClick (and maplibre_gl's
        // onFeatureTapped hands over only an id); tap() finds the aid with queryRenderedFeaturesInRect.
        await map.addSymbolLayer(l.source, l.id, SymbolLayerProperties.fromJson(l.properties),
            sourceLayer: l.sourceLayer, belowLayerId: before, minzoom: l.minzoom, maxzoom: l.maxzoom,
            filter: l.filter, enableInteraction: false);
        if (gen != _gen) return;
        _layers.add(l.id);
      }
      _shownUrl = key;
    } catch (_) {
      await _remove(force: true);
      rethrow;
    }
  }

  Future<void> _quietly(Future<void> Function() f) async {
    try {
      await f();
    } catch (_) {/* not there */}
  }

  Future<void> _remove({bool force = false}) async {
    if (!force && _shownUrl == null && _layers.isEmpty && _sources.isEmpty) return;
    final st = controller.style;
    final layers = {..._layers, if (force && st != null) ...st.layers.map((l) => l.id)};
    final sources = {..._sources, if (force && st != null) ...st.sources.map((s) => s.id)};
    for (final id in layers.toList().reversed) {
      await _quietly(() => map.removeLayer(id));
    }
    for (final id in sources) {
      await _quietly(() => map.removeSource(id));
    }
    _layers.clear();
    _sources.clear();
    _shownUrl = null;
  }

  /// A tap (from MapLibreMap.onMapClick): the aid under the finger, nearest first, or null when the tap isn't for
  /// this layer (it's off, or no aid there: pass it on). Calls [onFeatureTapped] with it. Nothing is sent anywhere.
  Future<AtonFeature?> tap(math.Point<double> point, LatLng at) async {
    if (_shownUrl == null || !controller.enabled) return null;
    try {
      // Android hands over the tap and takes the query box in physical pixels, iOS in points
      final views = ui.PlatformDispatcher.instance.views;
      final dpr = defaultTargetPlatform == TargetPlatform.android && views.isNotEmpty ? views.first.devicePixelRatio : 1.0;
      final hits = await map.queryRenderedFeaturesInRect(
          ui.Rect.fromCenter(center: ui.Offset(point.x, point.y), width: 30 * dpr, height: 30 * dpr), List.of(_layers), null);
      final feats = [for (final h in hits) AtonFeature.fromQuery(Map<String, dynamic>.from(h as Map))]
          .where((f) => f.id.isNotEmpty)
          .toList();
      if (feats.isEmpty) return null;
      AtonFeature best = feats.first;
      var bestD = double.infinity;
      for (final f in feats) {
        if (f.lat == null || f.lon == null) continue;
        final p = await map.toScreenLocation(LatLng(f.lat!, f.lon!));
        // the tap and toScreenLocation use the same platform pixels (Android: physical, iOS: points)
        final d = math.pow(p.x - point.x, 2) + math.pow(p.y - point.y, 2) - f.rank * 1e-3;
        if (d < bestD) {
          bestD = d.toDouble();
          best = f;
        }
      }
      onFeatureTapped?.call(best);
      return best;
    } catch (err) {
      debugPrint('vm_aton: tap: $err');
      return null;
    }
  }

  void dispose() => controller.removeListener(_sync);
}
