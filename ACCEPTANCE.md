# Acceptance list

An item is ticked only after its check has been run and the result is in `LOG.md`.

Items marked *proposed* contain a number or a rule that is not in the brief. The owner confirms or changes them.

## How a song result is judged

Against the reference material in `fixtures/audio/dev/`, which is not committed. Each song from the site has a folder there with a `mix.m4a` and a `labels.json`. `fixtures/audio/README.md` describes the format.

- **The checks read those files where they are.** When the material is not on the machine they print "skipped: no reference material". A song item cannot be ticked from a run that skipped.
- **The input is always the mix**, never the separate instrument tracks. Someone using the application uploads a whole recording.
- **The labels give every beat.** Each label file has a tempo, the time of the first beat and a number of beats, so beat *n* is at `first beat + n × 60 / bpm`.
- **The audio decides where a beat is.** The labels' tempo and beat counts are exact, but their times are early by a constant amount per song (104, 72 and 49 ms, measured in session 2). The first-beat time is therefore measured on the percussion of each mix and written into `labels.json` as a new field, beside the sha256 of the mix it was measured on. A mix whose hash no longer matches is measured again before anything is compared with it.
- **Same beat:** two times are the same beat when they are within 70 ms of each other. The owner allows up to 120 ms if the measurements show that 70 is too tight; the reason then goes in `LOG.md`.
- **Songs without labels** are the two commercial recordings. They get one automatic check on the tempo, and the owner's ear is the final word.

## Setup

- [x] `npm start` serves the page, on 127.0.0.1 only.
- [x] `npm test` passes.
- [x] The reference material has a fixture format, a place in the repository and a validator.

These three are true of the Node program of session 1. A Python program replaces it in slice 1 and the validator changes to the site's label format. The three items are then reworded and checked again.

## The whole application

- [ ] **G1** For every fixture, the output has the same derecho, majao and mambo sections as the reference, in the same order. *Open: the labels treat mambo as a part of the song whose rhythm is majao or derecho, not as a rhythm. See `NEXT.md`.*
- [ ] **G2** Every section starts on its first beat and ends on its last beat: both times are the same beat as the reference. In the labels a section's `end_s` is the start of the next section, so its last beat is one beat earlier.
- [ ] **G3** Nothing is invented: no output section falls in a part the reference marks `other`.
- [ ] **G4** The user can pick an existing song or upload a new one, and gets the sections for either. An existing song is a song in the server's library. The library is built in slice 1; this item is checked in slice 5, when the list has its real screen and the result is sections.
- [ ] **G5** Everything runs locally: marking a song sends nothing beyond the machine that serves the application and uses no paid API.
- [ ] **G6** It runs fluid. *No measure set yet. The owner has no expectation on analysis time yet; slice 1 measures it and the owner adjusts.*
- [ ] **G7** It is secure for the user and for the machine that serves it. The checks for the upload and the library are under slice 1. Later slices may add more.
- [ ] **G8** Visuals and UX are great. The owner judges this; no automatic check.

## Slices

Each slice takes a song and shows a visible result. There are five and the number does not change; new work is fitted into one of them.

### 1. Beats and tempo

The owner picks a file, mp3 or m4a, or a song from the list of remembered ones. The page shows a strip with one tick per beat, a marker that moves along it while the song plays, the BPM at the playing position, and a click on every beat that can be switched off. The ticks are not numbered; the count 1 to 8 arrives in slice 2.

Uploaded songs are remembered in one library on the server, the same for everyone who can reach the application.

Slice 1 is done when every item below holds, on all three mixes and both commercial recordings. Me Emborrachare comes first, and the beats are built before the library.

**The three mixes, checked automatically**

- [ ] From the first labelled beat to the last, every labelled beat has exactly one detected beat that is the same beat, and there is no detected beat without a labelled one. If a part with no clear pulse makes this impossible, the numbers go to the owner, who decides. The item is not loosened any other way.
- [ ] At every labelled beat, the shown BPM is within 4% of the label's BPM. That is the tempo a dancer counts, not half or double. *Proposed: the 4%.*

**The two commercial recordings**

