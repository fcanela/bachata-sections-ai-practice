import io
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bachata import places
from bachata.places import bars_of, beat_at, counts_with, missing, nearest_beat, place_in, place_of
from bachata.store import RATE, Store

HUELLAS = "3f2a9c" + "0" * 26
HEROE = "3f2b" + "1" * 28
SONG_JS = Path(__file__).parent.parent / "web" / "song.js"


def eights(length, first=0):
    return [(n - first) % 8 + 1 for n in range(length)]


def keep(data, song_id, name, beats=None, count=None, ones=(), added=1, version=5, bpm=None):
    """A song in a library, written as the store writes one. Without beats it has no result yet."""
    folder = Path(data) / "songs" / song_id
    folder.mkdir(parents=True)
    frames = round(((beats[-1] if beats else 30) + 1) * RATE)
    song = {"id": song_id, "name": name, "frames": frames, "added": added, "ones": list(ones)}
    (folder / "song.json").write_text(json.dumps(song))
    if beats is not None:
        result = {"version": version, "beats": beats, "bpm": bpm or [128.0] * len(beats), "bar": [], "count": count}
        (folder / "result.json").write_text(json.dumps(result))


@pytest.fixture
def data(tmp_path):
    """Two songs. Sus Huellas: 40 beats half a second apart from 0.52 s, the count starting on 7."""
    beats = [round(0.52 + n * 0.47, 2) for n in range(40)]
    bpm = [127.6] * 20 + [128.5] * 20
    keep(tmp_path, HUELLAS, "Romeo Santos - Sus Huellas", beats, eights(40, 2), bpm=bpm)
    keep(tmp_path, HEROE, "Romeo Santos - Héroe Favorito", [1.0, 1.5, 2.0, 2.5], eights(4), added=2, version=4)
    return tmp_path


def run(data, *arguments):
    """A command on a library: its status, what it printed, and what it said went wrong."""
    out, err = io.StringIO(), io.StringIO()
    status = places.command(list(arguments), data, out, err)
    return status, out.getvalue(), err.getvalue()


def test_where_prints_the_song_the_place_its_bar_and_a_link(data):
    assert run(data, "where", "huellas", "4.3") == (
        0,
        f"Romeo Santos - Sus Huellas  {HUELLAS}  analysis 5\n"
        "bar 4, beat 3   6.16 s   count 3   128 BPM\n"
        "bar 4: 5.22 5.69 6.16 6.63\n"
        f"link: ?song={HUELLAS}&at=4.3\n",
        "",
    )
    # A bar alone is its first beat, and the first bar of this song is short.
    assert run(data, "where", "huellas", "4")[1].splitlines()[1] == "bar 4, beat 1   5.22 s   count 1   128 BPM"
    assert run(data, "where", "huellas", "1.2")[1].splitlines()[1:3] == ["bar 1, beat 2   0.99 s   count 8   128 BPM", "bar 1: 0.52 0.99"]
    # The tempo is the one of the beat, rounded as the page rounds it: 128.5 is 129.
    assert run(data, "where", "huellas", "7.1")[1].splitlines()[1] == "bar 7, beat 1   10.86 s   count 5   129 BPM"
    assert run(data, "where", HEROE, "1.1")[1].splitlines()[0] == f"Romeo Santos - Héroe Favorito  {HEROE}  analysis 4"


def test_where_takes_a_time_and_prints_the_place_of_the_nearest_beat(data):
    at_the_beat = run(data, "where", "huellas", "4.3")
    assert run(data, "where", "huellas", "6.16s") == at_the_beat
    # 5.93 s is nearer to 6.16 than to 5.69, and 5.92 the other way.
    assert run(data, "where", "huellas", "5.93s") == at_the_beat
    assert run(data, "where", "huellas", "5.92s")[1].splitlines()[1].startswith("bar 4, beat 2   5.69 s")
    assert run(data, "where", "huellas", "0s")[1].splitlines()[1].startswith("bar 1, beat 1   0.52 s")
    # The last beat is at 18.85 s and the song ends a second after it.
    assert run(data, "where", "huellas", "19.85s")[1].splitlines()[1].startswith("bar 11, beat 2   18.85 s")
    assert run(data, "where", "huellas", "19.9s") == (1, "", "This song ends before 19.9 s.\n")
    assert run(data, "where", "huellas", "62s") == (1, "", "This song ends before 62 s.\n")


