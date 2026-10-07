import numpy as np
import pytest

from bachata.analysis import (
    BANDS,
    MAX_BPM,
    MIN_BPM,
    band_levels,
    bass_cycle,
    beats_from_activations,
    bpm_at_beats,
    count_from_bars,
    entries,
    entry_vote,
    first_heard_bar,
    first_ocho,
    over_music,
    rises,
    vote_is_clear,
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
    # It is the four beats before that are looked at: two quiet ones after two loud are music.
    levels = np.zeros((16, BANDS))
    levels[6:8] = -30
    assert over_music(levels)[8] is True


def test_silence_is_fifteen_decibels_under_the_song():
    levels = np.zeros((16, BANDS))
    levels[:6] = -14
    assert over_music(levels)[1:] == [True] * 15
    levels[:6] = -16
    assert over_music(levels)[1:7] == [False] * 6
    # The level of the song is that of its usual beat, not of its loudest.
    levels[:6] = -14
    levels[12:14] = 10
    assert over_music(levels)[1:7] == [True] * 6


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
    quiet_until_nine = [False] * 9 + [True] * 15
    assert entries(np.array(one_rise(8)), bars, quiet_until_nine) == [(8, 8.0, False)]
    assert entries(np.array(one_rise(9)), bars, quiet_until_nine) == [(8, 8.0, True)]


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


def bass_louder_from(first, beats=80, by=6.0, seed=3):
    """Made-up levels, a little uneven: the three bass bands are louder in every other bar, from the beat `first`."""
    levels = np.random.default_rng(seed).normal(0, 0.5, (beats, BANDS))
    for bar in range(first % 8, beats, 8):
        levels[bar : bar + 4, :3] += by
    return levels


HALF_SECONDS = [0.5 * n for n in range(400)]


def test_the_bass_says_which_bars_it_is_louder_in():
    # Louder in the bars that start the ochos counted from the first beat: surely so.
    assert bass_cycle(bass_louder_from(0), HALF_SECONDS, 0) > 10
    # Counted from a bar later, it is as surely the other way.
    assert bass_cycle(bass_louder_from(0), HALF_SECONDS, 4) < -10
    assert bass_cycle(bass_louder_from(4), HALF_SECONDS, 0) < -10
    # A song that starts inside a bar: the bars are counted from the first that is heard.
    assert bass_cycle(bass_louder_from(2), HALF_SECONDS, 2) > 10
    assert bass_cycle(bass_louder_from(2), HALF_SECONDS, 6) < -10


def test_a_bass_that_is_as_loud_in_every_bar_says_nothing_surely():
    assert abs(bass_cycle(bass_louder_from(0, by=0.0), HALF_SECONDS, 0)) < 2
    assert bass_cycle(np.zeros((80, BANDS)), HALF_SECONDS, 0) == 0
    # Nor does a song of fewer than three bars to compare, or of none.
    assert bass_cycle(bass_louder_from(0, beats=16), HALF_SECONDS, 0) == 0
    assert bass_cycle(np.zeros((0, BANDS)), [], 0) == 0


def test_only_the_three_lowest_bands_are_the_bass():
    levels = np.random.default_rng(3).normal(0, 0.5, (80, BANDS))
    for bar in range(0, 80, 8):
        levels[bar : bar + 4, 3:] += 6
    assert abs(bass_cycle(levels, HALF_SECONDS, 0)) < 2
    # One of the three is enough.
    for band in range(3):
        levels = np.random.default_rng(3).normal(0, 0.5, (80, BANDS))
        for bar in range(0, 80, 8):
            levels[bar : bar + 4, band] += 6
        assert bass_cycle(levels, HALF_SECONDS, 0) > 5


def test_the_bass_is_heard_over_the_first_ninety_seconds():
    # 400 beats, 200 s. The bass is louder in the one kind of bar up to 90 s, beat 180, and in the other after.
    levels = np.random.default_rng(3).normal(0, 0.5, (400, BANDS))
    for bar in range(0, 400, 4):
        if (bar % 8 == 0) == (bar < 180):
            levels[bar : bar + 4, :3] += 6
    assert bass_cycle(levels, HALF_SECONDS, 0) > 10
    # The same with the change at 60 s: a third of the bars heard say the other, and it is less sure.
    early = np.random.default_rng(3).normal(0, 0.5, (400, BANDS))
    for bar in range(0, 400, 4):
        if (bar % 8 == 0) == (bar < 120):
            early[bar : bar + 4, :3] += 6
    assert 0 < bass_cycle(early, HALF_SECONDS, 0) < 10


def test_a_bar_is_compared_with_the_two_around_it():
    # The bass gets 4 dB louder with every bar, and is 3 dB louder still in every other one.
    # Compared with the bar before only, every bar is louder than its neighbour, and the
    # two kinds of bar differ too unevenly to be sure of.
    levels = np.random.default_rng(3).normal(0, 0.1, (80, BANDS))
    for bar in range(0, 80, 4):
        levels[bar : bar + 4, :3] += bar + (3 if bar % 8 == 4 else 0)
    assert bass_cycle(levels, HALF_SECONDS, 0) < -10


def test_where_nothing_comes_in_a_sure_bass_sets_the_count():
    beats = [0.5 * n for n in range(200)]
    assert first_ocho(4, beats, [], -3.0) == 8
    assert first_ocho(4, beats, [], -2.0) == 8
    # Not sure enough, or sure of the first bar: the count stays.
    assert first_ocho(4, beats, [], -1.9) == 4
    assert first_ocho(4, beats, [], 3.0) == 4
    # What comes in after the first minute, or out of silence on the other bar, is nothing coming in.
    assert first_ocho(4, beats, [(128, 9.0, True)], -3.0) == 8
    assert first_ocho(4, beats, [(16, 9.0, False)], -3.0) == 8


def test_where_something_comes_in_the_bass_is_not_asked():
    beats = [0.5 * n for n in range(200)]
    assert first_ocho(4, beats, [(12, 6.0, True)], -9.0) == 4
    assert first_ocho(4, beats, [(12, 6.0, False)], -9.0) == 4
    assert first_ocho(4, beats, [(16, 6.0, True)], 9.0) == 8


def test_a_vote_is_clear_when_one_bar_has_three_times_the_other():
    assert vote_is_clear(9.0, 3.0) and vote_is_clear(3.0, 9.0)
    assert not vote_is_clear(9.0, 3.1) and not vote_is_clear(3.1, 9.0)
    assert not vote_is_clear(8.0, 8.0)
    # One side alone is clear, and so is nothing at all: there the bass is asked.
    assert vote_is_clear(5.0, 0.0) and vote_is_clear(0.0, 5.0) and vote_is_clear(0.0, 0.0)


def test_what_comes_in_is_weighed_for_each_of_the_two_bars():
    beats = [0.5 * n for n in range(200)]
    assert entry_vote(4, beats, [(12, 8.0, True), (16, 6.0, True), (28, 2.0, True), (40, 5.0, True)]) == (10.0, 11.0)
    # Out of silence it counts for the first bar only, and after the first minute for neither.
    assert entry_vote(4, beats, [(12, 8.0, False), (16, 6.0, False), (128, 9.0, True)]) == (8.0, 0.0)


def test_where_the_vote_is_not_clear_sure_fills_set_the_count():
    beats = [0.5 * n for n in range(200)]
    close = [(12, 8.0, True), (16, 6.0, True)]
    assert first_ocho(4, beats, close) == 4
    assert first_ocho(4, beats, close, fills=-2.0) == 8
    assert first_ocho(4, beats, close, fills=-1.9) == 4
    # The fills can also keep the bar that has less of what comes in.
    other = [(12, 6.0, True), (16, 8.0, True)]
    assert first_ocho(4, beats, other) == 8
    assert first_ocho(4, beats, other, fills=2.0) == 4
    assert first_ocho(4, beats, other, fills=1.9) == 8
    # Even is not clear.
    assert first_ocho(4, beats, [(12, 8.0, True), (16, 8.0, True)], fills=-3.0) == 8


def test_where_the_vote_is_clear_the_fills_are_not_asked():
    beats = [0.5 * n for n in range(200)]
    assert first_ocho(4, beats, [(12, 9.0, True), (16, 3.0, True)], fills=-9.0) == 4
    assert first_ocho(4, beats, [(12, 3.0, True), (16, 9.0, True)], fills=9.0) == 8
    assert first_ocho(4, beats, [(12, 6.0, True)], fills=-9.0) == 4
    # Where nothing comes in the bass is asked, and the fills are not.
    assert first_ocho(4, beats, [], 0.0, -9.0) == 4
    assert first_ocho(4, beats, [], -3.0, 9.0) == 8


def analysed_with_a_beat_every_half_second(monkeypatch, sound, rate, fills_of=None):
    """The analysis of a made-up sound, with made-up beats in place of the tracker's."""
    from bachata import analysis

    beats = [0.5 * n for n in range(len(sound) // (rate // 2))]
    monkeypatch.setattr(analysis, "beat_activations", lambda mono, rate: (None, None))
    monkeypatch.setattr(
        analysis, "beats_from_activations", lambda beat, downbeat: (beats, [n % 4 + 1 for n in range(len(beats))])
    )
    return analysis.analyse((sound[:, None] * 32767).astype(np.int16).repeat(2, axis=1), rate, fills_of)


def test_what_comes_in_between_two_ochos_moves_the_count_of_the_whole_song(monkeypatch):
    # 20 s of noise at 8 kHz. From the eleventh beat it is 12 dB louder: that starts the fourth bar.
    rate = 8000
    sound = 0.1 * np.random.default_rng(2).uniform(-1, 1, 20 * rate)
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate)
    assert result["count"][:9] == [1, 2, 3, 4, 5, 6, 7, 8, 1]
    sound[10 * rate // 2 :] *= 4
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate)
    assert result["count"][:13] == [5, 6, 7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1]


def test_the_fills_of_a_song_are_asked_only_where_what_comes_in_is_not_clear(monkeypatch):
    # 30 s of noise at 8 kHz that gets 7 dB louder at the eleventh beat, which starts the
    # fourth bar, and 5.5 dB louder again at the twenty-third, which starts the seventh.
    rate = 8000
    asked = []

    def fills_of(samples, rate, beats, bars, first):
        asked.append((len(samples), rate, len(beats), bars[:5], first))
        return said

    sound = 0.02 * np.random.default_rng(2).uniform(-1, 1, 30 * rate)
    sound[10 * rate // 2 :] *= 2.2
    said = 9.0
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate, fills_of)
    assert result["count"][:13] == [5, 6, 7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1] and asked == []
    # Two things come in, on bars of the two kinds: the fills are asked, with the song and its beats.
    sound[22 * rate // 2 :] *= 1.9
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate, fills_of)
    assert asked == [(30 * rate, rate, 60, [1, 2, 3, 4, 1], 0)]
    assert result["count"][:9] == [1, 2, 3, 4, 5, 6, 7, 8, 1]
    said = -9.0
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate, fills_of)
    assert result["count"][:9] == [5, 6, 7, 8, 1, 2, 3, 4, 5]
    # Fills that are not sure leave the count to what comes in: the larger rise.
    said = 1.0
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate, fills_of)
    assert result["count"][:9] == [5, 6, 7, 8, 1, 2, 3, 4, 5]


