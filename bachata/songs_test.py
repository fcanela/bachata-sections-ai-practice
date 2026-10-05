"""The song checks of ACCEPTANCE.md, on the reference material.

They read the material where the owner keeps it and skip when it is not on the machine.
The mixes are decoded here with ffmpeg, to the samples a browser would send: session 2
measured that Chrome, Firefox and ffmpeg give the same samples for these files.
"""

import functools
import statistics
import subprocess

import numpy as np
import pytest

from bachata.analysis import analyse
from bachata.model import sha256_of
from fixtures.validate import DEV, SAME_BEAT_S, beat_problems, labelled_songs, read_labels, reference_beats

# How far the shown BPM may be from the BPM a dancer counts.
BPM_TOLERANCE = 0.04

# The two commercial recordings and the BPM a dancer counts on each. They have no labels.
RECORDINGS = {"meemborrachare/original.mp3": 124, "elperdedor/original.mp3": 128}

MIXES = sorted(labelled_songs())


def decoded(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "2", "-ar", "44100", "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype="<i2").reshape(-1, 2)


@functools.cache
def analysed(path):
    return analyse(decoded(path), 44100)


def test_the_reference_material_is_on_the_machine():
    if not MIXES:
        pytest.skip("skipped: no reference material")


@pytest.mark.parametrize("song", MIXES)
def test_every_labelled_beat_is_detected_once_and_nothing_else_is(song):
    mix = DEV / song / "mix.m4a"
    reference = reference_beats(read_labels(DEV / song), sha256_of(mix))
    problems = beat_problems(reference, analysed(mix)["beats"])
    assert problems == [], f"{len(problems)} problems on {len(reference)} labelled beats"


@pytest.mark.parametrize("song", MIXES)
def test_the_shown_bpm_is_the_labels_bpm_at_every_labelled_beat(song):
    mix = DEV / song / "mix.m4a"
    labels = read_labels(DEV / song)
    result = analysed(mix)
    wrong = []
    for labelled in reference_beats(labels, sha256_of(mix)):
        nearest = min(range(len(result["beats"])), key=lambda i: abs(result["beats"][i] - labelled))
        assert abs(result["beats"][nearest] - labelled) <= SAME_BEAT_S, f"no beat at {labelled:.3f} s"
        if abs(result["bpm"][nearest] / labels["bpm"] - 1) > BPM_TOLERANCE:
            wrong.append(f"{result['bpm'][nearest]} BPM at {labelled:.3f} s")
    assert wrong == [], f"the labels say {labels['bpm']} BPM"


@pytest.mark.parametrize("recording", sorted(RECORDINGS))
def test_the_shown_bpm_of_a_commercial_recording_is_the_one_a_dancer_counts(recording):
    if not (DEV / recording).exists():
        pytest.skip("skipped: no reference material")
    result = analysed(DEV / recording)
    expected = RECORDINGS[recording]
    outside = [
        time for time, bpm in zip(result["beats"], result["bpm"]) if abs(bpm / expected - 1) > BPM_TOLERANCE
    ]
    # Printed for the owner, who has the last word on these two: `pytest -s` shows it.
    print(
        f"\n{recording}: {len(result['beats'])} beats, median {statistics.median(result['bpm'])} BPM, "
        f"{len(outside)} beats shown more than 4% from {expected} BPM"
        + (f", all between {outside[0]} and {outside[-1]} s" if outside else "")
    )
    assert abs(statistics.median(result["bpm"]) / expected - 1) <= BPM_TOLERANCE


def test_a_song_sent_to_the_upload_address_comes_back_with_its_beats(tmp_path):
    """The whole way of an upload, with the real analysis: the address, the store, the queue."""
    if "meemborrachare" not in MIXES:
        pytest.skip("skipped: no reference material")
    from starlette.testclient import TestClient

    from bachata.server import create_app

    mix = DEV / "meemborrachare" / "mix.m4a"
    samples = decoded(mix)
    song_id = sha256_of(mix)[:32]
    app = create_app(tmp_path / "data")
    client = TestClient(app, base_url="http://127.0.0.1")
    sent = client.put(
        f"/api/songs/{song_id}",
        params={"name": "Me Emborrachare", "rate": 44100, "frames": len(samples)},
        content=samples.tobytes(),
        headers={"Origin": "http://127.0.0.1"},
    )
    assert sent.status_code == 201
    assert app.queue.run_one() is True
    assert client.get(f"/api/songs/{song_id}").json()["state"] == "ready"

    result = client.get(f"/api/songs/{song_id}/result").json()
    reference = reference_beats(read_labels(DEV / "meemborrachare"), sha256_of(mix))
    assert beat_problems(reference, result["beats"]) == []
    # The stored sound is the samples that were sent, so the beats are the same ones.
    assert result == analysed(mix)
