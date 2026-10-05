"""End-to-end tests: whole flows through the page, in a real browser, against the real program.

    uv run pytest e2e

They start the program on its own data folder and drive Chrome and Firefox with Playwright.
Chrome is the one installed on the machine. Firefox is Playwright's own build, fetched once:

    PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install firefox

A browser that cannot start is skipped, and says so. The songs are made here with ffmpeg:
a drum-like click at 120 BPM. Nothing from the reference material is needed.
"""

import http.client
import os
import shutil
import socket
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).parent.parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright"))

RATE = 44100
BPM = 120
TAGGED = "Los Tests - Canción de prueba"


def a_song(path, seconds, *tags):
    """A file with a short burst of noise on every beat at 120 BPM, and a quieter one between."""
    random = np.random.default_rng(7)
    samples = random.normal(0, 30, round(RATE * seconds))
    burst = random.normal(0, 9000, 2000) * np.exp(-np.arange(2000) / 300)
    for n in range(int(seconds * 4) - 1):
        start = round((0.25 + n * 30 / BPM) * RATE)
        samples[start : start + 2000] += burst * (1.0 if n % 2 == 0 else 0.35)
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(np.repeat(samples.clip(-32768, 32767).astype("<i2"), 2).tobytes())
    metadata = [part for tag in tags for part in ("-metadata", tag)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), *metadata, str(path)], check=True)
    return path


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    if shutil.which("ffmpeg") is None:
        pytest.skip("skipped: ffmpeg is not installed, the test songs cannot be made")
    folder = tmp_path_factory.mktemp("songs")
    made = {
        "tagged": a_song(folder / "track01.m4a", 24.5, "title=Canción de prueba", "artist=Los Tests"),
        "untagged": a_song(folder / "Sin etiquetas.mp3", 22.5),
        "markup": a_song(folder / "markup.mp3", 21.5, "title=<img src=x onerror=document.title='broken'><b>bold</b>"),
        "short": a_song(folder / "short.mp3", 10),
        "wav": folder / "track01.wav",
        "text": folder / "notes.mp3",
        "broken": folder / "broken.mp3",
    }
    # Fifteen minutes and one second of silence, small enough to make and to decode quickly.
    made["long"] = folder / "long.mp3"
    silence = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "901", "-b:a", "32k"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *silence, str(made["long"])], check=True)
    made["text"].write_text("This is a text file with the name of a song.\n" * 50)
    made["broken"].write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00" + bytes(range(256)) * 400)
    return made


@pytest.fixture
def program(tmp_path):
    """The real program, on an empty library. Gives the address of its page."""
    # An unused port, or the one BACHATA_TEST_PORT names.
    with socket.socket() as probe:
        # A port that was just used by an earlier test may be taken again at once.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", int(os.environ.get("BACHATA_TEST_PORT", "0"))))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "bachata"],
        cwd=ROOT,
        env={**os.environ, "PORT": str(port), "BACHATA_DATA": str(tmp_path / "data")},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout.readline().startswith("Bachata sections")
        for _ in range(100):
            try:
                http.client.HTTPConnection("127.0.0.1", port).request("GET", "/")
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        process.wait()


@pytest.fixture(scope="module")
def playwright():
    with sync_playwright() as started:
        yield started


@pytest.fixture(scope="module", params=["chrome", "firefox"])
def browser(request, playwright):
    try:
        if request.param == "chrome":
            # The Chrome that is installed on the machine, not a build of Playwright's.
            started = playwright.chromium.launch(channel="chrome")
        else:
            started = playwright.firefox.launch()
    except Exception as error:
        pytest.skip(f"skipped: {request.param} could not start: {str(error).splitlines()[0]}")
    yield started
    started.close()


