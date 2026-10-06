import http.client
import os
import re
import socket
import subprocess
import sys
import time

import numpy as np
import pytest
from starlette.testclient import TestClient

from bachata.analysis import ANALYSIS_VERSION
from bachata.server import WEB, create_app
from bachata.store import RATE

ID_A, ID_B = "a" * 32, "b" * 32
OWN_PAGE = {"Origin": "http://127.0.0.1", "Sec-Fetch-Site": "same-origin"}

# Written out here, and not read from the program: a header taken out of the program
# must make these tests fail.
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def analyse(samples, rate):
    """Stands for the real analysis. The first sample says which song it was given."""
    if samples[0, 0] == 13:
        raise RuntimeError("this song cannot be analysed")
    return {"beats": [1.0, 1.5, float(samples[0, 0])], "bpm": [120.0, 120.0, 120.0], "bar": [1, 2, 3], "count": [1, 2, 3]}


def a_song(seconds=20, first=1):
    samples = np.random.default_rng(first).integers(-3000, 3000, size=(RATE * seconds, 2), dtype="<i2")
    samples[0, 0] = first
    return samples


class Program:
    """The application on a data folder, with no queue running: the tests run it by hand."""

    def __init__(self, data, **settings):
        self.app = create_app(data, **{"analyse": analyse, **settings})
        self.client = TestClient(self.app, base_url="http://127.0.0.1")
        self.get = self.client.get

    def put(self, song_id=ID_A, samples=None, headers=OWN_PAGE, **query):
        samples = a_song() if samples is None else samples
        body = samples if isinstance(samples, bytes) else samples.tobytes()
        query = {"name": "A song", "rate": RATE, "frames": len(body) // 4, **query}
        return self.client.put(f"/api/songs/{song_id}", params=query, content=body, headers=headers)

    def rename(self, song_id=ID_A, name="Another name", headers=OWN_PAGE):
        return self.client.patch(f"/api/songs/{song_id}", params={"name": name}, headers=headers)

    def delete(self, song_id=ID_A, headers=OWN_PAGE):
        return self.client.delete(f"/api/songs/{song_id}", headers=headers)

    def set_one(self, at, song_id=ID_A, on=True, headers=OWN_PAGE):
        send = self.client.put if on else self.client.delete
        return send(f"/api/songs/{song_id}/ones", params=None if at is None else {"at": at}, headers=headers)

    def ones(self, song_id=ID_A):
        return self.get(f"/api/songs/{song_id}").json()["ones"]

    def analyse_one(self):
        return self.app.queue.run_one()

    def listed(self):
        return [(song["name"], song["state"]) for song in self.get("/api/songs").json()]


@pytest.fixture
def program(tmp_path):
    return Program(tmp_path / "data")


def files_under(folder):
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file())


# The page


def test_the_page_is_served_with_the_security_headers(program):
    page = program.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"] == "text/html; charset=utf-8"
    assert "<title>Bachata sections</title>" in page.text
    for name, value in SECURITY_HEADERS.items():
        assert page.headers[name] == value
    assert page.headers["cache-control"] == "no-cache"
    for script in ("app", "song", "draw"):
        assert program.get(f"/{script}.js").headers["content-type"] == "text/javascript; charset=utf-8", script
    assert program.get("/style.css").headers["content-type"] == "text/css; charset=utf-8"


