"""Which symbol each aid gets (sym) and what kind of aid it is (kind), from the Light List's type, colour,
structure text and light.

The symbols are our own simple, chart-like drawings (vmaton/icons.py): cans, nuns, spheres and pillars for
buoys, a magenta flare for a light, squares and triangles for daybeacons. They are not NOAA or IHO artwork.
docs/SPEC.md has the table; tests/test_classify.py has a case for every symbol.
"""
from __future__ import annotations

import re

# sym -> what it shows (the legend and docs/SPEC.md)
SYMBOLS = {
    # unlighted buoys
    "can-g": "Green can (lateral, keep on your left returning from sea)",
    "can-r": "Red can",
    "can-y": "Yellow can (special purpose)",
    "can-w": "White can",
    "nun-r": "Red nun (lateral, keep on your right returning from sea)",
    "nun-g": "Green nun",
    "nun-y": "Yellow nun (special purpose)",
    "can-grg": "Preferred channel can, green-red-green",
    "nun-rgr": "Preferred channel nun, red-green-red",
    "sphere-rw": "Safe water sphere, red and white",
    "sphere-y": "Yellow sphere (special purpose)",
    "pillar-rw": "Safe water buoy, red and white stripes",
    "pillar-brb": "Isolated danger buoy, black-red-black",
    "reg-danger": "Regulatory buoy: danger (orange diamond)",
    "reg-control": "Regulatory buoy: controlled area (orange circle)",
    "reg-info": "Regulatory buoy: information (orange square)",
    "reg-exclusion": "Regulatory buoy: keep out (orange diamond with a cross)",
    "reg-plain": "Regulatory buoy, white and orange",
    "mooring": "Mooring buoy, white with a blue band",
    "buoy-other": "Buoy",
    # lighted buoys: a pillar with a magenta light flare
    "lb-g": "Green lighted buoy",
    "lb-r": "Red lighted buoy",
    "lb-y": "Yellow lighted buoy (special purpose)",
    "lb-w": "White lighted buoy",
    "lb-rw": "Safe water lighted buoy, red and white",
    "lb-rgr": "Preferred channel lighted buoy, red-green-red",
    "lb-grg": "Preferred channel lighted buoy, green-red-green",
    "lb-brb": "Isolated danger lighted buoy, black-red-black",
    "lb-wo": "Regulatory lighted buoy, white and orange",
    "lb-other": "Lighted buoy",
    # daybeacons
    "db-sq-g": "Green square daybeacon (SG)",
    "db-sq-r": "Red square daybeacon",
    "db-sq-y": "Yellow square daybeacon",
    "db-sq-w": "White square daybeacon",
    "db-tri-r": "Red triangle daybeacon (TR)",
    "db-tri-g": "Green triangle daybeacon",
    "db-tri-y": "Yellow triangle daybeacon",
    "db-tri-w": "White triangle daybeacon",
    "db-jn-g": "Junction daybeacon, green square with a red band (JG)",
    "db-jn-r": "Junction daybeacon, red triangle with a green band (JR)",
    "db-dia-w": "White diamond daybeacon (no lateral meaning)",
    "db-dia-r": "Red and white diamond daybeacon (no lateral meaning)",
    "db-dia-g": "Green and white diamond daybeacon (no lateral meaning)",
    "db-dia-y": "Yellow diamond daybeacon (special purpose)",
    "db-dia-b": "Black and white diamond daybeacon (no lateral meaning)",
    "db-reg": "Regulatory daybeacon, white with an orange diamond",
    "db-range": "Range daybeacon",
    "db-rw": "Safe water daybeacon, red and white",
    "db-other": "Daybeacon",
    # lights
    "light-r": "Light, red",
    "light-g": "Light, green",
    "light-w": "Light, white",
    "light-y": "Light, yellow",
    "light-major": "Major light (nominal range 10 NM or more)",
    "range-front": "Range front light",
    "range-rear": "Range rear light",
    # signals
    "racon": "Racon (radar beacon)",
    "vais": "Virtual AIS aid (V-AtoN)",
    "sound": "Sound signal",
    "other": "Aid to navigation",
}
# The status rings (drawn under the aid's symbol)
BADGES = {
    "badge-missing": "Missing, off station or destroyed (red ring, !)",
    "badge-fault": "Light out or damaged (amber ring, !)",
    "badge-temporary": "Temporary change: discontinued, relocated, replaced (grey dashed ring)",
}

