"""End-to-end tests: whole flows through the page, in a real browser, against the real program.

The beats of a song are drawn on two canvases. The page says in attributes of those
canvases which beat is lit and where the marks of the song are, and the tests read them.

    uv run pytest e2e

They start the program on its own data folder and drive Chrome and Firefox with Playwright.
Chrome is the one installed on the machine. Firefox is Playwright's own build, fetched once:

    PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install firefox

A browser that cannot start is skipped, and says so. The songs are made here with ffmpeg:
a drum-like click at 120 BPM. Nothing from the reference material is needed.
"""

import http.client
import json
import os
import re
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
IN_OPUS = "Los Tests - Canción en opus"


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
        # ffmpeg writes the names of an opus file's tags in small letters.
        "opus": a_song(folder / "track02.opus", 23.5, "title=Canción en opus", "artist=Los Tests"),
        "short opus": a_song(folder / "short.opus", 10),
        # Sound of another kind in the same wrapping as opus.
        "vorbis": a_song(folder / "vorbis.ogg", 21),
        "wav": folder / "track01.wav",
        "text": folder / "notes.mp3",
        "broken": folder / "broken.mp3",
    }
    # Fifteen minutes and one second of silence, small enough to make and to decode quickly.
    silence = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "901", "-b:a", "32k"]
    for name, file in (("long", "long.mp3"), ("long opus", "long.opus")):
        made[name] = folder / file
        subprocess.run(["ffmpeg", "-v", "error", "-y", *silence, str(made[name])], check=True)
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


# Notes every sound the page hands to the audio clock, with the loop it was given, the
# clock itself, and every volume control the page makes.
SPY = """
window.started = []
window.volumes = []
const start = AudioBufferSourceNode.prototype.start
AudioBufferSourceNode.prototype.start = function (when = 0, offset = 0) {
  window.clock = this.context
  const loop = this.loop ? { loopStart: this.loopStart, loopEnd: this.loopEnd } : {}
  window.started.push({ seconds: this.buffer.duration, when, offset, loop: this.loop, ...loop })
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

    def __init__(self, browser, address, path="/", **settings):
        self.context = browser.new_context(**settings)
        self.context.add_init_script(SPY)
        self.page = self.context.new_page()
        self.sent = []
        self.errors = []
        self.page.on("request", lambda request: self.sent.append((request.method, request.url.removeprefix(address))))
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("console", lambda message: message.type == "error" and self.errors.append(message.text))
        self.page.goto(address + path)

    def uploads(self):
        return [url for method, url in self.sent if method == "PUT"]

    def renamings(self):
        return [url for method, url in self.sent if method == "PATCH"]

    def pick(self, file):
        self.page.set_input_files("#file", str(file))

    def rows(self):
        return self.page.locator("#songs li")

    def row(self, name):
        return self.page.locator("#songs li", has=self.page.get_by_text(name, exact=True))

    def result(self, name):
        """What the analysis made of a song, as the server has it."""
        song_id = self.row(name).get_attribute("data-id")
        return self.page.evaluate("id => fetch(`/api/songs/${id}/result`).then((answer) => answer.json())", song_id)

    def beats(self, name):
        return self.result(name)["beats"]

    def counts(self):
        """The count of every beat, as the song on screen says it."""
        return [int(count) for count in self.page.locator("#map").get_attribute("data-counts").split()]

    def marks(self):
        """The middle of the mark of every beat, inside the canvas of the song."""
        return json.loads(self.page.locator("#map").get_attribute("data-marks"))

    def changes_of_count(self):
        return [(method, url) for method, url in self.sent if url.endswith("/ones") or "/ones?" in url]

    def lit(self):
        """The beat whose mark is lit, or -1 before the first one."""
        lit = self.page.locator("#now").get_attribute("data-lit")
        return int(lit) if lit else -1

    def point_of(self, beat):
        """Where the mark of a beat is on the page. The song says where it puts its marks."""
        box = self.page.locator("#map").bounding_box()
        x, y = self.marks()[beat]
        return box["x"] + x, box["y"] + y

    def press_beat(self, beat):
        self.page.mouse.click(*self.point_of(beat))

    def drag_across(self, first, last):
        self.page.mouse.move(*self.point_of(first))
        self.page.mouse.down()
        self.page.mouse.move(*self.point_of(last), steps=6)
        self.page.mouse.up()

    def close(self):
        self.context.close()


@pytest.fixture
def visit(browser, program):
    visitors = []

    def new(path="/", **settings):
        visitors.append(Visitor(browser, program, path, **settings))
        return visitors[-1]

    yield new
    for visitor in visitors:
        visitor.close()
        # 404 is how the server says a song is not in the library yet; the browser logs it.
        assert [error for error in visitor.errors if "404" not in error] == []


READY = 60_000  # ms: an analysis takes a few seconds, the first one loads the model too

# What the canvas of the song says about itself, in the order point_of() reads it.


def clock(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


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

    # It opens by itself: the count as the largest figure, the tempo, the beats, the click switch.
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    expect(page.locator("#song-name")).to_have_text(TAGGED)
    expect(page.locator("#duration")).to_have_text("0:24")
    beats = visitor.beats(TAGGED)
    assert 44 <= len(beats) <= 50, len(beats)
    assert int(page.locator("#now").get_attribute("data-beats")) == len(beats)
    assert abs(int(page.locator("#bpm").inner_text()) / BPM - 1) <= 0.04
    # The count is the largest figure on the page, and the tempo is small beside the time.
    sizes = page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('body *')].map(
            (part) => [part.id || part.className || part.tagName, parseFloat(getComputedStyle(part).fontSize)]))"""
    )
    assert sizes["count"] == max(sizes.values()) >= 100
    assert sizes["bpm"] < 30
    # No beat has sounded yet, so there is no count to show.
    expect(page.locator("#count")).to_have_text("–")
    counts = visitor.result(TAGGED)["count"]
    assert visitor.counts() == counts
    expect(page.locator("#click")).to_be_checked()
    expect(page.locator("#position")).to_have_text("0:00")
    # The list says which song is open, in words.
    expect(row).to_have_attribute("aria-current", "true")
    expect(row).to_contain_text("Open now")

    # No beat has sounded yet, so none is lit. Playing lights them one after the other.
    assert visitor.lit() == -1
    page.locator("#play").click()
    expect(page.locator("#play")).to_have_text("Pause")
    needs_sound(page)
    expect(page.locator("#position")).to_have_text("0:02", timeout=10_000)
    assert 2 <= visitor.lit() <= 5
    page.locator("#click").uncheck()
    page.locator("#click").check()
    page.locator("#play").click()
    expect(page.locator("#play")).to_have_text("Play")
    stopped = page.locator("#position").inner_text()
    page.wait_for_timeout(1200)
    assert page.locator("#position").inner_text() == stopped

    # A press on a beat of the song moves the playing position onto it.
    visitor.press_beat(24)
    expect(page.locator("#now")).to_have_attribute("data-lit", "24")
    expect(page.locator("#position")).to_have_text(clock(beats[24]))
    expect(page.locator("#count")).to_have_text(str(counts[24]))
    # The large view shows the ocho of that beat, each beat at the place of its count. A
    # press on one of them moves the position too.
    first, last = (int(beat) for beat in page.locator("#now").get_attribute("data-ocho").split())
    assert first <= 24 <= last and counts[first] == 1 and last - first == 7
    other = last if last != 24 else first
    large = page.locator("#now").bounding_box()
    page.mouse.click(large["x"] + large["width"] * (counts[other] - 0.5) / 8, large["y"] + large["height"] / 2)
    expect(page.locator("#now")).to_have_attribute("data-lit", str(other))
    expect(page.locator("#count")).to_have_text(str(counts[other]))
    # And so does the position control of the transport bar.
    page.locator("#seek").fill("5")
    expect(page.locator("#position")).to_have_text("0:05")
    assert visitor.lit() == max(n for n, beat in enumerate(beats) if beat <= 5)


