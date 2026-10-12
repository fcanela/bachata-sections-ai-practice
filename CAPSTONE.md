# Brief: a name for every bar and beat

Written on 2026-10-08, in session 12, from five answers of the owner. Branch `d5-capstone`, from `master` at `442abf2`. `BRIEF.md` and `PRODUCT.md` still hold for everything this does not speak of.

Items marked *proposed* are mine and not the owner's. He confirms or changes them.

## Goal

The owner and an LLM can name a place in a song, and each can find the place the other named. Today neither can say "the third beat of that bar" in a way the other can follow, so a detection cannot be pointed at and checked.

## Context

- A song has beats, a count from 1 to 8 on each, and bars: `barsOf()` in `web/song.js` starts one at every count 1 and every count 5. The lower view draws a plate for each bar.
- The count is the analysis's, changed by the count 1s the owner set by hand. The server keeps those as times, in `song.json`. Only the page works out the count with them, in `countsWith()`.
- The address of a song is `?song=<id>`.
- `uv run python -m bachata` starts the server and does nothing else.

## What the owner decided

1. **A place is a bar and a beat**, written `24.3`: bar 24, beat 3. `24` alone is the bar, and its first beat. His words: "while ocho is nice, I think bar and beat will be most robust".
2. **The page shows it in three places**: a readout of the place at the playing position, the number of its first bar beside each row of the map, and the number of the bar under the pointer. The plates keep their 1 and 5.
3. **The address carries a place**: `?song=<id>&at=24.3` opens the song there, and a button copies it. No field to type a bar into.
4. **An LLM gets two commands**: `where`, for one place, and `bars`, for the whole song.
5. **The numbers count the bars as the page shows them**, with the count 1s set by hand. A number can mean another place after a count 1 is set or the song is analysed again, so the seconds are always given beside it.

## The rules that follow

All *proposed*, except where an answer above already says it.

**The place**

- Bars are numbered from 1 in the order of `barsOf()`. A beat is its place in its bar, from 1. A short bar has beats 1 to n, whatever their count.
- A time is written with an `s`: `62.4s`. So `24.3` is never a time. The command and the address take both forms.
- A time names the beat nearest to it, as a count 1 set by hand does.

**The page**

- The readout says `Bar 24.3`. Before the first beat it says `Bar 1.1`. With no song open it is empty.
- **Changed while building, and again after the review:** the readout is in the top bar, just before "Copy place", and not in the bar under the song as this brief first said. The bar has no room for it: at 1100 wide the position control fell to 510 where the owner's check asks for 600, or the click switch went to a third line by itself. It was first put on the band, between the tempo and the time, where it took 23% of the width of the large view at 1100. The owner chose the top bar on 2026-10-08 as "the least wrong": **its place is provisional and waits for a design pass.**
- It is not announced at every beat to a screen reader.
- The number of a row's first bar is drawn at the left of the row, with its time.
- The bar under the pointer has a small tag drawn above its plate, `Bar 26`. The look of the tag and of the row numbers is for the owner's eye.
- `&at=` is used once, when the song's result is there. The song opens paused at the first beat of the place. The address does not follow the playing position. It keeps its `at` until another song is opened: when the same song is opened again it starts at its start, and the address still has the place.
- An `at` that names no place in the song: the song opens at its start and the page says "There is no bar 240 in this song." An `at` that is not a place at all is ignored.
- The button is "Copy place". **Changed while building:** it is in the top bar, after "Rename", for the same lack of room. It copies one line: `Sus Huellas, bar 24.3 (62.41 s) http://127.0.0.1:8080/?song=<id>&at=24.3`. The place is the one in the readout.

**The commands**

```
$ uv run python -m bachata where huellas 24.3
Sus Huellas  3f2a9c…  analysis 5
bar 24, beat 3   62.41 s   count 7   128 BPM
bar 24: 61.47 61.94 62.41 62.88
link: ?song=3f2a9c…&at=24.3

$ uv run python -m bachata where huellas 62.4s      the same four lines

$ uv run python -m bachata bars huellas
Sus Huellas  3f2a9c…  analysis 5  412 beats  104 bars
  1    0.52 s  count 1
  2    2.40 s  count 5
 13   24.10 s  count 1  2 beats  by hand
```

- The id is printed whole. Seconds have two decimals.
- The song is its id, the start of its id, or a part of its name, in any case and with or without accents. An id is found in capitals too, and a whole id is that song whatever the names of the others have in them. None or more than one: the command lists the songs that match, or all of them, and ends with status 2.
- A song with no result yet, a song whose analysis failed, and a place that is not in the song: one sentence, status 1.
- They read the library on disk, in `BACHATA_DATA` as the server does. They need no running server, change nothing in the library, and load neither torch nor the checkpoints.

