// The page: adding a song, the list of remembered songs, and playing one with its beats,
// their count and its bars.

import {
  MAX_NAME,
  MAX_SECONDS,
  MIN_SECONDS,
  RATE,
  addressOf,
  atIn,
  barOf,
  barsOf,
  beatAt,
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
  missing,
  nameFor,
  nearestBeat,
  ochoOf,
  ochosOf,
  placeOf,
  placeText,
  songIn,
  tagsOf,
  wrapped,
} from './song.js'
import { barAt, drawMap, drawNow, forgetTokens, mapLayout, nowLayout, rowOf } from './draw.js'

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
  if (!kindOf(bytes)) return say('This is not an mp3, m4a or opus file.', true)

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
  let answer
  try {
    answer = await send(`/api/songs/${id}?${query}`, samples, (part) => say(`Sending ${name}…`, false, part))
  } catch {
    return say('The song did not reach the server. It was not added.', true)
  }
  // 409: another browser sent the same song in the meantime.
  if (!answer.ok && answer.status !== 409) return say(`The server refused the song. ${answer.text.trim()}`, true)
  // A song that is sounding is left to sound: see `refresh`.
  say(`${name} is in the library. ${player.playing ? 'It is ready' : 'It opens'} when it has been analysed.`)
  return openWhenReady(id)
}

// ---- The list

const STATES = { waiting: 'waiting', analysing: 'being analysed', ready: 'ready', failed: 'failed' }
const FAILED = 'The analysis failed. To try again, delete the song and add the file again.'

let songs = []
const rows = new Map() // the rows on screen, by song: { row, from }, where `from` is what the row was built from
let confirming = null // the song whose deletion waits for its confirmation
let renaming = null // the name that is being typed: { id, where, draft }, where is 'row' or 'title'
let opening = null // the song that is being fetched: { id, part }
let wanted = null // the song to open as soon as it is ready
let linked = null // the song the address named when the page was loaded, until it is settled
let linkedAt = null // the place the address named in that song: { id, text, place }, and `used` once the song has opened there
let focusNext = null // where the keyboard goes once the list is on screen again: { id, where, key }
const notes = new Map() // what went wrong with a song, shown in its row: id, or 'title', to { text, refused }
const analysedSince = new Map() // when this page saw the analysis of a song start, by song
let listed = false // whether the list has been on screen before

// What the row of a song says of its state. An analysis this page saw start says for how
// long it has run: one that was already running when the page was loaded cannot.
function stateOf(song) {
  const since = analysedSince.get(song.id)
  if (since === undefined) return STATES[song.state]
  return `${STATES[song.state]} for ${clock((performance.now() - since) / 1000)}`
}

async function refresh() {
  let response
  const asked = counting
  try {
    response = await read('/api/songs')
  } catch {
    return
  }
  if (!response.ok) return
  const before = new Map(songs.map((song) => [song.id, song.state]))
  songs = await response.json()
  for (const id of analysedSince.keys()) if (!songs.some((song) => song.id === id && song.state === 'analysing')) analysedSince.delete(id)
  for (const song of songs) {
    if (listed && song.state === 'analysing' && before.get(song.id) !== 'analysing') analysedSince.set(song.id, performance.now())
  }
  listed = true
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
    wanted = linked = null
    // A song that is sounding is not cut off by one that has just been analysed.
    if (player.playing) say(`${song.name} is ready. Open it from the list.`)
    else await open(song)
  } else if (wanted && (!song || song.state === 'failed')) {
    // A song the address named and the library does not have is said in the middle of
    // the page: no control of the page asked for it.
    const named = wanted === linked
    wanted = linked = null
    if (named) showAddress(null)
    if (named && !song) showNothing(NOT_THERE)
    else say(song ? `The analysis of ${song.name} failed.` : 'The song was deleted.', true)
  }
}

const NOT_THERE = 'This song is not in the library.'

// Every song has an address of its own. The address bar shows the one of the open song,
// and the plain address of the page when none is open. Nothing is added to the history:
// Back leaves the page as it always did. A place the address was loaded with stays in it
// while its song is the open one: the address does not follow the playing position.
function showAddress(id) {
  if (linkedAt?.id !== id) linkedAt = null
  history.replaceState(null, '', id ? addressOf(id, linkedAt?.text) : location.pathname)
}

