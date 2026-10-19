#!/usr/bin/env python3
"""Buoys & lights job: the Coast Guard's Light List and Local Notice to Mariners -> tiles, icons, style, meta.

  python3 pipeline/run_aton.py --out build/site                    download from NAVCEN (no account needed)
  python3 pipeline/run_aton.py --out build/site --raw DIR          the same files from a folder
  python3 pipeline/run_aton.py --out build/site-sample --sample    made-up data (labelled SAMPLE), no network

The last published meta.json is read from <out>/meta.json if it's there (local runs), else from R2 when the R2_*
variables are set (GitHub Actions). If a district now has far fewer aids than it had (under 80%), nothing is
written for publishing: a short download must never replace the whole coast with half of it.
Exit codes: 0 done, 2 bad input or refused, 3 refused for shrinking.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time as _time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vmaton import build as B  # noqa: E402
from vmaton.sources import DirSource, HttpSource, SourceError  # noqa: E402


def r2_client():
    if not all(os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")):
        return None
    import boto3
    return boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def previous_meta(out: Path, sample: bool) -> dict | None:
    f = out / "meta.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except ValueError:
            return None
    s3 = None if sample else r2_client()
    if s3 is None:
        return None
    try:
        return json.loads(s3.get_object(Bucket=os.environ.get("R2_BUCKET") or "vm-aton", Key="meta.json")["Body"].read())
    except Exception:  # noqa: BLE001 - first publish
        return None


def shrunk(prev: dict | None, meta: dict, ratio: float) -> list[str]:
    """Districts with far fewer aids than the last published meta."""
    if not prev or prev.get("sample"):
        return []
    out = []
    for d, info in (prev.get("districts") or {}).items():
        before = int(info.get("aids") or 0)
        after = int(((meta.get("districts") or {}).get(d) or {}).get("aids") or 0)
        if before >= 100 and after < ratio * before:
            out.append(f"district {d}: {after} aids, was {before}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="build/site")
    ap.add_argument("--raw", help="read the NAVCEN files from this folder instead of downloading them")
    ap.add_argument("--sample", action="store_true", help="made-up data (labelled SAMPLE), no network")
    ap.add_argument("--now", help="the run's time, e.g. 2026-10-19T10:20:00Z (default: now)")
    ap.add_argument("--allow-shrink", action="store_true", help="write it even if a district has far fewer aids")
    ap.add_argument("--min-aids", type=int, help="fewest aids per district accepted (default: config)")
    a = ap.parse_args(argv)

    cfg = B.load_config()
    now = datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else datetime.now(timezone.utc)
    out = Path(a.out)
    t0 = _time.time()
    tmp = None
    try:
        if a.sample:
            from vmaton.sample import write_sample
            tmp = Path(tempfile.mkdtemp(prefix="aton-sample-"))
            write_sample(tmp, now)
            source = DirSource(tmp)
            cfg["min_aids_per_district"] = 0
            print("SAMPLE aids (made up, for testing only)")
        elif a.raw:
            source = DirSource(Path(a.raw))
        else:
            source = HttpSource(cfg["base_url"])
        if a.min_aids is not None:
            cfg["min_aids_per_district"] = a.min_aids
        prev = previous_meta(out, a.sample)
        if prev and not prev.get("sample") and a.sample:
            print("refusing to write SAMPLE data over a real build in this folder; use another --out", file=sys.stderr)
            return 2
        res = B.run(source, out, cfg, now, sample=a.sample)
    except (SourceError, B.BuildError) as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 2
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    meta = res.meta
    bad = shrunk(prev, meta, float(cfg["shrink_ratio"]))
    if bad and not a.allow_shrink:
        (out / "meta.json").replace(out / "meta.rejected.json")
        if prev:
            (out / "meta.json").write_text(json.dumps(prev, indent=1) + "\n")
        (out / "uploads.json").unlink(missing_ok=True)
        print("REFUSED: " + "; ".join(bad) + f". Nothing to publish (the new meta is in {out / 'meta.rejected.json'}). "
              "If the drop is real, run again with --allow-shrink.", file=sys.stderr)
        return 3
    c = meta["counts"]
    n = c["notices"]
    print(f"{c['aids']} aids ({c['listed']} in the Light List, {c['unlisted']} only in a notice) in "
          f"{_time.time() - t0:.0f} s; data of {meta['data_date']}")
    for d, info in meta["districts"].items():
        print(f"  district {d}: {info['aids']} aids in {info['light_list_parts']} Light List parts")
    print(f"  notices: {n['in_area']} in districts {', '.join(meta['districts'])} ({n['nationwide']} nationwide): "
          f"{n['matched_by_number']} matched by number, {n['matched_by_name']} by name, {n['unmatched']} unmatched "
          f"(shown at the notice's position); {n['corrected_in_area']} corrected items not shown")
    print(f"  status: {c['by_status']}")
    print(f"  by kind: {c['by_kind']}")
    t = meta["tiles"]
    print(f"  aton.pmtiles {t['bytes'] / 1e6:.1f} MB, {t['tiles']} tiles z{t['minzoom']}-{t['maxzoom']}, "
          f"version {t['version']}; {meta['icons']['count']} icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
