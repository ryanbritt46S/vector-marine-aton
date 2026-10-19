// A stand-in for the vm-aton Worker in tests: serves test/fixtures/site/ (meta.json, style.json and
// icons/icons.json of a SAMPLE build by the real job, see pipeline/tools/make_parity.py) with the key check and
// ETags; any icon PNG is a tiny made-up PNG. Records what was asked for.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vm_aton/src/api.dart';

const base = 'https://aton.test';
final png = Uint8List.fromList(base64Decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='));

class FakeWorker {
  FakeWorker({this.key = 'k1'});
  final String key;
  final requests = <String>[];
  final bodies = <String, String>{
    for (final f in ['meta.json', 'style.json', 'icons/icons.json']) f: File('test/fixtures/site/$f').readAsStringSync(),
  };

  /// Paths that fail (as if offline); '*' = everything.
  final failing = <String>{};

  late final client = MockClient((req) async {
    final path = req.url.path.substring(1);
    requests.add(path);
    if (req.headers['X-API-Key'] != key) return http.Response('{"error":"missing or invalid API key"}', 401);
    if (failing.contains(path) || failing.contains('*')) return http.Response('down', 503);
    final body = bodies[path];
    if (body != null) {
      final etag = '"${body.hashCode}"';
      if (req.headers['If-None-Match'] == etag) return http.Response('', 304, headers: {'etag': etag});
      return http.Response.bytes(utf8.encode(body), 200, headers: {'etag': etag, 'content-type': 'application/json'});
    }
    if (RegExp(r'^icons/[a-z0-9-]+(@[23]x)?\.png$').hasMatch(path)) return http.Response.bytes(png, 200);
    return http.Response('not found', 404);
  });
}

/// A cache in memory, to check what would be kept on the phone.
class MemoryCache implements AtonCache {
  final files = <String, Uint8List>{};
  @override
  Future<Uint8List?> read(String path) async => files[path];
  @override
  Future<void> write(String path, Uint8List bytes) async => files[path] = bytes;
}
