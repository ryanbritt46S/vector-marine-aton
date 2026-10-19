// models.dart - meta.json, style.json, icons/icons.json and one aid's tile properties (docs/API.md).

Map<String, dynamic> _map(Object? v) => v == null ? <String, dynamic>{} : Map<String, dynamic>.from(v as Map);
double? _d(Object? v) => v == null ? null : (v as num).toDouble();

/// meta.json: when the data is from, the tiles' and icons' versions, counts.
class AtonMeta {
  const AtonMeta({required this.version, required this.sample, required this.generatedAt, required this.run,
      required this.dataDate, required this.staleAfterHours, required this.attribution, required this.note,
      required this.tilesVersion, required this.minzoom, required this.maxzoom, required this.iconsVersion,
      this.counts = const {}});

  factory AtonMeta.fromJson(Map<String, dynamic> j) {
    final t = _map(j['tiles']);
    return AtonMeta(
      version: (j['version'] as num?)?.toInt() ?? 0,
      sample: j['sample'] == true,
      generatedAt: j['generated_at'] as String? ?? '',
      run: j['run'] as String? ?? '',
      dataDate: j['data_date'] as String? ?? '',
      staleAfterHours: (j['stale_after_hours'] as num?)?.toDouble() ?? 72,
      attribution: j['attribution'] as String? ?? '',
      note: j['note'] as String? ?? '',
      tilesVersion: t['version'] as String? ?? '',
      minzoom: _d(t['minzoom']) ?? 6,
      maxzoom: _d(t['maxzoom']) ?? 14,
      iconsVersion: _map(j['icons'])['version'] as String? ?? '',
      counts: _map(j['counts']),
    );
  }

  final int version;
  final bool sample;
  final String generatedAt, run, dataDate, attribution, note, tilesVersion, iconsVersion;
  final double staleAfterHours, minzoom, maxzoom;
  final Map<String, dynamic> counts;
}

/// One source of style.json ("{base}" in its url is this Worker).
class AtonSourceDef {
  const AtonSourceDef({required this.id, required this.minzoom, required this.maxzoom, this.attribution});
  final String id;
  final double minzoom, maxzoom;
  final String? attribution;
}

/// One layer of style.json, as MapLibre's style spec has it.
class AtonLayerDef {
  const AtonLayerDef({required this.id, required this.type, required this.source, required this.sourceLayer,
      this.minzoom, this.maxzoom, this.filter, this.layout = const {}, this.paint = const {}});

  factory AtonLayerDef.fromJson(Map<String, dynamic> j) => AtonLayerDef(
        id: j['id'] as String,
        type: j['type'] as String,
        source: j['source'] as String,
        sourceLayer: j['source-layer'] as String? ?? 'aton',
        minzoom: _d(j['minzoom']),
        maxzoom: _d(j['maxzoom']),
        filter: j['filter'],
        layout: _map(j['layout']),
        paint: _map(j['paint']),
      );

  final String id, type, source, sourceLayer;
  final double? minzoom, maxzoom;
  final Object? filter;
  final Map<String, dynamic> layout, paint;

  /// Layout and paint together, with the style spec's names (what SymbolLayerProperties.fromJson reads).
  Map<String, dynamic> get properties => {...layout, ...paint};
}

/// style.json: the overlay's sources and layers (the reference for how it looks, same as the preview).
class AtonStyle {
  const AtonStyle({required this.sources, required this.layers, required this.imagePrefix, required this.anchor,
      required this.attribution});

  factory AtonStyle.fromJson(Map<String, dynamic> j) => AtonStyle(
        sources: [
          for (final e in _map(j['sources']).entries)
            AtonSourceDef(
              id: e.key,
              minzoom: _d(_map(e.value)['minzoom']) ?? 6,
              maxzoom: _d(_map(e.value)['maxzoom']) ?? 14,
              attribution: _map(e.value)['attribution'] as String?,
            ),
        ],
        layers: [for (final l in (j['layers'] as List? ?? const [])) AtonLayerDef.fromJson(_map(l))],
        imagePrefix: j['image_prefix'] as String? ?? 'vm-aton-',
        anchor: j['anchor'] as String? ?? 'vm-overlays',
        attribution: j['attribution'] as String? ?? '',
      );

  final List<AtonSourceDef> sources;
  final List<AtonLayerDef> layers;
  final String imagePrefix, anchor, attribution;
}

/// icons/icons.json: every symbol, its PNG per pixel ratio (1, 2, 3).
class AtonIcons {
  const AtonIcons({required this.version, required this.prefix, required this.files, this.titles = const {}});

  factory AtonIcons.fromJson(Map<String, dynamic> j) {
    final files = <String, Map<int, String>>{};
    final titles = <String, String>{};
    for (final e in _map(j['icons']).entries) {
      final v = _map(e.value);
      files[e.key] = {for (final f in _map(v['files']).entries) int.parse(f.key): f.value as String};
      titles[e.key] = v['title'] as String? ?? e.key;
    }
    return AtonIcons(version: j['version'] as String? ?? '', prefix: j['prefix'] as String? ?? 'vm-aton-',
        files: files, titles: titles);
  }

  final String version, prefix;
  final Map<String, Map<int, String>> files;
  final Map<String, String> titles;

  /// The file of [sym] at [ratio] (the nearest there is).
  String? file(String sym, int ratio) {
    final f = files[sym];
    if (f == null || f.isEmpty) return null;
    return f[ratio] ?? f[f.keys.reduce((a, b) => (a - ratio).abs() <= (b - ratio).abs() ? a : b)];
  }
}

/// One aid as the tiles have it (properties in docs/API.md); [props] keeps everything for the card.
class AtonFeature {
  const AtonFeature(this.props, {this.lat, this.lon});

  factory AtonFeature.fromQuery(Map<String, dynamic> f) {
    final g = _map(f['geometry']);
    final c = g['coordinates'];
    return AtonFeature(_map(f['properties']),
        lon: c is List && c.length >= 2 ? (c[0] as num).toDouble() : null,
        lat: c is List && c.length >= 2 ? (c[1] as num).toDouble() : null);
  }

  final Map<String, dynamic> props;
  final double? lat, lon;

  String get id => props['id']?.toString() ?? '';
  String get name => props['name']?.toString() ?? '';
  String get sym => props['sym']?.toString() ?? 'other';
  String get kind => props['kind']?.toString() ?? 'other';

  /// "missing", "fault", "temporary", or "" when the aid has no current notice.
  String get status => props['status']?.toString() ?? '';
  int get rank => (props['rank'] as num?)?.toInt() ?? 0;
}
