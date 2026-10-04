# Run and cost log

Newest session first. Only measured figures go in here.

## 2026-10-05, session 1: setup

### Runs

| What was run | Result | Time |
| --- | --- | --- |
| `npm test` | 2 passed, 0 failed | 0.3 s |
| `npm start`, then `curl -i http://127.0.0.1:8080/` | 200, the page, and the three security headers. `ss -ltn` shows it listening on 127.0.0.1 only | not timed |
| `curl` for `/server.js`, `/../package.json` and `POST /` | 404 each | not timed |
| `npm test` on a scratch copy broken on purpose, three times: one header removed, listening on 0.0.0.0, two template sections overlapping | failed each time, in the expected test | not timed |
| `git commit` | failed twice: commits were signed with the owner's SSH key, which the session cannot use. The owner then turned signing off for this repository (`git config commit.gpgsign false`) and the commit was made unsigned | not timed |

### Cost

- Paid APIs: none used, $0.
- Network: none. Nothing was downloaded or installed.
- Dependencies: none.
- Cost of the Claude Code session itself: not measured from inside the session.

### Decisions

- **Stack for the setup:** Node's standard library and plain JavaScript. No dependencies and no build step. `server.js` sends one page and answers 404 to everything else. This is the smallest thing that runs and can be checked, and it does not settle where the analysis will run. Replace it freely when a slice needs more.
- **Where the analysis runs:** not decided. See `NEXT.md`.
- **Fixtures:**
  - Labels are committed, one JSON file per song in `fixtures/labels/`.
  - Audio stays out of git, in `fixtures/audio/`, because the songs are copyrighted.
  - Each label file records the sha256 and duration of its audio, because times copied from a website only hold for one exact recording.
  - Parts that are none of the three sections are written down as `other`, and the labels must cover the whole song. Without that, a check cannot tell an invented section from a part nobody labelled.
  - `fixtures/template.json` is a made-up example. `npm test` validates it and every file in `fixtures/labels/`.

### Machine

- Node 26.8.2, npm 11.19.1, Python 3.13.15, uv 0.11.32. Chrome and Firefox are installed.
- `ffmpeg` does not start in this session's shell: `symbol lookup error ... librt.so.1: undefined symbol: __pointer_chk_guard`. Nothing here depends on it. It matters as soon as audio has to be decoded outside a browser.