def test_a_song_that_starts_quietly_keeps_its_count_on_the_first_bar_that_is_heard(monkeypatch):
    # The same noise, 28 dB quieter for its first ten beats: it gets loud where the fourth bar is led in.
    rate = 8000
    sound = 0.5 * np.random.default_rng(2).uniform(-1, 1, 20 * rate)
    sound[: 10 * rate // 2] *= 0.04
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate)
    assert result["count"][:9] == [1, 2, 3, 4, 5, 6, 7, 8, 1]


def test_a_song_where_nothing_comes_in_is_counted_by_its_bass(monkeypatch):
    # 40 s of steady noise at 8 kHz with a tone of 80 Hz, which is louder in every other bar from the second.
    rate = 8000
    moments = np.arange(40 * rate) / rate
    tone = 0.1 * np.sin(2 * np.pi * 80 * moments)
    bar = (moments // 2).astype(int)
    sound = 0.02 * np.random.default_rng(2).uniform(-1, 1, 40 * rate) + tone * np.where(bar % 2 == 1, 2.0, 1.0)
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate)
    assert result["count"][:9] == [5, 6, 7, 8, 1, 2, 3, 4, 5]
    # Louder in every other bar from the first: the count stays on the first bar.
    sound = 0.02 * np.random.default_rng(2).uniform(-1, 1, 40 * rate) + tone * np.where(bar % 2 == 0, 2.0, 1.0)
    result = analysed_with_a_beat_every_half_second(monkeypatch, sound, rate)
    assert result["count"][:9] == [1, 2, 3, 4, 5, 6, 7, 8, 1]


def test_the_tempo_range_cannot_hold_a_tempo_and_its_double():
    assert MAX_BPM < 2 * MIN_BPM
