# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-05, after session 2)

The setup is done. No feature exists.

- Session 2 was questions and answers with the owner about slice 1: beats and tempo first, then the upload and the library of remembered songs. It changed the four docs and no code.
- The decisions and the measurements behind them are in `LOG.md`, session 2. What slice 1 must do is in `ACCEPTANCE.md`.
- The program is still the Node one of session 1: `npm start` serves one page at http://127.0.0.1:8080 and `npm test` runs two checks. Slice 1 replaces it.
- **The owner said: update the docs, do not start implementing.** Begin slice 1 only when the owner says so.

## Next: build slice 1

The beats come first, because they are the risky part. The library comes second. In this order.

**Beats and tempo**

1. **Put the material in place.**
   - Read `fixtures/audio/README.md` first. The owner regenerates files in that folder from another session; the Me Emborrachare mix changed during session 2.
   - Copy the two commercial recordings from the owner's downloads folder into the ignored folder, as `fixtures/audio/dev/meemborrachare/original.mp3` and `fixtures/audio/dev/elperdedor/original.mp3`. Their sha256 are in `LOG.md`.
2. **Start the Python project.**
   - `uv`, a pinned Python version and a lockfile. CPU-only torch.
   - Fetch the Beat This model once from its authors' release and record its hash. The running application uses no network.
   - Log every download in `LOG.md` with its size.
3. **Replace the Node program with a Python one**, with Starlette and uvicorn.
   - It keeps what the Node one does: one page, 127.0.0.1 only, 404 for everything else, the security headers.
   - Reword the three Setup items in `ACCEPTANCE.md` and check them again.
4. **Rework the reference.**
   - Remove `fixtures/labels/` and `fixtures/template.json`. The validator checks the site's label format.
   - Write the script that measures the first beat of each mix on its percussion. It writes the time into `labels.json`, beside the sha256 of the mix.
5. **Compare the trackers** on the five songs: Beat This full and small, madmom, and librosa as a floor. Drop any that does not install within 30 minutes. Put the table in `LOG.md`.
6. **Write the analysis and the song checks** of `ACCEPTANCE.md`. Measure the analysis time and log it.

**The library**

7. **Write the store.**
   - One data folder, `data/`, ignored by git, with its path changeable by one setting.
   - For each song: the sound, the results with the version of the analysis that made them, the name and the state.
   - File names on disk come from the song's id.
8. **Write the queue.**
   - One song at a time, in the order they arrived. It survives a restart.
   - A song whose analysis fails is marked failed, and the next one runs.
   - A result from an older version of the analysis sends its song back to the queue.
9. **Write the addresses the page talks to**: is this id known, upload, the list, a song's sound and results, delete.
   - Every one that changes the library refuses a request that is not from the application's own page.
   - Unit tests for every refusal listed in `ACCEPTANCE.md`.
10. **Write the page.**
    - Picking a file: check the type, take the fingerprint, ask the server whether it is known. If it is not: decode, check the length, read the name from the tags, send.
    - The list, with each song's state and a delete button with one confirmation.
    - Opening a song: fetch the stored sound, play it, and show the strip, the marker, the BPM at the playing position and the click.
    - Evaluate showing beats as they are found, to shorten the wait.
11. **Write the end-to-end tests** for the flows listed in `ACCEPTANCE.md`.
12. **Hand the owner's checks to the owner**: the click on the three mixes, and the two commercial recordings.

## Rules from session 2 that are easy to break

