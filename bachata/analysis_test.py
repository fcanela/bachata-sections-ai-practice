import numpy as np
import pytest

from bachata.analysis import (
    MAX_BPM,
    MIN_BPM,
    beats_from_activations,
    bpm_at_beats,
    count_from_bars,
    first_heard_bar,
)


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


def activations(beat_times, seconds, downbeat_times=()):
    beat = np.full(seconds * 50, 0.001)
    downbeat = np.full(seconds * 50, 0.001)
    for time in beat_times:
        beat[round(time * 50)] = 0.99
    for time in downbeat_times:
        downbeat[round(time * 50)] = 0.99
    return beat, downbeat


def test_a_half_time_part_keeps_the_tempo_a_dancer_counts():
    # 125 BPM for 20 s, with only every other beat marked from 8 s to 14 s.
    every = [0.48 * n for n in range(1, 41)]
    marked = [time for n, time in enumerate(every) if not (8 < time < 14 and n % 2)]
    beats, bars = beats_from_activations(*activations(marked, 20))
    assert beats == pytest.approx(every, abs=0.021)
    # Every beat has a place in a bar of four, and the places follow each other.
    assert all(after == before % 4 + 1 for before, after in zip(bars, bars[1:]))


def test_a_bar_is_four_beats_even_where_every_third_beat_is_rated_a_downbeat():
    # 125 BPM for 30 s. A tracker that may choose bars of three would choose them here.
    every = [0.48 * n for n in range(1, 61)]
    beats, bars = beats_from_activations(*activations(every, 30, every[::3]))
    # The tracker may leave out a beat at either end, where it has no bar to put it in.
    assert len(beats) >= 56 and all(min(abs(time - beat) for beat in every) <= 0.021 for time in beats)
    assert set(bars) == {1, 2, 3, 4}
    assert all(after == before % 4 + 1 for before, after in zip(bars, bars[1:]))


def test_the_count_runs_in_eights_from_the_first_bar_that_is_heard():
    assert count_from_bars([1, 2, 3, 4] * 3, 0) == [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4]
    # A song that starts inside a bar: its first beats end an ocho.
    assert count_from_bars([3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 1], 2) == [7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1]
    assert count_from_bars([], 0) == []


def test_a_bar_in_the_silence_before_a_song_does_not_start_the_count():
    rate = 100
    beats = [0.5 * n for n in range(12)]
    bars = [1, 2, 3, 4] * 3
    sound = np.ones(6 * rate, dtype=np.float32)
    assert first_heard_bar(sound, rate, beats, bars) == 0
    # Two seconds of silence, with a faint noise in them: the second bar is the first heard.
    sound[: 2 * rate] = 0.001
    assert first_heard_bar(sound, rate, beats, bars) == 4
    # A song that starts inside a bar.
    assert first_heard_bar(np.ones(6 * rate, dtype=np.float32), rate, beats, [3, 4, 1, 2] * 3) == 2
    assert first_heard_bar(np.zeros(6 * rate, dtype=np.float32), rate, beats, bars) == 0
    assert first_heard_bar(sound, rate, [], []) == 0


def test_the_tempo_range_cannot_hold_a_tempo_and_its_double():
    assert MAX_BPM < 2 * MIN_BPM
