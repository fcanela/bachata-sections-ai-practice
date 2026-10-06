# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-06, session 6)

Slice 2 is specified and not built. Session 6 asked the owner five questions, ran an experiment on the three mixes and on 96 songs without labels, and the owner set the shape of the slice from its result. `ACCEPTANCE.md` has the items under slice 2, and `LOG.md`, session 6, the figures and the decisions.

Before that, in session 5:

The redesigned page is built, with what slice 1 has. The owner chose its design, Terminal signs, among three, and the other two are deleted. Every check a program can run passes. The owner's checks of slice 1 are still open, listed below.

- Session 5 built the page from the brief below. What was run and decided is in `LOG.md`, session 5.
- The page now has a top bar, the library in a left rail, a band that says where the song is, every beat of the song in rows, and a transport bar.
  - The band shows the BPM as the largest figure, with the time small under it, and beside it the eight beats around the playing position. They slide past a fixed line and the one that crosses it lights.
  - A press on a beat moves the position there. A drag across beats marks a loop. "Start here" and "End here" mark its two ends at the playing position.
  - A song is renamed in its row or in the top bar. Space plays and pauses, and the arrows move the position by a beat.
- The server has one new request, `PATCH /api/songs/<id>?name=…`, for a renaming.
- The page shows no count, no grouping and no section: those come with slices 2 to 4.
- It has a light and a dark ground and takes the one the system is set to. It has no control for that.
- The program is a Python one. The Node program is gone.
- **To run it:** `uv run python -m bachata`, then http://127.0.0.1:8080. `PORT` changes the port and `BACHATA_DATA` the folder of the library. Sessions 3 and 5 used port 8081 for everything they started, as the owner asked in session 3.
- **To test it:** `uv run pytest`. It runs the unit tests, the song checks and the flows through the page, in a little over 3 minutes.
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

## Next: the owner's checks, then slice 2

### Left open by the redesign

- **`DESIGN.md`.** The design plugin ends a build by writing one from the finished page: the colours, the typeface and the rules of the design, for later design work. It is a new top-level file, so by the owner's rule on existing files it is asked first. Until then the design is described in `BRIEF.md`, under "The interface", and its values are in `web/style.css`.
- **A control for light and dark.** The page follows the system. A control on the page is the owner's to ask for.
- **The layout.** The owner found that the three designs looked like skins of one layout. That is what the brief of session 4 asked for, and what the plugin does for a tool: a design gives the typeface, the colours, the density and one move of its own, and the layout stays. The plugin has a separate round that keeps the design and proposes three arrangements of the screen. It was offered and not taken now. It is worth more once slice 2 has the count and the ochos on screen.
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
6. Answered on 2026-10-06: a section starts on count 1. It follows from the owner's rule that a half phrase is the last bar of its section.
7. **Listen to the seven half phrases the rule placed**, and say for each whether the extra bar is the last of its section. On Me Emborrachare: the Intro, the Breakdown and the Ending. On Eso Es Amor: the Intro, both Pre Choruses and the Bridge. Also whether the first labelled beat of each mix is a count 1.

If the click sounds loose rather than wrong: beat times come in steps of 20 ms, because the tracker looks at the song 50 times a second. Moving each beat onto the nearest attack of the sound is the next thing to try. It was not built, because only an ear can say whether it is needed.

### Then slice 2

**The grid of ochos**, as the owner shaped it on 2026-10-06.

- **Strict: the bar.** Every labelled beat of the three mixes is the first, second, third or fourth of its bar. The DBN already says so for every beat, and the analysis throws it away today. Session 6 measured it right on all 1,317 labelled beats.
- **Shown and measured: the count from 1 to 8.** The analysis starts the count on the first bar it hears and goes on in eights. It does not look for half phrases. How many labelled beats get the count of the reference is measured and logged, with no limit. The limit is in slice 4.
- **By hand: "Count 1 here".** One control. From the beat at the playing position the count runs in eights. On a beat set by hand, the control takes it back.
- **The page:** the count takes the place of the large figure and the tempo goes small beside the time. The large view shows the ocho that is sounding and stands still. The song is in rows of four ochos, and count 1 differs from the other beats by its form.
- A bar is always four beats: the DBN is no longer allowed bars of three.
- `ANALYSIS_VERSION` goes to 2. Every stored song is then analysed again by itself when the program starts, about 5 seconds a song.

## Rules that are easy to break

- **The page plays the samples the server stored**, never an `<audio>` element on the original file. Otherwise the click drifts from the sound by whatever the browser trims at the start of the file.
- **The page decodes a file at a fixed 44.1 kHz, in stereo**, and sends the rate and the length. An ordinary audio context would resample to the machine's own rate without saying so. The server mixes down and resamples for the analysis.
- **The server never reads a media file made elsewhere.** It receives plain samples, stores them as they are and sends them back as they are. No FLAC: Chrome does not decode it back to the same samples.
- **Every limit the page checks, the server checks again** on what it receives. A page's check can be bypassed.
- **The analysis must not assume one tempo for the whole song.** It would pass all five songs and be wrong.
- **The tempo range of the analysis must stay narrower than a factor of two.** That is what keeps a half-time part at the count of the song.
- **The analysis and its checks get the mix only.** The instrument tracks are for understanding a failure and for measuring the reference.
- **The every-beat item is not loosened.** If a part with no clear pulse makes it impossible, the numbers go to the owner.
- **The window is 90 ms.** It grows again only if the measurements show it must, up to 120 ms, with the reason logged.
- **The page has no inline script, no inline style and no `eval`.** Its content security policy blocks all three, and a test tool that evaluates a string inside the page is blocked with them.
- **The tests of the security headers carry their own list.** A test that reads the list from the program passes when a header is removed.
- **The page draws nothing an analysis has not produced.** Before slice 2 there is no count and no grouping of beats on screen, and before slice 4 no section. Until then a row of the song is a line wrap and nothing more.
- **Every file of the page is named in `PAGE_FILES`**, in `bachata/server.py`, and read once when the program starts. A new file needs an entry, and a changed file needs the program started again.
- **The tests find a beat through what the canvases say about themselves**: `data-lit` on the large beats, and the place of the marks on the song. A change to how the song is laid out keeps those attributes true.
- **The colours of the page are plain six-digit values on `:root`** in `web/style.css`, light first and dark after. `web/contrast.test.js` reads them from there.
- **A loop is played by the sound itself**, through the loop points of the audio source, and its clicks come from `clicksUntil` in `web/song.js`. A loop made by stopping and starting the sound would have a gap, and its clicks would drift.
- **Product facts go in `BRIEF.md`, never in `PRODUCT.md`.** `PRODUCT.md` only points at the brief. The design plugin's `init` command offers to fill it in; a new fact goes into the brief instead.
- **In the session's sandbox:**
  - `uv` needs `UV_CACHE_DIR` set to a writable folder, and each network host has to be allowed for the command that needs it.
  - Chrome does not start. Playwright's Firefox starts but plays nothing. `uv run pytest` then skips those tests and says so.
  - Playwright's Firefox does draw the page, so a screenshot that needs no sound can be taken inside the sandbox.
  - The whole run needs a command outside the sandbox, which the owner allows one at a time: `TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8081 .venv/bin/python -m pytest`. `TMPDIR` must be a short path, or Chrome dies with "Socket path too long".

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

**For later slices**

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
- **The last three labelled beats of Me Emborrachare have no percussion.** The analysis carries the pulse over them. Slice 2 will meet that ending again when it counts.
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
