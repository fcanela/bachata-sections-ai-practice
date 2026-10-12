# The same spec built at effort high and at xhigh (2026-10-07)

An excerpt of two things saved that day by the second Claude session: the usage panels of the two sessions, read at 17:33:27 UTC, and the table of its comparison report, written at 15:59:29 UTC. Session ids are left out. The sections of the report that describe how the table was checked are not copied.

Same model (Opus 5.5, 1M context), same harness (Claude Code 2.1.285), same commit (`450a573`), same spec and brief, fresh sessions started 31 seconds apart. One run each. Neither session needed a message from me.

## The usage panels

Cost is at list prices, from each session's own panel. It is not money paid: the work ran on a subscription plan. The panel includes an advisor model.

| Build | Effort | Launch to hand-back (UTC) | Cost at list prices | API time | Opus 5.5 | Fable 5.1 (advisor) |
| --- | --- | --- | --- | --- | --- | --- |
| `bars-high` | high | 13:38:31 to 15:49:46, 2 h 11 min 15 s | $13.64 | 33m 40s | 688 input, 147.6k output, 17.2m cache read, 291.8k cache write ($8.71) | 375.1k input, 23.4k output ($4.92) |
| `bars-xhigh` | xhigh | 13:39:02 to 15:53:15, 2 h 14 min 13 s | $26.97 | 1h 4m 18s | 498 input, 299.8k output, 31.0m cache read, 574.1k cache write ($16.60) | 839.6k input, 39.4k output ($10.36) |

Ratio xhigh to high: cost 1.98, API time 1.9, output tokens 2.03. The time from launch to hand-back is the wall clock and is almost the same. The two builds ran at the same time on the same machine.

## The comparison

Four subagents on Sonnet compared the two builds as "P" and "Q" without knowing which effort made which. The table is the summary of their reports, with the builds named.

| Characteristic | Build at high | Build at xhigh | Which is ahead |
| --- | --- | --- | --- |
| Time to hand-back | 2 h 11 min 15 s | 2 h 14 min 13 s | no real difference |
| Size of the change | 984 lines added; `web/draw.js` 324 lines; tests +718 | 1,272 lines added; `web/draw.js` 341 lines; tests +957 | high is leaner |
| Code structure | names the loop band's sizes as constants; uses `ochoOf` on bars, a misleading name | writes those sizes as plain numbers in `loopRun`; adds a clear `barOf` | no clear winner |
| Page code against odd conditions | guards a very narrow canvas and a canvas at a fraction of a pixel | follows the spec's formula to the letter, no guard | high |
| Tests against the spec's list (30 points counted by the subagent) | a real test for 28; reads the plate colours from the page's own style sheet; weaker checks of the halo, of the sound case and of a short ocho | a real test for 30; carries its own table of colours; records colour, weight and size of every count; checks the lit bar in pixels while the song plays | xhigh |
| The skill's round of breaks | 92 breaks, 1 test repaired | 117 breaks, 9 tests made stronger and 1 added | xhigh |
| Fidelity to the spec (74 points counted by the subagent) | 71 conform; 2 small departures, both of them the guards above | 73 conform; none departs | no real difference |
| The interface in the pictures | as the chosen picture | as the chosen picture | no difference a dancer would notice |
| Keeping to the brief | ran the outside-sandbox command 8 times where the brief said once; its first picture run rewrote 7 result files in the worktree's copy of the library | ran it once; changed no data; says the design hook did not run because it edited by script | xhigh |

One claim of a subagent was found wrong in the check of the table and is not in it.

## Limits, as the report states them

One task, one run at each level, and a task with a detailed written spec, which leaves little room for the page itself to differ. The two builds ran at the same time on the same machine, so their run times are not those of a quiet machine.

The build at high is kept by the tag `bars-high` (`3e17716`). The build at xhigh, as it was compared, is `b712db3`, which is on `master`. Three changes were made to it after the comparison, up to `918cc78`.
