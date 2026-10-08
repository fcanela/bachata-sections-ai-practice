"""A name for every bar and beat, and the two commands that speak it.

    uv run python -m bachata where <song> <place>    what the analysis has at one place
    uv run python -m bachata bars <song>             every bar of the song, one a line

A place is a bar and a beat, written 24.3: bar 24, beat 3. 24 alone is the first beat of
the bar. A time is written with an s, 62.4s, and names the beat nearest to it. `<song>` is
an id, the start of one, or a part of a name.

Bars are counted as the page shows them: from 1, a new one at every count 1 and count 5,
with the count 1s the user set by hand. The first half of this file is the twin of
`nearestBeat`, `countsWith`, `barsOf`, `placeOf`, `placeIn`, `beatAt` and `missing` in
web/song.js. places_test.py runs both on the same songs and compares them.

The commands read the library on disk. They need no running server and change nothing.
A number may name another place after a count 1 is set or a song is analysed again: the
seconds printed beside it are what stays true.
"""

import argparse
import json
import math
import re
import sys
import unicodedata
from bisect import bisect_right
from pathlib import Path

from bachata.store import RATE, well_formed

OCHO = 8

NAMED = re.compile(r"([1-9][0-9]{0,5})(?:\.([1-9]))?")
TIMED = re.compile(r"([0-9]{1,5}(?:\.[0-9]{1,3})?)s")


def nearest_beat(beats, seconds):
    """The beat nearest to a time in seconds, or -1 when there is no beat."""
    after = bisect_right(beats, seconds)
    if after == 0:
        return 0 if beats else -1
    if after == len(beats):
        return after - 1
    return after - 1 if seconds - beats[after - 1] <= beats[after] - seconds else after


def counts_with(beats, count, ones):
    """The count of every beat with the beats the user set to count 1, and those beats."""
    by_hand = sorted({nearest_beat(beats, seconds) for seconds in ones} - {-1})
    counted = list(count)
    for first, end in zip(by_hand, by_hand[1:] + [len(beats)]):
        for beat in range(first, end):
            counted[beat] = (beat - first) % OCHO + 1
    return counted, by_hand


def bars_of(count):
    """The bars of a song, each (first, last), beats, both included."""
    bars = []
    for beat, value in enumerate(count):
        if beat > 0 and value != 5 and value == count[beat - 1] + 1:
            bars[-1] = (bars[-1][0], beat)
        else:
            bars.append((beat, beat))
    return bars


def place_of(bars, beat):
    """The bar and the beat in it, both from 1, of a beat of the song. None when it has no such beat."""
    bar = bisect_right([first for first, _ in bars], beat) - 1
    if bar < 0 or beat > bars[bar][1]:
        return None
    return bar + 1, beat - bars[bar][0] + 1


def place_in(text):
    """The place a text names: (bar, beat), or a time in seconds as a float. None for anything else."""
    if named := NAMED.fullmatch(text):
        return int(named[1]), int(named[2] or 1)
    if timed := TIMED.fullmatch(text):
        return float(timed[1])
    return None


def beat_at(bars, beats, place, duration):
    """The beat at a place, or -1 when the song has no such place."""
    if isinstance(place, float):
        return nearest_beat(beats, place) if place <= duration else -1
    bar, beat = place
    if bar > len(bars):
        return -1
    first, last = bars[bar - 1]
    return first + beat - 1 if first + beat - 1 <= last else -1


def missing(bars, place):
    """What to say of a place the song does not have."""
    if isinstance(place, float):
        # The time as the page writes it: 62 and not 62.0.
        return f"This song ends before {repr(place).removesuffix('.0')} s." if bars else "This song has no beats."
    if place[0] > len(bars):
        return f"There is no bar {place[0]} in this song."
    return f"Bar {place[0]} has no beat {place[1]}."


class Stop(Exception):
    """A command cannot go on: what to say, and the status to end with."""

    def __init__(self, text, status):
        self.text, self.status = text, status


