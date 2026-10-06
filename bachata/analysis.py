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
top of it: nothing here hears which of two bars starts an ocho, nor a bar that is extra
(LOG.md, session 6). The page lets the user say where count 1 is.
"""

import numpy as np

from bachata.model import checked_model_path

# torch, Beat This and madmom are imported where they are used: they take seconds to
# load, and the program should answer before the first song is analysed.

# Stored with every result. A result with another number is made again from the stored
# sound. Raise it whenever the same song could give different beats or tempo.
ANALYSIS_VERSION = 2

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


def analyse(samples, rate):
    """The beats of a song, with the tempo, the place in the bar and the count at each.

    `samples` is what the page sends and the store keeps: 16-bit samples, one row per
    moment, one column per channel.
    """
    mono = samples.astype(np.float32).mean(axis=1) / 32768.0
    beats, bars = beats_from_activations(*beat_activations(mono, rate))
    return {
        "beats": [round(time, 3) for time in beats],
        "bpm": [round(bpm, 1) for bpm in bpm_at_beats(beats)],
        "bar": bars,
        "count": count_from_bars(bars, first_heard_bar(mono, rate, beats, bars)),
    }
