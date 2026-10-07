import json
import threading

import numpy as np
import pytest

from bachata import model
from bachata.queue import Queue, failure_of
from bachata.store import RATE, Store

ID_A, ID_B, ID_C = "a" * 32, "b" * 32, "c" * 32


def add(store, song_id, level):
    """A song whose samples all have the value `level`, so that a result can say which song it is."""
    upload = store.incoming(song_id)
    upload.write_bytes(np.full((RATE, 2), level, dtype="<i2").tobytes())
    store.add(song_id, f"Song {level}", upload)


def analyse(samples, rate):
    assert rate == RATE and samples.shape == (RATE, 2) and samples.dtype == np.int16
    if samples[0, 0] == 13:
        raise RuntimeError("this song cannot be analysed")
    return {"beats": [float(samples[0, 0])], "bpm": [120.0]}


def states(store, queue):
    return [(song["id"][0], queue.state(song)) for song in store.songs()]


def test_songs_are_analysed_one_at_a_time_in_the_order_they_arrived(tmp_path):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    for song_id, level in ((ID_B, 2), (ID_A, 1), (ID_C, 3)):
        add(store, song_id, level)
    assert states(store, queue) == [("b", "waiting"), ("a", "waiting"), ("c", "waiting")]

    assert queue.run_one() is True
    assert states(store, queue) == [("b", "ready"), ("a", "waiting"), ("c", "waiting")]
    assert queue.run_one() is True
    assert states(store, queue) == [("b", "ready"), ("a", "ready"), ("c", "waiting")]
    assert queue.run_one() is True
    assert queue.run_one() is False
    assert store.song(ID_B)["result"]["beats"] == [2.0]
    assert store.song(ID_B)["result"]["version"] == 1


def test_a_song_that_fails_is_marked_failed_and_the_next_one_runs(tmp_path, capsys):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    add(store, ID_A, 13)
    add(store, ID_B, 2)
    assert queue.run_one() is True
    assert states(store, queue) == [("a", "failed"), ("b", "waiting")]
    assert "this song cannot be analysed" in capsys.readouterr().err
    assert queue.run_one() is True
    assert states(store, queue) == [("a", "failed"), ("b", "ready")]
    # A failed song is not tried again by the same version.
    assert queue.run_one() is False


def test_the_song_being_analysed_shows_as_analysing(tmp_path):
    store = Store(tmp_path)
    seen = []
    queue = Queue(store, lambda samples, rate: seen.append(states(store, queue)) or analyse(samples, rate), version=1)
    add(store, ID_A, 1)
    add(store, ID_B, 2)
    queue.run_one()
    assert seen == [[("a", "analysing"), ("b", "waiting")]]


def test_the_queue_survives_a_restart(tmp_path):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    for song_id, level in ((ID_B, 2), (ID_A, 1), (ID_C, 3)):
        add(store, song_id, level)
    queue.run_one()

    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    assert states(store, queue) == [("b", "ready"), ("a", "waiting"), ("c", "waiting")]
    queue.run_one()
    assert states(store, queue) == [("b", "ready"), ("a", "ready"), ("c", "waiting")]


def test_a_result_of_an_older_version_sends_its_song_back_to_the_queue(tmp_path):
    store = Store(tmp_path)
    old = Queue(store, analyse, version=1)
    add(store, ID_A, 1)
    add(store, ID_B, 13)
    old.run_one(), old.run_one()
    assert states(store, old) == [("a", "ready"), ("b", "failed")]

    new = Queue(Store(tmp_path), lambda samples, rate: {"beats": [9.0], "bpm": [0.0]}, version=2)
    store = new._store
    assert states(store, new) == [("a", "waiting"), ("b", "waiting")]
    assert new.run_one() is True
    assert store.song(ID_A)["result"] == {"version": 2, "beats": [9.0], "bpm": [0.0], "seconds": 0.0}
    assert new.run_one() is True
    assert states(store, new) == [("a", "ready"), ("b", "ready")]


def test_a_waiting_song_that_is_deleted_is_out_of_the_queue(tmp_path):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    add(store, ID_A, 1)
    add(store, ID_B, 2)
    store.delete(ID_A)
    assert queue.run_one() is True
    assert states(store, queue) == [("b", "ready")]
    assert queue.run_one() is False


def test_a_song_deleted_while_it_is_analysed_is_discarded(tmp_path):
    store = Store(tmp_path)

    def delete_then_analyse(samples, rate):
        store.delete(ID_A)
        return analyse(samples, rate)

    queue = Queue(store, delete_then_analyse, version=1)
    add(store, ID_A, 1)
    assert queue.run_one() is True
    assert store.songs() == []
    assert list((tmp_path / "songs").iterdir()) == [] and list((tmp_path / "tmp").iterdir()) == []


