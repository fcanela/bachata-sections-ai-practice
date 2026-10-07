"""The fills: which of two bars starts an ocho, from the percussion and the bass of a song.

In bachata the first bar of an ocho marks the beats and the second fills: the percussion
and the bass have more of their attacks between two beats in the bar on 5 to 8. That is
heard on the two instruments alone, so the song is first split into its parts.

One published part, run as its authors ship it:

- Hybrid Demucs, as torchaudio offers it (HDEMUCS_HIGH_MUSDB_PLUS), splits a song into
  drums, bass, the rest and the voice. The drums and the bass are used.

The rest is ours. For each of the two parts and each bar: the share of the part's attacks
that fall on the four beats, minus half the share on the eight sixteenths next to a beat.
A bar is compared with the two around it, and the bars of the 60 seconds from where the
percussion comes in say which kind of bar has more. Before the percussion comes in there
is nothing to hear this on.

The analysis asks the fills only where what comes in during the first minute does not
say clearly which bar starts an ocho: the split takes some 30 seconds a song.
"""

import numpy as np

from bachata.analysis import BEATS_PER_BAR, BEATS_PER_OCHO, FRAMES_PER_SECOND
from bachata.model import checked_parts_path

# torch and torchaudio are imported where they are used, as in the analysis.

# The rate Hybrid Demucs was trained at. A song at another rate is brought to it first.
PARTS_RATE = 44100
# The parts in the order the model gives them, and the two that are listened to.
PARTS = ("drums", "bass", "other", "vocals")
HEARD = ("drums", "bass")
# A song is split in pieces of this many seconds, which fade into each other over this many.
PIECE_S = 30
FADE_S = 1.0

# The picture of a part: this many mel bands between these two frequencies in Hz, from
# windows of 46 ms.
MEL_BANDS = 80
MEL_LOWEST_HZ = 30
MEL_HIGHEST_HZ = 16000
WINDOW = 2048

# The percussion is in at a bar when its level there is no further than this under its
# loudest in the song, in dB, and it has come in where that holds for 4 bars in a row.
IN_DB = 12
IN_BARS = 4
# The fills are heard over the bars that start in this many seconds from there.
FILLS_WINDOW_S = 60
# What a bar has over the two around it is cut at this many times its usual size in the song.
CUT = 3.0
# What each sixteenth of a beat weighs: the beat itself, and the two next to a beat.
WEIGHTS = {0: 1.0, 1: -0.5, 3: -0.5}

_model = None


def split(samples, rate):
    """The drums and the bass of a song, each as one channel at 44.1 kHz.

    `samples` is what the analysis gets: 16-bit samples, one column per channel.
    """
    import torch
    import torchaudio

    global _model
    if _model is None:
        _model = torchaudio.models.hdemucs_high(sources=list(PARTS))
        _model.load_state_dict(torch.load(checked_parts_path(), weights_only=True))
        _model.eval()
    wave = torch.from_numpy(samples.astype(np.float32).T / 32768.0)
    if wave.shape[0] == 1:
        wave = wave.repeat(2, 1)
    if rate != PARTS_RATE:
        wave = torchaudio.functional.resample(wave, rate, PARTS_RATE)
    # The model wants the level of the songs it was trained on.
    both = wave.mean(0)
    mean, spread = both.mean(), both.std() + 1e-8
    wave = (wave - mean) / spread
    length = wave.shape[1]
    piece, fade = int(PIECE_S * PARTS_RATE), int(FADE_S * PARTS_RATE)
    parts = torch.zeros(len(PARTS), 2, length)
    for start in range(0, length, piece):
        end = min(start + piece + fade, length)
        with torch.no_grad():
            found = _model(wave[None, :, start:end])[0]
        weight = torch.ones(end - start)
        if start > 0:
            # The last piece can be shorter than the fade.
            head = min(fade, end - start)
            weight[:head] = torch.linspace(0, 1, fade)[:head]
        if end < length:
            weight[-fade:] = torch.linspace(1, 0, fade)
        parts[:, :, start:end] += found * weight
    parts = parts * spread + mean
    return {name: parts[PARTS.index(name)].mean(0).numpy() for name in HEARD}


