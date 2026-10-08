# Brief: a name for every bar and beat

Written on 2026-10-08, in session 12, from five answers of the owner. Branch `d5-capstone`, from `master` at `d76b864`. `BRIEF.md` and `PRODUCT.md` still hold for everything this does not speak of.

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
- **Changed while building:** the readout is on the band, between the tempo and the time, and not in the bar under the song as this brief first said. The bar has no room for it: at 1100 wide the position control fell to 510 where the owner's check asks for 600, or the click switch went to a third line by itself. On the band it stands beside the clock, as the picture in my second question had it, and the position is still said in one place.
- It is not announced at every beat to a screen reader.
- The number of a row's first bar is drawn at the left of the row, with its time.
- The bar under the pointer has a small tag drawn above its plate, `Bar 26`. The look of the tag and of the row numbers is for the owner's eye.
- `&at=` is used once, when the song's result is there. The song opens paused at the first beat of the place. The address does not follow the playing position. It keeps its `at` until another song is opened.
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
- The song is its id, the start of its id, or a part of its name, in any case and with or without accents. None or more than one: the command lists the songs that match, or all of them, and ends with status 2.
- A song with no result yet, and a place that is not in the song: one sentence, status 1.
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

**The place, in `web/song.test.js`** (`node --test web/`)

- [ ] **C1** Every beat of a song has one place, bar and beat from 1, and the place leads back to the same beat.
- [ ] **C2** In a short bar the beats are 1 to n. `24.3` is refused when bar 24 has two beats.
- [ ] **C3** `24.3`, `24` and `62.4s` are read. `0`, `24.0`, `24.3.1`, `-1`, `1e3`, `62.4sec` and words are not. `62.4` without an `s` is bar 62, beat 4.
- [ ] **C4** `?song=<id>&at=24.3` is written from an id and a place, and read back. Without a place it is `?song=<id>`, as today.

**The page, in `e2e/page_test.py`**

- [ ] **C5** The readout says the bar and beat at the playing position: after a press on a plate, after a step of one beat, and before the first beat.
- [ ] **C6** While the song plays, the readout follows the beat that is lit. *Needs sound: run outside the sandbox.*
- [ ] **C7** After "Count 1 here", the readout and the row numbers are those of the new bars.
- [ ] **C8** Every row of the map has the number of its first bar, and something is drawn where the page says it is. Which numeral it is stays for the eye.
- [ ] **C9** The bar under the pointer has its tag, and the tag goes when the pointer leaves.
- [ ] **C10** A link with `at=3.2` opens the song paused on that beat, and one with `at=4.75s` at the beat nearest to that time.
- [ ] **C11** A link with `at=240` opens the song at its start and says there is no bar 240. One with `at=x` opens it as a link without `at` does.
- [ ] **C12** "Copy place" hands the clipboard the line above, for the place in the readout. The test puts its own clipboard in the page and reads what it was given.
- [ ] **C13** The readout is not a live region.
- [ ] **C14** Every test of the page that passed before passes: the plates, the large view, a link without `at`. **Two of their assertions had to change**, both in the test of the plates: the left of a row holds two writings, its time and its number, where it held one, and the text of the player has "Bar 1.1" in it.

**The commands, in `bachata/places_test.py`**

- [ ] **C15** `where <song> 24.3` prints the four lines above for a stored song, to the letter.
- [ ] **C16** `where <song> 62.4s` prints the place of the nearest beat.
- [ ] **C17** `bars <song>` prints one line for every bar, and marks a short bar and a count 1 set by hand.
- [ ] **C18** A count 1 set through the store moves the numbers the commands print.
- [ ] **C19** The twin: on the same beats, count and count 1s, Python and `web/song.js` make the same bars and read the same places. *Skipped where node is not installed.*
- [ ] **C20** A song is found by its id, by the start of it, and by a part of its name without its accents. None and several end with status 2 and print no place.
- [ ] **C21** A song with no result, and a place that is not in the song, end with status 1 and one sentence.
- [ ] **C22** The commands load no torch, write nothing in the library, and read the folder `BACHATA_DATA` names.
- [ ] **C23** `python -m bachata` alone still serves on 127.0.0.1: the test of `bachata/server_test.py` that starts the program, unchanged.

**The whole run**

- [ ] **C24** `node --test web/` and `uv run pytest` pass, the second once outside the sandbox, with what was skipped and why.

## The records

*Proposed:* `LOG.md` gets its entry for the session and `NEXT.md` is rewritten, on the branch, in a commit of their own after the code, so a reviewer can read the code's diff alone. `ACCEPTANCE.md` is not changed: this list is the part's. A section "For the reviewer" is added to this file at the end, with how to get the diff. It is the one file a reviewer needs.