def test_the_running_queue_takes_songs_as_they_arrive(tmp_path):
    store = Store(tmp_path)
    done = threading.Event()

    def analyse_and_tell(samples, rate):
        result = analyse(samples, rate)
        if samples[0, 0] == 2:
            done.set()
        return result

    queue = Queue(store, analyse_and_tell, version=1)
    queue.start()
    try:
        add(store, ID_A, 1)
        queue.wake()
        add(store, ID_B, 2)
        queue.wake()
        assert done.wait(5)
    finally:
        queue.stop()
    assert states(store, queue) == [("a", "ready"), ("b", "ready")]


def test_the_running_queue_outlives_a_library_it_cannot_write(tmp_path, capsys):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    write, failed, done = store.write_result, threading.Event(), threading.Event()

    def full_disk(song_id, result):
        failed.set()
        raise OSError("No space left on device")

    def and_tell(song_id, result):
        write(song_id, result)
        done.set()

    store.write_result = full_disk
    add(store, ID_A, 1)
    queue.start()
    try:
        assert failed.wait(5)
        store.write_result = and_tell
        queue.wake()
        assert done.wait(5)
    finally:
        queue.stop()
    assert states(store, queue) == [("a", "ready")]
    assert "No space left on device" in capsys.readouterr().err


# Why an analysis failed

# What torch 2 says when the machine has no memory left for a tensor.
TORCH_NO_MEMORY = (
    "[enforce fail at alloc_cpu.cpp:118] err == 0. DefaultCPUAllocator: can't allocate memory: "
    "you tried to allocate 3221225472 bytes. Error code 12 (Cannot allocate memory)"
)


class OutOfMemoryError(RuntimeError):
    """Stands for torch.OutOfMemoryError, which has this name and this parent."""


def failed(tmp_path, analyse):
    """The stored result of one song after the queue ran `analyse` on it."""
    store = Store(tmp_path / "library")
    add(store, ID_A, 1)
    assert Queue(store, analyse, version=1).run_one() is True
    kept = json.loads((tmp_path / "library" / "songs" / ID_A / "result.json").read_text())
    assert kept == store.song(ID_A)["result"]
    return kept


def raising(error):
    def analyse(samples, rate):
        raise error

    return analyse


@pytest.mark.parametrize(
    "error",
    [MemoryError(), RuntimeError(TORCH_NO_MEMORY), OutOfMemoryError("CUDA out of memory. Tried to allocate 20.00 MiB"), OutOfMemoryError()],
)
def test_an_analysis_that_gets_no_memory_fails_for_memory(tmp_path, capsys, error):
    assert failed(tmp_path, raising(error)) == {"version": 1, "error": type(error).__name__, "reason": "memory", "seconds": 0.0}


@pytest.mark.parametrize("changed", [False, True])
def test_a_checkpoint_that_is_missing_or_changed_fails_for_the_model(tmp_path, capsys, monkeypatch, changed):
    # A path of its own: the checkpoints of the program stay where they are.
    checkpoint = tmp_path / "not-fetched.ckpt"
    if changed:
        checkpoint.write_bytes(b"not the recorded file")
    for path, check in (("MODEL_PATH", model.checked_model_path), ("PARTS_PATH", model.checked_parts_path)):
        monkeypatch.setattr(model, path, checkpoint)
        kept = failed(tmp_path / path, lambda samples, rate: check())
        assert kept == {"version": 1, "error": "Checkpoint", "reason": "model", "seconds": 0.0}
    said = capsys.readouterr().err
    assert ("has sha256" in said) is changed and ("is missing" in said) is not changed


@pytest.mark.parametrize("damage", ["gone", "half a sample", "one channel short"])
def test_a_stored_sound_that_cannot_be_read_fails_for_the_sound(tmp_path, capsys, damage):
    store = Store(tmp_path)
    add(store, ID_A, 1)
    add(store, ID_B, 2)
    sound, asked = store.sound_path(ID_A), []
    if damage == "gone":
        sound.unlink()
    else:
        sound.write_bytes(sound.read_bytes()[: -1 if damage == "half a sample" else -2])
    queue = Queue(store, lambda samples, rate: asked.append(samples[0, 0]) or analyse(samples, rate), version=1)
    assert queue.run_one() is True
    kept = store.song(ID_A)["result"]
    assert kept == {"version": 1, "error": "FileNotFoundError" if damage == "gone" else "ValueError", "reason": "sound", "seconds": 0.0}
    # The analysis was never called for it, and what went wrong is in the log.
    assert asked == []
    assert kept["error"] in capsys.readouterr().err
    # The song after it is analysed all the same.
    assert queue.run_one() is True
    assert states(store, queue) == [("a", "failed"), ("b", "ready")] and asked == [2]


