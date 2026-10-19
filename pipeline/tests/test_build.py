"""The whole job on a small REAL fixture (tests/fixtures/real: the Coast Guard's files of Oct 19, 2026, cut to
NJ's inlets, the NY harbor entrance and Miami by tools/make_fixture.py), on SAMPLE data, and the refusals."""
import gzip
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import mapbox_vector_tile
import pytest
from pmtiles.reader import MmapSource, Reader

import publish
import run_aton
from vmaton import build as B
from vmaton import tiles as T
from vmaton.sources import DirSource

FX = Path(__file__).parent / "fixtures" / "real"
NOW = datetime(2026, 10, 19, 10, 20, tzinfo=timezone.utc)


def cfg(**over):
    return B.load_config(min_aids_per_district=0, **over)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    res = B.run(DirSource(FX), out, cfg(), NOW)
    return out, res


def features_at(out: Path, z: int, lon: float, lat: float) -> list[dict]:
    x, y = (int(c // 512) for c in T.to_px(lon, lat, z))
    with open(out / "aton.pmtiles", "rb") as f:
        data = Reader(MmapSource(f)).get(z, x, y)
    if not data:
        return []
    layer = mapbox_vector_tile.decode(gzip.decompress(data), default_options={"y_coord_down": True}).get("aton")
    out_ = []
    for ft in (layer or {}).get("features", []):
        gx, gy = ft["geometry"]["coordinates"]
        out_.append({**ft["properties"], "_px": (x * 512 + gx / 8, y * 512 + gy / 8)})
    return out_


def find(out, z, lon, lat, name):
    hits = [f for f in features_at(out, z, lon, lat) if f["name"] == name]
    assert len(hits) == 1, f"{name} at z{z}: {len(hits)}"
    return hits[0]


def test_barnegat_inlet_lighted_buoy_1_in_its_tile(site):
    out, _ = site
    f = find(out, 14, -74.07679, 39.74692, "Barnegat Inlet Lighted Buoy 1")
    assert (f["sym"], f["kind"], f["char"], f["range"], f["llnr"], f["district"]) == ("lb-g", "lighted_buoy", "Fl G 2.5s", 5, "900", 5)
    assert f["structure"] == "Green." and f["remark"] == "Position of buoy frequently shifts with changing conditions."
    assert f["waterway"] == "Barnegat Inlet" and f["private"] is False and f["label"] == 'Fl G 2.5s\n"1"'
    px, py = T.to_px(-74.07679, 39.74692, 14)
    assert abs(f["_px"][0] - px) < 0.2 and abs(f["_px"][1] - py) < 0.2
    assert "status" not in f
    # a lighted buoy shows from z9, not before
    assert find(out, 9, -74.07679, 39.74692, "Barnegat Inlet Lighted Buoy 1")
    assert not [f for f in features_at(out, 8, -74.07679, 39.74692) if f["name"] == "Barnegat Inlet Lighted Buoy 1"]


def test_little_egg_missing_buoy_and_manasquan(site):
    out, _ = site
    f = find(out, 14, -74.28552, 39.47039, "Little Egg Inlet Lighted Buoy 2")
    assert (f["status"], f["status_text"], f["status_since"], f["status_raw"]) == ("missing", "Missing", "2025-12-02", "MISSING")
    assert f["rank"] > 300
    m = find(out, 14, -74.01339, 40.09229, "Manasquan Inlet Lighted Buoy 2M")
    assert (m["sym"], m["char"], m["district"], m["label"]) == ("lb-r", "Fl R 4s", 5, 'Fl R 4s\n"2M"')
    rw = find(out, 8, -74.06882, 39.73864, "Barnegat Inlet Outer Lighted Whistle Buoy BI")        # safe water: z8
    assert rw["sym"] == "lb-rw"


def test_meta_counts_and_files(site):
    out, res = site
    meta = json.loads((out / "meta.json").read_text())
    assert meta == res.meta and meta["sample"] is False and meta["version"] == 1
    assert {d: v["aids"] for d, v in meta["districts"].items()} == {"1": 90, "5": 230, "7": 45}
    n = meta["counts"]["notices"]
    assert n["in_area"] == n["matched_by_number"] + n["matched_by_name"] + n["unmatched"]
    assert n["in_area"] < n["nationwide"]                                   # the district 8/9 items are left out
    assert meta["counts"]["aids"] == meta["counts"]["listed"] + meta["counts"]["unlisted"] == 365 + meta["counts"]["unlisted"]
    assert meta["counts"]["by_status"]["missing"] >= 3
    assert meta["data_date"] == "2026-10-19" and meta["notices_date"] == "2026-10-19"
    assert meta["tiles"]["version"] and meta["tiles"]["minzoom"] == 6 and meta["tiles"]["maxzoom"] == 14
    icons = json.loads((out / "icons" / "icons.json").read_text())
    assert icons["version"] == meta["icons"]["version"]
    for sym in set(meta["counts"]["by_sym"]) | {"badge-missing", "badge-fault", "badge-temporary"}:
        for r in ("1", "2", "3"):
            assert (out / icons["icons"][sym]["files"][r]).is_file()
    up = json.loads((out / "uploads.json").read_text())
    assert up["run"] == meta["run"] and up["files"][-1] == "meta.json" and "aton.pmtiles" in up["files"]
    assert all((out / f).is_file() for f in up["files"])


def test_style(site):
    out, _ = site
    st = json.loads((out / "style.json").read_text())
    assert st["anchor"] == "vm-overlays" and st["sources"]["vm-aton"]["url"] == "{base}/aton.json"
    ids = [l["id"] for l in st["layers"]]
    assert ids == ["vm-aton-status", "vm-aton-symbols", "vm-aton-labels"]
    labels = st["layers"][2]
    assert labels["minzoom"] == 14 and labels["layout"]["text-field"] == ["get", "label"]
    assert all(l["source-layer"] == "aton" for l in st["layers"])
    assert [l["source"] for l in st["layers"]] == ["vm-aton", "vm-aton", "vm-aton-text"]      # labels on their own
    assert st["sources"]["vm-aton-text"]["url"] == "{base}/aton.json"


def test_unmatched_notice_is_shown(tmp_path):
    src = tmp_path / "raw"
    shutil.copytree(FX, src)
    fc = json.loads((src / "discFedAid_1.geojson").read_text())
    fc["features"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-74.1, 39.6]},
                           "properties": {"ATU": 5, "LLNR": None, "NAME": "Made Up Hazard Daybeacon A", "DISCREP_STATUS": "LT EXT",
                                          "CREATE_DATE": 1790000000000, "DESCRIPTION_TYPE": "DBN", "COLOR": "WO",
                                          "AID_TYPE": "PA", "LNM_UID": 4242, "DECIMAL_LONGITUDE": -74.1, "DECIMAL_LATITUDE": 39.6}})
    (src / "discFedAid_1.geojson").write_text(json.dumps(fc))
    B.run(DirSource(src), tmp_path / "site", cfg(), NOW)
    f = find(tmp_path / "site", 14, -74.1, 39.6, "Made Up Hazard Daybeacon A")
    assert (f["id"], f["listed"], f["sym"], f["status"], f["status_text"]) == ("5-n4242", False, "db-reg", "fault", "Light out")


