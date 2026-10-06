import json
import os

import numpy as np
import pytest

from bachata.store import MAX_ONES, RATE, Known, Store, TooMany, well_formed

ID_A = "a" * 32
ID_B = "b" * 32


def some_samples(seconds=1, seed=0):
    return np.random.default_rng(seed).integers(-32768, 32768, size=(RATE * seconds, 2), dtype="<i2")


def add(store, song_id, name="A song", samples=None):
    upload = store.incoming(song_id)
    upload.write_bytes((some_samples() if samples is None else samples).tobytes())
    store.add(song_id, name, upload)


def files_under(folder):
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file())


def test_a_song_is_kept_with_its_name_and_the_exact_samples(tmp_path):
    store = Store(tmp_path)
    samples = some_samples(2)
    add(store, ID_A, "Grupo Extra - Me Emborrachare", samples)

    song = store.song(ID_A)
    assert (song["id"], song["name"], song["frames"], song["result"]) == (ID_A, "Grupo Extra - Me Emborrachare", 2 * RATE, None)
    assert np.array_equal(store.samples(ID_A), samples)
    assert files_under(tmp_path) == [f"songs/{ID_A}/song.json", f"songs/{ID_A}/sound.raw"]
    assert store.sound_path(ID_A).read_bytes() == samples.tobytes()


def test_the_extreme_samples_are_kept_as_they_are(tmp_path):
    store = Store(tmp_path)
    samples = np.array([[-32768, 32767], [32767, -32768], [0, -1], [1, 0]] * 1000, dtype="<i2")
    add(store, ID_A, samples=samples)
    assert np.array_equal(store.samples(ID_A), samples)


def test_a_song_is_not_stored_twice(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A, "First")
    with pytest.raises(Known):
        add(store, ID_A, "Second")
    assert store.song(ID_A)["name"] == "First"
    assert files_under(tmp_path) == [f"songs/{ID_A}/song.json", f"songs/{ID_A}/sound.raw"]


def test_songs_come_in_the_order_they_arrived(tmp_path):
    store = Store(tmp_path)
    for song_id in (ID_B, ID_A, "c" * 32):
        add(store, song_id)
    assert [song["id"] for song in store.songs()] == [ID_B, ID_A, "c" * 32]


def test_the_library_survives_a_restart(tmp_path):
    store = Store(tmp_path)
    add(store, ID_B, "Second letter, first to arrive")
    add(store, ID_A, "With a result")
    store.write_result(ID_A, {"version": 1, "beats": [1.0, 1.5], "bpm": [120.0, 120.0]})

    again = Store(tmp_path)
    assert [song["id"] for song in again.songs()] == [ID_B, ID_A]
    assert again.song(ID_B)["name"] == "Second letter, first to arrive"
    assert again.song(ID_B)["result"] is None
    assert again.song(ID_A)["result"] == {"version": 1, "beats": [1.0, 1.5], "bpm": [120.0, 120.0]}
    assert np.array_equal(again.samples(ID_A), some_samples())


def test_a_renamed_song_keeps_everything_but_its_name(tmp_path):
    store = Store(tmp_path)
    samples = some_samples()
    add(store, ID_A, "track0", samples)
    store.write_result(ID_A, {"version": 1, "beats": [1.0], "bpm": [120.0]})
    before = store.song(ID_A)["added"]

    assert store.rename(ID_A, "Grupo Extra - Me Emborracharé") is True
    for library in (store, Store(tmp_path)):
        song = library.song(ID_A)
        assert (song["name"], song["frames"], song["added"]) == ("Grupo Extra - Me Emborracharé", RATE, before)
        assert song["result"] == {"version": 1, "beats": [1.0], "bpm": [120.0]}
        assert np.array_equal(library.samples(ID_A), samples)
    # The name is in song.json only, and nothing is left on the way.
    kept = json.loads((tmp_path / "songs" / ID_A / "song.json").read_text())
    assert kept.keys() == {"id", "name", "frames", "added", "ones"}
    assert files_under(tmp_path) == [f"songs/{ID_A}/{name}" for name in ("result.json", "song.json", "sound.raw")]

    assert store.rename(ID_B, "Not there") is False
    assert files_under(tmp_path) == [f"songs/{ID_A}/{name}" for name in ("result.json", "song.json", "sound.raw")]