- [ ] The shown BPM is within 4% of 124 on the full Me Emborracharé and of 128 on El Perdedor, once the owner confirms those are the counts a dancer steps. Both figures come from a rough measurement in session 2. *Proposed: the 4%.*
- [ ] By the owner's ear: with the click on, the click is on the beat wherever the owner can count the song.

**The page**

- [ ] It shows the strip, the moving marker, the BPM at the playing position and the click switch.
- [ ] By the owner's ear: with the click on, the click is on the beat through the whole song, on each of the three mixes.

**The library**

- [ ] An uploaded song is kept on the server with its results. It appears in the list in every browser, with its name and its state: waiting, being analysed, ready or failed.
- [ ] A song opened from the list plays and shows its beats in a browser that never had the file. Nothing is uploaded and nothing is analysed.
- [ ] A file that is already in the library, byte for byte, is not uploaded, not stored twice, and not analysed twice by the same version of the analysis. The stored song opens.
- [ ] A result made by an older version of the analysis is replaced: the server analyses the song again from the stored sound, with no upload.
- [ ] The name comes from the file's title and artist tags when it has them, and from the file name without its extension otherwise.
- [ ] Songs are analysed one at a time, in the order they arrived. A song whose analysis fails is marked failed and does not stop the next one.
- [ ] Any song can be deleted, with one confirmation, whatever its state. Deleting a waiting song takes it out of the queue.
- [ ] The library and the queue survive a restart of the program.

**What is refused, part of G7**

By the page, before anything is sent:

- [ ] A file that is not mp3 or m4a, or that the browser cannot decode.
- [ ] A song shorter than 20 seconds or longer than 15 minutes.

By the server, which cannot trust what a page checked:

- [ ] Anything from another machine: the program listens on 127.0.0.1 only.
- [ ] Any request that changes the library (an upload, a deletion, a removal from the queue) and does not come from the application's own page.
- [ ] A body that is not the expected sample format, or that holds less than 20 seconds or more than 15 minutes of sound.
- [ ] A song id that is not well formed, and a name longer than 200 characters. *Proposed: the 200.*
- [ ] A new song when the library has reached 20 GB.

What the server never does:

- [ ] It never reads a media file made elsewhere. It receives plain samples and stores the sound in its own packing.
- [ ] It writes only inside one data folder. File names on disk come from the song's id, never from text a page sent.
- [ ] It sends stored sound back only as sound data, never as a page. Names are always shown as plain text.
- [ ] It sends every answer with the security headers.

**How these are tested**

- Logic is covered by unit tests beside the code.
- Whole flows through the page are covered by end-to-end tests in a real browser: an upload, the list, opening a song in a browser that never had the file, a second upload of the same file, a deletion, a file of the wrong type, a song that is too short.
- The two by-ear items are the owner's.

**Not verified in slice 1**

- Following a tempo change. None of the five songs has one that a rough measurement can see, so there is nothing to check it against. The tracker must still not assume one tempo for the whole song. If the owner hears a shift in El Perdedor with the click on, that moment becomes a test spot.
- Analysis time. It is measured and logged, with no limit to pass.

### 2. The grid of ochos

- [ ] It shows the count of every beat and where each ocho starts, half phrases included.
- [ ] Every section start in the reference lands on a count 1. *Proposed: this assumes a section always starts on count 1.*
- [ ] On a song known to have a half phrase, the half phrase is found where the owner says it is. Eso Es Amor has four labelled half phrases.

### 3. Derecho or majao for each ocho

- [ ] It shows, for each ocho, derecho, majao or neither.
- [ ] Every ocho inside a derecho or majao section of the reference gets that label.
- [ ] No ocho inside an `other` part of the reference gets a label. *Open: which of the labels' rhythms count as `other`, and which wins when a section's rhythm and its blocks disagree. See `NEXT.md`.*

### 4. Mambo, so the full timeline

- [ ] G1, G2 and G3 hold on every fixture.

### 5. The screen

- [ ] The timeline of sections is on screen while the song plays, and the playing position sits in the section that is sounding.
- [ ] G4, G6 and G8 hold.