def picture(mono):
    """How loud a part is in each mel band, in dB: one row per 20 ms."""
    import torch

    hop = PARTS_RATE // FRAMES_PER_SECOND
    spectrum = torch.stft(
        torch.from_numpy(mono.astype(np.float32)), WINDOW, hop, window=torch.hann_window(WINDOW), center=True, return_complex=True
    )
    power = (spectrum.abs() ** 2).numpy().T
    frequencies = np.fft.rfftfreq(WINDOW, 1 / PARTS_RATE)
    mel = lambda hz: 2595 * np.log10(1 + hz / 700)
    edges = 700 * (10 ** (np.linspace(mel(MEL_LOWEST_HZ), mel(MEL_HIGHEST_HZ), MEL_BANDS + 2) / 2595) - 1)
    bank = np.zeros((MEL_BANDS, len(frequencies)), dtype=np.float32)
    for band in range(MEL_BANDS):
        low, middle, high = edges[band : band + 3]
        bank[band] = np.clip(np.minimum((frequencies - low) / (middle - low), (high - frequencies) / (high - middle)), 0, None)
    return (10 * np.log10(power @ bank.T + 1e-10)).astype(np.float32)


def bar_starts(bars):
    """The beats that start a bar."""
    return [beat for beat, place in enumerate(bars) if place == 1]


def over_the_bars_around(values):
    """What each bar has over the mean of the two around it, in its usual size in the song. 0 at both ends."""
    over = np.zeros(len(values))
    over[1:-1] = values[1:-1] - (values[:-2] + values[2:]) / 2
    usual = 1.4826 * np.median(np.abs(over - np.median(over))) + 1e-9
    return np.clip(over / usual, -CUT, CUT)


def beat_scores(pictures, beats, bars):
    """One score per bar: above 0 the bar marks the beats, under 0 it fills between them.

    `pictures` is a list of picture(): the parts that are listened to.
    """
    starts = bar_starts(bars)
    scores = np.zeros(len(starts))
    for mel in pictures:
        attacks = np.maximum(np.diff(mel, axis=0, prepend=mel[:1]), 0).sum(axis=1)
        heard = np.zeros((len(starts), 4 * BEATS_PER_BAR))
        for bar, start in enumerate(starts):
            for beat in range(BEATS_PER_BAR):
                if start + beat + 1 >= len(beats):
                    continue
                time, length = beats[start + beat], beats[start + beat + 1] - beats[start + beat]
                for sixteenth in range(4):
                    centre = time + length * sixteenth / 4
                    first = int(round((centre - length / 8) * FRAMES_PER_SECOND))
                    end = int(round((centre + length / 8) * FRAMES_PER_SECOND))
                    piece = attacks[max(first, 0) : max(end, first + 1)]
                    heard[bar, beat * 4 + sixteenth] = piece.mean() if len(piece) else 0.0
        share = heard / (heard.sum(axis=1, keepdims=True) + 1e-9)
        for slot in range(4 * BEATS_PER_BAR):
            if slot % 4 in WEIGHTS:
                scores += WEIGHTS[slot % 4] * over_the_bars_around(share[:, slot])
    return scores


def percussion_entry(drums, beats, bars):
    """The bar where the percussion comes in, as a number among the bars, or None when it never does."""
    starts = bar_starts(bars)
    power = (10 ** (drums / 10)).sum(axis=1)
    loudest = np.percentile(power, 95)
    levels = []
    for start in starts:
        first = int(round(beats[start] * FRAMES_PER_SECOND))
        end = int(round(beats[min(start + BEATS_PER_BAR, len(beats) - 1)] * FRAMES_PER_SECOND))
        heard = power[first : max(end, first + 1)]
        levels.append(10 * np.log10((heard.mean() if len(heard) else 0.0) / loudest + 1e-9))
    is_in = np.array(levels) > -IN_DB
    return next((bar for bar in range(len(starts) - IN_BARS + 1) if is_in[bar : bar + IN_BARS].all()), None)


def fills_cycle(scores, beats, bars, first, entry):
    """How surely the bars that start an ocho counted from `first` mark the beats.

    `scores` is from beat_scores() and `entry` from percussion_entry(). The result is the
    mean of what the bars of the one kind have over the other, divided by its
    uncertainty: above 0 the ochos start as counted from `first`, under 0 a bar later.
    0 with fewer than three bars, or when the percussion never comes in.
    """
    if entry is None:
        return 0.0
    starts = bar_starts(bars)
    since = beats[starts[entry]]
    more = [
        score if (start - first) % BEATS_PER_OCHO == 0 else -score
        for score, start in zip(scores, starts)
        if since <= beats[start] < since + FILLS_WINDOW_S
    ]
    if len(more) < 3:
        return 0.0
    return float(np.mean(more) / (np.std(more, ddof=1) / np.sqrt(len(more)) + 1e-9))


def second_bar_fills(samples, rate, beats, bars, first):
    """fills_cycle() of a song, from its samples: the split, the pictures and the scores."""
    parts = split(samples, rate)
    pictures = {name: picture(part) for name, part in parts.items()}
    scores = beat_scores(list(pictures.values()), beats, bars)
    return fills_cycle(scores, beats, bars, first, percussion_entry(pictures["drums"], beats, bars))
