# Contract: why an analysis failed, and "Try again"

The task is in `NEXT.md`, under "Left open by the critique": why an analysis failed, and a way to try it again without deleting the song.

This file is what the server and the page agree on for that task, and how the work is split. It is for this task only. The integrator deletes it when the work is accepted: by then `ACCEPTANCE.md` has the checks, the header of `bachata/server.py` has the request, and `LOG.md` has the decisions. The example, `fixtures/failed_songs.json`, stays, because tests read it.

Nothing is built yet. Written on 2026-10-08, after `d76b864`, and changed the same day to give each worker a folder and a branch.

## Decided by the owner on 2026-10-08

1. **Why.** The server sorts every failure into one of four reasons. The page has a sentence of its own for each. The text of the exception and its traceback stay in the server's log and are not sent.
2. **The request.** `DELETE /api/songs/<id>/result`, for a failed song only.
3. **By itself, never.** A failed song is analysed again only when the page asks, or when the version of the analysis changes, as today. Not at a restart, and not a second time right after the failure.
4. **Also kept: how long the analysis ran** before it failed. No count of tries and no date.
5. **This file**, with the example in `fixtures/`, until the work is built.
6. **A work folder and a branch for each worker**, `wt/server` on the branch `server` and `wt/page` on the branch `page`, both made from the same commit. Said after the interview: the course the owner follows requires it. A worker may commit on its own branch.

## What does not change

- **`ANALYSIS_VERSION` stays 5.** A new version would analyse the 18 songs of the library again, about 3 minutes and 3 GB. A failure that was stored before this work is read as it is: see "Stored" below.
- **The four states**: `waiting`, `analysing`, `ready`, `failed`, and how the queue reads them from the library.
- **Every field a song has in the list today**: `id`, `name`, `state`, `seconds`, `ones`. A song that has not failed is listed exactly as today, with no new key. `bachata/server_test.py` compares a whole song with `==`.
- **`GET /api/songs/<id>/result`**: 404 unless the song is ready.
- **The order of the list**: the order the songs arrived. A song that is tried again keeps its place, and is analysed after the songs that arrived before it and still wait.

## Stored: `result.json` of an analysis that failed

Written by the queue. `version` and `error` are there today; `reason` and `seconds` are new.

| Field | Type | Allowed values |
|---|---|---|
| `version` | integer | The version of the analysis that failed. |
| `error` | string | The name of the exception's class, as today. For a person who reads the file. It is never sent to the page. |
| `reason` | string | `"memory"`, `"model"`, `"sound"` or `"other"`. |
| `seconds` | number | How long the analysis ran before it failed: 0 or more, rounded to one decimal, measured as the `seconds` of a result that succeeded. |

A result is a failure when it has the key `error`. No key of a result that succeeded (`beats`, `bpm`, `bar`, `count`) is in it.

The four reasons:

| `reason` | When |
|---|---|
| `memory` | The analysis could not get the memory it asked for: Python's `MemoryError`, or torch saying it cannot allocate. |
| `model` | A checkpoint of `models/` is missing or is not the recorded file: what `bachata/model.py` raises. |
| `sound` | The stored sound could not be read as samples: reading `sound.raw` failed, before the analysis was called. |
| `other` | Everything else. |

How the server tells them apart is the server worker's to build. Each of the four has a test that fails when a failure of that kind gets another reason.

## Sent: a song in the list

`GET /api/songs` and `GET /api/songs/<id>`. One new key, `failure`.

| Field | Type | Allowed values |
|---|---|---|
| `failure` | object | Present when `state` is `"failed"`, and only then. Never `null`: the key is absent for the other three states. |
| `failure.reason` | string | `"memory"`, `"model"`, `"sound"` or `"other"`. |
| `failure.seconds` | number or `null` | The stored `seconds`. `null` when none was stored. |

Rules for reading, on both sides:

- **A stored failure with no `reason`**, or with one that is not of the four, is sent as `"other"`. With no `seconds` it is sent as `null`. That is every failure stored before this work.
- **The page reads a `reason` it does not know as `"other"`**, and a `seconds` of `null` as "not known": it then says no duration.
- **`failure` has these two keys and no other.** `error` is not sent.

