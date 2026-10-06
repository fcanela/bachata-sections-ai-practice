# Acceptance list

An item is ticked only after its check has been run and the result is in `LOG.md`.

Items marked *proposed* contain a number or a rule that is not in the brief. The owner confirms or changes them.

A ticked item names the check behind it. `uv run pytest` runs all of them; the ones in a browser need a machine where a browser can start and play.

## How a song result is judged

Against the reference material in `fixtures/audio/dev/`, which is not committed. Each song from the site has a folder there with a `mix.m4a` and a `labels.json`. `fixtures/audio/README.md` describes the format.

- **The checks read those files where they are.** When the material is not on the machine they print "skipped: no reference material". A song item cannot be ticked from a run that skipped.
- **The input is always the mix**, never the separate instrument tracks. Someone using the application uploads a whole recording.
- **The labels give every beat.** Each label file has a tempo, the time of the first beat and a number of beats, so beat *n* is at `first beat + n × 60 / bpm`.
- **The audio decides where a beat is.** The labels' tempo and beat counts are exact, but their times are early by a constant amount per song: 95, 62 and 40 ms, as `scripts/measure_first_beat.py` measures the start of the attacks. The script measures the first beat on the percussion tracks of each mix and writes it into `labels.json` as `first_beat_s`, beside `mix_sha256`, the mix it was measured on. A mix whose hash no longer matches is measured again before anything is compared with it: the checks refuse it until then.
- **Same beat:** two times are the same beat when they are within 90 ms of each other. It was 70 ms, and the owner allowed up to 120 ms if the measurements showed 70 to be too tight. They did, in session 3: on Old Town Road, from 108 to 114 s, the sound of the mix sits 50 ms after the labels' grid, and three beats are 73, 76 and 84 ms from their label. `LOG.md` has the measurement. *For the owner to confirm: the 90. It depends on where in an attack the beat is put: the script puts it at the very start, and with the beat 15 ms later, as in `fixtures/audio/README.md`, 70 ms holds on all three mixes.*
- **Songs without labels** are the two commercial recordings. They get one automatic check on the tempo, and the owner's ear is the final word.

## Setup

- [x] `uv run python -m bachata` serves the page, on 127.0.0.1 only. `bachata/server_test.py` starts the program and reads its listening sockets from the kernel.
- [x] `uv run pytest` passes.
- [x] The reference material has a place outside git, `fixtures/audio/dev/`, a validator for the site's label format, `fixtures/validate.py`, and a script that measures the first beat of each mix.

The three were reworded in session 3, when the Python program replaced the Node one, and checked again.

## The whole application

- [ ] **G1** For every fixture, the output has the same derecho, majao and mambo sections as the reference, in the same order. *Open: the labels treat mambo as a part of the song whose rhythm is majao or derecho, not as a rhythm. See `NEXT.md`.*
- [ ] **G2** Every section starts on its first beat and ends on its last beat: both times are the same beat as the reference. In the labels a section's `end_s` is the start of the next section, so its last beat is one beat earlier.
- [ ] **G3** Nothing is invented: no output section falls in a part the reference marks `other`.
- [ ] **G4** The user can pick an existing song or upload a new one, and gets the sections for either. An existing song is a song in the server's library. The library is built in slice 1; this item is checked in slice 5, when the list has its real screen and the result is sections.
- [ ] **G5** Everything runs locally: marking a song sends nothing beyond the machine that serves the application and uses no paid API.
- [ ] **G6** It runs fluid. *No measure set yet. The owner has no expectation on analysis time yet; slice 1 measures it and the owner adjusts.*
- [ ] **G7** It is secure for the user and for the machine that serves it. The checks for the upload and the library are under slice 1. Later slices may add more.
- [ ] **G8** Visuals and UX are great. The owner judges this; no automatic check.

## Slices

Each slice takes a song and shows a visible result. There are five and the number does not change; new work is fitted into one of them.

### 1. Beats and tempo

The owner picks a file, mp3, m4a or opus, or a song from the list of remembered ones. Opus was added by the owner on 2026-10-06, in session 6, with the same limits and checks. The page shows one mark per beat, lights the mark of the beat that is sounding, shows the BPM at the playing position, and gives a click on every beat that can be switched off. The marks are not numbered; the count 1 to 8 arrives in slice 2.

