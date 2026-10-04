# Next step

Rewritten at the end of every session.

## Where things stand (2026-10-05)

The setup is done. No feature exists.

- `npm start` serves one page at http://127.0.0.1:8080. Set `PORT` to use another port.
- `npm test` runs two checks: the program serves its page safely, and the fixture files follow the format.
- There are no dependencies. Node 24.2 or later is needed.

## Next: slice 1, beats and tempo

Two things are needed from the owner first:

1. The address of the reference website.
2. At least one testing song as an audio file, ideally one the website has labelled.

Then, in this order:

1. **Make the first fixture.**
   - Put the audio file in `fixtures/audio/`.
   - Copy `fixtures/template.json` to `fixtures/labels/<artist-title>.json` and fill it in from the website.
   - Take the hash with `sha256sum` and the duration from the file.
   - Check by ear that the website's times match this recording. If the recording starts earlier or later, shift the times.
   - Run `npm test`.
2. **Decide where the analysis runs**, using that song as evidence.
   - Recommendation: try the browser first. It decodes audio by itself, which avoids the broken `ffmpeg` on this machine, and a song that never leaves the browser removes most of the risk for the machine that serves it.
   - The unknown is whether beat tracking is accurate enough in the browser. If it is not, the alternative is a local server doing the analysis.
3. **Build slice 1** against `ACCEPTANCE.md`.

## Open

- **The website has not been seen.** These questions change how fixtures are filled in:
  - Does it give end times, or only where each section starts?
  - How precise are its times?
  - Does it label the whole song?
  - Which recording do its times refer to?
  - May its labels be copied into this repository?
- **The validator does not compare an audio file with its sha256 yet.** Add that with the first audio file.
- **"Existing song" is not defined.** Where existing songs are kept, in the browser or on the machine that serves the application, is part of the browser decision.
- **`ACCEPTANCE.md` has gaps and proposals for the owner:**
  - the 70 ms window;
  - the assumption that a section always starts on count 1;
  - no measure for "fluid";
  - no checks for "secure";
  - no reference for tempo.
- **`.claude/settings.json` is not committed.** It holds paths from the owner's machine.
