// api.dart - client for the vm-aton Worker (aton.vectormarine.us), with an on-phone copy of the last answers.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

class AtonApiException implements Exception {
  AtonApiException(this.message, [this.status]);
  final String message;
  final int? status;
  @override
  String toString() => message;
}

/// Where the last meta.json, style.json, icons.json and the symbols are kept between app launches, so the
/// overlay still draws offline (the tiles themselves are kept by MapLibre's own cache).
abstract class AtonCache {
  Future<Uint8List?> read(String path);
  Future<void> write(String path, Uint8List bytes);
}

/// Keeps the files in a folder on the phone, e.g. `VmAton.init(cacheDir: await getApplicationCacheDirectory())`
/// (path_provider, in the app). A few hundred KB: the three JSON files and one set of symbols.
class DirectoryCache implements AtonCache {
  DirectoryCache(Directory dir) : root = Directory('${dir.path}/vm_aton');

  final Directory root;

  /// Only these paths map to files: meta.json, style.json, icons/icons.json, icons/<version>/<sym>[@Nx].png.
  File? _file(String path) {
    if (!RegExp(r'^(meta\.json|style\.json|icons/icons\.json|icons/[0-9a-f]{6,40}/[a-z0-9-]{1,40}(@[23]x)?\.png)$').hasMatch(path)) {
      return null;
    }
    return File('${root.path}/$path');
  }

  @override
  Future<Uint8List?> read(String path) async {
    final f = _file(path);
    if (f == null) return null;
    try {
      return await f.readAsBytes();
    } on FileSystemException {
      return null;
    }
  }

  @override
  Future<void> write(String path, Uint8List bytes) async {
    final f = _file(path);
    if (f == null) return;
    try {
      await f.parent.create(recursive: true);
      final tmp = File('${f.path}.part');
      await tmp.writeAsBytes(bytes, flush: true);
      await tmp.rename(f.path);
    } on FileSystemException {
      // a full disk only costs a download next time
    }
  }
}

/// Reads meta.json, style.json and icons/icons.json (re-checked with their ETags; the last copy kept on the phone
/// for offline) and the symbols (kept per icons version: they never change under a version). The API key goes
/// in the X-API-Key header; map tile URLs carry it as ?key= (MapLibre can't add headers), see [tileUrl].
class AtonApi {
  AtonApi({required this.baseUrl, this.apiKey = '', http.Client? client, this.cache}) : _client = client ?? http.Client();

  final String baseUrl, apiKey;
  final AtonCache? cache;
  final http.Client _client;
  final Map<String, (String, Map<String, dynamic>)> _json = {}; // path -> (etag, decoded)

  String get base => baseUrl.replaceAll(RegExp(r'/+$'), '');

  Uri uri(String path) => Uri.parse('$base/$path');

  Map<String, String> get _headers => {if (apiKey.isNotEmpty) 'X-API-Key': apiKey};

  /// The tile URL template for the map: this Worker, the tiles' [version] (so a new build never mixes with
  /// cached tiles of the old one) and the key.
  String tileUrl(String version) {
    final q = ['v=${Uri.encodeQueryComponent(version)}', if (apiKey.isNotEmpty) 'key=${Uri.encodeQueryComponent(apiKey)}'];
    return '$base/aton/{z}/{x}/{y}.mvt?${q.join('&')}';
  }

  /// meta.json, style.json or icons/icons.json. Unchanged since last time: not downloaded again. Offline (or the
  /// server down), the last one kept on the phone, if any. Not for a refused key.
  Future<Map<String, dynamic>> json(String path) async {
    final had = _json[path];
    try {
      final res = await _client
          .get(uri(path), headers: {..._headers, if (had != null) 'If-None-Match': had.$1})
          .timeout(const Duration(seconds: 20));
      if (res.statusCode == 304 && had != null) return had.$2;
      _check(res);
      final j = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
      final etag = res.headers['etag'];
      if (etag != null) {
        _json[path] = (etag, j);
      } else {
        _json.remove(path);
      }
      await cache?.write(path, res.bodyBytes);
      return j;
    } catch (e) {
      if (e is AtonApiException && (e.status == 401 || e.status == 403)) rethrow;
      if (had != null) return had.$2;
      final kept = await cache?.read(path);
      if (kept == null || kept.isEmpty) rethrow;
      return jsonDecode(utf8.decode(kept)) as Map<String, dynamic>;
    }
  }

  /// One symbol (PNG) of icons [version]: from the phone's cache, else the server (then cached).
  Future<Uint8List> icon(String file, String version) async {
    final name = file.split('/').last;
    final key = 'icons/$version/$name';
    final c = cache;
    if (c != null) {
      final b = await c.read(key);
      if (b != null && b.isNotEmpty) return b;
    }
    final res = await _client.get(uri(file), headers: _headers).timeout(const Duration(seconds: 30));
    _check(res);
    await c?.write(key, res.bodyBytes);
    return res.bodyBytes;
  }

  void _check(http.Response res) {
    if (res.statusCode == 200) return;
    throw AtonApiException(
        res.statusCode == 401 ? 'Not allowed (API key)' : 'Unavailable (HTTP ${res.statusCode})', res.statusCode);
  }

  void close() => _client.close();
}
