// The page: adding a song, the list of remembered songs, and playing one with its beats
// and their count.

import {
  MAX_NAME,
  MAX_SECONDS,
  MIN_SECONDS,
  RATE,
  beatsUntil,
  bpmAt,
  channelsFrom16,
  cleanName,
  clicksUntil,
  clock,
  countsWith,
  idOf,
  interleaved16,
  kindOf,
  loopOf,
  nameFor,
  nearestBeat,
  ochoOf,
  ochosOf,
  tagsOf,
  wrapped,
} from './song.js'
import { beatAt, drawMap, drawNow, forgetTokens, mapLayout, markOf, nowLayout, rowOf } from './draw.js'

const $ = (id) => document.getElementById(id)

// A message about adding a song, beside the control that adds one. `part` is how much of
// the song has been sent, from 0 to 1, while it is being sent.
function say(text, refused = false, part = null) {
  $('message').textContent = text
  $('message').title = text
  $('message').classList.toggle('refused', refused)
  $('sending').hidden = part === null
  if (part !== null) $('sending').value = part
}

// A file is always decoded at 44.1 kHz. An ordinary audio context would resample it to the
// machine's own rate without saying so, and the beats are measured on these samples.
const decode = (bytes) => new OfflineAudioContext(2, 1, RATE).decodeAudioData(bytes)

// The stored sound needs no decoding: it is the samples themselves, 16 bits each, left and
// right in turn, in the byte order of every machine a browser runs on today.
function soundFrom(bytes) {
  const channels = channelsFrom16(new Int16Array(bytes))
  const sound = new AudioBuffer({ numberOfChannels: 2, length: channels[0].length, sampleRate: RATE })
  channels.forEach((channel, i) => sound.copyToChannel(channel, i))
  return sound
}

const read = (address) => fetch(address, { cache: 'no-store' })

// The body of an answer, read piece by piece so that `progress` hears how far it is.
async function bytesOf(answer, progress) {
  const length = Number(answer.headers.get('content-length'))
  if (!answer.body || !length) return answer.arrayBuffer()
  const bytes = new Uint8Array(length)
  const reader = answer.body.getReader()
  let received = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    bytes.set(value, received)
    received += value.length
    progress(received / length)
  }
  return bytes.buffer
}

// Sends an upload. `progress` hears how much of it has left, from 0 to 1.
function send(address, body, progress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('PUT', address)
    request.upload.addEventListener('progress', (event) => event.lengthComputable && progress(event.loaded / event.total))
    request.addEventListener('load', () => resolve({ ok: request.status >= 200 && request.status < 300, status: request.status, text: request.responseText }))
    request.addEventListener('error', () => reject(new Error('not sent')))
    request.send(body)
  })
}

// ---- Adding a song

$('file').addEventListener('change', async () => {
  const file = $('file').files[0]
  $('file').value = ''
  if (!file) return
  try {
    await add(file)
  } catch {
    say('Something went wrong. The song was not added.', true)
  }
})

async function add(file) {
  say(`Reading ${file.name}…`)
  const bytes = new Uint8Array(await file.arrayBuffer())
  if (!kindOf(bytes)) return say('This is not an mp3 or m4a file.', true)

  // A file the library already has is not sent again: the stored song opens.
  const id = idOf(await crypto.subtle.digest('SHA-256', bytes))
  if ((await read(`/api/songs/${id}`)).ok) {
    say('This song is already in the library.')
    return openWhenReady(id)
  }

  say(`Decoding ${file.name}…`)
  let sound
  try {
    // Decoding empties the buffer it is given, and the tags are still to be read.
    sound = await decode(bytes.slice().buffer)
  } catch {
    return say('The browser cannot decode this file.', true)
  }
  if (sound.length < MIN_SECONDS * RATE) return say(`This song is shorter than ${MIN_SECONDS} seconds.`, true)
  if (sound.length > MAX_SECONDS * RATE) return say(`This song is longer than ${MAX_SECONDS / 60} minutes.`, true)

  const name = nameFor(tagsOf(bytes), file.name)
  const right = sound.getChannelData(sound.numberOfChannels > 1 ? 1 : 0)
  const samples = interleaved16(sound.getChannelData(0), right)
  say(`Sending ${name}…`, false, 0)
  const query = new URLSearchParams({ name, rate: RATE, frames: sound.length })
  const answer = await send(`/api/songs/${id}?${query}`, samples, (part) => say(`Sending ${name}…`, false, part))
  // 409: another browser sent the same song in the meantime.
  if (!answer.ok && answer.status !== 409) return say(`The server refused the song. ${answer.text.trim()}`, true)
  say(`${name} is in the library. It opens when it has been analysed.`)
  return openWhenReady(id)
}

