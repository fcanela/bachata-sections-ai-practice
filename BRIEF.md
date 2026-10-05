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

## What we know about the music

- Dancers make sense of the music in groups of two bars. That group is a **phrase**, informally an **ocho**.
- Sometimes there is an extra bar, a **half phrase**. When it happens, it is usually after 4 phrases (8 bars).
- Derecho, majao and mambo are rhythms played by the percussion, mostly the güira and the bongos.
- Derecho is usually in the verses, majao in the choruses and mambo in the instrumental breaks.
- A song also has parts that are none of the three, like the intro or a break.
- Modern songs can add other rhythms.

## Plan: five slices

Each slice takes a song and shows a visible result.

1. Beats and tempo.
2. The grid of ochos: which beat is count 1, including the half phrase.
3. Derecho or majao for each ocho.
4. Mambo, so the full timeline of sections.
5. A screen that shows the timeline while the song plays.

## Reference material

- The website is emusicality.co.uk. It publishes songs as separate instrument tracks, with a breakdown of each song's parts and rhythms.
- The owner keeps the material in `fixtures/audio/`, which git ignores. Nothing from the site is committed, neither the audio nor the labels. `fixtures/audio/README.md` describes it.
- Three songs come from the site, each with its tracks, a mix of them and a label file: Me Emborrachare (the main song), Eso Es Amor and Old Town Road (bachata remix).
- Two commercial recordings with vocals have no labels: the full Me Emborracharé and El Perdedor.

## Limits

- Everything runs locally. No paid API.
- No backward compatibility, no extra features, no abstractions for later.
- The analysis runs on the local server, not in the browser. Decided on 2026-10-05: on the server the beat tracker runs as its authors published it, and more tools are available for the later slices. The cost is that every song is sent to the machine that serves the application.
- Uploaded songs are kept in one library on the server. Everyone who can reach the application can play every song in it.

## The other three files

- `ACCEPTANCE.md`: what has to be true for the application and for each slice to count as done.
- `LOG.md`: what was run in each session, what it showed and what it cost, plus the decisions taken.
- `NEXT.md`: where things stand and what to do next.
