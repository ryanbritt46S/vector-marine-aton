"""Put each discrepancy / temporary change on its aid: by district + Light List number, else by the same name
within name_match_m (300 m). Items that match nothing are still shown, as an aid of their own at the
notice's position (listed = false)."""
from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field

from .lightlist import Aid
from .notices import Notice
from .words import RANK, join_words, worst


def dist_m(lon1, lat1, lon2, lat2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class MatchResult:
    by_number: int = 0
    by_name: int = 0
    unmatched: list = field(default_factory=list)      # notices
    far: int = 0                                        # matched by number but over name_match_m away


def in_area(n: Notice, districts, bbox) -> bool:
    """Districts 1, 5, 7 by the notice's own district (ATU). A notice without one counts when it's inside the
    box (a box alone would take in Lake Ontario and the Ohio River, which belong to other districts)."""
    if n.district is not None:
        return n.district in districts
    if n.lon is None or n.lat is None or not bbox:
        return False
    w, s, e, nn = bbox
    return w <= n.lon <= e and s <= n.lat <= nn


def match(aids: list[Aid], notices: list[Notice], name_m: float = 300) -> MatchResult:
    by_key: dict = {}
    by_name: dict = {}
    for a in aids:
        by_key.setdefault((a.district, a.llnr), []).append(a)
        by_name.setdefault((a.district, a.name.lower()), []).append(a)
    res = MatchResult()

    def near(cands, n):
        if n.lon is None or n.lat is None or len(cands) == 1:
            return cands[0]
        return min(cands, key=lambda a: dist_m(a.lon, a.lat, n.lon, n.lat))

    for n in notices:
        hit = None
        if n.llnr and (n.district, n.llnr) in by_key:
            hit = near(by_key[(n.district, n.llnr)], n)
            res.by_number += 1
            if n.lon is not None and dist_m(hit.lon, hit.lat, n.lon, n.lat) > name_m:
                res.far += 1
        elif n.lon is not None:
            cands = [a for a in by_name.get((n.district, n.name.lower()), [])
                     if dist_m(a.lon, a.lat, n.lon, n.lat) <= name_m]
            if cands:
                hit = near(cands, n)
                res.by_name += 1
        if hit is None:
            res.unmatched.append(n)
        else:
            hit.notices.append(n)
    return res


def unlisted_aids(notices: list[Notice]) -> list[Aid]:
    """Aids for the notices that matched nothing: one per name and place (an aid often has a discrepancy and a
    temporary change), at the notice's position. Notices without a position are left out."""
    groups: dict = {}
    for n in notices:
        if n.lon is None or n.lat is None:
            continue
        k = (n.district, n.name.lower(), round(n.lon, 4), round(n.lat, 4))
        groups.setdefault(k, []).append(n)
    out = []
    for (district, _, _, _), ns in groups.items():
        n = ns[0]
        a = Aid(district=district or 0, llnr=n.llnr, name=n.name or "Aid to navigation", private=n.private,
                dtype=n.dtype, color=n.color, structure="", char="", height=None, range=None, lon=n.lon, lat=n.lat,
                subtype=n.subtype, waterway=n.waterway, remark="")
        a.id = f"{district or 0}-n{n.uid or zlib.crc32(f'{n.name}|{n.lon}|{n.lat}'.encode())}"
        a.notices = list(ns)
        out.append(a)
    return out


def summarize(notices: list[Notice]) -> dict:
    """The status properties of an aid from its notices: status (missing / fault / temporary), status_text
    (plain words), status_since (date of the first report of the worst problem), status_raw (the Coast Guard's
    codes), bnm (broadcast notice numbers)."""
    if not notices:
        return {}
    sev = worst(s for n in notices for _, _, s in n.codes)
    ordered = sorted(notices, key=lambda n: (-RANK.get(worst(s for _, _, s in n.codes), 0), n.since or "9999"))
    codes = [c for n in ordered for c in n.codes]
    words, raws, bnms = [], [], []
    for _, w, _ in sorted(codes, key=lambda c: -RANK.get(c[2], 0)):      # stable: worst first, then as reported
        if w not in words:
            words.append(w)
    for n in ordered:
        if n.raw not in raws:
            raws.append(n.raw)
        if n.bnm and n.bnm not in bnms:
            bnms.append(n.bnm)
    since = min((n.since for n in notices if n.since and any(s == sev for _, _, s in n.codes)), default="")
    return {"status": sev, "status_text": join_words(words), "status_since": since,
            "status_raw": "; ".join(raws), "bnm": ", ".join(bnms)}