// ---- The list

const STATES = { waiting: 'waiting', analysing: 'being analysed', ready: 'ready', failed: 'failed' }

let songs = []
const rows = new Map() // the rows on screen, by song: { row, from }, where `from` is what the row was built from
let confirming = null // the song whose deletion waits for its confirmation
let renaming = null // the name that is being typed: { id, where, draft }, where is 'row' or 'title'
let opening = null // the song that is being fetched: { id, part }
let wanted = null // the song to open as soon as it is ready
let focusNext = null // where the keyboard goes once the list is on screen again: { id, where, key }
const notes = new Map() // what went wrong with a song, shown in its row: id, or 'title', to { text, refused }

async function refresh() {
  let response
  const asked = counting
  try {
    response = await read('/api/songs')
  } catch {
    return
  }
  if (!response.ok) return
  songs = await response.json()
  // A count 1 set in another browser. A list that was asked for before this browser's
  // own last change may not have it yet, and is not believed.
  const playing = songs.find((song) => song.id === player.id)
  if (playing && asked === counting && String(playing.ones) !== String(player.ones)) recount(playing.ones)
  for (const id of notes.keys()) if (id !== 'title' && !songs.some((song) => song.id === id)) notes.delete(id)
  if (renaming && !songs.some((song) => song.id === renaming.id)) renaming = null
  if (player.id && !songs.some((song) => song.id === player.id)) closePlayer('The song was deleted.')
  showSongs()
  if (!player.id && !opening && !nothingSaid) showNothing()
  const song = songs.find((candidate) => candidate.id === wanted)
  if (song?.state === 'ready') {
    wanted = null
    await open(song)
  } else if (wanted && (!song || song.state === 'failed')) {
    wanted = null
    say(song ? `The analysis of ${song.name} failed.` : 'The song was deleted.', true)
  }
}

function openWhenReady(id) {
  wanted = id
  return refresh()
}

function element(tag, className, text) {
  const made = document.createElement(tag)
  if (className) made.className = className
  if (text !== undefined) made.textContent = text
  return made
}

// `key` names the button inside its row, so the keyboard can be put back on it.
function button(text, action, key, className) {
  const made = element('button', className, text)
  made.type = 'button'
  made.dataset.focus = key
  made.addEventListener('click', action)
  return made
}

function noteOf(key) {
  const note = notes.get(key)
  if (!note) return null
  const line = element('p', note.refused ? 'note refused' : 'note', note.text)
  line.setAttribute('role', 'status')
  return line
}

// The field a name is typed into, in a row of the list or in the top bar. Enter keeps
// the name and Escape leaves it as it was.
function nameField(song) {
  const group = element('div', 'rename')
  const field = element('input')
  field.type = 'text'
  field.value = renaming.draft
  field.maxLength = MAX_NAME
  field.autocomplete = 'off'
  field.spellcheck = false
  field.dataset.focus = 'name'
  field.setAttribute('aria-label', 'Name of the song')
  field.addEventListener('input', () => {
    renaming.draft = field.value
  })
  field.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') rename(song)
    if (event.key === 'Escape') stopRenaming()
  })
  group.append(field, button('Save', () => rename(song), 'save', 'primary'), button('Cancel', stopRenaming, 'cancel'))
  return group
}

function rowFor(song) {
  const row = element('li')
  row.dataset.id = song.id
  row.dataset.state = song.state
  const isOpen = player.id === song.id
  const isRenaming = renaming?.id === song.id && renaming.where === 'row'
  if (isOpen) row.setAttribute('aria-current', 'true')

  if (isRenaming) {
    row.append(nameField(song))
  } else {
    // A name is text someone typed or tagged: it is only ever put on screen as text.
    const name = element('span', 'name', song.name)
    name.title = song.name
    row.append(name)
  }
  row.append(element('span', 'state', `${clock(song.seconds)}, ${STATES[song.state]}`))

  const actions = element('div', 'actions')
  if (opening?.id === song.id) {
    row.setAttribute('aria-busy', 'true')
    const bar = element('progress')
    bar.max = 1
    bar.value = opening.part
    bar.setAttribute('aria-label', `Opening ${song.name}`)
    actions.append(element('span', 'current', 'Opening…'), bar)
  } else if (confirming === song.id) {
    actions.append(
      element('span', 'question', 'Delete this song?'),
      button('Yes, delete', () => remove(song), 'yes'),
      button('Keep', () => askToDelete(null, song.id), 'keep'),
    )
  } else if (!isRenaming) {
    if (isOpen) actions.append(element('span', 'current', 'Open now'))
    else if (song.state === 'ready') actions.append(button('Open', () => open(song), 'open'))
    actions.append(
      button('Rename', () => startRenaming(song, 'row'), 'rename', 'quiet'),
      button('Delete', () => askToDelete(song.id), 'delete', 'quiet'),
    )
  }
  if (actions.childElementCount) row.append(actions)
  const note = noteOf(song.id)
  if (note) row.append(note)
  return row
}

