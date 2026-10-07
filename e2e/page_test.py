"""End-to-end tests: whole flows through the page, in a real browser, against the real program.

A song is drawn on two canvases: the ocho that is sounding, and the whole song with a
plate for each bar. The page says in attributes of those canvases which beat is lit,
where the plates are and which bar is lit, and the tests read them. What was drawn they
read from the pixels of the canvas, at the boxes the page gives for its plates.

    uv run pytest e2e

They start the program on its own data folder and drive Chrome and Firefox with Playwright.
Chrome is the one installed on the machine. Firefox is Playwright's own build, fetched once:

    PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install firefox

A browser that cannot start is skipped, and says so. The songs are made here with ffmpeg:
a drum-like click at 120 BPM. Nothing from the reference material is needed.
"""

import http.client
import json
import math
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
LONGER = "Los Tests - Canción larga"
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
        # More than eight ochos: its song does not fit in one row.
        "longer": a_song(folder / "track03.m4a", 44.5, "title=Canción larga", "artist=Los Tests"),
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
# clock itself, and every volume control the page makes. And how many times each canvas
# has been wiped, which is how a drawing of it starts, and where the page wrote on it in
# its last drawing, with the colour and the typeface it asked for, each as the page set
# it. The pixels cannot tell two inks of one hue apart, or a weight from another. Which
# text was written is not noted: which numeral is on a plate is for the owner's eye.
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
window.drawn = { now: 0, map: 0 }
window.written = { now: [], map: [] }
const clearRect = CanvasRenderingContext2D.prototype.clearRect
CanvasRenderingContext2D.prototype.clearRect = function () {
  if (this.canvas.id in window.drawn) {
    window.drawn[this.canvas.id]++
    window.written[this.canvas.id] = []
  }
  return clearRect.apply(this, arguments)
}
for (const name of ['font', 'fillStyle']) {
  const own = Object.getOwnPropertyDescriptor(CanvasRenderingContext2D.prototype, name)
  Object.defineProperty(CanvasRenderingContext2D.prototype, name, {
    ...own,
    set(value) {
      this.asked = { ...this.asked, [name]: value }
      own.set.call(this, value)
    },
  })
}
const fillText = CanvasRenderingContext2D.prototype.fillText
CanvasRenderingContext2D.prototype.fillText = function (text, x, y) {
  if (this.canvas.id in window.written) window.written[this.canvas.id].push({ x, y, ink: this.asked?.fillStyle, font: this.asked?.font })
  return fillText.apply(this, arguments)
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
        """The first beat of every bar, as the song on screen says it."""
        return [int(beat) for beat in self.page.locator("#map").get_attribute("data-bars").split()]

    def plates(self):
        """The box of the plate of every bar inside the canvas of the song: left, top, width, height."""
        return json.loads(self.page.locator("#map").get_attribute("data-plates"))

    def lit_bar(self):
        """The bar the song says is lit, as its place among the bars, or -1 before the first beat."""
        lit = self.page.locator("#map").get_attribute("data-lit")
        return int(lit) if lit else -1

    def changes_of_count(self):
        return [(method, url) for method, url in self.sent if url.endswith("/ones") or "/ones?" in url]

    def lit(self):
        """The beat whose mark is lit, or -1 before the first one."""
        lit = self.page.locator("#now").get_attribute("data-lit")
        return int(lit) if lit else -1

    def on_page(self, x, y):
        """Where a point of the canvas of the song is on the page."""
        box = self.page.locator("#map").bounding_box()
        return box["x"] + x, box["y"] + y

    def point_in(self, bar, across=0.5):
        """A point of the plate of a bar, on the page: its middle, or as far across it as
        asked, from 0 to 1. The song says where it puts its plates."""
        x, y, wide, high = self.plates()[bar]
        return self.on_page(x + wide * across, y + high / 2)

    def press_bar(self, bar):
        self.page.mouse.click(*self.point_in(bar))

    def press_beat(self, beat):
        """Moves the playing position onto a beat: a press on the plate of its bar reaches
        the first beat of the bar, and the right arrow goes on from there, a beat at a time."""
        bars = self.bars()
        bar = max(n for n, first in enumerate(bars) if first <= beat)
        self.press_bar(bar)
        for _ in range(beat - bars[bar]):
            self.page.keyboard.press("ArrowRight")

    def drag_bars(self, first, last):
        """A press on the plate of one bar that is let go on the plate of another."""
        self.page.mouse.move(*self.point_in(first))
        self.page.mouse.down()
        self.page.mouse.move(*self.point_in(last), steps=6)
        self.page.mouse.up()

    def at(self, x, y):
        """The pixel of the canvas of the song at a point of it: red, green, blue and how
        solid it is, each up to 255. Where nothing was drawn it is not solid at all."""
        return self.page.evaluate(AT, [x, y])

    def written(self, box):
        """What the page wrote on the song inside a box, in its last drawing: for each
        writing the colour it asked for, as the style sheet has it, and the weight and
        the size of its typeface."""
        x, y, wide, high = box
        inside = [one for one in self.page.evaluate("window.written.map") if x <= one["x"] < x + wide and y <= one["y"] < y + high]
        return [(one["ink"], *one["font"].split()[:2]) for one in inside]

    def over(self, bar):
        """The pixel just above the middle of the plate of a bar: inside the block of a lit
        bar and inside a halo, and clear of a plate and of its lid."""
        x, y, wide, high = self.plates()[bar]
        return self.at(x + wide / 2, y - 2)

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

# The colours of the song as the spec of its plates gives them, in light and in dark:
# red, green and blue, and for the two that let the ground through, how solid from 0 to 1.
# The tests carry their own list. Read from the page, a colour that went wrong there
# would go wrong here with it.
COLOURS = {
    "light": {
        "ground": (229, 227, 220),
        "ink-soft": (75, 74, 69),
        "mark": (18, 18, 18),
        "plate": (205, 202, 192),
        "ink": (18, 18, 18),
        "lit": (18, 18, 18),
        "lit-ink": (255, 210, 0),
        "hover": (18, 18, 18, 0.14),
        "loop": (18, 18, 18),
        "loop-fill": (255, 210, 0, 0.6),
    },
    "dark": {
        "ground": (18, 18, 17),
        "ink-soft": (169, 166, 157),
        "mark": (243, 241, 234),
        "plate": (51, 50, 46),
        "ink": (243, 241, 234),
        "lit": (242, 197, 0),
        "lit-ink": (18, 18, 18),
        "hover": (243, 241, 234, 0.18),
        "loop": (242, 197, 0),
        "loop-fill": (242, 197, 0, 0.2),
    },
}

# The pixel of the canvas of the song at a point of it.
AT = """([x, y]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    return [...canvas.getContext('2d').getImageData(Math.floor(x * scale), Math.floor(y * scale), 1, 1).data]
}"""

# How solid each pixel is along a line of the canvas of the song, from a point to the right.
ALONG = """([x, y, wide]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const line = canvas.getContext('2d').getImageData(Math.floor(x * scale), Math.floor(y * scale), Math.round(wide * scale), 1).data
    return [...line].filter((part, n) => n % 4 === 3)
}"""

# What the canvas of the song has in a box, for the colour the box should be filled with
# and the colour of what should be written on it: how many pixels of its rim are not the
# fill, how much of it is the fill, how many pixels are nearer to the colour of the
# writing than to the fill, how far the middle of those is from the middle of the box,
# and how far from the middle of the box the farthest pixel is that is not the fill,
# across and down: a count reaches a few pixels, a mark for a beat would reach further.
BOX = """([[x, y, wide, high], fill, ink]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const [left, top, across, down] = [x, y, wide, high].map((size) => Math.round(size * scale))
    const data = canvas.getContext('2d').getImageData(left, top, across, down).data
    const far = (n, colour) => (data[4 * n + 3] < 255 ? Infinity : colour.reduce((sum, part, at) => sum + Math.abs(data[4 * n + at] - part), 0))
    let rim = 0
    let filled = 0
    let reach = null
    const written = []
    for (let n = 0; n < across * down; n++) {
        const isFill = far(n, fill) <= 12
        const onRim = n < across || n >= across * (down - 1) || n % across === 0 || n % across === across - 1
        if (onRim && !isFill) rim++
        if (isFill) {
            filled++
            continue
        }
        const [px, py] = [n % across, Math.floor(n / across)]
        reach = [Math.max(reach?.[0] ?? 0, Math.abs(px + 0.5 - across / 2) / scale), Math.max(reach?.[1] ?? 0, Math.abs(py + 0.5 - down / 2) / scale)]
        if (far(n, ink) < far(n, fill)) written.push([px, py])
    }
    const middle = (part, size) => (Math.min(...written.map((at) => at[part])) + Math.max(...written.map((at) => at[part])) + 1 - size) / 2 / scale
    return { rim, filled: filled / (across * down), written: written.length, off: written.length ? [middle(0, across), middle(1, down)] : null, reach }
}"""

# The ink the canvas of the song has outside a set of boxes, right of a line: how many
# pixels, and where the first one is.
STRAY = """([boxes, from]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const { width, height } = canvas
    const data = canvas.getContext('2d').getImageData(0, 0, width, height).data
    const inside = (x, y) => boxes.some(([left, top, wide, high]) => x >= left * scale && x < (left + wide) * scale && y >= top * scale && y < (top + high) * scale)
    let stray = 0
    let first = null
    for (let y = 0; y < height; y++) {
        for (let x = Math.round(from * scale); x < width; x++) {
            if (data[4 * (y * width + x) + 3] === 0 || inside(x, y)) continue
            stray++
            first ??= [x / scale, y / scale]
        }
    }
    return { stray, first }
}"""

# The box of the ink the canvas of the song has inside a box: its left, top, right and
# bottom, the last two not included. null where it has none.
INKED = """([x, y, wide, high]) => {
    const canvas = document.getElementById('map')
    const scale = canvas.width / canvas.clientWidth
    const [left, top, across, down] = [x, y, wide, high].map((size) => Math.round(size * scale))
    const data = canvas.getContext('2d').getImageData(left, top, across, down).data
    let found = null
    for (let n = 0; n < across * down; n++) {
        if (data[4 * n + 3] === 0) continue
        const [px, py] = [n % across, Math.floor(n / across)]
        found = found ? [Math.min(found[0], px), Math.min(found[1], py), Math.max(found[2], px + 1), Math.max(found[3], py + 1)] : [px, py, px + 1, py + 1]
    }
    return found && [x + found[0] / scale, y + found[1] / scale, x + found[2] / scale, y + found[3] / scale]
}"""


def is_colour(pixel, colour):
    """Whether a pixel of a canvas has a colour of the page. A colour that lets the
    ground through is as solid on the canvas as it says it is."""
    solid = colour[3] if len(colour) > 3 else 1
    return abs(pixel[3] - 255 * solid) <= 3 and all(abs(pixel[part] - colour[part]) <= 8 for part in range(3))


def hex_of(colour):
    """A colour as the style sheet writes it."""
    return "#%02x%02x%02x" % tuple(colour[:3])


def bars_of(counts):
    """The first beat of every bar that a count makes, worked out here: the first beat of
    the song, every count 5, and every beat whose count does not go on from the one before."""
    return [beat for beat, count in enumerate(counts) if beat == 0 or count == 5 or count != counts[beat - 1] + 1]


def ochos_of(counts):
    """The first beat of every ocho: where the count does not go on from the beat before."""
    return [beat for beat, count in enumerate(counts) if beat == 0 or count != counts[beat - 1] + 1]


def beats_in(counts, bars):
    """How many beats each bar has."""
    return [end - first for first, end in zip(bars, bars[1:] + [len(counts)])]


def whole_ochos(counts, bars):
    """The first bar of every whole ocho, as its place among the bars: a bar of four beats
    on count 1, with a bar of four beats on count 5 after it."""
    long = beats_in(counts, bars)
    return [
        bar
        for bar in range(len(bars) - 1)
        if (counts[bars[bar]], long[bar], counts[bars[bar + 1]], long[bar + 1]) == (1, 4, 5, 4)
    ]


def drawn_with(plates, lit):
    """The boxes the song has ink in when one bar is lit: the plates, and for the lit bar
    its block, 5 wider than its plate on each side and 6 higher."""
    return [[x - 5, y - 6, wide + 10, high + 12] if bar == lit else [x, y, wide, high] for bar, (x, y, wide, high) in enumerate(plates)]



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

    # A press on the plate of a bar, and the right arrow from there, move the playing
    # position onto a beat.
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
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")

    # Dragging from one bar to the next marks both and switches the loop on. It is eight
    # beats, four seconds, long.
    bars = visitor.bars()
    first, last = bars[2], bars[4] - 1
    assert last - first == 7
    visitor.drag_bars(2, 3)
    expect(page.locator("#loop")).to_be_checked()
    expect(page.locator("#map")).to_have_attribute("data-range", f"{first} {last}")
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[first])} to {clock(beats[last + 1] - 0.02)}")
    length = beats[last + 1] - beats[first]

    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    needs_sound(page)
    for _ in range(17):
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
    visitor.drag_bars(2, 3)
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
    bars = visitor.bars()
    first, last = bars[2], bars[4] - 1
    visitor.drag_bars(2, 3)
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
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    colours = COLOURS["light"]
    # Nothing is marked yet, so there is nothing to clear.
    expect(clear).to_be_disabled()
    expect(song).to_have_attribute("data-range", "")

    # A drag from the first bar of an ocho to its second marks both.
    one = whole_ochos(counts, bars)[1]
    marked = f"{bars[one]} {bars[one + 2] - 1}"
    visitor.drag_bars(one, one + 1)
    expect(page.locator("#loop")).to_be_checked()
    expect(song).to_have_attribute("data-range", marked)
    page.mouse.move(0, 0)
    # The bracket that opens the range is on the canvas, at the outer edge of its band,
    # 8 before the plate, and the band is behind the plates. The position is a moment
    # before the range, so the bar before it is lit: its block is not looked at.
    x, y, wide, high = plates[one]
    x_other, _, wide_other, _ = plates[one + 1]
    bracket = [x - 7, y + high / 2]
    band = [x_other + wide_other / 2, y - 4]
    # The top edge of the band between its two brackets, where a dashed rule runs.
    edge = [x + 6, y - 8, x_other + wide_other - x - 12]
    assert is_colour(visitor.at(*bracket), colours["loop"])
    assert is_colour(visitor.at(*band), colours["loop-fill"])
    assert all(abs(solid - 153) <= 3 for solid in page.evaluate(ALONG, edge))

    # Switched off, the loop keeps its range: it can be switched on again. The band is
    # gone, and two dashed rules run along where its top and its bottom were.
    page.locator("#loop").uncheck()
    expect(song).to_have_attribute("data-range", marked)
    assert is_colour(visitor.at(*bracket), colours["loop"])
    assert visitor.at(*band)[3] == 0
    for line in (y - 8, y + high + 7):
        rule = page.evaluate(ALONG, [edge[0], line, edge[2]])
        assert max(rule) > 128 and min(rule) == 0, rule
    # A rule is 1.5 thick, on the edge of the band: the line 2 above it and the line 1
    # under it have no ink, and neither have those around the lower rule.
    for line in (y - 10, y - 7, y + high + 6, y + high + 9):
        assert max(page.evaluate(ALONG, [edge[0], line, edge[2]])) == 0, line
    expect(clear).to_be_enabled()
    # Cleared, the range is gone from the song and from the transport bar.
    clear.click()
    expect(song).to_have_attribute("data-range", "")
    assert visitor.at(*bracket)[3] == 0
    assert max(page.evaluate(ALONG, edge)) == 0
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
    visitor.drag_bars(1, 2)
    expect(song).to_have_attribute("data-range", f"{bars[1]} {bars[3] - 1}")
    expect(page.locator("#loop")).to_be_checked()