def test_a_click_is_placed_on_every_beat_and_can_be_switched_off(visit, files):
    """Whether the click sounds on the beat is for the owner's ear. This checks what the ear
    cannot: that every beat gets one click, at its own time on the clock the song plays on."""
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beats = visitor.beats(TAGGED)

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

    # From a beat in the middle of the song, the first click is on that beat.
    visitor.press_beat(24)
    page.locator("#play").click()
    expect(page.locator("#position")).to_have_text(clock(beats[24] + 2), timeout=10_000)
    offset, clicks = placed()
    assert offset == beats[24]
    later = beats[24:]
    assert len(clicks) >= 3
    assert clicks == later[: len(clicks)]

    # The switch silences the clicks at once, the ones already placed included.
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [1]
    page.locator("#click").uncheck()
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [0]
    page.locator("#click").check()
    assert page.evaluate("window.volumes.map((volume) => volume.gain.value)") == [1]


def test_the_lit_beat_is_the_beat_that_clicks(visit, files):
    """The mark that is lit and the click are the same beat: both follow the clock the song
    plays on, and the mark allows for the time the sound takes to reach the speakers."""
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beats = visitor.beats(TAGGED)

    page.locator("#play").click()
    needs_sound(page)
    lit = set()
    for _ in range(20):
        page.wait_for_timeout(150)
        now = page.evaluate(
            """() => {
                const song = window.started.find((sound) => sound.seconds > 1)
                const heard = window.clock.currentTime - (window.clock.outputLatency || 0)
                return { lit: document.getElementById('now').dataset.lit, position: heard - song.when + song.offset }
            }"""
        )
        if now["position"] < beats[0] + 0.1:
            continue
        beat = int(now["lit"])
        lit.add(beat)
        # The mark is drawn once for every picture of the screen, so it may be one picture late.
        assert beats[beat] - 0.08 <= now["position"] < beats[beat + 1] + 0.08, now
    assert len(lit) >= 4
    # Each of those beats got its click, at its own time.
    started = page.evaluate("window.started")
    song = next(sound for sound in started if sound["seconds"] > 1)
    clicks = [round(sound["when"] - song["when"] + song["offset"], 3) for sound in started if sound["seconds"] < 1]
    assert all(beats[beat] in clicks for beat in lit)


