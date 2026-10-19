"""The Coast Guard Light List (lightList{DD}_{n}.csv): one row per aid to navigation, corrected weekly.

Read with the csv module: quoted fields hold commas and doubled quotes ("NW on pile worded "" Danger Shoal"".").
Columns used: ATU (district), LIGHT_LIST_NUMBER, NAME, AID_TYPE (FD federal / PA private), DESCRIPTION_TYPE,
COLOR, STATE, REMARK, STRUCTURE_REMARK, LIGHT_CHAR, LIGHT_FOCAL_PLANE (ft), LIGHT_NOM_RANGE (NM),
DECIMAL_LONGITUDE/LATITUDE (else ASSIGNED_LONGITUDE/LATITUDE as D-M-S text), AID_SUBTYPE (FX fixed / FL
floating), HWATERWAY_NAME.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

REQUIRED = ("ATU", "LIGHT_LIST_NUMBER", "NAME", "DESCRIPTION_TYPE", "DECIMAL_LONGITUDE", "DECIMAL_LATITUDE")


@dataclass
class Aid:
    district: int
    llnr: str
    name: str
    private: bool
    dtype: str                 # DESCRIPTION_TYPE: DBN, ULB, LT, LB, RF, RR, LTMA, VAIS, SSIG, DLT, RACN, BBL, ...
    color: str                 # COLOR as listed (cleaned: "N/A" -> "")
    structure: str
    char: str                  # LIGHT_CHAR, e.g. "Fl G 4s"
    height: float | None       # focal plane, ft
    range: float | None        # nominal range, NM
    lon: float
    lat: float
    subtype: str               # FX fixed / FL floating
    waterway: str
    remark: str
    state: str = ""
    id: str = ""
    notices: list = field(default_factory=list)


def clean(s: str | None) -> str:
    """Trim, and collapse the runs of spaces the export leaves where commas were."""
    return re.sub(r"\s{2,}", " ", (s or "").strip())


def norm_llnr(v) -> str:
    """Light List number as text: 900 -> "900", 5400.1 -> "5400.1", 36826.700000000004 -> "36826.7"."""
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    try:
        f = float(s)
    except ValueError:
        return s
    return f"{f:.3f}".rstrip("0").rstrip(".")


def number(s: str | None) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v.is_integer() else v


DMS = re.compile(r"^\s*(\d{1,3})-(\d{1,2})-(\d{1,2}(?:\.\d+)?)\s*([NSEW])\s*$")


def parse_dms(s: str | None) -> float | None:
    """'074-04-36.123W' -> -74.07670"""
    m = DMS.match(s or "")
    if not m:
        return None
    d, mi, se, h = int(m[1]), int(m[2]), float(m[3]), m[4]
    v = d + mi / 60 + se / 3600
    return -v if h in "SW" else v


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def read_rows(raw: bytes) -> list[dict]:
    text = decode(raw)
    rd = csv.DictReader(io.StringIO(text, newline=""))
    missing = [c for c in REQUIRED if c not in (rd.fieldnames or [])]
    if missing:
        raise ValueError(f"not a Light List file: missing columns {missing}")
    return list(rd)


def to_aid(row: dict) -> Aid | None:
    """One Light List row -> Aid; None without a position."""
    lon = number(row.get("DECIMAL_LONGITUDE"))
    lat = number(row.get("DECIMAL_LATITUDE"))
    if lon is None or lat is None:
        lon, lat = parse_dms(row.get("ASSIGNED_LONGITUDE")), parse_dms(row.get("ASSIGNED_LATITUDE"))
    if lon is None or lat is None or not (-180 <= lon <= 180 and -90 <= lat <= 90) or (lon == 0 and lat == 0):
        return None
    color = clean(row.get("COLOR"))
    if color.upper() in ("N/A", "NA", "NONE"):
        color = ""
    try:
        district = int(float(row.get("ATU") or 0))
    except ValueError:
        district = 0
    return Aid(
        district=district,
        llnr=norm_llnr(row.get("LIGHT_LIST_NUMBER")),
        name=clean(row.get("NAME")),
        private=clean(row.get("AID_TYPE")).upper() == "PA",
        dtype=clean(row.get("DESCRIPTION_TYPE")).upper(),
        color=color,
        structure=clean(row.get("STRUCTURE_REMARK")),
        char=clean(row.get("LIGHT_CHAR")),
        height=number(row.get("LIGHT_FOCAL_PLANE")),
        range=number(row.get("LIGHT_NOM_RANGE")),
        lon=round(float(lon), 6),
        lat=round(float(lat), 6),
        subtype=clean(row.get("AID_SUBTYPE")).upper(),
        waterway=clean(row.get("HWATERWAY_NAME")),
        remark=clean(row.get("REMARK")),
        state=clean(row.get("STATE")),
    )


def parse(raw: bytes) -> tuple[list[Aid], int]:
    """(aids, rows skipped for having no position)"""
    aids, skipped = [], 0
    for row in read_rows(raw):
        a = to_aid(row)
        if a is None:
            skipped += 1
        else:
            aids.append(a)
    return aids, skipped


def assign_ids(aids: list[Aid]) -> None:
    """id = "<district>-<llnr>"; the few numbers listed twice (11 on Oct 19, 2026) keep both rows: -2, -3..."""
    seen: dict[str, int] = {}
    for a in aids:
        base = f"{a.district}-{a.llnr}"
        n = seen.get(base, 0) + 1
        seen[base] = n
        a.id = base if n == 1 else f"{base}-{n}"
