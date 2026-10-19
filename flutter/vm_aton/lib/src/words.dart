// words.dart - every word Buoys & lights shows: the Coast Guard's status codes in plain English, the light
// characteristic spelled out, kinds of aid, dates, the tap card. The same functions as pipeline/vmaton/words.py
// (the reference) and preview/aton.js; test/words_test.dart checks them against the parity fixture
// (test/fixtures/words.json, written by pipeline/tools/make_parity.py). Change all three together.

const rank = {'missing': 3, 'fault': 2, 'temporary': 1};

/// What the rings mean (the legend).
const severityWords = {
  'missing': 'Missing, off station or destroyed',
  'fault': 'Light out or damaged',
  'temporary': 'Temporary change',
};

/// The rings' colours, "#rrggbb" (the same as the icons').
const severityColors = {'missing': '#e21e28', 'fault': '#f59e0b', 'temporary': '#788492'};

const statusCodes = <String, (String, String)>{
  'MISSING': ('Missing', 'missing'),
  'OFF STATION': ('Off station', 'missing'),
  'OFF STA': ('Off station', 'missing'),
  'STRUCT DEST': ('Structure destroyed', 'missing'),
  'STRUCT MISSING': ('Structure missing', 'missing'),
  'SINKING': ('Sinking', 'missing'),
  'ADRIFT': ('Adrift', 'missing'),
  'HAZ NAV': ('Hazard to navigation', 'missing'),
  'LT EXT': ('Light out', 'fault'),
  'LT IMCH': ('Light not showing as listed', 'fault'),
  'REDUCED INT': ('Light at reduced intensity', 'fault'),
  'NIGHT LT BURNING DAY': ('Light burning in daytime', 'fault'),
  'MSLD SIG': ('Misleading signal', 'fault'),
  'STRUCT DMGD': ('Structure damaged', 'fault'),
  'BUOY DMGD': ('Buoy damaged', 'fault'),
  'LEANING': ('Leaning', 'fault'),
  'DAYMK MISSING': ('Daymark missing', 'fault'),
  'DAYMK DMGD': ('Daymark damaged', 'fault'),
  'DAYMK IMCH': ('Daymark not as listed', 'fault'),
  'DBD DEST': ('Dayboard destroyed', 'fault'),
  'DBD DMGD': ('Dayboard damaged', 'fault'),
  'TMK MISSING': ('Topmark missing', 'fault'),
  'VEGETATION': ('Hidden by vegetation', 'fault'),
  'SS INOP': ('Sound signal not working', 'fault'),
  'SS IMCH': ('Sound signal not as listed', 'fault'),
  'RAC INOP': ('Racon not working', 'fault'),
  'AIS INOP': ('AIS not working', 'fault'),
  'AIS IMCH': ('AIS not as listed', 'fault'),
  'RBN IMCH': ('Radiobeacon not as listed', 'fault'),
  'OTHER DISC AIDS IN AREA': ('Other aids nearby also reported', 'fault'),
  'STATUS UNREPORTED': ('Status not reported', 'fault'),
  'TRLB': ('Temporarily replaced by a lighted buoy', 'temporary'),
  'TRUB': ('Temporarily replaced by an unlighted buoy', 'temporary'),
  'TRLT': ('Temporarily replaced by a light', 'temporary'),
  'TRDBN': ('Temporarily replaced by a daybeacon', 'temporary'),
  'TRSAIS': ('Temporarily replaced by a synthetic AIS aid', 'temporary'),
  'DISCONTINUED': ('Discontinued', 'temporary'),
  'DISCONTINUED FOR DREDGING': ('Discontinued for dredging', 'temporary'),
  'RELOCATED': ('Relocated', 'temporary'),
  'RELOCATED FOR DREDGING': ('Relocated for dredging', 'temporary'),
  'ESTABLISHED': ('Temporarily established', 'temporary'),
  'OTHER': ('Temporary change', 'temporary'),
};
const _defaultSeverity = {'disc': 'fault', 'tmp': 'temporary'};

String _squash(Object? s) => (s ?? '').toString().trim().replaceAll(RegExp(r'\s+'), ' ');