// Moves the playing position to the place the address named, once, when its song has
// opened. A place the song does not have is said beside its name.
function goToLinked() {
  if (!linkedAt || linkedAt.used) return
  linkedAt.used = true
  const { beats } = player.result
  const beat = beatAt(player.bars, beats, linkedAt.place, player.buffer.duration)
  if (beat >= 0) player.offset = beats[beat]
  else notes.set('title', { text: missing(player.bars, linkedAt.place), refused: true })
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
  row.append(element('span', 'state', `${clock(song.seconds)}, ${stateOf(song)}`))

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
  const note = noteOf(song.id) ?? (song.state === 'failed' ? element('p', 'note refused', FAILED) : null)
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
      stateOf(song),
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
  bars: [], // the bars that count makes, each { first, last }
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
  // The address may name a place in this song. Asked for any other way, the song opens at its start.
  if (linkedAt && (linkedAt.used || linkedAt.id !== song.id)) linkedAt = null
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
  notes.delete('title')
  showAddress(song.id)
  showPlayer()
  // The list may have moved on while the song was fetched.
  const { ones } = songs.find((candidate) => candidate.id === song.id) ?? song
  // The place is found in the bars the count makes, before anything is drawn.
  const counted = countsWith(result.beats, result.count, ones)
  player.bars = barsOf(counted.count)
  goToLinked()
  showSongs()
  showLoop()
  recount(ones)
  $('song').scrollTop = 0
  follow()
  // The button that opened the song is gone from its row: the keyboard goes to Play.
  if (document.activeElement === document.body) $('play').focus()
}

