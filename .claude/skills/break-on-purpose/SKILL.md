---
name: break-on-purpose
description: Breaks the code on purpose, one break at a time, to see whether the checks fail, and repairs the checks that do not. Use it whenever the owner asks to break the code on purpose, to see the checks fail, to prove or try out the tests, or for mutation testing; whenever someone says a test or an assertion cannot fail, is weak or would pass anyway; and before the checks of a part that was just built are trusted, even when the owner only asks whether its tests are any good.
---

# Break on purpose

A check that has never been seen to fail shows nothing. `ACCEPTANCE.md` ticks an item by naming the check behind it, so a check that cannot fail is a tick that was never earned. This skill makes one claim false at a time, in the code, and looks at which check notices. Where none does, it repairs the check and proves the repair.

Sessions 3, 6 and 7 did this by hand. Their tables in `LOG.md` ("Broken on purpose", "Breaking the code on purpose") show what the result looks like.

## Inputs

Two things, both from the owner's request:

- **The part under test**: files, a slice or a section of `ACCEPTANCE.md`, or a range of commits, whose changed code is then the part.
- **The command that runs its checks.** When the owner does not give it, take it from the table under "One break at a time" and say which one was taken.

If the part is not named, ask which part, and do nothing else until the answer is there. Breaking a part the owner did not mean costs minutes of runs and leaves a table nobody asked for.

## Before the first break

- **The files to break are as committed.** `git status --porcelain -- <files>` prints nothing. A break is undone by writing the file back from the commit, and that would also take away work that was never committed. If a file has changes of its own, stop and tell the owner.
- **The checks pass on the code as it is.** Run the checks of the part once and keep the figures: how many passed, how many were skipped, and why. A check that is skipped here cannot catch anything here. `NEXT.md`, under "In the session's sandbox", says what does not run inside the sandbox.

## Choose the breaks

If the owner hands over a list of breaks, that list is the work. Otherwise there are two lists, and the work is done when both are: there is no limit on the number of breaks.

**First list: every claim of the part, once.** Read the part of `ACCEPTANCE.md` that is under test, and what `BRIEF.md` and "Rules that are easy to break" in `NEXT.md` say about it. Every sentence there that says what the program does, refuses, keeps or never does is a claim. Write one break for each claim: the smallest change to the code that makes that one claim false and leaves the rest working.

The claims come first because they are what the owner was told is checked. A break taken from a claim is as narrow as the claim, and a narrow break is what shows a weak test: in a trial, a break that stopped every write to disk was caught, and hid that the test of one kind of write could not fail.

**Second list: what no claim speaks of.** Go through the code of the part, function by function and branch by branch, and write a break for each behaviour the first list did not touch: an edge of a range, a rarer form of the input, a method or a path that should not be answered, the order of two checks. Trials without the first list found real gaps this way that the claims alone did not reach. A break of this list that nothing catches is a question before it is a weak check: the behaviour is written down nowhere, so a test for it would fix something the owner never decided. Write the test where the surrounding claims leave no doubt what is right. Otherwise report it as the owner's to decide, and write none.

Kinds of break that have shown something in this project:

- a limit moved or taken away: 0.0.0.0 for 127.0.0.1, the window back at 70 ms, any number where 200 is the most
- a check that always says yes: the own-page check, the host check
- a step left out: one header not sent, a name not cut, a view that returns before it draws
- a place or a count moved by one
- something that holds on one path and is forgotten on another: after a restart, after a renaming, in a second browser
- a rule loosened back to what it was before the part was built

Breaks that show nothing, and are rewritten:

- **The program or the test file no longer loads.** A syntax error or a missing export fails every test, and none of them looked at the claim.
- **Two claims in one break, or a break wider than its claim.** There is no telling which one was caught.
- **A change that alters nothing a caller could see.** Say so in the table and go on.
- **A break that never ends.** A loop that does not stop names no test. Give the run a time limit, or leave the break out and say so.

Write each list whole before running any of it, the first grouped as `ACCEPTANCE.md` groups its items and the second by function. Each break gets a sentence that says what is now wrong, in the words of the claim ("A song shorter than 20 seconds is taken"), and **the test that should catch it**: the one the acceptance item points at, or the one whose name states the claim. Naming that test before the run is what makes the third outcome below visible.

## One break at a time

From the root of the repository, for each break:

1. Change the code with the Edit tool. Only this break: the one before it has been written back.
2. Run the checks through `scripts/one_break.sh`, which is in this skill's folder:

   ```
   bash <this skill's folder>/scripts/one_break.sh <name> <file>... -- <command that runs the checks>
   ```

   `<name>` is a short name for the break, `<file>...` the files it changed. The script refuses to run when a file is still as committed, because then the edit did not apply and a passing run would be read as a weak check. It keeps the break as a patch, runs the command, says how long it took, and writes the files back whatever happened, also when the run is cut off.
3. Read which tests failed, and what each one said.

**Which checks to run.** Wide enough that the expected test and the other tests of its part are in the run, and no wider. The whole suite takes minutes; twenty-five breaks cannot each wait for it.