# Notes every sound the page hands to the audio clock, and every volume control it makes.
SPY = """
window.started = []
window.volumes = []
const start = AudioBufferSourceNode.prototype.start
AudioBufferSourceNode.prototype.start = function (when = 0, offset = 0) {
  window.started.push({ seconds: this.buffer.duration, when, offset })
  return start.apply(this, arguments)
}
const createGain = BaseAudioContext.prototype.createGain
BaseAudioContext.prototype.createGain = function () {
  const volume = createGain.call(this)
  window.volumes.push(volume)
  return volume
}
"""


class Visitor:
    """Someone with a browser that has never been on the page. Notes what the browser sends."""

    def __init__(self, browser, address):
        self.context = browser.new_context()
        self.context.add_init_script(SPY)
        self.page = self.context.new_page()
        self.sent = []
        self.errors = []
        self.page.on("request", lambda request: self.sent.append((request.method, request.url.removeprefix(address))))
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda message: message.type == "error" and self.errors.append(message.text))
        self.page.goto(address)

    def uploads(self):
        return [url for method, url in self.sent if method == "PUT"]

    def pick(self, file):
        self.page.set_input_files("#file", str(file))

    def rows(self):
        return self.page.locator("#songs li")

    def row(self, name):
        return self.page.locator("#songs li", has=self.page.get_by_text(name, exact=True))

    def close(self):
        self.context.close()


@pytest.fixture
def visit(browser, program):
    visitors = []

    def new():
        visitors.append(Visitor(browser, program))
        return visitors[-1]

    yield new
    for visitor in visitors:
        visitor.close()
        # 404 is how the server says a song is not in the library yet; the browser logs it.
        assert [error for error in visitor.errors if "404" not in error] == []


READY = 60_000  # ms: an analysis takes a few seconds, the first one loads the model too


def needs_sound(page):
    """Skips a test about playing where the browser has no sound output at all.

    The question is put to an audio clock of the test's own, not to the page's, so a page
    that fails to play still fails its test. Ask after a press on the page: a browser
    starts no audio clock before one.
    """
    runs = page.evaluate(
        """async () => {
            const clock = new AudioContext()
            clock.resume()
            await new Promise((done) => setTimeout(done, 1000))
            return clock.state === 'running' && clock.currentTime > 0
        }"""
    )
    if not runs:
        pytest.skip("skipped: this browser has no sound output here, so nothing can play")


def test_an_uploaded_song_is_analysed_listed_and_played(visit, files):
    visitor = visit()
    page = visitor.page
    expect(page.locator("#empty")).to_be_visible()
    expect(page.locator("#player")).to_be_hidden()

    visitor.pick(files["tagged"])
    # The name comes from the tags of the file, and the song goes through its states.
    row = visitor.row(TAGGED)
    expect(row).to_have_attribute("data-state", "ready", timeout=READY)
    expect(row.locator(".state")).to_have_text("0:24, ready")
    expect(page.locator("#empty")).to_be_hidden()
    assert len(visitor.uploads()) == 1
    assert "rate=44100" in visitor.uploads()[0]

    # It opens by itself: the strip with one tick per beat, the tempo, the click switch.
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    expect(page.locator("#song-name")).to_have_text(TAGGED)
    expect(page.locator("#duration")).to_have_text("0:24")
    beats = int(page.locator("#strip").get_attribute("data-beats"))
    assert 44 <= beats <= 50, beats
    assert abs(int(page.locator("#bpm").inner_text()) / BPM - 1) <= 0.04
    expect(page.locator("#click")).to_be_checked()
    expect(page.locator("#position")).to_have_text("0:00")

    # Playing moves the marker along the strip.
    def marker_at():
        return page.evaluate(
            """() => {
                const canvas = document.getElementById('strip')
                const row = canvas.getContext('2d').getImageData(0, 2, canvas.width, 1).data
                for (let x = 0; x < canvas.width; x++) if (row[4 * x + 3] > 200) return x / canvas.width
                return null
            }"""
        )

    assert marker_at() < 0.01
    page.locator("#play").click()
    expect(page.locator("#play")).to_have_text("Pause")
    needs_sound(page)
    expect(page.locator("#position")).to_have_text("0:02", timeout=10_000)
    assert 0.05 < marker_at() < 0.2
    page.locator("#click").uncheck()
    page.locator("#click").check()
    page.locator("#play").click()
    expect(page.locator("#play")).to_have_text("Play")
    stopped = page.locator("#position").inner_text()
    page.wait_for_timeout(1200)
    assert page.locator("#position").inner_text() == stopped

    # A press on the strip moves the playing position.
    box = page.locator("#strip").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] / 2)
    expect(page.locator("#position")).to_have_text("0:12")
    assert 0.45 < marker_at() < 0.55


