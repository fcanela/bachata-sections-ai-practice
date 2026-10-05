# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-05, after session 4)

Slice 1 is built: beats and tempo, the upload and the library of remembered songs. Every item of it that a program can check is ticked in `ACCEPTANCE.md`. What is left of slice 1 is the owner's: the checks by ear and a few confirmations, listed below.

- Session 3 did the twelve steps of the previous `NEXT.md`, in order. The measurements and the decisions are in `LOG.md`, session 3.
- Session 4 changed no code. It ran two commands of the Impeccable design plugin, `init` and `shape`.
  - The owner said who the application is for. The answers are in `BRIEF.md`, under "Who it is for" and "The interface". `PRODUCT.md` is new: a pointer to the brief for the plugin.
  - The owner asked for the page to be redesigned whole and confirmed a brief for it, which is below. Three visual directions are to be built and compared.
- The program is a Python one. The Node program is gone.
- **To run it:** `uv run python -m bachata`, then http://127.0.0.1:8080. `PORT` changes the port and `BACHATA_DATA` the folder of the library. Session 3 used port 8081 for everything it started, as the owner asked.
- **To test it:** `uv run pytest`. It runs the unit tests, the song checks and the flows through the page, in under 2 minutes.
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

## Next: the redesigned page, then the owner's checks, then slice 2

The owner decided in session 4 that the page is redesigned whole, and that the new page is built next, with what slice 1 has. The owner's checks of slice 1 are listed after it, because the owner found the strip unreadable for checking a beat. They can also be done before it, by ear alone.

### The redesigned page

This is the brief the owner confirmed on 2026-10-05. Its checks are in `ACCEPTANCE.md`, under slice 5, marked *proposed*. The answers it comes from are in `LOG.md`, session 4.

**Who and what for**

- A dancer learning musicality, at the desk or three metres away on their feet. One screen serves both. It is a tool to operate while a song plays.
- For now the same person also checks the analysis by eye and ear.

**What it must do**

- From three metres: say where the song is now, the section and the count, 1 to 8.
- Second, what comes next and in how many ochos. Third, the shape of the whole song.
- Up close: every beat is its own mark. Count 1 and the start of each ocho stand apart, so a click can be checked against its mark.
- Nothing is drawn that an analysis has not produced.

**Direction**

- Three worlds are built as real pages on one layout. The owner judges them with a song playing, at the desk and from three metres. Two are then deleted. A temporary switch on the page changes world, and goes with them.
- A world supplies four things: typeface, colours, density and one signature move. The layout and the controls are the same in all three, and the controls are ordinary web controls.
  - **Dominó.** A deep green table, bone tiles, black pips. An ocho is a tile of two halves of four, and a half phrase is half a tile. A rhythm is told by the form of its pips (solid, ringed, doubled), then by colour.
  - **The counts sheet.** White quadrille paper and four pen colours. The beats are the written figures 1 to 8, one group per ocho, the playing count inked heavy. Sections are pen marks of different forms.
  - **Terminal signs.** Yellow panels and black type, after airport sign systems. Where the song is hangs as a sign band: the section's mark in a black square, its name, the count. A second band says what is ahead and how far. Rhythms differ by their mark, not by colour.
- The layout's own idea: the song is wrapped into rows instead of stretched on one line, so a beat gets about 30 pixels instead of 2.

**Layout and interaction**

- **Top bar:** the application's name, the open song's name, Add a song.
- **Left rail:** the library. Each row shows name, length, state, and which song is open. A message appears where its cause is.
- **Now band**, pinned above the song: the count as the largest thing on the screen, the section name second, BPM and time small. Beside the count, the ocho that is sounding, drawn large, its beats lighting on the beat.
- **The song:** every beat, in rows of four ochos, with each row's start time and the section brackets in the margin. The target is that a song of normal length fits a screen of 1920 by 1080 without scrolling. A longer one scrolls under the pinned band.
- **Transport bar** at the bottom: play and pause, position, loop, the click switch.
- Pressing a beat moves the position there. Pressing a section plays from its first beat. A loop is a range marked on the song that repeats without a gap, the click staying on the beat.
- A song is renamed in place, in the top bar or in its row.
- Keyboard: everything is reachable by Tab with a visible focus. Space plays and pauses. The arrow keys move the position by a beat, and by an ocho or a section once those exist.

**States and ranges**

- **Built next, with what slice 1 has:** beats and BPM only. The largest figure is the BPM, and the large view is the eight beats around the position, unnumbered and ungrouped. Rows are a line wrap with no meaning. No tile, no written count and no "ahead" band yet.
- **Later slices:** slice 2 puts the count in the large place and groups the beats into ochos. Slices 3 and 4 add each ocho's rhythm and the sections, and with them the jump to a section.
- A part that is none of the three rhythms is drawn plain and has no name. It never gets a fourth colour.
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

**Open, for the owner**

1. Whether mambo is a rhythm or a part of the song. It decides how many kinds the legend has. It is the same question as under "Open" below.
2. Whether each world has one ground, or a light and a dark one. Proposed: one, picked for an evening room with the screen three metres away.
3. What "replay the change between two sections" spans. It can wait for slice 4.

**To start the build**