def test_bars_prints_every_bar_and_marks_a_short_one_and_one_set_by_hand(data):
    # A count 1 on the twelfth beat, one beat into the fourth bar.
    Store(data).set_one(HUELLAS, 5.69, True)
    status, out, err = run(data, "bars", "huellas")
    assert (status, err) == (0, "")
    assert out.splitlines() == [
        f"Romeo Santos - Sus Huellas  {HUELLAS}  analysis 5  40 beats  12 bars",
        "  1    0.52 s  count 7  2 beats",
        "  2    1.46 s  count 1",
        "  3    3.34 s  count 5",
        "  4    5.22 s  count 1  1 beat",
        "  5    5.69 s  count 1  by hand",
        "  6    7.57 s  count 5",
        "  7    9.45 s  count 1",
        "  8   11.33 s  count 5",
        "  9   13.21 s  count 1",
        " 10   15.09 s  count 5",
        " 11   16.97 s  count 1",
        " 12   18.85 s  count 5  1 beat",
    ]


def test_the_numbers_stay_in_line_in_a_song_of_a_thousand_bars(tmp_path):
    keep(tmp_path, HUELLAS, "Long", [round(n * 0.2, 2) for n in range(4000)], eights(4000))
    lines = run(tmp_path, "bars", "long")[1].splitlines()
    assert lines[1] == "   1    0.00 s  count 1"
    assert lines[1000] == "1000  799.20 s  count 5"


def test_a_count_1_set_through_the_store_moves_the_numbers_the_commands_print(data):
    before = run(data, "where", "huellas", "6.16s")[1].splitlines()
    assert before[1:] == ["bar 4, beat 3   6.16 s   count 3   128 BPM", "bar 4: 5.22 5.69 6.16 6.63", f"link: ?song={HUELLAS}&at=4.3"]
    store = Store(data)
    store.set_one(HUELLAS, 5.69, True)
    after = run(data, "where", "huellas", "6.16s")[1].splitlines()
    assert after[1:] == ["bar 5, beat 2   6.16 s   count 2   128 BPM", "bar 5: 5.69 6.16 6.63 7.10", f"link: ?song={HUELLAS}&at=5.2"]
    # The same number is another place now.
    assert run(data, "where", "huellas", "4.3") == (1, "", "Bar 4 has no beat 3.\n")
    store.set_one(HUELLAS, 5.69, False)
    assert run(data, "where", "huellas", "6.16s")[1].splitlines() == before


def test_a_song_is_found_by_its_id_the_start_of_it_or_a_part_of_its_name(data):
    def found(asked):
        status, out, _ = run(data, "bars", asked)
        return status == 0 and out.split("  ")[1]

    assert found(HUELLAS) == HUELLAS
    assert found("3f2a") == HUELLAS
    assert found("3f2b") == HEROE
    assert found("Sus Huellas") == HUELLAS
    assert found("HUELLAS") == HUELLAS
    # With or without its accent, whichever way the accent is written.
    assert found("heroe") == HEROE
    assert found("héroe") == HEROE
    assert found("héroe") == HEROE
    # A whole id is that song, also when it is in the name of another one.
    keep(data, "c" * 32, f"A copy of {HUELLAS}", added=3)
    assert found(HUELLAS) == HUELLAS
    # A folder that is not a song's is not read, as the store does not read it.
    shutil.copytree(data / "songs" / HUELLAS, data / "songs" / "a copy by hand")
    assert found("sus huellas") == HUELLAS


def test_a_song_stored_before_count_1_could_be_set_has_none(data):
    file = data / "songs" / HUELLAS / "song.json"
    song = json.loads(file.read_text())
    del song["ones"]
    file.write_text(json.dumps(song))
    assert run(data, "where", "huellas", "4.3")[1].splitlines()[1] == "bar 4, beat 3   6.16 s   count 3   128 BPM"
    assert run(data, "bars", "huellas")[1].splitlines()[4] == "  4    5.22 s  count 1"


def test_no_song_and_more_than_one_end_with_status_2_and_print_no_place(data):
    both = f"{HUELLAS}  Romeo Santos - Sus Huellas\n{HEROE}  Romeo Santos - Héroe Favorito\n"
    assert run(data, "where", "romeo", "1.1") == (2, "", 'More than one song matches "romeo":\n' + both)
    assert run(data, "bars", "3f2") == (2, "", 'More than one song matches "3f2":\n' + both)
    assert run(data, "bars", "prince") == (2, "", 'No song matches "prince". The songs:\n' + both)
    # The middle of an id is not the start of it.
    assert run(data, "bars", "f2a9c")[0] == 2
    assert run(data / "nothing here", "bars", "huellas") == (2, "", f"The library at {data / 'nothing here'} has no songs.\n")


