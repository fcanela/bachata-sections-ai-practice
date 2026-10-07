import numpy as np
import pytest

from bachata import fills
from bachata.fills import (
    MEL_BANDS,
    PARTS_RATE,
    beat_scores,
    fills_cycle,
    over_the_bars_around,
    percussion_entry,
    picture,
    second_bar_fills,
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
    # A fill weighs half of what a beat weighs: with as many fills as beats, half as much again.
    assert before[3:10] == pytest.approx(1.5 * half[3:10])
    # Just after a beat it is as much of a fill as just before one.
    assert scores_with(BEAT_S / 4)[3:10] == pytest.approx(before[3:10])


def test_only_where_a_part_gets_louder_is_an_attack():
    # A note on every beat. In every other bar it is held and stops on the sixteenth before the next beat.
    beats, bars = made_up_bars(12)
    mel = np.full((round((beats[-1] + 1) * 50), MEL_BANDS), -60.0, dtype=np.float32)
    for beat, time in enumerate(beats[:-1]):
        mel[round(time * 50) : round(time * 50) + (18 if beat // 4 % 2 else 1)] = 0.0
    assert beat_scores([mel], beats, bars)[2:11] == pytest.approx(np.zeros(9))


def test_a_song_that_gets_faster_is_scored_by_the_length_of_each_beat():
    # Twelve bars at 94 BPM, then twelve at 125. Every other bar has an attack on the sixteenth before
    # each beat, and the bars between have one half way, which is no fill.
    beats = [0.64 * n for n in range(48)] + [48 * 0.64 + 0.48 * n for n in range(49)]
    bars = [n % 4 + 1 for n in range(len(beats))]
    times = []
    for beat in range(96):
        length = beats[beat + 1] - beats[beat]
        times += [beats[beat], beats[beat] + (3 if beat // 4 % 2 else 2) * length / 4]
    scores = beat_scores([picture_with_attacks(times, beats[-1] + 1)], beats, bars)
    assert all(scores[bar] < -1 for bar in range(1, 23, 2)) and all(scores[bar] > 1 for bar in range(2, 23, 2))


def test_a_bar_is_measured_against_the_two_around_it_and_cut_at_three_times_its_usual_size():
    over = over_the_bars_around(np.array([5.0, 1.0, 3.0, 1.0, 3.0, 1.0, 30.0, 1.0, 9.0]))
    assert over[0] == 0 and over[-1] == 0
    # The second bar has 1 where the two around it have 5 and 3: 3 under. The usual size here is 1.4826 * 2.
    assert over[1] == pytest.approx(-3.0 / (1.4826 * 2))
    assert over[3] == pytest.approx(-2.0 / (1.4826 * 2))
    assert over[6] == 3.0 and over[5] == -3.0


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
    # The level of a bar is that of the whole bar: percussion that leaves out the first beat of every bar is in all the same.
    mel, beats, bars = loud_from(6, 20)
    for bar in range(6, 20):
        mel[round(beats[4 * bar] * 50) : round(beats[4 * bar + 1] * 50)] = -40.0
    assert percussion_entry(mel, beats, bars) == 6


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
    # And so does the bar where the percussion comes in.
    first = scores.copy()
    first[10] *= -5
    assert fills_cycle(first, beats, bars, 0, 10) != whole


def test_the_picture_of_a_part_has_a_row_every_20_ms_and_a_tone_in_the_band_of_its_pitch():
    moments = np.arange(2 * PARTS_RATE) / PARTS_RATE
    low, high = picture(0.1 * np.sin(2 * np.pi * 200 * moments)), picture(0.1 * np.sin(2 * np.pi * 2000 * moments))
    assert low.shape == (101, 80)
    assert 0 < low[50].argmax() < high[50].argmax() < 79
    # Twice the amplitude is 6 dB more.
    louder = picture(0.2 * np.sin(2 * np.pi * 200 * moments))
    assert louder[50].max() - low[50].max() == pytest.approx(6.02, abs=0.01)


def test_the_bands_of_a_picture_reach_from_the_low_bass_to_15_khz_and_a_row_is_46_ms_of_sound():
    moments = np.arange(2 * PARTS_RATE) / PARTS_RATE

    def heard(hz):
        """How loud a tone is in the picture, over all its bands, in dB."""
        return 10 * np.log10((10 ** (picture(0.1 * np.sin(2 * np.pi * hz * moments))[50] / 10)).sum())

    # The lowest band starts at 30 Hz, so a tone at 40 Hz is only in part of one. The highest ends at 16 kHz.
    assert heard(40) > heard(200) - 10
    assert heard(15000) == pytest.approx(heard(2000), abs=1.0)
    assert heard(18000) < heard(2000) - 40
    # A click is in the rows whose 46 ms hold it: the row it is on, the one before and the one after.
    click = np.zeros(2 * PARTS_RATE)
    click[PARTS_RATE] = 0.5
    mel = picture(click)
    assert [row for row in range(len(mel)) if mel[row].max() > -90] == [49, 50, 51]


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


def as_stereo(sound):
    return (sound[:, None] * 32767).astype(np.int16).repeat(2, axis=1)


def test_the_model_gets_the_song_at_the_level_it_was_trained_on(monkeypatch):
    given = []

    def the_sound_itself(wave):
        given.append((float(wave.mean()), float(wave.std())))
        return wave[:, None].repeat(1, 4, 1, 1)

    monkeypatch.setattr(fills, "_model", the_sound_itself)
    split(as_stereo(0.2 + 0.1 * np.random.default_rng(6).uniform(-1, 1, 20 * PARTS_RATE)), PARTS_RATE)
    # A mean of 0 and a spread of 1, whatever the song has.
    assert given == [pytest.approx((0, 1), abs=1e-3)]


def test_two_pieces_of_a_split_fade_into_each_other_over_one_second(monkeypatch):
    # In place of the model, the first piece is 1 in every part and the second 0: what comes back
    # says how much the first piece weighs at each moment.
    said = iter((1.0, 0.0))
    monkeypatch.setattr(fills, "_model", lambda wave: wave[:, None].repeat(1, 4, 1, 1) * 0 + next(said))
    samples = as_stereo(0.2 + 0.1 * np.random.default_rng(6).uniform(-1, 1, 32 * PARTS_RATE))
    part = split(samples, PARTS_RATE)["drums"]
    song = samples[:, 0] / 32768
    weighs = (part - song.mean()) / song.std(ddof=1)
    at = lambda seconds: weighs[round(seconds * PARTS_RATE)]
    assert [at(29.9), at(30.25), at(30.5), at(30.75), at(31.1)] == pytest.approx([1, 0.75, 0.5, 0.25, 0], abs=1e-3)


def test_a_part_is_heard_in_both_channels(monkeypatch):
    monkeypatch.setattr(fills, "_model", lambda wave: wave[:, None].repeat(1, 4, 1, 1))
    samples = as_stereo(0.1 * np.random.default_rng(6).uniform(-1, 1, 2 * PARTS_RATE))
    samples[:, 0] = 0
    # Sound in the right channel alone: each part is the two channels together, half as loud.
    assert np.abs(split(samples, PARTS_RATE)["bass"] - samples[:, 1] / 32768 / 2).max() < 1e-4


def test_the_split_refuses_a_checkpoint_that_is_not_the_recorded_file(monkeypatch):
    from bachata import model

    monkeypatch.setattr(fills, "_model", None)
    monkeypatch.setattr(model, "PARTS_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="hdemucs_high_trained.pt has sha256 .*, expected 0000"):
        split(np.zeros((PARTS_RATE, 2), dtype=np.int16), PARTS_RATE)


def clicks(times, seconds):
    """A part as sound: the same short burst of noise at each of `times`."""
    sound = np.zeros(round(seconds * PARTS_RATE))
    burst = 0.5 * np.random.default_rng(8).uniform(-1, 1, 441) * np.linspace(1, 0, 441)
    for time in times:
        sound[round(time * PARTS_RATE) :][:441] += burst
    return sound


def test_the_fills_of_a_song_are_heard_on_its_drums_and_its_bass_from_where_the_drums_come_in(monkeypatch):
    # 44 bars. The drums come in at the thirteenth. A part that says something marks the beats in
    # every other bar and has an attack before each beat in the bars between; one that says nothing
    # marks the beats in every bar. `turned` is the same the other way round.
    beats, bars = made_up_bars(44)
    seconds = beats[-1] + 1

    def part(first_bar, last_bar, says=True, turned=False):
        times = []
        for bar in range(first_bar, last_bar):
            for beat in range(4):
                times.append(beats[4 * bar + beat])
                if says and (bar % 2 == 1) != turned:
                    times.append(beats[4 * bar + beat] + 3 * BEAT_S / 4)
        return clicks(times, seconds)

    split_as = {}
    asked = []
    monkeypatch.setattr(fills, "split", lambda samples, rate: asked.append((samples, rate)) or split_as)
    song = np.zeros((10, 2), dtype=np.int16)

    # The drums say it. Before they come in the bass says the opposite, and after that nothing.
    split_as.update(drums=part(12, 44), bass=part(0, 12, turned=True) + part(12, 44, says=False))
    assert second_bar_fills(song, 44100, beats, bars, 0) > 4
    assert asked[0][0] is song and asked[0][1] == 44100
    # Asked about the ochos counted from the next bar, the answer is the other way.
    assert second_bar_fills(song, 44100, beats, bars, 4) < -4
    # The bass says it, and the drums only come in.
    split_as.update(drums=part(12, 44, says=False), bass=part(0, 12, turned=True) + part(12, 44))
    assert second_bar_fills(song, 44100, beats, bars, 0) > 4
