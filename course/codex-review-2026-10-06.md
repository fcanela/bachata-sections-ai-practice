# Review by Codex of slice 2 and the redesigned page (2026-10-06)

The text below the line is the last message of the Codex session of 2026-10-06, given at 06:09:58 UTC. It was copied on 2026-10-12 from Codex's own record of that session, because the text had not been saved at the time. Tool: Codex CLI 0.159.3. Model: `gpt-6-astra`, effort `xhigh`. It changed no file.

The review holds more observations than the four that were handed to the builder. The four that were taken and fixed (`LOG.md`, session 7, commit `bd60198`) are its two numbered problems and the first two of the weak tests it lists.

---

**The suite passes, but two checked acceptance requirements fail.** Reviewed `2e67514..20a13db`; no repository files changed.

I independently ran:

```sh
PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/tmp/bachata-review-uv \
uv run --frozen --no-sync pytest -p no:cacheprovider -ra
```

Result: **182 passed in 287.49 seconds, no skips**, including Chrome, Firefox and the reference songs.

1. **[P2] Loop cannot be switched on or off during playback.**  
   In [app.js:794](<repo>/web/app.js:794), `replay()` calls `pause()`, which calls `showLoop()` and restores the checkbox’s previous value. The handler then reads that restored value. I reproduced both directions: switching off leaves it looping; switching on leaves it playing normally. This fails [ACCEPTANCE.md:192](<repo>/ACCEPTANCE.md:192). The existing test pauses before switching off.

   This command removes that pause **in memory**, leaving production code untouched:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
   import inspect, pytest
   import e2e.page_test as t
   name = 'test_a_marked_range_plays_in_a_loop_with_a_click_on_every_beat_of_every_pass'
   source = inspect.getsource(getattr(t, name))
   source = source.replace(
       '    page.locator("#play").click()\n\n    started =',
       '    started =', 1)
   exec(compile(source, t.__file__, 'exec'), t.__dict__)
   raise SystemExit(pytest.main([
       '-p', 'no:cacheprovider', '-q', 'e2e/page_test.py',
       '-k', 'marked_range_plays and chrome', '--tb=short']))
   PY
   ```

   Result: **1 failed** — `Locator.uncheck: Clicking the checkbox did not change its state`.

2. **[P2] Elapsed beat marks fail the required contrast.**  
   [draw.js:113](<repo>/web/draw.js:113) draws earlier beats at 28% opacity. Browser pixel measurements gave **1.818:1 in light mode and 1.793:1 in dark mode**, below the **3:1** requirement in [ACCEPTANCE.md:199](<repo>/ACCEPTANCE.md:199). The contrast tests check opaque tokens and miss this compositing.

   This command calculates the contrast from the actual source values:

   ```sh
   node --input-type=module - <<'JS'
   import {readFileSync} from 'node:fs'
   const css = readFileSync('web/style.css', 'utf8')
   const draw = readFileSync('web/draw.js', 'utf8')
   const alpha = Number(draw.match(/beat < lit \? ([\d.]+)/)[1])
   const rgb = h => h.match(/[\da-f]{2}/g).map(x => parseInt(x, 16))
   const lum = c => c.map(x => x / 255)
     .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4)
     .reduce((s, x, i) => s + x * [.2126, .7152, .0722][i], 0)
   const ink = rgb(css.match(/--band-mark: #([\da-f]{6})/)[1])
   for (const [, hex] of css.matchAll(/--band: #([\da-f]{6})/g)) {
     const bg = rgb(hex), fg = ink.map((x, i) => x * alpha + bg[i] * (1-alpha))
     console.log(hex, ((lum(bg)+.05)/(lum(fg)+.05)).toFixed(3), 'required >= 3')
   }
   JS
   ```

   Output: **1.825 and 1.800** before canvas alpha quantization.

The tests also give more assurance than they establish:

- **A tautological assertion:** [song.test.js:350](<repo>/web/song.test.js:350) claims to check that the original analysis count remains unchanged, but asserts `eights(30)[12] === 5` on a newly generated array. It cannot detect mutation of the supplied array. I changed `count.slice()` to `count` in an in-memory module; **all 26 song tests still passed**.
- **The large canvas can disappear without failing its claimed checks.** I intercepted `draw.js` in memory, made `drawNow()` return immediately, and removed the numbers drawn beneath the song’s marks. The upload/playback, lit-beat/click, marks/counts, and manual-count browser tests still produced **8 passes across Chrome and Firefox**. They check metadata and interactions; those checks do not establish that the large view is drawn. The missing number/empty-slot coverage is acknowledged in `NEXT.md`, but the uncovered large view is broader.
- **The fixture-presence test only passes or skips.** [songs_test.py:52](<repo>/bachata/songs_test.py:52) cannot fail and does not establish that all three required mixes exist.
- **Count accuracy is deliberately measurement-only.** Its test can reject malformed output, but cannot fail for a low match rate. That follows the current slice-2 agreement.
- **Commercial BPM checks only the median.** It can pass while individual displayed tempos violate the proposed tolerance.

I reran the measurements explicitly:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
-p no:cacheprovider -q -s bachata/songs_test.py \
-k 'count_is_measured or commercial_recording'
```

| Recording | Independently measured result |
|---|---|
| Me Emborrachare mix | 120/396 counts match |
| Eso Es Amor mix | 257/505 counts match |
| Old Town Road mix | 416/416 counts match |
| Commercial Me Emborracharé | **33 beats outside 4%**, from 0.28–18.52 seconds; median passes |
| El Perdedor | No beats outside 4% |

The commercial intro remains an unresolved slice-1 acceptance item, already documented in `NEXT.md`. The bar-position checks passed for all three mixes.

Other acceptance work remains open: the owner’s listening checks, commercial bar alignment, three-metre readability, the visual review for colour-independent distinctions, and the proposed reference/count rules. Reduced-motion behaviour lacks an automated check. Section detection, automatic half phrases, section navigation and section replay remain scheduled for later slices; the current documents explicitly defer them.

The one literal scope departure I found is **backward compatibility for old `song.json` records without `ones`**, in [store.py:70](<repo>/bachata/store.py:70), with a dedicated test. That conflicts with the brief’s “No backward compatibility” limit, although it preserves the existing library. Looping, renaming, manual counts, Clear, song URLs, Opus and the redesign are explicitly authorized.

Finally, `git diff --check 2e67514..20a13db` reports trailing whitespace in `web/fonts/LICENSE.txt:26`; this is housekeeping, not a functional defect.
