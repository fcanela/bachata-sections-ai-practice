"""End-to-end tests: whole flows through the page, in a real browser, against the real program.

A song is drawn on two canvases: the ocho that is sounding, and the whole song with a
plate for each bar. The page says in attributes of those canvases which beat and which
bar are lit and where the plates are. The tests find a bar through them, and read what
was drawn from the pixels of the canvas.

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
IN_ROWS = "Los Tests - Canción de dos filas"


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
        # Long enough for more than eight ochos: its plates fill a row and start another.
        "rows": a_song(folder / "track03.m4a", 44.5, "title=Canción de dos filas", "artist=Los Tests"),
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

    def bars(self):
        """The first and the last beat of every bar, as the song on screen says it."""
        firsts = [int(beat) for beat in self.page.locator("#map").get_attribute("data-bars").split()]
        return list(zip(firsts, [first - 1 for first in firsts[1:]] + [len(self.counts()) - 1]))

    def plates(self):
        """The plate of every bar inside the canvas of the song: its left, top, width and height."""
        return json.loads(self.page.locator("#map").get_attribute("data-plates"))

    def changes_of_count(self):
        return [(method, url) for method, url in self.sent if url.endswith("/ones") or "/ones?" in url]

    def lit(self):
        """The beat whose mark is lit in the large view, or -1 before the first one."""
        lit = self.page.locator("#now").get_attribute("data-lit")
        return int(lit) if lit else -1

    def lit_bar(self):
        """The bar the song says is lit, as its place among the bars, or -1 before the first beat."""
        lit = self.page.locator("#map").get_attribute("data-lit")
        return int(lit) if lit else -1

    def place(self, x, y):
        """Where a point of the canvas of the song is on the page. The canvas may start a
        part of a pixel down the page: the browser then paints it on the nearest whole one."""
        box = self.page.locator("#map").bounding_box()
        return int(box["x"] + 0.5) + x, int(box["y"] + 0.5) + y

    def middle_of(self, bar):
        x, y, wide, high = self.plates()[bar]
        return x + wide // 2, y + high // 2

    def press_at(self, x, y, **how):
        self.page.mouse.click(*self.place(x, y), **how)

    def press_bar(self, bar):
        self.press_at(*self.middle_of(bar))

    def press_beat(self, beat):
        """Goes to a beat as the owner does: a press on the plate of its bar, then the right
        arrow once for each beat after the bar's first."""
        bars = self.bars()
        bar = max(n for n, (first, last) in enumerate(bars) if first <= beat)
        self.press_bar(bar)
        for _ in range(beat - bars[bar][0]):
            self.page.keyboard.press("ArrowRight")
        expect(self.page.locator("#now")).to_have_attribute("data-lit", str(beat))

    def drag_bars(self, start, end, let_go=True):
        """Presses on one bar and lets go on another, which may be an earlier one."""
        self.page.mouse.move(*self.place(*self.middle_of(start)))
        self.page.mouse.down()
        self.page.mouse.move(*self.place(*self.middle_of(end)), steps=6)
        if let_go:
            self.page.mouse.up()

    def drawn(self, box):
        """What the canvas of the song has in a box [x, y, wide, high]: how many pixels it
        has, how many of them have ink, and how many have each colour, a colour being
        (red, green, blue, alpha)."""
        seen = self.page.evaluate(DRAWN, box)
        seen["colours"] = {tuple(int(part) for part in colour.split()): pixels for colour, pixels in seen["colours"].items()}
        return seen

    def pixel(self, x, y):
        """The colour of one point of the canvas of the song: (red, green, blue, alpha)."""
        return next(iter(self.drawn([x, y, 0, 0])["colours"]))

    def colour(self, name):
        """A colour of the page as it is now, in light or in dark: a custom property of
        the root, as the solid colour a canvas makes of it."""
        value = self.page.evaluate("name => getComputedStyle(document.documentElement).getPropertyValue(name).trim()", name)
        assert re.fullmatch("#[0-9a-f]{6}", value), (name, value)
        return (*(int(value[at : at + 2], 16) for at in (1, 3, 5)), 255)

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

# What the canvas of the song has drawn in a box, in the page's units: see Visitor.drawn().
# A box with no width or no height is one pixel.
DRAWN = """([x, y, wide, high]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const size = (length) => Math.max(1, Math.round(length * scale))
    const data = canvas.getContext('2d').getImageData(Math.round(x * scale), Math.round(y * scale), size(wide), size(high)).data
    const colours = {}
    let inked = 0
    for (let at = 0; at < data.length; at += 4) {
        if (data[at + 3] > 0) inked++
        const colour = data.slice(at, at + 4).join(' ')
        colours[colour] = (colours[colour] || 0) + 1
    }
    return { pixels: data.length / 4, inked, colours }
}"""

