// The tap card and the note line.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vm_aton/src/api.dart';
import 'package:vm_aton/src/controller.dart';
import 'package:vm_aton/src/models.dart';
import 'package:vm_aton/src/widgets.dart';

import 'fake_worker.dart';

Map<String, dynamic> _map(Object? v) => Map<String, dynamic>.from(v! as Map);
final _cards = [for (final c in _map(jsonDecode(File('test/fixtures/words.json').readAsStringSync()))['cards'] as List) _map(c)];

Widget _host(Widget child) => MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));

void main() {
  testWidgets('a missing aid: status with its date, the light spelled out, not for navigation', (t) async {
    final c = _cards.firstWhere((c) => _map(c['props'])['status'] == 'missing' && _map(c['props'])['char'] != '');
    final p = _map(c['props']);
    final want = _map(c['result']);
    var closed = false;
    await t.pumpWidget(_host(AtonCard(feature: AtonFeature(p), dataDate: '2026-10-19', onClose: () => closed = true)));
    expect(find.text(want['title'] as String), findsOneWidget);
    expect(find.text(want['subtitle'] as String), findsOneWidget);
    expect(find.text(want['status'] as String), findsOneWidget);
    expect((want['status'] as String).contains(' since '), isTrue);
    for (final r in want['rows'] as List) {
      expect(find.text((r as List)[1] as String), findsOneWidget);
    }
    expect(find.textContaining('Not for navigation'), findsOneWidget);
    await t.tap(find.byTooltip('Close'));
    expect(closed, isTrue);
  });

  testWidgets('an aid without a status: no status box', (t) async {
    final c = _cards.firstWhere((c) => _map(c['props'])['status'] == '');
    await t.pumpWidget(_host(AtonCard(feature: AtonFeature(_map(c['props'])), dataDate: '2026-10-19')));
    expect(find.textContaining(' since '), findsNothing);
    expect(find.text(_map(c['result'])['footer'] as String), findsOneWidget);
  });

  testWidgets('note line: data date, SAMPLE', (t) async {
    final w = FakeWorker();
    final c = AtonController(api: AtonApi(baseUrl: base, apiKey: 'k1', client: w.client), pixelRatio: 1,
        clock: () => DateTime.utc(2026, 10, 19, 12));
    await t.pumpWidget(_host(AtonNote(controller: c)));
    expect(find.byType(Text), findsNothing);                 // off: nothing
    await t.runAsync(c.start);
    await t.pump();
    expect(find.textContaining('SAMPLE DATA'), findsOneWidget);
    expect(find.textContaining('Coast Guard data of Oct 19, 2026 · Not for navigation'), findsOneWidget);
    c.dispose();
  });
}
