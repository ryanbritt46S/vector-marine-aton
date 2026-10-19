"""Every word the overlay shows: the Coast Guard's discrepancy and temporary-change codes in plain English, the
light characteristic spelled out, the kinds of aid, dates, and the card's lines.

This is the reference. preview/aton.js and flutter/vm_aton/lib/src/words.dart do exactly the same; the parity
fixture (pipeline/tools/make_parity.py -> flutter/vm_aton/test/fixtures/words.json) is checked by both sides'
tests. Change all three together, then bash check.sh.
"""
from __future__ import annotations

import re

# Severity of a status, highest first. "missing": the aid isn't there or isn't where it's listed (red ring);
# "fault": it's there but not working or not as listed (amber ring); "temporary": a temporary change (grey ring).
SEVERITIES = ("missing", "fault", "temporary")
RANK = {"missing": 3, "fault": 2, "temporary": 1}

SEVERITY_WORDS = {
    "missing": "Missing, off station or destroyed",
    "fault": "Light out or damaged",
    "temporary": "Temporary change",
}

# Coast Guard codes (DISCREP_STATUS, TC_STATUS; several joined with "/") -> (plain words, severity).
# Codes not in this table are shown as the Coast Guard wrote them, with the product's default severity.
STATUS_CODES = {
    "MISSING": ("Missing", "missing"),
    "OFF STATION": ("Off station", "missing"),
    "OFF STA": ("Off station", "missing"),
    "STRUCT DEST": ("Structure destroyed", "missing"),
    "STRUCT MISSING": ("Structure missing", "missing"),
    "SINKING": ("Sinking", "missing"),
    "ADRIFT": ("Adrift", "missing"),
    "HAZ NAV": ("Hazard to navigation", "missing"),
    "LT EXT": ("Light out", "fault"),
    "LT IMCH": ("Light not showing as listed", "fault"),
    "REDUCED INT": ("Light at reduced intensity", "fault"),
    "NIGHT LT BURNING DAY": ("Light burning in daytime", "fault"),
    "MSLD SIG": ("Misleading signal", "fault"),
    "STRUCT DMGD": ("Structure damaged", "fault"),
    "BUOY DMGD": ("Buoy damaged", "fault"),
    "LEANING": ("Leaning", "fault"),
    "DAYMK MISSING": ("Daymark missing", "fault"),
    "DAYMK DMGD": ("Daymark damaged", "fault"),
    "DAYMK IMCH": ("Daymark not as listed", "fault"),
    "DBD DEST": ("Dayboard destroyed", "fault"),
    "DBD DMGD": ("Dayboard damaged", "fault"),
    "TMK MISSING": ("Topmark missing", "fault"),
    "VEGETATION": ("Hidden by vegetation", "fault"),
    "SS INOP": ("Sound signal not working", "fault"),
    "SS IMCH": ("Sound signal not as listed", "fault"),
    "RAC INOP": ("Racon not working", "fault"),
    "AIS INOP": ("AIS not working", "fault"),
    "AIS IMCH": ("AIS not as listed", "fault"),
    "RBN IMCH": ("Radiobeacon not as listed", "fault"),
    "OTHER DISC AIDS IN AREA": ("Other aids nearby also reported", "fault"),
    "STATUS UNREPORTED": ("Status not reported", "fault"),
    "TRLB": ("Temporarily replaced by a lighted buoy", "temporary"),
    "TRUB": ("Temporarily replaced by an unlighted buoy", "temporary"),
    "TRLT": ("Temporarily replaced by a light", "temporary"),
    "TRDBN": ("Temporarily replaced by a daybeacon", "temporary"),
    "TRSAIS": ("Temporarily replaced by a synthetic AIS aid", "temporary"),
    "DISCONTINUED": ("Discontinued", "temporary"),
    "DISCONTINUED FOR DREDGING": ("Discontinued for dredging", "temporary"),
    "RELOCATED": ("Relocated", "temporary"),
    "RELOCATED FOR DREDGING": ("Relocated for dredging", "temporary"),
    "ESTABLISHED": ("Temporarily established", "temporary"),
    "OTHER": ("Temporary change", "temporary"),
}
DEFAULT_SEVERITY = {"disc": "fault", "tmp": "temporary"}


