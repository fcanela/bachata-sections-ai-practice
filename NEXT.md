# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-08, session 12)

**A name for every bar and beat is built on the branch `d5-capstone`, and is not merged.** It is the capstone of the owner's course. A session of another tool reviews it first, then the owner looks at it. `CAPSTONE.md` on that branch is its brief, its acceptance list and the reviewer's file. `LOG.md`, session 12, has the figures.

- **What it is.** A place is a bar and a beat from 1, written `24.3`, counted on the bars the page shows, with the count 1s set by hand. A time is written `62.4s`.
  - **The page**: the place at the playing position on the band, between the tempo and the time; the number of its first bar beside every row of the song; a tag with its number over the bar under the pointer; `?song=<id>&at=24.3` opens the song paused there; "Copy place", in the top bar, copies the song, the place, its seconds and that address as one line.
  - **Two commands**, which read the library and need no server: `uv run python -m bachata where <song> <place>` and `uv run python -m bachata bars <song>`. `python -m bachata` alone is the server, as it was.
- **Every check a program can run passes on the branch**: 294 tests, none skipped, outside the sandbox, in Chrome and in Firefox with sound.
- **Its checks were seen to fail.** 79 breaks: 70 caught as the tests stood, 78 after four tests were made stronger and two added. One is left: a tag could pass the right edge of the song by 3 pixels.
- **For the owner to look at**, none of it confirmed: where the readout and "Copy place" ended up, which is not where the brief had them; the look of the row numbers and of the tag; the wordings. `CAPSTONE.md` lists them.
- **Not checked by anything:** that the system's clipboard receives the line (the test puts its own clipboard in the page), and the page in a browser the owner drives.
- **The library in `data/` of this folder was analysed again by mistake**, 17 of its 18 songs, from version 2 to version 5. See "Rules that are easy to break".
- **If it is merged:** `ACCEPTANCE.md` has nothing of it yet. Its list is in `CAPSTONE.md`.

Before that, in session 11:

The lower view of the page is in plates, one for each bar, and it is on `master` since 2026-10-08. The owner accepted it. A critique of the page followed the same day, and three changes it led to are merged with it. Every check a program can run passed on the branch that was merged: 266 tests, none skipped. No test was run on `master` after the merge. What is open of this work is two commands of the critique that were not run, and what the owner has not yet seen. `LOG.md`, session 11, has the figures.

- **The plates**, merged from `bars-xhigh` at `cbd2241`, with a merge commit, `a1983b2`.
  - **The first attempt was rejected.** It is on the branch `d4-bars`. The owner: "It was like it just removed the extra beats, instead of doing a design that makes sense for showing the bars in a way that makes sense on their own".
  - **The owner chose the plates from three pictures**, on 2026-10-07. `SPEC.md` was written from that choice. It and the picture, `chosen.png`, are in `wt/bars-xhigh` and `wt/bars-high`, not in git.
  - **The same spec was built twice**, at high on the branch `bars-high` and at xhigh on `bars-xhigh`, by sessions that did not read each other's folder. The owner could not tell the two pages apart. Both were accepted, and he preferred the xhigh one, which is the one merged.
  - **What it is.** A bar is one thing on the song: a plate with the count of its first beat. The first bar of an ocho has a solid plate and the second a quiet grey one. A row holds eight ochos from about 1200 wide, four under that. The bar that holds the beat that is sounding is lit whole. A count 1 set by hand has a lid over its plate. A drag marks whole bars. The large view above is as it was.
  - **Its checks were seen to fail.** 116 breaks, one at a time: 98 caught as the tests stood, and after nine tests were made stronger and one added, 115. Which numeral is on a plate stays for the eye.
- **The critique of the page**, by the design plugin, on 2026-10-08: **23 of 40, "Acceptable"**, with five issues. The owner asked for all five.
  - **Done: the Space key.** After a press with the pointer on a control of the bar under the song, Space plays and pauses. Before, it pressed the control again, and after "Count 1 here" it took the count back on the server. A control the keyboard went to by itself keeps the key.
  - **Done: the lit bar is yellow on both grounds**, with black type, and in light with a black edge 3 wide inside it. **This departs from `SPEC.md` and from `chosen.png`, by the owner's choice** of 2026-10-08, "Yellow on both grounds": there the lit bar is a black block with a yellow count in light. `bars-high` still has it black.
  - **Done: the bar under the song.** The position control has 20rem at least and is drawn by the page, with a square handle and the marked range on it. Under 1600 wide the bar is two lines on purpose. "Clear" shows only while something is marked. The bar says the length of the song, and the position is on the band alone. The click switch stays in the bar: the owner's answers.
  - **Done in part: the wait for an analysis.** The row says for how long an analysis has run, when this page saw it start, and what to do when it failed. A song that becomes ready while another sounds does not open: the page says it is ready. A reason for a failure and "Try again" need the server, and are not built.
  - **Open: the two canvases cannot be reached with the keyboard or read by a screen reader**, and the count is said at every beat. It is the third of the issues the critique calls major.
  - **Not run: two commands of the critique, `audit` and `polish`.** See "Left open by the critique" below.
- **For the owner to look at**, none of it confirmed: the black edge of the lit bar in light and its width; the look of the drawn position control; that the bar is two lines from 1600 down; the nine points `SPEC.md` lists under "Not in the picture"; and the numeral on every plate. Pictures are in `wt/bars-xhigh/shots/`.
- **The work folders and the branches are all kept**, as the owner asked: see "Housekeeping".

Before that, in session 10:

Slice 2 is built, in the shape the owner gave it in session 6, and the owner has used it. Since session 9 the analysis also says which of two bars starts an ocho, and since session 10 the fills decide where what comes in is not clear: the owner accepted that on 2026-10-07 and it is on `master`. Every check a program can run passes. What is open is the owner's: to listen to the new count, the checks of slice 1, one by-ear item of slice 2, and the proposals listed below.