def test_the_typeface_is_served_by_the_program_itself(program):
    # The content security policy lets the page load nothing from elsewhere.
    fonts = sorted(path.name for path in (WEB / "fonts").glob("*.woff2"))
    assert fonts == ["hind-500.woff2", "hind-700.woff2"]
    for font in fonts:
        answer = program.get(f"/fonts/{font}")
        assert answer.status_code == 200
        assert answer.headers["content-type"] == "font/woff2"
        assert answer.content[:4] == b"wOF2"
    # Every file the page asks for by name is one the program serves.
    asked = set()
    for sheet in WEB.glob("*.css"):
        asked |= set(re.findall(r"url\([\"']?(/[^)\"']+)", sheet.read_text()))
    for text in [(WEB / "index.html").read_text(), *(script.read_text() for script in WEB.glob("*.js") if ".test." not in script.name)]:
        asked |= set(re.findall(r"""(?:href|src)=["'](/[^"']+)""", text))
        asked |= {"/" + name for name in re.findall(r"""from ['"]\./([^'"]+)['"]""", text)}
    assert asked == {"/style.css", "/app.js", "/song.js", "/draw.js", "/fonts/hind-500.woff2", "/fonts/hind-700.woff2"}
    for path in sorted(asked):
        assert program.get(path).status_code == 200, path


def test_everything_else_is_a_404(program):
    for method, path in [
        ("GET", "/server.py"),
        ("GET", "/../pyproject.toml"),
        ("POST", "/"),
        ("GET", "/web/index.html"),
        ("GET", "/api"),
        ("POST", "/api/songs"),
        ("PATCH", "/api/songs"),
        ("OPTIONS", f"/api/songs/{ID_A}"),
        ("GET", "/fonts/LICENSE.txt"),
        ("GET", "/fonts/"),
        ("GET", "/fonts/hind-500.woff2/x"),
        ("GET", f"/api/songs/{ID_A}/sound/more"),
    ]:
        answer = program.client.request(method, path)
        assert (answer.status_code, answer.text) == (404, "Not found\n"), (method, path)


