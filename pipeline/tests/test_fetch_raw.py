"""tools/fetch_raw.py: one day's NAVCEN copy from the bucket (written by worker/src/mirror.js) -> a folder for
run_aton.py --raw. A stand-in for the S3 client; no network."""
import io
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fetch_raw  # noqa: E402
from vmaton import build as B  # noqa: E402
from vmaton.sources import DirSource  # noqa: E402

FX = Path(__file__).parent / "fixtures" / "real"
DAY = "2026-10-21"
LM = "Mon, 19 Oct 2026 06:00:00 GMT"


class S3:
    """get_object / download_file / head_object over a dict of key -> (bytes, metadata)."""

    def __init__(self, objs):
        self.objs = objs

    def get_object(self, Bucket, Key):
        if Key not in self.objs:
            raise KeyError(Key)
        return {"Body": io.BytesIO(self.objs[Key][0])}

    def download_file(self, bucket, key, dest):
        if key not in self.objs:
            raise KeyError(key)
        Path(dest).write_bytes(self.objs[key][0])

    def head_object(self, Bucket, Key):
        return {"Metadata": self.objs[Key][1]}


def mirrored(**drop):
    """The bucket as the Worker leaves it after a complete day (the real fixture files)."""
    objs, files = {}, []
    for f in sorted(FX.iterdir()):
        b = f.read_bytes()
        objs[f"raw/{DAY}/{f.name}"] = (b, {"lastmodified": LM})        # the S3 API hands names back lower-case
        files.append({"name": f.name, "bytes": len(b), "lastModified": LM})
    done = {"at": f"{DAY}T10:21:00Z", "dir": f"raw/{DAY}", "light_list_parts": {"1": 1, "5": 1, "7": 1}, "files": files}
    objs[f"raw/{DAY}/_complete.json"] = (json.dumps(done).encode(), {})
    for k in drop:
        objs.pop(f"raw/{DAY}/{k.replace('__', '.')}", None)
    return objs


def test_complete_day_is_copied_with_the_coast_guards_dates_and_builds(tmp_path):
    out = tmp_path / "raw"
    done = fetch_raw.fetch(S3(mirrored()), "vm-aton", DAY, out)
    assert len(done["files"]) == len(list(FX.iterdir()))
    for f in FX.iterdir():
        assert (out / f.name).read_bytes() == f.read_bytes()
        assert datetime.fromtimestamp((out / f.name).stat().st_mtime, timezone.utc) == \
            datetime(2026, 10, 19, 6, 0, tzinfo=timezone.utc)
    # the build reads it like a download: the Light List dated by the Coast Guard, not by the copy
    res = B.run(DirSource(out), tmp_path / "site", B.load_config(min_aids_per_district=0),
                datetime(2026, 10, 21, 10, 50, tzinfo=timezone.utc))
    assert res.meta["light_list_date"] == "2026-10-19"
    assert res.meta["counts"]["aids"] > 0


def test_no_complete_marker_refuses(tmp_path, capsys):
    objs = mirrored()
    objs.pop(f"raw/{DAY}/_complete.json")
    with pytest.raises(SystemExit) as e:
        fetch_raw.fetch(S3(objs), "vm-aton", DAY, tmp_path / "raw")
    assert e.value.code == 2
    assert "no complete NAVCEN download for 2026-10-21" in capsys.readouterr().err


def test_missing_or_short_file_refuses(tmp_path, capsys):
    with pytest.raises(SystemExit):
        fetch_raw.fetch(S3(mirrored(lightListD05_1__csv=1)), "vm-aton", DAY, tmp_path / "a")
    assert "lightListD05_1.csv" in capsys.readouterr().err
    objs = mirrored()
    b, m = objs[f"raw/{DAY}/tmpChange_1.geojson"]
    objs[f"raw/{DAY}/tmpChange_1.geojson"] = (b[:-10], m)
    with pytest.raises(SystemExit):
        fetch_raw.fetch(S3(objs), "vm-aton", DAY, tmp_path / "b")
    assert "the mirror wrote" in capsys.readouterr().err


def test_cli_needs_credentials_and_a_proper_date(monkeypatch, tmp_path):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert fetch_raw.main(["--out", str(tmp_path / "x")]) == 2
    assert fetch_raw.main(["--out", str(tmp_path / "x"), "--date", "21-10-2026"]) == 2