// Puts the list and the name of the open song on screen, then the keyboard where the
// last action left it.
function showSongs() {
  showList()
  showTitle()
  if (!focusNext) return
  const { id, where, key } = focusNext
  focusNext = null
  const inside = where === 'title' ? $('title') : rows.get(id)?.row
  const control = inside?.querySelector(`[data-focus="${key}"]`)
  control?.focus()
  if (control?.type === 'text') control.select()
}

// A row is made again only when something it shows has changed, so a name that is being
// typed, and the place of the keyboard, survive the list being asked for every two seconds.
function showList() {
  $('empty').hidden = songs.length > 0
  const list = $('songs')
  for (const song of songs) {
    const from = JSON.stringify([
      song,
      player.id === song.id,
      confirming === song.id,
      renaming?.id === song.id && renaming.where,
      opening?.id === song.id,
      notes.get(song.id),
    ])
    const shown = rows.get(song.id)
    if (shown?.from === from) continue
    const row = rowFor(song)
    if (shown) {
      // The keyboard stays on the control it was on, if the row still has it.
      const held = shown.row.contains(document.activeElement) ? document.activeElement : null
      shown.row.replaceWith(row)
      if (held && !focusNext) {
        const again = row.querySelector(`[data-focus="${held.dataset.focus}"]`)
        again?.focus()
        if (again?.type === 'text') again.setSelectionRange(held.selectionStart, held.selectionEnd)
      }
    }
    rows.set(song.id, { row, from })
  }
  for (const [id, shown] of rows) {
    if (songs.some((song) => song.id === id)) continue
    shown.row.remove()
    rows.delete(id)
  }
  const order = songs.map((song) => song.id)
  if ([...list.children].map((row) => row.dataset.id).join() !== order.join()) {
    list.replaceChildren(...order.map((id) => rows.get(id).row))
  }
}

// The name of the open song, in the top bar, or the field it is renamed in.
function showTitle() {
  const song = songs.find((candidate) => candidate.id === player.id)
  const title = $('title')
  title.hidden = !song
  if (!song) return
  const isRenaming = renaming?.id === song.id && renaming.where === 'title'
  const from = JSON.stringify([song.name, isRenaming, notes.get('title')])
  if (title.dataset.from === from) return
  title.dataset.from = from
  $('song-name').textContent = song.name
  $('song-name').title = song.name
  $('song-name').hidden = isRenaming
  $('rename-open').hidden = isRenaming
  title.querySelector('.rename')?.remove()
  title.querySelector('.note')?.remove()
  if (isRenaming) title.append(nameField(song))
  const note = noteOf('title')
  if (note) title.append(note)
}

$('rename-open').dataset.focus = 'rename'
$('rename-open').addEventListener('click', () => {
  const song = songs.find((candidate) => candidate.id === player.id)
  if (song) startRenaming(song, 'title')
})

// One confirmation: the row asks, and only then is the song deleted.
function askToDelete(id, kept = null) {
  confirming = id
  if (id) notes.delete(id)
  focusNext = id ? { id, key: 'keep' } : { id: kept, key: 'delete' }
  showSongs()
}

async function remove(song) {
  confirming = null
  let failed = false
  try {
    const response = await fetch(`/api/songs/${song.id}`, { method: 'DELETE' })
    failed = !response.ok && response.status !== 404
  } catch {
    failed = true
  }
  if (failed) notes.set(song.id, { text: `${song.name} could not be deleted.`, refused: true })
  await refresh()
}

