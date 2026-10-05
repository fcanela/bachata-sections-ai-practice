import threading

import numpy as np

from bachata.queue import Queue
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