Uploaded songs are remembered in one library on the server, the same for everyone who can reach the application.

Slice 1 is done when every item below holds, on all three mixes and both commercial recordings. Me Emborrachare comes first, and the beats are built before the library.

**The three mixes, checked automatically**

- [x] From the first labelled beat to the last, every labelled beat has exactly one detected beat that is the same beat, and there is no detected beat without a labelled one. If a part with no clear pulse makes this impossible, the numbers go to the owner, who decides. The item is not loosened any other way. `bachata/songs_test.py`: 396, 505 and 416 beats, all found. It holds with the window at 90 ms; at 70 ms three beats of Old Town Road are outside.
- [x] At every labelled beat, the shown BPM is within 4% of the label's BPM. That is the tempo a dancer counts, not half or double. `bachata/songs_test.py`.

**The two commercial recordings**

- [ ] The shown BPM is within 4% of 124 on the full Me Emborracharé and of 128 on El Perdedor, once the owner confirms those are the counts a dancer steps. Both figures come from a rough measurement in session 2. *Waits for the owner. Measured in session 3: El Perdedor is within 4% at every beat. The full Me Emborracharé is within 4% from 0:19 to the end; its first 18.5 seconds read between 102 and 141 BPM. The automatic check, in `bachata/songs_test.py`, is on the median and passes for both.*
- [ ] By the owner's ear: with the click on, the click is on the beat wherever the owner can count the song.

**The page**

- [x] It shows one mark per beat, the lit mark of the beat that is sounding, the BPM at the playing position and the click switch. `e2e/page_test.py`, in Chrome and Firefox. It also checks that every beat gets one click, at its own time on the clock the song plays on. Reworded in session 5, when the page was rebuilt, and checked again: the strip and its moving marker are gone.
- [ ] By the owner's ear: with the click on, the click is on the beat through the whole song, on each of the three mixes.

**The library**

- [x] An uploaded song is kept on the server with its results. It appears in the list in every browser, with its name and its state: waiting, being analysed, ready or failed. The four states: `bachata/server_test.py` and `bachata/queue_test.py`. Two browsers: `e2e/page_test.py`.
- [x] A song opened from the list plays and shows its beats in a browser that never had the file. Nothing is uploaded and nothing is analysed. `e2e/page_test.py`.
- [x] A file that is already in the library, byte for byte, is not uploaded, not stored twice, and not analysed twice by the same version of the analysis. The stored song opens. `e2e/page_test.py` and `bachata/server_test.py`.
- [x] A result made by an older version of the analysis is replaced: the server analyses the song again from the stored sound, with no upload. `bachata/server_test.py` and `bachata/queue_test.py`.
- [x] The name comes from the file's title and artist tags when it has them, and from the file name without its extension otherwise. For an opus file too, whichever way the names of its tags are written, and when a cover picture makes them run over many pages. `web/song.test.js` and `e2e/page_test.py`.
- [x] Songs are analysed one at a time, in the order they arrived. A song whose analysis fails is marked failed and does not stop the next one. `bachata/queue_test.py`.
- [x] Any song can be deleted, with one confirmation, whatever its state. Deleting a waiting song takes it out of the queue. The states: `bachata/server_test.py` and `bachata/queue_test.py`. The confirmation: `e2e/page_test.py`.
- [x] The library and the queue survive a restart of the program. `bachata/server_test.py`, `bachata/store_test.py` and `bachata/queue_test.py`.

**What is refused, part of G7**

By the page, before anything is sent:

- [x] A file that is not mp3, m4a or opus, or that the browser cannot decode. The type is read from the first bytes of the file, not from its name. Other sound in the wrapping of opus, Vorbis for one, is refused. `e2e/page_test.py` and `web/song.test.js`.
- [x] A song shorter than 20 seconds or longer than 15 minutes. `e2e/page_test.py`, with an mp3 and with an opus file.

By the server, which cannot trust what a page checked:

All of these are checked in `bachata/server_test.py`, unless another file is named.

- [x] Anything from another machine: the program listens on 127.0.0.1 only. A request that names another host is refused too.
- [x] Any request that changes the library (an upload, a deletion, a removal from the queue) and does not come from the application's own page. Removing a song from the queue is deleting it while it waits.
- [x] A body that is not the expected sample format, or that holds less than 20 seconds or more than 15 minutes of sound.
- [x] A song id that is not well formed, and a name longer than 200 characters.
- [x] A new song when the library has reached 20 GB. Tested with a small limit.

