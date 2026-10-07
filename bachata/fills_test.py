import numpy as np
import pytest

from bachata import fills
from bachata.fills import (
    CUT,
    MEL_BANDS,
    PARTS_RATE,
    beat_scores,
    fills_cycle,
    over_the_bars_around,
    percussion_entry,
    picture,
    split,
)

# A beat every 480 ms is 24 rows of a picture, and a sixteenth is 6.
BEAT_S = 0.48


def made_up_bars(count):
    beats = [BEAT_S * n for n in range(4 * count + 1)]
    return beats, [n % 4 + 1 for n in range(len(beats))]


def picture_with_attacks(times, seconds, level=0.0):
    """A picture that is 60 dB down, with one row at `level` dB where each attack is."""
    mel = np.full((round(seconds * 50), MEL_BANDS), -60.0, dtype=np.float32)
    for time in times:
        mel[round(time * 50)] = level
    return mel


def marking_and_filling(count, marking):
    """The attacks of `count` bars: on the beats in the bars `marking` says, and also after each beat in the others."""
    beats, bars = made_up_bars(count)
    times = []
    for bar in range(count):
        for beat in range(4):
            at = beats[4 * bar + beat]
            times.append(at)
            if not marking(bar):
                times.append(at + BEAT_S / 4)
    return beats, bars, picture_with_attacks(times, beats[-1] + 1)


def test_a_bar_that_marks_the_beats_scores_over_one_that_fills_between_them():
    beats, bars, mel = marking_and_filling(12, lambda bar: bar % 2 == 0)
    scores = beat_scores([mel], beats, bars)
    assert len(scores) == 13
    assert all(scores[bar] > 0 for bar in range(2, 11, 2)) and all(scores[bar] < 0 for bar in range(1, 11, 2))
    # The other way round, the other bars score over.
    beats, bars, mel = marking_and_filling(12, lambda bar: bar % 2 == 1)
    scores = beat_scores([mel], beats, bars)
    assert all(scores[bar] < 0 for bar in range(2, 11, 2)) and all(scores[bar] > 0 for bar in range(1, 11, 2))
    # Two parts that say the same say it twice as loud, and bars that are all alike say nothing.
    assert beat_scores([mel, mel], beats, bars) == pytest.approx(2 * scores)
    beats, bars, mel = marking_and_filling(12, lambda bar: True)
    assert beat_scores([mel], beats, bars)[2:11] == pytest.approx(np.zeros(9))


def test_an_attack_just_before_a_beat_is_a_fill_and_one_half_way_between_two_beats_is_not():
    def scores_with(extra):
        beats, bars = made_up_bars(12)
        times = [beat for beat in beats[:-1]]
        times += [beats[4 * bar + beat] + extra for bar in range(1, 12, 2) for beat in range(4)]
        return beat_scores([picture_with_attacks(times, beats[-1] + 1)], beats, bars)

    before = scores_with(3 * BEAT_S / 4)
    assert all(before[bar] < 0 for bar in range(1, 11, 2)) and all(before[bar] > 0 for bar in range(2, 11, 2))
    # Half way it only takes from the share of the beats: less of a difference than a fill makes.
    half = scores_with(BEAT_S / 2)
    assert all(before[bar] < half[bar] < 0 for bar in range(3, 10, 2))


def test_a_bar_is_measured_against_the_two_around_it_and_cut_at_three_times_its_usual_size():
    over = over_the_bars_around(np.array([5.0, 1.0, 3.0, 1.0, 3.0, 1.0, 30.0, 1.0, 9.0]))
    assert over[0] == 0 and over[-1] == 0
    # The second bar has 1 where the two around it have 5 and 3: 3 under. The usual size here is 1.4826 * 2.
    assert over[1] == pytest.approx(-3.0 / (1.4826 * 2))
    assert over[3] == pytest.approx(-2.0 / (1.4826 * 2))
    assert over[6] == CUT and over[5] == -CUT


def loud_from(first_loud, count, also=()):
    beats, bars = made_up_bars(count)
    mel = np.full((round((beats[-1] + 1) * 50), MEL_BANDS), -40.0, dtype=np.float32)
    for bar in list(range(first_loud, count)) + list(also):
        mel[round(beats[4 * bar] * 50) : round(beats[4 * bar + 4] * 50)] = 0.0
    return mel, beats, bars


def test_the_percussion_comes_in_at_the_first_of_four_bars_in_a_row_where_it_is_loud():
    assert percussion_entry(*(loud_from(6, 20))) == 6
    assert percussion_entry(*(loud_from(0, 20))) == 0
    # A bar or three of it earlier are a fill, not the percussion coming in.
    assert percussion_entry(*(loud_from(9, 20, also=[1, 3, 4, 5]))) == 9
    assert percussion_entry(*(loud_from(9, 20, also=[2, 3, 4, 5]))) == 2
    # 11 dB under its loudest it is in, and 13 dB under it is not.
    mel, beats, bars = loud_from(6, 20)
    mel[mel < 0] = -11.0
    assert percussion_entry(mel, beats, bars) == 0
    mel[mel < 0] = -13.0
    assert percussion_entry(mel, beats, bars) == 6
    # Loud in every other bar only, it never comes in.
    mel, beats, bars = loud_from(20, 20, also=range(0, 20, 2))
    assert percussion_entry(mel, beats, bars) is None


