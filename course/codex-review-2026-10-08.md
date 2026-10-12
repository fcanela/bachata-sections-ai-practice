# Review by Codex of the feature of 2026-10-08

The text below the line is the review as Codex gave it on 2026-10-08, saved that day. Tool: Codex CLI 0.159.3. Model: `gpt-6-astra`, effort `xhigh`, in a fresh session that had not seen the build session. Its own usage line: total 236,142 tokens, input 212,365 (plus 2,942,336 cached), output 23,777. It changed no file. What was done with its four findings is in `CAPSTONE.md`, under "After the review".

---

**Verdict: changes needed.** I reviewed `235adb2` against `master` at `442abf2`. The changes I recommend, in order of importance:

1. **Make ID matching case-insensitive before matching names.** In [places.py](<repo>/bachata/places.py:134), only names are folded. My temporary-library probe found that `ab01` succeeds while `AB01` fails. More seriously, an uppercase full ID selected a different song whose *name* contained that ID. This violates the command’s matching rule.

2. **Handle stored analysis failures without a traceback.** The existing queue legitimately stores results such as `{"version":5,"error":"RuntimeError"}`. Both `where` and `bars` crash with `KeyError: 'beats'` in [counted()](<repo>/bachata/places.py:146). I reproduced both through `python -m bachata`. Return one explanatory sentence and status 1, and test this stored state.

3. **Preserve the accepted large beat view when adding the readout.** The new [readout placement](<repo>/web/index.html:41) expands the left column and shrinks the beat canvas. Comparing branch and master assets in the same browser at 1100 × 800, its width fell from **569.8 to 439.5 px—23%**. The beat marks shrink with it. This departs from the constraint that the large view stays as accepted. Fit the readout without taking this space from the beats.

4. **Keep `at` when the same song is selected again.** [open()](<repo>/web/app.js:559) clears it whenever it has been used. My browser probe confirmed that reselecting the same file removes `at`. The brief says it remains until **another song** opens. Keeping the address and applying its seek only once should be separate decisions.

I made no repository changes or commits. Every program start used a temporary `BACHATA_DATA`; the owner’s `data/` was untouched. Final Git status and diff checks were clean.

I ran these checks independently:

- **JS:** `node --test web/` — **41 passed**.
- **CLI:** `.venv/bin/python -m pytest bachata/places_test.py` with cache disabled — **14 passed**.
- **Full:** `uv run --no-sync pytest -p no:cacheprovider --basetemp=<temporary-folder> -rs` — **293 passed, 1 failed, none skipped**, in 798 seconds. This includes all **88 Chrome/Firefox browser cases**, with sound.
- Additional probes covered uppercase IDs, stored failures, the real Chrome clipboard API, delayed link opening, existing manual count corrections, address retention, and branch/master layout measurements.
- An additional **1,000 combinations** of song lengths, starting counts and manual corrections agreed between Python and JavaScript, round-tripped every beat, and matched independently calculated bar boundaries.

The full-run failure was the unchanged [entry test](<repo>/bachata/entry_test.py:121): its required recordings were absent from the temporary library. Its output explicitly reported “its sound is not in the library.” This is a fixture limitation, not evidence of a branch regression.

For each acceptance item, these are my results. “Browser” below means the Chrome and Firefox cases in that full run.