@pytest.mark.parametrize(
    "error",
    [
        IndexError("list index out of range"),
        # The same classes as a sound that cannot be read, but raised by the analysis.
        ValueError("cannot reshape array of size 3 into shape (2)"),
        FileNotFoundError("sound.raw"),
        # A RuntimeError that is neither a checkpoint nor memory.
        RuntimeError("this song cannot be analysed"),
        RuntimeError("models/beat_this-final0.ckpt is missing"),
        # Only a RuntimeError is read for what it says.
        KeyError("out of memory"),
        OSError(28, "No space left on device"),
    ],
)
def test_any_other_failure_of_the_analysis_fails_for_another_reason(tmp_path, capsys, error):
    assert failed(tmp_path, raising(error)) == {"version": 1, "error": type(error).__name__, "reason": "other", "seconds": 0.0}


def test_a_failure_keeps_for_how_long_the_analysis_ran(tmp_path, capsys, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("bachata.queue.time.monotonic", lambda: now[0])

    def after(seconds, error):
        def analyse(samples, rate):
            now[0] += seconds
            raise error

        return analyse

    assert failed(tmp_path / "1", after(41.66, MemoryError()))["seconds"] == 41.7
    assert failed(tmp_path / "2", after(62.04, IndexError()))["seconds"] == 62.0
    assert failed(tmp_path / "3", after(0.44, model.Checkpoint("missing")))["seconds"] == 0.4
    # The sound is read inside that time: the clock starts before it.
    store = Store(tmp_path / "4")
    add(store, ID_A, 1)

    def slow_and_broken(song_id):
        now[0] += 1.26
        return np.zeros(3, dtype="<i2").reshape(-1, 2)

    store.samples = slow_and_broken
    queue = Queue(store, analyse, version=1)
    queue.run_one()
    assert store.song(ID_A)["result"] == {"version": 1, "error": "ValueError", "reason": "sound", "seconds": 1.3}


def test_a_failure_has_none_of_the_keys_of_a_result_and_a_result_has_no_reason(tmp_path, capsys):
    store = Store(tmp_path)
    queue = Queue(store, analyse, version=1)
    add(store, ID_A, 13)
    add(store, ID_B, 2)
    queue.run_one(), queue.run_one()
    assert store.song(ID_A)["result"].keys() == {"version", "error", "reason", "seconds"}
    assert store.song(ID_B)["result"].keys() == {"version", "beats", "bpm", "seconds"}


def test_a_stored_failure_is_read_with_one_of_the_four_reasons(tmp_path):
    for reason in ("memory", "model", "sound", "other"):
        assert failure_of({"version": 1, "error": "X", "reason": reason, "seconds": 41.7}) == {"reason": reason, "seconds": 41.7}
    # Stored before reasons were kept.
    assert failure_of({"version": 1, "error": "MemoryError"}) == {"reason": "other", "seconds": None}
    # A reason that is not one of the four, of whatever kind, and nothing else is passed on.
    for reason in ("disk", "Memory", "", None, 3, ["memory"], {"memory": 1}):
        assert failure_of({"version": 1, "error": "OSError", "reason": reason, "seconds": 1.5}) == {"reason": "other", "seconds": 1.5}


def test_a_failed_song_waits_again_once_its_failure_is_thrown_away(tmp_path, capsys):
    store = Store(tmp_path)
    tries = []

    def fails_once(samples, rate):
        tries.append(int(samples[0, 0]))
        if tries.count(13) == 1 and samples[0, 0] == 13:
            raise MemoryError()
        return {"beats": [float(samples[0, 0])], "bpm": [120.0]}

    queue = Queue(store, fails_once, version=1)
    for song_id, level in ((ID_A, 1), (ID_B, 13), (ID_C, 3)):
        add(store, song_id, level)
    queue.run_one(), queue.run_one()
    assert states(store, queue) == [("a", "ready"), ("b", "failed"), ("c", "waiting")]

    assert store.discard_failure(ID_B) is True
    # It keeps its place, before the song that arrived after it and still waits.
    assert states(store, queue) == [("a", "ready"), ("b", "waiting"), ("c", "waiting")]
    assert queue.run_one() is True
    assert states(store, queue) == [("a", "ready"), ("b", "ready"), ("c", "waiting")]
    assert tries == [1, 13, 13]


def test_a_failed_song_is_not_tried_again_after_a_restart(tmp_path, capsys):
    store = Store(tmp_path)
    add(store, ID_A, 13)
    Queue(store, analyse, version=1).run_one()

    store = Store(tmp_path)
    queue = Queue(store, lambda samples, rate: pytest.fail("the failed song was analysed again"), version=1)
    assert states(store, queue) == [("a", "failed")]
    assert queue.run_one() is False
