# Acceptance list

An item is ticked only after its check has been run and the result is in `LOG.md`.

Items marked *proposed* contain a number or a rule that is not in the brief. The owner confirms or changes them.

## How a song result is judged

Against the reference fixtures in `fixtures/labels/`. A fixture says, for one exact recording, where every derecho, majao and mambo section starts and ends, and marks everything else as `other`. The format is described at the top of `fixtures/validate.js`.

No song item can be ticked until there is at least one fixture with its audio. Today there is none.

**Same beat** (*proposed*): two times are the same beat when they are within 70 ms of each other. That is the usual window for judging beat trackers. It only works if the reference times are that precise, which is unknown until the website has been looked at.

## Setup

- [x] `npm start` serves the page, on 127.0.0.1 only.
- [x] `npm test` passes.
- [x] The reference material has a fixture format, a place in the repository and a validator.

## The whole application

- [ ] **G1** For every fixture, the output has the same derecho, majao and mambo sections as the reference, in the same order.
- [ ] **G2** Every section starts on its first beat and ends on its last beat: both times are the same beat as the reference.
- [ ] **G3** Nothing is invented: no output section falls in a part the reference marks `other`.
- [ ] **G4** The user can pick an existing song or upload a new one, and gets the sections for either.
- [ ] **G5** Everything runs locally: marking a song sends nothing to another machine and uses no paid API.
- [ ] **G6** It runs fluid. *No measure set yet.*
- [ ] **G7** It is secure for the user and for the machine that serves it. *No checks set yet. They depend on whether an uploaded song leaves the browser.*
- [ ] **G8** Visuals and UX are great. The owner judges this; no automatic check.

## Slices

Each slice takes a song and shows a visible result.

### 1. Beats and tempo

- [ ] It shows the song's tempo and where its beats are.
- [ ] Every section start and end in the reference is the same beat as a detected beat.
- [ ] The tempo is the one a dancer counts, not half or double. *No reference for tempo yet.*

### 2. The grid of ochos

- [ ] It shows the count of every beat and where each ocho starts, half phrases included.
- [ ] Every section start in the reference lands on a count 1. *Proposed: this assumes a section always starts on count 1.*
- [ ] On a song known to have a half phrase, the half phrase is found where the owner says it is. *Needs such a song.*

### 3. Derecho or majao for each ocho

- [ ] It shows, for each ocho, derecho, majao or neither.
- [ ] Every ocho inside a derecho or majao section of the reference gets that label.
- [ ] No ocho inside an `other` part of the reference gets a label.

### 4. Mambo, so the full timeline

- [ ] G1, G2 and G3 hold on every fixture.

### 5. The screen

- [ ] The timeline of sections is on screen while the song plays, and the playing position sits in the section that is sounding.
- [ ] G4, G6 and G8 hold.