function startRenaming(song, where) {
  renaming = { id: song.id, where, draft: song.name }
  confirming = null
  notes.delete(where === 'title' ? 'title' : song.id)
  focusNext = { id: song.id, where, key: 'name' }
  showSongs()
}

function stopRenaming() {
  if (!renaming) return
  const { id, where } = renaming
  renaming = null
  notes.delete(where === 'title' ? 'title' : id)
  focusNext = { id, where, key: 'rename' }
  showSongs()
}

async function rename(song) {
  if (renaming?.id !== song.id) return
  const { where } = renaming
  const key = where === 'title' ? 'title' : song.id
  const refuse = (text) => {
    notes.set(key, { text, refused: true })
    focusNext = { id: song.id, where, key: 'name' }
    showSongs()
  }
  const name = cleanName(renaming.draft)
  if (!name) return refuse('A song needs a name.')
  if (name === song.name) return stopRenaming()
  let response
  try {
    response = await fetch(`/api/songs/${song.id}?${new URLSearchParams({ name })}`, { method: 'PATCH' })
  } catch {
    return refuse(`${song.name} could not be renamed.`)
  }
  // 404: the song was deleted in another browser. The list says so when it is asked for.
  if (!response.ok && response.status !== 404) return refuse(`The server refused the name. ${(await response.text()).trim()}`)
  stopRenaming()
  await refresh()
}

// ---- Playing a song

// The sound that plays is always the one the server stored, never the file that was
// picked: the beats were found on the stored samples, so the click lines up with them.
const player = {
  id: null,
  buffer: null, // the stored sound
  result: null, // { beats, bpm, bar, count }, as the analysis made them
  ones: [], // the times of the beats the user set to count 1
  count: [], // the count of every beat, with those
  byHand: new Set(), // the beats the user set to count 1
  ochos: [], // the ochos that count makes, each { first, last }
  context: null,
  source: null, // the sound that is playing
  playing: false,
  offset: 0, // where in the song the playing started, or stopped, in seconds
  startedAt: 0, // the time of the audio clock at which the playing started
  range: { first: null, last: null }, // the beats marked for a loop, both included. Either may be missing
  looping: false, // whether the playing goes round the marked range
  loop: null, // the seconds the sound that is playing goes round: { start, end }, or null
  clickSound: null,
  clickGain: null,
  clicks: [], // the clicks handed to the audio clock that may not have sounded yet
  nextClick: { beat: 0, pass: 0 }, // the first beat that has no click scheduled, and the pass of the loop it is in
  timer: null,
}

const reduced = matchMedia('(prefers-reduced-motion: reduce)')

let nothingSaid = false // whether the middle of the page says something of its own

// What the middle of the page says while no song is open: `text`, or how to get one.
function showNothing(text) {
  nothingSaid = text !== undefined
  $('player').hidden = true
  $('nothing').hidden = false
  $('nothing-text').textContent = text ?? (songs.length ? 'Open a song from the list, or add one.' : 'Add a song to see its beats.')
}

function showPlayer() {
  $('nothing').hidden = true
  $('player').hidden = false
}

async function open(song) {
  pause()
  notes.delete(song.id)
  confirming = null
  opening = { id: song.id, part: 0 }
  if (!player.id) showNothing(`Opening ${song.name}…`)
  showSongs()
  let result, buffer
  try {
    const [resultAnswer, soundAnswer] = await Promise.all([read(`/api/songs/${song.id}/result`), read(`/api/songs/${song.id}/sound`)])
    if (!resultAnswer.ok || !soundAnswer.ok) throw new Error('not there')
    result = await resultAnswer.json()
    const bytes = await bytesOf(soundAnswer, (part) => {
      if (opening?.id !== song.id) return
      opening.part = part
      const bar = rows.get(song.id)?.row.querySelector('progress')
      if (bar) bar.value = part
    })
    buffer = soundFrom(bytes)
  } catch {
    if (opening?.id !== song.id) return
    opening = null
    notes.set(song.id, { text: `${song.name} could not be opened.`, refused: true })
    if (!player.id) showNothing()
    return showSongs()
  }
  // Another song was asked for while this one was on its way.
  if (opening?.id !== song.id) return
  opening = null
  pause()
  Object.assign(player, { id: song.id, buffer, result, offset: 0, range: { first: null, last: null }, looping: false })
  $('duration').textContent = clock(buffer.duration)
  $('seek').max = buffer.duration
  $('now').dataset.beats = result.beats.length
  for (const control of ['play', 'seek', 'loop-start', 'loop-end']) $(control).disabled = false
  $('one').disabled = result.beats.length === 0
  $('one-note').textContent = ''
  say('')
  showPlayer()
  showSongs()
  showLoop()
  // The list may have moved on while the song was fetched.
  recount((songs.find((candidate) => candidate.id === song.id) ?? song).ones)
  $('song').scrollTop = 0
  // The button that opened the song is gone from its row: the keyboard goes to Play.
  if (document.activeElement === document.body) $('play').focus()
}