## The new request

```
DELETE /api/songs/<id>/result      no query, no body
```

It throws the failed result away. The song has no result then, so it is `waiting`, and the queue is woken.

| Answer | Body | When |
|---|---|---|
| 204 | none | The song had failed. It waits again. |
| 403 | `Not from the application's own page` | Checked first, as for every request that changes something. |
| 400 | `Not a song id` | The id is not 32 hex digits. |
| 404 | `No such song` | The library does not have it, or it was deleted meanwhile. |
| 409 | `The song has not failed` | The state is `waiting`, `analysing` or `ready`. |

- **What it removes**: `result.json` of that song, on disk and in memory. After a restart the song still waits.
- **What it keeps**: the id, the name, the sound, the place in the list, and `ones`, the count 1s set by hand. They are in `song.json`, which the request does not touch.
- **Asked twice**, the second answer is 409, or 204 if the analysis failed again in between. Two browsers that press at once start one analysis.
- **A song that is ready cannot be analysed again this way.** It answers 409 and keeps its result.
- Every answer carries the security headers, as all the others.

## The example both sides test against

`fixtures/failed_songs.json`. Nine songs, in the order they arrived. For each:

| Key | What it is |
|---|---|
| `case` | What the song is an example of. |
| `song` | What the library holds besides the result: `id`, `name`, `seconds` (its length, a whole number of samples at 44.1 kHz), `ones`. |
| `result` | The content of its `result.json`, or `null` when it has none. |
| `listed` | The song exactly as `GET /api/songs` and `GET /api/songs/<id>` send it, when the application is made with the `version` at the top of the file. |
| `again` | The status of `DELETE /api/songs/<id>/result` from the application's own page. |

After an `again` of 204 the song is listed as its `listed` with `state` `"waiting"` and no `failure`, and nothing else changed. After a 409 it is listed as before.

No song of the file is `analysing`: that state is not on disk. Such a song has no `failure` and answers 409.

- **The server's test** builds a library with these songs and results, and compares the list with every `listed`, in this order, and every answer with `again`. Then what the list says after each 204.
- **The page's test** answers `/api/songs` with every `listed`, in this order, and reads every row: the state, the sentence, and "Try again" in the rows that failed and in no other. It presses one and sees the request go out.

Neither worker changes the file. A worker that finds it wrong or short says so in what it returns.

## What the page does with it

This is the page worker's to build. What the two sides need to agree on is above; this is what the owner chose in the interview.

- A failed row says for how long the analysis ran: `3:20, failed after 0:42`, and `3:20, failed` when `seconds` is `null`.
- Under it, one sentence for the reason, in place of "To try again, delete the song and add the file again".
- A button, **Try again**, in every failed row, for every reason. It sends the request. On 204 the row says `waiting` at once or at the next list. On 409 the list is asked again and nothing is said: another browser was faster. On 404 the song was deleted. Anything else is said in the row.
- A song that was tried again does not open by itself when it is ready.
- The sentences are the owner's to word. A start: "The analysis ran out of memory.", "A file the analysis needs is missing or was changed.", "The stored sound could not be read.", "The analysis failed."

## The work