def test_the_fills_say_which_bars_mark_the_beats_from_where_the_percussion_comes_in():
    beats, bars = made_up_bars(60)
    noise = np.random.default_rng(5).normal(0, 0.5, 61)
    scores = np.where(np.arange(61) % 2 == 0, 1.0, -1.0) + noise
    # The bars that start an ocho counted from the first beat mark the beats, and so do those counted from the ninth.
    assert fills_cycle(scores, beats, bars, 0, 0) > 5
    assert fills_cycle(scores, beats, bars, 8, 0) == fills_cycle(scores, beats, bars, 0, 0)
    assert fills_cycle(scores, beats, bars, 4, 0) == -fills_cycle(scores, beats, bars, 0, 0)
    assert fills_cycle(-scores, beats, bars, 0, 0) < -5
    assert abs(fills_cycle(noise, beats, bars, 0, 0)) < 3
    # With no percussion, or fewer than three bars of it, they say nothing.
    assert fills_cycle(scores, beats, bars, 0, None) == 0
    assert fills_cycle(scores, beats, bars, 0, 59) == 0


def test_the_fills_are_heard_over_sixty_seconds_from_where_the_percussion_comes_in():
    beats, bars = made_up_bars(80)
    # A bar is 1.92 s. The bars before the tenth say the other thing, and so do those from 60 s after it.
    scores = np.where(np.arange(81) % 2 == 0, 1.0, -1.0) + np.random.default_rng(5).normal(0, 0.2, 81)
    whole = fills_cycle(scores, beats, bars, 0, 10)
    assert whole > 5
    before = scores.copy()
    before[:10] *= -5
    assert fills_cycle(before, beats, bars, 0, 10) == whole
    after = scores.copy()
    after[10 + 32 :] *= -5
    assert fills_cycle(after, beats, bars, 0, 10) == whole
    # The last bar that starts inside the 60 s counts.
    after[10 + 31] *= -5
    assert fills_cycle(after, beats, bars, 0, 10) != whole


def test_the_picture_of_a_part_has_a_row_every_20_ms_and_a_tone_in_the_band_of_its_pitch():
    moments = np.arange(2 * PARTS_RATE) / PARTS_RATE
    low, high = picture(0.1 * np.sin(2 * np.pi * 200 * moments)), picture(0.1 * np.sin(2 * np.pi * 2000 * moments))
    assert low.shape == (101, MEL_BANDS)
    assert 0 < low[50].argmax() < high[50].argmax() < MEL_BANDS - 1
    # Twice the amplitude is 6 dB more.
    louder = picture(0.2 * np.sin(2 * np.pi * 200 * moments))
    assert louder[50].max() - low[50].max() == pytest.approx(6.02, abs=0.01)


def test_the_split_puts_a_low_tone_in_the_bass_and_short_noises_in_the_drums():
    rate = PARTS_RATE
    moments = np.arange(8 * rate) / rate
    tone = 0.3 * np.sin(2 * np.pi * 70 * moments) * (np.sin(2 * np.pi * 2 * moments) > 0)
    hits = np.zeros(len(moments))
    noise = np.random.default_rng(4).uniform(-1, 1, len(moments))
    for start in range(0, len(moments), rate // 4):
        hits[start : start + rate // 50] = 0.5 * noise[start : start + rate // 50] * np.linspace(1, 0, rate // 50)

    def level(sound):
        return 10 * np.log10(np.mean(np.square(sound)) + 1e-12)

    def as_samples(sound, channels=2):
        return (sound[:, None] * 32767).astype(np.int16).repeat(channels, axis=1)

    parts = split(as_samples(tone + hits), rate)
    assert set(parts) == {"drums", "bass"} and all(len(part) == len(moments) for part in parts.values())
    in_bass, in_drums = split(as_samples(tone), rate), split(as_samples(hits), rate)
    assert level(in_bass["bass"]) > level(in_bass["drums"]) + 10
    assert level(in_drums["drums"]) > level(in_drums["bass"]) + 10
    # One channel, or another rate: the same parts, at 44.1 kHz.
    one = split(as_samples(tone + hits, channels=1), rate)
    assert level(one["bass"] - parts["bass"]) < level(parts["bass"]) - 30
    slow = split(as_samples((tone + hits)[::2]), rate // 2)
    assert len(slow["bass"]) == len(moments) and level(slow["bass"]) > level(slow["drums"])


def test_the_pieces_of_a_split_add_up_to_the_song_whatever_its_length(monkeypatch):
    # In place of the model, every part is the sound it was given: the parts must then come back as the song.
    pieces = []

    def the_sound_itself(wave):
        pieces.append(wave.shape[-1] / PARTS_RATE)
        return wave[:, None].repeat(1, 4, 1, 1)

    monkeypatch.setattr(fills, "_model", the_sound_itself)
    sound = 0.2 + 0.1 * np.random.default_rng(6).uniform(-1, 1, 62 * PARTS_RATE)
    # A song that ends within a second after 30 s, or after 60 s, gets no piece for that end alone:
    # the model refuses a piece under 18 ms, and the piece before already holds it.
    lengths = ((20, [20]), (30.01, [30.01]), (30.5, [30.5]), (31, [31]), (31.5, [31, 1.5]), (60.4, [31, 30.4]), (61.7, [31, 31, 1.7]))
    for seconds, expected in lengths:
        samples = (sound[: round(seconds * PARTS_RATE), None] * 32767).astype(np.int16).repeat(2, axis=1)
        pieces.clear()
        parts = split(samples, PARTS_RATE)
        assert pieces == pytest.approx(expected), f"the pieces of a song of {seconds} s"
        for part in parts.values():
            assert np.abs(part - samples[:, 0] / 32768).max() < 1e-4, f"a song of {seconds} s"