function closePlayer(text) {
  pause()
  Object.assign(player, { id: null, buffer: null, result: null, offset: 0, range: { first: null, last: null }, looping: false })
  Object.assign(player, { ones: [], count: [], byHand: new Set(), ochos: [] })
  for (const control of ['play', 'seek', 'loop', 'loop-start', 'loop-end', 'one']) $(control).disabled = true
  $('position').textContent = $('where').textContent = $('duration').textContent = clock(0)
  $('seek').value = 0
  showNothing(text)
  showLoop()
  showSongs()
}

// How long the song has been playing since its start, in seconds, by the audio clock.
// With a loop this goes on growing while the song goes round.
function played() {
  return player.offset + Math.max(0, player.context.currentTime - player.startedAt)
}

// Where the playing is in the song, in seconds.
function position() {
  if (!player.playing) return player.offset
  return Math.min(player.buffer.duration, wrapped(played(), player.loop))
}

// What is coming out of the speakers now is what the clock played a moment ago.
function heard() {
  if (!player.playing) return player.offset
  const before = Math.max(player.offset, played() - (player.context.outputLatency || 0))
  return Math.min(player.buffer.duration, wrapped(before, player.loop))
}

// A short tick: 30 ms of a 1600 Hz tone that dies away at once.
function makeClickSound(context) {
  const length = Math.round(context.sampleRate * 0.03)
  const sound = context.createBuffer(1, length, context.sampleRate)
  const data = sound.getChannelData(0)
  for (let i = 0; i < length; i++) {
    const seconds = i / context.sampleRate
    data[i] = 0.7 * Math.sin(2 * Math.PI * 1600 * seconds) * Math.exp(-seconds / 0.005)
  }
  return sound
}

// The seconds the marked range covers, or null while it has only one end.
function markedLoop() {
  const { first, last } = player.range
  if (first === null || last === null) return null
  return loopOf(player.result.beats, first, last, player.buffer.duration)
}

function play() {
  if (!player.buffer || player.playing) return
  // The audio context is made at the first press: a browser gives no sound before one.
  if (!player.context) {
    player.context = new AudioContext()
    player.clickSound = makeClickSound(player.context)
    player.clickGain = player.context.createGain()
    player.clickGain.gain.value = $('click').checked ? 1 : 0
    player.clickGain.connect(player.context.destination)
  }
  const context = player.context
  context.resume()
  if (player.offset >= player.buffer.duration - 0.05) player.offset = 0

  const source = context.createBufferSource()
  source.buffer = player.buffer
  source.connect(context.destination)
  // The sound goes round the range by itself, on the audio clock, so a pass follows the
  // one before without a gap. Past the end of the range the song plays on to its end.
  const loop = player.looping ? markedLoop() : null
  player.loop = loop && player.offset < loop.end ? loop : null
  if (player.loop) Object.assign(source, { loop: true, loopStart: player.loop.start, loopEnd: player.loop.end })
  source.onended = () => {
    if (player.source !== source) return
    pause()
    player.offset = 0
    show()
  }
  // The song and its clicks are placed on the same clock, so they cannot drift apart.
  player.startedAt = context.currentTime + 0.1
  source.start(player.startedAt, player.offset)
  player.source = source
  player.playing = true
  player.nextClick = { beat: beatsUntil(player.result.beats, player.offset - 0.0005), pass: 0 }
  scheduleClicks()
  player.timer = setInterval(scheduleClicks, 50)
  $('play').textContent = 'Pause'
  showLoop()
  requestAnimationFrame(frame)
}

// Hands the clicks of the next moments to the audio clock, each at the time of its beat.
// It looks a second and a half ahead: a browser lets a page that is not in front run its
// timers only once a second, and the clicks must not stop there.
function scheduleClicks() {
  const placed = clicksUntil(player.result.beats, player.loop, player.nextClick, played() + 1.5)
  player.nextClick = placed.next
  for (const { at } of placed.clicks) {
    const click = player.context.createBufferSource()
    click.buffer = player.clickSound
    click.connect(player.clickGain)
    click.start(player.startedAt + at - player.offset)
    click.onended = () => player.clicks.splice(player.clicks.indexOf(click) >>> 0, 1)
    player.clicks.push(click)
  }
}