def test_light_list_parts_are_probed_and_missing_parts_fail(tmp_path):
    src = tmp_path / "raw"
    shutil.copytree(FX, src)
    lines = (src / "lightListD05_1.csv").read_text().splitlines(keepends=True)
    (src / "lightListD05_1.csv").write_text("".join(lines[:100]))
    (src / "lightListD05_2.csv").write_text(lines[0] + "".join(lines[100:]))
    res = B.run(DirSource(src), tmp_path / "a", cfg(), NOW)
    assert res.meta["districts"]["5"] == {"name": res.meta["districts"]["5"]["name"], "aids": 230, "light_list_parts": 2}
    (src / "lightListD07_1.csv").unlink()
    with pytest.raises(B.BuildError, match="no Light List for district 7"):
        B.run(DirSource(src), tmp_path / "b", cfg(), NOW)
    with pytest.raises(B.BuildError, match="district 1: only 90 aids"):
        B.run(DirSource(FX), tmp_path / "c", B.load_config(min_aids_per_district=231), NOW)
    idx = json.loads((FX / "fileIndexNew.json").read_text())
    idx["tmpChange_"]["counter"] = 2
    shutil.copytree(FX, tmp_path / "raw2")
    (tmp_path / "raw2" / "fileIndexNew.json").write_text(json.dumps(idx))
    with pytest.raises(B.BuildError, match="tmpChange_2.geojson"):
        B.run(DirSource(tmp_path / "raw2"), tmp_path / "d", cfg(), NOW)


def test_cli_shrink_refusal_and_sample(tmp_path, capsys):
    out = tmp_path / "site"
    args = ["--out", str(out), "--raw", str(FX), "--min-aids", "0", "--now", "2026-10-19T10:20:00Z"]
    assert run_aton.main(args) == 0
    meta = json.loads((out / "meta.json").read_text())
    meta["districts"]["5"]["aids"] = 1000                                  # as if the last publish had 1000
    (out / "meta.json").write_text(json.dumps(meta))
    assert run_aton.main(args) == 3
    assert "REFUSED: district 5: 230 aids, was 1000" in capsys.readouterr().err
    assert json.loads((out / "meta.json").read_text())["districts"]["5"]["aids"] == 1000      # kept the last one
    assert (out / "meta.rejected.json").exists() and not (out / "uploads.json").exists()
    assert run_aton.main(args + ["--allow-shrink"]) == 0
    # sample: never over a real build, labelled, refused by publish
    assert run_aton.main(["--out", str(out), "--sample"]) == 2
    s = tmp_path / "sample"
    assert run_aton.main(["--out", str(s), "--sample", "--now", "2026-10-19T10:20:00Z"]) == 0
    sm = json.loads((s / "meta.json").read_text())
    assert sm["sample"] is True and sm["counts"]["by_status"] == {"missing": 3, "fault": 5, "temporary": 2}
    assert sm["counts"]["unlisted"] == 1 and sm["counts"]["notices"]["matched_by_name"] == 1
    assert publish.main(["--src", str(s), "--dry-run"]) == 2
    assert publish.main(["--src", str(out), "--dry-run"]) == 0


def test_publish_order(site):
    out, _ = site
    meta, ups = publish.plan(out)
    keys = [k for k, _ in ups]
    assert keys[-1] == "meta.json" and keys[-2] == "style.json"
    assert keys.index("icons/icons.json") > max(i for i, k in enumerate(keys) if k.endswith(".png"))
    assert keys.index("aton.pmtiles") < keys.index("meta.json")
