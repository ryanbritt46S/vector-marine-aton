"""Zooms, thinning, and the tiles themselves."""
import gzip

import mapbox_vector_tile
from pmtiles.reader import MmapSource, Reader

from vmaton import tiles as T

Z = {"min": 6, "max": 14, "major": 6, "sea": 8, "lighted": 9, "all": 11}


def test_minzoom_rules():
    assert T.minzoom("major_light", "light-major", False, 14, Z) == 6
    assert T.minzoom("lighted_buoy", "lb-rw", False, 6, Z) == 8              # safe water
    assert T.minzoom("buoy", "sphere-rw", False, None, Z) == 8
    assert T.minzoom("lighted_buoy", "lb-g", False, 6, Z) == 8               # sea buoy
    assert T.minzoom("lighted_buoy", "lb-g", False, 4, Z) == 9
    assert T.minzoom("light", "light-g", False, 4, Z) == 9
    assert T.minzoom("range_light", "range-front", False, None, Z) == 9
    assert T.minzoom("light", "light-g", True, 4, Z) == 11                   # private
    assert T.minzoom("lighted_buoy", "lb-g", True, 6, Z) == 11
    assert T.minzoom("buoy", "can-g", False, None, Z) == 11
    assert T.minzoom("daybeacon", "db-sq-g", False, None, Z) == 11
    assert T.minzoom("virtual_ais", "vais", False, None, Z) == 11


def test_rank_order():
    assert T.rank("major_light", "light-major", False, 17) > T.rank("lighted_buoy", "lb-rw", False, 6) \
        > T.rank("lighted_buoy", "lb-g", False, 4) > T.rank("light", "light-g", False, 4) \
        > T.rank("buoy", "can-g", False, None) > T.rank("daybeacon", "db-sq-g", False, None)
    assert T.rank("daybeacon", "db-sq-g", False, None, "temporary") > T.rank("major_light", "light-major", False, 20)
    assert T.rank("buoy", "can-g", False, None, "missing") > T.rank("buoy", "can-g", False, None, "fault")


def feat(i, lon, lat, rank, mz=9, keep=False):
    return {"lon": lon, "lat": lat, "minzoom": mz, "keep": keep, "props": {"id": f"5-{i}", "rank": rank}}


def test_thinning_keeps_the_best_per_cell_and_every_status():
    fs = [feat(1, -74.0, 39.0, 60), feat(2, -74.0001, 39.0001, 70), feat(3, -74.0002, 39.0, 20, keep=True),
          feat(4, -73.5, 39.0, 10), feat(5, -74.0, 39.0, 99, mz=11)]
    got = {f["props"]["id"] for f in T.thin(fs, 9, 24)}
    assert got == {"5-2", "5-3", "5-4"}                 # 2 beats 1 in their cell, 3 has a status, 5 not yet
    assert {f["props"]["id"] for f in T.thin(fs, 11, None)} == {"5-1", "5-2", "5-3", "5-4", "5-5"}


def test_tile_round_trip(tmp_path):
    p = {"id": "5-900", "name": "Barnegat Inlet Lighted Buoy 1", "sym": "lb-g", "range": 5, "height": None,
         "private": False, "status": "", "rank": 65, "char": "Fl G 2.5s", "district": 5}
    fs = [{"lon": -74.07679, "lat": 39.74692, "minzoom": 9, "keep": False, "props": p}]
    tiles = T.build(fs, 6, 14, {"8": 24, "9": 24, "10": 20})
    assert sorted(z for z, _, _ in tiles) == [9, 10, 11, 12, 13, 14]
    v = T.write_pmtiles(tmp_path / "t.pmtiles", tiles, {"name": "t"}, (-74.08, 39.74, -74.07, 39.75), 6, 14)
    assert len(v) == 12
    assert T.write_pmtiles(tmp_path / "u.pmtiles", tiles, {"name": "t"}, (-74.08, 39.74, -74.07, 39.75), 6, 14) == v
    with open(tmp_path / "t.pmtiles", "rb") as f:
        r = Reader(MmapSource(f))
        assert r.metadata()["version"] == v
        x, y = (int(c // 512) for c in T.to_px(-74.07679, 39.74692, 14))
        data = gzip.decompress(r.get(14, x, y))
    layer = mapbox_vector_tile.decode(data, default_options={"y_coord_down": True})["aton"]
    assert layer["extent"] == 4096
    (f0,) = layer["features"]
    assert f0["properties"] == {"id": "5-900", "name": "Barnegat Inlet Lighted Buoy 1", "sym": "lb-g", "range": 5,
                                "private": False, "rank": 65, "char": "Fl G 2.5s", "district": 5}
    gx, gy = f0["geometry"]["coordinates"]
    px, py = T.to_px(-74.07679, 39.74692, 14)
    assert abs(x * 512 + gx / 8 - px) < 0.2 and abs(y * 512 + gy / 8 - py) < 0.2