def test_the_page_loads_nothing_from_outside_and_has_no_inline_code():
    # The content security policy would block these; the page must not rely on them.
    page = (WEB / "index.html").read_text()
    assert not re.search(r"https?://", page)
    assert not re.search(r"<script(?![^>]*\bsrc=)", page)
    assert not re.search(r"<style|\sstyle=|\son\w+=", page)
    # A style sheet may name a file of the program and nothing else.
    for sheet in WEB.glob("*.css"):
        assert not re.search(r"https?:|url\(\s*(?![\"']?/)|@import", sheet.read_text()), sheet.name
    # A script must not write markup or a style attribute into the page either.
    for script in WEB.glob("*.js"):
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|setAttribute\(\s*['\"]style|\beval\(|new Function", script.read_text()), script.name


# The library


def test_an_uploaded_song_is_listed_with_its_name_and_its_state(program):
    assert program.put(ID_A, name="Grupo Extra - Me Emborracharé").status_code == 201
    assert program.put(ID_B, a_song(first=13), name="Fails").status_code == 201
    assert program.listed() == [("Grupo Extra - Me Emborracharé", "waiting"), ("Fails", "waiting")]
    assert program.get(f"/api/songs/{ID_A}").json() == {
        "id": ID_A,
        "name": "Grupo Extra - Me Emborracharé",
        "state": "waiting",
        "seconds": 20.0,
        "ones": [],
    }
    assert program.get(f"/api/songs/{ID_A}/result").status_code == 404

    program.analyse_one()
    assert program.listed() == [("Grupo Extra - Me Emborracharé", "ready"), ("Fails", "waiting")]
    program.analyse_one()
    assert program.listed() == [("Grupo Extra - Me Emborracharé", "ready"), ("Fails", "failed")]
    assert program.get(f"/api/songs/{ID_B}/result").status_code == 404

    result = program.get(f"/api/songs/{ID_A}/result")
    assert result.json() == {"beats": [1.0, 1.5, 1.0], "bpm": [120.0, 120.0, 120.0], "bar": [1, 2, 3], "count": [1, 2, 3]}
    assert result.headers["cache-control"] == "no-store"
    assert program.get("/api/songs").headers["cache-control"] == "no-store"


def test_the_stored_sound_is_the_samples_that_were_sent(program):
    samples = a_song()
    program.put(ID_A, samples)
    sound = program.get(f"/api/songs/{ID_A}/sound")
    assert sound.status_code == 200
    assert sound.content == samples.tobytes()


def test_a_song_already_in_the_library_is_not_stored_or_analysed_twice(tmp_path):
    analysed = []
    program = Program(tmp_path / "data", analyse=lambda samples, rate: analysed.append(1) or analyse(samples, rate))
    assert program.get(f"/api/songs/{ID_A}").status_code == 404
    assert program.put(ID_A, name="First").status_code == 201
    program.analyse_one()
    assert program.get(f"/api/songs/{ID_A}").json()["state"] == "ready"

    again = program.put(ID_A, name="Second")
    assert (again.status_code, again.text) == (409, "The song is already in the library\n")
    assert program.analyse_one() is False
    assert program.listed() == [("First", "ready")]
    assert analysed == [1]
    assert files_under(tmp_path) == [f"data/songs/{ID_A}/{name}" for name in ("result.json", "song.json", "sound.raw")]


def test_a_result_of_an_older_analysis_is_made_again_from_the_stored_sound(tmp_path):
    old = Program(tmp_path / "data", version=1)
    old.put(ID_A)
    old.analyse_one()
    assert old.listed() == [("A song", "ready")]

    newer = {"bpm": [0.0], "bar": [1], "count": [1]}
    new = Program(tmp_path / "data", version=2, analyse=lambda samples, rate: {"beats": [float(len(samples))]} | newer)
    assert new.listed() == [("A song", "waiting")]
    assert new.get(f"/api/songs/{ID_A}/result").status_code == 404
    new.analyse_one()
    assert new.get(f"/api/songs/{ID_A}/result").json() == {"beats": [20.0 * RATE]} | newer


def test_the_library_and_the_queue_survive_a_restart(tmp_path):
    program = Program(tmp_path / "data")
    program.put(ID_A, name="Analysed before")
    program.analyse_one()
    program.put(ID_B, a_song(first=2), name="Still waiting")

    program = Program(tmp_path / "data")
    assert program.listed() == [("Analysed before", "ready"), ("Still waiting", "waiting")]
    program.analyse_one()
    assert program.get(f"/api/songs/{ID_B}/result").json()["beats"] == [1.0, 1.5, 2.0]


def test_a_song_can_be_deleted_in_any_state(program, tmp_path):
    program.put(ID_A)
    program.analyse_one()
    program.put(ID_B, a_song(first=13))
    program.analyse_one()
    program.put("c" * 32, a_song(first=3))
    assert program.listed() == [("A song", "ready"), ("A song", "failed"), ("A song", "waiting")]

    for song_id in (ID_A, ID_B, "c" * 32):
        assert program.delete(song_id).status_code == 204
        assert program.get(f"/api/songs/{song_id}").status_code == 404
        assert program.get(f"/api/songs/{song_id}/sound").status_code == 404
    assert program.listed() == []
    # The waiting one left the queue with it.
    assert program.analyse_one() is False
    assert files_under(tmp_path) == []
    assert program.delete(ID_A).status_code == 404


def test_a_song_is_renamed_and_keeps_its_state_and_its_result(tmp_path):
    analysed = []
    program = Program(tmp_path / "data", analyse=lambda samples, rate: analysed.append(1) or analyse(samples, rate))
    program.put(ID_A, name="track0")
    program.put(ID_B, a_song(first=2), name="track0")
    program.analyse_one()
    assert program.listed() == [("track0", "ready"), ("track0", "waiting")]

    renamed = program.rename(ID_A, "Grupo Extra - Me Emborracharé")
    assert (renamed.status_code, renamed.content) == (204, b"")
    assert program.rename(ID_B, "Eso Es Amor").status_code == 204
    assert program.listed() == [("Grupo Extra - Me Emborracharé", "ready"), ("Eso Es Amor", "waiting")]
    assert program.get(f"/api/songs/{ID_A}").json()["name"] == "Grupo Extra - Me Emborracharé"
    # The sound and the result are the ones it had, and nothing was analysed again.
    assert program.get(f"/api/songs/{ID_A}/result").json()["beats"] == [1.0, 1.5, 1.0]
    assert program.get(f"/api/songs/{ID_A}/sound").content == a_song().tobytes()
    assert analysed == [1]

    # The new names survive a restart, and the waiting song is still in the queue.
    program = Program(tmp_path / "data")
    assert program.listed() == [("Grupo Extra - Me Emborracharé", "ready"), ("Eso Es Amor", "waiting")]
    assert program.analyse_one() is True

    missing = program.rename("c" * 32, "Not there")
    assert (missing.status_code, missing.text) == (404, "No such song\n")


def test_a_beat_is_set_to_count_1_and_taken_back(tmp_path):
    analysed = []
    program = Program(tmp_path / "data", analyse=lambda samples, rate: analysed.append(1) or analyse(samples, rate))
    program.put(ID_A)
    program.put(ID_B, a_song(first=2))
    program.analyse_one()

    done = program.set_one("1.5")
    assert (done.status_code, done.content) == (204, b"")
    assert program.set_one("12.345").status_code == 204
    assert program.set_one("0").status_code == 204
    # Set twice, a beat is there once.
    assert program.set_one("1.5").status_code == 204
    assert program.ones() == [0.0, 1.5, 12.345]
    assert [song["ones"] for song in program.get("/api/songs").json()] == [[0.0, 1.5, 12.345], []]

    assert program.set_one("0", on=False).status_code == 204
    # Taking back a beat that was not set changes nothing.
    assert program.set_one("7", on=False).status_code == 204
    assert program.ones() == [1.5, 12.345]

    # The song keeps its name, its state, its sound and its result, and nothing is analysed again.
    assert program.listed() == [("A song", "ready"), ("A song", "waiting")]
    assert program.get(f"/api/songs/{ID_A}/result").json()["beats"] == [1.0, 1.5, 1.0]
    assert program.get(f"/api/songs/{ID_A}/sound").content == a_song().tobytes()
    assert analysed == [1]

    # It survives a renaming, a restart and a new version of the analysis.
    assert program.rename(ID_A, "Renamed").status_code == 204
    program = Program(tmp_path / "data", version=ANALYSIS_VERSION + 1)
    assert program.listed() == [("Renamed", "waiting"), ("A song", "waiting")]
    program.analyse_one()
    assert program.listed() == [("Renamed", "ready"), ("A song", "waiting")]
    assert program.ones() == [1.5, 12.345]
    assert program.ones(ID_B) == []


def test_a_count_1_is_checked_before_it_is_kept(program):
    program.put(ID_A)
    missing = program.set_one("1.5", "c" * 32)
    assert (missing.status_code, missing.text) == (404, "No such song\n")
    assert program.set_one("1.5", "../../etc").status_code in (400, 404)
    assert program.set_one("1.5", "A" * 32).status_code == 400

    no_time = program.set_one(None)
    assert (no_time.status_code, no_time.text) == (400, "The time is not a number of seconds\n")
    for at in ["", "soon", "-1", "1e3", "nan", "inf", "1,5", "1.2345", "12345", " 1", "1.", ".5", "١"]:
        assert program.set_one(at).status_code == 400, repr(at)
        assert program.set_one(at, on=False).status_code == 400, repr(at)
    late = program.set_one("20.001")
    assert (late.status_code, late.text) == (400, "The time is after the end of the song\n")
    assert program.ones() == []
    assert program.set_one("20").status_code == 204
    assert program.ones() == [20.0]


def test_a_song_takes_200_beats_set_to_count_1_and_no_more(program):
    program.put(ID_A)
    for beat in range(200):
        assert program.set_one(f"{beat / 10:.1f}").status_code == 204
    full = program.set_one("19.95")
    assert (full.status_code, full.text) == (400, "The song has 200 beats set to count 1 already\n")
    # One that is there already may be set again, and one may be taken back.
    assert program.set_one("19.9").status_code == 204
    assert program.set_one("0.0", on=False).status_code == 204
    assert program.set_one("19.95").status_code == 204
    assert len(program.ones()) == 200


def test_a_new_name_is_checked_like_the_name_of_an_upload(program):
    program.put(ID_A, name="Before")
    long = program.rename(name="n" * 201)
    assert (long.status_code, long.text) == (400, "The name is longer than 200 characters\n")
    for name in ["", "   ", "two\nlines", "a\0b", "\x7f"]:
        assert program.rename(name=name).status_code == 400, repr(name)
    no_name = program.client.patch(f"/api/songs/{ID_A}", headers=OWN_PAGE)
    assert (no_name.status_code, no_name.text) == (400, "The song has no name\n")
    assert program.listed() == [("Before", "waiting")]
    assert program.rename(name="ñ" * 200).status_code == 204
    assert program.listed() == [("ñ" * 200, "waiting")]


def test_the_queue_runs_by_itself_when_the_program_runs(tmp_path):
    app = create_app(tmp_path / "data", analyse=analyse)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        body = a_song().tobytes()
        query = {"name": "A song", "rate": RATE, "frames": len(body) // 4}
        assert client.put(f"/api/songs/{ID_A}", params=query, content=body, headers=OWN_PAGE).status_code == 201
        for _ in range(100):
            if client.get(f"/api/songs/{ID_A}").json()["state"] == "ready":
                break
            time.sleep(0.05)
        assert client.get(f"/api/songs/{ID_A}/result").json()["beats"] == [1.0, 1.5, 1.0]


# What is refused


def test_a_request_for_another_host_is_refused(program):
    for host in ["evil.example", "evil.example:8080", "127.0.0.1.evil.example", ""]:
        for path in ["/", "/api/songs"]:
            answer = program.get(path, headers={"Host": host})
            assert (answer.status_code, answer.text) == (400, "Unknown host\n"), host
    assert program.get("/", headers={"Host": "localhost:8080"}).status_code == 200
    # Two hosts in one request: no telling which one the rest of the program would read.
    two = program.get("/", headers=[("Host", "evil.example"), ("Host", "127.0.0.1")])
    assert two.status_code == 400


NOT_THE_OWN_PAGE = [
    {},
    {"Origin": "http://evil.example"},
    {"Origin": "null"},
    {"Origin": "https://127.0.0.1"},
    {"Origin": "http://127.0.0.1:9999"},
    {"Origin": "http://localhost"},
    {"Origin": "http://127.0.0.1", "Sec-Fetch-Site": "cross-site"},
    {"Origin": "http://127.0.0.1", "Sec-Fetch-Site": "same-site"},
    {"Sec-Fetch-Site": "same-origin"},
    {"Referer": "http://127.0.0.1/"},
]


@pytest.mark.parametrize("headers", NOT_THE_OWN_PAGE)
def test_an_upload_that_is_not_from_the_own_page_is_refused(program, tmp_path, headers):
    answer = program.put(ID_A, headers=headers)
    assert (answer.status_code, answer.text) == (403, "Not from the application's own page\n")
    assert program.listed() == []
    assert files_under(tmp_path) == []


@pytest.mark.parametrize("headers", NOT_THE_OWN_PAGE)
def test_a_deletion_that_is_not_from_the_own_page_is_refused(program, headers):
    program.put(ID_A)
    answer = program.delete(ID_A, headers=headers)
    assert (answer.status_code, answer.text) == (403, "Not from the application's own page\n")
    assert program.listed() == [("A song", "waiting")]
    # Deleting a waiting song is the removal from the queue, so that is refused with it.
    assert program.analyse_one() is True


@pytest.mark.parametrize("headers", NOT_THE_OWN_PAGE)
def test_a_renaming_that_is_not_from_the_own_page_is_refused(program, headers):
    program.put(ID_A)
    answer = program.rename(ID_A, headers=headers)
    assert (answer.status_code, answer.text) == (403, "Not from the application's own page\n")
    assert program.listed() == [("A song", "waiting")]


@pytest.mark.parametrize("headers", NOT_THE_OWN_PAGE)
def test_a_count_1_that_is_not_from_the_own_page_is_refused(program, headers):
    program.put(ID_A)
    assert program.set_one("2.5").status_code == 204
    for on in (True, False):
        answer = program.set_one("1.5" if on else "2.5", on=on, headers=headers)
        assert (answer.status_code, answer.text) == (403, "Not from the application's own page\n")
    assert program.ones() == [2.5]


def test_the_own_page_may_use_either_name_of_the_program(program):
    localhost = {"Host": "localhost:8080", "Origin": "http://localhost:8080", "Sec-Fetch-Site": "same-origin"}
    assert program.put(ID_A, headers=localhost).status_code == 201
    assert program.rename(ID_A, headers=localhost).status_code == 204
    assert program.delete(ID_A, headers=localhost).status_code == 204
    # Firefox sends no Sec-Fetch-Site to a page that is not served securely.
    assert program.put(ID_A, headers={"Origin": "http://127.0.0.1"}).status_code == 201


def test_a_body_that_is_not_the_expected_samples_is_refused(program, tmp_path):
    body = a_song(21).tobytes()
    frames = len(body) // 4
    refusals = [
        (program.put(rate=48000), 400, "The samples must be at 44100 Hz"),
        (program.put(rate=""), 400, "The samples must be at 44100 Hz"),
        (program.put(frames=""), 400, "The number of frames is missing"),
        (program.put(frames="-5"), 400, "The number of frames is missing"),
        (program.put(frames="1e6"), 400, "The number of frames is missing"),
        (program.put(frames="٣٣٣٣٣٣٣"), 400, "The number of frames is missing"),
        (program.put(samples=body, frames=frames + 1), 400, "The body is not 4 bytes for every frame"),
        (program.put(samples=body, frames=frames - 1), 400, "The body is not 4 bytes for every frame"),
        (program.put(samples=body[:-1], frames=frames), 400, "The body is not 4 bytes for every frame"),
        (program.put(samples=body + b"\0\0", frames=frames), 400, "The body is not 4 bytes for every frame"),
        (program.put(samples=b"", frames=frames), 400, "The body is not 4 bytes for every frame"),
    ]
    for answer, status, reason in refusals:
        assert (answer.status_code, answer.text) == (status, reason + "\n")
    assert program.listed() == []
    assert files_under(tmp_path) == []


def test_a_body_that_stops_before_its_stated_length_is_refused(program, tmp_path):
    # A client that states a length and sends less: the test client cannot do that, so
    # the request is handed to the application directly.
    import anyio

    body = a_song().tobytes()
    sent = []

    async def receive():
        return {"type": "http.request", "body": body[: len(body) // 2], "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "PUT",
        "path": f"/api/songs/{ID_A}",
        "query_string": f"name=x&rate={RATE}&frames={len(body) // 4}".encode(),
        "headers": [
            (b"host", b"127.0.0.1"),
            (b"origin", b"http://127.0.0.1"),
            (b"content-length", str(len(body)).encode()),
        ],
    }
    anyio.run(program.app, scope, receive, send)
    assert sent[0]["status"] == 400
    assert program.listed() == []
    assert files_under(tmp_path) == []


def test_a_song_that_is_too_short_or_too_long_is_refused(program):
    short = program.put(samples=a_song(19))
    assert (short.status_code, short.text) == (400, "The song is shorter than 20 seconds\n")
    just_short = program.put(samples=a_song(20)[:-1])
    assert just_short.status_code == 400
    assert program.put(samples=a_song(20)).status_code == 201

    # 15 minutes of samples are 159 MB. The length is refused from what the request
    # states, before any of the body is read.
    long = program.put(ID_B, samples=b"", frames=15 * 60 * RATE + 1)
    assert (long.status_code, long.text) == (413, "The song is longer than 15 minutes\n")
    exactly = program.put(ID_B, samples=b"", frames=15 * 60 * RATE)
    assert (exactly.status_code, exactly.text) == (400, "The body is not 4 bytes for every frame\n")
    assert program.listed() == [("A song", "waiting")]


@pytest.mark.parametrize(
    "song_id",
    ["a" * 31, "a" * 33, "A" * 32, "g" * 32, "a" * 31 + ".", "%2e%2e", "a" * 32 + "%0a", "ａ" * 32],
)
def test_a_song_id_that_is_not_well_formed_is_refused(program, tmp_path, song_id):
    refused = (400, "Not a song id\n")
    put = program.put(song_id)
    assert (put.status_code, put.text) == refused
    for path in (f"/api/songs/{song_id}", f"/api/songs/{song_id}/sound", f"/api/songs/{song_id}/result"):
        get = program.get(path)
        assert (get.status_code, get.text) == refused
    rename = program.rename(song_id)
    assert (rename.status_code, rename.text) == refused
    delete = program.delete(song_id)
    assert (delete.status_code, delete.text) == refused
    assert files_under(tmp_path) == []


def test_a_name_that_is_too_long_or_empty_is_refused(program):
    long = program.put(name="n" * 201)
    assert (long.status_code, long.text) == (400, "The name is longer than 200 characters\n")
    for name in ["", "   ", "two\nlines", "a\0b", "\x7f"]:
        assert program.put(name=name).status_code == 400, repr(name)
    assert program.listed() == []
    assert program.put(name="ñ" * 200).status_code == 201
    assert program.listed() == [("ñ" * 200, "waiting")]


def test_a_new_song_is_refused_when_the_library_is_full(tmp_path):
    program = Program(tmp_path / "data", limit=1_000_000)
    assert program.put(ID_A).status_code == 201
    full = program.put(ID_B, a_song(first=2))
    assert (full.status_code, full.text) == (507, "The library is full\n")
    assert program.listed() == [("A song", "waiting")]
    assert files_under(tmp_path) == [f"data/songs/{ID_A}/song.json", f"data/songs/{ID_A}/sound.raw"]
    # Deleting makes room again.
    program.delete(ID_A)
    assert program.put(ID_B, a_song(first=2)).status_code == 201


# What the server never does


def test_a_media_file_is_never_read_as_one(program):
    # The start of an mp3 file with a tag, sent as if it were samples. The server keeps
    # those bytes as the samples they were said to be and makes nothing else of them.
    body = (b"ID3\x04\x00\x00\x00\x00\x00\x15TIT2\x00\x00\x00\x0b\x00\x00\x03Not a song" + b"\xff\xfb\x90\x64") * 120000
    body = body[: 20 * RATE * 4]
    assert program.put(samples=body).status_code == 201
    assert program.get(f"/api/songs/{ID_A}/sound").content == body
    assert program.listed() == [("A song", "waiting")]
    program.analyse_one()
    assert program.get(f"/api/songs/{ID_A}/result").json()["beats"][2] == float(int.from_bytes(b"ID", "little"))


def test_only_the_data_folder_is_written_and_names_on_disk_come_from_the_id(program, tmp_path):
    program.put(ID_A, name="../../outside")
    program.put(ID_B, a_song(first=2), name="b" * 32 + "/../../" + "c" * 32)
    assert program.rename(ID_B, "../../" + "d" * 32 + "/song.json").status_code == 204
    program.analyse_one()
    assert files_under(tmp_path) == [
        f"data/songs/{ID_A}/result.json",
        f"data/songs/{ID_A}/song.json",
        f"data/songs/{ID_A}/sound.raw",
        f"data/songs/{ID_B}/song.json",
        f"data/songs/{ID_B}/sound.raw",
    ]


def test_stored_sound_is_sent_as_sound_data_and_never_as_a_page(program):
    program.put(ID_A, name="<script>alert(1)</script>")
    sound = program.get(f"/api/songs/{ID_A}/sound")
    assert sound.headers["content-type"] == "application/octet-stream"
    assert sound.headers["content-disposition"] == f'attachment; filename="{ID_A}.raw"'
    assert sound.headers["x-content-type-options"] == "nosniff"
    assert sound.headers["cross-origin-resource-policy"] == "same-origin"
    # A name is data too: it travels as JSON and the page shows it as plain text.
    listed = program.get("/api/songs")
    assert listed.headers["content-type"] == "application/json"
    assert listed.json()[0]["name"] == "<script>alert(1)</script>"


def test_every_answer_has_the_security_headers(program):
    program.put(ID_A)
    answers = [
        program.get("/"),
        program.get("/app.js"),
        program.get("/nothing"),
        program.client.post("/"),
        program.get("/", headers={"Host": "evil.example"}),
        program.get("/api/songs"),
        program.get(f"/api/songs/{ID_A}"),
        program.get(f"/api/songs/{ID_A}/sound"),
        program.get(f"/api/songs/{ID_A}/result"),
        program.get(f"/api/songs/{ID_B}"),
        program.get("/api/songs/not-an-id"),
        program.put(ID_A),
        program.put(ID_B, headers={}),
        program.put(ID_B, rate=1),
        program.put(ID_B, a_song(first=2)),
        program.rename(ID_B),
        program.rename(ID_B, headers={}),
        program.rename(ID_B, name=""),
        program.rename("c" * 32),
        program.set_one("1.5"),
        program.set_one("1.5", headers={}),
        program.set_one("soon"),
        program.set_one("1.5", "c" * 32),
        program.set_one("1.5", on=False),
        program.get("/fonts/hind-700.woff2"),
        program.delete(ID_B, headers={}),
        program.delete(ID_B),
        program.delete(ID_B),
    ]
    assert sorted({answer.status_code for answer in answers}) == [200, 201, 204, 400, 403, 404, 409]
    for answer in answers:
        for name, value in SECURITY_HEADERS.items():
            assert answer.headers[name] == value, (answer.request.method, answer.request.url, answer.status_code)


def test_an_error_inside_the_program_still_has_the_security_headers(tmp_path):
    program = Program(tmp_path / "data")
    program.app.store.songs = None
    answer = TestClient(program.app, base_url="http://127.0.0.1", raise_server_exceptions=False).get("/api/songs")
    assert answer.status_code == 500
    for name, value in SECURITY_HEADERS.items():
        assert answer.headers[name] == value


def test_the_program_listens_on_the_loopback_interface_only(tmp_path):
    # An unused port, or the one BACHATA_TEST_PORT names.
    with socket.socket() as probe:
        # A port that was just used by an earlier test may be taken again at once.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", int(os.environ.get("BACHATA_TEST_PORT", "0"))))
        port = probe.getsockname()[1]
    program = subprocess.Popen(
        [sys.executable, "-m", "bachata"],
        env={**os.environ, "PORT": str(port), "BACHATA_DATA": str(tmp_path / "data")},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert program.stdout.readline() == f"Bachata sections: http://127.0.0.1:{port}\n"
        for _ in range(100):
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port)
                connection.request("GET", "/api/songs")
                answer = connection.getresponse()
                assert (answer.status, answer.read()) == (200, b"[]")
                assert answer.getheader("server") is None
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        else:
            raise AssertionError("the program did not start")
        # Every listening socket of the program, as the kernel reports them.
        listening = subprocess.run(["ss", "-Hltnp"], capture_output=True, text=True, check=True).stdout
        mine = [line.split()[3] for line in listening.splitlines() if f"pid={program.pid}," in line]
        assert mine == [f"127.0.0.1:{port}"]
        # The library is where the setting says.
        assert (tmp_path / "data" / "songs").is_dir()
    finally:
        program.terminate()
        program.wait()
