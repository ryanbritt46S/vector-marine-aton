"""Status codes in plain words, the light characteristic spelled out, dates, the card."""
from vmaton import words as W


def test_status_codes():
    assert W.decode_codes("MISSING") == [("MISSING", "Missing", "missing")]
    assert W.decode_codes("LT IMCH/STRUCT DMGD") == [("LT IMCH", "Light not showing as listed", "fault"),
                                                    ("STRUCT DMGD", "Structure damaged", "fault")]
    assert W.decode_codes("OFF STA")[0][1:] == ("Off station", "missing")
    assert W.decode_codes("STRUCT DEST")[0][1:] == ("Structure destroyed", "missing")
    assert W.decode_codes("LT EXT")[0][1:] == ("Light out", "fault")
    assert W.decode_codes("TRLB")[0][1:] == ("Temporarily replaced by a lighted buoy", "temporary")
    assert W.decode_codes("TRUB")[0][1:] == ("Temporarily replaced by an unlighted buoy", "temporary")
    assert W.decode_codes("Missing")[0][1:] == ("Missing", "missing")
    assert W.decode_codes("RELOCATED FOR DREDGING", "tmp")[0][1:] == ("Relocated for dredging", "temporary")
    assert W.decode_codes("DISCONTINUED", "tmp")[0][1:] == ("Discontinued", "temporary")
    # unknown codes: shown raw, the product's default severity
    assert W.decode_codes("Temp V-AIS: MMSI 993672514") == [("Temp V-AIS: MMSI 993672514", "Temp V-AIS: MMSI 993672514", "fault")]
    assert W.decode_codes("SOMETHING NEW", "tmp") == [("SOMETHING NEW", "SOMETHING NEW", "temporary")]
    assert W.decode_codes("") == [] and W.decode_codes(None) == []
    assert W.worst(["temporary", "missing", "fault"]) == "missing" and W.worst([]) == ""


def test_join_and_status_line():
    assert W.join_words(["Structure destroyed", "Temporarily replaced by an unlighted buoy"]) == \
        "Structure destroyed; temporarily replaced by an unlighted buoy"
    assert W.join_words(["Light out", "AIS not working"]) == "Light out; AIS not working"
    assert W.status_line("Missing", "2025-12-02") == "MISSING since Dec 2, 2025"
    assert W.status_line("Light out", "") == "LIGHT OUT"
    assert W.status_line("", "2025-12-02") == ""
    assert W.fmt_date("2026-10-19") == "Oct 19, 2026" and W.fmt_date("") == "" and W.fmt_date(None) == ""


def test_light_words():
    cases = {
        "Fl G 4s": "flashing green, every 4 s",
        "Fl R 2.5s": "flashing red, every 2.5 s",
        "Q R": "quick flashing red",
        "VQ W": "very quick flashing white",
        "Iso W 6s": "isophase white, every 6 s",
        "Oc W 4s": "occulting white, every 4 s",
        "F W": "fixed white",
        "F W R G": "fixed white, red and green",
        "Mo (A) W": "Morse code (A) white",
        "Fl (2)W 5s": "group flashing (2) white, every 5 s",
        "Fl (2+1)R 6s": "composite group flashing (2+1) red, every 6 s",
        "FL Y 3s": "flashing yellow, every 3 s",
        "LFl W 10s": "long flashing white, every 10 s",
        "Al Fl W R 10s": "alternating flashing white and red, every 10 s",
        "Q (3) W 10s": "group quick flashing (3) white, every 10 s",
    }
    for char, want in cases.items():
        assert W.light_words(char) == want, char
    for bad in ("", None, "STROBE", "Fl", "Fl G 4s (2 lights)"):
        assert W.light_words(bad) is None


def test_card():
    p = {"id": "5-1105", "llnr": "1105", "name": "Little Egg Inlet Lighted Buoy 2", "kind": "lighted_buoy",
         "char": "Fl R 4s", "range": 5, "structure": "Red.", "remark": "Position of buoy frequently shifts with changing conditions.",
         "waterway": "Little Egg Inlet", "district": 5, "private": False, "status": "missing", "status_text": "Missing",
         "status_since": "2025-12-02", "status_raw": "MISSING", "bnm": ""}
    c = W.card(p, "2026-10-19")
    assert c["title"] == "Little Egg Inlet Lighted Buoy 2"
    assert c["subtitle"] == "Lighted buoy · Light List 1105 · Federal aid"
    assert c["status"] == "MISSING since Dec 2, 2025"
    assert c["status_note"] == "Local Notice to Mariners. Coast Guard code: MISSING."
    assert c["rows"] == [["Light", "Fl R 4s (flashing red, every 4 s)"], ["Range", "5 NM"], ["Structure", "Red."],
                         ["Remarks", "Position of buoy frequently shifts with changing conditions."],
                         ["Waterway", "Little Egg Inlet"], ["District", "Coast Guard District 5"]]
    assert c["unlisted"] == "" and c["footer"] == "Coast Guard data of Oct 19, 2026. Not for navigation."
    q = W.card({"name": "X", "kind": "daybeacon", "private": True, "listed": False, "height": 12.5, "char": "STROBE",
                "status": "fault", "status_text": "Light out", "status_raw": "LT EXT", "bnm": "0394LM"})
    assert q["subtitle"] == "Daybeacon · Private aid"
    assert q["rows"] == [["Light", "STROBE"], ["Height", "12.5 ft"]]
    assert q["status"] == "LIGHT OUT" and q["status_note"] == "Local Notice to Mariners, broadcast notice 0394LM. Coast Guard code: LT EXT."
    assert q["unlisted"].startswith("Not in the current Light List") and q["footer"] == "Not for navigation."
    assert W.kind_words("nope") == "Aid to navigation"
