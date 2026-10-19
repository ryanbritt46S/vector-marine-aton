#!/usr/bin/env python3
"""Write the fixtures the app's, the preview's and the Worker's tests check themselves against:

  flutter/vm_aton/test/fixtures/words.json     status codes, light characteristics, dates and tap cards, with the
                                               answers of pipeline/vmaton/words.py (the reference)
  flutter/vm_aton/test/fixtures/site/          meta.json, style.json, icons/icons.json of a SAMPLE build
  worker/test/fixtures/                        the same SAMPLE build's aton.pmtiles, meta.json, style.json, icons

Run by bash check.sh; never edit the outputs by hand.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from vmaton import build as B  # noqa: E402
from vmaton import words as W  # noqa: E402
from vmaton.sample import write_sample  # noqa: E402
from vmaton.sources import DirSource  # noqa: E402

FX = ROOT / "flutter" / "vm_aton" / "test" / "fixtures"
WFX = ROOT / "worker" / "test" / "fixtures"
REAL = ROOT / "pipeline" / "tests" / "fixtures" / "real"
NOW = datetime(2026, 10, 19, 10, 20, tzinfo=timezone.utc)

EXTRA_CODES = ["MISSING", "OFF STA", "LT IMCH/STRUCT DMGD", "STRUCT DEST/TRUB", "Missing", "  lt  ext ", "Status Unreported",
               "Temp V-AIS: MMSI 993672514", "Missing 01 Dayboard (East side)", "", "SOMETHING NEW"]
EXTRA_CHARS = ["Fl G 4s", "Q R", "Mo (A) W", "Fl (2+1)R 6s", "Fl (2)W 5s", "F W R G", "FL Y 3s", "LFl W 10s", "VQ W",
               "Al Fl W R 10s", "Q (3) W 10s", "Iso G 2s", "Oc W 4s", "F R", "Fl W 7.5s", "STROBE", "Fl", "", "fl g 4 s",
               "Fl G 4s (2 lights)", "Fl Bu 4s"]


def build(src_dir: Path, out: Path):
    return B.run(DirSource(src_dir), out, B.load_config(min_aids_per_district=0), NOW, sample=src_dir.name == "sample")


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="aton-parity-"))
    try:
        sample_src = tmp / "sample"
        write_sample(sample_src, NOW)
        sample = build(sample_src, tmp / "site")
        real = build(REAL, tmp / "real")

        codes = sorted(W.STATUS_CODES) + EXTRA_CODES
        chars = sorted({f["props"]["char"] for f in real.features if f["props"]["char"]}) + EXTRA_CHARS
        cards = [f["props"] for f in sample.features]
        cards += [f["props"] for f in real.features if f["props"]["status"]]
        cards += [f["props"] for f in real.features if not f["props"]["status"]][::12]
        fx = {
            "_generated": "by pipeline/tools/make_parity.py from pipeline/vmaton/words.py; never edit",
            "codes": [{"raw": c, "product": p, "result": [list(x) for x in W.decode_codes(c, p)]}
                      for c in codes for p in ("disc", "tmp")],
            "join": [{"words": ws, "result": W.join_words(ws)} for ws in
                     (["Missing"], ["Structure destroyed", "Temporarily replaced by an unlighted buoy"],
                      ["Light out", "AIS not working"], ["Light out", "x"], [])],
            "lights": [{"char": c, "result": W.light_words(c)} for c in chars],
            "dates": [{"date": d, "result": W.fmt_date(d)} for d in ("2025-12-02", "2026-01-31", "2026-10-19", "", "bad")],
            "status_lines": [{"text": t, "since": s, "result": W.status_line(t, s)} for t, s in
                             (("Missing", "2025-12-02"), ("Light out; structure damaged", "2026-09-30"), ("Light out", ""), ("", "2025-12-02"))],
            "kinds": [{"kind": k, "result": W.kind_words(k)} for k in [*W.KIND_WORDS, "nope", ""]],
            "severity_words": W.SEVERITY_WORDS,
            "nums": [{"value": v, "result": W.num(v)} for v in (5, 2.5, 5.0, 12.25, 0, 17)],
            "stale": [{"meta": {"generated_at": "2026-10-19T10:20:00Z", "stale_after_hours": 72}, "now_ms": ms,
                       "result": W.stale_text({"generated_at": "2026-10-19T10:20:00Z", "stale_after_hours": 72}, ms)}
                      for ms in (1792405200000 + h * 3600000 for h in (0, 71, 73, 95, 97, 24 * 10))],
            "cards": [{"props": p, "data_date": "2026-10-19", "result": W.card(p, "2026-10-19")} for p in cards],
        }
        FX.mkdir(parents=True, exist_ok=True)
        (FX / "words.json").write_text(json.dumps(fx, indent=1, ensure_ascii=False) + "\n")

        site = FX / "site"
        shutil.rmtree(site, ignore_errors=True)
        (site / "icons").mkdir(parents=True)
        for f in ("meta.json", "style.json", "icons/icons.json"):
            shutil.copy(tmp / "site" / f, site / f)

        shutil.rmtree(WFX, ignore_errors=True)
        (WFX / "icons").mkdir(parents=True)
        for f in ("aton.pmtiles", "meta.json", "style.json", "icons/icons.json", "icons/lb-g@2x.png", "icons/badge-missing.png"):
            shutil.copy(tmp / "site" / f, WFX / f)
        print(f"wrote {(FX / 'words.json').relative_to(ROOT)}: {len(fx['codes'])} codes, {len(fx['lights'])} lights, "
              f"{len(fx['cards'])} cards; {site.relative_to(ROOT)}; {WFX.relative_to(ROOT)} "
              f"(aton.pmtiles {(WFX / 'aton.pmtiles').stat().st_size // 1024} KB)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
