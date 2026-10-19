"""Downloads from NAVCEN (with a stand-in session: no network in tests)."""
import pytest

from vmaton.build import read_light_lists
from vmaton.sources import HttpSource, SourceError


class Resp:
    def __init__(self, status, content=b"", headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}


class Session:
    def __init__(self, answers):
        self.answers, self.asked, self.headers = answers, [], {}

    def get(self, url, timeout=None):
        self.asked.append(url)
        a = self.answers.get(url.rsplit("/", 1)[-1], [Resp(404)])
        return a.pop(0) if len(a) > 1 else a[0]


def src(answers):
    return HttpSource("https://navcen.example/msi/", waits=(0, 0, 0), session=Session(answers))


def test_404_is_not_there_and_retries_then_fails():
    s = src({"a.csv": [Resp(503), Resp(200, b"x", {"Last-Modified": "Mon, 19 Oct 2026 06:00:00 GMT"})]})
    assert s.get("a.csv") == b"x"
    assert s.fetched[0].name == "a.csv" and s.fetched[0].modified.isoformat() == "2026-10-19T06:00:00+00:00"
    assert s.get("b.csv") is None
    assert s.session.asked == ["https://navcen.example/msi/a.csv"] * 2 + ["https://navcen.example/msi/b.csv"]
    bad = src({"c.csv": [Resp(500)]})
    with pytest.raises(SourceError, match="HTTP 500"):
        bad.get("c.csv")
    assert len(bad.session.asked) == 4                     # tried 4 times


def test_light_list_parts_probed_until_a_404():
    head = b"ATU,LIGHT_LIST_NUMBER,NAME,DESCRIPTION_TYPE,DECIMAL_LONGITUDE,DECIMAL_LATITUDE\n"
    row = lambda n: head + f"5,{n},Buoy {n},ULB,-74.0,39.{n}\n".encode()  # noqa: E731
    s = src({"lightListD05_1.csv": [Resp(200, row(1))], "lightListD05_2.csv": [Resp(200, row(2))]})
    parts, aids, skipped = read_light_lists(s, [5], 40)
    assert parts == {5: 2} and [a.llnr for a in aids] == ["1", "2"] and skipped == 0
    assert s.session.asked[-1].endswith("lightListD05_3.csv")
