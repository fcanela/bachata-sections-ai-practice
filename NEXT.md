# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-06, session 8)

Slice 2 is built, in the shape the owner gave it in session 6, and the owner has used it. Every check a program can run passes. What is open is the owner's: the checks of slice 1, one by-ear item of slice 2, and the proposals listed below.

- **A skill breaks the code on purpose**, since session 8: `.claude/skills/break-on-purpose/`. Asked to break a part and see its checks fail, it breaks every claim of the part once, then what no claim speaks of, and repairs each weak check it finds.
  - It was tried on three tasks before the owner's last changes to it, and not since. `LOG.md`, session 8.
  - It is committed with the project: `.gitignore` keeps `.claude/` out except that one folder.
  - The program and its tests did not change in session 8.

- **The reference changed on 2026-10-06, outside git.** The owner's label files now carry the site's order of phrases, as blocks, for every section with a phrase shorter than an ocho.
  - The Intro of Me Emborrachare has its short bar first. The old reference had it last, by the last-bar rule, and was wrong: the owner listened.
  - The measured count is 88 of 396 on Me Emborrachare, where it was 120. Eso Es Amor is still 257 of 505 and Old Town Road 416 of 416. The analysis did not change: it lost the 32 beats it had only shared with the wrong reference.
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
- **The analysis** now keeps the place of every beat in its bar, and a count from 1 to 8 that runs in eights from the first bar that is not silence. It is version 2. The five songs in `data/` have been analysed again: that happened by itself when the owner started the program.
- **The page** shows the count as the largest figure, with the tempo small beside the time. The large view is the ocho that is sounding, standing still, each beat at the place of its count. The song is in rows of four ochos, with the count under every mark. Count 1 is an upright bar.
- **"Count 1 here"**, in the transport bar, makes the beat at the playing position count 1. From there the count runs in eights. On a beat set this way the control reads "Not count 1" and takes it back. A beat set by hand has a cap across its bar.
- The arrows with Shift move the position by an ocho.
- The server has two new requests, `PUT` and `DELETE /api/songs/<id>/ones?at=<seconds>`.
- **The count is right only where no half phrase has passed.** On Me Emborrachare the Intro starts with one: the count is four off from the fifth beat of the song, at 0:02, to the end of the Breakdown, at 2:31. "Count 1 here" on those two beats puts all 396 right: that is what the control is for. *Corrected in session 8. This said "from 0:17, the end of the Intro", by a reference that had the short bar last.*

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
- **To test it:** `uv run pytest`. It runs the unit tests, the song checks and the flows through the page, 182 tests in about 4 and a half minutes.
- **A program that is running shows the page it started with.** After a change to the page or to the server, stop it and start it again.
- **On a new machine, once:**
  - `uv sync`
  - `uv run python scripts/fetch_model.py`, which downloads the Beat This model into `models/` and checks its hash.
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
- Up close: every beat is its own mark. Count 1 and the start of each ocho stand apart, so a click can be checked against its mark.
- Nothing is drawn that an analysis has not produced.

**Direction**

- Three worlds were built as real pages on one layout, with a temporary switch between them. The owner chose **Terminal signs** in session 5. The other two and the switch are deleted.
- The page has a light and a dark ground. The owner's decision of session 5.
- A world supplies four things: typeface, colours, density and one signature move. The layout and the controls are the same in all three, and the controls are ordinary web controls.
  - **Terminal signs, the one that stays.** Yellow panels and black type, after airport sign systems. Where the song is hangs as a sign band: the section's mark in a black square, its name, the count. A second band says what is ahead and how far. Rhythms differ by their mark, not by colour.
  - The two that went were Dominó, a green table with bone tiles and black pips, and The counts sheet, quadrille paper with four pen colours.
- The layout's own idea: the song is wrapped into rows instead of stretched on one line, so a beat gets about 30 pixels instead of 2.

**Layout and interaction**

- **Top bar:** the application's name, the open song's name, Add a song.
- **Left rail:** the library. Each row shows name, length, state, and which song is open. A message appears where its cause is.
- **Now band**, pinned above the song: the count as the largest thing on the screen, the section name second, BPM and time small. Beside the count, the ocho that is sounding, drawn large, its beats lighting on the beat.
- **The song:** every beat, in rows of four ochos, with each row's start time and the section brackets in the margin. It scrolls under the pinned band. It does not have to be whole on screen: the owner's change of session 5.
- **Transport bar** at the bottom: play and pause, position, loop, the click switch.
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
7. **Listen to the half phrases the owner has not heard**, and say for each whether the short bar is where the site puts it. The Intro of Me Emborrachare is answered: the owner heard it on 2026-10-06, and the short bar is first. Left: on Me Emborrachare the Breakdown, short bar last, and the Ending. On Eso Es Amor the Intro, both Pre Choruses and the Bridge, short bar last in each. Since session 8 these come from the site's blocks, not from a rule of ours. Also whether the first labelled beat of Me Emborrachare is a count 1: for the other two mixes the owner confirmed it on 2026-10-06. The owner's note on intros and endings, under "For later slices", bears on three of the seven, and on the Outro of Eso Es Amor.

If the click sounds loose rather than wrong: beat times come in steps of 20 ms, because the tracker looks at the song 50 times a second. Moving each beat onto the nearest attack of the sound is the next thing to try. It was not built, because only an ear can say whether it is needed.

### Slice 2, as built, and what it leaves to the owner