- **The fills**, on `master` since 2026-10-07: the owner had the branch `d4-patch` merged with a fast-forward, at `e5dde4b`. Where what comes in during the first minute is under 3 to 1, the song is split into its parts by Hybrid Demucs, and the drums and the bass say which bar starts an ocho: the first bar marks the beats, the second has attacks on the sixteenths next to them. It is version 5: the program analyses every stored song again when it next starts, about 3 minutes for the 18 songs of the library where it was a little over one. `LOG.md`, session 10, has the figures.
  - **The owner's verdict, on 2026-10-07:** "Overall, I think the first beat detection is better, I have not tested everything but I did the tests review of the algo and it was better. I will accept it". He kept the six-song check at "at least 5 of 6" and the limits as the patch has them.
  - **What it rests on.** The six songs he heard on 7 October: `bachata/entry_pairs_test.py` reads 6 of 6, where version 4 has 0 of 6. They are the songs the rule was built on. And the fills alone on the 17 songs whose count at the start is known: on the right side on all 17, and sure on 16.
  - **No song of the reference changed.** The 18 songs of the library have the beats and the count they had, and the entry check still reads 5 of 5. The fills are asked on 3 of them, Sus Huellas, La Bachata and Héroe Favorito, and say what the vote said.
  - **What it costs.** 30 to 50 seconds for a song whose fills are asked, where it took 3 to 5, and 3 GB of memory in place of 0.8. A song of 15 minutes: 3 minutes for the split alone, and 5.4 GB.
  - **Thin places.** Feeling Something is under 3 to 1 by little, 2.85: with the limit at 2.8 it would stay wrong. Nómada and Decídete are sure by 4.15 and 4.23. And sure by 2 is reached by 24% of made-up songs with no fills at all, because each bar is compared with the two around it.
  - **Four faults were repaired on the way.** A song that ends within a second after a piece of 30 s failed in the split or was too loud at its end. The program started without the new checkpoint. The cost was written as "some 30 seconds a song". And the watch on what the analysis opens could not see a file behind a link.
  - **Still for the owner:** the licence of the Hybrid Demucs checkpoint, which is not logged; whether the whole song has to be split when 60 seconds of it are listened to; and the argument `fills_of` of `analyse()`, which only a test uses.
  - **The work folder is still there**: `wt/d4-patch`, on the branch `d4-patch`. The owner asked for both to be kept. The notes the records were written from are in it, `NOTES-for-records.md`, which git does not see.

- **The entry**, on `master` since the owner had the branch `goal-entry` merged and deleted, the same day. The owner listened to 13 songs in full and set a target: count 1 on his mark on at least 4 of 5 songs whose count was four off from the start, and no other song worse. `bachata/entry_test.py` checks it and passes: 5 of 5 since the third part of the session, none worse. `LOG.md`, session 9, has the figures.
  - **What the analysis does now.** It looks at where the sound rises in the first minute: the 4 beats from a beat against the 4 before it, in 16 bands. A rise of 5 dB or more is something coming in, and it starts the nearest bar. The count moves by a bar, for the whole song, when more comes in on the bars between its ochos than on them. A rise out of silence cannot move it. Where nothing comes in, the bass decides: see below. It was version 4. *Since session 10 it is version 5, and where the two sides are under 3 to 1 the fills decide: see "The fills" above.*
  - **The Me Emborrachare mix is right since the third part of the session**: 1 at 2.28 s, and the check reads 5 of 5. Nothing comes in during its first minute, so the bass decides. Against the labels it is 308 of 396, where it was 88: the 88 left are the first four beats and the part after its half phrase at 151 s.
    - **The bass rule.** In most songs the bass, 40 to 123 Hz, is louder in the first bar of an ocho than in the second. Where no rise of the first minute counts, the count moves by a bar when the bass of the first 90 s says so by 2 or more: the mean difference between the two kinds of bar over its own uncertainty. It came with version 4 of the analysis.
    - **What it rests on.** On the 17 songs with marks it is sure on 9 and right on all 9. On the 104 inbox songs, when it is sure of the other bar the vote of what comes in says the same on 5 of 6. It was chosen from a scan of about 150 measures on 14 songs, and 5 of 6 is a small number: `LOG.md`, session 9, second goal and third part.
    - **What it leans on most: the 90 seconds.** Over 60 s the mix reads -1.7 and would stay wrong.
    - **What comes in will not find the mix, and its start will not either.** Its largest rises sit on the labels' count 5, and a measure fine enough for the guitars at its fifth beat fires at the second bar of 8 of the 12 songs whose count is right.
    - **Not built, for later:** the bass changes side at his half-phrase marks on the mix, on Herrera and on El Perdedor, so it is a second witness for slice 4 beside the rises. And measuring rises from the third beat of a song instead of the fifth widens the two thinnest votes, Héroe Favorito to 30 against 6 and Bachata Que Duele to 13, with no song wrong.
    - **For the owner to listen to:** Ronny Dae - You Gotta Go, the one inbox song the bass moves.
  - **Thin votes, where the next song may go wrong.** Héroe Favorito keeps its count by 16.1 against 13.8. *Since session 10 that is under 3 to 1, so its fills are asked: they read 4.47 for the bar it keeps.* Bachata Que Duele moves on one rise of 6.0 dB, the bass, with the limit at 5.0. Eso Es Amor keeps its count because its start, out of silence, counts for the first bar: 32.7 against the 5.4 of its first half phrase, at 11 s.
  - **For the owner to listen to.** Every stored song gets the new count. Of the songs he marked only in part, Imitadora and El Perdedor keep the count they had. On Sus Huellas the whole count moved by a bar, so the intro before 28.76 s, which he agreed with, now reads four off: the analysis moves the count once and does not put a short bar where he hears one.
  - **The check is stricter than his words in one place.** "From the entry on" has no mark to stand on for the six songs he found right, so they are judged from the first count 1 they had. All six pass that. If a later change fails it only inside an intro without percussion, that is for him to say.

- **What was learned about half phrases**, which are not part of the entry. The same rises mark them.
  - **Of his 14 marks that are not of the kind `entry`, 9 have something coming in on the very bar he marked**: both of Herrera, the one of Sin Fin, the one of Sus Huellas, the one of El Perdedor, 2 of the 3 of Imitadora, and 2 of the 5 of Eso Es Amor, which are count 1s of the labels and not all after a half phrase. The one of Me Emborrachare, at 151.32 s, has none.
  - **From a mark on, what comes in does so on the other bar**, until the next mark. Herrera reads first bar six times up to 37 s, the other bar at 54 s, his first mark, and the first bar again at 111 s, his second.
  - **It also reports some that are not there.** On the seven songs with no half phrase, 34 rises are on the first bar and 6 on the other: three on Héroe Favorito, two on La Bachata, one at the very start of La Noche Perfecta. On La Bachata the bass comes in a bar before the chorus, at 36.86 s.
  - **What that suggests for slice 4**: follow the bar that things come in on along the song, with a cost for changing it, and put a short bar just before the rise where it changes. One rise alone on the other bar is not enough: two in a row, or one much larger than those around it, would be the thing to test. Session 6 tried the same with the harmony and it did worse.
  - **The half phrase of Sus Huellas is of this kind**, and the owner described it: the bar before the percussion enters is half length. The rises read first bar at 9 and 14 s, the other bar at 29, 48 and 131 s, and the first bar once more at 156 s.

- **A skill breaks the code on purpose**, since session 8: `.claude/skills/break-on-purpose/`. Asked to break a part and see its checks fail, it breaks every claim of the part once, then what no claim speaks of, and repairs each weak check it finds.
  - It was tried on three tasks before the owner's last changes to it, and not since. `LOG.md`, session 8.
  - It is committed with the project: `.gitignore` keeps `.claude/` out except that one folder.
  - The program and its tests did not change in session 8.