def code_key(code: str) -> str:
    return re.sub(r"\s+", " ", code.strip()).upper()


def decode_codes(raw: str | None, product: str = "disc") -> list[tuple[str, str, str]]:
    """'LT IMCH/STRUCT DMGD' -> [('LT IMCH', 'Light not showing as listed', 'fault'), ('STRUCT DMGD', ...)].
    Unknown codes keep the Coast Guard's text, with the product's default severity (disc: fault, tmp: temporary)."""
    out = []
    for part in (raw or "").split("/"):
        code = re.sub(r"\s+", " ", part.strip())
        if not code:
            continue
        words, sev = STATUS_CODES.get(code_key(code), (code, DEFAULT_SEVERITY.get(product, "fault")))
        out.append((code, words, sev))
    return out


def join_words(words: list[str]) -> str:
    """['Structure destroyed', 'Temporarily replaced by an unlighted buoy'] ->
    'Structure destroyed; temporarily replaced by an unlighted buoy' (acronyms keep their capitals)."""
    out = []
    for w in words:
        if out and len(w) > 1 and w[0].isupper() and w[1].islower():
            w = w[0].lower() + w[1:]
        out.append(w)
    return "; ".join(out)


def worst(severities) -> str:
    best = ""
    for s in severities:
        if RANK.get(s, 0) > RANK.get(best, 0):
            best = s
    return best


# ------------------------------------------------------------------------------------------------ dates

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def fmt_date(iso: str | None) -> str:
    """'2025-12-02' -> 'Dec 2, 2025' ('' for nothing)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return ""
    return f"{MONTHS[int(m[2]) - 1]} {int(m[3])}, {m[1]}"


def status_line(text: str | None, since: str | None) -> str:
    """('Missing', '2025-12-02') -> 'MISSING since Dec 2, 2025'"""
    if not text:
        return ""
    d = fmt_date(since)
    return f"{text.upper()} since {d}" if d else text.upper()


# ------------------------------------------------------------------------------------------------ lights

LIGHT_KINDS = {
    "F": "fixed", "FL": "flashing", "LFL": "long flashing", "Q": "quick flashing", "VQ": "very quick flashing",
    "IQ": "interrupted quick flashing", "ISO": "isophase", "OC": "occulting", "MO": "Morse code",
    "FFL": "fixed and flashing",
}
COLOURS = {"W": "white", "R": "red", "G": "green", "Y": "yellow", "BU": "blue"}
LIGHT_RE = re.compile(
    r"^(AL\.?\s+)?(FFL|LFL|FL|VQ|IQ|Q|ISO|OC|MO|F)\s*(\([^()]{1,8}\))?\s*((?:(?:BU|W|R|G|Y)\s*)*)\s*"
    r"(?:(\d{1,3}(?:\.\d{1,2})?)\s*S(?:EC)?)?$")


def and_list(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def num(v) -> str:
    """5 -> '5', 2.5 -> '2.5', 5.0 -> '5'"""
    if v is None or v == "":
        return ""
    f = float(v)
    if f == int(f):
        return str(int(f))
    return f"{f:.2f}".rstrip("0").rstrip(".")


def light_words(char: str | None) -> str | None:
    """'Fl G 4s' -> 'flashing green, every 4 s'; 'Fl (2+1)R 6s' -> 'composite group flashing (2+1) red, every 6 s';
    'Mo (A) W' -> 'Morse code (A) white'. None when it can't be read (the card then shows the characteristic only)."""
    s = re.sub(r"\s+", " ", (char or "").strip()).upper()
    if not s:
        return None
    m = LIGHT_RE.match(s)
    if not m:
        return None
    alt, kind, group, cols, period = m[1], m[2], m[3], m[4], m[5]
    colours = re.findall(r"BU|W|R|G|Y", cols or "")
    if not colours:
        return None
    k = LIGHT_KINDS[kind]
    if group:
        g = group.replace(" ", "")
        if kind == "MO":
            k = f"Morse code {g}"
        elif "+" in g:
            k = f"composite group {k} {g}"
        else:
            k = f"group {k} {g}"
    if alt:
        k = f"alternating {k}"
    words = f"{k} {and_list([COLOURS[c] for c in colours])}"
    if period:
        words += f", every {num(period)} s"
    return words