/// 'LT IMCH/STRUCT DMGD' -> [('LT IMCH', 'Light not showing as listed', 'fault'), ...]. Unknown codes keep the
/// Coast Guard's text, with the product's default severity (disc: fault, tmp: temporary).
List<(String, String, String)> decodeCodes(String? raw, [String product = 'disc']) {
  final out = <(String, String, String)>[];
  for (final part in (raw ?? '').split('/')) {
    final code = _squash(part);
    if (code.isEmpty) continue;
    final hit = statusCodes[code.toUpperCase()];
    out.add(hit == null ? (code, code, _defaultSeverity[product] ?? 'fault') : (code, hit.$1, hit.$2));
  }
  return out;
}

bool _isUpper(String c) => c.toUpperCase() == c && c.toLowerCase() != c;
bool _isLower(String c) => c.toLowerCase() == c && c.toUpperCase() != c;

/// ['Structure destroyed', 'Temporarily replaced …'] -> 'Structure destroyed; temporarily replaced …'
String joinWords(List<String> words) {
  final out = <String>[];
  for (var w in words) {
    if (out.isNotEmpty && w.length > 1 && _isUpper(w[0]) && _isLower(w[1])) w = w[0].toLowerCase() + w.substring(1);
    out.add(w);
  }
  return out.join('; ');
}

String worst(Iterable<String> severities) {
  var best = '';
  for (final s in severities) {
    if ((rank[s] ?? 0) > (rank[best] ?? 0)) best = s;
  }
  return best;
}

const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// '2025-12-02' -> 'Dec 2, 2025' ('' for nothing).
String fmtDate(String? iso) {
  final m = RegExp(r'^(\d{4})-(\d{2})-(\d{2})').firstMatch(iso ?? '');
  if (m == null) return '';
  return '${_months[int.parse(m[2]!) - 1]} ${int.parse(m[3]!)}, ${m[1]}';
}

/// ('Missing', '2025-12-02') -> 'MISSING since Dec 2, 2025'
String statusLine(String? text, String? since) {
  if (text == null || text.isEmpty) return '';
  final d = fmtDate(since);
  return d.isNotEmpty ? '${text.toUpperCase()} since $d' : text.toUpperCase();
}

const _lightKinds = {
  'F': 'fixed', 'FL': 'flashing', 'LFL': 'long flashing', 'Q': 'quick flashing', 'VQ': 'very quick flashing',
  'IQ': 'interrupted quick flashing', 'ISO': 'isophase', 'OC': 'occulting', 'MO': 'Morse code', 'FFL': 'fixed and flashing',
};
const _colours = {'W': 'white', 'R': 'red', 'G': 'green', 'Y': 'yellow', 'BU': 'blue'};
final _lightRe = RegExp(r'^(AL\.?\s+)?(FFL|LFL|FL|VQ|IQ|Q|ISO|OC|MO|F)\s*(\([^()]{1,8}\))?\s*((?:(?:BU|W|R|G|Y)\s*)*)\s*'
    r'(?:(\d{1,3}(?:\.\d{1,2})?)\s*S(?:EC)?)?$');

String _andList(List<String> items) =>
    items.length <= 1 ? items.join() : '${items.sublist(0, items.length - 1).join(', ')} and ${items.last}';

/// 5 -> '5', 2.5 -> '2.5', 5.0 -> '5' ('' for nothing).
String fmtNum(Object? v) {
  if (v == null || v == '') return '';
  final f = v is num ? v.toDouble() : double.parse(v.toString());
  if (f == f.truncateToDouble()) return f.toInt().toString();
  return f.toStringAsFixed(2).replaceFirst(RegExp(r'0+$'), '').replaceFirst(RegExp(r'\.$'), '');
}

/// 'Fl G 4s' -> 'flashing green, every 4 s'; 'Fl (2+1)R 6s' -> 'composite group flashing (2+1) red, every 6 s';
/// null when it can't be read (the card then shows the characteristic only).
String? lightWords(String? char) {
  final s = _squash(char).toUpperCase();
  if (s.isEmpty) return null;
  final m = _lightRe.firstMatch(s);
  if (m == null) return null;
  final alt = m[1], kind = m[2]!, group = m[3], cols = m[4] ?? '', period = m[5];
  final colours = RegExp(r'BU|W|R|G|Y').allMatches(cols).map((x) => x[0]!).toList();
  if (colours.isEmpty) return null;
  var k = _lightKinds[kind]!;
  if (group != null) {
    final g = group.replaceAll(' ', '');
    if (kind == 'MO') {
      k = 'Morse code $g';
    } else if (g.contains('+')) {
      k = 'composite group $k $g';
    } else {
      k = 'group $k $g';
    }
  }
  if (alt != null) k = 'alternating $k';
  var words = '$k ${_andList([for (final c in colours) _colours[c]!])}';
  if (period != null) words += ', every ${fmtNum(period)} s';
  return words;
}

