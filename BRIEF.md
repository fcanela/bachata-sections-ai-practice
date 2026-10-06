# Brief: Bachata sections

A web application that takes a bachata song and marks its sections.

## Goal

The user gives it a song and it tells them where each section starts and ends.

- The sections are **derecho**, **majao** and **mambo**.
- A section starts on its first beat and ends on its last beat.
- It must not invent sections that are not there.
- The user can mark an existing song or upload a new one.
- It has great visuals and UX.
- It runs fluid.
- It is secure, both for the user and for the machine that serves it.

## Who it is for

The owner answered these on 2026-10-05, in session 4.

- The user is a dancer learning musicality: a social dancer who wants to hear and anticipate the changes between derecho, majao and mambo in the songs they dance to.
- They use it in two situations:
  - at a desk, with their eyes on the screen;
  - on their feet, practising a few metres from the screen and glancing at it now and then.
- It is a private tool. The owner uses it on localhost, in desktop Chrome and Firefox.
- A few coworkers may get it later, to show them how bachata works. That is not the goal.
- A public version is possible later. It would be a major refactor, with accounts and more security. Nothing is designed for it now.
- What sets it apart from emusicality's breakdowns: it marks any recording the user gives it, automatically, on their own machine. Emusicality covers the songs its authors broke down by hand.

## The interface

Also answered on 2026-10-05, in session 4.

- The name is "Bachata sections".
- The interface is in English. The rhythm names stay in Spanish: derecho, majao, mambo, ocho.
- Its sentences are short and plain, like "Delete this song?" and "This is not an mp3, m4a or opus file."
- A section is never told apart by colour alone. Its name, its position or its shape identifies it too.
- While a song plays, the first thing the dancer reads is where the song is now: the section and the count. What comes next, and the shape of the whole song, come second.
- One screen serves the desk and the distance. There is no separate view for practising.
- The user can jump to a section, replay a part of the song in a loop, and rename a song. Play, pause and the position also work from the keyboard.
- The user can say where count 1 is, with one control: "Count 1 here". From that beat the count runs in eights. The application cannot yet hear which of two bars starts an ocho, nor where a bar is extra; until it does, this is how a wrong count is put right. Decided on 2026-10-06, in session 6, with the words "one simple control, nothing more".
- A marked range can be taken away again, with "Clear". Switching the loop off keeps the range. Asked for by the owner on 2026-10-06, after using the page.
- Every song has an address of its own. Loaded again, or opened from a link, the page opens that song. Asked for by the owner on 2026-10-06.
- A song is an mp3, an m4a or an opus file. Opus was added by the owner on 2026-10-06.
- A replay is of one section by itself, without the change into the next one. Until the application finds sections, the user marks the range to loop by hand. Decided on 2026-10-05, in session 5.
- The page has a light and a dark ground, and takes the one the system is set to. Decided on 2026-10-05, in session 5.
- The page looks after airport sign systems. Where the song is hangs as a yellow sign band with black type; everything else is on black panels, over a ground of concrete grey by day and black by night. A beat is a small square, and the one that is sounding gets the large square a sign keeps for its pictogram. The typeface is Hind. The owner chose this among three designs on 2026-10-05, in session 5.

## What we know about the music

- Dancers make sense of the music in groups of two bars. That group is a **phrase**, informally an **ocho**.
- Sometimes there is an extra bar, a **half phrase**. When it happens, it is usually after 4 phrases (8 bars).
- A half phrase is counted 1 to 4, and the next ocho starts on 1. A section starts on count 1. The owner's answers of 2026-10-06, in session 6.
- Derecho, majao and mambo are rhythms played by the percussion, mostly the güira and the bongos.
- Derecho is usually in the verses, majao in the choruses and mambo in the instrumental breaks.
- A song also has parts that are none of the three, like the intro or a break.
- Modern songs can add other rhythms.

## Plan: five slices

Each slice takes a song and shows a visible result.

1. Beats and tempo.
2. The grid of ochos: which beat is count 1, including the half phrase. Since session 6 this slice answers for the bar, which beat is the first of four, and shows the count from 1 to 8 as well as it can. The count and the half phrase are answered for in slice 4, where the sections say where the count starts again.
3. Derecho or majao for each ocho.
4. Mambo, so the full timeline of sections.
5. A screen that shows the timeline while the song plays.

The screen of slice 5 is built early, after slice 1, with what slice 1 has. Each later slice puts its result in its place on it. Decided on 2026-10-05, in session 4.

## Reference material

- The website is emusicality.co.uk. It publishes songs as separate instrument tracks, with a breakdown of each song's parts and rhythms.
- The owner keeps the material in `fixtures/audio/`, which git ignores. Nothing from the site is committed, neither the audio nor the labels. `fixtures/audio/README.md` describes it.
- Three songs come from the site, each with its tracks, a mix of them and a label file: Me Emborrachare (the main song), Eso Es Amor and Old Town Road (bachata remix).
- Two commercial recordings with vocals have no labels: the full Me Emborracharé and El Perdedor.

## Limits

- Everything runs locally. No paid API.
- No backward compatibility, no extra features, no abstractions for later. The jump, the loop and the renaming under "The interface" are the owner's additions of 2026-10-05, and count 1 by hand, clearing a marked range, the address of a song and opus files are the owner's additions of 2026-10-06. They are not extras.
- The analysis runs on the local server, not in the browser. Decided on 2026-10-05: on the server the beat tracker runs as its authors published it, and more tools are available for the later slices. The cost is that every song is sent to the machine that serves the application.
- Uploaded songs are kept in one library on the server. Everyone who can reach the application can play every song in it.

## The other files

- `ACCEPTANCE.md`: what has to be true for the application and for each slice to count as done.
- `LOG.md`: what was run in each session, what it showed and what it cost, plus the decisions taken.
- `NEXT.md`: where things stand and what to do next.
- `PRODUCT.md`: a pointer for the Impeccable design plugin, which looks for a file of that name. It gives the platform and sends the reader to this brief. It holds no product fact of its own.