- **The reference changed on 2026-10-06, outside git.** The owner's label files now carry the site's order of phrases, as blocks, for every section with a phrase shorter than an ocho.
  - The Intro of Me Emborrachare has its short bar first. The old reference had it last, by the last-bar rule, and was wrong: the owner listened.
  - The measured count was then 88 of 396 on Me Emborrachare, where it was 120. *Since session 9 it is 308 of 396.* Eso Es Amor is still 257 of 505 and Old Town Road 416 of 416. The analysis did not change: it lost the 32 beats it had only shared with the wrong reference.
  - The last-bar rule stays for a section without blocks, and decides nothing on these three mixes.
  - No code changed but one docstring. `LOG.md`, session 8, and `ACCEPTANCE.md`, slice 2.

- **After a review of the last commit**, the same day, in session 7. A fresh reviewer had four findings in `a775210`, and all four held:
  - **The loop can be switched off and on while the song plays.** The switch did nothing during playback.
  - **A large beat that has sounded is `#7a6500`**, 3.9 to 1 against the band in light and 3.5 in dark. It was the black of the marks at 28%, which is 1.8 to 1. It is less faint than it was: whether it is faint enough is the owner's to say.
  - **Two checks were repaired.** An assertion of `web/song.test.js` looked at a new array and could not fail. And no test read the large view: one now reads its canvas, in light and in dark.
  - Each of the four has a check that was seen to fail. `LOG.md`, session 7.

- **After the owner's check by hand**, in session 6:
  - **"Clear"**, in the transport bar, takes a marked range away. Switching the loop off still keeps it.
  - **Every song has an address**, `/?song=` and its id. The address bar shows it while the song is open. Loaded again, or opened from a link, the page opens that song. Back does not go from song to song.
  - **Opus files are taken**, like mp3 and m4a. The server did not change: it still receives plain samples.
  - **The checks of slice 2 were seen to fail.** The code was broken on purpose in 25 ways. Two breaks were caught by nothing and one not by the test that claimed it. Three tests were added or changed, and all 25 are caught now. `LOG.md` has the table.
  - The owner confirmed by ear that Old Town Road is right throughout, and that on Eso Es Amor the first percussion is count 1.
  - The owner's five notes for later are under "For later slices".

- Session 6 asked the owner five questions, ran an experiment on the three mixes and on 96 songs without labels, and the owner set the shape of the slice from its result. `LOG.md`, session 6, has the figures and the decisions, and `ACCEPTANCE.md` the items.
- **The analysis** now keeps the place of every beat in its bar, and a count from 1 to 8 that runs in eights from the first bar that is not silence. It was version 2 then. *Since session 9 the count may start a bar later, and since session 10 it is version 5: see the top of this file.* The five songs in `data/` have been analysed again: that happened by itself when the owner started the program.
- **The page** shows the count as the largest figure, with the tempo small beside the time. The large view is the ocho that is sounding, standing still, each beat at the place of its count. The song is in rows of four ochos, with the count under every mark. Count 1 is an upright bar. *Since session 11 the song is in plates, one for each bar, in rows of eight ochos: see the top of this file. The large view is as this says.*
- **"Count 1 here"**, in the transport bar, makes the beat at the playing position count 1. From there the count runs in eights. On a beat set this way the control reads "Not count 1" and takes it back. A beat set by hand has a cap across its bar. *Since session 11 that is the large view: on the song it has a lid over its plate.*
- The arrows with Shift move the position by an ocho.
- The server has two new requests, `PUT` and `DELETE /api/songs/<id>/ones?at=<seconds>`.
- **The count is right only where no half phrase has passed.** On Me Emborrachare the Intro starts with one: the count is four off from the fifth beat of the song, at 0:02, to the end of the Breakdown, at 2:31. "Count 1 here" on those two beats puts all 396 right: that is what the control is for. *Since session 9 this is turned round on the mix: the count is right from the fifth beat to the end of the Breakdown, and four off on the first four beats and after 2:31. One beat set by hand, at 2:31, should put the part after it right, and the first four beats would still read 5 to 8 where the labels have 1 to 4; that was worked out and not run.* *Corrected in session 8. This said "from 0:17, the end of the Intro", by a reference that had the short bar last.*

Before that, in session 5:

The redesigned page is built, with what slice 1 has. The owner chose its design, Terminal signs, among three, and the other two are deleted. Every check a program can run passes. The owner's checks of slice 1 are still open, listed below.

- Session 5 built the page from the brief below. What was run and decided is in `LOG.md`, session 5.
- The page now has a top bar, the library in a left rail, a band that says where the song is, every beat of the song in rows, and a transport bar.
  - The band shows the BPM as the largest figure, with the time small under it, and beside it the eight beats around the playing position. They slide past a fixed line and the one that crosses it lights.
  - A press on a beat moves the position there. A drag across beats marks a loop. "Start here" and "End here" mark its two ends at the playing position.
  - A song is renamed in its row or in the top bar. Space plays and pauses, and the arrows move the position by a beat.
- The server has one new request, `PATCH /api/songs/<id>?name=…`, for a renaming.
- The page showed no count and no grouping then. It still shows no section: those come with slices 3 and 4.
- It has a light and a dark ground and takes the one the system is set to. It has no control for that.
- The program is a Python one. The Node program is gone.
- **To run it:** `uv run python -m bachata`, then http://127.0.0.1:8080. `PORT` changes the port and `BACHATA_DATA` the folder of the library. Sessions 3 and 5 used port 8081 for everything they started, as the owner asked in session 3.
- **To test it:** `uv run pytest`. It runs the unit tests, the song checks and the flows through the page: 266 tests in about 15 and a half minutes since session 11, on the branch that was merged; 242 in about 11 and a half in session 10, and 215 in 5 and a half in session 9. Which tests the time went to was not measured. Since session 9 the entry check is one of them: `uv run pytest bachata/entry_test.py -s` prints a line per song, in about a minute. It needs the owner's 13 songs in the library and `fixtures/audio/by-ear.json`, and skips without the second. Since session 10 the six-song check is one too: `uv run pytest bachata/entry_pairs_test.py -s` prints a line per song, in about 4 minutes. It needs `fixtures/audio/entry-pairs.json` and the six songs in `fixtures/audio/entries/`, and skips without the first.
- **A program that is running shows the page it started with.** After a change to the page or to the server, stop it and start it again.
- **On a new machine, once:**
  - `uv sync`
  - `uv run python scripts/fetch_model.py`, which downloads two files into `models/` and checks the hash of each: the Beat This model, 81 MB, and since session 10 the Hybrid Demucs one, 335 MB. The program does not start without either.
  - `PLAYWRIGHT_BROWSERS_PATH=.playwright uv run playwright install firefox`, for the browser tests.
  - All three are already done on the owner's machine.
