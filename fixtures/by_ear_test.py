from fixtures.by_ear import count_at, first_one, kept, reading

# Made-up numbers, not a real song: a beat every half second from 1.0 s. The count starts
# on the third beat.
BEFORE = {"beats": [1.0 + n / 2 for n in range(20)], "count": [(n - 2) % 8 + 1 for n in range(20)]}


def test_the_count_at_a_mark_is_the_count_of_the_beat_there():
    assert count_at(BEFORE["beats"], BEFORE["count"], 2.0) == 1
    assert count_at(BEFORE["beats"], BEFORE["count"], 2.05) == 1
    assert count_at(BEFORE["beats"], BEFORE["count"], 2.5) == 2


def test_a_mark_with_no_beat_near_it_has_no_count():
    assert count_at(BEFORE["beats"], BEFORE["count"], 2.25) is None
    assert count_at([], [], 2.0) is None


def test_the_count_of_a_song_started_at_its_first_one():
    assert first_one(BEFORE) == 2.0


def test_a_count_that_did_not_change_is_kept_on_every_beat():
    assert kept(BEFORE, BEFORE["beats"], BEFORE["count"], 2.0) == (18, 18, None)


def test_beats_found_a_little_elsewhere_keep_their_count():
    moved = [time + 0.04 for time in BEFORE["beats"]]
    assert kept(BEFORE, moved, BEFORE["count"], 2.0) == (18, 18, None)


def test_a_count_four_off_from_some_beat_on_is_lost_from_there():
    shifted = BEFORE["count"][:10] + [(count + 3) % 8 + 1 for count in BEFORE["count"][10:]]
    assert kept(BEFORE, BEFORE["beats"], shifted, 2.0) == (8, 18, 6.0)


def test_a_beat_that_is_no_longer_found_has_lost_its_count():
    beats, counts = BEFORE["beats"][:5] + BEFORE["beats"][6:], BEFORE["count"][:5] + BEFORE["count"][6:]
    assert kept(BEFORE, beats, counts, 2.0) == (17, 18, 3.5)


def test_only_the_stretch_asked_for_is_judged():
    shifted = BEFORE["count"][:10] + [(count + 3) % 8 + 1 for count in BEFORE["count"][10:]]
    # The change is at 6.0 s: a stretch that ends there has kept everything.
    assert kept(BEFORE, BEFORE["beats"], shifted, 2.0, 6.0) == (8, 8, None)
    assert kept(BEFORE, BEFORE["beats"], shifted, 2.0, 6.5) == (8, 9, 6.0)
    # What comes before the start is not judged either.
    changed_start = [5, 6] + BEFORE["count"][2:]
    assert kept(BEFORE, BEFORE["beats"], changed_start, 2.0) == (18, 18, None)
    assert kept(BEFORE, BEFORE["beats"], changed_start, 1.0) == (18, 20, 1.0)


def test_a_file_opened_under_a_watched_folder_is_listed(tmp_path):
    (tmp_path / "watched").mkdir()
    (tmp_path / "watched" / "marks.json").write_text("{}")
    (tmp_path / "elsewhere.json").write_text("{}")
    with reading(tmp_path / "watched") as found:
        (tmp_path / "elsewhere.json").read_text()
        assert found == []
        (tmp_path / "watched" / "marks.json").read_text()
    assert found == [str((tmp_path / "watched" / "marks.json").resolve())]
    # Outside the block nothing more is listed.
    (tmp_path / "watched" / "marks.json").read_text()
    assert len(found) == 1
