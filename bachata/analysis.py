"""The analysis: from the samples of a song to its beats, its tempo, its bars and a count.

Two published parts, run as their authors ship them:

- Beat This (the full model) says, for every 20 ms of the song, how likely a beat is, and
  how likely the first beat of a bar.
- The DBN of madmom turns that into beat times, and gives each beat its place in its bar.
  Beat This offers this pairing itself (`dbn=True`); the settings below are its own,
  except for the tempo range and the length of a bar.

The tempo range is ours. As published the DBN may follow anything from 55 to 215 BPM, and
in a half-time part it drops to half the tempo, which is not what a dancer counts. Here it
may only follow tempos a bachata dancer steps. The range spans less than a factor of two,
so a tempo and its half or its double are never both allowed.

The DBN does not assume one tempo for the song: the tempo may change at every beat, and a
change costs more the larger it is.

A bar is four beats, always: as published the DBN may also choose bars of three. The
place in the bar is what the analysis answers for. The count from 1 to 8 is a guess on
top of it, and the page lets the user say where count 1 is.

Which of two bars starts an ocho is ours too, and is read from the sound: an instrument
that comes in, comes in on count 1. The count is set once, for the whole song, by the
places where the sound rises in its first minute, over music that is already playing.
Where nothing rises, the bass decides: it is louder in the first bar of an ocho than in
the second. Where the rises do not agree, the fills decide: the percussion and the bass
mark the beats in the first bar and fill between them in the second (bachata/fills.py).
Nothing here hears a bar that is extra later in the song (LOG.md, sessions 6 and 9).
"""

import numpy as np

from bachata.model import checked_model_path

# torch, Beat This and madmom are imported where they are used: they take seconds to
# load, and the program should answer before the first song is analysed.

# Stored with every result. A result with another number is made again from the stored
# sound. Raise it whenever the same song could give different beats or tempo.
ANALYSIS_VERSION = 5

# The tempos a dancer may be counting, in BPM.
MIN_BPM = 90
MAX_BPM = 175

FRAMES_PER_SECOND = 50

BEATS_PER_BAR = 4
BEATS_PER_OCHO = 8

# A beat this far under the level of the whole song is silence: the tracker carries the
# pulse back over the silence before a song, and no ocho starts there. As a ratio of
# amplitudes: 40 dB.
SILENCE = 0.01

# Where the sound is looked at for what comes in: in bands an equal part of an octave wide,
# between these two frequencies in Hz, and no further than this under its loudest, in dB.
BANDS = 16
LOWEST_HZ = 40
HIGHEST_HZ = 16000
FLOOR_DB = 60

# The sound rises at a beat by how much louder the 4 beats from it are than the 4 beats
# before it, in dB, as a mean over the bands, a band that gets quieter counting as 0.
RISE_SPAN_BEATS = 4
# Something comes in where the rise is at least this much, in dB, and no beat within 3
# beats rises more.
ENTRY_RISE_DB = 5.0
ENTRY_APART_BEATS = 3
# A rise comes out of silence when the 4 beats before it are this far under the level of
# the song, in dB. That is the song starting, and it cannot move the count: where a song
# starts quietly, the place of its first bars is the tracker's guess. Seen on the songs
# the owner checked by ear (LOG.md, session 9).
OUT_OF_SILENCE_DB = 15
# The count is set by what comes in during this many seconds from the start. Later in a
# song a bar that is extra moves the ochos, and what comes in after it would vote wrong.
ENTRY_WINDOW_S = 60

# Where nothing comes in, the bass says which bar starts an ocho: it is louder in the
# first bar than in the second. The bass is the lowest of the bands, 40 to 123 Hz, over
# the bars that start in this many seconds: longer than for what comes in, because this
# is a mean over bars and needs many.
BASS_BANDS = 3
BASS_WINDOW_S = 90
# The bass is sure when the mean difference between the two kinds of bar is this many
# times its own uncertainty.
BASS_SURE = 2.0

# What comes in says clearly which bar starts an ocho when one of the two has at least
# this many times the rise of the other. Under that, the fills are asked.
VOTE_CLEAR = 3
# The fills are sure when the mean difference between the two kinds of bar is this many
# times its own uncertainty.
FILLS_SURE = 2.0

# The shown tempo at a beat is measured from 4 beats before it to 4 beats after it: one
# ocho. Beat times come in steps of 20 ms, so a single interval is only good to about 4%.
BPM_SPAN_BEATS = 4

_frames = None


def beat_activations(mono, rate):
    """How likely a beat and a downbeat are in every 20 ms of the song, from Beat This."""
    import torch
    from beat_this.inference import Audio2Frames

    global _frames
    if _frames is None:
        _frames = Audio2Frames(checkpoint_path=str(checked_model_path()), device="cpu")
    beat, downbeat = _frames(mono, rate)
    return torch.sigmoid(beat.double()).numpy(), torch.sigmoid(downbeat.double()).numpy()