- **After a mix changes:** `uv run python scripts/measure_first_beat.py`. The song checks refuse a mix whose hash is not the one in its `labels.json`.
- **The library, `data/`, already holds the five songs.** They went in through the page, in Chrome. Their names come from the tags of the files, which are poor:

  | In the list | Length | It is |
  | --- | --- | --- |
  | mix | 3:15 | Me Emborrachare, the mix |
  | track0 | 3:54 | Eso Es Amor, the mix |
  | track0 | 3:20 | Old Town Road, the mix |
  | original | 3:59 | Me Emborracharé, the full commercial version |
  | original | 3:35 | El Perdedor |

## Next: the owner's checks, then slice 3

### Left open by the critique

The critique of 2026-10-08 is kept in `wt/bars-xhigh/.impeccable/critique/`, which git does not see. Its commands are the design plugin's, run as `/impeccable` and the name.

- **`audit`, not run.** For the one major issue that is open: the two canvases, `#now` and `#map`, have no role and cannot take the keyboard, and their labels tell the user to press what a keyboard cannot press. The count, an `<output>`, is said by a screen reader at every beat. The position control gives its value as raw seconds. What the critique proposes: labels that describe, the count said once an ocho or not at all, the time in words on the position control, and the song as one stop of Tab where the arrows move by a bar and Shift marks a range. A ring on a canvas has to be black: the yellow of the focus ring is 1.0 to 1 on the band and 1.1 on the light ground.
- **`polish`, not run.** The last pass. What the critique left for it: weight 600 is asked for in five places of `web/style.css` and only 500 and 700 are served; in dark the band and the lit bar are `#f2c500` while Play, "Add a song" and the focus ring stay `#ffd200`; "Add a song to see its beats." speaks of beats; and the end of a song has no state of its own.
- **Needs the server, so not built in a branch for the page:** why an analysis failed, and a way to try it again without deleting the song.
- **Not tried:** "Add a song" pressed with the pointer still leaves the keyboard on the file control, so Space opens the file window again. Where Tab starts from after a press with the pointer on the bar. The two lines of the message beside "Add a song", in a browser.
- **The rest of what the critique found**, not asked for: no key for the loop, its ends, "Clear" or count 1; no search in the list; a song's name in the list does not open it; Tab goes through three controls a song before it reaches Play; nothing says the count may be wrong and that "Count 1 here" puts it right; and from three metres nothing says whether the loop is on.
- **`BRIEF.md`**, under "The interface", says "A beat is a small square, and the one that is sounding gets the large square a sign keeps for its pictogram". That is the large view now. On the song a bar is a plate, and the one that is sounding a yellow block. The brief was not changed: it is the owner's to word.

### Left open by the redesign

- **`DESIGN.md`.** The design plugin ends a build by writing one from the finished page: the colours, the typeface and the rules of the design, for later design work. It is a new top-level file, so by the owner's rule on existing files it is asked first. Until then the design is described in `BRIEF.md`, under "The interface", and its values are in `web/style.css`.
- **A control for light and dark.** The page follows the system. A control on the page is the owner's to ask for.
- **The layout.** The owner found that the three designs looked like skins of one layout. That is what the brief of session 4 asked for, and what the plugin does for a tool: a design gives the typeface, the colours, the density and one move of its own, and the layout stays. The plugin has a separate round that keeps the design and proposes three arrangements of the screen. It was offered in session 5 and not taken. Slice 2 has since put the count and the ochos on screen, which is what the round was waiting for.
- **What the owner judges by eye**, in `ACCEPTANCE.md` under slice 5: each large beat against its click, the figure read from three metres, and nothing told by colour alone.
- **One small thing the plugin's reviewer named** and did not count as a fault: the time under the large figure ends a little to the right of the figure's last digit.

### The redesigned page

This is the brief the owner confirmed on 2026-10-05, in session 4, with the decisions of session 5 written in. It stays here because slices 2 to 4 each put their result in a place it names. Its checks are in `ACCEPTANCE.md`, under slice 5.

**Who and what for**

- A dancer learning musicality, at the desk or three metres away on their feet. One screen serves both. It is a tool to operate while a song plays.
- For now the same person also checks the analysis by eye and ear.

**What it must do**

- From three metres: say where the song is now, the section and the count, 1 to 8.
- Second, what comes next and in how many ochos. Third, the shape of the whole song.
- Up close: every beat is its own mark. Count 1 and the start of each ocho stand apart, so a click can be checked against its mark. *Since session 11 that is the large view alone. On the song a bar is one plate, and nothing keeps a place for the beats inside it.*
- Nothing is drawn that an analysis has not produced.

**Direction**

- Three worlds were built as real pages on one layout, with a temporary switch between them. The owner chose **Terminal signs** in session 5. The other two and the switch are deleted.
- The page has a light and a dark ground. The owner's decision of session 5.
- A world supplies four things: typeface, colours, density and one signature move. The layout and the controls are the same in all three, and the controls are ordinary web controls. *Since session 11 the position control is drawn by the page.*
  - **Terminal signs, the one that stays.** Yellow panels and black type, after airport sign systems. Where the song is hangs as a sign band: the section's mark in a black square, its name, the count. A second band says what is ahead and how far. Rhythms differ by their mark, not by colour.
  - The two that went were Dominó, a green table with bone tiles and black pips, and The counts sheet, quadrille paper with four pen colours.
- The layout's own idea: the song is wrapped into rows instead of stretched on one line, so a beat gets about 30 pixels instead of 2.

**Layout and interaction**

- **Top bar:** the application's name, the open song's name, Add a song.
- **Left rail:** the library. Each row shows name, length, state, and which song is open. A message appears where its cause is.
- **Now band**, pinned above the song: the count as the largest thing on the screen, the section name second, BPM and time small. Beside the count, the ocho that is sounding, drawn large, its beats lighting on the beat.
- **The song:** every beat, in rows of four ochos, with each row's start time and the section brackets in the margin. *Since session 11 every bar, as a plate, in rows of eight ochos: the owner's note of 2026-10-06 and his choice of 2026-10-07.* It scrolls under the pinned band. It does not have to be whole on screen: the owner's change of session 5.
- **Transport bar** at the bottom: play and pause, position, loop, the click switch. *The owner kept the click switch there on 2026-10-08.*
- Pressing a beat moves the position there. Pressing a section plays from its first beat. A loop is a range marked on the song that repeats without a gap, the click staying on the beat.
- A replay is of one section by itself, without the change into the next one. Until sections exist, the range is marked by hand. The owner's decision of session 5.
- A song is renamed in place, in the top bar or in its row.
- Keyboard: everything is reachable by Tab with a visible focus. Space plays and pauses. The arrow keys move the position by a beat, and by an ocho or a section once those exist.

**States and ranges**