| Part | Command | Time |
| --- | --- | --- |
| The page's logic and its colours, `web/*.js` | `node --test web/` | under 1 s |
| The server, the store, the queue, the analysis | `.venv/bin/python -m pytest bachata/<name>_test.py` | seconds |
| The three mixes | `.venv/bin/python -m pytest bachata/songs_test.py` | about 30 s; skipped without the reference material |
| The page in a browser | `.venv/bin/python -m pytest e2e -k "firefox and <words of the test's name>"` | 10 to 15 s a test, about 2 min for all; pass a longer timeout |

Inside the sandbox Chrome does not start, and Firefox plays no sound, so the tests that need sound are skipped. A break whose expected test is skipped has not been tried: say so in the table, or ask the owner for that one run outside the sandbox.

**What a run can show.** There are three results, and one that is not a result.

- **Caught where it should be.** The expected test fails, and its message is about the claim: the two values it compares, the thing it did not find. Keep that message; it is the evidence.
- **Caught by nothing.** Every check passes. The claim has no check.
- **Caught, but not by the test that should.** Other tests fail and the expected one passes. The break is caught today by luck, and the expected test is weak all the same. This one is easy to miss, because the run is red.
- **Not a result:** everything fails, or a test fails on something else than the claim (a time-out, an import, a helper that broke). Rewrite the break smaller and run it again.

## A weak check: repair it and prove it

For every break caught by nothing, or not by the test that should:

1. **Find why the test could not see it** before changing anything. The reason is worth more than the fix: it says what other tests have the same blind spot. In session 3 the tests of the security headers read the list of headers from the program itself, so a header taken out of the program was taken out of the test too.
2. **Change the test, not the code.** Make the expected test stronger when there is one. Write a new one when no test states the claim, named as the tests around it are named: a sentence that says what holds.
3. **Run the very same break again**: `one_break.sh <name> -- <command>`, with no files, applies the patch that was kept. The test must now fail, with a message about the claim. A new test that has only ever passed is in the same position as the one it replaces.
4. **Run the checks of the part on the code as committed.** They pass.

Some claims cannot be checked by a program: what is judged by the owner's eye or ear. Leave those as caught by nothing, and say why.

If a break shows that the code as committed is wrong, or that `ACCEPTANCE.md` claims something the program does not do, that is a finding and not a weak check. Stop on it and tell the owner; it is not repaired here.

## When someone says a check cannot fail

A reviewer's finding, or the owner's doubt about one test, is the same work started from the other end. Write the break that this check exists to catch and run it.

- The check passes: the finding holds, and that run is the proof of it. Repair the check and prove the repair, as above.
- The check fails: the finding does not hold. Say so, with the message.

A new check for a fault that is in the code needs no break: it is seen to fail on the code as committed, before the fix.

## At the end

- `git status --porcelain` lists only tests and the project's records. Every file that was broken is as committed: `git diff --stat HEAD -- <the files that were broken>` prints nothing. Inside the sandbox the list also has a few dotfiles at the root, `.bashrc` among them, that are not there: they are the sandbox's own.
- Run the checks of every part whose tests changed once more, on the code as committed.
- The whole suite, in Chrome and with sound, runs outside the sandbox and is the owner's to allow. Ask for it when a test of the page changed.
- Do not commit unless the owner asks.

## The record

The project keeps its facts in four files, and the result goes into them, not into a new one.

**`LOG.md`**, in the entry of the session, newest first. Only what was measured. If the session has no entry yet, it gets one at the top, numbered one after the newest.

- One sentence on how it was done, then the table, grouped by part with a row in bold for each group:

  ```
  **Breaking the code on purpose.** One break at a time, on the committed build: the file is changed, the checks run, and the file is written back as it was. 4 breaks; 3 were caught as the tests stood, and after one fix to the tests all 4 are.

  | Break | Caught by |
  | --- | --- |
  | **The bar** | |
  | Every place in the bar moved on by one | `test_every_labelled_beat_is_in_its_place_of_the_bar`, on all three mixes: every labelled beat reported, 505 of 505 on Eso Es Amor |
  | Bars of three allowed again beside bars of four | **Nothing.** The DBN chooses bars of four on these songs either way. Now `test_a_bar_is_four_beats_even_where_every_third_beat_is_rated_a_downbeat` |
  | **What the server refuses** | |
  | The own-page check always says yes | 21 tests: every refusal of an upload and of a deletion |
  | The host check accepts any host | The host test |
  ```

- The breaks of the second list follow in the same table, under a row in bold that says no claim speaks of them.
- A break caught elsewhere reads "**Not the test that claims it**", with the name of that test, why it could not see the break, and what it does now.
- Under "Runs", in the table `What was run | Result | Time`: the checks on the code as it was, the breaks, each weak check again after its repair with the message it failed on, and the last run.
- Under "Decisions": what was decided while repairing, and what the repaired checks still do not look at.

**`ACCEPTANCE.md`**, under "How these are tested" for the part: one line that the checks were seen to fail, how many breaks, how many were not caught, and what changed. No item is ticked or unticked by this work, and none is loosened.

**`NEXT.md`**: where things stand, and under "Rules that are easy to break" one rule for each blind spot that could come back. "The tests of the security headers carry their own list" is there for that reason.

**To the owner**, at the end: the part and the command that were taken, how many breaks in each list, how many were caught as the tests stood, each one that was not with what changed, what was skipped or left unchecked, and anything that is theirs to decide.