def test_a_deleted_song_leaves_nothing_behind(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A)
    store.write_result(ID_A, {"version": 1, "beats": [], "bpm": []})
    assert store.delete(ID_A) is True
    assert store.song(ID_A) is None
    assert store.songs() == []
    assert files_under(tmp_path) == []
    assert store.delete(ID_A) is False
    # The result of an analysis that was still running is discarded.
    store.write_result(ID_A, {"version": 1, "beats": [], "bpm": []})
    assert files_under(tmp_path) == []


def test_what_an_interrupted_upload_left_is_removed_at_startup(tmp_path):
    store = Store(tmp_path)
    store.incoming(ID_A).write_bytes(b"half an upload")
    assert files_under(tmp_path) != []
    assert Store(tmp_path).songs() == []
    assert files_under(tmp_path) == []


def test_an_upload_that_is_given_up_leaves_nothing(tmp_path):
    store = Store(tmp_path)
    upload = store.incoming(ID_A)
    upload.write_bytes(b"not wanted")
    store.discard(upload)
    assert files_under(tmp_path) == []


def test_the_library_is_full_when_it_reaches_its_limit(tmp_path):
    store = Store(tmp_path, limit=1000)
    assert not store.full()
    add(store, ID_A)
    assert store.full()
    assert not Store(tmp_path).full()


def test_only_a_well_formed_id_becomes_a_name_on_disk(tmp_path):
    assert well_formed("0123456789abcdef0123456789abcdef")
    bad = ["", "a" * 31, "a" * 33, "A" * 32, "g" * 32, "../" + "a" * 29, "a" * 31 + "/", "a" * 32 + "\n", None, 5]
    store = Store(tmp_path / "data")
    for song_id in bad:
        assert not well_formed(song_id), repr(song_id)
        with pytest.raises(ValueError):
            store.incoming(song_id)
        with pytest.raises(ValueError):
            store.sound_path(song_id)
    # Nothing was written, inside the data folder or beside it.
    assert files_under(tmp_path) == []
    assert os.listdir(tmp_path) == ["data"]


def test_the_text_a_page_sent_never_names_a_file(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A, "../../etc/passwd")
    assert files_under(tmp_path) == [f"songs/{ID_A}/song.json", f"songs/{ID_A}/sound.raw"]
    assert json.loads((tmp_path / "songs" / ID_A / "song.json").read_text())["name"] == "../../etc/passwd"


def test_the_beats_set_to_count_1_are_kept_with_the_song(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A)
    store.write_result(ID_A, {"version": 1, "beats": [1.0], "bpm": [120.0]})
    assert store.song(ID_A)["ones"] == []

    assert store.set_one(ID_A, 12.5, True) is True
    assert store.set_one(ID_A, 3.0, True) is True
    assert store.set_one(ID_A, 12.5, True) is True
    assert store.set_one(ID_A, 40.0, False) is True
    assert store.rename(ID_A, "Renamed") is True
    for library in (store, Store(tmp_path)):
        song = library.song(ID_A)
        assert (song["name"], song["ones"]) == ("Renamed", [3.0, 12.5])
        assert song["result"] == {"version": 1, "beats": [1.0], "bpm": [120.0]}
    assert store.set_one(ID_A, 3.0, False) is True
    assert Store(tmp_path).song(ID_A)["ones"] == [12.5]

    assert store.set_one(ID_B, 1.0, True) is False
    assert files_under(tmp_path) == [f"songs/{ID_A}/{name}" for name in ("result.json", "song.json", "sound.raw")]


def test_a_song_stored_before_count_1_could_be_set_has_none(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A)
    file = tmp_path / "songs" / ID_A / "song.json"
    file.write_text(json.dumps({key: value for key, value in json.loads(file.read_text()).items() if key != "ones"}))
    again = Store(tmp_path)
    assert again.song(ID_A)["ones"] == []
    assert again.set_one(ID_A, 1.0, True) is True
    assert Store(tmp_path).song(ID_A)["ones"] == [1.0]


def test_a_song_takes_only_so_many_beats_set_to_count_1(tmp_path):
    store = Store(tmp_path)
    add(store, ID_A)
    for beat in range(MAX_ONES):
        store.set_one(ID_A, float(beat), True)
    with pytest.raises(TooMany):
        store.set_one(ID_A, 1000.0, True)
    assert len(store.song(ID_A)["ones"]) == MAX_ONES
    assert files_under(tmp_path) == [f"songs/{ID_A}/song.json", f"songs/{ID_A}/sound.raw"]