def beats_from_activations(beat, downbeat):
    """The beat times in seconds and the place of each beat in its bar, 1 to 4.

    By the DBN, set up as in Beat This's own postprocessor.
    """
    from madmom.features.downbeats import DBNDownBeatTrackingProcessor

    dbn = DBNDownBeatTrackingProcessor(
        beats_per_bar=[BEATS_PER_BAR],
        min_bpm=MIN_BPM,
        max_bpm=MAX_BPM,
        fps=FRAMES_PER_SECOND,
        transition_lambda=100,
    )
    # 0 and 1 create problems in the DBN.
    epsilon = 1e-5
    beat = beat * (1 - epsilon) + epsilon / 2
    downbeat = downbeat * (1 - epsilon) + epsilon / 2
    combined = np.vstack((np.maximum(beat - downbeat, epsilon / 2), downbeat)).T
    found = dbn(combined)
    return [float(time) for time in found[:, 0]], [int(place) for place in found[:, 1]]


def first_heard_bar(mono, rate, beats, bars):
    """The first beat that starts a bar and is not silence, or 0 when there is none."""
    level = float(np.sqrt(np.mean(np.square(mono, dtype=np.float64)))) if len(mono) else 0.0
    for beat, place in enumerate(bars):
        if place != 1:
            continue
        end = beats[beat + 1] if beat + 1 < len(beats) else len(mono) / rate
        heard = mono[round(beats[beat] * rate) : round(end * rate)]
        if len(heard) and np.sqrt(np.mean(np.square(heard, dtype=np.float64))) > SILENCE * level:
            return beat
    return 0


def band_levels(mono, rate, beats):
    """How loud each beat is in each band, in dB: one row per beat, from it to the next."""
    hop = rate // FRAMES_PER_SECOND
    size = 2 ** round(np.log2(rate * 0.046))
    starts = np.arange(0, len(mono) - size, hop)
    frequencies = np.fft.rfftfreq(size, 1 / rate)
    edges = np.geomspace(LOWEST_HZ, min(HIGHEST_HZ, rate / 2), BANDS + 1)
    in_band = [(frequencies >= low) & (frequencies < high) for low, high in zip(edges, edges[1:])]
    energy = np.zeros((len(starts), BANDS))
    # In pieces, to keep the memory small: a whole song is some 15,000 frames.
    for piece in range(0, len(starts), 4096):
        frames = np.stack([mono[start : start + size] for start in starts[piece : piece + 4096]])
        power = np.abs(np.fft.rfft(frames * np.hanning(size), axis=1)) ** 2
        energy[piece : piece + 4096] = np.stack([power[:, band].sum(axis=1) for band in in_band], axis=1)
    levels = np.full((len(beats), BANDS), -100.0)
    for beat, time in enumerate(beats):
        first = int(time * FRAMES_PER_SECOND)
        end = int((beats[beat + 1] if beat + 1 < len(beats) else time + 0.5) * FRAMES_PER_SECOND)
        heard = energy[first : max(end, first + 1)]
        if len(heard):
            levels[beat] = 10 * np.log10(heard.mean(axis=0) + 1e-10)
    return np.maximum(levels, levels.max() - FLOOR_DB) if len(beats) else levels


def rises(levels):
    """How much the sound rises at each beat, in dB. 0 at the beats too near either end."""
    span = RISE_SPAN_BEATS
    rise = np.zeros(len(levels))
    for beat in range(span, len(levels) - span):
        change = levels[beat : beat + span].mean(axis=0) - levels[beat - span : beat].mean(axis=0)
        rise[beat] = np.maximum(change, 0).mean()
    return rise


def over_music(levels):
    """For each beat, whether the beats before it are music and not silence."""
    if not len(levels):
        return []
    power = (10 ** (levels / 10)).sum(axis=1)
    song = np.median(10 * np.log10(power))
    return [
        bool(beat > 0 and 10 * np.log10(power[max(0, beat - RISE_SPAN_BEATS) : beat].mean()) >= song - OUT_OF_SILENCE_DB)
        for beat in range(len(levels))
    ]


def entries(rise, bars, music):
    """Where something comes in: the bar it starts, as the number of a beat, its rise, and
    whether it comes in over music.

    What comes in is often led in by a beat or two, so it starts the nearest bar, and
    the bar after when it is in the middle of one.
    """
    found = []
    for beat in range(len(rise)):
        near = rise[max(0, beat - ENTRY_APART_BEATS) : beat + ENTRY_APART_BEATS + 1]
        if rise[beat] >= ENTRY_RISE_DB and rise[beat] == near.max():
            place = bars[beat]
            bar = beat - (place - 1) if place <= 2 else beat + (BEATS_PER_BAR + 1 - place)
            found.append((bar, float(rise[beat]), bool(music[beat])))
    return found


