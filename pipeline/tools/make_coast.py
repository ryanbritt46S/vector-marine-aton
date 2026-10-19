#!/usr/bin/env python3
"""Optional: a rough coastline for the PREVIEW only (never the app, never published), so screenshots show where
the land is. Cuts GSHHG full-resolution shorelines (pip package basemap-data-hires, ~90 MB, LGPL) to a few boxes
and writes build/coast.geojson, which preview/serve.mjs serves as /coast.geojson when it's there.

  pip install basemap-data-hires
  python3 pipeline/tools/make_coast.py                         the screenshot places (docs/img)
  python3 pipeline/tools/make_coast.py --box=-74.4,39.3,-73.9,40.6 --out build/coast.geojson

GSHHG is about 100-200 m off in places: good enough to see the inlet, not to steer by.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# New Jersey and New York harbor, and Miami: the docs/img places with room around them
PLACES = [(-75.6, 38.6, -73.3, 41.2), (-80.7, 25.2, -79.8, 26.6)]


def gshhs_dir() -> Path:
    import importlib.util
    spec = importlib.util.find_spec("mpl_toolkits.basemap_data")
    if spec is None or not spec.submodule_search_locations:
        raise SystemExit("pip install basemap-data-hires (the GSHHG shorelines)")
    return Path(list(spec.submodule_search_locations)[0])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--box", action="append", help="W,S,E,N (repeat); default: the screenshot places")
    ap.add_argument("--out", default=str(ROOT / "build" / "coast.geojson"))
    a = ap.parse_args(argv)
    boxes = [tuple(float(v) for v in b.split(",")) for b in a.box] if a.box else PLACES
    d = gshhs_dir()
    data = (d / "gshhs_f.dat").read_bytes()
    feats = []
    from shapely.geometry import Polygon, box, mapping
    clips = [box(*b) for b in boxes]
    with open(d / "gshhsmeta_f.dat") as meta:
        for line in meta:
            parts = line.split()
            level, npts, south, north, off, nbytes = int(parts[0]), int(parts[2]), float(parts[3]), float(parts[4]), int(parts[5]), int(parts[6])
            if level not in (1, 2) or not any(south <= b[3] and north >= b[1] for b in boxes):
                continue
            pts = struct.unpack(f"<{npts * 2}f", data[off:off + nbytes])
            ring = list(zip(pts[0::2], pts[1::2]))
            xs = [p[0] for p in ring]
            if not any(min(xs) <= b[2] and max(xs) >= b[0] for b in boxes):
                continue
            poly = Polygon(ring).buffer(0)
            for c in clips:
                g = poly.intersection(c)
                if not g.is_empty:
                    feats.append({"type": "Feature", "properties": {"level": level}, "geometry": mapping(g.simplify(0.00005))})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    print(f"{out}: {len(feats)} pieces of land / lakes, {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
