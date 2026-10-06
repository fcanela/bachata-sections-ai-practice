import numpy as np
import pytest

from bachata.analysis import (
    BANDS,
    MAX_BPM,
    MIN_BPM,
    band_levels,
    beats_from_activations,
    bpm_at_beats,
    count_from_bars,
    entries,
    first_heard_bar,
    first_ocho,
    over_music,
    rises,
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


def test_a_band_is_as_loud_at_a_beat_as_the_sound_is_there():
    # Four seconds at 8 kHz, a beat every half second. A tone of 1 kHz starts at 2 s, on a faint noise.
    rate = 8000
    beats = [0.5 * n for n in range(8)]
    moments = np.arange(4 * rate) / rate
    sound = 0.001 * np.random.default_rng(1).standard_normal(4 * rate)
    sound[2 * rate :] += 0.5 * np.sin(2 * np.pi * 1000 * moments[2 * rate :])
    levels = band_levels(sound.astype(np.float32), rate, beats)
    assert levels.shape == (8, BANDS)
    loudest = int(np.argmax(levels[6]))
    # The band of the tone is much louder from the fifth beat on, and was not before.
    assert all(levels[beat, loudest] > levels[2, loudest] + 30 for beat in range(4, 8))
    assert all(abs(levels[beat, loudest] - levels[2, loudest]) < 6 for beat in range(3))
    # Each beat is the sound from it to the next: the tone is whole in the fifth beat, and
    # the fourth has only the edge of it.
    assert all(abs(levels[beat, loudest] - levels[6, loudest]) < 1 for beat in range(4, 8))
    assert levels[3, loudest] < levels[4, loudest] - 6
    # A band far from the tone stays as it was.
    assert abs(levels[6, 0] - levels[2, 0]) < 6


def test_no_band_is_further_under_the_loudest_than_the_floor():
    rate = 8000
    sound = np.zeros(4 * rate, dtype=np.float32)
    sound[2 * rate :] = np.sin(2 * np.pi * 1000 * np.arange(2 * rate) / rate)
    levels = band_levels(sound, rate, [0.5 * n for n in range(8)])
    assert levels.min() == pytest.approx(levels.max() - 60)
    assert band_levels(sound, rate, []).shape == (0, BANDS)


def test_the_sound_rises_where_the_beats_after_are_louder_than_the_beats_before():
    # 16 beats: quiet, and 20 dB louder in every band from the ninth on.
    levels = np.zeros((16, BANDS))
    levels[8:] = 20
    rise = rises(levels)
    assert rise[8] == pytest.approx(20)
    assert rise[7] == pytest.approx(15) and rise[9] == pytest.approx(15)
    # Too near either end there are not four beats on each side.
    assert list(rise[:4]) == [0] * 4 and list(rise[12:]) == [0] * 4
    # A band that gets quieter counts as nothing, and half the bands rising is half the rise.
    assert rises(-levels).max() == 0
    levels[8:, : BANDS // 2] = 0
    assert rises(levels)[8] == pytest.approx(10)


MUSIC = [True] * 24


def test_a_beat_is_over_music_when_the_beats_before_it_are_not_silence():
    # 16 beats: the first six are 30 dB under the others.
    levels = np.zeros((16, BANDS))
    levels[:6] = -30
    music = over_music(levels)
    # The first beat has nothing before it. Up to the seventh, all that is before is silence.
    assert music[:7] == [False] * 7
    # From the eighth the loud beats before it carry: one loud beat in four is 6 dB under.
    assert music[7:] == [True] * 9
    assert over_music(np.zeros((0, BANDS))) == []


def test_silence_is_fifteen_decibels_under_the_song():
    levels = np.zeros((16, BANDS))
    levels[:6] = -14
    assert over_music(levels)[1:] == [True] * 15
    levels[:6] = -16
    assert over_music(levels)[1:7] == [False] * 6


def test_what_comes_in_starts_the_nearest_bar_and_the_bar_after_from_the_middle_of_one():
    bars = [1, 2, 3, 4] * 6

    def one_rise(beat, rise=8.0):
        return [rise if n == beat else 0.0 for n in range(24)]

    assert entries(np.array(one_rise(8)), bars, MUSIC) == [(8, 8.0, True)]
    assert entries(np.array(one_rise(9)), bars, MUSIC) == [(8, 8.0, True)]
    assert entries(np.array(one_rise(10)), bars, MUSIC) == [(12, 8.0, True)]
    assert entries(np.array(one_rise(11)), bars, MUSIC) == [(12, 8.0, True)]
    # A rise under 5 dB is nothing coming in.
    assert entries(np.array(one_rise(8, 4.9)), bars, MUSIC) == []
    assert entries(np.array(one_rise(8, 5.0)), bars, MUSIC) == [(8, 5.0, True)]
    # Whether it comes in over music is that of the beat that rises, not of the bar it starts.
    quiet_until_ten = [False] * 10 + [True] * 14
    assert entries(np.array(one_rise(9)), bars, quiet_until_ten) == [(8, 8.0, False)]
    assert entries(np.array(one_rise(10)), bars, quiet_until_ten) == [(12, 8.0, True)]


def test_of_rises_close_together_only_the_largest_is_something_coming_in():
    bars = [1, 2, 3, 4] * 6
    rise = np.zeros(24)
    rise[7], rise[8], rise[9] = 6, 9, 7
    assert entries(rise, bars, MUSIC) == [(8, 9.0, True)]
    # Three beats apart they are still one.
    rise = np.zeros(24)
    rise[8], rise[11] = 9, 7
    assert entries(rise, bars, MUSIC) == [(8, 9.0, True)]
    # Four beats apart they are two.
    rise = np.zeros(24)
    rise[8], rise[12] = 9, 7
    assert entries(rise, bars, MUSIC) == [(8, 9.0, True), (12, 7.0, True)]


def test_the_first_ocho_starts_on_the_bar_that_more_comes_in_on():
    beats = [0.5 * n for n in range(200)]
    # Nothing comes in: the first bar that is heard starts the count.
    assert first_ocho(4, beats, []) == 4
    # What comes in on the ochos counted from that bar keeps it.
    assert first_ocho(4, beats, [(12, 8.0, True), (36, 6.0, True)]) == 4
    # What comes in on the bars between moves the count by a bar.
    assert first_ocho(4, beats, [(16, 8.0, True), (40, 6.0, True)]) == 8
    # The larger rises win, whichever way.
    assert first_ocho(4, beats, [(12, 8.0, True), (16, 6.0, True), (40, 5.0, True)]) == 8
    assert first_ocho(4, beats, [(12, 12.0, True), (16, 6.0, True), (40, 5.0, True)]) == 4
    # Even, the count stays where it was.
    assert first_ocho(4, beats, [(12, 8.0, True), (16, 8.0, True)]) == 4
    # A rise out of silence cannot move the count, and can keep it.
    assert first_ocho(4, beats, [(16, 30.0, False)]) == 4
    assert first_ocho(4, beats, [(12, 9.0, False), (16, 8.0, True)]) == 4
    assert first_ocho(4, beats, [(12, 7.0, False), (16, 8.0, True)]) == 8
    # A bar before the first that is heard has its say too.
    assert first_ocho(4, beats, [(0, 8.0, True)]) == 8


def test_what_comes_in_after_the_first_minute_does_not_set_the_count():
    beats = [0.5 * n for n in range(200)]
    # Beat 112 is at 56 s and beat 128 at 64 s.
    assert first_ocho(4, beats, [(12, 6.0, True), (112, 9.0, True)]) == 8
    assert first_ocho(4, beats, [(12, 6.0, True), (128, 9.0, True)]) == 4
    # A bar that would start after the last beat is not there.
    assert first_ocho(4, beats, [(200, 9.0, True)]) == 4


def test_the_tempo_range_cannot_hold_a_tempo_and_its_double():
    assert MAX_BPM < 2 * MIN_BPM
