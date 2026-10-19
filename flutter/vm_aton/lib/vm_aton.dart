/// Buoys & lights for the Vector Marine map's Overlays menu: every US Coast Guard aid to navigation from Maine
/// to Florida and Puerto Rico, drawn with our own chart-like symbols, with the outages and temporary changes from
/// the Local Notice to Mariners. An overlay on top of whatever map style is loaded; nothing here changes the chart.
library;

export 'src/api.dart' show AtonApi, AtonApiException, AtonCache, DirectoryCache;
export 'src/config.dart' show VmAton;
export 'src/controller.dart' show AtonController;
export 'src/maplibre.dart' show AtonMapLibre;
export 'src/models.dart' show AtonFeature, AtonIcons, AtonLayerDef, AtonMeta, AtonSourceDef, AtonStyle;
export 'src/widgets.dart' show AtonCard, AtonNote, showAtonCard;
export 'src/words.dart'
    show AtonCardText, cardFor, decodeCodes, fmtDate, fmtNum, joinWords, kindWords, lightWords, severityColors,
        severityWords, staleText, statusLine, worst;
