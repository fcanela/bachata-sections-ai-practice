import copy

import pytest

from fixtures.validate import (
    bar_problems,
    beat_problems,
    count_matches,
    labelled_songs,
    problems,
    read_labels,
    reference_beats,
    reference_counts,
)

# A made-up song in the site's format, at 120 BPM: a beat every half second from 1.0 s.
EXAMPLE = {
    "title": "Made-up numbers, not a real song",
    "bpm": 120,
    "lead_s": 1.0,
    "total_s": 13.0,
    "total_beats": 24,
    "sections": [
        {"title": "Intro", "structure": None, "start_s": 1.0, "end_s": 5.0, "beats": 8, "blocks": []},
        {
            "title": "Verse",
            "structure": "Derecho",
            "start_s": 5.0,
            "end_s": 13.0,
            "beats": 16,
            "blocks": [
                {"structure": "Derecho", "beats": 8, "start_s": 5.0, "end_s": 9.0},
                {"structure": "Majao", "beats": 8, "start_s": 9.0, "end_s": 13.0},
            ],
        },
    ],
}


def changed(**changes):
    labels = copy.deepcopy(EXAMPLE)
    labels.update(changes)
    return labels


def test_the_example_is_valid():
    assert problems(EXAMPLE) == []
    assert problems(changed(first_beat_s=1.07, mix_sha256="ab" * 32)) == []


# The check above means nothing if the validator accepts anything.
def test_a_broken_label_file_is_rejected():
    assert problems(changed(bpm=0)) == ["bpm: must be a positive number"]
    assert problems(changed(total_beats=25)) == [
        "sections: add up to 24 beats, total_beats is 25",
        "total_s: is 13.0, but the last section ends at 13.000",
    ]

    gap = copy.deepcopy(EXAMPLE)
    gap["sections"][1]["start_s"] = 5.5
    assert problems(gap) == ["sections[1].start_s: is 5.5, but beat 8 is at 5.000"]

    short_blocks = copy.deepcopy(EXAMPLE)
    del short_blocks["sections"][1]["blocks"][1]
    assert problems(short_blocks) == ["sections[1].blocks: add up to 8 beats, the section has 16"]

    assert problems(changed(first_beat_s=1.07)) == ["mix_sha256: must be 64 lowercase hex characters"]


def test_the_reference_beats_start_at_the_measured_first_beat_of_that_mix():
    labels = changed(first_beat_s=1.07, mix_sha256="ab" * 32)
    beats = reference_beats(labels, "ab" * 32)
    assert len(beats) == 24
    assert beats[:3] == pytest.approx([1.07, 1.57, 2.07])
    with pytest.raises(ValueError, match="not measured on this mix"):
        reference_beats(labels, "cd" * 32)
    with pytest.raises(ValueError, match="not measured on this mix"):
        reference_beats(EXAMPLE, "ab" * 32)


def test_every_label_file_on_the_machine_is_valid():
    songs = labelled_songs()
    if not songs:
        pytest.skip("skipped: no reference material")
    for name, folder in songs.items():
        assert problems(read_labels(folder)) == [], name


REFERENCE = [1.0 + n * 0.5 for n in range(24)]


def test_beats_on_the_labelled_ones_are_accepted():
    assert beat_problems(REFERENCE, REFERENCE) == []
    assert beat_problems(REFERENCE, [time + 0.085 for time in REFERENCE]) == []
    # Beats before the first labelled one and after the last are not judged.
    assert beat_problems(REFERENCE, [0.0, 0.5] + REFERENCE + [13.0, 13.5]) == []


def test_a_missing_an_extra_and_a_late_beat_are_each_reported():
    assert beat_problems(REFERENCE, REFERENCE[:5] + REFERENCE[6:]) == ["labelled beat at 3.500 s has no detected beat"]
    assert beat_problems(REFERENCE, REFERENCE[:-1]) == ["labelled beat at 12.500 s has no detected beat"]
    assert beat_problems(REFERENCE, sorted(REFERENCE + [3.75])) == [
        "detected beat at 3.750 s has no labelled beat: the nearest is 250 ms away, at 3.500 s"
    ]
    assert beat_problems(REFERENCE, sorted(REFERENCE + [3.52])) == [
        "labelled beat at 3.500 s has 2 detected beats: [3.5, 3.52]"
    ]
    late = [time + (0.095 if time == 3.5 else 0) for time in REFERENCE]
    assert beat_problems(REFERENCE, late) == [
        "detected beat at 3.595 s has no labelled beat: the nearest is 95 ms away, at 3.500 s",
        "labelled beat at 3.500 s has no detected beat",
    ]


# The check this one replaced looked only at section edges, and a tracker that marks a
# beat every 50 ms passed it.
def test_a_beat_every_50_ms_is_rejected():
    everywhere = [n * 0.05 for n in range(300)]
    assert len(beat_problems(REFERENCE, everywhere)) >= len(REFERENCE)


def section(beats, *blocks):
    return {"beats": beats, "blocks": [{"beats": block} for block in blocks]}


def test_the_reference_count_starts_again_at_every_section_and_every_block():
    assert reference_counts(EXAMPLE) == [1, 2, 3, 4, 5, 6, 7, 8] * 3
    # A section of an ocho and a half: the half phrase is its last bar, counted 1 to 4.
    assert reference_counts({"sections": [section(12), section(8)]}) == [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4] + [1, 2, 3, 4, 5, 6, 7, 8]
    # Blocks say where a half phrase is when it is not at the end.
    assert reference_counts({"sections": [section(20, 8, 4, 8)]}) == [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8]
    # Nine beats: an ocho and one beat on count 1.
    assert reference_counts({"sections": [section(9)]}) == [1, 2, 3, 4, 5, 6, 7, 8, 1]


def test_a_beat_in_the_wrong_place_of_its_bar_is_reported():
    reference = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    counts = [1, 2, 3, 4, 1, 2]
    assert bar_problems(reference, counts, reference, [1, 2, 3, 4, 1, 2]) == []
    # Counts 5 to 8 are the same places of a bar as 1 to 4.
    assert bar_problems(reference, [5, 6, 7, 8, 1, 2], reference, [1, 2, 3, 4, 1, 2]) == []
    shifted = bar_problems(reference, counts, reference, [2, 3, 4, 1, 2, 3])
    assert len(shifted) == 6 and shifted[0] == "the beat at 1.000 s is beat 2 of its bar, the labels say 1"
    assert bar_problems(reference, counts, reference[:5], [1, 2, 3, 4, 1]) == ["no beat at 3.500 s"]


def test_the_beats_shown_with_the_count_of_the_reference_are_counted():
    reference = [1.0, 1.5, 2.0, 2.5]
    assert count_matches(reference, [1, 2, 3, 4], reference, [1, 2, 3, 4]) == 4
    assert count_matches(reference, [1, 2, 3, 4], reference, [5, 6, 7, 8]) == 0
    assert count_matches(reference, [1, 2, 3, 4], [1.0, 1.5, 2.0], [1, 2, 7]) == 2