def test_a_click_is_placed_on_every_beat_and_can_be_switched_off(visit, files):
    """Whether the click sounds on the beat is for the owner's ear. This checks what the ear
    cannot: that every beat gets one click, at its own time on the clock the song plays on."""
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    row = visitor.row(TAGGED)
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beats = page.evaluate("id => fetch(`/api/songs/${id}/result`).then((answer) => answer.json())", row.get_attribute("data-id"))["beats"]

    def placed():
        """The beat each click was placed on, from when it and the song were started."""
        started = page.evaluate("window.started.splice(0)")
        songs = [sound for sound in started if sound["seconds"] > 1]
        assert len(songs) == 1
        return songs[0]["offset"], [
            round(sound["when"] - songs[0]["when"] + songs[0]["offset"], 3) for sound in started if sound["seconds"] < 1
        ]

    page.locator("#play").click()
    needs_sound(page)
    expect(page.locator("#position")).to_have_text("0:03", timeout=10_000)
    page.locator("#play").click()
    offset, clicks = placed()
    assert offset == 0
    assert len(clicks) >= 6
    assert clicks == beats[: len(clicks)]

    # From the middle of the song, the first click is on the first beat after that point.
    box = page.locator("#strip").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] / 2)
    page.locator("#play").click()
    expect(page.locator("#position")).to_have_text("0:14", timeout=10_000)
    offset, clicks = placed()
    assert 12 < offset < 12.5
    later = [beat for beat in beats if beat >= offset]
    assert len(clicks) >= 3
    assert clicks == later[: len(clicks)]

    # The switch silences the clicks at once, the ones already placed included.
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [1]
    page.locator("#click").uncheck()
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [0]
    page.locator("#click").check()
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [1]


def test_a_song_opens_in_a_browser_that_never_had_the_file(visit, files):
    first = visit()
    first.pick(files["untagged"])
    # No tags: the name is the file name without its extension.
    expect(first.row("Sin etiquetas")).to_have_attribute("data-state", "ready", timeout=READY)

    other = visit()
    row = other.row("Sin etiquetas")
    expect(row).to_have_attribute("data-state", "ready")
    expect(other.page.locator("#player")).to_be_hidden()
    row.get_by_role("button", name="Open").click()
    expect(other.page.locator("#player")).to_be_visible()
    expect(other.page.locator("#song-name")).to_have_text("Sin etiquetas")
    assert int(other.page.locator("#strip").get_attribute("data-beats")) >= 40
    other.page.locator("#play").click()
    needs_sound(other.page)
    expect(other.page.locator("#position")).to_have_text("0:01", timeout=10_000)
    # Nothing was uploaded, and the song was not analysed again.
    assert other.uploads() == []
    expect(row).to_have_attribute("data-state", "ready")
    assert [method for method, url in other.sent if method not in ("GET",)] == []


def test_a_file_already_in_the_library_is_not_uploaded_again(visit, files):
    first = visit()
    first.pick(files["tagged"])
    expect(first.row(TAGGED)).to_have_attribute("data-state", "ready", timeout=READY)

    other = visit()
    expect(other.rows()).to_have_count(1)
    other.pick(files["tagged"])
    expect(other.page.locator("#player")).to_be_visible()
    expect(other.page.locator("#song-name")).to_have_text(TAGGED)
    assert other.uploads() == []
    expect(other.rows()).to_have_count(1)
    expect(other.row(TAGGED)).to_have_attribute("data-state", "ready")