What the server never does:

- [x] It never reads a media file made elsewhere. It receives plain samples and stores those samples as they are.
- [x] It writes only inside one data folder. File names on disk come from the song's id, never from text a page sent. Also `bachata/store_test.py`.
- [x] It sends stored sound back only as sound data, never as a page. Names are always shown as plain text: `e2e/page_test.py`.
- [x] It sends every answer with the security headers.

**How these are tested**

- Logic is covered by unit tests beside the code. The page's logic is in `web/song.js`, with tests for Node's own runner that `pytest` also runs.
- Whole flows through the page are covered by end-to-end tests in a real browser, in `e2e/page_test.py`: an upload, an upload of an opus file, the list, opening a song in a browser that never had the file, a second upload of the same file, a deletion, a file of the wrong type, a song that is too short, a song that is too long, a name with markup in it, the clicks, and the exact samples that play. They run in the installed Chrome and in Playwright's Firefox, and skip a browser that cannot start.
- The two by-ear items are the owner's.

**Not verified in slice 1**

- Following a tempo change. No acceptance check covers it. Session 3 measured it on two mixes whose second half was sped up or slowed with `ffmpeg`: a change of 8% is followed with every beat found, a jump of 20% on one mix of two. The intro of the full Me Emborracharé reads about 102 BPM before the song settles at 124, which the owner can hear with the click on. If the owner hears a shift in El Perdedor, that moment becomes a test spot.
- Analysis time. It is measured and logged, with no limit to pass: about 4 seconds for a song of 4 minutes, and 6 to 8 seconds from picking a file to seeing its beats.

### 2. The grid of ochos

The owner decided the shape of this slice on 2026-10-06, in session 6, after an experiment that `LOG.md` records. The analysis hears the bar on every labelled beat of the three mixes. Nothing at hand hears which of two bars is the first of an ocho, or where a bar is extra. So the slice is strict on the bar. The count from 1 to 8 is shown and measured, and becomes strict in slice 4, where a section gives it a place to start again. Until then the user can say where count 1 is.

**The reference count.** The labels give every section a length in beats, and some sections a list of blocks. Since 2026-10-06, in session 8, a section that holds a phrase shorter than an ocho has the site's own order of its phrases as blocks, so the blocks say where a half phrase is. The count of every labelled beat follows by these rules, which the owner set in session 6. `fixtures/validate.py` applies them.

- The first labelled beat of a song is count 1. The owner confirmed it by ear on 2026-10-06 for Old Town Road, which is right throughout, and for Eso Es Amor, whose first percussion is count 1. For Me Emborrachare the owner accepted it on 2026-10-06, in session 8: its first four beats are read as a half phrase, counted 1 to 4, as the site's blocks have them.
- The count starts again at 1 at every section and at every block.
- A block of 4 beats is a half phrase. It is counted 1 to 4.
- A section without blocks is whole ochos from its start, and what is left over is at its end: 4 beats are a half phrase, its last bar. This is only what is done where the labels give no blocks. On the three mixes it now decides nothing: every section with a short phrase has blocks, and the one section of 4 beats is a half phrase whole.
- Every section starts on count 1, which answers check 6 of session 5.
- Eso Es Amor has eight half phrases, Me Emborrachare three and Old Town Road none. All are where the site puts them. On Me Emborrachare the Intro is 4, 8, 8, 8, 8, the short bar first, and the Breakdown 8, 8, 8, 8, 4. On Eso Es Amor the Intro and both Pre Choruses are 8, 8, 4 and the Bridge 8, 8, 8, 8, 4.
- The owner listened to the Intro of Me Emborrachare on 2026-10-06: the short bar is first, as the site has it. Until then the last-bar rule had put it last, which was wrong. *The other half phrases are the site's and have not been heard by the owner.*
- The Outro of Eso Es Amor is 9 beats: one ocho and one beat on count 1. The site's blocks say the same, 8 and 1.

**The three mixes, checked automatically**

