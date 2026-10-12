# The test run of the rejected build (2026-10-07)

An excerpt. The session that built the first attempt at the bars view wrote notes in its work folder (`wt/d4-bars`, on the branch `d4-bars`) on 2026-10-07. Git did not see that file, and the work folder was removed on 2026-10-08. A copy of the notes was kept outside this repository. Below are the list of commits and two rows of its table of runs, as written there. The rest of the notes is not copied.

The commits, on `d4-bars`, made from `master` at `036c71b`:

- `289c033` The song shows one mark for each bar
- `6b50c32` Repair two checks of the song that could not fail
- `5b1ed39` The label of the song says where a press reaches a beat

They are kept in this repository by the tag `d4-bars`.

| Command | Result | Time |
| --- | --- | --- |
| The whole run, outside the sandbox: `TMPDIR=/tmp/claude-1000/e2e-b BACHATA_TEST_PORT=8084 .venv/bin/python -m pytest -rs`, from inside `wt/d4-bars` | 218 passed, 1 failed, none skipped. Every test of the page ran in Chrome and in Firefox, with sound. The one that failed is `bachata/entry_test.py`: "its sound is not in the library" for each of the owner's 13 songs. It reads `data/`, and this working copy has none: `data` is not among the links the task made | 448.79 s |
| `bachata/entry_test.py` alone, inside the sandbox, from inside `wt/d4-bars`, with `BACHATA_DATA` naming the library of the main folder. It only reads | 1 passed: the count enters on 1 on 5 of 5 songs, and 0 other songs got worse. The failure above is the missing library and nothing else | 90 s |

Times, from my session log (UTC): the session handed the build back at 11:34:02, my first words on it are of 11:39:01, my description of what was wrong is of 11:41:58, and I rejected it at 11:53:20. My words are quoted in `LOG.md`, in the entry of session 11.
