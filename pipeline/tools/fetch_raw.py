#!/usr/bin/env python3
"""Copy one day's NAVCEN files from the vm-aton bucket (raw/<YYYY-MM-DD>/, written by the Worker's daily mirror,
worker/src/mirror.js) into a folder, for  run_aton.py --raw <folder>.

  python3 pipeline/tools/fetch_raw.py --out raw                  today (UTC)
  python3 pipeline/tools/fetch_raw.py --out raw --date 2026-10-20

Refuses a day the mirror didn't finish (no _complete.json) and checks every file it lists arrived at its size.
Each file's modification time is set to the Coast Guard's Last-Modified (kept by the mirror), because the build
dates the Light List from it (build.py: Last-Modified when downloading, the file's time when reading a folder).

R2 credentials as for publish.py: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET (default vm-aton).
Exit codes: 0 done, 2 not complete / missing or short files / no credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

COMPLETE = "_complete.json"


def r2_client():
    acct, key_id, secret = (os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    if not (acct and key_id and secret):
        return None
    import boto3
    return boto3.client("s3", endpoint_url=f"https://{acct}.r2.cloudflarestorage.com", aws_access_key_id=key_id,
                        aws_secret_access_key=secret, region_name="auto")


def _meta(head: dict, key: str) -> str:
    """User metadata, whatever case the S3 API hands the name back in."""
    for k, v in (head.get("Metadata") or {}).items():
        if k.lower() == key.lower():
            return v
    return ""


def fetch(s3, bucket: str, day: str, out: Path) -> dict:
    """Download raw/<day>/ into out. Returns the _complete.json record. Raises SystemExit(2) when not usable."""
    prefix = f"raw/{day}/"
    try:
        done = json.loads(s3.get_object(Bucket=bucket, Key=prefix + COMPLETE)["Body"].read())
    except Exception:  # noqa: BLE001 - not there (or unreadable): the mirror didn't finish that day
        print(f"FAILED: no complete NAVCEN download for {day} ({prefix}{COMPLETE} not found). "
              "Check the vm-aton Worker's cron runs (Workers & Pages -> vm-aton -> Logs).", file=sys.stderr)
        raise SystemExit(2)
    out.mkdir(parents=True, exist_ok=True)
    for f in done.get("files") or []:
        name = f["name"]
        if "/" in name or name.startswith("."):
            print(f"FAILED: unexpected file name in {COMPLETE}: {name!r}", file=sys.stderr)
            raise SystemExit(2)
        dest = out / name
        try:
            s3.download_file(bucket, prefix + name, str(dest))
            head = s3.head_object(Bucket=bucket, Key=prefix + name)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED: {prefix}{name}: {e}", file=sys.stderr)
            raise SystemExit(2)
        if dest.stat().st_size != int(f.get("bytes", -1)):
            print(f"FAILED: {prefix}{name} is {dest.stat().st_size} bytes, the mirror wrote {f.get('bytes')}",
                  file=sys.stderr)
            raise SystemExit(2)
        lm = f.get("lastModified") or _meta(head, "lastModified")
        if lm:
            try:
                t = parsedate_to_datetime(lm).timestamp()
                os.utime(dest, (t, t))
            except (TypeError, ValueError):
                pass                      # no usable date: the build falls back to the file's own time
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", default="", help="YYYY-MM-DD (default: today, UTC)")
    a = ap.parse_args(argv)
    day = a.date or datetime.now(timezone.utc).date().isoformat()
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        print(f"FAILED: --date must be YYYY-MM-DD, not {day!r}", file=sys.stderr)
        return 2
    s3 = r2_client()
    if s3 is None:
        print("Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY.", file=sys.stderr)
        return 2
    try:
        done = fetch(s3, os.environ.get("R2_BUCKET") or "vm-aton", day, Path(a.out))
    except SystemExit as e:
        return int(e.code or 2)
    parts = done.get("light_list_parts") or {}
    print(f"raw/{day}: {len(done.get('files') or [])} files (mirrored {done.get('at')}); Light List parts "
          + ", ".join(f"district {d}: {n}" for d, n in parts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
