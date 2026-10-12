# The three-prompt test of the skill `break-on-purpose`

Run on 2026-10-06, after the skill was committed (`9e14c5d`). Three fresh Claude Code sessions (Opus 5.5, effort xhigh), one prompt each, with no other message. The second Claude session started them at my request and saved each answer as it was given. The answers below are those saved files, complete.

What the answers cannot show by themselves: whether the skill was loaded. That was read from each session's own record, which is not in this repository: the skill was loaded in the first and in the third session, and not in the second.

Read this before the first answer: that session worked in a private copy of the project, not in this repository. The tests it changed and the table it wrote in `LOG.md`, `ACCEPTANCE.md` and `NEXT.md` stayed in that copy and were never brought here. So its "session 9" is not the session 9 of this repository's `LOG.md`.

## 1. Should activate

Prompt: "break the code on purpose for the per-song URL and tell me which tests catch each break"

```
start 2026-10-06T09:26:04Z
I broke the per-song URL in 32 ways, one at a time. Every claim of the acceptance item is caught by the test that claims it; the gaps are all in behaviour no claim speaks of. The program is as committed, nothing is committed, and the changes to the tests are uncommitted in the working tree.

- **The claims:** 14 breaks, 14 caught where they should be.
- **What no claim speaks of:** 18 breaks. 7 were caught, 1 was caught only by a different test, and 10 by nothing.
- **Repairs:** 7 of those 11 now have a check (four tests changed, one added), and each was seen to fail on its own break. The other 4 are yours to decide and have no test.

**One thing I need from you:** the whole suite in Chrome and with sound has not run since `e2e/page_test.py` changed. The command was not allowed in this session, so the new and changed browser tests have run in Firefox only. The command, with a free port:

`TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8083 .venv/bin/python -m pytest`

You named no command, so I took the three from the skill's table: `node --test web/`, `pytest bachata/server_test.py` and `pytest e2e -k "firefox and address"`.

## Which test catches each break

- **Unit** is "a song has an address of its own" in `web/song.test.js`.
- **Address** is `test_every_song_has_an_address_that_opens_it` in `e2e/page_test.py`.
- **Server** is `test_the_address_of_a_song_is_the_page` in `bachata/server_test.py`.

| Break | Caught by |
| --- | --- |
| **The claims** | |
| The address is `?id=` and the id | Unit and Address |
| A second song keeps the first song's address | Address |
| An open song leaves the plain address | Address |
| A closed song keeps its address | Address |
| The page does not read its address on load | Address |
| An address opens the first song of the list | Address, in the other browser |
| A page loaded with an address sends an upload | Address |
| A song the library lacks: nothing is said | Address |
| A song the library lacks: the address stays | Address |
| `?song=../../etc/passwd`: nothing is said | Address |
| `?song=../../etc/passwd`: the address stays | Address |
| The server refuses a `?song=` that is not an id | Server |
| The page reads the song from `?id=` | Unit and Address |
| Any text is taken as an id | Unit (Address passes: the page looks the id up in the list, so it says the same) |
| **No claim speaks of these** | |
| Capitals, 31 or 33 characters, either end of the id left open (5 breaks) | Unit |
| The song is read only as the first parameter | Unit |
| The page forgets that the address named the song | Address |
| The song is read only when nothing follows it | Nothing. Unit now has `?song=…&from=mail` |
| A song that cannot be opened takes the address while another stays open | Nothing. `test_a_message_appears_beside_its_cause…` now reads the address |
| A named song still being analysed is given up | Nothing. New test: `test_an_address_that_names_a_song_still_being_analysed_opens_it_when_it_is_ready` |
| A plain address says "This song is not in the library." | Nothing. Address now checks it |
| A page loaded with an address sends a renaming | Nothing: Address counted uploads only. It now looks at everything that is not a plain read |
| The server redirects `/?song=…` to `/` | Address only. Server passed, because its client followed the redirect by itself; it no longer does, in any server test |
| The server writes a stored song's name into the page | Nothing: Server asked on an empty library. It now asks with a song the library has |
| Opening a song adds to the browser's history | Nothing, no test |
| Of two `song` parameters the last is taken | Nothing, no test |
| A named song whose analysis failed says nothing | Nothing, no test |
| An upload gone before it opens is treated as named by the address | Nothing, no test |

The two "sends" breaks added a request; no code of the page sends anything on that path.

## Yours to decide

These four have no test because what is right is written nowhere:

- **Back:** opening a song rewrites the address in place today. With it added to the history instead, every test passes.
- **Two songs in one address:** the page opens the first.
- **An address for a song whose analysis failed:** the page says "The analysis of … failed." beside the Add control and the address becomes plain.
- **An upload another browser deletes before it opens:** the page says "The song was deleted." It is not really about the address.

The new test for a song still being analysed rests on a line under "Open" in `NEXT.md`, not on an acceptance item. It only asserts that the song opens once ready and the address then names it. Say so if you would rather not fix that behaviour yet.

Besides Chrome, the 6 tests that need sound were skipped in every run. The full table with the failure messages is in `LOG.md` under session 9; `ACCEPTANCE.md` has one new paragraph and `NEXT.md` four new rules and the open points.

exit 0
end 2026-10-06T10:08:18Z
```