- Ask the design plugin for the page with this section as the brief. It reads `PRODUCT.md`, which sends it to `BRIEF.md`; it has to be pointed here as well.
- The plugin writes the chosen direction into a file of its own under `.impeccable/` before any code. Git ignores that folder, so what the plugin keeps there is a working copy and not part of the project's record. Whether the direction is also written here is the owner's to say, by the rule on existing files.
- The key of the roll that dealt the directions is `6e38c9ca`. The plugin asks for it. In its terms Dominó is the assigned direction, The counts sheet is its own pick, and Terminal signs is the catalogue direction `wayfinding-cartography-signage-terminal-yellow-wayfinding`.
- The plugin reviews a finished page from screenshots. Those need a browser, so commands outside the sandbox.
- The ticked item of slice 1 about the strip is reworded and checked again when the page is rebuilt, as the setup items were in session 3.

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
6. **Say whether "the items marked proposed are accepted" also covered the item of slice 2**: "a section always starts on count 1". Session 3 applied it to the two numbers of slice 1 only.

If the click sounds loose rather than wrong: beat times come in steps of 20 ms, because the tracker looks at the song 50 times a second. Moving each beat onto the nearest attack of the sound is the next thing to try. It was not built, because only an ear can say whether it is needed.

### Then slice 2

**The grid of ochos.**

- It starts with a round of questions to the owner, as slice 1 did in session 2. Nothing of it is decided.
- Two things are already at hand and have not been evaluated:
  - Beat This also rates every moment as a downbeat or not.
  - The DBN gives each beat its place in the bar, 1 to 4 or 1 to 3. The analysis throws it away today.
- A bar is four beats and an ocho is two bars. Neither of the two knows about ochos or half phrases.
- A change of the analysis raises `ANALYSIS_VERSION`, and every stored song is then analysed again by itself.

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
- **Product facts go in `BRIEF.md`, never in `PRODUCT.md`.** `PRODUCT.md` only points at the brief. The design plugin's `init` command offers to fill it in; a new fact goes into the brief instead.
- **In the session's sandbox:**
  - `uv` needs `UV_CACHE_DIR` set to a writable folder, and each network host has to be allowed for the command that needs it.
  - Chrome does not start. Playwright's Firefox starts but plays nothing. `uv run pytest` then skips those tests and says so.
  - The whole run needs a command outside the sandbox, which the owner allows one at a time: `TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8081 .venv/bin/python -m pytest`. `TMPDIR` must be a short path, or Chrome dies with "Socket path too long".

## Open

**For slice 1**

- **The owner's checks and confirmations** above.
- **The names in the library are only as good as the tags.** The reference files give "track0", "mix" and "original". Renaming a song is now part of the redesigned page, by the owner's decision in session 4.
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

- **Mambo.** The brief names it as one of three rhythms, and the owner confirms that. The labels treat it as a part of the song, like Verse or Chorus, whose rhythm is majao or derecho. No label has mambo as a rhythm, so G1 has nothing to compare mambo against. Settle before slice 3.
- **When a section's rhythm and its blocks disagree, which wins?** On Me Emborrachare the Bridge is labelled Derecho, and its two blocks are `-` and Majao.
- **Which rhythms count as `other`?** The labels also have Urban, Trap, Dembow, `-` and none.
- **A section's `end_s` in the labels is the start of the next section.** G2 speaks of the last beat, which is one beat earlier.
- **The assumption that a section always starts on count 1** is still a proposal, unless the owner's answer to check 6 says otherwise.
- **The last three labelled beats of Me Emborrachare have no percussion.** The analysis carries the pulse over them. Slice 2 will meet that ending again when it counts.
- **Lining up the labels with the commercial recordings.** The full Me Emborracharé is 44 s longer than the mix and differs in places.
- **The screen of slice 5 is built early**, with what slice 1 has, and G4 is still checked in slice 5. The strip of slice 1 has about one tick every 2 pixels for a whole song, which is why the owner could not check a beat on it.
- **Which of the three visual directions stays** is the owner's choice, after using them. No `DESIGN.md` exists. The plugin writes one from the finished page, which is another file to weigh against the owner's rule on existing files.
- **The design plugin's live mode is not set up.** It puts a script of its own into the page, which the page's content security policy blocks. Allowing it is the owner's decision.
- **No measure for "fluid".**
- **Deployment for coworkers** is out of scope. When it comes:
  - a container;
  - an nginx body limit far above the default, since a 4-minute song is about 42 MB of samples and a 15-minute one about 159 MB;
  - the library is shared, so everyone who can log in can play and delete every song;
  - the program answers only to `127.0.0.1` and `localhost`, and takes a request as its own page's only over plain `http`: both have to learn the public name and `https`;
  - the page takes the fingerprint of a file with a browser function that works only on `https` or on localhost.

**Housekeeping**

- **`.claude/` and `.impeccable/` are ignored by git**, on the owner's instruction in session 4. The first holds Claude Code's settings, with paths from the owner's machine. The second is where the design plugin keeps its working files; it does not exist yet.
- **Not in git, and each rebuilt by one command:** `.venv/`, `models/`, `.playwright/`. `data/` is the library and is not rebuilt by anything.
