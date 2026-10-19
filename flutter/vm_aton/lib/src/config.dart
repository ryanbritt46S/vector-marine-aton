// config.dart - one place to set the Buoys & lights server, key and the on-phone cache.
import 'dart:io' show Directory;

import 'package:http/http.dart' as http;

import 'api.dart';

/// Set up once, before the map screen:
///   VmAton.init(apiKey: key, cacheDir: await getApplicationCacheDirectory());   // production
///   VmAton.init(baseUrl: 'http://10.0.2.2:8787');                                // local Worker (Android emulator)
/// The key is the same one the app already uses for tiles.vectormarine.us (fetched from your backend).
/// Without [cacheDir] the last meta, style and icons are only kept in memory while the app runs.
class VmAton {
  VmAton._(this.api);

  static const defaultBaseUrl = 'https://aton.vectormarine.us';
  static VmAton? _instance;

  static VmAton get instance => _instance ?? (throw StateError('Call VmAton.init(...) before using Buoys & lights'));

  static bool get isInitialized => _instance != null;

  static VmAton init({String baseUrl = defaultBaseUrl, String apiKey = '', Directory? cacheDir, AtonCache? cache,
      http.Client? client}) {
    _instance?.api.close();
    return _instance = VmAton._(AtonApi(
        baseUrl: baseUrl, apiKey: apiKey, client: client,
        cache: cache ?? (cacheDir == null ? null : DirectoryCache(cacheDir))));
  }

  final AtonApi api;
}