## 2. Similar, should not activate

Prompt: "run the tests"

```
start 2026-10-06T09:21:19Z
The tests pass as far as they could run here: 155 passed, 31 skipped, none failed, in 2 minutes 26 seconds. The 31 skips are all browser flows in `e2e/page_test.py`, so the page itself was only partly tested.

- **25 skipped because Chrome could not start** in the sandbox.
- **6 skipped because Firefox has no sound output** in the sandbox, so nothing can play.

I first asked to run the full suite outside the sandbox, which is what those flows need, and that request was declined. To cover them, run this yourself, or allow it if you ask me again:

```
mkdir -p /tmp/claude-1000/e2e && TMPDIR=/tmp/claude-1000/e2e .venv/bin/python -m pytest -rs
```

I left `BACHATA_TEST_PORT` unset so the tests pick a free port and stay clear of anything you have running on 8081 or 8082.

The run collected 186 tests, while `NEXT.md` still says 182.

exit 0
end 2026-10-06T09:25:50Z
```

## 3. Missing input

Prompt: "do a mutation check"

```
start 2026-10-06T09:21:19Z
Which part should I break? The skill asks this before anything else, and nothing has been changed or run.

The candidates, from `LOG.md` and `ACCEPTANCE.md`:

| Part | Command I would take | Broken before |
| --- | --- | --- |
| The page's logic, `web/song.js` | `node --test web/` | Session 8's trial, on a copy only: 5 of 51 breaks went uncaught, and the three changed tests were never brought into the repository |
| The redesigned page of session 5: the loop, renaming, the band | `pytest e2e -k "firefox and …"` | No break table in that session's entry |
| Slice 1: the server, the store, the queue, the analysis | `pytest bachata/<name>_test.py` | Eight breaks in session 3 |
| Slice 2 as a whole, section 2 of `ACCEPTANCE.md` | the three above, per file | 25 breaks in session 6, four more in session 7 |
| "The whole application": the headers, 127.0.0.1, the host check | `pytest bachata/server_test.py` | Three breaks in session 1 |

I recommend `web/song.js`. It has known gaps at the current commit that were only ever repaired in a throwaway copy, and each run takes under a second.

The session 5 page is the least tested by breaking, but it is slower at 10 to 15 seconds a test. Inside the sandbox its tests that need sound are skipped, so some breaks there would need a run outside it.

Name one of these, a set of files, or a range of commits, and give your own command if you want a different one.

exit 0
end 2026-10-06T09:22:03Z
```
