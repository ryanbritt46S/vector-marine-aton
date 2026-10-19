// controller.dart - Buoys & lights: on/off, the last meta/style/icons (kept for offline), the symbols at the
// screen's pixel ratio, the data date and staleness lines.
import 'dart:async';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show ChangeNotifier, debugPrint;

import 'api.dart';
import 'config.dart';
import 'models.dart';
import 'words.dart';

/// State of the Buoys & lights overlay. [AtonMapLibre] draws it on maplibre_gl; [AtonCard] is the tap card.
/// Data: GET /meta.json, /style.json and /icons/icons.json when switched on (then meta.json every hour while on),
/// the symbols once per icons version, and the map tiles (MapLibre fetches and caches those itself).
///
///   final aton = AtonController();
///   aton.toggle();                                      // from Overlays -> Buoys & lights
class AtonController extends ChangeNotifier {
  AtonController({AtonApi? api, DateTime Function()? clock, this.refreshEvery = const Duration(hours: 1), int? pixelRatio})
      : _api = api,
        _clock = clock ?? DateTime.now,
        ratio = pixelRatio ?? _screenRatio();

  final Duration refreshEvery;
  final AtonApi? _api;
  AtonApi get api => _api ?? VmAton.instance.api;
  final DateTime Function() _clock;

  /// The symbols' pixel ratio (1, 2 or 3): both platforms read an image at the screen's density, so a 2x screen
  /// gets the @2x PNG and the symbol shows at its designed size.
  final int ratio;

  bool enabled = false, loading = false;
  String? error;
  AtonMeta? meta;
  AtonStyle? style;
  AtonIcons? icons;

  /// sym -> PNG at [ratio], ready for map.addImage (named [AtonIcons.prefix] + sym).
  final Map<String, Uint8List> images = {};

  Timer? _refresh;
  bool _disposed = false;

  static int _screenRatio() {
    final views = ui.PlatformDispatcher.instance.views;
    final dpr = views.isEmpty ? 2.0 : views.first.devicePixelRatio;
    return dpr >= 2.5 ? 3 : dpr >= 1.5 ? 2 : 1;
  }

  /// Everything the map needs is here (style, symbols, tiles' version).
  bool get ready => meta != null && style != null && icons != null && images.isNotEmpty;

  /// The tiles' URL template (with the version and the key).
  String? get tileUrl => meta == null ? null : api.tileUrl(meta!.tilesVersion);

  DateTime get now => _clock();

  /// "Buoys & lights · Coast Guard data of Oct 19, 2026 · Not for navigation", for the line under the map.
  String get noteLine => meta == null
      ? 'Buoys & lights · Not for navigation'
      : 'Buoys & lights · Coast Guard data of ${fmtDate(meta!.dataDate)} · Not for navigation';

  /// "Coast Guard data not updated for 3 days" when the last meta.json is older than 72 hours, else null.
  String? get staleLine {
    final m = meta;
    if (m == null) return null;
    final s = staleText(m.generatedAt, m.staleAfterHours, _clock().millisecondsSinceEpoch);
    return s.isEmpty ? null : s;
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> start() async {
    enabled = true;
    _notify();
    await refresh();
    if (!enabled || _disposed) return;
    _refresh?.cancel();
    _refresh = Timer.periodic(refreshEvery, (_) => refresh());
  }

  void stop() {
    enabled = false;
    _refresh?.cancel();
    _refresh = null;
    _notify();
  }

  void toggle() => enabled ? stop() : start();

  /// Re-read meta.json (and style.json / icons when their versions changed). A new build of the tiles changes
  /// [tileUrl]; AtonMapLibre then swaps the source.
  Future<void> refresh() async {
    loading = true;
    if (enabled) _notify();
    try {
      final m = AtonMeta.fromJson(await api.json('meta.json'));
      if (m.version != 1) throw AtonApiException('This app is too old for the Buoys & lights data (version ${m.version})');
      final restyle = style == null || meta?.tilesVersion != m.tilesVersion;
      if (restyle) style = AtonStyle.fromJson(await api.json('style.json'));
      if (icons == null || icons!.version != m.iconsVersion || images.isEmpty) {
        final ic = AtonIcons.fromJson(await api.json('icons/icons.json'));
        final got = <String, Uint8List>{};
        await Future.wait([
          for (final sym in ic.files.keys)
            () async {
              final f = ic.file(sym, ratio);
              if (f != null) got[sym] = await api.icon(f, ic.version);
            }(),
        ]);
        icons = ic;
        images
          ..clear()
          ..addAll(got);
      }
      meta = m;
      error = null;
    } catch (e) {
      error = e is AtonApiException ? e.message : 'Buoys & lights are unavailable right now';
      debugPrint('vm_aton: $e');
    }
    loading = false;
    if (enabled) _notify();
  }

  @override
  void dispose() {
    _disposed = true;
    _refresh?.cancel();
    super.dispose();
  }
}
