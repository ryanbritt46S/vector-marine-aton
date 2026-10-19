#!/usr/bin/env python3
"""Upload the build to the vm-aton R2 bucket: icons first, then aton.pmtiles and style.json, meta.json last.

  python3 pipeline/publish.py --src build/site              upload what uploads.json lists
  python3 pipeline/publish.py --src build/site --dry-run    show what would happen

Order matters: the app reads meta.json first and the tiles and icons it names, so meta.json goes up only when
everything else is there. The bucket holds one copy (the files are replaced, not versioned): the tile URLs carry
the tiles' version (?v=), so caches never mix two days' tiles.

R2 credentials (Cloudflare dashboard -> R2 -> Manage API tokens, Object Read & Write on vm-aton only):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_BUCKET (default vm-aton).
Refuses to publish sample data.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TYPES = {".png": "image/png", ".json": "application/json", ".pmtiles": "application/octet-stream"}
# icons may change design under the same name: a day; the Worker sets the caching it serves with
CACHE = {".png": "public, max-age=86400", ".json": "no-cache", ".pmtiles": "no-cache"}


def plan(src: Path) -> tuple[dict, list[tuple[str, Path]]]:
    meta = json.loads((src / "meta.json").read_text())
    up = json.loads((src / "uploads.json").read_text())
    if up.get("run") != meta["run"]:
        raise SystemExit("uploads.json is from another run; build again")
    files = [f for f in up["files"] if f != "meta.json"]
    missing = [f for f in files if not (src / f).exists()]
    if missing:
        raise SystemExit(f"missing files: {missing[:5]}")
    first = [f for f in files if f.startswith("icons/") and f != "icons/icons.json"]
    rest = [f for f in files if f not in first]
    return meta, [(f, src / f) for f in first + rest] + [("meta.json", src / "meta.json")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="build/site")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    src = Path(a.src)
    meta, ups = plan(src)
    if meta.get("sample"):
        print("Refusing to publish SAMPLE data. Build with real data first.", file=sys.stderr)
        return 2
    total = sum(p.stat().st_size for _, p in ups)
    print(f"run {meta['run']}: {len(ups)} files to upload, {total / 1e6:.1f} MB; tiles version {meta['tiles']['version']}")
    if a.dry_run:
        for k, p in ups[:8] + ([("...", None)] if len(ups) > 12 else []) + ups[-4:]:
            print(f"  {k}" + (f"  ({p.stat().st_size} bytes)" if p else ""))
        return 0
    acct, key_id, secret = (os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    bucket = os.environ.get("R2_BUCKET") or "vm-aton"
    if not (acct and key_id and secret):
        print("Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY.", file=sys.stderr)
        return 2
    import boto3
    s3 = boto3.client("s3", endpoint_url=f"https://{acct}.r2.cloudflarestorage.com", aws_access_key_id=key_id,
                      aws_secret_access_key=secret, region_name="auto")
    for k, p in ups:
        s3.upload_file(str(p), bucket, k, ExtraArgs={"ContentType": TYPES.get(p.suffix, "application/octet-stream"),
                                                    "CacheControl": CACHE.get(p.suffix, "no-cache")})
    c = meta["counts"]
    print(f"uploaded; meta.json now says {c['aids']} aids, {sum(c['by_status'].values())} with a status, "
          f"data of {meta['data_date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