| Item | Holds? | What I ran and observed |
|---|---|---|
| C1 | Yes | JS round-trip test; additional 1,000-combination probe. |
| C2 | Yes | JS short-bar tests reject beats beyond a bar’s end. |
| C3 | Yes, for the listed forms | JS parser tests accept and reject the specified examples. Additional restrictions are discussed below. |
| C4 | Yes | JS address construction and parsing tests. |
| C5 | Yes | Browser readout tests: before the first beat, plate presses and individual beat steps. |
| C6 | Yes | Playback/readout tests passed in both browsers with sound, including a separate focused run. |
| C7 | Yes | Browser tests change count 1 and check the updated readout and row numbers. |
| C8 | Yes | Browser tests inspect requested row text and actual ink in each row’s margin. |
| C9 | Yes | Browser hover tests check tag text, drawing and disappearance. |
| C10 | Yes | Browser link tests; independent probe also waited for readiness and resolved a place using an existing manual correction. |
| C11 | Yes | Browser tests check missing bars, missing beats, out-of-range times and malformed `at`. |
| C12 | Yes | Browser clipboard-stub tests; independent Chrome clipboard write/read returned the expected line. |
| C13 | Yes | Browser test checks that the readout has no live-region ancestor. |
| C14 | Yes as a test claim | Existing browser tests pass with the two disclosed assertion edits. They do **not** establish unchanged large-view dimensions. |
| C15 | Yes | CLI test checks all four output lines exactly for its stored fixture. |
| C16 | Yes | CLI tests check times on either side of a nearest-beat boundary. |
| C17 | Yes | CLI test checks the complete bar listing, short bars and manual markers. |
| C18 | Yes | CLI test changes count 1 through `Store`, checks changed addresses, then reverses it. |
| C19 | Yes | Existing 201-song comparison and my additional 1,000-combination check. |
| C20 | Partial | Listed lookup and ambiguity tests pass; independent uppercase-ID probes fail the accompanying case-insensitivity rule. |
| C21 | Partial | Missing files and nonexistent places get the required sentence/status. A stored failed analysis produces a traceback. |
| C22 | Yes | CLI tests check library contents, subprocess imports, checkpoint avoidance and `BACHATA_DATA`. |
| C23 | Yes | The unchanged no-argument loopback-server test passed in the full run. |
| C24 | Not fully established | JS passes; full pytest has the fixture failure above. No tests skipped. I did not repeat the full run outside the sandbox. |

I found no vacuous newly added test, but several limits matter:

- **One test enforces the wrong contract.** The [same-file reopening assertion](<repo>/e2e/page_test.py:1057) explicitly expects `at` to disappear, contrary to the brief.
- **Lookup coverage misses uppercase IDs.** It tests uppercase names and lowercase IDs, allowing finding 1 through.
- **Failure coverage omits saved error results.** The one-sentence test creates a missing `result.json`, not the failure record the queue actually writes.
- **The large-view test checks relative shapes and contrast.** Its [size comparison](<repo>/e2e/page_test.py:1926) can pass while every beat becomes smaller. My master comparison demonstrates that gap.
- **Twin agreement is not an independent correctness oracle.** Both implementations could share a mistake. The fixed expected cases help; my additional boundary checks found no discrepancy.
- **Clipboard and drawing claims are mostly scoped honestly.** C12 explicitly promises a stub check. Row/tag tests combine drawing-call observations with pixels. The tag test still omits the narrow, final plate that exercises right-edge clamping.

The two altered assertions in the old plate test are justified: adding a row number creates a second text drawing, and adding the readout changes the player’s text. Those edits do not themselves weaken the old checks.

The requested feature set is present. There are no new dependencies, server routes or stored fields, and none of the explicitly excluded controls were added. The small additional behaviors—scrolling a linked place into view and clearing stale title messages when opening a song—are sensible.

I agree with the proposed one-based numbering, short-bar numbering, nearest-beat interpretation, explicit `s` suffix and seconds in shared output. Interpreting `62.4` as bar 62, beat 4 is consistent with that grammar.

Moving **Copy place** to the top bar is sound: my measurement confirmed that the position control retains about 615 px at 1100 px viewport width. Moving the readout onto the band is understandable, but its effect on the accepted beat display needs correcting as described above.

Finally, the parsers add undocumented limits: six bar digits, one beat digit and three fractional digits for seconds. The length caps are harmless for supported song lengths; I would relax the time-precision restriction rather than reject an otherwise meaningful input such as `4.7501s`.