## Constraints

- `uv run python -m bachata` with no argument starts the server exactly as today.
- No new dependency. No new route on the server. Nothing new is stored.
- The plates and the large view are as the owner accepted them. Only the left edge of the rows and the tag are added to the map.
- The bar numbers of the command are made by a Python twin of `countsWith()`, `barsOf()` and `nearestBeat()`, in a file of its own beside `store.py`. A test runs both on the same songs and compares them.
- The interface stays in English, in short plain sentences.
- Work on `d5-capstone`. Nothing is merged into `master`.

## Not in this

A field to type a bar into. Numbers for ochos or sections. A range of bars as one place. Reaching the canvases with the keyboard.

## Acceptance checks

Each is one claim and names the check behind it. For breaking on purpose, the claims of this part are this list and the two sections above it.

Ticked on 2026-10-08 from the whole run outside the sandbox, on `492e41f`: 294 passed, none skipped, in Chrome and in Firefox with sound. The checks were seen to fail: 79 breaks, 78 caught, in `LOG.md`, session 12. A tick says the check passed, not that the owner accepted what it checks.

**The place, in `web/song.test.js`** (`node --test web/`)

- [x] **C1** Every beat of a song has one place, bar and beat from 1, and the place leads back to the same beat.
- [x] **C2** In a short bar the beats are 1 to n. `24.3` is refused when bar 24 has two beats.
- [x] **C3** `24.3`, `24` and `62.4s` are read. `0`, `24.0`, `24.3.1`, `-1`, `1e3`, `62.4sec` and words are not. `62.4` without an `s` is bar 62, beat 4.
- [x] **C4** `?song=<id>&at=24.3` is written from an id and a place, and read back. Without a place it is `?song=<id>`, as today.

**The page, in `e2e/page_test.py`**

- [x] **C5** The readout says the bar and beat at the playing position: after a press on a plate, after a step of one beat, and before the first beat.
- [x] **C6** While the song plays, the readout follows the beat that is lit. *Needs sound: run outside the sandbox.*
- [x] **C7** After "Count 1 here", the readout and the row numbers are those of the new bars.
- [x] **C8** Every row of the map has the number of its first bar, and something is drawn where the page says it is. Which numeral it is stays for the eye.
- [x] **C9** The bar under the pointer has its tag, and the tag goes when the pointer leaves.
- [x] **C10** A link with `at=3.2` opens the song paused on that beat, and one with `at=4.75s` at the beat nearest to that time.
- [x] **C11** A link with `at=240` opens the song at its start and says there is no bar 240. One with `at=x` opens it as a link without `at` does.
- [x] **C12** "Copy place" hands the clipboard the line above, for the place in the readout. The test puts its own clipboard in the page and reads what it was given.
- [x] **C13** The readout is not a live region.
- [x] **C14** Every test of the page that passed before passes: the plates, the large view, a link without `at`. **One of their assertions had to change**, in the test of the plates: the left of a row holds two writings, its time and its number, where it held one. A second, on the text of the player, was changed while the readout was on the band and is as it was again.

**The commands, in `bachata/places_test.py`**

- [x] **C15** `where <song> 24.3` prints the four lines above for a stored song, to the letter.
- [x] **C16** `where <song> 62.4s` prints the place of the nearest beat.
- [x] **C17** `bars <song>` prints one line for every bar, and marks a short bar and a count 1 set by hand.
- [x] **C18** A count 1 set through the store moves the numbers the commands print.
- [x] **C19** The twin: on the same beats, count and count 1s, Python and `web/song.js` make the same bars and read the same places. *Skipped where node is not installed.*
- [x] **C20** A song is found by its id, by the start of it, and by a part of its name without its accents. None and several end with status 2 and print no place.
- [x] **C21** A song with no result, and a place that is not in the song, end with status 1 and one sentence.
- [x] **C22** The commands load no torch, write nothing in the library, and read the folder `BACHATA_DATA` names.
- [x] **C23** `python -m bachata` alone still serves on 127.0.0.1: the test of `bachata/server_test.py` that starts the program, unchanged.

**The whole run**

- [x] **C24** `node --test web/` and `uv run pytest` pass, the second once outside the sandbox, with what was skipped and why.

## The records

`LOG.md` has the entry of the session, 12, and `NEXT.md` says where things stand, in a commit of their own after the code. `ACCEPTANCE.md` is not changed: this list is the part's.

## For the reviewer

**The task**, in the owner's words: "When I use the app I cannot refer to a specific beat or bar. That would have been very useful each time an LLM or I want to point at a specific place in a song and check if it was detected correctly or not."

**What to judge it against:** "What the owner decided", "The rules that follow", "Constraints" and "Acceptance checks" above. The rules marked *proposed* and the two marked **Changed while building** are the session's and not the owner's: say where you would have decided otherwise.