KIND_OF = {
    "LB": "lighted_buoy", "ULB": "buoy", "DBN": "daybeacon", "LT": "light", "LTMA": "major_light",
    "RF": "range_light", "RR": "range_light", "RFDB": "range_daybeacon", "RRDB": "range_daybeacon",
    "DLT": "directional_light", "BBL": "articulated_light", "RACN": "racon", "VAIS": "virtual_ais",
    "SSIG": "sound_signal",
}
LIGHTS = ("LT", "DLT", "BBL", "LTMA")

COLOR_ALIASES = {"R/W STRIPES": "RW", "GW": "G", "YBY": "Y", "WBW": "W", "BR": "BRB", "WBU": "WBu", "GRAY": "",
                 "N/A": "", "NA": ""}
SIMPLE = {"R": "r", "G": "g", "Y": "y", "W": "w"}


def norm_color(color: str | None) -> str:
    c = re.sub(r"\s+", " ", (color or "").strip()).upper()
    if c in COLOR_ALIASES:
        return COLOR_ALIASES[c]
    return c


def light_color(char: str | None) -> str:
    """First colour of a light characteristic: 'Fl (2+1)R 6s' -> 'R', 'F W R G' -> 'W', '' -> ''."""
    s = re.sub(r"\([^)]*\)", " ", (char or "").upper())
    m = re.search(r"(?<![A-Z])(BU|W|R|G|Y)(?![A-Z])", s)
    return {"BU": "W"}.get(m[1], m[1]) if m else ""


DAYBOARD = re.compile(r"^([STNJKMC])([A-Z]{1,3})(?=$|[\s\-.,;:(])")
COLOR_WORDS = {"red": "R", "green": "G", "yellow": "Y", "white": "W", "black": "B", "orange": "WO"}


def color_from_text(structure: str | None) -> str:
    """The colour from the structure text when the COLOR column is empty: 'Red nun.' -> 'R',
    'Red and white stripes ...' -> 'RW', 'SG on pile.' -> 'G', 'White with orange bands.' -> 'WO'."""
    s = (structure or "").strip()
    t = s.lower()
    if not t:
        return ""
    m = DAYBOARD.match(s)
    if m:
        shape, cc = m[1], m[2]
        if shape == "J":
            return {"G": "GRG", "R": "RGR"}.get(cc[:1], "")
        if shape in "KM":
            return "RW"
        return {"G": "G", "R": "R", "Y": "Y", "W": "W", "B": "B"}.get(cc[:1], "")
    if re.search(r"red (and|with) white|white and red", t):
        return "RW"
    if "orange" in t:
        return "WO"
    if re.search(r"green (and|with) red", t):
        return "GRG"
    if re.search(r"red (and|with) green", t):
        return "RGR"
    if re.search(r"black.{0,12}red", t):
        return "BRB"
    if "blue" in t and "white" in t:
        return "WBu"
    m = re.match(r"^(red|green|yellow|white|black)\b", t)
    return COLOR_WORDS[m[1]] if m else ""


def buoy_shape(structure: str, code: str) -> str:
    t = (structure or "").lower().replace("spherical topmark", "topmark")
    if re.search(r"\bnun\b", t):
        return "nun"
    if re.search(r"\bcan\b", t):
        return "can"
    if re.search(r"\bspher", t):
        return "sphere"
    if re.search(r"\b(spar|pillar|pole)\b", t):
        return "pillar"
    return {"R": "nun", "RGR": "nun", "RW": "pillar", "BRB": "pillar"}.get(code, "can")


def reg_mark(structure: str, name: str) -> str:
    """The orange mark of a white-and-orange regulatory aid: diamond (danger), diamond with a cross (keep out),
    circle (controlled area), square (information)."""
    s = (structure or "").lower()
    n = f"{s} {(name or '').lower()}"
    if re.search(r"cross|keep out|exclusion", n):
        return "exclusion"
    if "diamond" in s:
        return "danger"
    if "circle" in s:
        return "control"
    if re.search(r"square|rectangle", s):
        return "info"
    if re.search(r"danger|hazard|warning|obstruction|rock|shoal|reef|jetty|wreck|dike|submerged", n):
        return "danger"
    if re.search(r"speed|no wake|slow|idle|mph|regulat|restrict|anchor|swim|controlled|zone", n):
        return "control"
    if re.search(r"info|marina|pump|fuel", n):
        return "info"
    return "plain"


