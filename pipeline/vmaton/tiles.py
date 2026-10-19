"""The aids as vector tiles (MVT, one layer "aton", points) in one PMTiles file, in pure Python
(mapbox-vector-tile + pmtiles; no GDAL or tippecanoe).

Which aids show at which zoom (minzoom), and the thinning below zoom 11:
  z6+   major lights (nominal range 10 NM or more, or listed as a major light)
  z8+   safe water marks and federal sea buoys (lighted, nominal range 6 NM or more)
  z9+   every other federal lighted buoy and light (minor lights, ranges, directional, articulated)
  z11+  everything (unlighted buoys, daybeacons, private aids, racons, virtual AIS, sound signals)
Below z11 the most important aid in each cell of cell_px screen pixels is kept (rank). An aid with a
discrepancy or temporary change is never thinned out: it shows from its own minzoom on.
"""
from __future__ import annotations

import gzip
import hashlib
import math
from io import BytesIO

import mapbox_vector_tile
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

LAYER = "aton"
EXTENT = 4096
TILE_PX = 512

SAFE_WATER = {"sphere-rw", "pillar-rw", "lb-rw"}


def minzoom(kind: str, sym: str, private: bool, rng, zcfg: dict, sea_range: float = 6) -> int:
    if kind == "major_light":
        return zcfg["major"]
    if sym in SAFE_WATER and not private:
        return zcfg["sea"]
    if kind == "lighted_buoy" and not private and rng is not None and float(rng) >= sea_range:
        return zcfg["sea"]
    if not private and kind in ("lighted_buoy", "light", "range_light", "directional_light", "articulated_light"):
        return zcfg["lighted"]
    return zcfg["all"]


def rank(kind: str, sym: str, private: bool, rng, status: str = "") -> int:
    """Who wins a thinning cell below z11, and who's drawn on top (symbol-sort-key): higher wins."""
    r = {"major_light": 90, "lighted_buoy": 60, "range_light": 55, "light": 50, "directional_light": 50,
         "articulated_light": 50, "racon": 40, "buoy": 25, "daybeacon": 20, "range_daybeacon": 20,
         "virtual_ais": 15, "sound_signal": 10}.get(kind, 5)
    if sym in SAFE_WATER:
        r = max(r, 80)
    if rng is not None:
        r += min(9, int(float(rng)))
    if private:
        r -= 15
    if status:
        r += {"missing": 300, "fault": 200, "temporary": 100}.get(status, 100)
    return r


def to_px(lon: float, lat: float, z: int) -> tuple[float, float]:
    """Web Mercator pixels at zoom z for 512-px tiles."""
    n = TILE_PX * 2 ** z
    lat = max(-85.05112878, min(85.05112878, lat))
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def thin(feats: list[dict], z: int, cell_px: int | None) -> list[dict]:
    """The features shown at zoom z: minzoom <= z; with cell_px, one per cell (highest rank), plus every feature
    with a status."""
    cands = [f for f in feats if f["minzoom"] <= z]
    if not cell_px:
        return cands
    cands.sort(key=lambda f: (not f["keep"], -f["props"]["rank"], f["props"]["id"]))
    taken, out = set(), []
    for f in cands:
        x, y = to_px(f["lon"], f["lat"], z)
        c = (int(x // cell_px), int(y // cell_px))
        if f["keep"]:
            out.append(f)                   # always shown, and doesn't take the cell from the others
        elif c not in taken:
            out.append(f)
            taken.add(c)
    return out


def clean_props(p: dict) -> dict:
    """Leave out empty values (smaller tiles); MVT has no null."""
    return {k: v for k, v in p.items() if v is not None and v != "" and not (isinstance(v, float) and math.isnan(v))}


def encode_tile(feats: list[tuple[int, int, int, dict]]) -> bytes:
    """[(fid, x, y, props)] in tile coordinates (0..4095, y down) -> MVT bytes."""
    layer = {"name": LAYER, "features": [
        {"geometry": f"POINT({x} {y})", "properties": clean_props(p), "id": fid} for fid, x, y, p in feats]}
    return mapbox_vector_tile.encode([layer], default_options={"extents": EXTENT, "y_coord_down": True})


def build(feats: list[dict], zmin: int, zmax: int, cell_px: dict) -> dict:
    """{(z, x, y): mvt bytes} for every tile with at least one aid."""
    tiles: dict = {}
    for i, f in enumerate(sorted(feats, key=lambda f: f["props"]["id"])):
        f["fid"] = i + 1
    for z in range(zmin, zmax + 1):
        per: dict = {}
        for f in thin(feats, z, cell_px.get(str(z)) or cell_px.get(z)):
            px, py = to_px(f["lon"], f["lat"], z)
            tx, ty = int(px // TILE_PX), int(py // TILE_PX)
            lx = min(EXTENT - 1, max(0, int(round((px - tx * TILE_PX) / TILE_PX * EXTENT))))
            ly = min(EXTENT - 1, max(0, int(round((py - ty * TILE_PX) / TILE_PX * EXTENT))))
            per.setdefault((tx, ty), []).append((f["fid"], lx, ly, f["props"]))
        for (tx, ty), fs in per.items():
            fs.sort(key=lambda t: (t[3].get("rank", 0), t[0]))     # drawn in rank order
            tiles[(z, tx, ty)] = encode_tile(fs)
    return tiles


def write_pmtiles(path, tiles: dict, metadata: dict, bounds, zmin: int, zmax: int) -> str:
    """Write the archive (tiles gzip-compressed) and return its version: the first 12 hex digits of a SHA-256
    over the tiles, so the same aids give the same version and a change of any aid a new one."""
    order = sorted(tiles.items(), key=lambda kv: zxy_to_tileid(*kv[0]))
    h = hashlib.sha256()
    blobs = []
    for (z, x, y), data in order:
        gz = gzip.compress(data, compresslevel=9, mtime=0)
        h.update(f"{z}/{x}/{y}:".encode())
        h.update(data)
        blobs.append((zxy_to_tileid(z, x, y), gz))
    version = h.hexdigest()[:12]
    w_, s_, e_, n_ = bounds
    header = {
        "tile_type": TileType.MVT, "tile_compression": Compression.GZIP, "min_zoom": zmin, "max_zoom": zmax,
        "min_lon_e7": int(w_ * 1e7), "min_lat_e7": int(s_ * 1e7), "max_lon_e7": int(e_ * 1e7), "max_lat_e7": int(n_ * 1e7),
        "center_zoom": zmin, "center_lon_e7": int((w_ + e_) / 2 * 1e7), "center_lat_e7": int((s_ + n_) / 2 * 1e7),
    }
    buf = BytesIO()
    wr = Writer(buf)
    for tid, gz in blobs:
        wr.write_tile(tid, gz)
    wr.finalize(header, {**metadata, "version": version})
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return version