**The diff.** The branch is `d5-capstone`, and `master` is where it started, at `442abf2`. Nothing is merged.

```
git diff master...d5-capstone --stat
git diff master...d5-capstone -- web bachata e2e      # the code and its tests
git diff master...d5-capstone -- LOG.md NEXT.md       # the records
git log --oneline master..d5-capstone                  # one commit for each step, in the order they were built
```

| Commit | What |
| --- | --- |
| `f1007a2` | This brief, as the owner said "go" to it |
| `c6137c6` | The place in `web/song.js`, its twin and the two commands in `bachata/places.py`, `bachata/__main__.py` |
| `fed68dc` | The address with `at`, in `web/app.js` |
| `46ded84` | The readout and the row numbers: `web/app.js`, `web/draw.js`, `web/index.html`, `web/style.css` |
| `b14c60e` | The tag and "Copy place" |
| `492e41f` | Tests made stronger after the breaks, and this brief brought up to what was built |
| the last one | The records, and this section |

**To run the checks.**

```
node --test web/                                         # under 1 s
.venv/bin/python -m pytest bachata/places_test.py        # under 1 s
.venv/bin/python -m pytest e2e -k "firefox and (address_with_a_place or far_down or readout or every_row or tag_above or copy_place)"
.venv/bin/python -m pytest                               # everything; Chrome and sound need a machine that has them
```

**To try it by hand.** Start the program on a library of its own, never on `data/` of this folder, which it would analyse again: `BACHATA_DATA=/some/scratch/folder PORT=8090 uv run python -m bachata`. The commands only read: `uv run python -m bachata bars <part of a name>`.

**Where a second pair of eyes is worth most.**

- `bachata/places.py` against `web/song.js`: the same rule written twice. The test that compares them makes its own songs: is there a kind of song it does not make?
- `open()` and `goToLinked()` in `web/app.js`: when the place of the address is used, kept in the address, and dropped.
- The assertion of an existing test that was changed, in `test_every_bar_has_one_plate_with_its_count_in_rows_of_eight_ochos_in_light_and_in_dark`.
- `run()` at the end of `bachata/__main__.py`: with no argument it must be the server exactly as before.

**What was run.** `node --test web/`: 41 passed. The whole run outside the sandbox, `.venv/bin/python -m pytest -rs`: 294 passed, none skipped, 932 s. 79 breaks of the code, one at a time: 70 caught as the tests stood, 78 after the tests were made stronger, in `LOG.md`.

**What was not checked.**

- That the system's clipboard receives the line: the test puts a clipboard of its own in the page.
- The page in a browser driven by a person. The session looked at four pictures taken by Playwright's Firefox.
- The commands on a library while the server is writing to it.
- One break is caught by nothing: a tag may pass the right edge of the song by up to 3 pixels, over a plate of one beat that ends its row.
- The tests of the twin are skipped where node is not installed, and the tests of the page where ffmpeg or a browser is missing.

## After the review

A session of another tool reviewed `235adb2` on 2026-10-08 and asked for four changes. Each was reproduced before it was believed, and all four hold.

| Finding | Reproduced | What was done |
| --- | --- | --- |
| 1. An id in capitals is not found, and a whole id in capitals picks another song whose name has it | Yes: `bars AB01` did not find the song whose id starts `ab01`, and `bars AB01…AB01` answered the song named "A copy of AB01…AB01" | Fixed in `found()`. `test_a_song_is_found_by_its_id_the_start_of_it_or_a_part_of_its_name` failed before the fix |
| 2. A song whose analysis failed stops the commands with a traceback | Yes: `KeyError: 'beats'` from `where` and from `bars`, on a result `{"version": 5, "error": "RuntimeError"}` as the queue writes it | Fixed in `counted()`: "The analysis of <name> failed.", status 1. `test_what_cannot_be_answered_is_said_in_one_sentence` failed before the fix |
| 3. The readout on the band takes room from the large view | Yes: at 1100 by 800 in Firefox the large view is 576.5 wide on `master` and 444.5 on the branch, 23% less | Two places that take nothing from the large view were shown to the owner with pictures: the top bar before "Copy place", and the lower right corner of the band. **He chose the top bar**, as provisional: "I do not think either option is good design; A is the least wrong and I will redo it later with the design plugin." The test of the readout now says where it is and that the band holds only the count, the tempo and the time |
| 4. The address loses its place when the same song is opened again | Yes: the test asserted it | Fixed in `open()`: the place stays in the address until another song opens, and the position goes there once. The assertion that was wrong is corrected, and failed before the fix |

Not asked for and not done: the reviewer would let a time have more than three decimals, `4.7501s`.