def test_a_marked_range_plays_in_a_loop_with_a_click_on_every_beat_of_every_pass(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beats = visitor.beats(TAGGED)
    expect(page.locator("#loop")).to_be_disabled()
    expect(page.locator("#loop-range")).to_have_text("Drag across beats")

    # Dragging across four beats marks them and switches the loop on. It is two seconds long.
    first, last = 8, 11
    visitor.drag_across(first, last)
    expect(page.locator("#loop")).to_be_checked()
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[first])} to {clock(beats[last + 1] - 0.02)}")
    length = beats[last + 1] - beats[first]

    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    needs_sound(page)
    for _ in range(11):
        page.wait_for_timeout(500)
        # The position never leaves the range. It starts a moment before its first beat.
        assert first - 1 <= visitor.lit() <= last
    page.locator("#play").click()

    started = page.evaluate("window.started.splice(0)")
    songs = [sound for sound in started if sound["seconds"] > 1]
    assert len(songs) == 1
    song = songs[0]
    # The sound goes round by itself, from just before the first beat to just before the
    # beat after the last one: there is no gap to hear between two passes.
    assert song["loop"] is True
    assert song["offset"] == song["loopStart"]
    assert beats[first] - 0.05 < song["loopStart"] <= beats[first]
    assert abs(song["loopEnd"] - song["loopStart"] - length) < 1e-6

    # On every pass each beat inside the range gets one click, at its own time.
    passes = {}
    for sound in started:
        if sound["seconds"] < 1:
            played = sound["when"] - song["when"] + song["offset"]
            turn = int((played - song["loopStart"]) // length)
            passes.setdefault(turn, []).append(round(played - turn * length, 3))
    assert len(passes) >= 3
    whole = [turn for turn in sorted(passes)[:-1]]
    assert len(whole) >= 2
    for turn in whole:
        assert passes[turn] == beats[first : last + 1], turn
    assert passes[max(passes)] == beats[first : first + len(passes[max(passes)])]

    # With the loop switched off the song plays on, past the end of the range.
    page.locator("#loop").uncheck()
    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "playing")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(last + 3), timeout=10_000)
    page.locator("#play").click()
    assert [sound["loop"] for sound in page.evaluate("window.started.splice(0)") if sound["seconds"] > 1] == [False]

    # Cleared while the song goes round it, the range is gone and the song plays on.
    visitor.drag_across(first, last)
    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    page.locator("#loop-clear").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "playing")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(last + 2), timeout=10_000)
    page.locator("#play").click()
    assert [sound["loop"] for sound in page.evaluate("window.started.splice(0)") if sound["seconds"] > 1] == [True, False]

    # The two ends can also be set at the playing position, one at a time.
    visitor.press_beat(20)
    page.locator("#loop-start").click()
    expect(page.locator("#loop-range")).to_have_text(f"From {clock(beats[20])}")
    expect(page.locator("#loop")).to_be_disabled()
    visitor.press_beat(23)
    page.locator("#loop-end").click()
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[20])} to {clock(beats[24] - 0.02)}")
    expect(page.locator("#loop")).to_be_checked()
    # An end set before the start drops the start.
    visitor.press_beat(16)
    page.locator("#loop-end").click()
    expect(page.locator("#loop-range")).to_have_text(f"To {clock(beats[16])}")
    expect(page.locator("#loop")).not_to_be_checked()


