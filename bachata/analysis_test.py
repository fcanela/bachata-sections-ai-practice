import numpy as np
import pytest

from bachata.analysis import MAX_BPM, MIN_BPM, beats_from_activations, bpm_at_beats


def test_the_shown_bpm_is_the_mean_tempo_of_the_ocho_around_each_beat():
    steady = [1.0 + n * 0.5 for n in range(20)]
    assert bpm_at_beats(steady) == pytest.approx([120.0] * 20)

    # Beat times come in steps of 20 ms: at 124 BPM the intervals are 480 or 500 ms.
    stepped = [round((0.3 + n * 60 / 124) * 50) / 50 for n in range(40)]
    assert all(abs(bpm / 124 - 1) < 0.01 for bpm in bpm_at_beats(stepped))

    # A song that goes from 120 to 150 BPM shows each tempo, one ocho away from the change.
    changing = [n * 0.5 for n in range(20)] + [10.0 + n * 0.4 for n in range(20)]
    shown = bpm_at_beats(changing)
    assert shown[15] == pytest.approx(120.0)
    assert shown[24] == pytest.approx(150.0)
    assert 120 < shown[20] < 150

    assert bpm_at_beats([]) == []
    assert bpm_at_beats([1.0]) == [0.0]


def activations(beat_times, seconds):
    beat = np.full(seconds * 50, 0.001)
    for time in beat_times:
        beat[round(time * 50)] = 0.99
    return beat, np.full(seconds * 50, 0.001)


def test_a_half_time_part_keeps_the_tempo_a_dancer_counts():
    # 125 BPM for 20 s, with only every other beat marked from 8 s to 14 s.
    every = [0.48 * n for n in range(1, 41)]
    marked = [time for n, time in enumerate(every) if not (8 < time < 14 and n % 2)]
    beats = beats_from_activations(*activations(marked, 20))
    assert beats == pytest.approx(every, abs=0.021)


def test_the_tempo_range_cannot_hold_a_tempo_and_its_double():
    assert MAX_BPM < 2 * MIN_BPM
