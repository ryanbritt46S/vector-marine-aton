"""Current discrepancies and temporary changes from the Local Notice to Mariners (NAVCEN GeoJSON, nationwide).

discFedAid_{n} / discPriAid_{n}: DISCREP_STATUS ("MISSING", "LT EXT", "STRUCT DEST/TRUB", ...).
tmpChange_{n}: TC_STATUS ("DISCONTINUED", "RELOCATED FOR DREDGING", ...).
Both: ATU, LLNR (number, sometimes 36826.700000000004 or null), NAME, CREATE_DATE (ms since 1970, UTC),
WATERWAY_NAME, AID_TYPE, AID_SUBTYPE, COLOR, DESCRIPTION_TYPE, DECIMAL_LONGITUDE/LATITUDE, BNM_NUM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .lightlist import clean, norm_llnr
from .words import decode_codes


@dataclass
class Notice:
    product: str               # "disc" or "tmp"
    district: int | None
    llnr: str
    name: str
    raw: str                   # the Coast Guard's status text
    codes: list                # [(code, words, severity)]
    since: str                 # YYYY-MM-DD (New York date of CREATE_DATE)
    lon: float | None
    lat: float | None
    bnm: str
    waterway: str
    private: bool
    dtype: str
    color: str
    subtype: str
    uid: str


def product_of(name: str) -> str:
    return "tmp" if name.startswith("tmpChange") else "disc"


def date_of(ms, tz: str = "America/New_York") -> str:
    if ms in (None, ""):
        return ""
    try:
        t = datetime.fromtimestamp(float(ms) / 1000, timezone.utc).astimezone(ZoneInfo(tz))
    except (OverflowError, OSError, ValueError):
        return ""
    return t.date().isoformat()


def parse(raw: bytes, product: str, tz: str = "America/New_York") -> list[Notice]:
    d = json.loads(raw.decode("utf-8-sig"))
    out = []
    for f in d.get("features") or []:
        p = f.get("properties") or {}
        status = p.get("TC_STATUS") if product == "tmp" else p.get("DISCREP_STATUS")
        codes = decode_codes(status, product)
        if not codes:
            continue
        lon, lat = p.get("DECIMAL_LONGITUDE"), p.get("DECIMAL_LATITUDE")
        g = f.get("geometry") or {}
        if (lon is None or lat is None) and g.get("type") == "Point":
            lon, lat = g["coordinates"][:2]
        try:
            district = int(p["ATU"]) if p.get("ATU") is not None else None
        except (TypeError, ValueError):
            district = None
        color = clean(p.get("COLOR"))
        out.append(Notice(
            product=product, district=district, llnr=norm_llnr(p.get("LLNR")), name=clean(p.get("NAME")),
            raw="/".join(c for c, _, _ in codes), codes=codes,
            since=date_of(p.get("CREATE_DATE"), tz),
            lon=None if lon is None else round(float(lon), 6), lat=None if lat is None else round(float(lat), 6),
            bnm=clean(p.get("BNM_NUM")), waterway=clean(p.get("WATERWAY_NAME")),
            private=clean(p.get("AID_TYPE")).upper() == "PA", dtype=clean(p.get("DESCRIPTION_TYPE")).upper(),
            color="" if color.upper() in ("N/A", "NONE") else color, subtype=clean(p.get("AID_SUBTYPE")).upper(),
            uid=str(p.get("LNM_UID") or p.get("ESRI_OID") or ""),
        ))
    return out


def count_features(raw: bytes) -> int:
    try:
        return len(json.loads(raw.decode("utf-8-sig")).get("features") or [])
    except (ValueError, AttributeError):
        return 0
