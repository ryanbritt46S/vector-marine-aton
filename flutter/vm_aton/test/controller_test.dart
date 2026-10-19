// AtonController and AtonApi against a stand-in Worker serving a SAMPLE build (test/fixtures/site/).
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vm_aton/src/api.dart';
import 'package:vm_aton/src/controller.dart';

import 'fake_worker.dart';

final _meta = Map<String, dynamic>.from(jsonDecode(File('test/fixtures/site/meta.json').readAsStringSync()) as Map);
final _icons = Map<String, dynamic>.from(jsonDecode(File('test/fixtures/site/icons/icons.json').readAsStringSync()) as Map);
final _generated = DateTime.parse(_meta['generated_at'] as String);

AtonController _controller(FakeWorker w, {MemoryCache? cache, String key = 'k1', DateTime? now}) => AtonController(
    api: AtonApi(baseUrl: '$base/', apiKey: key, client: w.client, cache: cache),
    clock: () => now ?? _generated.add(const Duration(hours: 5)),
    pixelRatio: 2);

void main() {
  test('on: meta, style, icons and every symbol at 2x; off', () async {
    final w = FakeWorker();
    final c = _controller(w);
    await c.start();
    expect(c.enabled, isTrue);
    expect(c.error, isNull);
    expect(c.ready, isTrue);
    expect(c.meta!.sample, isTrue);
    expect(c.meta!.tilesVersion, (_meta['tiles'] as Map)['version']);
    expect(c.style!.layers.map((l) => l.id), ['vm-aton-status', 'vm-aton-symbols', 'vm-aton-labels']);
    expect(c.style!.sources.map((s) => s.id), ['vm-aton', 'vm-aton-text']);
    expect(c.style!.layers[1].properties['icon-image'], ['concat', 'vm-aton-', ['get', 'sym']]);
    expect(c.images.keys.toSet(), (_icons['icons'] as Map).keys.toSet());
    expect(w.requests.where((p) => p.endsWith('.png')).every((p) => p.endsWith('@2x.png')), isTrue);
    expect(c.tileUrl, '$base/aton/{z}/{x}/{y}.mvt?v=${(_meta['tiles'] as Map)['version']}&key=k1');
    expect(c.noteLine, 'Buoys & lights · Coast Guard data of Oct 19, 2026 · Not for navigation');
    expect(c.staleLine, isNull);
    c.stop();
    expect(c.enabled, isFalse);
    c.dispose();
  });

  test('refresh: nothing downloaded again when unchanged', () async {
    final w = FakeWorker();
    final c = _controller(w);
    await c.start();
    final pngs = w.requests.where((p) => p.endsWith('.png')).length;
    w.requests.clear();
    await c.refresh();
    expect(w.requests, ['meta.json']);                 // 304: same tiles, same icons
    expect(pngs, (_icons['icons'] as Map).length);
    c.dispose();
  });

  test('stale after 72 hours (on the phone\'s clock)', () async {
    final c = _controller(FakeWorker(), now: _generated.add(const Duration(hours: 97)));
    await c.start();
    expect(c.staleLine, 'Coast Guard data not updated for 4 days');
    c.dispose();
  });

  test('offline: the last copy on the phone draws the overlay; a refused key is an error', () async {
    final cache = MemoryCache();
    final online = _controller(FakeWorker(), cache: cache);
    await online.start();
    expect(cache.files.keys, containsAll(['meta.json', 'style.json', 'icons/icons.json']));
    expect(cache.files.keys.where((k) => k.startsWith('icons/${_icons['version']}/')).length, (_icons['icons'] as Map).length);
    online.dispose();

    final down = FakeWorker()..failing.add('*');
    final offline = _controller(down, cache: cache);
    await offline.start();
    expect(offline.error, isNull);
    expect(offline.ready, isTrue);
    expect(down.requests.where((p) => p.endsWith('.png')), isEmpty);   // symbols from the phone
    offline.dispose();

    final refused = _controller(FakeWorker(), key: 'nope');
    await refused.start();
    expect(refused.ready, isFalse);
    expect(refused.error, 'Not allowed (API key)');
    refused.dispose();
  });

  test('DirectoryCache keeps only its own paths', () async {
    final dir = await Directory.systemTemp.createTemp('vm_aton_test');
    try {
      final c = DirectoryCache(dir);
      await c.write('meta.json', utf8.encode('{}'));
      await c.write('icons/abcdef123456/lb-g@2x.png', png);
      await c.write('../evil.json', utf8.encode('x'));
      await c.write('icons/lb-g.png', png);                  // unversioned: not kept
      expect(await c.read('meta.json'), isNotNull);
      expect(await c.read('icons/abcdef123456/lb-g@2x.png'), png);
      expect(await c.read('../evil.json'), isNull);
      expect(await c.read('icons/lb-g.png'), isNull);
    } finally {
      await dir.delete(recursive: true);
    }
  });
}
