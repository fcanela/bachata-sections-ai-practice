# Bachata sections

A web app for your own computer. You give it a bachata song and it finds the beats, the bars and the count from 1 to 8. The goal is to mark the sections of the song (derecho, majao, mambo). That part is not built yet.

## The problem

A social dancer who is learning musicality wants to hear and anticipate the changes between derecho, majao and mambo. For that they need to see where the song is and what comes next, from a few metres away. Sites like emusicality.co.uk break songs down by hand, a few songs at a time. This app takes any recording, on your own machine, with no paid service.

## State

What works:

- Uploading a song (mp3, m4a, opus) into a library kept on the machine.
- Beats and tempo, with a click on every beat.
- The bar and the count 1 to 8, with a control to set count 1 by hand. The count is a best guess and can be wrong after a half phrase.
- A page that plays the song and shows it as one plate per bar.
- A name for every bar and beat ("24.3" is bar 24, beat 3), in the page, in the address, and in the commands `where` and `bars`.

What is not built (slices 3 to 5 of `BRIEF.md`): derecho or majao for each ocho, mambo, and the sections on the screen.

I accepted slices 1 and 2 on 2026-10-06 as they stood. Some checks by ear in `ACCEPTANCE.md` are still open, and its block of 2026-10-12 lists them.

## Run it

It needs Python 3.12, `uv` and a C compiler (one dependency, madmom, is built from source).

    uv sync
    uv run python scripts/fetch_model.py
    uv run python -m bachata

The second command downloads two model files (81 MB and 335 MB). The app listens on http://127.0.0.1:8080 only.

## What a fresh clone can run

The test files hold 294 tests. That number is a count of what they contain and the result of the runs in `LOG.md` on my machine. It is not the result of a run on a fresh clone.

- 19 of them need audio, labels and my listening marks, which are not in git. Without that material they skip.
- The others need the model files, `ffmpeg`, `node`, a browser and sound output. Without the model files about 90 of them fail at start.
- Only those 19 run the beat tracker on real music, so the accuracy figures in the records cannot be reproduced from this repository alone.

## The records

- `BRIEF.md`: what the project is for and its five slices.
- `ACCEPTANCE.md`: the checks, ticked only when a named check ran.
- `LOG.md`: every run and its result, newest first.
- `NEXT.md`: the state of the project and what comes next.
- `CAPSTONE.md`: the brief and the checks of the last feature.
- `course/`: material cited in my course report.

The records were written during the work, so some of their statements became wrong later. Notes dated 2026-10-12 correct them. The earlier lines are kept, and those commits delete no line. `SPEC.md` and `fixtures/audio/README.md`, which the records name, are not in git.

The branches `d4-graph` and `integrator-stopped` hold a side experiment with a workflow that is not merged. The tags `d4-bars` and `bars-high` keep two builds that were not merged: a first attempt that I rejected, and the build at effort high of a comparison.

## How it was made

Claude Code sessions wrote the code and the records, between 5 and 9 October 2026 (commit dates, +0700). I gave the tasks, answered their questions, listened and looked, and accepted or rejected the results. It was my project for a company course on AI-driven development. A second Claude session helped me check that I was applying the course and kept the details for my report.

In the records "the owner" is me, and "a session" is a Claude Code session. "A session of another tool" is Codex, and its two reviews are in `course/`.

## Personal data and the history of this repository

This repository is public, so some personal data, like the folders of my machine, was redacted before publishing. To do that the history was rewritten once, on 2026-10-11, before the first push.

What was changed, in every commit that contained it:

- the path of this project's working folder on my machine, replaced by `<repo>`;
- the path of my own music folder, which is not part of the repository, replaced by `<music-library>/`.

What was not changed: the number of commits and their order, their author, their dates, their messages (except two that quote a commit identifier, which was updated) and every other byte of every file.

What follows from it:

- Every commit from the seventh on has a different identifier from the one it had when it was made. `HISTORY.md` lists both for each commit.
- The records were written before that. In their versions of that time they quote the earlier identifiers. The commit `8a76d39` updated the identifiers quoted in the current records.
- The two tags were created on 2026-10-11. Their messages say so.

## Third-party material

- Beat This: MIT. madmom: its code is BSD and its models are CC BY-NC-SA; only its decoder is used. Both according to `LOG.md`, not checked again.
- The Hybrid Demucs model: its licence was not checked.
- The Hind font: SIL Open Font License, in `web/fonts/`.
- The songs and the labels come from emusicality.co.uk and from my own library. They are not in git, and I have not checked their terms.
- This repository has no licence file.