def bass_cycle(levels, beats, first):
    """How surely the bass is louder in the bars that start an ocho counted from `first`.

    Each bar is compared with the two around it. The result is the mean of what the bars
    of the one kind have over the other, divided by its uncertainty: above 0 the ochos
    start as counted from `first`, under 0 a bar later. 0 with fewer than three bars.
    """
    if not len(levels):
        return 0.0
    bass = 10 * np.log10((10 ** (levels[:, :BASS_BANDS] / 10)).sum(axis=1))
    more = []
    for bar in range(first % BEATS_PER_BAR, len(bass) - 2 * BEATS_PER_BAR + 1, BEATS_PER_BAR):
        if bar >= BEATS_PER_BAR and beats[bar] < BASS_WINDOW_S:
            around = (bass[bar - BEATS_PER_BAR : bar].mean() + bass[bar + BEATS_PER_BAR : bar + 2 * BEATS_PER_BAR].mean()) / 2
            over = bass[bar : bar + BEATS_PER_BAR].mean() - around
            more.append(over if (bar - first) % BEATS_PER_OCHO == 0 else -over)
    if len(more) < 3:
        return 0.0
    return float(np.mean(more) / (np.std(more) / np.sqrt(len(more)) + 1e-9))


def entry_vote(first, beats, found):
    """How much comes in on each of the two bars during the first minute: for `first`, and for the bar after it.

    Each thing that comes in counts for the bar it starts, with the weight of its rise.
    A rise out of silence says nothing for the other bar.
    """
    for_first = for_next = 0.0
    for bar, rise, music in found:
        if bar < len(beats) and beats[bar] < ENTRY_WINDOW_S:
            if (bar - first) % BEATS_PER_OCHO == 0:
                for_first += rise
            elif music:
                for_next += rise
    return for_first, for_next


def vote_is_clear(for_first, for_next):
    """Whether one bar has at least three times what the other has. A vote of nothing is not asked here."""
    return min(for_first, for_next) * VOTE_CLEAR <= max(for_first, for_next)


def first_ocho(first, beats, found, bass=0.0, fills=0.0):
    """The beat that starts the first ocho: `first`, a beat that starts a bar, or the bar after it.

    What comes in during the first minute says which of the two it is: entry_vote().
    The first bar that is heard stays unless the other has more.

    Where nothing comes in, `bass`, from bass_cycle(), decides, when it is sure.
    Where the vote is not clear, `fills`, from fills.fills_cycle(), decides, when it is sure.
    """
    for_first, for_next = entry_vote(first, beats, found)
    if for_first == for_next == 0:
        return first + BEATS_PER_BAR if bass <= -BASS_SURE else first
    if not vote_is_clear(for_first, for_next) and abs(fills) >= FILLS_SURE:
        return first + BEATS_PER_BAR if fills < 0 else first
    return first + BEATS_PER_BAR if for_next > for_first else first


def count_from_bars(bars, first):
    """The count of each beat, 1 to 8: in eights from the beat `first`, which starts a bar.

    The beats before that one are counted as the end of an ocho that started earlier.
    """
    return [(beat - first) % BEATS_PER_OCHO + 1 for beat in range(len(bars))]


def bpm_at_beats(beats):
    """The shown tempo at each beat: the mean tempo of the ocho around it."""
    last = len(beats) - 1
    shown = []
    for i in range(len(beats)):
        first, end = max(0, i - BPM_SPAN_BEATS), min(last, i + BPM_SPAN_BEATS)
        shown.append(60 * (end - first) / (beats[end] - beats[first]) if end > first else 0.0)
    return shown


def analyse(samples, rate, fills_of=None):
    """The beats of a song, with the tempo, the place in the bar and the count at each.

    `samples` is what the page sends and the store keeps: 16-bit samples, one row per
    moment, one column per channel. `fills_of` is fills.second_bar_fills unless a check
    gives another.
    """
    mono = samples.astype(np.float32).mean(axis=1) / 32768.0
    beats, bars = beats_from_activations(*beat_activations(mono, rate))
    first = first_heard_bar(mono, rate, beats, bars)
    levels = band_levels(mono, rate, beats)
    found = entries(rises(levels), bars, over_music(levels))
    fills = 0.0
    if not vote_is_clear(*entry_vote(first, beats, found)):
        # Only here, because it takes the split of the song: bachata/fills.py.
        if fills_of is None:
            from bachata.fills import second_bar_fills as fills_of
        fills = fills_of(samples, rate, beats, bars, first)
    first = first_ocho(first, beats, found, bass_cycle(levels, beats, first), fills)
    return {
        "beats": [round(time, 3) for time in beats],
        "bpm": [round(bpm, 1) for bpm in bpm_at_beats(beats)],
        "bar": bars,
        "count": count_from_bars(bars, first),
    }
