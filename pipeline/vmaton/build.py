"""The whole job: read the Light List and the notices, match them, classify, and write the site:

  aton.pmtiles     vector tiles (layer "aton", z6-14)
  icons/           the symbols at 1x/2x/3x + icons.json
  style.json       the overlay's source and layers (MapLibre style fragment)
  meta.json        when, what, how many (the app reads it first; publish.py uploads it last)
  uploads.json     what publish.py uploads, in order
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import classify as C
from . import icons as I
from . import lightlist as L
from . import notices as N
from . import style as S
from . import tiles as T
from .match import in_area, match, summarize, unlisted_aids

CONFIG = Path(__file__).resolve().parents[1] / "config" / "aton.json"


class BuildError(RuntimeError):
    pass


def load_config(**over) -> dict:
    cfg = json.loads(CONFIG.read_text())
    cfg.update({k: v for k, v in over.items() if v is not None})
    return cfg


NUM_RE = re.compile(r"\b(?:Buoy|Light|Daybeacon|Beacon|Marker|Mark)\s+([A-Z0-9]{1,5}(?:-[A-Z0-9]{1,3})?)\s*$")


def aid_number(name: str) -> str:
    """'Barnegat Inlet Lighted Buoy 1' -> '1', '... Lighted Whistle Buoy BI' -> 'BI', 'Shinnecock Light' -> ''."""
    m = NUM_RE.search(name or "")
    return m[1] if m else ""


def label_of(char: str, num: str) -> str:
    """The chart-style label: 'Fl G 4s\\n"3"', '"3"', 'Fl W 6s' or ''."""
    parts = []
    if char:
        parts.append(char)
    if num:
        parts.append(f'"{num}"')
    return "\n".join(parts)


def bbox_of(points) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)]


@dataclass
class Result:
    meta: dict
    style: dict
    features: list = field(default_factory=list)


def read_light_lists(source, districts, max_parts: int) -> tuple[dict, list, int]:
    """Probe lightList{DD}_{n}.csv, n = 1, 2, ... until one isn't there (the part counts aren't in
    fileIndexNew.json). Returns ({district: parts}, aids, rows without a position)."""
    parts, aids, skipped = {}, [], 0
    for d in districts:
        n = 0
        while True:
            if n >= max_parts:
                raise BuildError(f"district {d}: more than {max_parts} Light List parts; check the source")
            raw = source.get(f"lightListD{d:02d}_{n + 1}.csv")
            if raw is None:
                break
            n += 1
            got, sk = L.parse(raw)
            aids += got
            skipped += sk
        if n == 0:
            raise BuildError(f"no Light List for district {d} (lightListD{d:02d}_1.csv not found)")
        parts[d] = n
    return parts, aids, skipped


def read_notices(source, index: dict, products, tz: str) -> tuple[list, dict]:
    out, parts = [], {}
    for prod in products:
        count = int((index.get(prod) or {}).get("counter") or 0)
        parts[prod] = count
        for i in range(1, count + 1):
            raw = source.get(f"{prod}{i}.geojson")
            if raw is None:
                raise BuildError(f"{prod}{i}.geojson is in fileIndexNew.json but not there")
            out += N.parse(raw, N.product_of(prod), tz)
    return out, parts


def count_corrected(source, index: dict, products, districts) -> int:
    n = 0
    for prod in products:
        for i in range(1, int((index.get(prod) or {}).get("counter") or 0) + 1):
            raw = source.get(f"{prod}{i}.geojson")
            if raw is None:
                continue
            for f in json.loads(raw.decode("utf-8-sig")).get("features") or []:
                if (f.get("properties") or {}).get("ATU") in districts:
                    n += 1
    return n


def run(source, out: Path, cfg: dict, now: datetime, sample: bool = False) -> Result:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tz = ZoneInfo(cfg["timezone"])
    districts = [int(d) for d in cfg["districts"]]

    raw_index = source.get("fileIndexNew.json")
    if raw_index is None:
        raise BuildError("fileIndexNew.json not found")
    index = json.loads(raw_index.decode("utf-8-sig"))

    parts, aids, skipped = read_light_lists(source, districts, int(cfg["light_list_max_parts"]))
    per_district = Counter(a.district for a in aids)
    for d in districts:
        if per_district[d] < int(cfg.get("min_aids_per_district") or 0):
            raise BuildError(f"district {d}: only {per_district[d]} aids in the Light List "
                             f"(at least {cfg['min_aids_per_district']} expected)")
    L.assign_ids(aids)

    all_notices, notice_parts = read_notices(source, index, cfg["notice_products"], cfg["timezone"])
    box = bbox_of([(a.lon, a.lat) for a in aids]) if aids else None
    notices = [n for n in all_notices if in_area(n, districts, box)]
    m = match(aids, notices, float(cfg["name_match_m"]))
    unlisted = unlisted_aids(m.unmatched)
    corrected = count_corrected(source, index, cfg.get("corrected_products") or [], districts)

    feats = []
    for a, listed in [(a, True) for a in aids] + [(a, False) for a in unlisted]:
        sym, kind, code = C.classify(a.dtype, a.color, a.structure, a.char, a.range, a.name, float(cfg["major_range_nm"]))
        st = summarize(a.notices)
        num = aid_number(a.name)
        props = {
            "id": a.id, "llnr": a.llnr, "name": a.name, "sym": sym, "kind": kind, "color": code,
            "char": a.char, "range": a.range, "height": a.height, "structure": a.structure, "remark": a.remark,
            "private": a.private, "waterway": a.waterway, "district": a.district,
            "status": st.get("status", ""), "status_text": st.get("status_text", ""),
            "status_since": st.get("status_since", ""), "status_raw": st.get("status_raw", ""), "bnm": st.get("bnm", ""),
            "num": num, "label": label_of(a.char, num),
            "rank": T.rank(kind, sym, a.private, a.range, st.get("status", "")),
        }
        if not listed:
            props["listed"] = False
        feats.append({"lon": a.lon, "lat": a.lat, "props": props, "keep": bool(st),
                      "minzoom": T.minzoom(kind, sym, a.private, a.range, cfg["zoom"], float(cfg["sea_buoy_range_nm"]))})

    z = cfg["zoom"]
    tiles = T.build(feats, z["min"], z["max"], z["cell_px"])
    bounds = bbox_of([(f["lon"], f["lat"]) for f in feats])
    fields = {k: ("Number" if k in ("range", "height", "district", "rank") else "Boolean" if k in ("private", "listed")
                  else "String") for k in {k for f in feats for k in f["props"]}}
    tmeta = {"name": "vm-aton", "description": "Buoys & lights: US Coast Guard aids to navigation. Not for navigation.",
             "attribution": cfg["attribution"], "format": "pbf", "type": "overlay",
             "vector_layers": [{"id": T.LAYER, "minzoom": z["min"], "maxzoom": z["max"], "fields": dict(sorted(fields.items()))}]}
    pm = out / "aton.pmtiles"
    version = T.write_pmtiles(pm, tiles, tmeta, bounds, z["min"], z["max"])
    manifest = I.write_icons(out)

    # dates: the notices' from fileIndexNew.json, the Light List's from the files (Last-Modified / mtime)
    stamps = [int((index.get(p) or {}).get("timestamp") or 0) for p in cfg["notice_products"]]
    notices_at = datetime.fromtimestamp(max(stamps), timezone.utc) if any(stamps) else now
    ll_mod = [f.modified for f in getattr(source, "fetched", []) if f.name.startswith("lightList") and f.modified]
    ll_at = max(ll_mod) if ll_mod else now
    data_at = max(notices_at, ll_at)
    by_status = Counter(f["props"]["status"] for f in feats if f["props"]["status"])
    meta = {
        "version": 1, "layer": "aton", "sample": bool(sample), "title": "Buoys & lights",
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "run": now.strftime("%Y%m%dT%H%MZ"),
        "data_date": data_at.astimezone(tz).date().isoformat(),
        "light_list_date": ll_at.astimezone(tz).date().isoformat(),
        "notices_date": notices_at.astimezone(tz).date().isoformat(),
        "stale_after_hours": cfg["stale_after_hours"],
        "attribution": cfg["attribution"], "note": cfg["note"],
        "districts": {str(d): {"name": cfg["district_names"].get(str(d), f"District {d}"), "aids": per_district[d],
                               "light_list_parts": parts[d]} for d in districts},
        "counts": {
            "aids": len(feats), "listed": len(aids), "unlisted": len(unlisted),
            "skipped_no_position": skipped,
            "by_kind": dict(sorted(Counter(f["props"]["kind"] for f in feats).items())),
            "by_sym": dict(sorted(Counter(f["props"]["sym"] for f in feats).items())),
            "by_status": {s: by_status.get(s, 0) for s in ("missing", "fault", "temporary")},
            "notices": {"nationwide": len(all_notices), "in_area": len(notices), "matched_by_number": m.by_number,
                        "matched_by_name": m.by_name, "unmatched": len(m.unmatched), "matched_far": m.far,
                        "corrected_in_area": corrected, "parts": notice_parts},
        },
        "tiles": {"file": "aton.pmtiles", "layer": T.LAYER, "minzoom": z["min"], "maxzoom": z["max"],
                  "version": version, "bytes": pm.stat().st_size, "tiles": len(tiles), "bounds": bounds},
        "icons": {"file": "icons/icons.json", "version": manifest["version"], "count": len(manifest["icons"])},
        "style": "style.json",
        "source": source.describe() if not sample else "SAMPLE (made up)",
        "sources": [{"file": f.name, "bytes": f.bytes,
                     "modified": f.modified.strftime("%Y-%m-%dT%H:%M:%SZ") if f.modified else None}
                    for f in getattr(source, "fetched", [])],
    }
    style = S.build(meta, cfg)
    (out / "style.json").write_text(json.dumps(style, indent=1) + "\n")
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    files = sorted(f for v in manifest["icons"].values() for f in v["files"].values())
    uploads = {"run": meta["run"], "files": [*files, "icons/icons.json", "aton.pmtiles", "style.json", "meta.json"]}
    (out / "uploads.json").write_text(json.dumps(uploads, indent=1) + "\n")
    return Result(meta=meta, style=style, features=feats)