function pause() {
  if (!player.playing) return
  player.offset = position()
  player.playing = false
  player.loop = null
  clearInterval(player.timer)
  const source = player.source
  player.source = null
  source.stop()
  for (const click of player.clicks) click.stop()
  player.clicks = []
  $('play').textContent = 'Play'
  showLoop()
  show()
}

// Changes something about the playing, and goes on playing if the song was.
function replay(change) {
  const wasPlaying = player.playing
  pause()
  change()
  if (wasPlaying) play()
  showLoop()
  show()
}

function moveTo(seconds) {
  replay(() => {
    player.offset = Math.max(0, Math.min(player.buffer.duration, seconds))
  })
  follow()
}

// The beat the playing position is on, or the first one before the song has reached it.
const beatHere = () => Math.max(0, beatsUntil(player.result.beats, heard()) - 1)

// One beat on, or one beat back. Going back while the song plays, a beat that has only
// just started counts as reached: otherwise the position could never get past it.
function step(by) {
  const { beats } = player.result
  const now = heard()
  const on = beatsUntil(beats, now) - 1
  if (by > 0) return moveTo(on + 1 < beats.length ? beats[on + 1] : player.buffer.duration)
  if (on < 0) return moveTo(0)
  const justStarted = now - beats[on] < (player.playing ? 0.25 : 0.0005)
  moveTo(justStarted ? (on > 0 ? beats[on - 1] : 0) : beats[on])
}

// One ocho on, or one ocho back: to the first beat of the next ocho, or of this one. Going
// back from a first beat, or from one that has only just started, goes to the ocho before.
function stepOcho(by) {
  const { beats } = player.result
  const { ochos } = player
  const now = heard()
  const on = beatsUntil(beats, now) - 1
  const here = ochoOf(ochos, on)
  if (by > 0) return moveTo(here + 1 < ochos.length ? beats[ochos[here + 1].first] : player.buffer.duration)
  if (here < 0) return moveTo(0)
  const first = ochos[here].first
  const justStarted = on === first && now - beats[first] < (player.playing ? 0.25 : 0.0005)
  moveTo(justStarted ? (here > 0 ? beats[ochos[here - 1].first] : 0) : beats[first])
}

// ---- Count 1 by hand

let counting = 0 // how many times this browser has changed the beats set to count 1

// Counts the song again with the beats the user set to count 1, and draws it again.
function recount(ones) {
  const { beats, count } = player.result
  const counted = countsWith(beats, count, ones)
  Object.assign(player, { ones, count: counted.count, byHand: new Set(counted.byHand), ochos: ochosOf(counted.count) })
  layOut()
}

// The one control: the beat at the playing position is count 1 from now on. On a beat
// that was set this way, it takes that back.
$('one').addEventListener('click', async () => {
  const { id } = player
  const { beats } = player.result
  const here = beatHere()
  const set = !player.byHand.has(here)
  // A time the server keeps may have found this beat from a little way off.
  const times = set ? [beats[here]] : player.ones.filter((seconds) => nearestBeat(beats, seconds) === here)
  counting++
  recount(set ? [...player.ones, beats[here]] : player.ones.filter((seconds) => !times.includes(seconds)))
  $('one-note').textContent = ''
  let kept = true
  try {
    for (const at of times) {
      const answer = await fetch(`/api/songs/${id}/ones?${new URLSearchParams({ at })}`, { method: set ? 'PUT' : 'DELETE' })
      kept &&= answer.ok
    }
  } catch {
    kept = false
  }
  counting++
  if (!kept && player.id === id) $('one-note').textContent = 'The count was not kept.'
  await refresh()
})

// ---- The loop

function showLoop() {
  const { first, last } = player.range
  const beats = player.result?.beats
  const loop = beats ? markedLoop() : null
  $('loop').disabled = !loop
  $('loop').checked = Boolean(loop) && player.looping
  let text = 'Drag across beats'
  if (loop) text = `${clock(beats[first])} to ${clock(loop.end)}`
  else if (first !== null) text = `From ${clock(beats[first])}`
  else if (last !== null) text = `To ${clock(beats[last])}`
  $('loop-range').textContent = text
  $('player').dataset.state = player.playing ? (player.loop ? 'looping' : 'playing') : 'paused'
  for (const end of ['loop-start', 'loop-end']) $(end).disabled = !beats
}