const kindWordsTable = {
  'major_light': 'Major light', 'light': 'Light', 'lighted_buoy': 'Lighted buoy', 'buoy': 'Buoy',
  'daybeacon': 'Daybeacon', 'range_light': 'Range light', 'range_daybeacon': 'Range daybeacon',
  'directional_light': 'Directional light', 'articulated_light': 'Articulated light',
  'racon': 'Racon (radar beacon)', 'virtual_ais': 'Virtual AIS aid', 'sound_signal': 'Sound signal',
  'other': 'Aid to navigation',
};

String kindWords(String? kind) => kindWordsTable[kind ?? ''] ?? kindWordsTable['other']!;

/// The tap card's text.
class AtonCardText {
  const AtonCardText({required this.title, required this.subtitle, required this.status, required this.statusNote,
      required this.rows, required this.unlisted, required this.footer});
  final String title, subtitle, status, statusNote, unlisted, footer;
  final List<(String, String)> rows;

  Map<String, Object> toJson() => {
        'title': title, 'subtitle': subtitle, 'status': status, 'status_note': statusNote,
        'rows': [for (final r in rows) [r.$1, r.$2]], 'unlisted': unlisted, 'footer': footer,
      };
}

bool _truthy(Object? v) => switch (v) {
      null => false,
      bool b => b,
      String s => s.isNotEmpty,
      num n => n != 0,
      _ => true,
    };

String _str(Object? v) => v == null ? '' : v.toString().trim();

/// The tap card for one aid, from its tile properties (pipeline/vmaton/words.py card()).
AtonCardText cardFor(Map<String, dynamic> p, [String? dataDate]) {
  final sub = [kindWords(p['kind']?.toString())];
  if (_truthy(p['llnr'])) sub.add('Light List ${p['llnr']}');
  sub.add(_truthy(p['private']) ? 'Private aid' : 'Federal aid');
  final status = statusLine(p['status_text']?.toString(), p['status_since']?.toString());
  var note = '';
  if (_truthy(p['status'])) {
    note = 'Local Notice to Mariners';
    if (_truthy(p['bnm'])) note += ', broadcast notice ${p['bnm']}';
    if (_truthy(p['status_raw'])) note += '. Coast Guard code: ${p['status_raw']}';
    note += '.';
  }
  final rows = <(String, String)>[];
  final char = _str(p['char']);
  if (char.isNotEmpty) {
    final w = lightWords(char);
    rows.add(('Light', w != null ? '$char ($w)' : char));
  }
  if (p['range'] != null && p['range'] != '') rows.add(('Range', '${fmtNum(p['range'])} NM'));
  if (p['height'] != null && p['height'] != '') rows.add(('Height', '${fmtNum(p['height'])} ft'));
  for (final (label, key) in const [('Structure', 'structure'), ('Remarks', 'remark'), ('Waterway', 'waterway')]) {
    if (_str(p[key]).isNotEmpty) rows.add((label, _str(p[key])));
  }
  if (_truthy(p['district'])) rows.add(('District', 'Coast Guard District ${p['district']}'));
  final listed = p.containsKey('listed') ? _truthy(p['listed']) : true;
  final d = fmtDate(dataDate);
  return AtonCardText(
    title: _truthy(p['name']) ? p['name'].toString() : 'Aid to navigation',
    subtitle: sub.join(' · '),
    status: status,
    statusNote: note,
    rows: rows,
    unlisted: listed ? '' : 'Not in the current Light List: shown where the notice puts it.',
    footer: '${d.isNotEmpty ? 'Coast Guard data of $d. ' : ''}Not for navigation.',
  );
}

/// "Coast Guard data not updated for 3 days" once meta.json is older than [staleAfterHours], else ''.
String staleText(String? generatedAt, double staleAfterHours, int nowMs) {
  if (generatedAt == null || generatedAt.isEmpty) return '';
  final t = DateTime.parse(generatedAt).millisecondsSinceEpoch;
  final hours = (nowMs - t) / 3600000;
  if (hours <= staleAfterHours) return '';
  final days = (hours / 24).floor();
  return 'Coast Guard data not updated for $days day${days == 1 ? '' : 's'}';
}