- **Built in session 5, with what slice 1 has:** beats and BPM only. The largest figure is the BPM, and the large view is the eight beats around the position, unnumbered and ungrouped. Rows are a line wrap with no meaning. No tile, no written count and no "ahead" band yet.
- **Later slices:** slice 2 puts the count in the large place and groups the beats into ochos. Slices 3 and 4 add each ocho's rhythm and the sections, and with them the jump to a section.
  - What the owner cares about most is the phrases and the count from 1 to 8. Their places are kept: the count takes the place of the large figure, and the BPM goes small beside the time. The ocho that is sounding takes the place of the eight sliding beats.
  - The eight beats slide because a window that turned its page every eight beats would draw a grouping no analysis has produced. Once the ochos exist, the large view can stand still and show one ocho at a time, as the brief says.
- There are three rhythms: derecho, majao and mambo. Mambo is a rhythm: the owner's decision of session 5. A part that is none of the three is drawn plain and has no name. It never gets a fourth colour.
- **Song:** none open, opening (about 40 MB to fetch, with progress), paused, playing, looping, ended, deleted from another browser.
- **Library:** empty, waiting, being analysed, ready, failed, asking to delete, being renamed. From 0 to about 470 songs, 5 today. Names run up to 200 characters, are often poor and sometimes identical.
- **Adding:** reading, decoding, sending (with progress), already in the library, and each refusal in its own words.
- **A song:** 20 seconds to 15 minutes at 90 to 175 BPM, so 30 to about 2,600 beats. Usually 400 to 520.

**Boundaries**

- **Stays as it is:** the analysis, the upload, the sound path and its clock, the server's checks and headers, the list asked for every 2 seconds, and the wording of the existing messages.
- **Changes outside the page:** renaming needs a new request on the server, with the same checks as a deletion and the 200 characters of a name. Looping touches how clicks are scheduled. The end-to-end tests follow the new page in the same change.
- **Not wanted:** a waveform, texture or shadow on tiles and paper, a handwriting typeface, a separate view for practising, a phone layout, anything for a public version, and any feature beyond jump, loop, rename and the keyboard.

**Constraints**

- Typefaces are system ones or files the application serves: the page's content security policy allows nothing from elsewhere. A typeface file is a download, to be logged with its size and its licence.
- Colours stay as custom properties on `:root`, which the canvas reads.
- Per-beat marks are drawn on a canvas, on the device pixel, not as elements.
- Never colour alone. Text contrast meets WCAG AA. Motion stops under the reduced-motion setting, and state changes still show.

**Where each part is in the code**

- `web/index.html` and `web/style.css`: the layout, the controls, the typeface and the colours. The colours are custom properties on `:root`, for light and for dark.
- `web/draw.js`: the two canvases. Where every mark goes, and how a beat, the place the large beats pass and a marked range are drawn.
- `web/app.js`: everything the page does.
- `web/song.js`: what can be worked out without the screen or the sound card, the loop and its clicks included. `web/song.test.js` checks it.

### The owner's checks

**The owner's checks**, which close slice 1. Start the program, open each song from the list, and play it with the click on.

1. **By ear, the three mixes**: the click is on the beat through the whole song. Places where the tracker had trouble before the fix, so worth a listen:
   - Old Town Road from 1:29 to 1:59 and from 2:58 to the end. These are the Trap parts, where the tracker alone heard half the tempo.
   - Old Town Road from 1:48 to 1:55. The sound of the mix is 50 ms behind the labels there, and the click follows the sound.
   - Eso Es Amor from 0:24 to 0:30, where the tracker alone went to the off-beat.
   - Me Emborrachare from 3:10. The percussion has stopped and the click carries on for five beats, to 3:12.
2. **By ear, the two commercial recordings**: the click is on the beat wherever the song can be counted.
3. **Confirm that 124 and 128 are the counts a dancer steps** on the full Me Emborracharé and on El Perdedor.
4. **Decide what the intro of the full Me Emborracharé is.** It is shown at 116 BPM at the start, at about 102 from 0:06 to 0:13, up to 141 at 0:17, and at 124 from 0:19 on. If the click is right there, the item about the commercial recordings holds as measured. If it is not, that intro is the first test spot for a tempo change.
5. **Confirm two numbers of session 3**:
   - the window of 90 ms for "the same beat", up from 70. It grew for three beats of Old Town Road, and partly because the script puts the first beat at the very start of the attack. With the beat 15 ms later in the attack, where `fixtures/audio/README.md` has it, 70 ms holds on all three mixes; with session 2's figure one beat is at 75 ms. `LOG.md` has the table. The choice is between 90 ms with the reference as it is, and a later reference with 70 ms;
   - the tempos the analysis may follow, 90 to 175 BPM.
6. Answered on 2026-10-06: a section starts on count 1.
7. **Listen to the half phrases the owner has not heard**, and say for each whether the short bar is where the site puts it. The Intro of Me Emborrachare is answered: the owner heard it on 2026-10-06, and the short bar is first. Left: on Me Emborrachare the Breakdown, short bar last, and the Ending. On Eso Es Amor the Intro, both Pre Choruses and the Bridge, short bar last in each. Since session 8 these come from the site's blocks, not from a rule of ours. The first labelled beat of Me Emborrachare is answered too: the owner accepted on 2026-10-06 that the song opens with a half phrase, so that beat is count 1. The owner's note on intros and endings, under "For later slices", bears on the Intro of Eso Es Amor, on the Ending of Me Emborrachare and on the Outro of Eso Es Amor.

If the click sounds loose rather than wrong: beat times come in steps of 20 ms, because the tracker looks at the song 50 times a second. Moving each beat onto the nearest attack of the sound is the next thing to try. It was not built, because only an ear can say whether it is needed.

### Slice 2, as built, and what it leaves to the owner

- **By ear, the two commercial recordings:** a beat shown as 1 or as 5 is the first beat of a bar, wherever the song can be counted.
- **By eye:** count 1 against the other beats, and a count 1 set by hand against the others, in the large view and on the song. Since session 7 also the large beats that have sounded, in their new colour, against the ones to come.
- **The proposals in `ACCEPTANCE.md`, under slice 2:** the 40 dB under which a bar is silence, the half phrases the owner has not heard (check 7 above), and that the control takes a count 1 back.
- **The control, in use.** It is one button and nothing more, as asked. Whether a song with several half phrases is quick enough to put right with it is the owner's to say after using it.

### Then slice 3

**Derecho or majao for each ocho.** Nothing of it is decided. It starts with a round of questions, as slices 1 and 2 did. Three questions are already open under "For later slices": mambo in the labels, a section whose blocks disagree with it, and which rhythms count as `other`.

## Rules that are easy to break

