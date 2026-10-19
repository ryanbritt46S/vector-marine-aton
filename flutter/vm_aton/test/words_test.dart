// words.dart against the parity fixture written from the Python reference (pipeline/tools/make_parity.py from
// pipeline/vmaton/words.py). preview/test/aton.test.mjs checks the same file: Python, JS and Dart say the same.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vm_aton/src/words.dart';

Map<String, dynamic> _map(Object? v) => Map<String, dynamic>.from(v! as Map);
final _fx = _map(jsonDecode(File('test/fixtures/words.json').readAsStringSync()));
List<Map<String, dynamic>> _cases(String k) => [for (final c in _fx[k] as List) _map(c)];

void main() {
  test('status codes', () {
    for (final c in _cases('codes')) {
      final got = [for (final r in decodeCodes(c['raw'] as String, c['product'] as String)) [r.$1, r.$2, r.$3]];
      expect(got, c['result'], reason: '${c['raw']} (${c['product']})');
    }
    for (final c in _cases('join')) {
      expect(joinWords(List<String>.from(c['words'] as List)), c['result']);
    }
    expect(severityWords, _map(_fx['severity_words']));
    expect(worst(['temporary', 'missing', 'fault']), 'missing');
    expect(worst(const []), '');
  });

  test('light characteristics, dates, kinds, numbers, staleness', () {
    for (final c in _cases('lights')) {
      expect(lightWords(c['char'] as String), c['result'], reason: c['char'] as String);
    }
    for (final c in _cases('dates')) {
      expect(fmtDate(c['date'] as String), c['result']);
    }
    for (final c in _cases('status_lines')) {
      expect(statusLine(c['text'] as String, c['since'] as String), c['result']);
    }
    for (final c in _cases('kinds')) {
      expect(kindWords(c['kind'] as String), c['result']);
    }
    for (final c in _cases('nums')) {
      expect(fmtNum(c['value']), c['result'], reason: '${c['value']}');
    }
    for (final c in _cases('stale')) {
      final m = _map(c['meta']);
      expect(staleText(m['generated_at'] as String, (m['stale_after_hours'] as num).toDouble(), (c['now_ms'] as num).toInt()),
          c['result']);
    }
  });

  test('tap cards', () {
    final cards = _cases('cards');
    expect(cards.length, greaterThan(100));
    for (final c in cards) {
      final p = _map(c['props']);
      expect(cardFor(p, c['data_date'] as String).toJson(), c['result'], reason: '${p['id']}');
      // as they come out of a tile: no empty values
      final fromTile = Map<String, dynamic>.fromEntries(p.entries.where((e) => e.value != null && e.value != ''));
      expect(cardFor(fromTile, c['data_date'] as String).toJson(), c['result'], reason: '${p['id']} (tile)');
    }
  });

  test('the words people see (same cases as pipeline/tests/test_words.py)', () {
    expect(statusLine('Missing', '2025-12-02'), 'MISSING since Dec 2, 2025');
    expect(lightWords('Fl G 4s'), 'flashing green, every 4 s');
    expect(lightWords('Mo (A) W'), 'Morse code (A) white');
    expect(decodeCodes('STRUCT DEST/TRUB').map((c) => c.$2).toList(),
        ['Structure destroyed', 'Temporarily replaced by an unlighted buoy']);
  });
}
