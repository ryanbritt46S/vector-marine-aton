"""Made-up Coast Guard files for tests and --sample: one aid for every symbol, and notices of each kind. Every
name says SAMPLE and meta.json has "sample": true; publish.py refuses to publish it.

CASES is also the classification table the tests check: (expected sym, DESCRIPTION_TYPE, COLOR,
STRUCTURE_REMARK, LIGHT_CHAR, LIGHT_NOM_RANGE, NAME).
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

CASES = [
    ("can-g", "ULB", "G", "Green can.", "", "", "Buoy 1"),
    ("can-r", "ULB", "R", "Red can.", "", "", "Buoy 2C"),
    ("can-y", "ULB", "Y", "Yellow can.", "", "", "Research Buoy A"),
    ("can-w", "ULB", "W", "White can.", "", "", "Buoy W"),
    ("nun-r", "ULB", "R", "Red nun.", "", "", "Buoy 2"),
    ("nun-g", "ULB", "G", "Green nun.", "", "", "Buoy 3N"),
    ("nun-y", "ULB", "Y", "Yellow nun.", "", "", "Buoy B"),
    ("can-grg", "ULB", "GRG", "Green and red bands; can.", "", "", "Junction Buoy C"),
    ("nun-rgr", "ULB", "RGR", "Red and green bands; nun.", "", "", "Junction Buoy D"),
    ("sphere-rw", "ULB", "RW", "Red and white sphere.", "", "", "Buoy SW"),
    ("sphere-y", "ULB", "Y", "Yellow sphere.", "", "", "Buoy Y"),
    ("pillar-rw", "ULB", "RW", "Red and white stripes with red spherical topmark.", "", "", "Approach Buoy A"),
    ("pillar-brb", "ULB", "BRB", "Black and red bands with two black spherical topmarks.", "", "", "Isolated Danger Buoy DH"),
    ("reg-danger", "ULB", "WO", "White can with orange bands and diamond worded REEF.", "", "", "Reef Danger Buoy A"),
    ("reg-control", "ULB", "WO", "White can with orange bands and circle worded SLOW NO WAKE.", "", "", "Regulatory Buoy SN"),
    ("reg-info", "ULB", "WO", "White can with orange bands and square worded MARINA.", "", "", "Information Buoy M"),
    ("reg-exclusion", "ULB", "WO", "White with orange diamond with cross worded KEEP OUT.", "", "", "Exclusion Buoy E"),
    ("reg-plain", "ULB", "WO", "White and orange.", "", "", "Buoy O"),
    ("mooring", "ULB", "WBu", "White with blue band.", "", "", "Coast Guard Mooring Buoy"),
    ("buoy-other", "ULB", "", "", "", "", "Buoy X"),
    ("lb-g", "LB", "G", "Green.", "Fl G 4s", "4", "Lighted Buoy 1"),
    ("lb-r", "LB", "R", "Red.", "Fl R 4s", "4", "Lighted Buoy 2"),
    ("lb-y", "LB", "Y", "Yellow.", "Fl Y 4s", "3", "Lighted Buoy A"),
    ("lb-w", "LB", "W", "White.", "Fl W 2.5s", "4", "Lighted Buoy W"),
    ("lb-rw", "LB", "RW", "Red and white stripes with red spherical topmark.", "Mo (A) W", "6", "Lighted Whistle Buoy SI"),
    ("lb-rgr", "LB", "RGR", "Red and green bands.", "Fl (2+1)R 6s", "4", "Junction Lighted Buoy BR"),
    ("lb-grg", "LB", "GRG", "Green and red bands.", "Fl (2+1)G 6s", "4", "Junction Lighted Buoy BG"),
    ("lb-brb", "LB", "BRB", "Black and red bands.", "Fl (2)W 5s", "5", "Isolated Danger Lighted Buoy DL"),
    ("lb-wo", "LB", "WO", "White with orange bands.", "Fl Y 4s", "3", "Hazard Lighted Buoy H"),
    ("lb-other", "LB", "", "", "", "", "Lighted Buoy Q"),
    ("db-sq-g", "DBN", "G", "SG on pile.", "", "", "Daybeacon 1"),
    ("db-sq-r", "DBN", "R", "SR on pile.", "", "", "Daybeacon 1R"),
    ("db-sq-y", "DBN", "Y", "SY on pile.", "", "", "Daybeacon 1Y"),
    ("db-sq-w", "DBN", "W", "SW on pile.", "", "", "Daybeacon 1W"),
    ("db-tri-r", "DBN", "R", "TR on pile.", "", "", "Daybeacon 2"),
    ("db-tri-g", "DBN", "G", "TG on pile.", "", "", "Daybeacon 2G"),
    ("db-tri-y", "DBN", "Y", "TY on pile.", "", "", "Daybeacon 2Y"),
    ("db-tri-w", "DBN", "W", "TW on pile.", "", "", "Daybeacon 2W"),
    ("db-jn-g", "DBN", "GRG", "JG on pile.", "", "", "Junction Daybeacon JG"),
    ("db-jn-r", "DBN", "RGR", "JR on pile.", "", "", "Junction Daybeacon JR"),
    ("db-dia-w", "DBN", "W", "NW on pile.", "", "", "Daybeacon N"),
    ("db-dia-r", "DBN", "RW", "NR on pile.", "", "", "Daybeacon NR"),
    ("db-dia-g", "DBN", "GW", "NG on pile.", "", "", "Daybeacon NG"),
    ("db-dia-y", "DBN", "Y", "NY on pile.", "", "", "Daybeacon NY"),
    ("db-dia-b", "DBN", "BW", "NB on pile.", "", "", "Daybeacon NB"),
    ("db-reg", "DBN", "WO", "NW on pile worded DANGER SHOAL.", "", "", "Warning Daybeacon"),
    ("db-range", "RFDB", "RWR", "KRW on pile.", "", "", "Range Front Daybeacon"),
    ("db-rw", "DBN", "RW", "MR on pile.", "", "", "Safe Water Daybeacon"),
    ("db-other", "DBN", "", "On pile.", "", "", "Daybeacon P"),
    ("light-r", "LT", "R", "TR on pile.", "Q R", "4", "Light 4"),
    ("light-g", "LT", "G", "SG on pile.", "Fl G 2.5s", "4", "Light 5"),
    ("light-w", "LT", "", "On pile.", "Iso W 6s", "5", "Light 7"),
    ("light-y", "LT", "Y", "NY on pile.", "Fl Y 4s", "3", "Light 8"),
    ("light-major", "LTMA", "", "White conical tower.", "Fl W 15s", "14", "Lighthouse"),
    ("range-front", "RF", "", "KRW on skeleton tower.", "Q W", "", "Range Front Light"),
    ("range-rear", "RR", "", "KRW on skeleton tower.", "Iso W 6s", "", "Range Rear Light"),
    ("racon", "RACN", "", "On bridge.", "", "", "Bridge Racon"),
    ("vais", "VAIS", "", "", "", "", "Virtual AIS V1"),
    ("sound", "SSIG", "", "On bridge abutment.", "", "", "Bridge Sound Signal"),
    ("other", "XYZ", "", "", "", "", "Unknown Aid"),
]

COLUMNS = ["ATU", "LIGHT_LIST_NUMBER", "NAME", "AID_TYPE", "DESCRIPTION_TYPE", "COLOR", "STATE", "GROUP_JURISDICTION",
           "REMARK", "STRUCTURE_REMARK", "LIGHT_CHAR", "LIGHT_FOCAL_PLANE", "LIGHT_NOM_RANGE", "ASSIGNED_LONGITUDE",
           "ASSIGNED_LATITUDE", "DECIMAL_LONGITUDE", "DECIMAL_LATITUDE", "AID_SUBTYPE", "HWATERWAY_NAME",
           "VOLUME_NUMBER", "VOLUME_TITLE", "NON_AID_TYPE", "RIVER_MILE", "RIVER_NAME", "RIVER_BANK"]

# where each district's made-up aids go (open water off NJ, NY and Miami; a 6-column grid 400 m apart)
ORIGIN = {1: (-73.93, 40.43), 5: (-74.02, 39.66), 7: (-80.07, 25.70)}


def rows_for(district: int) -> list[dict]:
    out = []
    lon0, lat0 = ORIGIN[district]
    for i, (sym, dtype, color, structure, char, rng, name) in enumerate(CASES):
        lon, lat = lon0 + (i % 6) * 0.005, lat0 + (i // 6) * 0.004
        floating = dtype in ("ULB", "LB")
        out.append({
            "ATU": district, "LIGHT_LIST_NUMBER": 90000 + i, "NAME": f"SAMPLE {name}",
            "AID_TYPE": "PA" if i % 7 == 6 else "FD", "DESCRIPTION_TYPE": dtype, "COLOR": color, "STATE": "",
            "GROUP_JURISDICTION": "SAMPLE", "REMARK": "Made up for testing." if i % 3 == 0 else "",
            "STRUCTURE_REMARK": structure, "LIGHT_CHAR": char, "LIGHT_FOCAL_PLANE": "15" if char and not floating else "",
            "LIGHT_NOM_RANGE": rng, "ASSIGNED_LONGITUDE": "", "ASSIGNED_LATITUDE": "",
            "DECIMAL_LONGITUDE": round(lon, 5), "DECIMAL_LATITUDE": round(lat, 5),
            "AID_SUBTYPE": "FL" if floating else "FX", "HWATERWAY_NAME": "Sample Channel", "VOLUME_NUMBER": "",
            "VOLUME_TITLE": "", "NON_AID_TYPE": "", "RIVER_MILE": "0", "RIVER_NAME": "", "RIVER_BANK": "",
        })
    return out


def feature(props: dict, lon: float, lat: float) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {**props, "DECIMAL_LONGITUDE": lon, "DECIMAL_LATITUDE": lat}}


def notice_for(row: dict, status: str, when: datetime, key: str = "DISCREP_STATUS", **over) -> dict:
    p = {"ATU": row["ATU"], "LLNR": row["LIGHT_LIST_NUMBER"], "NAME": row["NAME"], key: status,
         "CREATE_DATE": int(when.timestamp() * 1000), "WATERWAY_NAME": row["HWATERWAY_NAME"],
         "AID_TYPE": row["AID_TYPE"], "AID_SUBTYPE": row["AID_SUBTYPE"], "COLOR": row["COLOR"] or None,
         "DESCRIPTION_TYPE": row["DESCRIPTION_TYPE"], "BNM_NUM": "0001-26 SAMPLE", "LNM_UID": 1000 + row["LIGHT_LIST_NUMBER"]}
    p.update(over)
    return feature(p, row["DECIMAL_LONGITUDE"], row["DECIMAL_LATITUDE"])


def by_name(rows, name):
    return next(r for r in rows if r["NAME"] == f"SAMPLE {name}")


def write_sample(folder: Path, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rows = {d: rows_for(d) for d in (1, 5, 7)}
    for d, rs in rows.items():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)
        (folder / f"lightListD{d:02d}_1.csv").write_text(buf.getvalue())
    r5, r1, r7 = rows[5], rows[1], rows[7]
    days = lambda n: now - timedelta(days=n)  # noqa: E731
    fed = [
        notice_for(by_name(r5, "Lighted Buoy 2"), "MISSING", days(40)),
        notice_for(by_name(r5, "Light 5"), "LT EXT", days(3)),
        notice_for(by_name(r5, "Daybeacon 2"), "STRUCT DEST/TRUB", days(120)),
        notice_for(by_name(r1, "Lighted Buoy 1"), "OFF STATION", days(9)),
        notice_for(by_name(r7, "Light 4"), "LT IMCH/STRUCT DMGD", days(15)),
        # no Light List number: matched by its name (the aid is 50 m away)
        notice_for(by_name(r5, "Buoy 1"), "DAYMK MISSING", days(2), LLNR=None),
        # an aid that isn't in the Light List: shown at the notice's position
        feature({"ATU": 5, "LLNR": None, "NAME": "SAMPLE Jetty Hazard Daybeacon A", "DISCREP_STATUS": "LT EXT",
                 "CREATE_DATE": int(days(6).timestamp() * 1000), "AID_TYPE": "PA", "AID_SUBTYPE": "FX", "COLOR": "WO",
                 "DESCRIPTION_TYPE": "DBN", "WATERWAY_NAME": "Sample Channel", "BNM_NUM": None, "LNM_UID": 777},
                -74.035, 39.655),
        # another district (8): not shown
        feature({"ATU": 8, "LLNR": 5, "NAME": "SAMPLE Gulf Buoy", "DISCREP_STATUS": "MISSING",
                 "CREATE_DATE": int(days(4).timestamp() * 1000), "DESCRIPTION_TYPE": "ULB", "COLOR": "G"}, -88.0, 30.0),
    ]
    pri = [notice_for(by_name(r7, "Daybeacon 1"), "DBD DMGD", days(30), AID_TYPE="PA")]
    tmp = [notice_for(by_name(r5, "Lighted Buoy 1"), "RELOCATED FOR DREDGING", days(60), key="TC_STATUS"),
           notice_for(by_name(r5, "Lighted Buoy 2"), "DISCONTINUED", days(20), key="TC_STATUS"),
           notice_for(by_name(r1, "Buoy 2"), "SOMETHING NEW", days(1), key="TC_STATUS")]
    # the name-matched notice sits 50 m north of its aid
    fed[5]["properties"]["DECIMAL_LATITUDE"] += 0.00045
    fed[5]["geometry"]["coordinates"][1] += 0.00045
    fc = lambda fs: json.dumps({"type": "FeatureCollection", "features": fs})  # noqa: E731
    (folder / "discFedAid_1.geojson").write_text(fc(fed))
    (folder / "discPriAid_1.geojson").write_text(fc(pri))
    (folder / "tmpChange_1.geojson").write_text(fc(tmp))
    (folder / "discFedAidCor_1.geojson").write_text(fc([notice_for(by_name(r5, "Buoy 2"), "MISSING", days(90))]))
    ts = int(now.timestamp())
    index = {p: {"counter": 1, "timestamp": ts} for p in ("discFedAid_", "discPriAid_", "tmpChange_", "discFedAidCor_")}
    index["discPriAidCor_"] = {"counter": 0, "timestamp": ts}
    index["tmpChangeCor_"] = {"counter": 0, "timestamp": ts}
    (folder / "fileIndexNew.json").write_text(json.dumps(index))
    for f in folder.iterdir():                     # the files' dates are the run's (meta.json reports them)
        os.utime(f, (ts, ts))