- [x] Every labelled beat is the beat of its bar that the reference says: first, second, third or fourth. A bar is always four beats. If a part makes this impossible, the numbers go to the owner, who decides. The item is not loosened any other way. `bachata/songs_test.py`: 396, 505 and 416 beats, all in their place.
- [x] The share of labelled beats that get the count of the reference is measured on each mix and written in `LOG.md`. There is no limit to pass in this slice. The limit is in slice 4. `bachata/songs_test.py` prints it: 88 of 396 on Me Emborrachare, 257 of 505 on Eso Es Amor, 416 of 416 on Old Town Road. Me Emborrachare read 120 of 396 until session 8, against a reference that had the short bar of its Intro last: the analysis counts that Intro in eights from its first beat, and so did the wrong reference.

**The two commercial recordings**

- [ ] By the owner's ear: a beat shown as 1 or as 5 is the first beat of a bar, wherever the song can be counted.

**The page**

- [x] Every beat shows its count, in the large view and on the song, and the count of the beat that is sounding is the largest figure on the page. `e2e/page_test.py`: the figure and its size, and the count the song says for every beat. In the large view it reads the canvas and finds something written under every beat. Which number that is, and the numbers on the song, were looked at in pictures, not by a test.
- [x] The large view shows the ocho that is sounding and stands still while it sounds. An ocho of fewer than 8 beats leaves the other places empty. `e2e/page_test.py`: which ocho is shown, and that a press on the place of a count moves to the beat with that count. Since session 7 it also reads the canvas, in light and in dark: every beat of the ocho is drawn at the place of its count, the one that is sounding in the large square, and an ocho cut to a bar leaves the places of 5 to 8 empty.
- [x] The song is in rows of four ochos, in a window 1280 pixels wide or wider. An ocho of fewer than 8 beats takes less room, and the next row starts in line again. `e2e/page_test.py`, in a window of 1280: four ochos a row, the marks 26 pixels apart.
- [x] Count 1 is told apart from the other beats by its form, not by colour alone. It is an upright bar and the others are squares. `e2e/page_test.py` reads the canvas of the song and, since session 7, the one of the large view, in light and in dark.

**Count 1 by hand**

One control, "Count 1 here". The owner added it on 2026-10-06, in session 6, with the words "one simple control, nothing more".

- [x] It makes the beat at the playing position count 1. From that beat the count runs in eights, up to the next beat set the same way or to the end of the song. Before the first one, the count is the analysis's. The ocho before it ends where it is cut, so a bar left alone there is shown as a half phrase. `web/song.test.js` and `e2e/page_test.py`.
- [x] On a beat that was set by hand the control takes it back. It then reads "Not count 1". `e2e/page_test.py`. *Proposed: without this a wrong press could not be undone.*
- [x] A beat set by hand is told apart from the other count 1s by its form: its bar has a cap across the top. `e2e/page_test.py` reads the canvas.
- [x] It is kept on the server with the song, as a time. It shows in every browser, and it survives a restart, a renaming and a new version of the analysis. `bachata/server_test.py` and `bachata/store_test.py`. Every browser: `e2e/page_test.py`, with the song open in two and opened later in a third.

**The entry, by the owner's ear**

The owner listened to 13 songs in full on 2026-10-06 and set this target the same day, in session 9: on five of them the count was four off from the start, so where the main part enters the page showed 5 and he heard 1. His marks and notes are in `fixtures/audio/by-ear.json`, which git ignores. They are for checks only: the analysis never reads them, the label files or the marks in the library.

- [x] With no mark used, count 1 falls on the owner's mark on at least 4 of these 5: Bachata Que Duele, Escalofríos, No vuelvo a caer (17.04 s and 32.16 s are equally right), the Me Emborrachare mix (count 1 at 2.28 s; the four beats before it are not judged), Sus Huellas. `bachata/entry_test.py`: 5 of 5. Four by what comes in during the first minute; the Me Emborrachare mix, where nothing comes in, by its bass.
- [x] No other song gets worse. The six songs he found right throughout keep their count; Herrera and Sin Fin keep it up to their first mark; Old Town Road stays 416 of 416 and Eso Es Amor does not go below 257 of 505. `bachata/entry_test.py`, against the count version 2 of the analysis gave, kept in `fixtures/by_ear_before.json`. *Mine: with no mark to say where a song enters, a song is judged from the first count 1 it had, which is stricter than "from the entry on".*
- [x] The analysis opens no file of the reference or of the library. `bachata/songs_test.py` and `bachata/entry_test.py` refuse an analysis that does.
- What the count shows inside an intro without percussion is not judged. Half phrases in the middle of a song are not part of this.