def test_what_cannot_be_answered_is_said_in_one_sentence(data):
    keep(data, "d" * 32, "Not analysed", added=3)
    assert run(data, "bars", "not analysed") == (1, "", "Not analysed has no result yet.\n")
    assert run(data, "where", "not analysed", "1.1") == (1, "", "Not analysed has no result yet.\n")
    assert run(data, "where", "huellas", "12") == (1, "", "There is no bar 12 in this song.\n")
    assert run(data, "where", "huellas", "11.4") == (1, "", "Bar 11 has no beat 4.\n")
    assert run(data, "where", "huellas", "62.4sec") == (2, "", '"62.4sec" is not a place. Write 24.3, 24 or 62.4s.\n')
    assert run(data, "where", "huellas", "x") == (2, "", '"x" is not a place. Write 24.3, 24 or 62.4s.\n')


def test_a_command_that_is_not_one_ends_with_status_2(data, capsys):
    for arguments in (["sections", "huellas"], ["where", "huellas"], ["bars"], ["bars", "huellas", "4.3"]):
        assert run(data, *arguments) == (2, "", "")
        assert "usage: python -m bachata" in capsys.readouterr().err


def everything_under(folder):
    return {str(path.relative_to(folder)): path.is_dir() or (path.read_bytes(), path.stat().st_mtime_ns) for path in folder.rglob("*")}


def test_the_commands_write_nothing_in_the_library(data):
    keep(data, "d" * 32, "Not analysed", added=3)
    (data / "tmp").mkdir()
    (data / "tmp" / "an upload on its way").write_bytes(b"half")
    before = everything_under(data)
    for arguments in (["bars", "huellas"], ["where", "huellas", "4.3"], ["where", "huellas", "99"], ["bars", "romeo"], ["bars", "not"]):
        run(data, *arguments)
    assert everything_under(data) == before
    # A library that is not there is not made.
    run(data / "nothing here", "bars", "huellas")
    assert not (data / "nothing here").exists()


def test_the_program_runs_a_command_on_the_folder_the_setting_names_and_loads_no_torch(data):
    # What `python -m bachata bars 3f2a` does, and then which modules it loaded.
    script = (
        "import runpy, sys\n"
        "sys.argv = ['bachata', 'bars', '3f2a']\n"
        "try:\n"
        "    runpy.run_module('bachata', run_name='__main__')\n"
        "except SystemExit as stop:\n"
        "    print('status', stop.code)\n"
        "print('loaded', sorted(name for name in ('torch', 'torchaudio', 'beat_this', 'madmom') if name in sys.modules))\n"
    )
    ran = subprocess.run([sys.executable, "-c", script], env={**os.environ, "BACHATA_DATA": str(data)}, capture_output=True, text=True)
    lines = ran.stdout.splitlines()
    assert lines[0] == f"Romeo Santos - Sus Huellas  {HUELLAS}  analysis 5  40 beats  11 bars"
    assert lines[-2:] == ["status 0", "loaded []"]
    # And the status is the program's own.
    ran = subprocess.run([sys.executable, "-m", "bachata", "where", "3f2a", "99"], env={**os.environ, "BACHATA_DATA": str(data)}, capture_output=True, text=True)
    assert (ran.returncode, ran.stdout, ran.stderr) == (1, "", "There is no bar 99 in this song.\n")


def test_a_command_does_not_ask_for_the_checkpoints_or_start_the_server(data, monkeypatch, capsys):
    from bachata import __main__ as program
    from bachata import model

    monkeypatch.setenv("BACHATA_DATA", str(data))
    monkeypatch.setattr(model, "MODEL_PATH", data / "not-fetched.ckpt")
    monkeypatch.setattr(model, "PARTS_PATH", data / "not-fetched.pt")
    monkeypatch.setattr(program, "create_app", lambda data: pytest.fail("the program went on to start"))
    assert program.run(["where", "huellas", "4.3"]) == 0
    assert capsys.readouterr().out.splitlines()[1] == "bar 4, beat 3   6.16 s   count 3   128 BPM"
    # With no argument it is the server, which does ask for them.
    with pytest.raises(RuntimeError, match="not-fetched.ckpt is missing"):
        program.run([])


TEXTS = ["1", "1.1", "1.2", "1.4", "2.4", "3", "3.3", "7.2", "40.1", "41", "99.9", "0", "24.0", "24.10", "1e3", "-1", "x", ""]
TEXTS += ["0s", "3.2s", "3.25s", "17.999s", "19s", "500s", "62.4", "62.4 s", "12345.678s", "123456s", "1.2345s", "024", "1234567"]