def folded(text):
    """A name as it is compared: no capitals and no accents."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold()


def songs_in(data):
    """Every song of the library, as its song.json has it, in the order they arrived."""
    songs = []
    folder = Path(data) / "songs"
    for song_folder in folder.iterdir() if folder.is_dir() else []:
        if well_formed(song_folder.name):
            try:
                songs.append({"ones": []} | json.loads((song_folder / "song.json").read_text()))
            except FileNotFoundError:
                pass
    return sorted(songs, key=lambda song: (song["added"], song["id"]))


def found(data, asked):
    """The one song `asked` names: by its id, by the start of it, or by a part of its name."""
    songs = songs_in(data)
    matches = [song for song in songs if song["id"] == asked]
    if not matches:
        part = folded(asked)
        matches = [song for song in songs if song["id"].startswith(asked) or part in folded(song["name"])]
    if len(matches) == 1:
        return matches[0]
    if not songs:
        raise Stop(f"The library at {data} has no songs.", 2)
    says = f'More than one song matches "{asked}":' if matches else f'No song matches "{asked}". The songs:'
    raise Stop("\n".join([says] + [f"{song['id']}  {song['name']}" for song in matches or songs]), 2)


def counted(data, song):
    """What the commands need of a song: its result, its count and bars as the page shows them."""
    try:
        result = json.loads((Path(data) / "songs" / song["id"] / "result.json").read_text())
    except FileNotFoundError:
        raise Stop(f"{song['name']} has no result yet.", 1) from None
    count, by_hand = counts_with(result["beats"], result["count"], song["ones"])
    return result, count, bars_of(count), by_hand


def where(data, asked, text):
    place = place_in(text)
    if place is None:
        raise Stop(f'"{text}" is not a place. Write 24.3, 24 or 62.4s.', 2)
    song = found(data, asked)
    result, count, bars, _ = counted(data, song)
    beats = result["beats"]
    beat = beat_at(bars, beats, place, song["frames"] / RATE)
    if beat < 0:
        raise Stop(missing(bars, place), 1)
    bar, in_bar = place_of(bars, beat)
    first, last = bars[bar - 1]
    return [
        f"{song['name']}  {song['id']}  analysis {result['version']}",
        # The tempo as the page rounds it.
        f"bar {bar}, beat {in_bar}   {beats[beat]:.2f} s   count {count[beat]}   {math.floor(result['bpm'][beat] + 0.5)} BPM",
        f"bar {bar}: " + " ".join(f"{seconds:.2f}" for seconds in beats[first : last + 1]),
        f"link: ?song={song['id']}&at={bar}.{in_bar}",
    ]


def bars(data, asked):
    song = found(data, asked)
    result, count, bars, by_hand = counted(data, song)
    beats = result["beats"]
    wide = max(3, len(str(len(bars))))
    lines = [f"{song['name']}  {song['id']}  analysis {result['version']}  {len(beats)} beats  {len(bars)} bars"]
    for number, (first, last) in enumerate(bars, 1):
        line = f"{number:>{wide}}  {beats[first]:6.2f} s  count {count[first]}"
        if last - first + 1 != OCHO // 2:
            line += f"  {last - first + 1} beat{'s' if last > first else ''}"
        if first in by_hand:
            line += "  by hand"
        lines.append(line)
    return lines


def command(arguments, data, out=None, err=None):
    """Runs `where` or `bars` on the library in `data`. Returns the status to end with."""
    out, err = out or sys.stdout, err or sys.stderr
    parser = argparse.ArgumentParser(prog="python -m bachata", description="With no command, starts the server.")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("where", help="what the analysis has at one place of a song")
    one.add_argument("song", help="an id, the start of one, or a part of a name")
    one.add_argument("place", help="24.3 for bar 24, beat 3; 24 for the bar; 62.4s for a time")
    every = commands.add_parser("bars", help="every bar of a song, one a line")
    every.add_argument("song", help="an id, the start of one, or a part of a name")
    try:
        asked = parser.parse_args(arguments)
    except SystemExit as stop:
        return stop.code
    try:
        lines = where(data, asked.song, asked.place) if asked.command == "where" else bars(data, asked.song)
    except Stop as stop:
        print(stop.text, file=err)
        return stop.status
    print("\n".join(lines), file=out)
    return 0
