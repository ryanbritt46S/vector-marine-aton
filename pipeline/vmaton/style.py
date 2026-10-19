"""style.json: the overlay as a MapLibre style fragment (one vector source, three symbol layers), the reference
for how Buoys & lights looks. The preview adds these layers as they are; the Flutter package adds the same
layers through maplibre_gl, under the map style's "vm-overlays" anchor.

"{base}" in the source URL is filled in by the Worker with its own address.
"""
from __future__ import annotations

PREFIX = "vm-aton-"
SOURCE = "vm-aton"
TEXT_SOURCE = "vm-aton-text"     # the same tiles again for the labels: if the map's fonts fail to load (offline,
                                 # no glyphs cached), MapLibre drops that source's symbols with them; the
                                 # symbols and rings must never go with the labels

ICON_SIZE = ["interpolate", ["linear"], ["zoom"], 6, 0.5, 9, 0.6, 11, 0.72, 13, 0.9, 14, 1.05, 16, 1.3]


def build(meta: dict, cfg: dict) -> dict:
    z = cfg["zoom"]
    common = {"source": SOURCE, "source-layer": "aton"}
    return {
        "version": 1,
        "id": "vm-aton",
        "name": "Buoys & lights",
        "anchor": "vm-overlays",
        "tiles_version": meta["tiles"]["version"],
        "icons_version": meta["icons"]["version"],
        "image_prefix": PREFIX,
        "attribution": cfg["attribution"],
        "sources": {
            SOURCE: {"type": "vector", "url": "{base}/aton.json", "minzoom": z["min"], "maxzoom": z["max"],
                     "attribution": cfg["attribution"]},
            TEXT_SOURCE: {"type": "vector", "url": "{base}/aton.json", "minzoom": z["min"], "maxzoom": z["max"]},
        },
        "layers": [
            {   # the status rings, under the symbols: red missing, amber fault, grey (dashed) temporary
                "id": f"{PREFIX}status", "type": "symbol", **common, "minzoom": z["min"],
                "filter": ["has", "status"],
                "layout": {
                    "icon-image": ["concat", f"{PREFIX}badge-", ["get", "status"]],
                    "icon-size": ICON_SIZE,
                    "icon-allow-overlap": True, "icon-ignore-placement": True, "icon-anchor": "center",
                    "symbol-sort-key": ["get", "rank"],
                },
                "paint": {},
            },
            {   # every aid: our own chart-like symbol (icons/icons.json); a missing aid is drawn faded
                "id": f"{PREFIX}symbols", "type": "symbol", **common, "minzoom": z["min"],
                "layout": {
                    "icon-image": ["concat", PREFIX, ["get", "sym"]],
                    "icon-size": ICON_SIZE,
                    "icon-allow-overlap": True, "icon-ignore-placement": True, "icon-anchor": "center",
                    "symbol-sort-key": ["get", "rank"],
                },
                "paint": {
                    "icon-opacity": ["case", ["==", ["get", "status"], "missing"], 0.5, 1],
                },
            },
            {   # the light characteristic and number, like the chart's: Fl G 4s "3"
                "id": f"{PREFIX}labels", "type": "symbol", "source": TEXT_SOURCE, "source-layer": "aton",
                "minzoom": cfg.get("label_minzoom", 14),
                "filter": ["has", "label"],
                "layout": {
                    "text-field": ["get", "label"],
                    "text-font": [cfg["font"]],
                    "text-size": 11,
                    "text-anchor": "left",
                    "text-offset": [1.1, 0],
                    "text-justify": "left",
                    "text-max-width": 12,
                    "text-padding": 1,
                    "text-allow-overlap": False,
                    "symbol-sort-key": ["-", 0, ["get", "rank"]],
                },
                "paint": {
                    "text-color": ["case", ["has", "status"], "#9b1c1c", "#1b2733"],
                    "text-halo-color": "rgba(255,255,255,0.92)",
                    "text-halo-width": 1.3,
                },
            },
        ],
    }
