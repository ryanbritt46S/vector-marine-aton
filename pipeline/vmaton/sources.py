"""Where the Coast Guard's files come from: NAVCEN's "MSI Products" data files over HTTPS (the daily job), or a
folder with copies of them (--raw, tests). Both answer get(name) -> bytes, or None when the file isn't there.

The files (https://navcen.uscg.gov/sites/default/files/msi/<file>, public, no key):
  fileIndexNew.json                  how many numbered parts each notice product has right now
  lightList{DD}_{n}.csv              the Light List of district DD, in parts n = 1, 2, ... (not in the index: probed)
  discFedAid_{n}.geojson             current discrepancies of federal aids (nationwide)
  discPriAid_{n}.geojson             current discrepancies of private aids (nationwide)
  tmpChange_{n}.geojson              current temporary changes (nationwide)
  *Cor_{n}.geojson                   corrected / closed items (only counted)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


class SourceError(RuntimeError):
    pass


@dataclass
class Fetched:
    name: str
    bytes: int
    modified: datetime | None


@dataclass
class DirSource:
    """Copies of the files in a folder (--raw, tests)."""
    path: Path
    fetched: list[Fetched] = field(default_factory=list)

    def __post_init__(self):
        self.path = Path(self.path)
        if not self.path.is_dir():
            raise SourceError(f"no such folder: {self.path}")

    def describe(self) -> str:
        return f"folder {self.path}"

    def get(self, name: str) -> bytes | None:
        f = self.path / name
        if not f.is_file():
            return None
        b = f.read_bytes()
        self.fetched.append(Fetched(name, len(b), datetime.fromtimestamp(f.stat().st_mtime, timezone.utc)))
        return b


@dataclass
class HttpSource:
    """NAVCEN over HTTPS. A 404 is "not there" (that's how the Light List parts are counted); other failures are
    tried again after 2, 6 and 18 s, then the run fails (and publishes nothing)."""
    base_url: str
    timeout: float = 90
    waits: tuple = (2, 6, 18)
    fetched: list[Fetched] = field(default_factory=list)
    session: object = None

    def describe(self) -> str:
        return self.base_url

    def _session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.headers["User-Agent"] = "VectorMarine-aton/1.0 (+https://vectormarine.us; daily, one copy per file)"
        return self.session

    def get(self, name: str) -> bytes | None:
        url = self.base_url.rstrip("/") + "/" + name
        last = None
        for wait in (*self.waits, None):
            try:
                r = self._session().get(url, timeout=self.timeout)
                if r.status_code == 404:
                    return None
                if r.status_code == 200:
                    mod = None
                    if r.headers.get("Last-Modified"):
                        try:
                            mod = parsedate_to_datetime(r.headers["Last-Modified"])
                        except (TypeError, ValueError):
                            mod = None
                    self.fetched.append(Fetched(name, len(r.content), mod))
                    return r.content
                last = f"HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001 - network trouble: try again
                last = f"{type(e).__name__}: {e}"
            if wait is None:
                break
            time.sleep(wait)
        raise SourceError(f"{url}: {last}")