- **The page plays the sound the server stored**, or the very samples it just sent, never an `<audio>` element on the original file. Otherwise the click drifts from the sound by whatever the browser trims at the start of the file.
- **The page decodes at a fixed 44.1 kHz, in stereo**, and sends the rate and the length. An ordinary audio context would resample to the machine's own rate without saying so. The server mixes down and resamples for the analysis.
- **The server never reads a media file made elsewhere.** It receives plain samples and only packs and unpacks its own stored sound. That is why the file type can only be checked by the page.
- **Every limit the page checks, the server checks again** on the samples it receives. A page's check can be bypassed.
- **The tracker must not assume one tempo for the whole song.** It would pass all five songs and be wrong.
- **The analysis and its checks get the mix only.** The instrument tracks are for understanding a failure and for measuring the reference.
- **The every-beat item is not loosened.** If a part with no clear pulse makes it impossible, the numbers go to the owner.
- **The window stays at 70 ms** unless the measurements show it must grow, up to 120 ms, with the reason logged.
- **In the session's sandbox**, run `uv` with `UV_CACHE_DIR` set to a writable folder. A browser or Docker has to run outside the sandbox; the owner allows that when asked, one command at a time. See Machine in `LOG.md`.

## To settle while building

These are implementation choices. None needs the owner unless it goes wrong.

- **How the stored sound is packed.** The plan is FLAC, which loses nothing and is about half the size. Check that Chrome and Firefox decode it back to the exact samples. If they do not, store raw samples.
- **The exact sample format of an upload**: the bit depth, the channel layout, and how the rate and the length are sent.
- **How the page reads a file's tags**: a small reader for mp3 and m4a tags written here, or a pinned library.
- **How a name is built from tags**: artist and title when both are there, the title alone, or the file name.
- **The end-to-end tool.** It is a new dependency, pinned like the others. It drives real browsers, so it runs outside the sandbox, one approved command at a time.
- **Deleting the song that is being analysed**: stop at the next piece of the song if the tracker allows it, otherwise finish and discard.

## Open

**For slice 1**

- **Two numbers are still proposals**: the 4% tolerance on the BPM and the 200-character limit on a name. The owner has not answered either.
- **The server cannot verify a song's fingerprint**, because it never sees the file. Someone inside the group could file a sound under the wrong one. The owner was told this is taken as acceptable for a private tool and did not object.
- **Browser decoding matches `ffmpeg`'s on this machine, for four files only.** Chrome 154 and Firefox 157 gave the same samples with no shift. A file from another encoder may still decode with a shift; the rules about the page above are what make that harmless.
- **No song with a real tempo change.** One way to get a check without one: speed up the second half of a mix by a known amount with `ffmpeg` and scale its labels to match. Not put to the owner yet.
- **Three spots in the full Me Emborracharé** read about 165 BPM in a rough measurement, near 1:08, 2:16 and 3:28. The cause is not established. They are where a tracker is most likely to trip.
- **The three mixes are clean and at an exact tempo.** They are probably easier than a commercial recording, so a pass on them does not prove a pass on the two recordings.

**For later slices**

- **Mambo.** The brief names it as one of three rhythms, and the owner confirms that. The labels treat it as a part of the song, like Verse or Chorus, whose rhythm is majao or derecho. No label has mambo as a rhythm, so G1 has nothing to compare mambo against. Settle before slice 3.
- **When a section's rhythm and its blocks disagree, which wins?** On Me Emborrachare the Bridge is labelled Derecho, and its two blocks are `-` and Majao.
- **Which rhythms count as `other`?** The labels also have Urban, Trap, Dembow, `-` and none.
- **A section's `end_s` in the labels is the start of the next section.** G2 speaks of the last beat, which is one beat earlier.
- **The assumption that a section always starts on count 1** is still a proposal.
- **Lining up the labels with the commercial recordings.** The full Me Emborracharé is 44 s longer than the mix and differs in places.
- **The list of remembered songs gets its real screen in slice 5**, where G4 is checked. Whether a song can be renamed is not decided.
- **No measure for "fluid".**
- **Deployment for coworkers** is out of scope. When it comes:
  - a container;
  - an nginx body limit far above the default, since a 4-minute song is about 42 MB of samples and a 15-minute one about 159 MB;
  - the library is shared, so everyone who can log in can play and delete every song.

**Housekeeping**

- **`.claude/settings.json` is not committed.** It holds paths from the owner's machine.
