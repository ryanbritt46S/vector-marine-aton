#!/usr/bin/env python3
"""Cut the small REAL test fixture (pipeline/tests/fixtures/real/) out of a full download of the NAVCEN files:
New Jersey's inlets from Little Egg to Manasquan (district 5), the New York harbor entrance (district 1) and
Miami's Government Cut (district 7), with their notices, plus two notices from other districts (left out by the job).

  python3 pipeline/tools/make_fixture.py /path/to/aton_raw

Not run by check.sh: the fixture is a frozen copy of the Coast Guard's files of Oct 19, 2026, so the tests check
real rows (quoted commas, doubled quotes, floats in LLNR, duplicates). Keep it under 300 KB.
"""
from __future__ import annotations

import csv
import glob
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "pipeline" / "tests" / "fixtures" / "real"
BOXES = {1: [(-74.06, 40.42, -73.82, 40.52)], 5: [(-74.36, 39.44, -73.98, 40.12)], 7: [(-80.16, 25.745, -80.085, 25.79)]}


def inside(d, lon, lat):
    return any(w <= lon <= e and s <= lat <= n for w, s, e, n in BOXES.get(d, []))


def main(raw: str) -> None:
    raw_dir = Path(raw)
    OUT.mkdir(parents=True, exist_ok=True)
    for d in BOXES:
        rows, fields = [], None
        for f in sorted(glob.glob(str(raw_dir / f"lightListD{d:02d}_*.csv"))):
            with open(f, newline="", encoding="utf-8") as fh:
                rd = csv.DictReader(fh)
                fields = rd.fieldnames
                rows += [r for r in rd if inside(d, float(r["DECIMAL_LONGITUDE"]), float(r["DECIMAL_LATITUDE"]))]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        (OUT / f"lightListD{d:02d}_1.csv").write_text(buf.getvalue())
        print(f"district {d}: {len(rows)} aids")
    index = json.loads((raw_dir / "fileIndexNew.json").read_text())
    keep = {}
    for prod in ("discFedAid_", "discPriAid_", "tmpChange_", "discFedAidCor_"):
        feats, others = [], []
        for i in range(1, index[prod]["counter"] + 1):
            for f in json.loads((raw_dir / f"{prod}{i}.geojson").read_text())["features"]:
                p = f["properties"]
                if inside(p.get("ATU"), p["DECIMAL_LONGITUDE"], p["DECIMAL_LATITUDE"]):
                    feats.append(f)
                elif p.get("ATU") in (8, 9) and len(others) < 1:
                    others.append(f)
        feats += others
        (OUT / f"{prod}1.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
        keep[prod] = {"counter": 1, "timestamp": index[prod]["timestamp"]}
        print(f"{prod}: {len(feats)} items")
    for prod in ("discPriAidCor_", "tmpChangeCor_"):
        keep[prod] = {"counter": 0, "timestamp": index[prod]["timestamp"]}
    (OUT / "fileIndexNew.json").write_text(json.dumps(keep))
    total = sum(f.stat().st_size for f in OUT.iterdir())
    print(f"{OUT.relative_to(ROOT)}: {total / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1])