**What is refused, part of G7**

- [x] A count 1 that does not come from the application's own page, one for a song id that is not well formed or not in the library, a time that is not a number inside the song, and one more when a song has 200 of them. `bachata/server_test.py`.

**How these are tested**

- The bar and the measured count: `bachata/songs_test.py`, on the three mixes.
- The count from the analysis and from the beats set by hand: unit tests beside the code, in Python for the analysis and in `web/song.test.js` for the page.
- The page and the control: `e2e/page_test.py`.
- Two tests of slice 1 are reworded, because what they checked is no longer true: the one that found the marks of a row all the same distance apart and no text but the tempo and the time, and the one that found the tempo to be the largest figure.
- The checks were seen to fail. Session 6 broke the code on purpose in 25 ways, in the bar, in count 1 by hand and in the server's part of it. Two breaks were caught by nothing and one not by the test that claimed it; three tests were added or changed, and all 25 are now caught. `LOG.md` has the table.
- Session 7 took four findings of a review of that commit. Two were faults of the page and two of its checks: an assertion that could not fail, and no test that failed when the large view drew nothing. Each has a check that was seen to fail. `LOG.md`, session 7.

**Not in slice 2**

- Finding a half phrase from the sound. Session 6 tried the two-bar cycle of the harmony: it found two of three on Me Emborrachare, four of eight at most on Eso Es Amor, and one to four that are not there on Old Town Road.
- Telling the first bar of an ocho from the second. *Since session 9 the analysis does tell them, once for the whole song, by what comes in during the first minute: see "The entry, by the owner's ear" above. What follows is how the first bar is found before that.* The analysis starts the count on the first bar it hears and goes on in eights. The first bar it hears is the first whose first beat is not more than 40 dB under the level of the whole song: the tracker carries the pulse back over the silence before a song. *Proposed: the 40.* On Old Town Road and Eso Es Amor, the two mixes that start with such a bar, the owner's ear agrees with where the count then starts. The beats it puts before that bar are counted as the end of an ocho, up to 8.
- Any mark of doubt on a count.

### 3. Derecho or majao for each ocho

- [ ] It shows, for each ocho, derecho, majao or neither.
- [ ] Every ocho inside a derecho or majao section of the reference gets that label.
- [ ] No ocho inside an `other` part of the reference gets a label. *Open: which of the labels' rhythms count as `other`, and which wins when a section's rhythm and its blocks disagree. See `NEXT.md`.*

### 4. Mambo, so the full timeline

- [ ] G1, G2 and G3 hold on every fixture.
- [ ] Every labelled beat of the three mixes gets the count of the reference, half phrases included, with no beat set by hand. The reference count is described under slice 2. If a part makes this impossible, the numbers go to the owner. Moved here from slice 2 by the owner on 2026-10-06, in session 6.

### 5. The screen

- [ ] The timeline of sections is on screen while the song plays, and the playing position sits in the section that is sounding.
- [ ] G4, G6 and G8 hold.

**The redesigned page.** The owner decided on 2026-10-05 that the screen is built ahead of slices 2 to 4: first with the beats and the BPM of slice 1, then each slice puts its result in its place. The brief is in `NEXT.md`. The items come from that brief. The owner accepted them on 2026-10-05, in session 5, with one change: a mark for every beat of the whole song does not have to be on screen all the time. The item about a song of 4 minutes showing whole in a window of 1920 by 1080 is therefore gone, and the item about the large beats is new.

With what slice 1 has:

