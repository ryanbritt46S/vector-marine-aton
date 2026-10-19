"""Which symbol each aid gets: a case for every symbol (vmaton/sample.py CASES) plus real Light List rows."""
import pytest

from vmaton.classify import BADGES, SYMBOLS, classify, color_from_text, light_color, norm_color
from vmaton.icons import draw
from vmaton.sample import CASES


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_every_symbol(case):
    sym, dtype, color, structure, char, rng, name = case
    assert classify(dtype, color, structure, char, float(rng) if rng else None, name)[0] == sym


def test_table_covers_every_symbol():
    assert {c[0] for c in CASES} == set(SYMBOLS)


# real rows (district, name, DESCRIPTION_TYPE, COLOR, STRUCTURE_REMARK, LIGHT_CHAR, LIGHT_NOM_RANGE) -> sym, kind
REAL = [
    ("Barnegat Inlet Lighted Buoy 1", "LB", "G", "Green.", "Fl G 2.5s", 5, "lb-g", "lighted_buoy"),
    ("Barnegat Inlet Buoy 2", "ULB", "R", "Red nun.", "", None, "nun-r", "buoy"),
    ("Barnegat Inlet Buoy 3", "ULB", "G", "Green can.", "", None, "can-g", "buoy"),
    ("Barnegat Inlet North Jetty Danger Buoy B", "ULB", "WO", "White and orange; can.", "", None, "reg-danger", "buoy"),
    ("Barnegat Inlet Outer Lighted Whistle Buoy BI", "LB", "RW", "Red and white stripes with red spherical topmark.", "Mo (A) W", 6, "lb-rw", "lighted_buoy"),
    ("Barnegat Inlet North Breakwater Light 6", "LT", "R", "TR on multi-pile structure.", "Q R", 5, "light-r", "light"),
    ("Barnegat Inlet South Breakwater Light 7", "LT", "G", "SG on skeleton tower.", "Q G", 5, "light-g", "light"),
    ("Metompkin Daybeacon 5", "DBN", "G", "SG on pile.", "", None, "db-sq-g", "daybeacon"),
    ("Some Creek Daybeacon 4", "DBN", "", "TR-TY on pile.", "", None, "db-tri-r", "daybeacon"),
    ("Virginia Inside Passage Warning Daybeacon", "DBN", "WO", 'NW on pile worded " Danger Shoal".', "", None, "db-reg", "daybeacon"),
    ("Shinnecock Light", "LTMA", "N/A", "Skeleton tower.", "Fl (2)W 15s", 11, "light-major", "major_light"),
    ("Montauk Point Light", "LTMA", "", "White conical tower with red stripe.", "Fl W 5s", 14, "light-major", "major_light"),
    ("A Light", "LT", "", "On pile.", "Fl W 6s", 12, "light-major", "major_light"),
    ("Princes Bay Range Front Light", "RF", "", "KRW on white skeleton tower.", "Q R", None, "range-front", "range_light"),
    ("Princes Bay Range Rear Light", "RR", "", "KRW on grey monopole.", "Iso G 6s", None, "range-rear", "range_light"),
    ("Craney Island Disposal Area North Range Front Daybeacon", "RFDB", "RWR", "KRW on pile.", "", None, "db-range", "range_daybeacon"),
    ("Miami Turning Basin Articulated Light A", "BBL", "RW", "NR on mast.", "Iso W 6s", 4, "light-w", "articulated_light"),
    ("Elizabethport Directional Light", "DLT", "N/A", "On skeleton tower.", "F W R G", None, "light-w", "directional_light"),
    ("Newport - Pell Bridge Racon", "RACN", "", "On bridge.", "", None, "racon", "racon"),
    ("Manana Island VAIS 14M", "VAIS", "", "", "", None, "vais", "virtual_ais"),
    ("Braga Bridge Sound Signal", "SSIG", "N/A", "", "", None, "sound", "sound_signal"),
    ("Bar Harbor CG Mooring Buoy", "ULB", "WBu", "White with blue band.", "", None, "mooring", "buoy"),
    ("Little Egg Inlet Buoy 4", "ULB", "R", " Red nun.", "", None, "nun-r", "buoy"),
    ("Hatteras Inlet Channel Buoy 12B", "ULB", "", "Red nun.", "", None, "nun-r", "buoy"),
    ("Some Lighted Buoy 3", "LB", "", "", "Fl G 4s", 4, "lb-g", "lighted_buoy"),
    ("Junction Lighted Buoy", "LB", "RGR", "Red and green bands.", "Fl (2+1)R 6s", 4, "lb-rgr", "lighted_buoy"),
    ("Isolated Danger Buoy", "ULB", "BRB", "Black and red bands.", "", None, "pillar-brb", "buoy"),
    ("Safe water spar", "ULB", "RW", "Red and white stripes; spar.", "", None, "pillar-rw", "buoy"),
    ("Junction Daybeacon", "DBN", "RGR", "JR on pile.", "", None, "db-jn-r", "daybeacon"),
]


@pytest.mark.parametrize("row", REAL, ids=[r[0] for r in REAL])
def test_real_rows(row):
    name, dtype, color, structure, char, rng, sym, kind = row
    got = classify(dtype, color, structure, char, rng, name)
    assert got[:2] == (sym, kind)


def test_colours():
    assert norm_color("N/A") == "" and norm_color("R/W STRIPES") == "RW" and norm_color("wbu") == "WBu"
    assert color_from_text("Red nun.") == "R" and color_from_text("SG-SY on pile.") == "G"
    assert color_from_text("Red and white stripes; spar.") == "RW" and color_from_text("JG on pile.") == "GRG"
    assert color_from_text("White with Orange bands.") == "WO" and color_from_text("Mono pile") == ""
    assert light_color("Fl (2+1)R 6s") == "R" and light_color("F W R G") == "W" and light_color("Mo (A) W") == "W"
    assert light_color("") == ""


def test_icons_draw_at_every_ratio():
    for sym in list(SYMBOLS) + list(BADGES):
        for r in (1, 2, 3):
            im = draw(sym, r)
            assert im.size == (48 * r, 48 * r)
            assert im.getbbox() is not None, sym