def test_a_song_is_deleted_after_one_confirmation(visit, files):
    visitor = visit()
    visitor.pick(files["tagged"])
    row = visitor.row(TAGGED)
    expect(row).to_have_attribute("data-state", "ready", timeout=READY)
    expect(visitor.page.locator("#player")).to_be_visible(timeout=READY)
    other = visit()
    expect(other.rows()).to_have_count(1)

    row.get_by_role("button", name="Delete").click()
    expect(row).to_contain_text("Delete this song?")
    row.get_by_role("button", name="Keep").click()
    expect(row).not_to_contain_text("Delete this song?")
    expect(visitor.rows()).to_have_count(1)

    row.get_by_role("button", name="Delete").click()
    row.get_by_role("button", name="Yes, delete").click()
    expect(visitor.rows()).to_have_count(0)
    expect(visitor.page.locator("#empty")).to_be_visible()
    expect(visitor.page.locator("#player")).to_be_hidden()
    # It is gone for everyone.
    expect(other.rows()).to_have_count(0, timeout=10_000)


def test_a_file_of_the_wrong_type_is_refused_by_the_page(visit, files):
    visitor = visit()
    message = visitor.page.locator("#message")
    for file, said in [
        (files["wav"], "This is not an mp3 or m4a file."),
        (files["text"], "This is not an mp3 or m4a file."),
        (files["broken"], "The browser cannot decode this file."),
    ]:
        visitor.pick(file)
        expect(message).to_have_text(said)
        expect(message).to_contain_class("refused")
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


def test_a_song_that_is_too_short_is_refused_by_the_page(visit, files):
    visitor = visit()
    visitor.pick(files["short"])
    expect(visitor.page.locator("#message")).to_have_text("This song is shorter than 20 seconds.")
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


def test_a_song_that_is_too_long_is_refused_by_the_page(visit, files):
    visitor = visit()
    visitor.pick(files["long"])
    expect(visitor.page.locator("#message")).to_have_text("This song is longer than 15 minutes.", timeout=READY)
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


def test_a_name_is_shown_as_plain_text(visit, files):
    visitor = visit()
    visitor.pick(files["markup"])
    name = "<img src=x onerror=document.title='broken'><b>bold</b>"
    expect(visitor.row(name)).to_have_attribute("data-state", "ready", timeout=READY)
    expect(visitor.page.locator("#song-name")).to_have_text(name, timeout=READY)
    assert visitor.page.locator("#songs img, #songs b, #player img, #player b").count() == 0
    assert visitor.page.title() == "Bachata sections"


def test_the_sound_that_plays_is_the_exact_samples_that_were_sent(visit, files):
    """The beats are found on the stored samples. The page must play those and no others."""
    visitor = visit()
    visitor.pick(files["tagged"])
    row = visitor.row(TAGGED)
    expect(row).to_have_attribute("data-state", "ready", timeout=READY)
    song_id = row.get_attribute("data-id")
    compared = visitor.page.evaluate(
        """async ([id, original]) => {
            const { interleaved16, channelsFrom16 } = await import('/song.js')
            const decoded = await new OfflineAudioContext(2, 1, 44100).decodeAudioData(Uint8Array.from(original).buffer)
            const sent = interleaved16(decoded.getChannelData(0), decoded.getChannelData(1))
            const stored = new Int16Array(await (await fetch(`/api/songs/${id}/sound`)).arrayBuffer())
            const played = interleaved16(...channelsFrom16(stored))
            let different = 0
            for (let i = 0; i < sent.length; i++) if (sent[i] !== played[i]) different++
            return { sent: sent.length, played: played.length, different }
        }""",
        [song_id, list(files["tagged"].read_bytes())],
    )
    assert compared["sent"] >= 24 * RATE * 2
    assert compared == {"sent": compared["sent"], "played": compared["sent"], "different": 0}
