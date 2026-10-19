"""Reading the Light List CSV and the notices."""
import json

from vmaton import lightlist as L
from vmaton import notices as N

HEADER = ("ATU,LIGHT_LIST_NUMBER,NAME,AID_TYPE,DESCRIPTION_TYPE,COLOR,STATE,GROUP_JURISDICTION,REMARK,STRUCTURE_REMARK,"
          "LIGHT_CHAR,LIGHT_FOCAL_PLANE,LIGHT_NOM_RANGE,ASSIGNED_LONGITUDE,ASSIGNED_LATITUDE,DECIMAL_LONGITUDE,"
          "DECIMAL_LATITUDE,AID_SUBTYPE,HWATERWAY_NAME,VOLUME_NUMBER,VOLUME_TITLE,NON_AID_TYPE,RIVER_MILE,RIVER_NAME,RIVER_BANK\n")

# real rows from lightListD05_1.csv / D01 (Oct 19, 2026): quoted commas, doubled quotes, a remark with commas
REAL = HEADER + (
    '5,6590,"Virginia Inside Passage Warning Daybeacon",FD,DBN,WO,VA,"CG SECTOR VIRGINIA",,"NW on pile worded "" Danger Shoal"".",'
    ',,,075-58-13.714W,37-06-53.092N,-75.97048,37.11475,FX,"Virginia Inside Passage",02,"Atlantic Coast (Tom\'s Rivers  New Jersey to Little River  South Carolina).",,0,,\n'
    '1,35135,"Sandy Hook Channel Range Front Light",FD,RF,,NJ,"CG SECTOR NEW YORK","Red from 063.0° to 073.0°. Green from 300.5° to 315.5°, see chart.",'
    '"KGB (E section) KRW (Main section) on skeleton tower.",Q W,45,6,,,-73.99309,40.48754,FX,"Sandy Hook Channel",01,"Atlantic Coast",,0,,\n'
    '5,900,"Barnegat Inlet Lighted Buoy 1",FD,LB,G,NJ,"CG SECTOR DELAWARE BAY","Position of buoy frequently shifts with changing conditions.",'
    '"Green.",Fl G 2.5s,,5,074-04-36.444W,39-44-48.912N,-74.07679,39.74692,FL,"Barnegat Inlet",02,"Atlantic Coast",,0,,\n'
    '5,5400.1,"Dup Light",PA,LT,R,MD,,,"TR on pile.",Q R,12,3,,,-76.1,38.9,FX,"X",02,"",,0,,\n'
    '5,5400.1,"Dup Light",PA,LT,R,MD,,,"TR on pile.",Q R,12,3,,,-76.2,38.95,FX,"X",02,"",,0,,\n'
    '5,7,"Only DMS",FD,ULB,R,NJ,,,"Red nun.",,,,074-04-36.444W,39-44-48.912N,,,FL,"X",02,"",,0,,\n'
    '5,8,"No position",FD,ULB,R,NJ,,,"Red nun.",,,,,,,,FL,"X",02,"",,0,,\n'
)


def test_quoted_commas_and_doubled_quotes():
    aids, skipped = L.parse(REAL.encode("utf-8"))
    assert skipped == 1
    va = aids[0]
    assert va.structure == 'NW on pile worded " Danger Shoal".'
    assert va.district == 5 and va.llnr == "6590" and va.dtype == "DBN" and va.color == "WO"
    assert va.waterway == "Virginia Inside Passage"
    sh = aids[1]
    assert sh.remark == "Red from 063.0° to 073.0°. Green from 300.5° to 315.5°, see chart."
    assert sh.char == "Q W" and sh.height == 45 and sh.range == 6 and sh.color == ""
    b = aids[2]
    assert (b.name, b.char, b.range, b.height, b.lon, b.lat, b.private) == ("Barnegat Inlet Lighted Buoy 1", "Fl G 2.5s", 5, None, -74.07679, 39.74692, False)
    assert aids[3].private and aids[3].llnr == "5400.1"


def test_dms_when_no_decimal_and_ids_for_duplicates():
    aids, _ = L.parse(REAL.encode("utf-8"))
    only = [a for a in aids if a.name == "Only DMS"][0]
    assert abs(only.lon - -74.07679) < 1e-4 and abs(only.lat - 39.74692) < 1e-4
    L.assign_ids(aids)
    assert [a.id for a in aids if a.name == "Dup Light"] == ["5-5400.1", "5-5400.1-2"]
    assert len({a.id for a in aids}) == len(aids)


def test_numbers_and_llnr():
    assert L.norm_llnr(36826.700000000004) == "36826.7"
    assert L.norm_llnr(28722.350000000002) == "28722.35"
    assert L.norm_llnr(900) == "900" and L.norm_llnr("603.03") == "603.03" and L.norm_llnr(None) == ""
    assert L.number("2.5") == 2.5 and L.number("15") == 15 and L.number("") is None and L.number("x") is None
    assert L.parse_dms("075-58-13.714W") < -75.97 and L.parse_dms("37-06-53.092N") > 37.11
    assert L.clean("Tom's Rivers  New Jersey") == "Tom's Rivers New Jersey"


def test_bad_file():
    try:
        L.parse(b"a,b,c\n1,2,3\n")
    except ValueError as e:
        assert "not a Light List" in str(e)
    else:
        raise AssertionError("should refuse")


def test_notices_parse_and_dates():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.28552, 39.47039]},
         "properties": {"ATU": 5, "LLNR": 1105, "NAME": "Little Egg Inlet Lighted Buoy 2", "DISCREP_STATUS": "MISSING",
                        "CREATE_DATE": 1764704265000, "BNM_NUM": None, "LNM_UID": 1, "AID_TYPE": "FD",
                        "DECIMAL_LONGITUDE": -74.28552, "DECIMAL_LATITUDE": 39.47039}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-81.0, 29.0]},
         "properties": {"ATU": 7, "LLNR": 36826.700000000004, "NAME": "X", "DISCREP_STATUS": "STRUCT DEST/TRUB",
                        "CREATE_DATE": 1700000000000, "DECIMAL_LONGITUDE": None, "DECIMAL_LATITUDE": None}},
        {"type": "Feature", "geometry": None, "properties": {"ATU": 7, "NAME": "Y", "DISCREP_STATUS": None}},
    ]}
    ns = N.parse(json.dumps(fc).encode(), "disc")
    assert len(ns) == 2
    assert (ns[0].since, ns[0].raw, ns[0].codes[0][2], ns[0].llnr) == ("2025-12-02", "MISSING", "missing", "1105")
    assert ns[1].llnr == "36826.7" and ns[1].raw == "STRUCT DEST/TRUB" and (ns[1].lon, ns[1].lat) == (-81.0, 29.0)
    assert [c[2] for c in ns[1].codes] == ["missing", "temporary"]