- **The bars are counted in two places, and a test holds them together.** `web/song.js` counts them for the page and `bachata/places.py` for the commands. A change to `countsWith`, `barsOf`, `nearestBeat` or to how a place is read is made in both, and `test_python_and_the_page_number_the_bars_of_a_song_alike` says when it was not.
- **`python -m bachata` with no argument is never run on this folder's `data/` to try something.** It analyses every song of an older version again. To try the server, `BACHATA_DATA` names a scratch folder. `where` and `bars` only read.
- **Breaks of a Python file that are run by a script each get their own `PYTHONPYCACHEPREFIX`.** Two in the same second that leave the file the same size share a compiled file, and the second reports the failure of the first.
- **A bar number is not a place for good.** It moves when a count 1 is set by hand or the song is analysed again. The seconds beside it do not: whatever prints a place prints them too.
- **The page plays the samples the server stored**, never an `<audio>` element on the original file. Otherwise the click drifts from the sound by whatever the browser trims at the start of the file.
- **The page decodes a file at a fixed 44.1 kHz, in stereo**, and sends the rate and the length. An ordinary audio context would resample to the machine's own rate without saying so. The server mixes down and resamples for the analysis.
- **The type of a file is read from its first bytes**, never from its name: mp3, m4a, and opus, which is `OggS` with `OpusHead` at the start of its first page. Other sound in Ogg is refused. The tags of an opus file run over many pages when it has a cover picture.
- **The server looks at nothing in the address of the page.** The page reads the song from `?song=`, checks that it could be an id, and asks for it like any other song.
- **A test that restarts the program to see what reached the disk restarts before it renames.** A renaming writes the whole song again and hides what was only in memory.
- **The server never reads a media file made elsewhere.** It receives plain samples, stores them as they are and sends them back as they are. No FLAC: Chrome does not decode it back to the same samples.
- **Every limit the page checks, the server checks again** on what it receives. A page's check can be bypassed.
- **The analysis must not assume one tempo for the whole song.** It would pass all five songs and be wrong.
- **The tempo range of the analysis must stay narrower than a factor of two.** That is what keeps a half-time part at the count of the song.
- **The analysis and its checks get the mix only.** The instrument tracks are for understanding a failure and for measuring the reference.
- **The every-beat item is not loosened.** If a part with no clear pulse makes it impossible, the numbers go to the owner.
- **The window is 90 ms.** It grows again only if the measurements show it must, up to 120 ms, with the reason logged.
- **The page has no inline script, no inline style and no `eval`.** Its content security policy blocks all three, and a test tool that evaluates a string inside the page is blocked with them.
- **The tests of the security headers carry their own list.** A test that reads the list from the program passes when a header is removed.
- **The page draws nothing that neither an analysis nor the user has produced.** Before slice 4 there is no section on screen.
- **The analysis answers for the bar, not for the count.** The count is a guess in eights until slice 4. Nothing in slice 2 may look for half phrases in the sound and show them as found: the tracker of session 6 reports ones that are not there.
- **The analysis never reads the owner's marks**: not `fixtures/audio/by-ear.json`, not `fixtures/by_ear_before.json`, not a label file, not `song.json` in the library. It gets the samples and the rate. The song checks watch what it opens.
- **`fixtures/by_ear_before.json` is written once.** It is the count the songs had before session 9. A check that makes it again from the analysis compares the analysis with itself.
- **The entry check reads the sound of the library, `data/songs/<id>/sound.raw`, and nothing else of it.** A stored result is made again by every new version of the analysis, and a mark set by hand is the owner's answer.
- **The count is put together on the page**, in `countsWith` of `web/song.js`, from the analysis's count and the beats set by hand. The server keeps those as times, with the song and not with the result, so a new version of the analysis leaves them alone.
- **A bar is four beats.** The DBN is given bars of four only.
- **Every file of the page is named in `PAGE_FILES`**, in `bachata/server.py`, and read once when the program starts. A new file needs an entry, and a changed file needs the program started again.
- **The tests find a bar through what the song says about itself**: `data-bars`, the first beat of every bar, `data-plates`, the box of its plate, and `data-lit`, the bar that is lit, beside `data-counts` and `data-by-hand`. `data-marks` is gone. They reach a beat with a press on the plate of its bar and the right arrow, once for each beat after the bar's first. A change to how the song is laid out keeps those attributes true. `data-lit` and `data-ocho` on the large view are as they were, and `LARGE` in `e2e/page_test.py` still takes an eighth of its width for the place of each count.
- **In light, the marks, the ink and the brackets are all `#121212`.** A test that reads a pixel in light cannot say which of them the page used. Whatever is told by its colour is looked at in dark as well. Since 2026-10-08 the lit block is not one of them: in light it is the yellow, and its edge the black.
- **The tests of the song carry their own list of the colours.** Read from the page, a colour that went wrong there would go wrong in the test with it. The list came from `SPEC.md`; the lit bar in it is the owner's of 2026-10-08.
- **A press that should do nothing is tried from a bar that a wrong press would not reach.** From the first bar of a row, a press left of the row that went to the nearest bar changed nothing.
- **A halo cannot be seen on a first bar's plate in light**, nor a band: they are checked on a second bar's plate, which they would darken.
- **A test does not wait for the value it is about to check.** Two breaks of the layout were caught only by a time-out, which names no claim. After a new width the test waits for the song to be drawn again, and then looks.
- **The pixels of a thin figure do not tell two greys apart, or one weight from another.** For those the tests read the colour and the typeface the page asked for. They do not replace the pixels: `data-lit` alone, or a colour that was asked for, does not show what was drawn.
- **A song of the tests that fills one row cannot show what a second row does.** The tests of the rows use a song of 44 seconds, or a window 1100 wide.
- **Space on a switch stays the switch's.** A checkbox does not answer to Enter, so Space for play everywhere would leave the loop and the click with no key. The page takes the keyboard off a control of the bar after a press with the pointer instead.
- **The position control is drawn by the page so that its two ends are known**: the handle is 1rem wide and its middle goes from 0.5rem inside one end to 0.5rem inside the other. The range drawn on it, and the yellow of its line, are placed by that. A handle of another width moves both.
- **The page sets a place or a size through the style of an element, never through a `style` attribute.** The content security policy lets the first through and blocks the second.
- **The colours of the page are plain six-digit values on `:root`** in `web/style.css`, light first and dark after. `web/contrast.test.js` reads them from there. A colour or a strength that is set in `web/draw.js` is one that test cannot see: the large beats that have sounded were drawn at 28% there until session 7, at 1.8 to 1.
- **A loop is played by the sound itself**, through the loop points of the audio source, and its clicks come from `clicksUntil` in `web/song.js`. A loop made by stopping and starting the sound would have a gap, and its clicks would drift.
- **Product facts go in `BRIEF.md`, never in `PRODUCT.md`.** `PRODUCT.md` only points at the brief. The design plugin's `init` command offers to fill it in; a new fact goes into the brief instead.
- **A test of a setting carries its own number.** The tests of the picture and of the cut read 80 and 3.0 from the program, and passed with 40 and 5.0. The same blind spot as the security headers of session 3.
- **A made-up song for a test is not the plainest one.** It starts before its first bar, changes its tempo, or has its sound in one channel, wherever the code under test could tell the difference. Until session 10 the fills were asked about beat 0 in every test, and were scored at one tempo.
- **A chain of steps gets a test of the chain.** Every step of the fills had a test, and nothing but the six-song check ran them together.
- **`split()` never makes a piece for the end of a song alone.** The model refuses a piece under 18 ms, and a piece that only repeats the end of the one before counts twice.
- **The program checks every checkpoint before it starts.** A file that only some songs need would otherwise fail only those songs.
- **The watch on what the analysis opens looks at a path as it was asked for and as it is on disk.** In a work folder whose reference is links to the main folder, the second alone sees nothing.
- **A work folder under `wt/` shares `.venv`, `models`, `.playwright` and the items under `fixtures/audio/` with the main folder through links, and has a copy of `data/`.** Its checks are started from inside it: started from the main folder, a check tests `master`.
- **In the session's sandbox:**
  - `uv` needs `UV_CACHE_DIR` set to a writable folder, and each network host has to be allowed for the command that needs it.
  - Chrome does not start. Playwright's Firefox starts but plays nothing. `uv run pytest` then skips those tests and says so.
  - Playwright's Firefox does draw the page, so a screenshot that needs no sound can be taken inside the sandbox.
  - The whole run needs a command outside the sandbox, which the owner allows one at a time: `TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8081 .venv/bin/python -m pytest`. `TMPDIR` must be a short path, or Chrome dies with "Socket path too long".
  - When the owner's own program is on 8081, every test of the page fails at once with "Address already in use". Session 6 then used `BACHATA_TEST_PORT=8083` and left the owner's program alone. On 2026-10-06 one was on 8081, started that morning, and another on 8082, started the day before.
  - A program started inside the sandbox listens on a loopback of its own, which the owner's browser does not reach. For a review it is started outside the sandbox, as the whole test run is. On 2026-10-07 one was started that way on 8083, from `wt/d4-patch`.
  - A command inside the sandbox does not reach a program another command started, either. A picture of the page is taken by one command that starts the program and the browser both.
  - A command in the background is stopped after ten minutes unless it is given longer. The whole run takes fifteen.
  - A work folder has a port of its own for the whole run: `wt/bars-xhigh` used 8086, with `TMPDIR=/tmp/claude-1000/e2e-x`.