# The sizes the song is drawn with, in pixels: a plate is 30 high, the two plates of an
# ocho are 2 apart and two ochos 14, and the first plate of a row stands 80 from the left.
HIGH, INSIDE, BETWEEN, LEFT = 30, 2, 14, 80


def clock(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def bars_of(counts):
    """The bars a count makes, each (first, last): one starts at the first beat of the song,
    at every count 5, and at every beat whose count does not go on from the beat before."""
    firsts = [beat for beat, count in enumerate(counts) if beat == 0 or count == 5 or count != counts[beat - 1] + 1]
    return list(zip(firsts, [first - 1 for first in firsts[1:]] + [len(counts) - 1]))


def ochos_from(counts):
    """The beats an ocho starts on."""
    return {beat for beat, count in enumerate(counts) if beat == 0 or count != counts[beat - 1] + 1}


def rows_of(plates):
    """The bars of every row, top to bottom."""
    rows = {}
    for bar, (x, y, wide, high) in enumerate(plates):
        rows.setdefault(y, []).append(bar)
    return [rows[y] for y in sorted(rows)]


def whole_ocho(visitor, row=0, after=1):
    """The two bars of a whole ocho in a row, and the first bar of the ocho after it, also
    whole: the places of three bars side by side. Not the first ochos of the row."""
    counts, bars = visitor.counts(), visitor.bars()
    whole = lambda bar, count: bars[bar][1] - bars[bar][0] == 3 and counts[bars[bar][0]] == count
    inside = rows_of(visitor.plates())[row]
    return next(bar for bar in inside[after:-2] if whole(bar, 1) and whole(bar + 1, 5) and whole(bar + 2, 1))


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

    # A press on a bar of the song and the arrows move the playing position onto a beat.
    visitor.press_beat(24)
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
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")

    # Dragging across two bars marks them and switches the loop on. It is four seconds long.
    bars = visitor.bars()
    start = whole_ocho(visitor)
    first, last = bars[start][0], bars[start + 1][1]
    assert last - first == 7
    visitor.drag_bars(start, start + 1)
    expect(page.locator("#loop")).to_be_checked()
    expect(page.locator("#map")).to_have_attribute("data-range", f"{first} {last}")
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[first])} to {clock(beats[last + 1] - 0.02)}")
    length = beats[last + 1] - beats[first]

    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    needs_sound(page)
    for _ in range(21):
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
    visitor.drag_bars(start, start + 1)
    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    page.locator("#loop-clear").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "playing")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(last + 2), timeout=10_000)
    page.locator("#play").click()
    assert [sound["loop"] for sound in page.evaluate("window.started.splice(0)") if sound["seconds"] > 1] == [True, False]

    # The two ends can also be set at the playing position, one at a time: on any beat,
    # also inside a bar.
    visitor.press_beat(21)
    page.locator("#loop-start").click()
    expect(page.locator("#loop-range")).to_have_text(f"From {clock(beats[21])}")
    expect(page.locator("#loop")).to_be_disabled()
    visitor.press_beat(23)
    page.locator("#loop-end").click()
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[21])} to {clock(beats[24] - 0.02)}")
    expect(page.locator("#map")).to_have_attribute("data-range", "21 23")
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
    start = whole_ocho(visitor)
    first, last = visitor.bars()[start][0], visitor.bars()[start + 1][1]
    visitor.drag_bars(start, start + 1)
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

    bars = visitor.bars()
    start = whole_ocho(visitor)
    marked = f"{bars[start][0]} {bars[start + 1][1]}"
    visitor.drag_bars(start, start + 1)
    expect(page.locator("#loop")).to_be_checked()
    expect(song).to_have_attribute("data-range", marked)
    # The range is on the canvas: its bracket left of its first plate, its band above the
    # plate, and nothing where its dashed rule would be but the band. The bar is lit, and
    # its block reaches 6 above its plate: the band is read above that.
    x, y, wide, high = visitor.plates()[start]
    bracket, band, rule = (x - 7, y + 15), (x + wide // 2, y - 7), [x + 12, y - 9, wide - 12, 2]
    loop = visitor.colour("--loop")
    page.mouse.move(0, 0)
    assert visitor.pixel(*bracket) == loop
    assert 0 < visitor.pixel(*band)[3] < 255
    assert loop not in visitor.drawn(rule)["colours"]

    # Switched off, the loop keeps its range, with two dashed rules in place of the band:
    # it can be switched on again.
    page.locator("#loop").uncheck()
    expect(song).to_have_attribute("data-range", marked)
    assert visitor.pixel(*bracket) == loop
    assert visitor.pixel(*band)[3] == 0
    dashed = visitor.drawn(rule)
    assert 0 < dashed["inked"] < dashed["pixels"], dashed
    expect(clear).to_be_enabled()
    # Cleared, the range is gone from the song and from the transport bar.
    clear.click()
    expect(song).to_have_attribute("data-range", "")
    assert visitor.pixel(*bracket)[3] == 0 and visitor.drawn(rule)["inked"] == 0
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")
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
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")
    expect(clear).to_be_disabled()
    expect(page.locator("#loop-start")).to_be_focused()
    # A new range can be marked afterwards.
    visitor.drag_bars(start + 1, start + 2)
    expect(song).to_have_attribute("data-range", f"{bars[start + 1][0]} {bars[start + 2][1]}")
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


def test_every_bar_has_one_plate_with_its_count_on_it_and_nothing_else_in_light_and_in_dark(visit, files):
    # Two points of the canvas for every pixel of the page, as on a dense screen: a
    # figure then has pixels that are its colour and nothing else.
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light", device_scale_factor=2)
    page = visitor.page
    visitor.pick(files["rows"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    result = visitor.result(IN_ROWS)
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    # The count on screen is the one of the analysis, one for every beat. The bars are
    # the ones that count makes, and each has its plate.
    assert counts == result["count"] and set(counts) == set(range(1, 9))
    assert bars == bars_of(counts)
    assert len(plates) == len(bars) and len(rows_of(plates)) >= 2
    assert page.evaluate("document.getElementById('map').width / document.getElementById('map').clientWidth") == 2

    # Whole plates are all as wide as each other, and a short bar's plate is narrower in
    # the proportion of its beats. Every plate is 30 high.
    (whole,) = {wide for (x, y, wide, high), (first, last) in zip(plates, bars) if last - first == 3}
    for (x, y, wide, high), (first, last) in zip(plates, bars):
        assert wide == int(whole * (last - first + 1) / 4 + 0.5) and high == HIGH, (first, last, wide, high)

    # No beat has sounded, so no bar is lit, and the pointer is not on the song.
    assert visitor.lit_bar() == -1
    page.mouse.move(0, 0)
    size = page.locator("#map").bounding_box()
    seen = {}
    for scheme in ("light", "dark"):
        # The page follows the system, and draws the song again in the colours of each.
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        mark, quiet, ground, ink = (visitor.colour(name) for name in ("--mark", "--plate", "--ground", "--ink"))
        for box, (first, last) in zip(plates, bars):
            # A first bar and a second bar differ by their fill and by the colour of their count.
            fill, figure = (mark, ground) if counts[first] <= 4 else (quiet, ink)
            on = visitor.drawn(box)
            assert on["inked"] == on["pixels"], (scheme, first)
            assert max(on["colours"], key=on["colours"].get) == fill, (scheme, first, on["colours"])
            x, y, wide, high = box
            assert visitor.pixel(x, y) == fill and visitor.pixel(x + wide - 0.5, y + high - 0.5) == fill, (scheme, first)
            # Something is written on it in the colour of its count, unless it is too narrow.
            assert (figure in on["colours"]) == (wide >= 14), (scheme, first, on["colours"])
        # There is nothing else: right of the times of the rows, the ink is the plates.
        # So there is none in the 2 pixels inside an ocho, in the 14 between two ochos,
        # between two rows, or for a beat inside a bar.
        beside = visitor.drawn([LEFT - 10, 0, size["width"], size["height"]])
        assert beside["inked"] == 4 * sum(wide * high for x, y, wide, high in plates), scheme
        # Every row has its time, left of its first plate.
        for row in rows_of(plates):
            x, y, wide, high = plates[row[0]]
            assert visitor.drawn([0, y, LEFT - 10, high])["inked"] > 0, (scheme, row[0])
        seen[scheme] = (mark, quiet, ground)
    assert not set(seen["light"]) & set(seen["dark"]), seen
    # No section is written: the text where the song is shown is the count, which is not
    # there before the first beat, the tempo and the time.
    assert page.locator("#player").inner_text().split() == ["–", page.locator("#bpm").inner_text(), "BPM", "0:00"]


def test_a_row_holds_eight_ochos_and_a_short_ocho_moves_the_rest_of_its_row_left(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["rows"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")

    def rows_as_laid_out(most):
        """The rows, after a look at each: it starts in line on the first bar of an ocho,
        holds no more ochos than `most`, and has its plates 2 apart inside an ocho and 14
        apart between two."""
        counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
        starts = ochos_from(counts)
        rows = rows_of(plates)
        for n, row in enumerate(rows):
            ochos = [bar for bar in row if bars[bar][0] in starts]
            assert ochos[0] == row[0] and plates[row[0]][0] == LEFT, row
            # Every row but the last is full.
            assert len(ochos) == most if n + 1 < len(rows) else len(ochos) <= most, (n, len(ochos))
            for left, right in zip(row, row[1:]):
                gap = plates[right][0] - plates[left][0] - plates[left][2]
                assert gap == (BETWEEN if bars[right][0] in starts else INSIDE), (left, right, gap)
            # The rows are 62 apart, and the first is 28 from the top.
            assert plates[row[0]][1] == 28 + 62 * n
        assert song.bounding_box()["height"] == 28 + 62 * (len(rows) - 1) + HIGH + 28
        return rows

    # In a window 1280 wide a row holds eight ochos, with plates as wide as the room allows.
    expect(song).to_have_attribute("data-per-row", "8")
    rows = rows_as_laid_out(8)
    assert len(rows) >= 2, "the test song must fill its first row"
    bars, before = visitor.bars(), visitor.plates()
    whole = max(wide for x, y, wide, high in before)
    assert whole == min(96, (page.evaluate("document.getElementById('map').clientWidth") - 80 - 16 - 7 * 14 - 8 * 2) // 16)

    # A second bar of the first row is set to count 1: the bar before it is left alone, a
    # short ocho. The ochos after it in the row stand further left by the plate that is
    # not there, and the next row starts in line.
    start = whole_ocho(visitor)
    visitor.press_bar(start + 1)
    page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", str(bars[start + 1][0]))
    full = rows[0]
    rows = rows_as_laid_out(8)
    after = visitor.plates()
    assert visitor.bars() == bars
    assert after[start] == before[start]
    # The ocho that now starts on that bar stands where the ocho after it stood, less
    # the plate and the 2 pixels: and so does every ocho after it in the row.
    for bar in range(start + 1, rows[0][-1], 2):
        assert after[bar][0] == before[bar + 1][0] - whole - INSIDE, bar
    # The row has its eight ochos with one plate fewer, so the next row starts a bar earlier.
    assert len(rows[0]) == len(full) - 1 and after[rows[1][0]][:2] == [LEFT, 28 + 62]

    # A narrower window has room for four ochos a row.
    page.set_viewport_size({"width": 1100, "height": 720})
    expect(song).to_have_attribute("data-per-row", "4")
    rows_as_laid_out(4)


def test_the_bar_of_the_beat_that_is_sounding_is_lit_whole_and_no_other(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, now = page.locator("#map"), page.locator("#now")
    bars, plates = visitor.bars(), visitor.plates()

    def blocks():
        """The bars drawn as a block: with ink above the plate. No bar has a lid here."""
        return [bar for bar, (x, y, wide, high) in enumerate(plates) if visitor.pixel(x + wide // 2, y - 5)[3] > 0]

    # No bar is lit before the first beat.
    expect(song).to_have_attribute("data-by-hand", "")
    assert visitor.lit() == -1 and visitor.lit_bar() == -1
    assert blocks() == []

    # After a press on a plate that bar is lit, and no other.
    lit = whole_ocho(visitor)
    visitor.press_bar(lit)
    expect(now).to_have_attribute("data-lit", str(bars[lit][0]))
    expect(song).to_have_attribute("data-lit", str(lit))
    page.mouse.move(0, 0)
    x, y, wide, high = plates[lit]
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        block, figure, quiet = (visitor.colour(name) for name in ("--lit", "--lit-ink", "--plate"))
        # Its block reaches 5 beyond the box of its plate on each side, over the edge of
        # the plate beside it, and 6 above it and under it. No further.
        for point in ((x - 5, y + 15), (x + wide + 4, y + 15), (x + wide // 2, y - 6), (x + wide // 2, y + high + 5)):
            assert visitor.pixel(*point) == block, (scheme, point)
        for point in ((x - 6, y + 15), (x + wide // 2, y - 7), (x + wide // 2, y + high + 6)):
            assert visitor.pixel(*point)[3] == 0, (scheme, point)
        assert visitor.pixel(x + wide + 5, y + 15) == quiet, scheme
        # Its count is written on it in the colour the lit bar keeps for it.
        on = visitor.drawn([x, y, wide, high])["colours"]
        assert max(on, key=on.get) == block and figure in on, (scheme, on)
        assert blocks() == [lit], scheme

    # The right arrow moves the position by a beat. The lit bar stays for the beats of
    # the bar, and the song is not drawn again for them: the fourth press lights the next bar.
    page.evaluate(
        """() => {
            window.drawings = 0
            const clear = CanvasRenderingContext2D.prototype.clearRect
            CanvasRenderingContext2D.prototype.clearRect = function () {
                if (this.canvas.id === 'map') window.drawings++
                return clear.apply(this, arguments)
            }
        }"""
    )
    for on in (1, 2, 3):
        page.keyboard.press("ArrowRight")
        expect(now).to_have_attribute("data-lit", str(bars[lit][0] + on))
        assert visitor.lit_bar() == lit and blocks() == [lit]
    assert page.evaluate("window.drawings") == 0
    page.keyboard.press("ArrowRight")
    expect(now).to_have_attribute("data-lit", str(bars[lit + 1][0]))
    expect(song).to_have_attribute("data-lit", str(lit + 1))
    assert blocks() == [lit + 1]
    assert page.evaluate("window.drawings") == 1


def test_while_the_song_plays_the_lit_bar_is_the_bar_of_the_beat_the_large_view_lights(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    bars = visitor.bars()

    page.locator("#play").click()
    needs_sound(page)
    lit = set()
    for _ in range(24):
        page.wait_for_timeout(150)
        # Both are read in one look at the page, so no beat can start between the two.
        beat, bar = page.evaluate("['now', 'map'].map((id) => document.getElementById(id).dataset.lit)")
        if beat == "":
            assert bar == ""
            continue
        assert bars[int(bar)][0] <= int(beat) <= bars[int(bar)][1], (beat, bar)
        lit.add(int(bar))
    assert len(lit) >= 2, lit


def test_a_press_anywhere_on_a_bar_moves_the_position_to_its_first_beat(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["rows"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    now = page.locator("#now")
    bars, plates = visitor.bars(), visitor.plates()
    rows = rows_of(plates)
    # Two bars of one ocho and the first bar of the next.
    one, two, three = (whole_ocho(visitor) + n for n in range(3))
    x, y, wide, high = plates[one]
    middle = y + high // 2

    def reaches(bar, px, py, **how):
        visitor.press_at(px, py, **how)
        expect(now).to_have_attribute("data-lit", str(bars[bar][0]))

    # On the middle of a plate, and 2 pixels inside its left edge and its right edge.
    reaches(one, x + wide // 2, middle)
    reaches(two, plates[two][0] + 2, middle)
    reaches(one, x + wide - 3, middle)
    reaches(two, plates[two][0] + wide - 3, middle)
    reaches(one, x + 2, middle)
    # In the top row of pixels of a plate and in the bottom one.
    reaches(two, plates[two][0] + 5, y)
    reaches(one, x + 5, y + high - 1)

    # Between the two plates of an ocho, and between two ochos: the nearer bar.
    assert plates[two][0] == x + wide + INSIDE and plates[three][0] == plates[two][0] + wide + BETWEEN
    reaches(three, plates[three][0] + 5, middle)
    reaches(one, x + wide, middle)
    reaches(two, x + wide + 1, middle)
    reaches(three, plates[three][0] - 7, middle)
    reaches(two, plates[three][0] - 8, middle)

    # A row has the band from 16 above its plates to 16 under them, and the bands of two
    # rows meet: just above the second row's band the bar is one of the first row.
    reaches(three, plates[three][0] + 5, y - 16)
    reaches(one, x + 5, y + high + 15)
    under = next(bar for bar in rows[1] if plates[bar][0] <= x + 5 < plates[bar][0] + plates[bar][2])
    assert under != one
    reaches(under, x + 5, y + high + 16)
    reaches(one, x + 5, y - 10)

    # Where there is no bar nothing moves: left of a row, on its time; right of the last
    # plate of a row; above the band of the first row. Nor with another button.
    last = plates[rows[-1][-1]]
    assert last[0] + last[2] + 40 < page.locator("#map").bounding_box()["width"], "the last row must not be full"
    for point, how in (
        ((40, middle), {}),
        ((LEFT - 1, middle), {}),
        ((last[0] + last[2], last[1] + 15), {}),
        ((last[0] + last[2] + 30, last[1] + 15), {}),
        ((x + 5, y - 17), {}),
        ((plates[three][0] + 5, middle), {"button": "right"}),
    ):
        visitor.press_at(*point, **how)
        assert visitor.lit() == bars[one][0], (point, how)
    assert page.locator("#position").inner_text() == clock(visitor.beats(IN_ROWS)[bars[one][0]])
    assert page.locator("#map").get_attribute("data-range") == ""

    # The plate under the pointer has a faint halo, 4 larger than the plate on every
    # side. It goes when the pointer leaves, and it is not there while a press is held.
    tx, ty = plates[two][0] + wide // 2, y
    page.mouse.move(*visitor.place(tx, middle))
    assert 0 < visitor.pixel(tx, ty - 4)[3] < 255 and visitor.pixel(tx, ty - 5)[3] == 0
    assert 0 < visitor.pixel(tx, ty + high + 3)[3] < 255 and visitor.pixel(tx, ty + high + 4)[3] == 0
    page.mouse.down()
    assert visitor.pixel(tx, ty - 4)[3] == 0
    page.mouse.up()
    expect(now).to_have_attribute("data-lit", str(bars[two][0]))
    page.mouse.move(*visitor.place(plates[three][0] + 5, middle))
    assert visitor.pixel(plates[three][0] + 5, y - 4)[3] > 0
    page.mouse.move(0, 0)
    assert visitor.pixel(plates[three][0] + 5, y - 4)[3] == 0


def test_a_drag_marks_whole_bars_whichever_way_it_goes(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["rows"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, now = page.locator("#map"), page.locator("#now")
    beats = visitor.beats(IN_ROWS)
    bars, plates = visitor.bars(), visitor.plates()
    rows = rows_of(plates)
    start = whole_ocho(visitor)
    end = start + 3
    marked = f"{bars[start][0]} {bars[end][1]}"

    # From one bar to a later one: from the first beat of the earlier to the last beat
    # of the later. The loop is switched on, and the position moves to its start.
    visitor.press_bar(rows[-1][-1])
    visitor.drag_bars(start, end)
    expect(song).to_have_attribute("data-range", marked)
    expect(page.locator("#loop")).to_be_checked()
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[bars[start][0]])} to {clock(beats[bars[end][1] + 1] - 0.02)}")
    # A loop starts a moment before its first beat, as it did before the plates.
    assert visitor.lit() in (bars[start][0] - 1, bars[start][0])
    page.locator("#loop-clear").click()
    expect(song).to_have_attribute("data-range", "")

    # From one bar to an earlier one: the same range. While the press is held the bars
    # show as marked, with dashed rules and no band: the range is not played round yet.
    visitor.drag_bars(end, start, let_go=False)
    expect(song).to_have_attribute("data-range", marked)
    x, y, wide, high = plates[start + 1]
    assert visitor.pixel(x + wide // 2, y - 7)[3] == 0
    dashed = visitor.drawn([x, y - 9, wide, 2])
    assert 0 < dashed["inked"] < dashed["pixels"], dashed
    expect(page.locator("#loop")).to_be_disabled()
    page.mouse.up()
    expect(song).to_have_attribute("data-range", marked)
    expect(page.locator("#loop")).to_be_checked()
    assert 0 < visitor.pixel(x + wide // 2, y - 7)[3] < 255
    page.locator("#loop-clear").click()

    # Let go on the bar it started on, it is a press: nothing is marked, and the
    # position is on the first beat of that bar.
    visitor.drag_bars(end, start, let_go=False)
    page.mouse.move(*visitor.place(*visitor.middle_of(end)), steps=6)
    page.mouse.up()
    expect(song).to_have_attribute("data-range", "")
    expect(now).to_have_attribute("data-lit", str(bars[end][0]))
    expect(page.locator("#loop")).to_be_disabled()

    # A drag may leave the rows: it takes the nearest row, and in it the nearest bar.
    # Under the last row and right of it, that is the last bar of the song.
    box = song.bounding_box()
    page.mouse.move(*visitor.place(*visitor.middle_of(end)))
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] - 2, box["y"] + box["height"] + 30, steps=6)
    expect(song).to_have_attribute("data-range", f"{bars[end][0]} {len(beats) - 1}")
    # And left of the first row, on its time, the first bar of that row.
    page.mouse.move(box["x"] + 30, box["y"] + plates[0][1] + 15, steps=6)
    page.mouse.up()
    expect(song).to_have_attribute("data-range", f"0 {bars[end][1]}")
    page.locator("#loop-clear").click()


def test_a_marked_range_is_drawn_over_its_bars_whole_and_not_past_them(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["rows"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")
    bars, plates = visitor.bars(), visitor.plates()
    rows = rows_of(plates)
    loop = visitor.colour("--loop")

    def band(bar):
        """Whether the band is behind a plate: above it, clear of the block of a lit bar."""
        x, y, wide, high = plates[bar]
        return 0 < visitor.pixel(x + wide // 2, y - 7)[3] < 255

    def upright(bar, side):
        """Whether a bracket stands at a side of a plate, -1 for its left: 8 beyond it,
        and as high as the band. Its foot is turned inward."""
        x, y, wide, high = plates[bar]
        at = x - 8 if side < 0 else x + wide + 4
        solid = visitor.drawn([at, y - 8, 4, high + 16])["colours"] == {loop: 4 * (high + 16)}
        foot = visitor.drawn([at - 6 if side > 0 else at, y - 8, 10, 4])["colours"] == {loop: 40}
        assert solid == foot, (bar, side)
        return solid

    # A range of two ochos that runs over the end of the first row: from the first bar of
    # the last ocho of that row to the second bar of the first ocho of the next.
    counts = visitor.counts()
    start, end = rows[0][-2], rows[1][1]
    assert [counts[bars[bar][0]] for bar in range(start, end + 1)] == [1, 5, 1, 5] and bars[end][1] - bars[start][0] == 15
    visitor.drag_bars(start, end)
    expect(song).to_have_attribute("data-range", f"{bars[start][0]} {bars[end][1]}")
    # The position is in the range. It is put on a bar outside it, so that no bar of the
    # range is lit, and the pointer is taken off the song.
    page.locator("#loop").uncheck()
    visitor.press_bar(rows[0][0])
    page.locator("#loop").check()
    page.mouse.move(0, 0)
    # One run in each row, over the bars of the range and not past them.
    assert [bar for bar in range(len(bars)) if band(bar)] == list(range(start, end + 1))
    # A bracket where the range starts and where it ends, and none where a run only
    # meets the end of its row: there the band goes 8 beyond the plate.
    assert upright(start, -1) and upright(end, 1)
    assert not upright(rows[0][-1], 1) and not upright(rows[1][0], -1)
    for bar, side in ((rows[0][-1], 1), (rows[1][0], -1)):
        x, y, wide, high = plates[bar]
        inside, outside = (x + wide + 7, x + wide + 8) if side > 0 else (x - 8, x - 9)
        assert 0 < visitor.pixel(inside, y + 15)[3] < 255 and visitor.pixel(outside, y + 15)[3] == 0, (bar, side)
    # The plates stand on the band: each is whole, in its own colour.
    for bar in range(start, end + 1):
        assert visitor.pixel(plates[bar][0], plates[bar][1]) == visitor.colour("--mark" if bar % 2 == start % 2 else "--plate")
    page.locator("#loop-clear").click()
    assert not any(band(bar) for bar in range(len(bars)))

    # A range set with "Start here" and "End here" inside two bars is kept in beats, and
    # drawn over those bars whole. It starts and ends inside an ocho here: the band goes
    # 1 beyond the plate, and the plate stands on the bracket.
    first = next(bar for bar in rows[0][1:-3] if [counts[bars[bar + n][0]] for n in range(4)] == [5, 1, 5, 1])
    last = first + 3
    assert bars[last][1] - bars[first][0] == 15
    visitor.press_beat(bars[first][0] + 1)
    page.locator("#loop-start").click()
    visitor.press_beat(bars[last][0] + 2)
    page.locator("#loop-end").click()
    expect(song).to_have_attribute("data-range", f"{bars[first][0] + 1} {bars[last][0] + 2}")
    expect(page.locator("#loop")).to_be_checked()
    visitor.press_bar(rows[1][-1])
    page.mouse.move(0, 0)
    assert [bar for bar in range(len(bars)) if band(bar)] == list(range(first, last + 1))
    x, y, wide, high = plates[first]
    assert visitor.drawn([x - 1, y - 8, 1, high + 16])["colours"] == {loop: high + 16}
    assert visitor.pixel(x - 2, y + 15)[3] == 0 and visitor.pixel(x - 2, y - 7)[3] == 0
    assert visitor.drawn([x - 1, y - 8, 10, 4])["colours"] == {loop: 40}
    x, y, wide, high = plates[last]
    assert visitor.drawn([x + wide, y - 8, 1, high + 16])["colours"] == {loop: high + 16}
    assert visitor.pixel(x + wide + 1, y + 15)[3] == 0 and visitor.pixel(x + wide + 1, y - 7)[3] == 0
    assert visitor.drawn([x + wide - 9, y + high + 4, 10, 4])["colours"] == {loop: 40}


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
    bars, plates = visitor.bars(), visitor.plates()
    mark = visitor.colour("--mark")

    # The first beat of a second bar, which the analysis counts as 5, well inside the
    # song: the user says it is count 1. A press on its plate puts the position on it.
    beat = next(n for n in range(16, len(before)) if before[n] == 5)
    bar = bars.index((beat, beat + 3))
    visitor.press_bar(bar)
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
    # The bars are the ones the new count makes: the same bars here, and the one before
    # that beat is left alone.
    assert visitor.bars() == bars_of(after) == bars
    # Right after the press the bar that starts on that beat is the lit one. Its lid shows
    # over its block: a strip 4 high, 3 above the block and 3 wider than it on each side.
    page.mouse.move(0, 0)
    x, y, wide, high = visitor.plates()[bar]
    assert visitor.lit_bar() == bar
    assert visitor.drawn([x - 8, y - 13, wide + 16, 4])["colours"] == {mark: 4 * (wide + 16)}
    assert visitor.drawn([x - 9, y - 14, wide + 18, 1])["inked"] == 0 and visitor.drawn([x - 5, y - 9, wide + 10, 3])["inked"] == 0
    assert visitor.pixel(x - 9, y - 11)[3] == 0 and visitor.pixel(x + wide + 8, y - 11)[3] == 0
    # With the playing position elsewhere, its plate is a first bar's, with a lid: 3
    # above the plate and 3 wider than it on each side. The plate before it has none.
    visitor.press_bar(bar + 2)
    page.mouse.move(0, 0)
    assert visitor.pixel(x, y) == mark and visitor.pixel(x + wide - 1, y + high - 1) == mark
    assert visitor.drawn([x - 3, y - 7, wide + 6, 4])["colours"] == {mark: 4 * (wide + 6)}
    assert visitor.drawn([x - 4, y - 8, wide + 8, 1])["inked"] == 0 and visitor.drawn([x - 3, y - 3, wide + 6, 3])["inked"] == 0
    assert visitor.pixel(x - 4, y - 5)[3] == 0 and visitor.pixel(x + wide + 3, y - 5)[3] == 0
    x_other, y_other, wide_other, high_other = visitor.plates()[bar - 1]
    assert visitor.pixel(x_other, y_other) == mark
    assert visitor.drawn([x_other - 3, y_other - 8, wide_other + 6, 8])["inked"] == 0

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
    # Taken back, the count, the bars and the plates are as before, and the lid is gone.
    assert visitor.counts() == before
    assert visitor.bars() == bars and visitor.plates() == plates
    visitor.press_bar(bar + 2)
    page.mouse.move(0, 0)
    x, y, wide, high = plates[bar]
    assert visitor.pixel(x, y) == visitor.colour("--plate")
    assert visitor.drawn([x - 1, y - 8, wide + 4, 8])["inked"] == 0
    expect(other.page.locator("#map")).to_have_attribute("data-by-hand", "", timeout=6000)
    assert other.counts() == before
    assert [method for method, url in visitor.changes_of_count()] == ["PUT", "DELETE", "DELETE"]


def test_count_1_on_a_beat_inside_a_bar_cuts_the_bar_and_taken_back_leaves_it_whole(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, one = page.locator("#map"), page.locator("#one")
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    mark = visitor.colour("--mark")
    whole = max(wide for x, y, wide, high in plates)
    cut = whole_ocho(visitor)
    first = bars[cut][0]

    # The second beat of a whole bar, reached with a press on its plate and the arrow.
    visitor.press_bar(cut)
    page.keyboard.press("ArrowRight")
    expect(page.locator("#now")).to_have_attribute("data-lit", str(first + 1))
    one.click()
    expect(song).to_have_attribute("data-by-hand", str(first + 1))
    # The bar is cut: what is left of it is one beat, and a bar starts on the beat. The
    # count runs in eights from there, so every bar after it starts a beat later.
    after = counts[: first + 1] + [(n - first - 1) % 8 + 1 for n in range(first + 1, len(counts))]
    assert visitor.counts() == after
    cut_bars, cut_plates = visitor.bars(), visitor.plates()
    assert cut_bars == bars_of(after) and len(cut_plates) == len(cut_bars)
    assert cut_bars[cut : cut + 3] == [(first, first), (first + 1, first + 4), (first + 5, first + 8)]
    # Every plate is as wide as the beats of its bar: the one that was cut is a quarter
    # of a whole one, and stands where it stood.
    for (x, y, wide, high), (start, end) in zip(cut_plates, cut_bars):
        assert wide == int(whole * (end - start + 1) / 4 + 0.5), (start, end, wide)
    assert cut_plates[cut] == [plates[cut][0], plates[cut][1], int(whole / 4 + 0.5), HIGH]
    # The new bar is the lit one, with its lid over its block.
    page.mouse.move(0, 0)
    x, y, wide, high = cut_plates[cut + 1]
    assert visitor.lit_bar() == cut + 1 and wide == whole
    assert visitor.drawn([x - 8, y - 13, wide + 16, 4])["colours"] == {mark: 4 * (wide + 16)}
    # With the position elsewhere: the cut plate is a first bar's, too narrow for its
    # count, and has no lid. The new one is a first bar's with its count and a lid.
    visitor.press_bar(cut + 3)
    page.mouse.move(0, 0)
    assert cut_plates[cut][2] < 14
    assert visitor.drawn(cut_plates[cut])["colours"] == {mark: cut_plates[cut][2] * HIGH}
    assert visitor.drawn([cut_plates[cut][0] - 3, y - 8, cut_plates[cut][2] + 3, 8])["inked"] == 0
    on = visitor.drawn([x, y, wide, high])["colours"]
    assert max(on, key=on.get) == mark and visitor.colour("--ground") in on, on
    assert visitor.drawn([x - 3, y - 7, wide + 6, 4])["colours"] == {mark: 4 * (wide + 6)}

    # Taken back: a press on the plate with the lid puts the position on that beat, and
    # the control takes it back. The bars and the plates are as before.
    visitor.press_bar(cut + 1)
    expect(page.locator("#now")).to_have_attribute("data-lit", str(first + 1))
    expect(one).to_have_text("Not count 1")
    one.click()
    expect(song).to_have_attribute("data-by-hand", "")
    assert visitor.counts() == counts and visitor.bars() == bars and visitor.plates() == plates
    assert visitor.lit_bar() == cut


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
