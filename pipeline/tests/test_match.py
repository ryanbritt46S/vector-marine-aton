"""Putting notices on their aids."""
from vmaton.lightlist import Aid
from vmaton.match import dist_m, in_area, match, summarize, unlisted_aids
from vmaton.notices import Notice
from vmaton.words import decode_codes


def aid(llnr, name, lon, lat, district=5, id_=None):
    a = Aid(district=district, llnr=llnr, name=name, private=False, dtype="LB", color="R", structure="", char="",
            height=None, range=None, lon=lon, lat=lat, subtype="FL", waterway="", remark="")
    a.id = id_ or f"{district}-{llnr}"
    return a


def notice(llnr, name, lon, lat, raw="MISSING", district=5, product="disc", since="2026-01-02", bnm="", uid="1"):
    return Notice(product=product, district=district, llnr=llnr, name=name, raw=raw, codes=decode_codes(raw, product),
                  since=since, lon=lon, lat=lat, bnm=bnm, waterway="W", private=False, dtype="ULB", color="G",
                  subtype="FL", uid=uid)


def test_by_number_then_nearest_duplicate():
    a1, a2 = aid("5400.1", "Dup", -76.1, 38.9, id_="5-5400.1"), aid("5400.1", "Dup", -76.2, 38.95, id_="5-5400.1-2")
    r = match([a1, a2], [notice("5400.1", "Dup", -76.199, 38.95)])
    assert r.by_number == 1 and not a1.notices and len(a2.notices) == 1


def test_number_wins_over_name_and_district_matters():
    a = aid("900", "Barnegat Inlet Lighted Buoy 1", -74.07679, 39.74692)
    other = aid("900", "Elsewhere", -70.0, 42.0, district=1)
    r = match([a, other], [notice("900", "Barnegat Inlet Lighted Buoy 1", -74.0768, 39.7469)])
    assert r.by_number == 1 and a.notices and not other.notices


def test_name_fallback_within_300_m_only():
    a = aid("1105", "Little Egg Inlet Lighted Buoy 2", -74.28552, 39.47039)
    near = notice("", "Little Egg Inlet Lighted Buoy 2", -74.28552, 39.47039 + 0.002)        # ~220 m
    far = notice("", "Little Egg Inlet Lighted Buoy 2", -74.28552, 39.47039 + 0.004)         # ~445 m
    assert 200 < dist_m(a.lon, a.lat, near.lon, near.lat) < 300 < dist_m(a.lon, a.lat, far.lon, far.lat)
    r = match([a], [near, far])
    assert r.by_name == 1 and r.unmatched == [far] and a.notices == [near]
    # names are compared case-insensitively, in the same district only
    b = aid("1", "Buoy 1", -74.0, 39.0)
    r2 = match([b], [notice("", "BUOY 1", -74.0, 39.0005), notice("", "Buoy 1", -74.0, 39.0005, district=1)])
    assert r2.by_name == 1 and len(r2.unmatched) == 1


def test_unmatched_become_their_own_aids():
    ns = [notice("", "Mount Sinai Jetty Hazard Daybeacon A", -73.04, 40.96, raw="LT EXT", uid="77"),
          notice("", "Mount Sinai Jetty Hazard Daybeacon A", -73.04, 40.96, raw="RELOCATED", product="tmp", uid="78"),
          notice("", "No position", None, None)]
    out = unlisted_aids(ns)
    assert len(out) == 1 and out[0].id == "5-n77" and len(out[0].notices) == 2
    assert (out[0].lon, out[0].lat, out[0].name) == (-73.04, 40.96, "Mount Sinai Jetty Hazard Daybeacon A")


def test_area():
    box = (-82, 17, -64, 46)
    assert in_area(notice("1", "x", -74, 39), [1, 5, 7], box)
    assert not in_area(notice("1", "x", -80, 40.4, district=9), [1, 5, 7], box)      # Lake Erie: district 9
    assert not in_area(notice("1", "x", -80, 40.4, district=2), [1, 5, 7], box)      # Ohio River at Pittsburgh
    n = notice("1", "x", -74, 39, district=None)
    assert in_area(n, [1, 5, 7], box) and not in_area(notice("1", "x", -90, 30, district=None), [1, 5, 7], box)


def test_summarize():
    assert summarize([]) == {}
    s = summarize([notice("1", "x", 0, 0, raw="LT EXT", since="2026-09-01", bnm="0394LM"),
                   notice("1", "x", 0, 0, raw="STRUCT DEST/TRUB", since="2026-03-05"),
                   notice("1", "x", 0, 0, raw="RELOCATED FOR DREDGING", product="tmp", since="2026-01-01")])
    assert s["status"] == "missing"
    assert s["status_text"] == ("Structure destroyed; light out; temporarily replaced by an unlighted buoy; "
                                "relocated for dredging")
    assert s["status_since"] == "2026-03-05"
    assert s["status_raw"] == "STRUCT DEST/TRUB; LT EXT; RELOCATED FOR DREDGING"
    assert s["bnm"] == "0394LM"
    t = summarize([notice("1", "x", 0, 0, raw="DISCONTINUED", product="tmp", since="2026-05-05")])
    assert (t["status"], t["status_text"], t["status_since"]) == ("temporary", "Discontinued", "2026-05-05")