```
                 ┌──────────────────────────────────────────┐
                 │ CONTRACT                                 │
                 │ CONTRACT.md, fixtures/failed_songs.json  │
                 │ committed on master: that commit is the  │
                 │ base of both branches; nobody changes it │
                 └────────────────────┬─────────────────────┘
                                      │ both read it whole
                 ┌────────────────────┴─────────────────────┐
                 ▼                                          ▼
  ┌─────────────────────────────┐          ┌─────────────────────────────┐
  │ WORKER A                    │          │ WORKER B                    │
  │ the server and the queue    │          │ the page                    │
  │ wt/server, branch `server`  │          │ wt/page, branch `page`      │
  │                             │          │                             │
  │ bachata/queue.py            │          │ web/app.js                  │
  │ bachata/store.py            │          │ web/song.js                 │
  │ bachata/server.py           │          │ web/index.html              │
  │ bachata/model.py            │          │ web/style.css               │
  │ bachata/queue_test.py       │          │ web/song.test.js            │
  │ bachata/store_test.py       │          │ web/contrast.test.js        │
  │ bachata/server_test.py      │          │ e2e/page_test.py            │
  │                             │          │                             │
  │ the reason and the seconds  │          │ the reason in the row,      │
  │ kept, `failure` in the list,│          │ "failed after", "Try again",│
  │ DELETE .../result           │          │ the list answered by a test │
  │                             │          │                             │
  │ port 8087                   │          │ port 8088                   │
  │                             │          │                             │
  │ returns: the base commit,   │          │ returns: the base commit,   │
  │ changed files, executed     │          │ changed files, executed     │
  │ checks, open assumptions    │          │ checks, open assumptions    │
  └──────────────┬──────────────┘          └──────────────┬──────────────┘
                 │        at the same time, no word       │
                 │        between them but the contract   │
                 └────────────────────┬─────────────────────┘
                                      ▼
                 ┌──────────────────────────────────────────┐
                 │ JOIN                                     │
                 │ both have returned; both branches start  │
                 │ at the base; no file is in both lists;   │
                 │ the contract and the example are as      │
                 │ committed; each side's test of the       │
                 │ example passes                           │
                 └────────────────────┬─────────────────────┘
                                      ▼
                 ┌──────────────────────────────────────────┐
                 │ INTEGRATOR, owns acceptance              │
                 │ in the main folder, on master            │
                 │ both branches merged into master; one    │
                 │ flow through the real program and        │
                 │ the real page; the whole run; the open   │
                 │ assumptions, settled or taken to the     │
                 │ owner; ACCEPTANCE.md, LOG.md, NEXT.md;   │
                 │ the checks seen to fail; the commit on   │
                 │ master; this file deleted                │
                 │ port 8089                                │
                 └──────────────────────────────────────────┘
```

### What the two workers share

Each worker has a work folder of its own, on a branch of its own, and both branches start at the same commit: **the base**, which is the commit of `master` that holds this file as it is now.

| Worker | Folder | Branch |
|---|---|---|
| A, the server and the queue | `wt/server` | `server` |
| B, the page | `wt/page` | `page` |

**How a work folder is made**, by its worker, from the main folder. `NEXT.md` describes it under "Rules that are easy to break" and "Housekeeping".

- `git worktree add -b <branch> wt/<name> <base>`.
- Links to the main folder: `.venv`, `models`, `.playwright`, and each item under `fixtures/audio/` except its `.gitignore`: `README.md`, `by-ear.json`, `dev`, `entries`, `entry-pairs.json`.
- **No copy of `data/`**, where `NEXT.md` gives a work folder one: no check a worker runs reads the library.
- **Every check is started from inside the work folder.** Started from the main folder, it tests `master`.
- `.git/info/exclude` keeps `wt/` and the three links at the root out of git's listing. It is set, and it is not part of any commit.

**A worker starts by checking that its folder is at the base**: `git rev-parse HEAD` in it is the base, and `git status` shows no work. A folder that is already there with work in it, or a branch that is past the base, is put back to the base, the links are made again, and the worker starts over. It returns the hash it started from.

**A worker may commit**, on its own branch, from inside its own folder, staging each file by its path.

What is still one thing for both, and how it is kept from harm:

| Shared | Rule |
|---|---|
| **The repository** | One `.git` behind both folders and the main one: the commits, the branches, and the stash. A worker commits on its own branch and touches no other: it does not check out, merge, rebase, move or delete a branch, stash, clean up the repository, or run a `git worktree` command for a folder that is not its own. It writes nothing in the main folder but its work folder. |
| **`.venv`** | One, through the link. Read only. Checks are run with `.venv/bin/python -m pytest`, not `uv run`, which may change it. No `uv sync`, no `uv add`, no change to `pyproject.toml` or `uv.lock`. A dependency that seems needed is an open assumption. |
| **`models/`** | One, through the link. Read only: the two checkpoints, 3 GB between them in memory when both are loaded. Neither worker fetches, moves or renames them. A test of the reason `model` uses a path of its own in a temporary folder. |
| **`.playwright/`** | One, through the link. The browsers, read only. Only worker B and the integrator start one. |
| **`fixtures/audio/`** | One, through the links. The owner's recordings and marks, read only. No check of a worker needs them. |
| **`data/`** | The owner's library, 18 songs, in the main folder only. Neither worker reads or writes it. Tests make their library in a temporary folder, and the program is never started without `BACHATA_DATA` set to one. |
| **Ports** | The owner's own program may be on 8080 to 8083, and a work folder used 8086. Worker A: `BACHATA_TEST_PORT=8087`. Worker B: `8088`. The integrator: `8089`. With no port named a test takes a free one, which is also safe. |
| **Memory and time** | A real analysis takes 3 GB. Each worker runs its own checks and not the song checks (`bachata/songs_test.py`, `entry_test.py`, `entry_pairs_test.py`, `fills_test.py`): the whole run is the integrator's, alone, once both have stopped. A worker stops after 35 minutes of work and returns what it has. |
| **Temporary files** | A folder each, with a short path: `/tmp/claude-1000/e2e-a`, `e2e-b`, `e2e-i`. Chrome dies on a long one. |
| **The contract and the example** | Each folder has them as the base has them. Neither worker changes them, on its branch or anywhere. |
| **The four project files** | `ACCEPTANCE.md`, `BRIEF.md`, `LOG.md`, `NEXT.md`: the integrator's. A worker that wants a line in one says so in what it returns. |
| **`break-on-purpose`** | The integrator's, after the merge. It writes files back from the last commit, and it takes longer than a worker has. |

Not shared any more: the files being written, git's index, and `.pytest_cache`. Each folder has its own.

`NEXT.md`, under "In the session's sandbox", says what does not run inside the sandbox: Chrome does not start, and the whole run needs a command outside it that the owner allows.

### What each worker returns

The base commit its folder was at when it started, the commit its branch is at when it stops, and three lists. Nothing is taken as done that is not in them.

1. **Changed files.** Every path that differs from the base on its branch, and every path it wrote and did not commit. Each is in its box, or the worker says why not.
2. **Executed checks.** Each command as it was run, and what it printed at the end: how many passed, failed and were skipped, and why the skipped ones were. And the checks it did not run, with the reason. A check that was not run is not reported as passing.
3. **Open assumptions.** Everything it decided that this file does not say, and everything in this file or in the example it found wrong, short or impossible. It does not change the contract to fit: it says so and builds to the contract as written, or stops.

### What the integrator accepts

- **The join holds**: the five conditions in its box above, read from git and not from what the workers said.
- **Both branches are merged into `master`**, in the main folder, each with a merge commit. No file is in both, so a conflict means the join did not hold: the merge is taken back and the owner is told. No work folder and no branch is removed.
- **One flow, through the real program and the real page**, which neither worker can run alone. A library made on disk with one song whose `result.json` is a failure of this version, and a count 1 set by hand: the row says the reason, "Try again" is pressed, the real analysis runs, the song is ready, and it has the same id, the same place and the same count 1.
- **The whole run passes** outside the sandbox, with the number of tests and none skipped: `TMPDIR=/tmp/claude-1000/e2e-i BACHATA_TEST_PORT=8089 .venv/bin/python -m pytest`.
- **`ANALYSIS_VERSION` is 5**, and the sentence "delete the song and add the file again" is in no file.
- **The checks were seen to fail**: the `break-on-purpose` skill on this part, after the work is committed.
- **The records**: the items in `ACCEPTANCE.md` with the check behind each, the request in the header of `bachata/server.py`, the session in `LOG.md` with the five decisions above, `NEXT.md` rewritten, and this file deleted.

## Open, for the owner

- **A process the system kills for memory writes no failure.** The song waits again at the next start, and is tried again by itself. Only a failure Python gets to see becomes `memory`.
- **`sound` and "Try again".** A sound that cannot be read will fail again. The button is there all the same, by the answer "every failed row"; the sentence could say to delete the song and add the file.
- **Two branches beside `master`**, `server` and `page`, by the owner's word of 2026-10-08 for this task. They and their folders are kept after the merge, as the others are.
