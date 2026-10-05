"""The analysis: from the samples of a song to its beats and its tempo.

Two published parts, run as their authors ship them:

- Beat This (the full model) says, for every 20 ms of the song, how likely a beat is.
- The DBN of madmom turns that into beat times. Beat This offers this pairing itself
  (`dbn=True`); the settings below are its own, except for the tempo range.

The tempo range is ours. As published the DBN may follow anything from 55 to 215 BPM, and
in a half-time part it drops to half the tempo, which is not what a dancer counts. Here it
may only follow tempos a bachata dancer steps. The range spans less than a factor of two,
so a tempo and its half or its double are never both allowed.

The DBN does not assume one tempo for the song: the tempo may change at every beat, and a
change costs more the larger it is.
"""

import numpy as np

from bachata.model import checked_model_path

# torch, Beat This and madmom are imported where they are used: they take seconds to
# load, and the program should answer before the first song is analysed.

# Stored with every result. A result with another number is made again from the stored
# sound. Raise it whenever the same song could give different beats or tempo.
ANALYSIS_VERSION = 1

# The tempos a dancer may be counting, in BPM.
MIN_BPM = 90
MAX_BPM = 175

FRAMES_PER_SECOND = 50

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
    """The beat times in seconds, by the DBN, set up as in Beat This's own postprocessor."""
    from madmom.features.downbeats import DBNDownBeatTrackingProcessor

    dbn = DBNDownBeatTrackingProcessor(
        beats_per_bar=[3, 4],
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
    return [float(time) for time in dbn(combined)[:, 0]]


def bpm_at_beats(beats):
    """The shown tempo at each beat: the mean tempo of the ocho around it."""
    last = len(beats) - 1
    shown = []
    for i in range(len(beats)):
        first, end = max(0, i - BPM_SPAN_BEATS), min(last, i + BPM_SPAN_BEATS)
        shown.append(60 * (end - first) / (beats[end] - beats[first]) if end > first else 0.0)
    return shown


def analyse(samples, rate):
    """The beats and the tempo of a song.

    `samples` is what the page sends and the store keeps: 16-bit samples, one row per
    moment, one column per channel.
    """
    mono = samples.astype(np.float32).mean(axis=1) / 32768.0
    beats = beats_from_activations(*beat_activations(mono, rate))
    return {"beats": [round(time, 3) for time in beats], "bpm": [round(bpm, 1) for bpm in bpm_at_beats(beats)]}