# ------------------------------------------------------------------------------------------------ kinds

KIND_WORDS = {
    "major_light": "Major light",
    "light": "Light",
    "lighted_buoy": "Lighted buoy",
    "buoy": "Buoy",
    "daybeacon": "Daybeacon",
    "range_light": "Range light",
    "range_daybeacon": "Range daybeacon",
    "directional_light": "Directional light",
    "articulated_light": "Articulated light",
    "racon": "Racon (radar beacon)",
    "virtual_ais": "Virtual AIS aid",
    "sound_signal": "Sound signal",
    "other": "Aid to navigation",
}


def kind_words(kind: str | None) -> str:
    return KIND_WORDS.get(kind or "", KIND_WORDS["other"])


# ------------------------------------------------------------------------------------------------ the card

def card(p: dict, data_date: str | None = None) -> dict:
    """The tap card for one aid, from its tile properties. Returns
    {title, subtitle, status, status_note, rows: [[label, value]], unlisted, footer}; empty parts are '' / []."""
    sub = [kind_words(p.get("kind"))]
    if p.get("llnr"):
        sub.append(f"Light List {p['llnr']}")
    sub.append("Private aid" if p.get("private") else "Federal aid")
    status = status_line(p.get("status_text"), p.get("status_since"))
    note = ""
    if p.get("status"):
        note = "Local Notice to Mariners"
        if p.get("bnm"):
            note += f", broadcast notice {p['bnm']}"
        if p.get("status_raw"):
            note += f". Coast Guard code: {p['status_raw']}"
        note += "."
    rows = []
    char = (p.get("char") or "").strip()
    if char:
        w = light_words(char)
        rows.append(["Light", f"{char} ({w})" if w else char])
    if p.get("range") not in (None, ""):
        rows.append(["Range", f"{num(p['range'])} NM"])
    if p.get("height") not in (None, ""):
        rows.append(["Height", f"{num(p['height'])} ft"])
    for label, key in (("Structure", "structure"), ("Remarks", "remark"), ("Waterway", "waterway")):
        if (p.get(key) or "").strip():
            rows.append([label, p[key].strip()])
    if p.get("district"):
        rows.append(["District", f"Coast Guard District {p['district']}"])
    unlisted = "" if p.get("listed", True) else "Not in the current Light List: shown where the notice puts it."
    d = fmt_date(data_date)
    footer = (f"Coast Guard data of {d}. " if d else "") + "Not for navigation."
    return {"title": p.get("name") or "Aid to navigation", "subtitle": " · ".join(sub), "status": status,
            "status_note": note, "rows": rows, "unlisted": unlisted, "footer": footer}


def stale_text(meta: dict | None, now_ms: float) -> str:
    """'Coast Guard data not updated for 3 days' once meta.json is older than stale_after_hours (72), else ''."""
    from datetime import datetime
    if not meta or not meta.get("generated_at"):
        return ""
    t = datetime.fromisoformat(meta["generated_at"].replace("Z", "+00:00")).timestamp() * 1000
    hours = (now_ms - t) / 3600000
    if hours <= (meta.get("stale_after_hours") or 72):
        return ""
    days = int(hours // 24)
    return f"Coast Guard data not updated for {days} day{'' if days == 1 else 's'}"
