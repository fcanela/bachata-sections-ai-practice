# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-05, after session 3)

Slice 1 is built: beats and tempo, the upload and the library of remembered songs. Every item of it that a program can check is ticked in `ACCEPTANCE.md`. What is left of slice 1 is the owner's: the checks by ear and a few confirmations, listed below.

- Session 3 did the twelve steps of the previous `NEXT.md`, in order. The measurements and the decisions are in `LOG.md`, session 3.
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

## Next: the owner's checks, then slice 2

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

**Then slice 2: the grid of ochos.**

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
- **In the session's sandbox:**
  - `uv` needs `UV_CACHE_DIR` set to a writable folder, and each network host has to be allowed for the command that needs it.
  - Chrome does not start. Playwright's Firefox starts but plays nothing. `uv run pytest` then skips those tests and says so.
  - The whole run needs a command outside the sandbox, which the owner allows one at a time: `TMPDIR=/tmp/claude-1000/e2e BACHATA_TEST_PORT=8081 .venv/bin/python -m pytest`. `TMPDIR` must be a short path, or Chrome dies with "Socket path too long".

## Open

**For slice 1**

- **The owner's checks and confirmations** above.
- **The names in the library are only as good as the tags.** The reference files give "track0", "mix" and "original". Whether a song can be renamed is not decided; a title tag set when a mix is made would be enough for these.
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
- **The list of remembered songs gets its real screen in slice 5**, where G4 is checked. The strip of slice 1 has about one tick every 2 pixels for a whole song, which shows that the beats are there and little more.
- **No measure for "fluid".**
- **Deployment for coworkers** is out of scope. When it comes:
  - a container;
  - an nginx body limit far above the default, since a 4-minute song is about 42 MB of samples and a 15-minute one about 159 MB;
  - the library is shared, so everyone who can log in can play and delete every song;
  - the program answers only to `127.0.0.1` and `localhost`, and takes a request as its own page's only over plain `http`: both have to learn the public name and `https`;
  - the page takes the fingerprint of a file with a browser function that works only on `https` or on localhost.

**Housekeeping**

- **`.claude/settings.json` is not committed.** It holds paths from the owner's machine.
- **Not in git, and each rebuilt by one command:** `.venv/`, `models/`, `.playwright/`. `data/` is the library and is not rebuilt by anything.
