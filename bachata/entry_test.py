"""The entry: the count 1 where the main part of a song enters, checked against the owner's ear.

The owner listened to 13 songs in full on 2026-10-06 (fixtures/audio/by-ear.json). On
five of them the count was four off from the start. The target he set, with no mark used:

- The count 1 falls on his mark on at least 4 of those 5.
- No other song gets worse. The songs he found right keep the count they had, from where
  it started. The two with a half phrase in the middle keep it up to their first mark.
  Old Town Road and Eso Es Amor keep their figures against the labels.

One test, which prints one line per song: `pytest -s` shows them, and so does a failure.
It reads the sound of the songs in the library and nothing else of it. It skips when the
owner's reference is not on the machine.
"""

import functools

import numpy as np
import pytest

from bachata.model import sha256_of
from bachata.songs_test import LIBRARY, analysed, analysed_samples
from fixtures.by_ear import count_at, first_one, kept, read_before, read_by_ear
from fixtures.validate import DEV, count_matches, read_labels, reference_beats, reference_counts

# The five songs whose count was four off from the start, as the owner listed them. Count
# 1 must be on the first mark of each. On the Me Emborrachare mix the four beats before
# the mark are not judged: 1 to 4 and 5 to 8 are both right there. The owner, 2026-10-06.
ENTRIES = {
    "727c45af50459a75abf666773c489f50": "Bachata Que Duele",
    "428f56afecc488838d0ff818712b8eec": "Escalofríos",
    "46f8d03da14b5cbf0ee3664c3727cdb7": "No vuelvo a caer",
    "ecd0cede4f7d7fad4390343d3e415564": "Me Emborrachare, the mix",
    "b1bc1bda60051e71ac5ff0575aff746b": "Sus Huellas",
}
ENTRIES_NEEDED = 4

# The two songs with a half phrase in the middle: they keep their count up to their first mark.
KEPT_TO_THE_FIRST_MARK = {
    "5ce30e574aefaaa6d5c5b40adae12d02": "Herrera",
    "ac2d92b08b6561bb29b08f109d933493": "Sin Fin",
}

# The songs he found right throughout: reviewed in full, with no mark.
RIGHT_THROUGHOUT = 6

# The least number of labelled beats that are shown with the count of the reference.
LABELLED = {"oldtownroad": 416, "esoesamor": 257}


@functools.cache
def analysed_from_the_library(song_id):
    """The analysis of a song of the library, from its sound alone. None when it is not there."""
    sound = LIBRARY / "songs" / song_id / "sound.raw"
    if not sound.exists():
        return None
    return analysed_samples(np.fromfile(sound, dtype="<i2").reshape(-1, 2))


def entry_line(song, result):
    """Whether count 1 is on the owner's mark, and the line that says so."""
    mark = song["marks"][0]
    places = [mark["at_s"]] + ([mark["also_right_at_s"]] if "also_right_at_s" in mark else [])
    shown = [count_at(result["beats"], result["count"], at) for at in places]
    said = " and ".join(f"{'no beat' if count is None else f'count {count}'} at {at} s" for at, count in zip(places, shown))
    return 1 in shown, f"{said}, where he hears 1"


def kept_line(before, result, end=float("inf")):
    """Whether the count is the one the song had, from where it started, and the line that says so."""
    start = first_one(before)
    still, judged, lost_at = kept(before, result["beats"], result["count"], start, end)
    until = "the end" if end == float("inf") else f"the mark at {end} s"
    said = f"{still} of {judged} beats keep their count from {start} s to {until}"
    return still == judged, said + ("" if lost_at is None else f", lost first at {lost_at} s")


def test_the_count_enters_on_one_and_no_other_song_gets_worse():
    by_ear = read_by_ear()
    if not by_ear:
        pytest.skip("skipped: no reference by ear")
    before = read_before()
    right_throughout = [song_id for song_id, song in by_ear.items() if song["reviewed"] == "full" and not song["marks"]]
    assert len(right_throughout) == RIGHT_THROUGHOUT and set(ENTRIES) | set(KEPT_TO_THE_FIRST_MARK) <= set(by_ear)

    lines, entered, worse = [], [], []

    def judge(song_id, name, line):
        """Prints the line of a song and returns whether it holds."""
        result = analysed_from_the_library(song_id)
        holds, said = (False, "its sound is not in the library") if result is None else line(result)
        lines.append(f"{'ok  ' if holds else 'FAIL'}  {name}: {said}")
        return holds

    for song_id, name in ENTRIES.items():
        if judge(song_id, name, lambda result: entry_line(by_ear[song_id], result)):
            entered.append(name)
    for song_id in right_throughout:
        name = by_ear[song_id]["name"]
        if not judge(song_id, name, lambda result: kept_line(before[song_id], result)):
            worse.append(name)
    for song_id, name in KEPT_TO_THE_FIRST_MARK.items():
        mark = by_ear[song_id]["marks"][0]["at_s"]
        if not judge(song_id, name, lambda result: kept_line(before[song_id], result, mark)):
            worse.append(name)
    for song, least in LABELLED.items():
        mix = DEV / song / "mix.m4a"
        labels, result = read_labels(DEV / song), analysed(mix)
        counts = reference_counts(labels)
        right = count_matches(reference_beats(labels, sha256_of(mix)), counts, result["beats"], result["count"])
        lines.append(
            f"{'ok  ' if right >= least else 'FAIL'}  {labels['title']}: {right} of {len(counts)} labelled beats "
            f"are shown with the count of the reference, at least {least} needed"
        )
        if right < least:
            worse.append(labels["title"])

    print("\n" + "\n".join(lines))
    print(f"The count enters on 1 on {len(entered)} of {len(ENTRIES)} songs, at least {ENTRIES_NEEDED} needed.")
    print(f"{len(worse)} other songs got worse.")
    assert len(entered) >= ENTRIES_NEEDED and worse == [], (
        f"the count enters on 1 on {len(entered)} of {len(ENTRIES)} songs, and {len(worse)} other songs got worse"
    )