## Open

**For slice 1**

- **The owner's checks and confirmations** above.
- **The names in the library are only as good as the tags.** The reference files give "track0", "mix" and "original". A song can now be renamed on the page. The five in the library have not been.
- **The page asks for `/favicon.ico` and gets a 404**, which Chrome writes to its console on every visit. It did before the redesign as well.
- **Nothing checks the reduced-motion setting automatically.** The large beats are built to step instead of slide under it, and the lit beat not to swell.
- **A name is cut to 200 characters by the page**, as the server counts them, but the field itself stops at 200 units of the browser's own counting, which is fewer characters for some scripts and for emoji.
- **The installed Firefox, 157, was not driven by the tests.** Playwright brings its own build, 155. Session 2 measured the decoding of 157 by hand; the page itself was not opened in it.
- **The server cannot verify a song's fingerprint**, because it never sees the file. Someone inside the group could file a sound under the wrong one. Taken as acceptable for a private tool.
- **Browser decoding matches `ffmpeg`'s for the five songs only**, in Chrome 154 and in Playwright's Firefox 155: the beats from an upload are identical to those of the song checks. A file from another encoder may decode with a shift; the rules about the page above are what make that harmless.
- **No song with a real tempo change has labels.** Session 3 measured changes made with `ffmpeg`, which the analysis follows. Turning that into a check, or labelling the intro of the full Me Emborracharé, has not been put to the owner.
- **A song a dancer counts below 90 or above 175 BPM is shown wrong.** None of the five is near either end.
- **Plain samples take about 10 MB a minute.** The 20 GB hold about 31 hours of music, some 470 songs of 4 minutes.
- **madmom comes from a commit of its main branch and is built from source.** The packages its build fetches are not in the lockfile.
- **Torch and Beat This on Python 3.13 were not tried.** The project pins 3.12.13.
- **`fixtures/audio/README.md` is the owner's file** and does not mention the two fields the script adds to `labels.json`: `first_beat_s` and `mix_sha256`. `fixtures/validate.py` describes them. A `labels.json` made again from the site loses them, and the song checks then refuse the mix until the script has run.

**For slice 2**

- **Under 1600 wide the transport bar takes two lines, on purpose since session 11**: Play, the position and the length of the song, and under them the loop, count 1 and the click. At 1280 that costs a row of plates, as the two lines did before.
- **A song of 3:15 shows whole at 1920 by 1080 since the plates**, 398 beats in 7 rows, and scrolls at 1280 by 720. A row of plates is 62 from the one before.
- **Nothing checks by a test which numeral is on a plate.** In the large view a test finds something written under every beat, and the empty places of a short ocho, since session 7. The numerals on the song were looked at in pictures.
- **After a drag, the bar before the range is lit until the song plays.** A loop starts 20 ms before its first beat, and a position outside the range moves to that start. Before the plates it was one small mark; now it is a whole block beside the range. Whether a loop should start on its first beat when the song is paused is the owner's to say.
- **The nine points of `SPEC.md` under "Not in the picture"** are built as the spec has them and are not confirmed: every colour in dark, the halo under the pointer, which bar a point between two plates belongs to, that a drag cannot mark one bar alone, a range drawn over whole bars, the lid over the lit block, four ochos a row under about 1200, the text "Drag across bars", and the faint plate of a second bar counted as a ground for text.
- **One break of the plates was not tried**, the one that needs sound: the lit bar a beat early while the song plays. `LOG.md`, session 11, says how to run it.
- **A change of count 1 in another browser arrives with the list**, so up to two seconds later.
- **The count starts on the first bar that is not silence**, 40 dB under the level of the song. A song that fades in over several bars may start its count late; none of the 101 songs analysed in session 6 does.
- **Sure by 2 is weaker than it reads**, for the fills and, by how it is built, for the bass too: 24% of made-up songs with no fills read 2 or more, where 4.6% would if the uncertainty were right. The owner kept the limits on 2026-10-07. The bass was not measured the same way.
- **A song whose fills are sure, and where what comes in is clear the other way, keeps what comes in.** None of the songs here is such a one.
- **Where the settings of the fills come from is not written**: 3 to 1, sure by 2, 60 seconds, 12 dB, 4 bars, the cut at 3, half weight for a fill.
- **The licence of the Hybrid Demucs checkpoint is not logged**, and the download in `scripts/fetch_model.py` was not run: the file was already in `models/`.
- **Not looked at by any test:** the real model on a song longer than one piece of 30 s, the floor of a picture, and the 5% behind "its loudest" where the percussion comes in.
- **The inbox songs were not run with the fills.** From the table of session 9, 30 of the 104 have a vote under 3 to 1 and would be split: worked out, not measured.