// Marks a whole range and plays round it. A position outside it moves to its start.
function markRange(first, last) {
  replay(() => {
    player.range = { first, last }
    player.looping = true
    const loop = markedLoop()
    if (player.offset < loop.start || player.offset >= loop.end) player.offset = loop.start
  })
  follow()
}

// Sets one end of the range at the playing position. An other end that is now on the
// wrong side of it is dropped. The loop starts when the range has both ends.
function markEnd(end) {
  const here = beatHere()
  replay(() => {
    const range = { ...player.range, [end]: here }
    if (end === 'first' && range.last !== null && range.last < here) range.last = null
    if (end === 'last' && range.first !== null && range.first > here) range.first = null
    const wasWhole = markedLoop() !== null
    player.range = range
    if (markedLoop() === null) player.looping = false
    else if (!wasWhole) player.looping = true
  })
}

$('loop-start').addEventListener('click', () => markEnd('first'))
$('loop-end').addEventListener('click', () => markEnd('last'))

$('loop').addEventListener('change', () => {
  replay(() => {
    player.looping = $('loop').checked
    // Switched on after the range has been passed: the playing goes back into it.
    const loop = markedLoop()
    if (player.looping && player.offset >= loop.end) player.offset = loop.start
  })
  follow()
})

// ---- What is on screen while a song is open

let layout = null // where the rows of the song are, on the canvas as it is now
let hover = -1 // the beat under the pointer
let drag = null // a press on the song that has not been let go: { from, to }, beats
let mapFrom = null // what the song on screen was drawn from
let laidOut = 0 // how many times the song has been laid out
let litShown = -1 // the beat that is lit on it

// The canvas of the song is as tall as its rows, and the part of the page it is in scrolls.
function layOut() {
  if (!player.buffer) return
  layout = mapLayout($('song').clientWidth, player.ochos)
  $('map').style.height = `${layout.height}px`
  // Where the marks are and what they say, for whoever needs to find one without reading
  // the canvas: the middle of every mark, its count, the beats set by hand, and how many
  // ochos a row holds.
  const marks = player.count.map((count, beat) => [markOf(layout, beat).x, markOf(layout, beat).y])
  Object.assign($('map').dataset, {
    marks: JSON.stringify(marks),
    counts: player.count.join(' '),
    byHand: [...player.byHand].join(' '),
    perRow: layout.perRow,
  })
  laidOut++
  show()
}

function show() {
  if (!player.buffer || !layout) return
  const { beats } = player.result
  const now = heard()
  const lit = beatsUntil(beats, now) - 1

  const time = clock(now)
  if ($('position').textContent !== time) $('position').textContent = $('where').textContent = time
  const tempo = String(bpmAt(player.result, now) ?? '–')
  if ($('bpm').textContent !== tempo) $('bpm').textContent = tempo
  const count = String(player.count[lit] ?? '–')
  if ($('count').textContent !== count) $('count').textContent = count
  $('seek').value = now
  // The control says what a press would do to the beat the song is on.
  const one = player.byHand.has(Math.max(0, lit)) ? 'Not count 1' : 'Count 1 here'
  if ($('one').textContent !== one) $('one').textContent = one

  // The ocho that is sounding stands still, and its beats light one after the other.
  // Before the first beat it is the first ocho. Under the reduced-motion setting the lit
  // beat does not swell.
  const ocho = player.ochos[Math.max(0, ochoOf(player.ochos, lit))] ?? null
  const sounded = lit >= 0 ? now - beats[lit] : Infinity
  drawNow($('now'), {
    ocho,
    count: player.count,
    byHand: player.byHand,
    lit,
    pulse: reduced.matches || !player.playing ? 0 : Math.exp(-sounded / 0.07),
  })
  Object.assign($('now').dataset, { lit: lit < 0 ? '' : lit, ocho: ocho ? `${ocho.first} ${ocho.last}` : '' })

  // The song is drawn again only when something on it has changed.
  const marked = drag ? { first: Math.min(drag.from, drag.to), last: Math.max(drag.from, drag.to) } : player.range
  const range = marked.first !== null && marked.last !== null ? { ...marked, on: !drag && player.looping } : null
  const from = JSON.stringify([lit, hover, range, laidOut])
  if (from !== mapFrom) {
    mapFrom = from
    drawMap($('map'), layout, { beats, count: player.count, byHand: player.byHand, lit, hover, range })
    if (lit !== litShown && player.playing) follow()
    litShown = lit
  }
}

