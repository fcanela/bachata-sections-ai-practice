"""The fills, checked against the owner's ear: the count once the percussion is in.

On 2026-10-07 the owner heard six songs in pairs of clips (fixtures/audio/entry-pairs.json):
one clip with the loud click on each count 1 that version 4 showed, one with it four
beats from there. On all six he heard his 1 on the second. What comes in during the
first minute of these songs does not say clearly which bar starts an ocho, and the fills
do. The target: the count 1 falls where he heard it on at least 5 of the 6.

One test, which prints one line per song: `pytest -s` shows them, and so does a failure.
It reads the songs from fixtures/audio/entries/ and skips when they are not on the machine.
"""

import pytest

from bachata.songs_test import analysed
from fixtures.by_ear import ENTRY_PAIRS, count_at, read_entry_pairs

PAIRS = 6
PAIRS_NEEDED = 5


def test_the_count_is_on_one_where_he_heard_it_once_the_percussion_is_in():
    pairs = read_entry_pairs()
    if not pairs:
        pytest.skip("skipped: no reference by ear")
    assert len(pairs) == PAIRS

    lines, right = [], []
    for song in pairs:
        result = analysed(ENTRY_PAIRS.parent / song["file"])
        shown = count_at(result["beats"], result["count"], song["one_at_s"])
        said = "no beat" if shown is None else f"count {shown}"
        lines.append(f"{'ok  ' if shown == 1 else 'FAIL'}  {song['name']}: {said} at {song['one_at_s']} s, where he hears 1")
        if shown == 1:
            right.append(song["name"])

    print("\n" + "\n".join(lines))
    print(f"The count is on 1 where he heard it on {len(right)} of {len(pairs)} songs, at least {PAIRS_NEEDED} needed.")
    assert len(right) >= PAIRS_NEEDED, f"the count is on 1 where he heard it on {len(right)} of {len(pairs)} songs"