- [x] Every beat of a song has its own mark, and two neighbouring marks are at least 20 pixels apart in a window 1280 pixels wide or wider. The marks are in rows that scroll under the band above them. `e2e/page_test.py` reads the canvas, in light and in dark: the marks are 26 pixels apart in a window of 1280, and 32 in a wider one.
- [ ] The beats around the playing position are shown large, eight at a time. By the owner's eye and ear: each one can be checked against its click. *Built in session 5, where they passed a fixed line. Since slice 2 they are the ocho that is sounding and stand still, each at the place of its count: about 168 pixels apart in a window of 1920.*
- [x] The mark of the beat that is sounding is lit while it sounds. With the click on, the lit mark and the click are the same beat. `e2e/page_test.py`, in Chrome and Firefox, with sound.
- [x] Nothing is shown that neither an analysis nor the user has produced: before slice 4 no section. `e2e/page_test.py`: the count on screen is the one the server has, changed only by the beats set by hand, and the only text where the song is shown is the count, the tempo and the time. Reworded in session 6, when slice 2 put the count and the ochos on screen.
- [x] A range of the song can be marked and replays in a loop until the loop is switched off. On every pass each beat inside it gets one click, at its own time. `e2e/page_test.py`, with sound, and `web/song.test.js`. The loop is switched off and on while the song plays as well as while it is paused: until session 7 the switch did nothing during playback, and no test pressed it then.
- [x] A marked range can be taken away again, whole or with one end only, and while the song goes round it: the song then plays on. Switching the loop off keeps the range. `e2e/page_test.py`, which also reads the canvas. Added by the owner on 2026-10-06, in session 6, after using the page.
- [x] Every song has an address of its own, `/?song=` and its id. The address bar shows it while the song is open, and the plain address when none is. Loaded again, or opened in another browser, the page opens that song and sends nothing. An address that names a song the library does not have says so. `e2e/page_test.py`, `web/song.test.js` and `bachata/server_test.py`. Added by the owner on 2026-10-06, in session 6.
- [x] A song can be renamed from the page, and the new name shows in every browser. The server treats a renaming as it treats a deletion and a name: it must come from the application's own page, and the name is at most 200 characters. Part of G7. `e2e/page_test.py`, `bachata/server_test.py` and `bachata/store_test.py`.
- [x] Playing, pausing, moving the position, the loop, the click switch, count 1, and opening, renaming and deleting a song can all be done from the keyboard, with the focus visible. `e2e/page_test.py`: Space, the arrows, the arrows with Shift for an ocho, the loop and a renaming are done with keys alone, and Tab reaches every control with a ring on each.
- [ ] Nothing is told by colour alone: two marks that differ in colour also differ in form, in position or in name. By the owner's eye. *Built in session 5: the lit mark is a larger square in the opposite of its ground, a marked range has a bar at each end, and the open song and a failed one say so in words.*
- [x] A message appears beside what caused it, and the list shows which song is open. `e2e/page_test.py`.
- [x] The page has a light and a dark ground, and takes the one the system is set to. In both, text has a contrast of 4.5 to 1 or more against what it is on, and marks and focus rings 3 to 1 or more. `web/contrast.test.js`, and `e2e/page_test.py` for the change from one to the other. Added in session 5, by the owner's decision that the page gets both. A large beat that has sounded is a mark too. It was drawn at 1.8 to 1 against the band until session 7, at a strength set in the drawing code, where the test of the colours could not see it. Its colour is now in the style sheet with the others, and `e2e/page_test.py` measures it on the canvas.
- [ ] By the owner's eye: from three metres, on the screen used for practising, the largest figure and the name beside it can be read.
- [x] By the owner: one of the three visual directions is chosen, and the other two are deleted with the switch between them. The owner chose Terminal signs on 2026-10-05, in session 5. A search of `web/`, `bachata/` and `e2e/` finds no name of the other two, of their typefaces or of the switch.

With later slices:

- [x] From slice 2: the count is the largest figure while a song plays, and count 1 and the start of each ocho are told apart from the other beats. `e2e/page_test.py`; the items are under slice 2.
- [ ] From slice 4: pressing a section plays from its first beat, and the page says which section comes next and in how many ochos.
- [ ] From slice 4: a section can be replayed in a loop by itself, from its first beat to its last, without the change into the next one. Until sections exist, the loop is a range marked by hand. Decided by the owner on 2026-10-05, in session 5.

**How the page is tested.** As in slice 1. The end-to-end tests add these flows: the lit beat against the clicks, a loop, the marks in light and in dark, a renaming in the row and in the top bar, the keyboard, a song that cannot be opened, and a song deleted in another browser. The beats are drawn on two canvases; the page says in attributes of those canvases which beat is lit, which ocho is shown, where the mark of every beat is, its count, and which beats were set by hand, and the tests read them. Since slice 2 they add the count and the rows of ochos, and count 1 set by hand in three browsers. Since session 7 they add the loop switched off and on while the song plays, and one test reads the canvas of the large view itself.