def test_the_loop_is_switched_off_and_on_while_the_song_plays(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    player, loop = page.locator("#player"), page.locator("#loop")
    first, last = 8, 11
    visitor.drag_across(first, last)
    page.locator("#play").click()
    expect(player).to_have_attribute("data-state", "looping")

    # Switched off while the song goes round the range: the song plays on and the range stays.
    loop.click()
    expect(loop).not_to_be_checked()
    expect(player).to_have_attribute("data-state", "playing")
    expect(page.locator("#map")).to_have_attribute("data-range", f"{first} {last}")
    # Switched on again, the song goes round it again without a press on Play.
    loop.click()
    expect(loop).to_be_checked()
    expect(player).to_have_attribute("data-state", "looping")
    # And from the keyboard.
    loop.focus()
    page.keyboard.press("Space")
    expect(loop).not_to_be_checked()
    expect(player).to_have_attribute("data-state", "playing")
    expect(page.locator("#play")).to_have_text("Pause")
    # The sound was handed to the audio clock again at each change, with the loop or without.
    assert [sound["loop"] for sound in page.evaluate("window.started") if sound["seconds"] > 1] == [True, False, True, False]

    # Without the loop the song leaves the range. Switched on after that, it goes back
    # into the range and stays there.
    needs_sound(page)
    page.wait_for_function("last => Number(document.getElementById('now').dataset.lit) > last", arg=last, timeout=10_000)
    loop.click()
    expect(player).to_have_attribute("data-state", "looping")
    for _ in range(6):
        page.wait_for_timeout(500)
        assert first - 1 <= visitor.lit() <= last


def test_a_marked_range_can_be_cleared(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, clear = page.locator("#map"), page.locator("#loop-clear")
    beats = visitor.beats(TAGGED)
    # Nothing is marked yet, so there is nothing to clear.
    expect(clear).to_be_disabled()
    expect(song).to_have_attribute("data-range", "")

    visitor.drag_across(8, 11)
    expect(page.locator("#loop")).to_be_checked()
    expect(song).to_have_attribute("data-range", "8 11")
    # The bar that opens the range is on the canvas, at the left edge of its first beat.
    marks = visitor.marks()
    edge = [marks[8][0] - (marks[9][0] - marks[8][0]) / 2 + 2, marks[8][1]]
    page.mouse.move(0, 0)
    assert page.evaluate(INK, edge)["inked"]

    # Switched off, the loop keeps its range: it can be switched on again.
    page.locator("#loop").uncheck()
    expect(song).to_have_attribute("data-range", "8 11")
    assert page.evaluate(INK, edge)["inked"]
    expect(clear).to_be_enabled()
    # Cleared, the range is gone from the song and from the transport bar.
    clear.click()
    expect(song).to_have_attribute("data-range", "")
    assert not page.evaluate(INK, edge)["inked"]
    expect(page.locator("#loop-range")).to_have_text("Drag across beats")
    expect(page.locator("#loop")).to_be_disabled()
    expect(page.locator("#loop")).not_to_be_checked()
    expect(clear).to_be_disabled()

    # A range with only one end is cleared too, and from the keyboard: it then goes to
    # the control beside the one that is no longer there to press.
    visitor.press_beat(20)
    page.locator("#loop-start").click()
    expect(page.locator("#loop-range")).to_have_text(f"From {clock(beats[20])}")
    clear.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#loop-range")).to_have_text("Drag across beats")
    expect(clear).to_be_disabled()
    expect(page.locator("#loop-start")).to_be_focused()
    # A new range can be marked afterwards.
    visitor.drag_across(4, 6)
    expect(song).to_have_attribute("data-range", "4 6")
    expect(page.locator("#loop")).to_be_checked()


def test_every_song_has_an_address_that_opens_it(visit, files):
    visitor = visit()
    page = visitor.page
    # With no song open the address is the plain one.
    assert page.url.endswith("/")
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    tagged = visitor.row(TAGGED).get_attribute("data-id")
    # The address names the song that is open.
    expect(page).to_have_url(re.compile(rf"/\?song={tagged}$"))

    # Loaded again, the page opens that song. Nothing is sent again.
    page.reload()
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    expect(page.locator("#song-name")).to_have_text(TAGGED)
    expect(visitor.row(TAGGED)).to_have_attribute("aria-current", "true")
    expect(page).to_have_url(re.compile(rf"/\?song={tagged}$"))
    assert len(visitor.uploads()) == 1

    # Another song has another address.
    visitor.pick(files["untagged"])
    expect(page.locator("#song-name")).to_have_text("Sin etiquetas", timeout=READY)
    untagged = visitor.row("Sin etiquetas").get_attribute("data-id")
    assert untagged != tagged
    expect(page).to_have_url(re.compile(rf"/\?song={untagged}$"))
    visitor.row(TAGGED).get_by_role("button", name="Open").click()
    expect(page).to_have_url(re.compile(rf"/\?song={tagged}$"))

    # A browser that was given the address opens the song it names.
    other = visit(path=f"/?song={untagged}")
    expect(other.page.locator("#player")).to_be_visible(timeout=READY)
    expect(other.page.locator("#song-name")).to_have_text("Sin etiquetas")
    expect(other.row("Sin etiquetas")).to_have_attribute("aria-current", "true")
    assert other.uploads() == []

    # An address that names a song the library does not have says so, and becomes the plain one.
    lost = visit(path=f"/?song={'0' * 32}")
    expect(lost.page.locator("#nothing-text")).to_have_text("This song is not in the library.")
    expect(lost.page.locator("#player")).to_be_hidden()
    expect(lost.page).to_have_url(re.compile(r"/$"))
    # So does one that names nothing a song could be called.
    odd = visit(path="/?song=../../etc/passwd")
    expect(odd.page.locator("#nothing-text")).to_have_text("This song is not in the library.")
    expect(odd.page).to_have_url(re.compile(r"/$"))

    # A song deleted in another browser is closed here, and the address is the plain one again.
    row = visitor.row("Sin etiquetas")
    row.get_by_role("button", name="Delete").click()
    row.get_by_role("button", name="Yes, delete").click()
    expect(other.page.locator("#player")).to_be_hidden(timeout=10_000)
    expect(other.page.locator("#nothing-text")).to_have_text("The song was deleted.")
    expect(other.page).to_have_url(re.compile(r"/$"))


INK = """([x, y]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const at = (px, py) => canvas.getContext('2d').getImageData(Math.round(px * scale), Math.round(py * scale), 1, 1).data
    // How tall the ink is through this point, and what is at the point itself.
    let tall = 0
    for (let up = 0; at(x, y - up)[3] > 128; up++) tall++
    for (let down = 1; at(x, y + down)[3] > 128; down++) tall++
    const [red, green, blue, alpha] = at(x, y)
    return { tall: tall / scale, inked: alpha > 128, light: red + green + blue }
}"""


def test_every_beat_has_its_own_mark_and_its_count_in_rows_of_four_ochos_in_light_and_in_dark(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    result = visitor.result(TAGGED)
    counts, marks = visitor.counts(), visitor.marks()
    # The count on screen is the one of the analysis, one for every beat.
    assert counts == result["count"] and len(marks) == len(result["beats"])
    assert set(counts) == set(range(1, 9))

    # A row holds four ochos: it starts on the first beat of one and has no fifth.
    assert page.locator("#map").get_attribute("data-per-row") == "4"
    rows = {}
    for beat, (x, y) in enumerate(marks):
        rows.setdefault(y, []).append(beat)
    assert len(rows) >= 2, "the test song must fill its first row"
    for beats in rows.values():
        starts = [beat for beat in beats if beat == 0 or counts[beat] != counts[beat - 1] + 1]
        assert starts[0] == beats[0] and len(starts) <= 4, beats
        # Neighbours are 20 pixels apart or more, and further apart from one ocho to the next.
        gaps = [marks[beat][0] - marks[beat - 1][0] for beat in beats[1:]]
        assert min(gaps) >= 20, gaps
        for beat, gap in zip(beats[1:], gaps):
            assert (gap > min(gaps)) == (beat in starts), (beat, gap)

    seen = {}
    for scheme in ("light", "dark"):
        # The page follows the system, and draws the song again in the colours of each.
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        inks = [page.evaluate(INK, mark) for mark in marks]
        assert all(ink["inked"] for ink in inks), scheme
        # Count 1 is told apart by its form: an upright bar, where the others are squares.
        for beat, ink in enumerate(inks):
            assert (ink["tall"] > 15) == (counts[beat] == 1), (scheme, beat, ink)
            assert ink["tall"] >= 7
        # Between two marks there is no ink.
        between = page.evaluate(INK, [(marks[1][0] + marks[2][0]) / 2, marks[1][1]])
        assert not between["inked"], scheme
        ground = page.evaluate("getComputedStyle(document.body).backgroundColor")
        seen[scheme] = (sum(int(part) for part in ground[4:-1].split(",")), inks[0]["light"])
    # Dark marks on a light ground, then light marks on a dark one.
    assert seen["light"][0] > seen["light"][1] and seen["dark"][0] < seen["dark"][1], seen
    # No section is written: the text where the song is shown is the count, which is not
    # there before the first beat, the tempo and the time.
    assert page.locator("#player").inner_text().split() == ["–", page.locator("#bpm").inner_text(), "BPM", "0:00"]


# What the large view has drawn at the place of a count, 1 to 8: the ink down the middle
# of the place, how tall and how wide it is, its colour just inside its top and in its
# middle, and whether something is written under it. Colours are as the eye gets them,
# on the band behind the canvas: ink that is not solid lets the band through.
LARGE = """(place) => {
    const canvas = document.getElementById('now')
    const scale = canvas.width / canvas.clientWidth
    const band = getComputedStyle(canvas.parentElement).backgroundColor.match(/[0-9.]+/g).slice(0, 3).map(Number)
    const wide = Math.floor(canvas.width / 8)
    const high = canvas.height
    const cell = canvas.getContext('2d').getImageData(Math.round(((place - 1) * canvas.width) / 8), 0, wide, high).data
    const at = (x, y) => cell.subarray(4 * (y * wide + x), 4 * (y * wide + x) + 4)
    const alpha = (x, y) => at(x, y)[3]
    const seen = (x, y) => band.map((ground, part) => Math.round((at(x, y)[part] * alpha(x, y) + ground * (255 - alpha(x, y))) / 255))
    const middle = wide >> 1
    let top = 0
    while (top < high && alpha(middle, top) < 32) top++
    if (top === high) return { empty: cell.every((part, n) => n % 4 !== 3 || part === 0) }
    let bottom = top
    while (bottom + 1 < high && alpha(middle, bottom + 1) >= 32) bottom++
    const row = (top + bottom) >> 1
    let left = middle
    let right = middle
    while (left > 0 && alpha(left - 1, row) >= 32) left--
    while (right + 1 < wide && alpha(right + 1, row) >= 32) right++
    let under = false
    for (let y = bottom + 3; y < high && !under; y++) for (let x = 0; x < wide && !under; x++) under = alpha(x, y) > 128
    return {
        empty: false,
        tall: (bottom - top + 1) / scale,
        across: (right - left + 1) / scale,
        edge: seen(middle, top + Math.round(3 * scale)),
        middle: seen(middle, row),
        under,
        band,
    }
}"""


def contrast(one, other):
    """The contrast of two colours, each three numbers up to 255, as WCAG counts it."""

    def luminance(colour):
        parts = [part / 255 for part in colour]
        red, green, blue = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in parts]
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    dark, light = sorted((luminance(one), luminance(other)))
    return (light + 0.05) / (dark + 0.05)


def test_the_large_view_draws_the_ocho_that_is_sounding_in_light_and_in_dark(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    counts = visitor.counts()
    # A whole ocho with the playing position on its count 4: three of its beats have
    # sounded, one is sounding and four are to come.
    first = next(beat for beat in range(len(counts) - 7) if counts[beat : beat + 8] == list(range(1, 9)))
    visitor.press_beat(first + 3)
    expect(page.locator("#now")).to_have_attribute("data-ocho", f"{first} {first + 7}")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(first + 3))

    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        places = [page.evaluate(LARGE, place) for place in range(1, 9)]
        # Every beat of the ocho is drawn at the place of its count, with its count under it.
        assert not any(place["empty"] for place in places), scheme
        assert all(place["under"] for place in places), scheme
        band = places[0]["band"]
        sounded, lit, coming = places[:3], places[3], places[4:]
        # A beat that has sounded is fainter than one to come, and still a mark: it has a
        # contrast of 3 to 1 or more against the band.
        faint = [contrast(place["middle"], band) for place in sounded]
        full = [contrast(place["middle"], band) for place in coming]
        assert min(faint + full) >= 3, (scheme, [round(ratio, 2) for ratio in faint + full])
        assert max(faint) < min(full), (scheme, faint, full)
        # Count 1 is an upright bar and the others are squares, whether they have sounded or not.
        assert sounded[0]["tall"] > 2 * sounded[0]["across"], (scheme, sounded[0])
        for place in sounded[1:] + coming:
            assert abs(place["tall"] - place["across"]) <= 1.5, (scheme, place)
        # The beat that is sounding has the large square, with its own mark inside it.
        side = coming[0]["tall"]
        assert lit["tall"] > 3 * side and lit["across"] > 3 * side, (scheme, lit)
        assert contrast(lit["edge"], band) >= 3 and contrast(lit["middle"], lit["edge"]) >= 3, (scheme, lit)

    # An ocho of fewer than 8 beats leaves the other places empty. Its fifth beat is set
    # to count 1, which cuts it to a bar.
    visitor.press_beat(first + 4)
    page.locator("#one").click()
    expect(page.locator("#map")).to_have_attribute("data-by-hand", str(first + 4))
    visitor.press_beat(first + 1)
    expect(page.locator("#now")).to_have_attribute("data-ocho", f"{first} {first + 3}")
    assert [page.evaluate(LARGE, place)["empty"] for place in range(1, 9)] == [False] * 4 + [True] * 4


def test_count_1_is_set_by_hand_shown_in_every_browser_and_taken_back(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song_id = visitor.row(TAGGED).get_attribute("data-id")
    result = visitor.result(TAGGED)
    before, beats = result["count"], result["beats"]
    # Another browser has the song open too.
    other = visit(viewport={"width": 1280, "height": 720})
    other.row(TAGGED).get_by_role("button", name="Open").click()
    expect(other.page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")
    expect(song).to_have_attribute("data-by-hand", "")

    # A beat the analysis counts as 5, well inside the song: the user says it is count 1.
    beat = next(n for n in range(16, len(before)) if before[n] == 5)
    visitor.press_beat(beat)
    expect(page.locator("#count")).to_have_text("5")
    expect(page.locator("#one")).to_have_text("Count 1 here")
    page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", str(beat))
    expect(page.locator("#count")).to_have_text("1")
    expect(page.locator("#one")).to_have_text("Not count 1")
    # Before it the count is the analysis's, and from it the count runs in eights.
    after = before[:beat] + [(n - beat) % 8 + 1 for n in range(beat, len(before))]
    assert visitor.counts() == after
    # The ocho before it was cut to a bar, and the large view shows the ocho that starts here.
    assert after[beat - 4 : beat + 1] == [1, 2, 3, 4, 1]
    expect(page.locator("#now")).to_have_attribute("data-ocho", f"{beat} {min(beat + 7, len(beats) - 1)}")
    assert visitor.changes_of_count() == [("PUT", f"/api/songs/{song_id}/ones?at={str(beats[beat]).removesuffix('.0')}")]
    # A count 1 set by hand has a cap across its top, and the other count 1s have none.
    # Looked at with the playing position elsewhere, so that neither mark is the lit one.
    visitor.press_beat(beat + 2)
    x, y = visitor.marks()[beat]
    x_other, y_other = visitor.marks()[beat - 4]
    assert page.evaluate(INK, [x + 7, y - 8])["inked"] and not page.evaluate(INK, [x_other + 7, y_other - 8])["inked"]
    assert page.evaluate(INK, [x_other, y_other])["tall"] > 15

    # The other browser learns of it from the list, with the song open.
    expect(other.page.locator("#map")).to_have_attribute("data-by-hand", str(beat), timeout=6000)
    assert other.counts() == after
    # And a browser that opens the song later finds it there.
    late = visit()
    late.row(TAGGED).get_by_role("button", name="Open").click()
    expect(late.page.locator("#map")).to_have_attribute("data-by-hand", str(beat), timeout=READY)

    # A second one, set in the other browser, holds from its beat on. The first holds up to it.
    second = beat + 12
    other.press_beat(second)
    other.page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", f"{beat} {second}", timeout=6000)
    both = after[:second] + [(n - second) % 8 + 1 for n in range(second, len(before))]
    assert visitor.counts() == both and both[second - 4 : second + 1] == [1, 2, 3, 4, 1]

    # On a beat that was set by hand, the control takes it back.
    visitor.press_beat(second)
    expect(page.locator("#one")).to_have_text("Not count 1")
    page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", str(beat))
    assert visitor.counts() == after
    visitor.press_beat(beat)
    page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", "")
    expect(page.locator("#one")).to_have_text("Count 1 here")
    assert visitor.counts() == before
    expect(other.page.locator("#map")).to_have_attribute("data-by-hand", "", timeout=6000)
    assert other.counts() == before
    assert [method for method, url in visitor.changes_of_count()] == ["PUT", "DELETE", "DELETE"]


def test_a_list_asked_for_before_a_count_1_was_set_does_not_take_it_back(visit, files):
    """The list is asked for every two seconds, and an answer may be late."""
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beat = 20
    visitor.press_beat(beat)

    # The next answer to the list is kept back, as it is now: without a count 1. The
    # lists after it pass, the one the page asks for after its own change among them.
    held, late, closed = [], [], []

    def on_list(route):
        if not held:
            held.append(route)
        elif closed:
            late.append(route)
        else:
            route.continue_()

    page.route("**/api/songs", on_list)
    for _ in range(40):
        if held:
            break
        page.wait_for_timeout(100)
    old = held[0].fetch()
    assert all(song["ones"] == [] for song in old.json())
    page.locator("#one").click()
    expect(page.locator("#map")).to_have_attribute("data-by-hand", str(beat))
    expect(page.locator("#one")).to_have_text("Not count 1")
    page.wait_for_timeout(500)

    # The old answer arrives now, and no newer one can put things right behind it.
    closed.append(True)
    held[0].fulfill(response=old)
    for _ in range(8):
        page.wait_for_timeout(100)
        assert page.locator("#map").get_attribute("data-by-hand") == str(beat)
    for route in late:
        route.continue_()
    page.unroute("**/api/songs")


def test_a_song_is_renamed_in_its_row_and_in_the_top_bar(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    row = visitor.row(TAGGED)
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    other = visit()
    expect(other.row(TAGGED)).to_be_visible()

    # In the row: the field holds the name, and Enter keeps the new one.
    row.get_by_role("button", name="Rename").click()
    field = page.locator("#songs input")
    expect(field).to_be_focused()
    expect(field).to_have_value(TAGGED)
    field.fill("  Grupo Extra -\tMe Emborracharé  ")
    field.press("Enter")
    renamed = visitor.row("Grupo Extra - Me Emborracharé")
    expect(renamed).to_be_visible()
    expect(page.locator("#songs input")).to_have_count(0)
    expect(renamed.get_by_role("button", name="Rename")).to_be_focused()
    # The open song shows its new name in the top bar, and every browser gets it.
    expect(page.locator("#song-name")).to_have_text("Grupo Extra - Me Emborracharé")
    expect(other.row("Grupo Extra - Me Emborracharé")).to_be_visible(timeout=10_000)
    assert len(visitor.renamings()) == 1

    # Escape leaves the name as it was, and nothing is sent.
    renamed.get_by_role("button", name="Rename").click()
    page.locator("#songs input").fill("Not this")
    page.locator("#songs input").press("Escape")
    expect(visitor.row("Grupo Extra - Me Emborracharé")).to_be_visible()
    assert len(visitor.renamings()) == 1
    # A name of spaces is refused where it was typed, and the field stays.
    renamed.get_by_role("button", name="Rename").click()
    page.locator("#songs input").fill("   ")
    page.locator("#songs input").press("Enter")
    expect(page.locator("#songs li .note")).to_have_text("A song needs a name.")
    expect(page.locator("#songs li .note")).to_contain_class("refused")
    expect(page.locator("#songs input")).to_be_focused()
    page.get_by_role("button", name="Cancel").click()
    assert len(visitor.renamings()) == 1

    # In the top bar, with a name that looks like markup and one that is too long.
    page.locator("#rename-open").click()
    field = page.locator("#title input")
    expect(field).to_be_focused()
    field.fill("<i>cursiva</i> " + "ñ" * 300)
    page.locator("#title").get_by_role("button", name="Save").click()
    name = "<i>cursiva</i> " + "ñ" * 185
    expect(page.locator("#song-name")).to_have_text(name)
    expect(visitor.row(name)).to_be_visible()
    expect(other.row(name)).to_be_visible(timeout=10_000)
    assert page.locator("i").count() == 0 and other.page.locator("i").count() == 0
    assert len(visitor.renamings()) == 2
    assert other.renamings() == []


def test_the_keyboard_plays_moves_the_position_and_reaches_every_control(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    # The song opened by itself: the keyboard is on Play.
    expect(page.locator("#play")).to_be_focused()

    # Space plays and pauses, from anywhere that has no use of its own for the key.
    page.locator("#seek").focus()
    page.keyboard.press("Space")
    expect(page.locator("#play")).to_have_text("Pause")
    page.keyboard.press("Space")
    expect(page.locator("#play")).to_have_text("Play")

    # The position control: the song is silent while it is dragged, and goes on from
    # where it is let go.
    page.keyboard.press("Space")
    bar = page.locator("#seek").bounding_box()
    page.mouse.move(bar["x"] + bar["width"] * 0.3, bar["y"] + bar["height"] / 2)
    page.mouse.down()
    expect(page.locator("#play")).to_have_text("Play")
    page.mouse.move(bar["x"] + bar["width"] * 0.6, bar["y"] + bar["height"] / 2, steps=8)
    assert 13 < float(page.locator("#seek").input_value()) < 16.5
    page.mouse.up()
    expect(page.locator("#play")).to_have_text("Pause")
    page.keyboard.press("Space")
    expect(page.locator("#play")).to_have_text("Play")
    assert 13 < float(page.locator("#seek").input_value()) < 19

    # The arrows move the position by a beat.
    visitor.press_beat(10)
    expect(page.locator("#now")).to_have_attribute("data-lit", "10")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    expect(page.locator("#now")).to_have_attribute("data-lit", "12")
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#now")).to_have_attribute("data-lit", "11")
    page.locator("#loop-start").focus()
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#now")).to_have_attribute("data-lit", "10")
    # With Shift they move by an ocho: on to the first beat of the next one, back to the
    # first beat of this one, and from there to the one before.
    counts = visitor.counts()
    starts = [beat for beat, count in enumerate(counts) if beat == 0 or count != counts[beat - 1] + 1]
    here = max(start for start in starts if start <= 10)
    page.keyboard.press("Shift+ArrowRight")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(starts[starts.index(here) + 1]))
    page.keyboard.press("Shift+ArrowLeft")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(here))
    visitor.press_beat(here + 2)
    page.keyboard.press("Shift+ArrowLeft")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(here))
    visitor.press_beat(10)
    expect(page.locator("#now")).to_have_attribute("data-lit", "10")
    page.locator("#loop-start").focus()

    # The loop, from the keyboard alone: its two ends, then its switch.
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.locator("#loop-end").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#loop")).to_be_checked()
    page.locator("#loop").focus()
    page.keyboard.press("Space")
    expect(page.locator("#loop")).not_to_be_checked()
    expect(page.locator("#play")).to_have_text("Play")

    # In a field, the keys type: a space does not start the song.
    visitor.row(TAGGED).get_by_role("button", name="Rename").focus()
    page.keyboard.press("Enter")
    page.keyboard.type("a b")
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#songs input")).to_have_value("a b")
    expect(page.locator("#play")).to_have_text("Play")
    expect(page.locator("#now")).to_have_attribute("data-lit", "13")
    page.keyboard.press("Escape")

    # Tab goes through every control, and each one shows where the keyboard is.
    # From the top of the page: a press on its heading is where the keyboard starts from.
    page.locator("h1").click()
    reached = {}
    for _ in range(24):
        page.keyboard.press("Tab")
        on = page.evaluate(
            """() => {
                const on = document.activeElement
                // The file input is driven by its label, which shows the ring for it.
                const shown = getComputedStyle(on.id === 'file' ? document.querySelector('label[for="file"]') : on)
                return { name: on.id || on.dataset.focus || on.tagName, ring: shown.outlineStyle !== 'none' && parseFloat(shown.outlineWidth) >= 2 }
            }"""
        )
        # After the last control the keyboard leaves the page.
        if on["name"] not in ("BODY", "HTML"):
            reached[on["name"]] = on["ring"] and reached.get(on["name"], True)
    controls = {"rename-open", "file", "rename", "delete", "play", "seek", "loop", "loop-start", "loop-end", "loop-clear", "one", "click"}
    assert controls <= set(reached), controls - set(reached)
    assert all(reached.values()), reached


def test_a_message_appears_beside_its_cause_and_the_list_says_which_song_is_open(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#song-name")).to_have_text(TAGGED, timeout=READY)
    visitor.pick(files["untagged"])
    expect(page.locator("#song-name")).to_have_text("Sin etiquetas", timeout=READY)
    first, second = visitor.row(TAGGED), visitor.row("Sin etiquetas")
    expect(second).to_have_attribute("aria-current", "true")
    expect(first).not_to_have_attribute("aria-current", "true")
    # What adding a song says is beside the control that adds one.
    assert page.locator(".add #message").count() == 1

    # A song that cannot be opened says so in its own row, and the open song stays.
    page.route("**/api/songs/*/sound", lambda route: route.fulfill(status=404, body="Not found\n"))
    first.get_by_role("button", name="Open").click()
    expect(first.locator(".note")).to_have_text(f"{TAGGED} could not be opened.")
    expect(first.locator(".note")).to_contain_class("refused")
    expect(second.locator(".note")).to_have_count(0)
    expect(page.locator("#song-name")).to_have_text("Sin etiquetas")
    expect(second).to_have_attribute("aria-current", "true")

    # Opened for good, it is the one the list marks, and its row says nothing more.
    page.unroute("**/api/songs/*/sound")
    first.get_by_role("button", name="Open").click()
    expect(page.locator("#song-name")).to_have_text(TAGGED)
    expect(first).to_have_attribute("aria-current", "true")
    expect(first).to_contain_text("Open now")
    expect(first.locator(".note")).to_have_count(0)
    expect(second).not_to_have_attribute("aria-current", "true")
    expect(second.get_by_role("button", name="Open")).to_be_visible()

    # A song deleted in another browser closes here, and the page says why.
    other = visit()
    row = other.row(TAGGED)
    row.get_by_role("button", name="Delete").click()
    expect(row.get_by_role("button", name="Keep")).to_be_focused()
    row.get_by_role("button", name="Yes, delete").click()
    expect(page.locator("#player")).to_be_hidden(timeout=10_000)
    expect(page.locator("#nothing-text")).to_have_text("The song was deleted.")
    expect(page.locator("#title")).to_be_hidden()
    expect(page.locator("#play")).to_be_disabled()


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
    assert int(other.page.locator("#now").get_attribute("data-beats")) >= 40
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
        (files["wav"], "This is not an mp3, m4a or opus file."),
        (files["text"], "This is not an mp3, m4a or opus file."),
        (files["vorbis"], "This is not an mp3, m4a or opus file."),
        (files["broken"], "The browser cannot decode this file."),
    ]:
        visitor.pick(file)
        expect(message).to_have_text(said)
        expect(message).to_contain_class("refused")
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


@pytest.mark.parametrize("file", ["short", "short opus"])
def test_a_song_that_is_too_short_is_refused_by_the_page(visit, files, file):
    visitor = visit()
    visitor.pick(files[file])
    expect(visitor.page.locator("#message")).to_have_text("This song is shorter than 20 seconds.")
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


@pytest.mark.parametrize("file", ["long", "long opus"])
def test_a_song_that_is_too_long_is_refused_by_the_page(visit, files, file):
    visitor = visit()
    visitor.pick(files[file])
    expect(visitor.page.locator("#message")).to_have_text("This song is longer than 15 minutes.", timeout=READY)
    expect(visitor.rows()).to_have_count(0)
    assert visitor.uploads() == []


def test_an_opus_file_is_taken_like_an_mp3_or_an_m4a(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["opus"])
    # The name comes from the tags of the file, and the song goes through its states.
    row = visitor.row(IN_OPUS)
    expect(row).to_have_attribute("data-state", "ready", timeout=READY)
    expect(row.locator(".state")).to_have_text("0:23, ready")
    # What is sent is the same as for any other file: plain samples at 44.1 kHz.
    assert len(visitor.uploads()) == 1
    sent = dict(part.split("=") for part in visitor.uploads()[0].split("?")[1].split("&"))
    assert sent["rate"] == "44100" and abs(int(sent["frames"]) / RATE - 23.5) < 0.1

    # It opens by itself and has its beats, at the tempo of the test song.
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    expect(page.locator("#song-name")).to_have_text(IN_OPUS)
    assert 42 <= len(visitor.beats(IN_OPUS)) <= 48
    assert abs(int(page.locator("#bpm").inner_text()) / BPM - 1) <= 0.04

    # Picked again, it is found in the library and not sent again.
    other = visit()
    other.pick(files["opus"])
    expect(other.page.locator("#message")).to_have_text("This song is already in the library.")
    expect(other.page.locator("#song-name")).to_have_text(IN_OPUS)
    assert other.uploads() == []


def test_a_name_is_shown_as_plain_text(visit, files):
    visitor = visit()
    visitor.pick(files["markup"])
    name = "<img src=x onerror=document.title='broken'><b>bold</b>"
    expect(visitor.row(name)).to_have_attribute("data-state", "ready", timeout=READY)
    expect(visitor.page.locator("#song-name")).to_have_text(name, timeout=READY)
    assert visitor.page.locator("img, b").count() == 0
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