// Scrolls the song so that the row of the playing position is on screen.
function follow() {
  if (!player.buffer || !layout?.count) return
  const song = $('song')
  const row = rowOf(layout, beatHere())
  if (row.top >= song.scrollTop && row.bottom <= song.scrollTop + song.clientHeight) return
  song.scrollTop = Math.max(0, row.top - Math.max(layout.top, song.clientHeight / 3))
}

function frame() {
  show()
  if (player.playing) requestAnimationFrame(frame)
}

// Light or dark changed, or the typeface arrived: everything is drawn again.
function redraw() {
  forgetTokens()
  layOut()
}

$('play').addEventListener('click', () => (player.playing ? pause() : play()))

$('click').addEventListener('change', () => {
  if (player.clickGain) player.clickGain.gain.value = $('click').checked ? 1 : 0
})

// The position control. While it is dragged the song is silent and the page follows the
// drag; the song goes on from where the control is let go.
let dragged = null // a drag of the position control: { playing }, whether the song was playing when it began

$('seek').addEventListener('pointerdown', () => {
  dragged = { playing: player.playing }
  pause()
})

$('seek').addEventListener('input', () => moveTo(Number($('seek').value)))

for (const end of ['pointerup', 'pointercancel']) {
  window.addEventListener(end, () => {
    if (!dragged) return
    const { playing } = dragged
    dragged = null
    if (playing) play()
  })
}

// A press on a beat of the song moves the playing position there. A press that is
// dragged across several beats marks them as a loop.
const beatUnder = (event, nearest) => {
  const box = $('map').getBoundingClientRect()
  return beatAt(layout, event.clientX - box.left, event.clientY - box.top, nearest)
}

$('map').addEventListener('pointerdown', (event) => {
  if (!player.buffer || event.button !== 0) return
  const beat = beatUnder(event, false)
  if (beat < 0) return
  drag = { from: beat, to: beat }
  $('map').setPointerCapture(event.pointerId)
  show()
})

$('map').addEventListener('pointermove', (event) => {
  if (!player.buffer) return
  if (drag) drag.to = beatUnder(event, true)
  else hover = beatUnder(event, false)
  show()
})

$('map').addEventListener('pointerup', () => {
  if (!drag) return
  const { from, to } = drag
  drag = null
  if (from === to) moveTo(player.result.beats[from])
  else markRange(Math.min(from, to), Math.max(from, to))
})

$('map').addEventListener('pointercancel', () => {
  drag = null
  show()
})

$('map').addEventListener('pointerleave', () => {
  hover = -1
  show()
})

// A press on one of the large beats moves the playing position to it as well. Each
// stands at the place of its count.
$('now').addEventListener('click', (event) => {
  if (!player.buffer) return
  const ocho = player.ochos[Math.max(0, ochoOf(player.ochos, beatsUntil(player.result.beats, heard()) - 1))]
  if (!ocho) return
  const box = $('now').getBoundingClientRect()
  const place = Math.floor((event.clientX - box.left) / nowLayout(box.width).step) + 1
  const beat = ocho.first + place - player.count[ocho.first]
  if (beat >= ocho.first && beat <= ocho.last) moveTo(player.result.beats[beat])
})

// The keyboard: Space plays and pauses, the arrows move the position by a beat, and with
// Shift by an ocho. A key that already means something where the keyboard is keeps that
// meaning.
document.addEventListener('keydown', (event) => {
  if (!player.buffer || event.altKey || event.ctrlKey || event.metaKey) return
  const on = event.target
  if (on.matches('input[type="text"]')) return
  if (event.key === ' ' && !on.matches('button, input[type="checkbox"], input[type="file"]')) {
    event.preventDefault()
    if (player.playing) pause()
    else play()
  } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault()
    const by = event.key === 'ArrowRight' ? 1 : -1
    if (event.shiftKey) stepOcho(by)
    else step(by)
  }
})

new ResizeObserver(layOut).observe($('song'))
new ResizeObserver(show).observe($('now'))
document.fonts.addEventListener('loadingdone', redraw)
reduced.addEventListener('change', show)
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw)

// The list is the same in every browser, so it is asked for again every two seconds.
setInterval(() => document.hidden || refresh(), 2000)
showNothing()
refresh()
