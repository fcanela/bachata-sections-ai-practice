"""Measures where the first beat of each mix is, and writes it into its labels.json.

    uv run python scripts/measure_first_beat.py

The labels' tempo and beat counts are exact, but their times are early by a constant
amount per song. This finds that amount on the percussion tracks of the song: the shift
at which the labelled beats fall on the strongest attacks.

It writes `first_beat_s` and `mix_sha256`, the mix the measurement holds for. The same
measurement is repeated on the mix; when the two differ by more than 10 ms nothing is
written for that song.

Needs ffmpeg, to decode the tracks. The application itself never decodes a file.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from bachata.model import sha256_of
from fixtures.validate import labelled_songs, problems, read_labels

RATE = 44100
STEP = 44  # samples between two measurements: about 1 ms
WINDOW = 441  # samples of the energy window: 10 ms
PERCUSSION = ("gu-ra", "guira", "bongo", "kick", "drum", "percussion")
# The shifts tried, in seconds. Half a beat is 227 ms at 132 BPM: the range stays inside
# it, so that the off-beat cannot be taken for the beat.
SHIFTS = np.arange(-0.100, 0.200, 0.001)
AGREE_S = 0.010


def decode_mono(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype="<f4")


def onset_strength(signal):
    """How much the energy rises at each step: the 10 ms after it against the 10 ms before.

    The signal is differenced first, which favours the sharp attacks of the percussion.
    Entry k is for the time (k * STEP + WINDOW) / RATE.
    """
    squared = np.diff(signal.astype(np.float64)) ** 2
    total = np.concatenate([[0.0], np.cumsum(squared)])
    starts = np.arange(0, len(squared) - 2 * WINDOW, STEP)
    before = total[starts + WINDOW] - total[starts]
    after = total[starts + 2 * WINDOW] - total[starts + WINDOW]
    floor = 1e-10 * WINDOW
    return np.maximum(0.0, np.log(after + floor) - np.log(before + floor))


def best_shift(signal, labels):
    """The shift, in seconds, at which the labelled beats see the strongest attacks on average."""
    strength = onset_strength(signal)
    beats = labels["lead_s"] + np.arange(labels["total_beats"]) * 60 / labels["bpm"]
    scores = []
    for shift in SHIFTS:
        index = np.round(((beats + shift) * RATE - WINDOW) / STEP).astype(int)
        index = index[(index >= 0) & (index < len(strength))]
        scores.append(strength[index].mean())
    return float(SHIFTS[int(np.argmax(scores))])


def measure(folder):
    labels = read_labels(folder)
    if problems(labels):
        return f"labels.json is not valid: {problems(labels)}"
    tracks = [
        path for path in sorted((folder / "tracks").iterdir()) if any(word in path.name for word in PERCUSSION)
    ]
    if not tracks:
        return "no percussion track"
    decoded = [decode_mono(path) for path in tracks]
    percussion = np.sum([track[: min(map(len, decoded))] for track in decoded], axis=0)

    on_percussion = best_shift(percussion, labels)
    on_mix = best_shift(decode_mono(folder / "mix.m4a"), labels)
    report = (
        f"percussion {on_percussion * 1000:+.0f} ms ({', '.join(path.name for path in tracks)}), "
        f"mix {on_mix * 1000:+.0f} ms"
    )
    if abs(on_percussion - on_mix) > AGREE_S:
        return f"{report}: they disagree, nothing written"

    # The two fields go after the song's own, before the sections.
    measured = {name: value for name, value in labels.items() if name not in ("first_beat_s", "mix_sha256", "sections")}
    measured["first_beat_s"] = round(labels["lead_s"] + on_percussion, 3)
    measured["mix_sha256"] = sha256_of(folder / "mix.m4a")
    measured["sections"] = labels["sections"]
    (folder / "labels.json").write_text(json.dumps(measured, indent=1, ensure_ascii=False))
    return f"{report}: first_beat_s = {measured['first_beat_s']}"


if __name__ == "__main__":
    songs = labelled_songs()
    if not songs:
        sys.exit("skipped: no reference material")
    for name, folder in songs.items():
        print(f"{name}: {measure(folder)}")