function closePlayer(text) {
  pause()
  Object.assign(player, { id: null, buffer: null, result: null, offset: 0, range: { first: null, last: null }, looping: false })
  Object.assign(player, { ones: [], count: [], byHand: new Set(), ochos: [], bars: [] })
  for (const control of ['play', 'seek', 'loop', 'loop-start', 'loop-end', 'one']) $(control).disabled = true
  $('position').textContent = $('duration').textContent = clock(0)
  $('place').textContent = ''
  $('seek').value = 0
  $('seek').style.setProperty('--at', 0)
  showAddress(null)
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

// Counts the song again with the beats the user set to count 1, makes its ochos and its
// bars again, and draws it again. The bars may be other ones now: what the pointer was
// on, or was dragging across, is forgotten.
function recount(ones) {
  const { beats, count } = player.result
  const counted = countsWith(beats, count, ones)
  Object.assign(player, { ones, count: counted.count, byHand: new Set(counted.byHand) })
  Object.assign(player, { ochos: ochosOf(counted.count), bars: barsOf(counted.count) })
  hover = -1
  drag = null
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
  let text = 'Drag across bars'
  if (loop) text = `${clock(beats[first])} to ${clock(loop.end)}`
  else if (first !== null) text = `From ${clock(beats[first])}`
  else if (last !== null) text = `To ${clock(beats[last])}`
  $('loop-range').textContent = text
  // The range on the position control: two ends, and filled while the playing goes round it.
  const onSeek = $('seek-loop')
  onSeek.hidden = !loop
  if (loop) {
    onSeek.style.setProperty('--from', loop.start / player.buffer.duration)
    onSeek.style.setProperty('--to', loop.end / player.buffer.duration)
    onSeek.toggleAttribute('data-on', player.looping)
  }
  $('player').dataset.state = player.playing ? (player.loop ? 'looping' : 'playing') : 'paused'
  for (const end of ['loop-start', 'loop-end']) $(end).disabled = !beats
  // The keyboard does not stay on a control that can no longer be pressed.
  const nothingMarked = first === null && last === null
  if (nothingMarked && document.activeElement === $('loop-clear')) $('loop-start').focus()
  $('loop-clear').disabled = nothingMarked
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

// Takes the marked range away, whole or with one end. A song that was going round it
// plays on from where it is.
$('loop-clear').addEventListener('click', () => {
  replay(() => {
    player.range = { first: null, last: null }
    player.looping = false
  })
})

$('loop').addEventListener('change', () => {
  // Read before the song is stopped: stopping it shows the switch as it was.
  const on = $('loop').checked
  replay(() => {
    player.looping = on
    // Switched on after the range has been passed: the playing goes back into it.
    const loop = markedLoop()
    if (player.looping && player.offset >= loop.end) player.offset = loop.start
  })
  follow()
})

// ---- What is on screen while a song is open

let layout = null // where the plates of the song are, on the canvas as it is now
let hover = -1 // the bar under the pointer, as its place in the bars
let drag = null // a press on the song that has not been let go: { from, to }, bars
let mapFrom = null // what the song on screen was drawn from
let laidOut = 0 // how many times the song has been laid out
let litShown = -1 // the bar that is lit on it

// The canvas of the song is as tall as its rows, and the part of the page it is in scrolls.
function layOut() {
  if (!player.buffer) return
  layout = mapLayout($('song').clientWidth, player.ochos, player.bars)
  $('map').style.height = `${layout.height}px`
  // Where the plates are and what they stand for, for whoever needs to find one without
  // reading the canvas: the count of every beat, the beats set by hand, how many ochos a
  // row holds, the first beat of every bar, and the box of its plate.
  Object.assign($('map').dataset, {
    counts: player.count.join(' '),
    byHand: [...player.byHand].join(' '),
    perRow: layout.perRow,
    bars: player.bars.map((bar) => bar.first).join(' '),
    rows: layout.rows.map((row) => row.first).join(' '),
    plates: JSON.stringify(layout.plates.map(({ x, y, wide, high }) => [x, y, wide, high])),
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
  if ($('position').textContent !== time) $('position').textContent = time
  const tempo = String(bpmAt(player.result, now) ?? '–')
  if ($('bpm').textContent !== tempo) $('bpm').textContent = tempo
  const count = String(player.count[lit] ?? '–')
  if ($('count').textContent !== count) $('count').textContent = count
  // The bar and the beat the song is on, and before its first beat those of that beat.
  const here = placeOf(player.bars, Math.max(0, lit))
  const place = here ? `Bar ${placeText(here)}` : ''
  if ($('place').textContent !== place) $('place').textContent = place
  $('seek').value = now
  // How far along the song is, from 0 to 1: the line of the position control is drawn to there.
  $('seek').style.setProperty('--at', now / player.buffer.duration)
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

  // On the song the bar that holds that beat is lit, whole. The song is drawn again only
  // when something on it has changed: when another bar is lit, not at every beat. While
  // a press is held, the bars it has crossed show as a range, and no bar has a halo.
  const { bars } = player
  const litBar = barOf(bars, lit)
  const marked = drag ? { first: bars[Math.min(drag.from, drag.to)].first, last: bars[Math.max(drag.from, drag.to)].last } : player.range
  const range = marked.first !== null && marked.last !== null ? { ...marked, on: !drag && player.looping } : null
  const under = drag ? -1 : hover
  const from = JSON.stringify([litBar, under, range, laidOut])
  if (from !== mapFrom) {
    mapFrom = from
    drawMap($('map'), layout, { beats, bars, count: player.count, byHand: player.byHand, lit: litBar, hover: under, range })
    Object.assign($('map').dataset, { lit: litBar < 0 ? '' : litBar, range: range ? `${range.first} ${range.last}` : '' })
    if (litBar !== litShown && player.playing) follow()
    litShown = litBar
  }
}

// Scrolls the song so that the row of the playing position is on screen.
function follow() {
  if (!player.buffer || !layout?.plates.length) return
  const song = $('song')
  const row = rowOf(layout, barOf(player.bars, beatHere()))
  if (row.top >= song.scrollTop && row.bottom <= song.scrollTop + song.clientHeight) return
  song.scrollTop = Math.max(0, row.top - Math.max(rowOf(layout, 0).top, song.clientHeight / 3))
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

// A press on a bar of the song moves the playing position to its first beat. A press
// that is dragged from one bar to another marks whole bars as a loop, from the first beat
// of the earlier one to the last beat of the later, whichever way the drag went.
const barUnder = (event, nearest) => {
  const box = $('map').getBoundingClientRect()
  return barAt(layout, event.clientX - box.left, event.clientY - box.top, nearest)
}

$('map').addEventListener('pointerdown', (event) => {
  if (!player.buffer || event.button !== 0) return
  const bar = barUnder(event, false)
  if (bar < 0) return
  drag = { from: bar, to: bar }
  $('map').setPointerCapture(event.pointerId)
  show()
})

$('map').addEventListener('pointermove', (event) => {
  if (!player.buffer) return
  hover = barUnder(event, false)
  // A drag may leave the rows: it takes the nearest row, and in it the nearest bar.
  if (drag) drag.to = barUnder(event, true)
  show()
})

$('map').addEventListener('pointerup', () => {
  if (!drag) return
  const { from, to } = drag
  const { bars } = player
  drag = null
  if (from === to) moveTo(player.result.beats[bars[from].first])
  else markRange(bars[Math.min(from, to)].first, bars[Math.max(from, to)].last)
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

// A press with the pointer does not leave the keyboard on the control it pressed. Space
// would press that control again, and take back a count 1 or move an end of the loop,
// when it was meant to play. A control the keyboard itself went to keeps it.
let pointed = false // whether the last thing pressed was the pointer, not a key
document.addEventListener('pointerdown', () => (pointed = true), true)
document.addEventListener('keydown', () => (pointed = false), true)
document.querySelector('.transport').addEventListener('click', (event) => {
  const on = document.activeElement
  if (pointed && event.currentTarget.contains(on) && on.matches('button, input[type="checkbox"]')) on.blur()
})

new ResizeObserver(layOut).observe($('song'))
new ResizeObserver(show).observe($('now'))
document.fonts.addEventListener('loadingdone', redraw)
reduced.addEventListener('change', show)
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw)

// The list is the same in every browser, so it is asked for again every two seconds.
setInterval(() => document.hidden || refresh(), 2000)

// The address may name a song: it opens as soon as the list has it ready.
linked = wanted = songIn(location.search)
if (linked && atIn(location.search)) linkedAt = { id: linked, text: new URLSearchParams(location.search).get('at'), place: atIn(location.search) }
if (!linked && new URLSearchParams(location.search).has('song')) {
  showAddress(null)
  showNothing(NOT_THERE)
} else {
  showNothing()
}
refresh()
