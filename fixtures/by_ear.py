"""The owner's ear as a reference: the counts he checked by listening, and the count as it was.

    fixtures/audio/by-ear.json    his marks and notes, never committed
    fixtures/audio/entry-pairs.json   six songs he heard in pairs of clips, with the songs
                                  in fixtures/audio/entries/, never committed
    fixtures/by_ear_before.json   the beats and the count of the songs that must not get
                                  worse, as version 2 of the analysis gave them

Both are for checks only. The analysis must never read them, nor the label files, nor
the marks in the library: reading() is how a check sees that it did not.

What a check compares the analysis with:

- count_at(): the count shown at a time he marked.
- kept(): how many beats of a stretch still have the count they had.
"""

import contextlib
import json
import os
import sys
from pathlib import Path

from fixtures.validate import SAME_BEAT_S

BY_EAR = Path(__file__).parent / "audio" / "by-ear.json"
BEFORE = Path(__file__).parent / "by_ear_before.json"
ENTRY_PAIRS = Path(__file__).parent / "audio" / "entry-pairs.json"


def read_by_ear():
    """His songs by id, or nothing when the reference is not on the machine."""
    if not BY_EAR.exists():
        return {}
    return {song["id"]: song for song in json.loads(BY_EAR.read_text())["songs"]}


def read_entry_pairs():
    """The songs he heard in pairs of clips, or nothing when they are not on the machine."""
    if not ENTRY_PAIRS.exists():
        return []
    return json.loads(ENTRY_PAIRS.read_text())["songs"]


def read_before():
    """The beats and the count each song had, by id."""
    return json.loads(BEFORE.read_text())["songs"]


def count_at(beats, counts, at):
    """The count shown at `at` seconds, or None when no beat is there."""
    if not beats:
        return None
    nearest = min(range(len(beats)), key=lambda n: abs(beats[n] - at))
    return counts[nearest] if abs(beats[nearest] - at) <= SAME_BEAT_S else None


def first_one(before):
    """The time of the first count 1 a song had: where its count started."""
    return next(time for time, count in zip(before["beats"], before["count"]) if count == 1)


def kept(before, beats, counts, start, end=float("inf")):
    """How the count from `start` to before `end`, in seconds, compares with what it was.

    Returns how many of the beats the song had there still have their count, how many
    there were, and the time of the first that has another count or is not found.
    """
    judged = [(time, count) for time, count in zip(before["beats"], before["count"]) if start <= time < end]
    lost = [time for time, count in judged if count_at(beats, counts, time) != count]
    return len(judged) - len(lost), len(judged), lost[0] if lost else None


_watched = []
_hooked = []


def _note_what_is_opened(event, args):
    if _watched and event == "open" and isinstance(args[0], (str, bytes, Path)):
        asked = Path(os.path.abspath(args[0].decode() if isinstance(args[0], bytes) else args[0]))
        opened = asked.resolve()
        for folders, found in _watched:
            # As it was asked for and as it is on disk: a watched folder may hold links to
            # files that are kept elsewhere, and those are under it too.
            if any(path.is_relative_to(folder) for folder in folders for path in (asked, opened)):
                found.append(str(opened))


@contextlib.contextmanager
def reading(*folders):
    """Lists the files under `folders` that are opened while the block runs."""
    if _note_what_is_opened not in _hooked:
        # A hook cannot be taken away again: it is added once and does nothing outside a block.
        sys.addaudithook(_note_what_is_opened)
        _hooked.append(_note_what_is_opened)
    found = []
    entry = ([path for folder in folders for path in (Path(os.path.abspath(folder)), Path(folder).resolve())], found)
    _watched.append(entry)
    try:
        yield found
    finally:
        _watched.remove(entry)