def test_a_range_set_inside_bars_is_kept_in_beats_and_drawn_over_the_whole_bars(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")
    beats = visitor.beats(TAGGED)
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    colours = COLOURS["light"]
    # "Start here" on the second beat of the first bar of an ocho, and "End here" on the
    # third beat of the second bar of the ocho after it: both inside a bar.
    ochos = whole_ochos(counts, bars)
    first, last = ochos[1], ochos[2] + 1
    start, end = bars[first] + 1, bars[last] + 2
    visitor.press_beat(start)
    page.locator("#loop-start").click()
    visitor.press_beat(end)
    page.locator("#loop-end").click()
    # The range is those beats, in what the song says and in what the loop plays.
    expect(song).to_have_attribute("data-range", f"{start} {end}")
    expect(page.locator("#loop")).to_be_checked()
    expect(page.locator("#loop-range")).to_have_text(f"{clock(beats[start])} to {clock(beats[end + 1] - 0.02)}")

    # The band covers the four bars that hold a beat of it, whole. It is read in the two
    # lines between its top and the block of a lit bar, which the last bar is.
    page.mouse.move(0, 0)
    for bar in range(first, last + 1):
        x, y, wide, high = plates[bar]
        assert is_colour(visitor.at(x + wide / 2, y - 7), colours["loop-fill"]), bar
    # Its brackets are at the outer edges of those bars, 8 beyond their plates, not at
    # the beats: an upright, with a foot turned inward at the top and at the bottom.
    x, y, wide, high = plates[first]
    assert is_colour(visitor.at(x - 7, y + high / 2), colours["loop"])
    assert is_colour(visitor.at(x, y - 7), colours["loop"]) and is_colour(visitor.at(x, y + high + 6), colours["loop"])
    assert visitor.at(x - 9, y + high / 2)[3] == 0
    # The upright is 4 wide: the band shows from the fifth pixel on.
    assert all(is_colour(visitor.at(x - before, y + high / 2), colours["loop"]) for before in (8, 5))
    assert is_colour(visitor.at(x - 4, y + high / 2), colours["loop-fill"])
    x, y, wide, high = plates[last]
    assert is_colour(visitor.at(x + wide + 6, y + high + 6), colours["loop"])
    assert is_colour(visitor.at(x + wide - 1, y - 7), colours["loop"]) and is_colour(visitor.at(x + wide - 1, y + high + 6), colours["loop"])
    assert visitor.at(x + wide + 8, y + high + 6)[3] == 0
    # And it is over no other bar.
    for bar in (first - 1, last + 1):
        x, y, wide, high = plates[bar]
        assert visitor.at(x + wide / 2, y - 7)[3] == 0, bar


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


def test_every_bar_has_one_plate_with_its_count_in_rows_of_eight_ochos_in_light_and_in_dark(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = visitor.page
    visitor.pick(files["longer"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")
    result = visitor.result(LONGER)
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    # The count on screen is the one of the analysis, one for every beat.
    assert counts == result["count"] and len(counts) == len(result["beats"])
    assert set(counts) == set(range(1, 9))
    # The bars are the ones that count makes, and each has one plate. No beat has a mark.
    assert bars == bars_of(counts)
    assert len(plates) == len(bars)
    assert song.get_attribute("data-marks") is None
    assert song.get_attribute("aria-label") == (
        "The song in rows of ochos, a plate for each bar with its count on it. "
        "Press a bar to move the playing position to its first beat. Drag across bars to mark them as a loop."
    )

    # A row holds eight ochos: it starts on the first bar of an ocho and has no ninth.
    assert song.get_attribute("data-per-row") == "8"
    ochos = ochos_of(counts)
    rows = {}
    for bar, (x, y, wide, high) in enumerate(plates):
        rows.setdefault(y, []).append(bar)
    tops = sorted(rows)
    assert len(tops) >= 2, "the test song must fill its first row"
    assert [bar for top in tops for bar in rows[top]] == list(range(len(bars)))
    # The plates of the first row are 28 from the top, a row is 62 under the one before,
    # and the canvas ends 28 under the plates of the last.
    assert tops[0] == 28 and all(under - over == 62 for over, under in zip(tops, tops[1:])), tops
    assert song.bounding_box()["height"] == tops[-1] + 30 + 28
    assert [bars[rows[top][0]] in ochos for top in tops] == [True] * len(tops), [bars[rows[top][0]] for top in tops]
    for top in tops:
        in_row = rows[top]
        starts = [bar for bar in in_row if bars[bar] in ochos]
        # Eight ochos, and in the last row what is left of the song.
        assert len(starts) <= 8 and (len(starts) == 8 or top == tops[-1]), (top, len(starts))
        # It starts 80 from the left. The two plates of an ocho are 2 apart, and two ochos 14.
        assert plates[in_row[0]][0] == 80
        for left, right in zip(in_row, in_row[1:]):
            gap = plates[right][0] - plates[left][0] - plates[left][2]
            assert gap == (14 if right in starts else 2), (left, right, gap)

    # Whole plates are all as wide as each other, 48 in a window this wide, and 30 high.
    # The plate of a bar of fewer beats is narrower in the proportion of its beats.
    long = beats_in(counts, bars)
    assert {plates[bar][2] for bar in range(len(bars)) if long[bar] == 4} == {48}
    for bar, (x, y, wide, high) in enumerate(plates):
        assert high == 30 and wide == math.floor(48 * long[bar] / 4 + 0.5), (bar, wide, high)

    page.mouse.move(0, 0)
    for scheme in ("light", "dark"):
        # The page follows the system, and draws the song again in the colours of each.
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        colours = COLOURS[scheme]
        ground = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert tuple(int(part) for part in ground[4:-1].split(",")) == colours["ground"], scheme
        for bar, box in enumerate(plates):
            # The plate of a first bar is solid, in the colour of the marks, and the plate
            # of a second bar is the quiet grey. Each is a plain rectangle, with its count
            # written in its middle in the colour of its count: the two are told apart by
            # the fill and by the count.
            first = counts[bars[bar]] <= 4
            fill, ink = (colours["mark"], colours["ground"]) if first else (colours["plate"], colours["ink"])
            seen = page.evaluate(BOX, [box, fill, ink])
            assert seen["rim"] == 0 and seen["filled"] > 0.75, (scheme, bar, seen)
            # A plate narrower than 14 has no count: it is its fill and nothing else.
            if box[2] < 14:
                assert seen["written"] == 0 and seen["reach"] is None and visitor.written(box) == [], (scheme, bar, seen)
                continue
            # The count is in the middle of the plate, both ways, and nothing else is on
            # the plate: no beat inside the bar has a mark. The page asked for the count
            # in its colour, heavy on a first bar and less so on a second, 15 high.
            assert seen["written"] >= 12 and max(abs(off) for off in seen["off"]) <= 1.5 and max(seen["reach"]) <= 8, (scheme, bar, seen)
            assert visitor.written(box) == [(hex_of(ink), "700" if first else "500", "15px")], (scheme, bar)
        # A plate for each bar and nothing else: no ink in the 2 pixels inside an ocho, in
        # the 14 between two ochos, between two rows, or anywhere else right of the times.
        assert page.evaluate(STRAY, [plates, 67]) == {"stray": 0, "first": None}, scheme
        # Every row has its time, which ends 14 left of its first plate, level with the
        # middle of the plates.
        for top in tops:
            time = page.evaluate(INKED, [0, top - 16, 80, 62])
            assert time and 62 <= time[2] <= 66 and abs((time[1] + time[3]) / 2 - (top + 15)) <= 1.5, (scheme, top, time)
            assert visitor.written([0, top - 16, 80, 62]) == [(hex_of(colours["ink-soft"]), "500", "12px")], (scheme, top)
    # No section is written: the text where the song is shown is the count, which is not
    # there before the first beat, the tempo and the time.
    assert page.locator("#player").inner_text().split() == ["–", page.locator("#bpm").inner_text(), "BPM", "0:00"]

    # How many ochos a row holds, and how wide a whole plate is, follow the width of the
    # window: a row holds eight ochos where that leaves a whole plate 44 wide or more,
    # which is from about 1200, and four under that. A plate is never wider than 96. The
    # window is high enough for the song not to scroll, at any of these widths.
    for width, per_row, whole in ((1100, "4", 83), (1190, "4", 94), (1210, "8", 44), (1920, "8", 88), (2400, "8", 96)):
        drawn = page.evaluate("window.drawn.map")
        page.set_viewport_size({"width": width, "height": 900})
        # The song is laid out and drawn again when its part of the page has its new
        # size: by two pictures of the screen later. It is as wide as the window leaves it.
        page.wait_for_function("drawn => window.drawn.map > drawn", arg=drawn)
        page.evaluate("() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))")
        assert song.bounding_box()["width"] == width - 288, width
        assert song.get_attribute("data-per-row") == per_row, width
        resized = visitor.plates()
        assert {resized[bar][2] for bar in range(len(bars)) if long[bar] == 4} == {whole}, width
        in_first_row = [bar for bar, plate in enumerate(resized) if plate[1] == 28]
        assert len([bar for bar in in_first_row if bars[bar] in ochos]) == int(per_row), width


def test_the_bar_that_holds_the_beat_that_is_sounding_is_lit_whole_in_light_and_in_dark(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, now = page.locator("#map"), page.locator("#now")
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    # Before the first beat of the song no bar is lit: the song says so, and it has no
    # ink but its plates.
    expect(song).to_have_attribute("data-lit", "")
    assert visitor.lit() == -1 and visitor.lit_bar() == -1
    assert page.evaluate(STRAY, [plates, 67])["stray"] == 0

    # A press on the plate of the first bar of a whole ocho: that bar is lit.
    bar = whole_ochos(counts, bars)[1]
    x, y, wide, high = plates[bar]
    visitor.press_bar(bar)
    expect(song).to_have_attribute("data-lit", str(bar))
    expect(now).to_have_attribute("data-lit", str(bars[bar]))
    page.mouse.move(0, 0)
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.wait_for_timeout(300)
        colours = COLOURS[scheme]
        # It is a block in place of its plate, 5 wider on each side and 6 higher, with
        # its count in the middle in a colour of its own. The corners of the block are
        # rounded, so its rim is read 2 inside its left and its right.
        seen = page.evaluate(BOX, [[x - 3, y - 6, wide + 6, high + 12], colours["lit"], colours["lit-ink"]])
        assert seen["rim"] == 0 and seen["written"] >= 12 and max(abs(off) for off in seen["off"]) <= 1.5 and max(seen["reach"]) <= 9, (scheme, seen)
        assert visitor.written(plates[bar]) == [(hex_of(colours["lit-ink"]), "700", "17px")], scheme
        assert is_colour(visitor.at(x - 5, y + high / 2), colours["lit"]) and is_colour(visitor.at(x + wide + 4, y + high / 2), colours["lit"])
        assert visitor.at(x - 5, y - 6)[3] < 255, scheme
        # No other bar is lit: there is no ink but that block and the plates of the others,
        # and each of the others has the fill of a plate, not far from a corner.
        assert page.evaluate(STRAY, [drawn_with(plates, bar), 67])["stray"] == 0, scheme
        for other, (left, top, across, down) in enumerate(plates):
            fill = colours["mark"] if counts[bars[other]] <= 4 else colours["plate"]
            assert other == bar or is_colour(visitor.at(left + across - 2, top + down - 2), fill), (scheme, other)

    # The right arrow, three times: the beat of the large view moves on each time, and
    # the lit bar stays. Nothing moves inside it, and the song is not drawn again.
    drawn = page.evaluate("window.drawn.map")
    for step in (1, 2, 3):
        page.keyboard.press("ArrowRight")
        expect(now).to_have_attribute("data-lit", str(bars[bar] + step))
        assert visitor.lit_bar() == bar
        assert page.evaluate("window.drawn.map") == drawn
        assert is_colour(visitor.over(bar), colours["lit"]) and visitor.over(bar + 1)[3] == 0
    # The fourth time the next bar is lit, and this one is a plate again.
    page.keyboard.press("ArrowRight")
    expect(now).to_have_attribute("data-lit", str(bars[bar + 1]))
    expect(song).to_have_attribute("data-lit", str(bar + 1))
    assert page.evaluate("window.drawn.map") > drawn
    assert is_colour(visitor.over(bar + 1), colours["lit"]) and visitor.over(bar)[3] == 0
    assert page.evaluate(STRAY, [drawn_with(plates, bar + 1), 67])["stray"] == 0


# One look at the page while it plays: the beat the large view says is lit, the bar the
# song says is lit, and the bars the song has drawn as a block, which are those with ink
# just above their plate.
PLAYING = """() => {
    const [now, song] = ['now', 'map'].map((id) => document.getElementById(id))
    const scale = song.width / song.clientWidth
    const pen = song.getContext('2d')
    const blocks = []
    JSON.parse(song.dataset.plates).forEach(([x, y, wide], bar) => {
        if (pen.getImageData(Math.floor((x + wide / 2) * scale), Math.floor((y - 2) * scale), 1, 1).data[3] > 0) blocks.push(bar)
    })
    return { beat: now.dataset.lit, bar: song.dataset.lit, blocks }
}"""


def test_while_the_song_plays_the_lit_bar_is_the_bar_of_the_beat_the_large_view_lights(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    bars = visitor.bars()

    page.locator("#play").click()
    needs_sound(page)
    page.mouse.move(0, 0)
    lit = set()
    for _ in range(36):
        page.wait_for_timeout(150)
        now = page.evaluate(PLAYING)
        if now["beat"] == "":
            continue
        bar = max(n for n, first in enumerate(bars) if first <= int(now["beat"]))
        # The song says that bar is lit, and that bar is the one it has drawn as a block.
        assert now["bar"] == str(bar) and now["blocks"] == [bar], now
        lit.add(bar)
    assert len(lit) >= 3, lit


def test_a_press_on_a_bar_moves_the_position_to_its_first_beat_and_the_bar_under_the_pointer_has_a_halo(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, now = page.locator("#map"), page.locator("#now")
    beats = visitor.beats(TAGGED)
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    colours = COLOURS["light"]
    # Three whole ochos that follow each other in the one row of this song: the position
    # goes to the first before every press, and the presses are on the other two.
    ochos = whole_ochos(counts, bars)
    away, one = ochos[0], ochos[1]
    two, next_ocho = one + 1, one + 2
    assert next_ocho == ochos[2] and len({plates[bar][1] for bar in (away, one, two, next_ocho)}) == 1

    def press(x, y, **how):
        page.mouse.click(*visitor.on_page(x, y), **how)

    def is_on(bar):
        expect(now).to_have_attribute("data-lit", str(bars[bar]))
        expect(song).to_have_attribute("data-lit", str(bar))
        expect(page.locator("#position")).to_have_text(clock(beats[bars[bar]]))

    def press_reaches(x, y, bar):
        visitor.press_bar(away)
        is_on(away)
        press(x, y)
        is_on(bar)

    # On the middle of a plate, and 2 pixels inside its left edge and its right edge: the
    # position is on the first beat of that bar. On the second plate of an ocho as well.
    for bar in (one, two):
        x, y, wide, high = plates[bar]
        for across in (wide / 2, 2, wide - 2):
            press_reaches(x + across, y + high / 2, bar)
    x, y, wide, high = plates[one]
    middle = y + high / 2
    # In the 2 pixels between the two plates of an ocho, the bar whose plate is nearer.
    press_reaches(x + wide + 0.5, middle, one)
    # In the 14 between two ochos too, and the left one when both are as near.
    gap = plates[two][0] + plates[two][2]
    assert plates[next_ocho][0] == gap + 14
    press_reaches(gap + 4, middle, two)
    press_reaches(gap + 10, middle, next_ocho)
    press_reaches(gap + 7, middle, two)
    # In the band of a row, above its plates and under them: a bar of that row.
    press_reaches(x + wide / 2, y - 12, one)
    press_reaches(x + wide / 2, y + high + 12, one)

    # The bar under the pointer has a faint halo behind its plate, 4 larger than the
    # plate on every side. The plate itself is as it was.
    visitor.press_bar(away)
    page.mouse.move(*visitor.point_in(one))
    assert is_colour(visitor.over(one), colours["hover"])
    assert [visitor.at(x - before, middle)[3] > 0 for before in (5, 4)] == [False, True]
    assert [visitor.at(x + wide / 2, y - above)[3] > 0 for above in (5, 4)] == [False, True]
    assert [visitor.at(x + wide / 2, y + high + under)[3] > 0 for under in (3, 4)] == [True, False]
    assert page.evaluate(BOX, [plates[one], colours["mark"], colours["ground"]])["rim"] == 0
    # It follows the pointer to another bar. That one has a plate of the quiet grey, which
    # a halo drawn over it would darken: the plate is its own fill to its rim.
    page.mouse.move(*visitor.point_in(two))
    assert visitor.over(one)[3] == 0 and is_colour(visitor.over(two), colours["hover"])
    assert page.evaluate(BOX, [plates[two], colours["plate"], colours["ink"]])["rim"] == 0
    # Not while a press is held.
    page.mouse.down()
    assert visitor.over(two)[3] == 0
    page.mouse.up()
    is_on(two)
    # And it goes when the pointer leaves the song.
    page.mouse.move(*visitor.point_in(one))
    assert is_colour(visitor.over(one), colours["hover"])
    page.mouse.move(0, 0)
    assert visitor.over(one)[3] == 0

    # Where there is no bar a press does nothing: left of a row, on its time, right of its
    # last plate, and above the band of the first row. Nor does a press with another
    # button. The position is on a bar in the middle of the row, which is none of the
    # bars such a press would reach if it reached one: the first of the row, its last,
    # and the one that is pressed.
    row = [bar for bar, plate in enumerate(plates) if plate[1] == y]
    assert two not in (row[0], row[-1], one)
    visitor.press_bar(two)
    is_on(two)
    end = plates[row[-1]][0] + plates[row[-1]][2]
    for point in ((50, middle), (end + 8, middle), (x + wide / 2, 5)):
        press(*point)
        page.wait_for_timeout(100)
        is_on(two)
    press(x + wide / 2, middle, button="right")
    page.wait_for_timeout(100)
    is_on(two)
    expect(song).to_have_attribute("data-range", "")


def test_a_drag_marks_whole_bars_whichever_way_it_goes_and_a_band_with_brackets_covers_them(visit, files):
    visitor = visit(viewport={"width": 1100, "height": 720})
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song, now, loop = page.locator("#map"), page.locator("#now"), page.locator("#loop")
    counts, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    colours = COLOURS["light"]
    band, bracket = colours["loop-fill"], colours["loop"]
    last_beat = [end - 1 for end in bars[1:] + [len(counts)]]
    # In a window under about 1200 wide a row holds four ochos, so this song has two rows.
    assert song.get_attribute("data-per-row") == "4"
    tops = sorted({top for left, top, across, down in plates})
    assert len(tops) == 2
    upper, lower = ([bar for bar, plate in enumerate(plates) if plate[1] == top] for top in tops)
    ochos = whole_ochos(counts, bars)

    def above(bar):
        """The pixel in the middle of a bar, 7 above its plate: inside the band of a range
        and clear of a lid and of the block of a lit bar."""
        x, y, wide, high = plates[bar]
        return visitor.at(x + wide / 2, y - 7)

    # The bands of two rows meet half way between their plates: 16 under the plates of the
    # upper row, and so 16 above those of the lower. A press 15 under the upper plates
    # reaches the bar of the upper row, and one 17 under them the bar of the lower.
    assert upper[0] in ochos and lower[0] in ochos
    x, y, wide, high = plates[upper[1]]
    assert plates[lower[1]][:2] == [x, y + 62]
    for under, bar in ((15, upper[1]), (17, lower[1])):
        page.mouse.click(*visitor.on_page(x + wide / 2, y + high + under))
        expect(now).to_have_attribute("data-lit", str(bars[bar]))

    # A press that is let go on the bar it started on is a press, also when the pointer
    # moved inside the bar: it marks nothing.
    bar = ochos[2]
    page.mouse.move(*visitor.point_in(bar, across=0.2))
    page.mouse.down()
    page.mouse.move(*visitor.point_in(bar, across=0.8), steps=4)
    page.mouse.up()
    expect(now).to_have_attribute("data-lit", str(bars[bar]))
    expect(song).to_have_attribute("data-range", "")
    expect(loop).to_be_disabled()

    # From the second bar of an ocho to the first bar of the next one. While the press is
    # held the two bars show as a range that is not played round yet: no band, and two
    # dashed rules along where its top and its bottom will be.
    first, last = ochos[0] + 1, ochos[1]
    marked = f"{bars[first]} {last_beat[last]}"
    x, y, wide, high = plates[first]
    x_last, _, wide_last, _ = plates[last]
    assert last == first + 1 and last_beat[last] - bars[first] == 7 and x_last == x + wide + 14
    page.mouse.move(*visitor.point_in(first))
    page.mouse.down()
    page.mouse.move(*visitor.point_in(last), steps=6)
    expect(song).to_have_attribute("data-range", marked)
    expect(loop).not_to_be_checked()
    assert above(first)[3] == 0 and above(last)[3] == 0
    for line in (y - 8, y + high + 7):
        rule = page.evaluate(ALONG, [x + 10, line, x_last + wide_last - x - 20])
        assert max(rule) > 128 and min(rule) == 0, rule
    # Let go: the range is from the first beat of the earlier bar to the last beat of the
    # later, the loop is on, and the position, which was outside the range, is at its
    # start. A loop starts a moment before its first beat, so the beat before it is lit.
    page.mouse.up()
    expect(song).to_have_attribute("data-range", marked)
    expect(loop).to_be_checked()
    expect(now).to_have_attribute("data-lit", str(bars[first] - 1))
    page.mouse.move(0, 0)
    # The band is on the canvas over both bars and over the room between their ochos.
    assert is_colour(above(first), band) and is_colour(above(last), band)
    assert is_colour(visitor.at(x + wide + 7, y - 7), band)
    # It is not past them. Each has the other plate of its ocho beside it, 2 away: the
    # band reaches 1 into those 2 pixels, where the upright of its bracket is, and the
    # plate beside has no band over it.
    assert above(first - 1)[3] == 0 and above(last + 1)[3] == 0
    assert [visitor.at(x - before, y - 7)[3] for before in (2, 1)] == [0, 255]
    assert [visitor.at(x_last + wide_last + after, y - 7)[3] for after in (0, 1)] == [255, 0]
    # The plate stands on the middle of each bracket, and its two ends still show above
    # the plate and under it: an upright, and a foot 10 long and 4 thick turned inward.
    for line in (y - 7, y + high + 6):
        assert all(is_colour(visitor.at(x + across, line), bracket) for across in (-1, 4, 8)), line
        assert is_colour(visitor.at(x + 9, line), band), line
        assert all(is_colour(visitor.at(x_last + wide_last - across, line), bracket) for across in (0, 4, 9)), line
        assert is_colour(visitor.at(x_last + wide_last - 10, line), band), line
    assert [visitor.at(x + 4, y - above_it)[3] for above_it in (9, 8, 5)] == [0, 255, 255]
    assert is_colour(visitor.at(x + 6, y - 4), band)
    # The band is behind the plates: the later of the two, which the block of the lit
    # bar does not touch, is its own fill to its rim.
    assert page.evaluate(BOX, [plates[last], colours["mark"], colours["mark"]])["rim"] == 0
    # In dark the band and its brackets have the colours of dark.
    page.emulate_media(color_scheme="dark")
    page.wait_for_timeout(300)
    assert is_colour(above(last), COLOURS["dark"]["loop-fill"]) and is_colour(visitor.at(x + 4, y - 7), COLOURS["dark"]["loop"])
    page.emulate_media(color_scheme="light")
    page.wait_for_timeout(300)

    # From a bar to an earlier one, over the end of a row: from the second bar of the
    # first ocho of the lower row back to the first bar of the last ocho of the upper one.
    later, earlier = lower[1], upper[-2]
    assert earlier in ochos and lower[0] in ochos
    visitor.drag_bars(later, earlier)
    expect(song).to_have_attribute("data-range", f"{bars[earlier]} {last_beat[later]}")
    expect(loop).to_be_checked()
    expect(now).to_have_attribute("data-lit", str(bars[earlier] - 1))
    page.mouse.move(0, 0)
    # It has a run in each row, over the four bars and over no other.
    assert all(is_colour(above(bar), band) for bar in (earlier, upper[-1], lower[0], later))
    assert above(earlier - 1)[3] == 0 and above(later + 1)[3] == 0
    # The run of the upper row opens with a bracket 8 before the plate of the earlier bar,
    # and reaches 8 beyond the last plate of the row, where it has no bracket.
    x, y, wide, high = plates[earlier]
    assert [visitor.at(x - before, y - 7)[3] for before in (9, 8)] == [0, 255]
    assert is_colour(visitor.at(x - 7, y + high / 2), bracket)
    x_end, _, wide_end, _ = plates[upper[-1]]
    assert is_colour(visitor.at(x_end + wide_end + 7, y + high / 2), band)
    assert visitor.at(x_end + wide_end + 8, y + high / 2)[3] == 0
    # The run of the lower row starts 8 before the first plate of the row, with no
    # bracket, and closes with a bracket 8 beyond the plate of the later bar.
    x, y, wide, high = plates[lower[0]]
    assert is_colour(visitor.at(x - 8, y + high / 2), band) and visitor.at(x - 9, y + high / 2)[3] == 0
    x, y, wide, high = plates[later]
    assert is_colour(visitor.at(x + wide + 7, y + high / 2), bracket)
    assert visitor.at(x + wide + 8, y + high / 2)[3] == 0
    # Between the two rows there is nothing: a band is 8 higher than the plates on each side.
    assert [visitor.at(x + wide / 2, y - above_it)[3] > 0 for above_it in (9, 8)] == [False, True]
    x, y, wide, high = plates[earlier]
    assert [visitor.at(x + wide / 2, y + high + under)[3] > 0 for under in (7, 8)] == [True, False]

    # A drag may leave the rows: it takes the nearest row, and in it the nearest bar. The
    # pointer goes there in one move, over no other bar on its way. Let go above the first
    # row and left of its plates, the drag ends on the first bar of the song.
    page.mouse.move(*visitor.point_in(upper[2]))
    page.mouse.down()
    page.mouse.move(*visitor.on_page(40, 3))
    page.mouse.up()
    expect(song).to_have_attribute("data-range", f"0 {last_beat[upper[2]]}")
    # Let go under the last row and right of its plates, on the last bar of the song.
    page.mouse.move(*visitor.point_in(lower[0]))
    page.mouse.down()
    page.mouse.move(*visitor.on_page(plates[lower[-1]][0] + plates[lower[-1]][2] + 30, tops[-1] + 30 + 25))
    page.mouse.up()
    expect(song).to_have_attribute("data-range", f"{bars[lower[0]]} {len(counts) - 1}")


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
    colours = COLOURS["light"]
    assert bars == bars_of(before)

    # A beat the analysis counts as 5, well inside the song: the user says it is count 1.
    # It is the first beat of a second bar, so a press on its plate reaches it.
    beat = next(n for n in range(16, len(before)) if before[n] == 5)
    bar = bars.index(beat)
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
    # The bars start where they did, and a bar starts on that beat. The bar before it stays
    # whole and stands alone: the plate of the beat now starts an ocho, 14 after it and not 2.
    assert visitor.bars() == bars_of(after) == bars
    set_plates = visitor.plates()
    x, y, wide, high = set_plates[bar]
    x_before, _, wide_before, _ = set_plates[bar - 1]
    assert (wide, wide_before) == (plates[bar][2], plates[bar - 1][2]) and x == x_before + wide_before + 14 == plates[bar][0] + 12
    # Right after the press the position is still on that beat, so its bar is the lit one.
    # Its lid shows over the block: a strip 4 high, 3 above the block and 3 wider than it
    # on each side, in the colour of the marks. The block is 5 wider than the plate on each
    # side and 6 higher.
    expect(song).to_have_attribute("data-lit", str(bar))
    page.mouse.move(0, 0)
    middle = x + wide / 2
    assert is_colour(visitor.at(middle, y - 3), colours["lit"])
    assert [visitor.at(middle, y - above)[3] for above in (14, 13, 10, 9, 7)] == [0, 255, 255, 0, 0]
    assert is_colour(visitor.at(middle, y - 12), colours["mark"])
    assert [visitor.at(x - before, y - 12)[3] for before in (9, 8)] == [0, 255]
    assert [visitor.at(x + wide + after, y - 12)[3] for after in (7, 8)] == [255, 0]
    # In dark the lid has the colour of the marks of dark, which the block has not.
    page.emulate_media(color_scheme="dark")
    page.wait_for_timeout(300)
    assert is_colour(visitor.at(middle, y - 12), COLOURS["dark"]["mark"]) and is_colour(visitor.at(middle, y - 3), COLOURS["dark"]["lit"])
    page.emulate_media(color_scheme="light")
    page.wait_for_timeout(300)
    # With the position elsewhere its plate is the plate of a first bar, with its lid: 3
    # above the plate and 3 wider than it on each side. The plate before it has none.
    visitor.press_bar(0)
    page.mouse.move(0, 0)
    for one in (bar - 1, bar):
        seen = page.evaluate(BOX, [set_plates[one], colours["mark"], colours["ground"]])
        assert seen["rim"] == 0 and seen["written"] >= 12, (one, seen)
    assert [visitor.at(middle, y - above)[3] for above in (8, 7, 4, 3, 1)] == [0, 255, 255, 0, 0]
    assert is_colour(visitor.at(middle, y - 6), colours["mark"])
    assert [visitor.at(x - before, y - 6)[3] for before in (4, 3)] == [0, 255]
    assert [visitor.at(x + wide + after, y - 6)[3] for after in (2, 3)] == [255, 0]
    assert all(visitor.at(x_before + wide_before / 2, y - above)[3] == 0 for above in range(1, 15))

    # The other browser learns of it from the list, with the song open: the count, the
    # bars, and the lid over the plate.
    expect(other.page.locator("#map")).to_have_attribute("data-by-hand", str(beat), timeout=6000)
    assert other.counts() == after
    assert other.bars() == bars and other.plates() == set_plates
    assert is_colour(other.at(middle, y - 6), colours["mark"])
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
    # A press on the plate with the lid puts the position on the beat that was set.
    visitor.press_bar(bar)
    expect(page.locator("#one")).to_have_text("Not count 1")
    page.locator("#one").click()
    expect(song).to_have_attribute("data-by-hand", "")
    expect(page.locator("#one")).to_have_text("Count 1 here")
    assert visitor.counts() == before
    # Taken back, the bars and the plates are as before, and the lid is gone: there is no
    # ink but the plates and the block of the bar the position is on.
    assert visitor.bars() == bars and visitor.plates() == plates
    page.mouse.move(0, 0)
    assert page.evaluate(STRAY, [drawn_with(plates, bar), 67])["stray"] == 0
    expect(other.page.locator("#map")).to_have_attribute("data-by-hand", "", timeout=6000)
    assert other.counts() == before
    assert [method for method, url in visitor.changes_of_count()] == ["PUT", "DELETE", "DELETE"]


def test_count_1_inside_a_bar_cuts_it_and_the_rest_of_its_row_stands_further_left(visit, files):
    visitor = visit(viewport={"width": 1280, "height": 720})
    page = visitor.page
    visitor.pick(files["longer"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    song = page.locator("#map")
    before, bars, plates = visitor.counts(), visitor.bars(), visitor.plates()
    colours = COLOURS["light"]
    # The first bar of a whole ocho in the middle of the first row, and the row under it.
    cut = whole_ochos(before, bars)[2]
    x, y, whole, high = plates[cut]
    upper, lower = ([bar for bar, plate in enumerate(plates) if plate[1] == top] for top in (28, 90))
    assert cut in upper and lower and len([bar for bar in upper if bars[bar] in ochos_of(before)]) == 8
    row_ended = plates[upper[-1]][0] + plates[upper[-1]][2]

    for kept in (3, 1):
        # A beat inside that bar is reached with a press on its plate and the right arrow,
        # and set to count 1.
        beat = bars[cut] + kept
        visitor.press_beat(beat)
        expect(page.locator("#now")).to_have_attribute("data-lit", str(beat))
        expect(page.locator("#one")).to_have_text("Count 1 here")
        # The control is pressed from the keyboard, with the pointer at rest on the second
        # plate of the row under.
        rest_x, rest_y = plates[lower[1]][0] + plates[lower[1]][2] / 2, plates[lower[1]][1] + 15
        page.mouse.move(*visitor.on_page(rest_x, rest_y))
        assert is_colour(visitor.over(lower[1]), colours["hover"])
        page.locator("#one").focus()
        page.keyboard.press("Enter")
        expect(song).to_have_attribute("data-by-hand", str(beat))
        after = before[:beat] + [(n - beat) % 8 + 1 for n in range(beat, len(before))]
        assert visitor.counts() == after
        # The bar is cut: what is left of it ends before the beat, and a bar starts on the
        # beat. That one is lit, with its lid.
        cut_bars, cut_plates = visitor.bars(), visitor.plates()
        assert cut_bars == bars_of(after) and len(cut_plates) == len(cut_bars)
        assert cut_bars[: cut + 2] == bars[: cut + 1] + [beat]
        expect(song).to_have_attribute("data-lit", str(cut + 1))
        # The bars are other ones now and the pointer has not moved. No bar has a halo
        # but the one that is under the pointer now: there is no ink but the plates, the
        # block of the lit bar with its lid, and what a halo there would cover.
        left, top, across, _ = cut_plates[cut + 1]
        under = [[px - 4, py - 4, pw + 8, ph + 8] for px, py, pw, ph in cut_plates if px <= rest_x < px + pw and py <= rest_y < py + ph]
        assert len(under) == 1 and cut_plates.index([side + 4 for side in under[0][:2]] + [side - 8 for side in under[0][2:]]) != lower[1]
        assert page.evaluate(STRAY, [drawn_with(cut_plates, cut + 1) + [[left - 8, top - 13, across + 16, 4]] + under, 67])["stray"] == 0
        # The plate of what is left is narrower in the proportion of its beats, and the
        # plate of the new bar is whole.
        narrow = math.floor(whole * kept / 4 + 0.5)
        assert cut_plates[cut] == [x, y, narrow, high] and cut_plates[cut + 1][2] == whole
        # What is left is an ocho by itself, and a short one. It takes less room, so the
        # ocho after it stands 14 after its plate, and the rest of the row further left
        # than a whole ocho would leave it. The row still holds eight ochos.
        assert cut_plates[cut + 1][:2] == [x + narrow + 14, y]
        in_row = [bar for bar, plate in enumerate(cut_plates) if plate[1] == y]
        assert len([bar for bar in in_row if cut_bars[bar] in ochos_of(after)]) == 8
        assert cut_plates[in_row[-1]][0] + cut_plates[in_row[-1]][2] == row_ended - (2 * whole + 2 - narrow)
        # The next row starts in line, at the left.
        assert cut_plates[in_row[-1] + 1][:2] == [80, y + 62]
        # On the canvas: with the position elsewhere there is no ink but the plates, the
        # block of the lit bar, and the lid of the new bar.
        visitor.press_bar(0)
        page.mouse.move(0, 0)
        left, top, across, _ = cut_plates[cut + 1]
        assert page.evaluate(STRAY, [drawn_with(cut_plates, 0) + [[left - 3, top - 7, across + 6, 4]], 67])["stray"] == 0
        # The narrower plate is a first bar's, with its count if it has the room for one:
        # a plate narrower than 14 has none.
        seen = page.evaluate(BOX, [cut_plates[cut], colours["mark"], colours["ground"]])
        assert seen["rim"] == 0 and (seen["written"] >= 12 if narrow >= 14 else seen["written"] == 0), (kept, seen)
        seen = page.evaluate(BOX, [cut_plates[cut + 1], colours["mark"], colours["ground"]])
        assert seen["rim"] == 0 and seen["written"] >= 12, (kept, seen)
        assert is_colour(visitor.at(left + across / 2, top - 6), colours["mark"])

        # Taken back, with a press on the plate that has the lid: the bars and the plates
        # are as before.
        visitor.press_bar(cut + 1)
        expect(page.locator("#now")).to_have_attribute("data-lit", str(beat))
        expect(page.locator("#one")).to_have_text("Not count 1")
        page.locator("#one").click()
        expect(song).to_have_attribute("data-by-hand", "")
        assert visitor.counts() == before and visitor.bars() == bars and visitor.plates() == plates
        page.mouse.move(0, 0)
        assert page.evaluate(STRAY, [drawn_with(plates, cut), 67])["stray"] == 0


def test_the_song_scrolls_so_that_the_row_of_the_playing_position_is_on_screen(visit, files):
    # A window too low for the three rows this song has in it: the song scrolls.
    visitor = visit(viewport={"width": 1100, "height": 520})
    page = visitor.page
    visitor.pick(files["longer"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    beats = visitor.beats(LONGER)
    bars, plates = visitor.bars(), visitor.plates()
    tops = sorted({top for left, top, across, down in plates})
    assert len(tops) == 3

    def seen():
        """What part of the canvas of the song is on screen: from where to where, down it."""
        top, high, whole = page.locator("#song").evaluate("(part) => [part.scrollTop, part.clientHeight, part.scrollHeight]")
        assert 62 <= high < whole, "the window must hold a row and not the whole song"
        return top, top + high

    def row_of(beat):
        """The band of the row a beat is in: from 16 above its plates to 16 under them."""
        top = plates[max(bar for bar, first in enumerate(bars) if first <= beat)][1]
        return top - 16, top + 30 + 16

    # The song opens at its top. The position goes to a beat of the last row: the song
    # scrolls, and the whole band of that row is on screen.
    assert seen()[0] == 0
    beat = bars[min(bar for bar, plate in enumerate(plates) if plate[1] == tops[-1])] + 1
    assert row_of(beat)[0] == tops[-1] - 16 and row_of(beat)[1] > seen()[1]
    page.locator("#seek").fill(str(beats[beat]))
    expect(page.locator("#now")).to_have_attribute("data-lit", str(beat))
    assert seen()[0] > 0 and seen()[0] <= row_of(beat)[0] and row_of(beat)[1] <= seen()[1], (seen(), row_of(beat))
    # Back on a beat of the first row, the song is at its top again.
    page.locator("#seek").fill(str(beats[2]))
    expect(page.locator("#now")).to_have_attribute("data-lit", "2")
    assert seen()[0] == 0


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


def test_a_press_with_the_pointer_leaves_space_to_play_and_pause(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["tagged"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    play = page.locator("#play")

    def space_plays_and_pauses():
        page.keyboard.press("Space")
        expect(play).to_have_text("Pause")
        page.keyboard.press("Space")
        expect(play).to_have_text("Play")

    # An end of the loop is set with the pointer. Space then plays: it does not press the
    # control again.
    visitor.press_beat(10)
    page.locator("#loop-start").click()
    start = f"From {clock(visitor.beats(TAGGED)[10])}"
    expect(page.locator("#loop-range")).to_have_text(start)
    space_plays_and_pauses()
    expect(page.locator("#loop-range")).to_have_text(start)

    # Clear is gone once it is pressed. The keyboard is not put on the control beside it.
    page.locator("#loop-clear").click()
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")
    space_plays_and_pauses()
    expect(page.locator("#loop-range")).to_have_text("Drag across bars")

    # The switch of the loop, pressed on its name.
    visitor.drag_bars(2, 3)
    expect(page.locator("#loop")).to_be_checked()
    page.locator("#loop-label").click()
    expect(page.locator("#loop")).not_to_be_checked()
    space_plays_and_pauses()
    expect(page.locator("#loop")).not_to_be_checked()

    # Count 1 set with the pointer is not taken back by the Space that follows.
    visitor.press_beat(10)
    page.locator("#one").click()
    expect(page.locator("#map")).to_have_attribute("data-by-hand", "10")
    space_plays_and_pauses()
    visitor.press_beat(10)
    expect(page.locator("#map")).to_have_attribute("data-by-hand", "10")
    assert [method for method, _ in visitor.changes_of_count()] == ["PUT"]

    # A control the keyboard went to by itself keeps the key.
    page.locator("#loop").focus()
    page.keyboard.press("Space")
    expect(page.locator("#loop")).to_be_checked()
    expect(play).to_have_text("Play")


def test_a_song_that_is_ready_while_another_plays_does_not_cut_it_off(visit, files):
    visitor = visit()
    page = visitor.page
    visitor.pick(files["longer"])
    expect(page.locator("#player")).to_be_visible(timeout=READY)
    # In a loop the song goes on for as long as the other one takes.
    visitor.drag_bars(2, 3)
    page.locator("#play").click()
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")

    visitor.pick(files["tagged"])
    row = visitor.row(TAGGED)
    # The page does not promise to open it.
    expect(page.locator("#message")).to_have_text(f"{TAGGED} is in the library. It is ready when it has been analysed.", timeout=READY)
    expect(row).to_have_attribute("data-state", "ready", timeout=READY)
    expect(page.locator("#message")).to_have_text(f"{TAGGED} is ready. Open it from the list.")
    expect(page.locator("#song-name")).to_have_text(LONGER)
    expect(page.locator("#player")).to_have_attribute("data-state", "looping")
    # It waits in the list, and opens when it is asked for.
    row.get_by_role("button", name="Open").click()
    expect(page.locator("#song-name")).to_have_text(TAGGED)


def test_the_list_says_how_long_an_analysis_has_run_and_what_to_do_when_it_failed(visit):
    visitor = visit()
    page = visitor.page
    # The list is answered here, so that the song stays in each state for as long as needed.
    song = {"id": "ab" * 16, "name": "Una", "seconds": 200.0, "ones": []}
    state = {"now": "waiting"}
    page.route("**/api/songs", lambda route: route.fulfill(json=[{**song, "state": state["now"]}]))
    said = visitor.row("Una").locator(".state")
    expect(said).to_have_text("3:20, waiting")
    state["now"] = "analysing"
    expect(said).to_have_text(re.compile(r"^3:20, being analysed for 0:0[0-2]$"))
    expect(said).to_have_text(re.compile(r"^3:20, being analysed for 0:0[4-9]$"), timeout=12_000)

    state["now"] = "failed"
    expect(said).to_have_text("3:20, failed")
    expect(visitor.row("Una").locator(".note")).to_have_text(
        "The analysis failed. To try again, delete the song and add the file again."
    )

    # An analysis that was running when the page was loaded: the page cannot say for how long.
    state["now"] = "analysing"
    page.reload()
    expect(said).to_have_text("3:20, being analysed")
    page.wait_for_timeout(4500)
    expect(said).to_have_text("3:20, being analysed")


def test_a_song_that_does_not_reach_the_server_is_said_so(visit, files):
    visitor = visit()
    page = visitor.page
    page.route(
        re.compile(r"/api/songs/[0-9a-f]+\?"),
        lambda route: route.abort() if route.request.method == "PUT" else route.continue_(),
    )
    visitor.pick(files["tagged"])
    message = page.locator("#message")
    expect(message).to_have_text("The song did not reach the server. It was not added.", timeout=READY)
    expect(message).to_have_class(re.compile("refused"))
    expect(page.locator("#empty")).to_be_visible()
    # The browser logs the request that was cut. Nothing else went wrong.
    assert all("ERR_FAILED" in error or "NS_ERROR" in error or "404" in error for error in visitor.errors), visitor.errors
    visitor.errors.clear()


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