# What web/song.js makes of the same songs: for each, its count, its beats set by hand, its
# bars, the place of every beat, and for every text the place it names and the beat there.
IN_THE_PAGE = """
import { barsOf, beatAt, countsWith, missing, nearestBeat, placeIn, placeOf } from %s
let text = ''
for await (const chunk of process.stdin) text += chunk
const { songs, texts } = JSON.parse(text)
const answers = songs.map(({ beats, count, ones, duration, times }) => {
  const counted = countsWith(beats, count, ones)
  const bars = barsOf(counted.count)
  const read = texts.map((one) => {
    const place = placeIn(one)
    if (place === null) return null
    const beat = beatAt(bars, beats, place, duration)
    return [place.seconds ?? [place.bar, place.beat], beat, beat < 0 ? missing(bars, place) : null]
  })
  return {
    count: counted.count,
    byHand: counted.byHand,
    bars: bars.map((bar) => [bar.first, bar.last]),
    places: beats.map((_, beat) => placeOf(bars, beat)).map((place) => [place.bar, place.beat]),
    nearest: times.map((seconds) => nearestBeat(beats, seconds)),
    read,
  }
})
console.log(JSON.stringify(answers))
"""


def some_songs():
    """Songs of every kind the count can take: a late start, jumps, short bars, counts set by hand, none at all."""
    dice = random.Random(8)
    songs = [{"beats": [], "count": [], "ones": [], "duration": 30.0, "times": [0.0, 3.0]}]
    for _ in range(200):
        length = dice.randint(1, 120)
        beats, at = [], dice.uniform(0, 3)
        for _ in range(length):
            beats.append(round(at, 2))
            at += dice.uniform(0.3, 0.7)
        count, value = [], dice.randint(1, 8)
        for _ in range(length):
            count.append(value)
            value = dice.randint(1, 8) if dice.random() < 0.05 else value % 8 + 1
        # Count 1s as the page sends them, a little off a beat or far from any, and one twice.
        ones = [round(dice.choice(beats) + dice.uniform(-0.3, 0.3), 2) for _ in range(dice.choice([0, 0, 1, 2, 5]))]
        ones += ones[:1] + [dice.uniform(-5, at + 5)] * dice.randint(0, 1)
        # Times on a beat, half way between two, and anywhere.
        times = [beats[0], (beats[0] + beats[-1]) / 2] + [(a + b) / 2 for a, b in zip(beats, beats[1:])][:10] + [dice.uniform(-1, at + 1) for _ in range(10)]
        songs.append({"beats": beats, "count": count, "ones": ones, "duration": dice.choice([at, beats[-1], beats[-1] - 0.5]), "times": times})
    return songs


def test_python_and_the_page_number_the_bars_of_a_song_alike():
    node = shutil.which("node")
    if node is None:
        pytest.skip("skipped: node is not installed")
    songs = some_songs()
    script = IN_THE_PAGE % json.dumps(SONG_JS.as_uri())
    ran = subprocess.run([node, "--input-type=module", "-e", script], input=json.dumps({"songs": songs, "texts": TEXTS}), capture_output=True, text=True)
    assert ran.returncode == 0, ran.stderr[-2000:]
    in_the_page = json.loads(ran.stdout)
    assert len(in_the_page) == len(songs)
    short = by_hand = 0
    for song, page in zip(songs, in_the_page):
        beats, duration = song["beats"], song["duration"]
        count, set_by_hand = counts_with(beats, song["count"], song["ones"])
        bars = bars_of(count)
        assert count == page["count"]
        assert set_by_hand == page["byHand"]
        assert [list(bar) for bar in bars] == page["bars"]
        assert [list(place_of(bars, beat)) for beat in range(len(beats))] == page["places"]
        assert [nearest_beat(beats, seconds) for seconds in song["times"]] == page["nearest"]
        read = []
        for text in TEXTS:
            place = place_in(text)
            if place is None:
                read.append(None)
                continue
            beat = beat_at(bars, beats, place, duration)
            read.append([place if isinstance(place, float) else list(place), beat, missing(bars, place) if beat < 0 else None])
        assert read == page["read"]
        short += sum(last - first != 3 for first, last in bars)
        by_hand += len(set_by_hand)
    # The songs did have what the two could disagree on.
    assert short > 100 and by_hand > 100
    assert sum(one is not None and one[1] >= 0 for page in in_the_page for one in page["read"]) > 1000