- **By ear, the two commercial recordings:** a beat shown as 1 or as 5 is the first beat of a bar, wherever the song can be counted.
- **By eye:** count 1 against the other beats, and a count 1 set by hand against the others, in the large view and on the song. Since session 7 also the large beats that have sounded, in their new colour, against the ones to come.
- **The proposals in `ACCEPTANCE.md`, under slice 2:** that the first labelled beat of Me Emborrachare is count 1, the 40 dB under which a bar is silence, the half phrases the owner has not heard (check 7 above), and that the control takes a count 1 back.
- **The control, in use.** It is one button and nothing more, as asked. Whether a song with several half phrases is quick enough to put right with it is the owner's to say after using it.

### Then slice 3

**Derecho or majao for each ocho.** Nothing of it is decided. It starts with a round of questions, as slices 1 and 2 did. Three questions are already open under "For later slices": mambo in the labels, a section whose blocks disagree with it, and which rhythms count as `other`.

## Rules that are easy to break

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
- **The count is put together on the page**, in `countsWith` of `web/song.js`, from the analysis's count and the beats set by hand. The server keeps those as times, with the song and not with the result, so a new version of the analysis leaves them alone.
- **A bar is four beats.** The DBN is given bars of four only.
- **Every file of the page is named in `PAGE_FILES`**, in `bachata/server.py`, and read once when the program starts. A new file needs an entry, and a changed file needs the program started again.
- **The tests find a beat through what the canvases say about themselves**: `data-lit` and `data-ocho` on the large beats, and on the song `data-marks`, the middle of every mark, `data-counts` and `data-by-hand`. A change to how the song is laid out keeps those attributes true. One test reads the canvas of the large view without them, `LARGE` in `e2e/page_test.py`: it takes an eighth of the width for the place of each count.
- **The colours of the page are plain six-digit values on `:root`** in `web/style.css`, light first and dark after. `web/contrast.test.js` reads them from there. A colour or a strength that is set in `web/draw.js` is one that test cannot see: the large beats that have sounded were drawn at 28% there until session 7, at 1.8 to 1.
- **A loop is played by the sound itself**, through the loop points of the audio source, and its clicks come from `clicksUntil` in `web/song.js`. A loop made by stopping and starting the sound would have a gap, and its clicks would drift.
- **Product facts go in `BRIEF.md`, never in `PRODUCT.md`.** `PRODUCT.md` only points at the brief. The design plugin's `init` command offers to fill it in; a new fact goes into the brief instead.
- **In the session's sandbox:**
  - `uv` needs `UV_CACHE_DIR` set to a writable folder, and each network host has to be allowed for the command that needs it.
  - Chrome does not start. Playwright's Firefox starts but plays nothing. `uv run pytest` then skips those tests and says so.
  - Playwright's Firefox does draw the page, so a screenshot that needs no sound can be taken inside the sandbox.
  - The whole run needs a command outside the sandbox, which the owner allows one at a time: `TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8081 .venv/bin/python -m pytest`. `TMPDIR` must be a short path, or Chrome dies with "Socket path too long".
  - When the owner's own program is on 8081, every test of the page fails at once with "Address already in use". Session 6 then used `BACHATA_TEST_PORT=8083` and left the owner's program alone. On 2026-10-06 one was on 8081, started that morning, and another on 8082, started the day before.

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

- **At 1280 wide the transport bar takes two lines**: the click switch goes under the other controls.
- **A song longer than about 3 minutes no longer shows whole at 1920 by 1080.** A row is 50 pixels high, for the count under each mark.
- **Nothing checks by a test which number is drawn under a mark.** In the large view a test finds something written under every beat, and the empty places of a short ocho, since session 7. The numbers on the song were looked at in pictures.
- **A change of count 1 in another browser arrives with the list**, so up to two seconds later.
- **The count starts on the first bar that is not silence**, 40 dB under the level of the song. A song that fades in over several bars may start its count late; none of the 101 songs analysed in session 6 does.

- **Back does not go from song to song.** Opening a song rewrites the address in place and adds nothing to the browser's history. The owner asked for reloading and sharing; whether Back should step through the songs is the owner's to say.
- **An address that names a song still being analysed** shows the page as with no song, and opens the song when it is ready.
- **"Clear" is one more control in the transport bar.** Its name and its place are the session's choice.
- **Opus is decoded by the browser**, as mp3 and m4a are. Checked in Chrome and in Playwright's Firefox, with files made by `ffmpeg`, and the type and tags of the 106 files of the owner's folder were read by the page's own code. None of those 106 was uploaded.

**For later slices**

- **The owner's notes of 2026-10-06, after using slice 2. None of it is built.**
  - Extra bars are not detected, so 1 and 5 swap. They frequently come after 4 phrases, and beat information alone is not enough: the energy of the instruments has to be correlated.
  - In intros and endings a section can start on an unexpected count or be an isolated bar. That is a way to make sense of the intro or ending, not an extra bar.
  - The count 1 the owner sets by hand should later serve as feedback: reference data to measure and improve the analysis.
  - The lower view could show bars instead of every beat. Not critical.
  - The beats in the silence before the music are shown with counts 5 to 8. They could be shown without a count.
- **What those notes touch, as the session reads them:**
  - The second note is about the reference count. Its rules, in `ACCEPTANCE.md` under slice 2, give an intro or an ending whole ochos from its start and count what is left over at its end: the Intro of 36 beats and the Ending of 4 on Me Emborrachare, the Intro of 20 and the Outro of 9 on Eso Es Amor. How those four are counted is to be settled with check 7, before slice 4 makes the count strict.
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