def classify(dtype: str, color: str, structure: str = "", char: str = "", rng=None, name: str = "",
             major_range: float = 10) -> tuple[str, str, str]:
    """(sym, kind, colour code) for one aid."""
    dtype = (dtype or "").upper()
    code = norm_color(color) or color_from_text(structure)
    lc = light_color(char)
    if not code and dtype in ("LB", *LIGHTS):
        code = lc
    kind = KIND_OF.get(dtype, "other")
    major = dtype == "LTMA" or (dtype in LIGHTS and rng is not None and float(rng) >= major_range)
    if major:
        return "light-major", "major_light", code
    if dtype in ("LT", "DLT", "BBL"):
        c = SIMPLE.get(lc or code, "w")
        return f"light-{c}", kind, code
    if dtype == "RF":
        return "range-front", kind, code
    if dtype == "RR":
        return "range-rear", kind, code
    if dtype in ("RFDB", "RRDB"):
        return "db-range", kind, code
    if dtype == "RACN":
        return "racon", kind, code
    if dtype == "VAIS":
        return "vais", kind, code
    if dtype == "SSIG":
        return "sound", kind, code
    if dtype == "LB":
        sym = {"G": "lb-g", "R": "lb-r", "Y": "lb-y", "W": "lb-w", "RW": "lb-rw", "RGR": "lb-rgr", "GRG": "lb-grg",
               "BRB": "lb-brb", "WO": "lb-wo"}.get(code, "lb-other")
        return sym, kind, code
    if dtype == "ULB":
        return unlighted(code, structure, name), kind, code
    if dtype == "DBN":
        return daybeacon(code, structure, name), kind, code
    if char:
        return f"light-{SIMPLE.get(lc, 'w')}", "light", code
    return "other", kind, code


def unlighted(code: str, structure: str, name: str) -> str:
    if code == "WO":
        return f"reg-{reg_mark(structure, name)}"
    if code == "WBu":
        return "mooring"
    if code == "BRB":
        return "pillar-brb"
    shape = buoy_shape(structure, code)
    if code == "RW":
        return "sphere-rw" if shape == "sphere" else "pillar-rw"
    if code == "GRG":
        return "can-grg"
    if code == "RGR":
        return "nun-rgr"
    c = SIMPLE.get(code)
    if not c:
        return "buoy-other"
    if shape == "sphere":
        return "sphere-y" if c == "y" else ("sphere-rw" if c == "r" else f"can-{c}")
    if shape == "nun" and c in ("r", "g", "y"):
        return f"nun-{c}"
    return f"can-{c}" if c in ("g", "r", "y", "w") else "buoy-other"


def daybeacon(code: str, structure: str, name: str) -> str:
    m = DAYBOARD.match((structure or "").strip())
    worded = re.search(r"\bworded\b|danger|warning|regulat", f"{structure} {name}".lower()) is not None
    if m:
        shape, cc = m[1], m[2]
        c = SIMPLE.get(cc[:1], "")
        if shape == "S":
            return f"db-sq-{c}" if c else "db-other"
        if shape == "T":
            return f"db-tri-{c}" if c else "db-other"
        if shape == "J":
            return "db-jn-g" if cc.startswith("G") else "db-jn-r"
        if shape == "N":
            if cc.startswith("W") and (code == "WO" or worded):
                return "db-reg"
            return {"W": "db-dia-w", "R": "db-dia-r", "G": "db-dia-g", "Y": "db-dia-y", "B": "db-dia-b"}.get(cc[:1], "db-other")
        if shape == "K":
            return "db-range"
        if shape == "M":
            return "db-rw"
        return "db-other"
    return {"G": "db-sq-g", "R": "db-tri-r", "Y": "db-sq-y", "WO": "db-reg", "GRG": "db-jn-g", "RGR": "db-jn-r",
            "RW": "db-rw"}.get(code, "db-other")