- **Back does not go from song to song.** Opening a song rewrites the address in place and adds nothing to the browser's history. The owner asked for reloading and sharing; whether Back should step through the songs is the owner's to say.
- **An address that names a song still being analysed** shows the page as with no song, and opens the song when it is ready.
- **"Clear" is one more control in the transport bar.** Its name and its place are the session's choice. *Since session 11 it shows only while something is marked: the owner's choice of 2026-10-08.*
- **Opus is decoded by the browser**, as mp3 and m4a are. Checked in Chrome and in Playwright's Firefox, with files made by `ffmpeg`, and the type and tags of the 106 files of the owner's folder were read by the page's own code. None of those 106 was uploaded.

**For later slices**

- **The owner's notes of 2026-10-06, after using slice 2. None of it is built.**
  - Extra bars are not detected, so 1 and 5 swap. They frequently come after 4 phrases, and beat information alone is not enough: the energy of the instruments has to be correlated.
  - In intros and endings a section can start on an unexpected count or be an isolated bar. That is a way to make sense of the intro or ending, not an extra bar.
  - The count 1 the owner sets by hand should later serve as feedback: reference data to measure and improve the analysis.
  - The lower view could show bars instead of every beat. Not critical. *Built in session 11: the plates.*
  - The beats in the silence before the music are shown with counts 5 to 8. They could be shown without a count.
- **What those notes touch, as the session reads them:**
  - The second note is about the reference count. It bears on four sections: the Intro of 36 beats and the Ending of 4 on Me Emborrachare, the Intro of 20 and the Outro of 9 on Eso Es Amor. Since session 8 the site's blocks say how each is counted, not a rule of ours, and the Intro of Me Emborrachare is settled: the owner heard its short bar first. How the other three are counted is to be settled with check 7, before slice 4 makes the count strict.
  - The third note already has data. On 2026-10-06 the owner's library held five beats set by hand on the mix of Eso Es Amor, at labelled beats 20, 112, 268, 360 and 436, and one on El Perdedor at 1:39. All five are a count 1 in the reference. With them, 460 of the 505 labelled beats have the count of the reference, against 257 without. The 45 that differ are in the Mambo, beats 344 to 359 and 380 to 399, and after the last Chorus, from beat 496. `data/` is not in git: a copy of those beats is in `LOG.md`.
  - The first note agrees with what session 6 measured: the harmony alone finds some extra bars and reports others that are not there.

- **Mambo.** It is a rhythm: the owner said so again in session 5, so the page will have three kinds. The labels treat it as a part of the song, like Verse or Chorus, whose rhythm is majao or derecho. No label has mambo as a rhythm, so G1 has nothing to compare mambo against. How G1 is checked for mambo is still to settle before slice 3.
- **When a section's rhythm and its blocks disagree, which wins?** On Me Emborrachare the Bridge is labelled Derecho, and its two blocks are `-` and Majao.
- **Which rhythms count as `other`?** The labels also have Urban, Trap, Dembow, `-` and none.
- **A section's `end_s` in the labels is the start of the next section.** G2 speaks of the last beat, which is one beat earlier.
- **The tempo, to look at again. Not in slice 2.** The owner's two points of 2026-10-06:
  - The tempo of a bachata song is usually stable, so a tempo that moves inside a song is more likely the analysis than the music. In session 6, 13 of 96 songs read a tempo that spans more than 8% of their median; `LOG.md` lists them. An intro may read loose, and that is understood.
  - In a part that is not the intro and has no percussion, the tempo may be worked out from the part before it and the part after it that have percussion, instead of being read from the part itself.
- **The songs that stood apart in session 6**, in `LOG.md`, are the owner's to look at. "Entre La Espada Y La Pared" was downloaded wrong and is ignored.
- **Hearing count 1 from count 5, and a half phrase, from the sound.** Session 6 found no plain measure that does it. Slice 4 needs it, or the sections that make it unnecessary. A model taught on labelled ochos was not tried: three songs have labels.
- **"Jiory - Eso Es Amor" is among the 96 songs**: the commercial recording of a mix that has labels.
- **The last three labelled beats of Me Emborrachare have no percussion.** The analysis carries the pulse over them, and their place in the bar is right.
- **Lining up the labels with the commercial recordings.** The full Me Emborracharé is 44 s longer than the mix and differs in places.
- **The screen of slice 5 is built early**, with what slice 1 has, and G4 is still checked in slice 5.
- **No `DESIGN.md` exists.** See "Left open by the redesign" above.
- **The design plugin's live mode is not set up.** It puts a script of its own into the page, which the page's content security policy blocks. Allowing it is the owner's decision.
- **No measure for "fluid".**
- **Deployment for coworkers** is out of scope. When it comes:
  - a container;
  - an nginx body limit far above the default, since a 4-minute song is about 42 MB of samples and a 15-minute one about 159 MB;
  - the library is shared, so everyone who can log in can play and delete every song;
  - the program answers only to `127.0.0.1` and `localhost`, and takes a request as its own page's only over plain `http`: both have to learn the public name and `https`;
  - the page takes the fingerprint of a file with a browser function that works only on `https` or on localhost.

**Housekeeping**

- **`.claude/` and `.impeccable/` are ignored by git**, on the owner's instruction in session 4. The first holds Claude Code's settings, with paths from the owner's machine. The second is where the design plugin keeps its working files: since session 5, the direction it was given for the page, the screenshots of the three designs under `review/`, which are the only pictures left of the two that went, and in `config.json` one exception for its hook, which is explained in `LOG.md`.
- **Not in git, and each rebuilt by one command:** `.venv/`, `models/`, `.playwright/`. `data/` is the library and is not rebuilt by anything.
- **`wt/` holds work folders, one for each task that runs beside another**, each on a branch of its own. `.git/info/exclude` keeps `wt/` out of git's listing, with the three files a task keeps in its folder: `TASK.md`, `incoming.patch` and `NOTES-for-records.md`. `git worktree list` names them. The owner asked on 2026-10-08 that no work folder and no branch be removed. As they stand:
  - `wt/d4-patch`, branch `d4-patch`: the fills, merged in session 10.
  - `wt/d4-bars`, branch `d4-bars`, at `11d19ef`: the first attempt at bars, rejected by the owner, not merged.
  - `wt/bars-high`, branch `bars-high`, at `9a7c8bf`: the plates built at high, accepted, not merged. Its notes were not read, and its lit bar is black in light.
  - `wt/bars-xhigh`, branch `bars-xhigh`, at `cbd2241`: the plates built at xhigh, with the three changes after the critique, merged in session 11. It holds `SPEC.md`, `chosen.png`, the pictures in `shots/`, the notes these records were written from, and the critique.
