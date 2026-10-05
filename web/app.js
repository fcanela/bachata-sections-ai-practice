// The page: adding a song, the list of remembered songs, and playing one with its beats.

import { MAX_SECONDS, MIN_SECONDS, RATE, beatsUntil, bpmAt, channelsFrom16, clock, idOf, interleaved16, kindOf, nameFor, tagsOf } from './song.js'

const $ = (id) => document.getElementById(id)

function say(text, refused = false) {
  $('message').textContent = text
  $('message').classList.toggle('refused', refused)
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
  say(`Sending ${name}…`)
  const query = new URLSearchParams({ name, rate: RATE, frames: sound.length })
  const response = await fetch(`/api/songs/${id}?${query}`, { method: 'PUT', body: samples })
  // 409: another browser sent the same song in the meantime.
  if (!response.ok && response.status !== 409) return say(`The server refused the song. ${await response.text()}`, true)
  say(`${name} is in the library. It opens when it has been analysed.`)
  return openWhenReady(id)
}

// ---- The list

const STATES = { waiting: 'waiting', analysing: 'being analysed', ready: 'ready', failed: 'failed' }

let songs = []
let shown = null // what the list on screen was built from
let confirming = null // the song whose deletion waits for its confirmation
let wanted = null // the song to open as soon as it is ready

async function refresh() {
  let response
  try {
    response = await read('/api/songs')
  } catch {
    return
  }
  if (!response.ok) return
  songs = await response.json()
  showList()

  if (player.id && !songs.some((song) => song.id === player.id)) closePlayer()
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

function button(text, action) {
  const element = document.createElement('button')
  element.type = 'button'
  element.textContent = text
  element.addEventListener('click', action)
  return element
}

function showList() {
  const state = JSON.stringify([songs, confirming])
  if (state === shown) return
  shown = state
  $('empty').hidden = songs.length > 0
  $('songs').replaceChildren(
    ...songs.map((song) => {
      const row = document.createElement('li')
      row.dataset.id = song.id
      row.dataset.state = song.state
      // A name is text someone typed or tagged: it is only ever put on screen as text.
      const name = document.createElement('span')
      name.className = 'name'
      name.textContent = song.name
      const state = document.createElement('span')
      state.className = 'state'
      state.textContent = `${clock(song.seconds)}, ${STATES[song.state]}`
      row.append(name, state)
      if (song.state === 'ready') row.append(button('Open', () => open(song)))
      if (confirming === song.id) {
        const question = document.createElement('span')
        question.textContent = 'Delete this song?'
        row.append(question, button('Yes, delete', () => remove(song)), button('Keep', () => askToDelete(null)))
      } else {
        row.append(button('Delete', () => askToDelete(song.id)))
      }
      return row
    }),
  )
}

// One confirmation: the row asks, and only then is the song deleted.
function askToDelete(id) {
  confirming = id
  showList()
}

async function remove(song) {
  confirming = null
  const response = await fetch(`/api/songs/${song.id}`, { method: 'DELETE' })
  if (!response.ok && response.status !== 404) say(`${song.name} could not be deleted.`, true)
  await refresh()
}

// ---- Playing a song

// The sound that plays is always the one the server stored, never the file that was
// picked: the beats were found on the stored samples, so the click lines up with them.
const player = {
  id: null,
  buffer: null, // the stored sound
  result: null, // { beats, bpm }
  context: null,
  source: null, // the sound that is playing
  playing: false,
  offset: 0, // where in the song the playing started, or stopped, in seconds
  startedAt: 0, // the time of the audio clock at which the playing started
  clickSound: null,
  clickGain: null,
  clicks: [], // the clicks handed to the audio clock that may not have sounded yet
  nextClick: 0, // the first beat that has no click scheduled
  timer: null,
}

async function open(song) {
  pause()
  say(`Opening ${song.name}…`)
  let result, buffer
  try {
    const [resultAnswer, soundAnswer] = await Promise.all([read(`/api/songs/${song.id}/result`), read(`/api/songs/${song.id}/sound`)])
    if (!resultAnswer.ok || !soundAnswer.ok) throw new Error('not there')
    result = await resultAnswer.json()
    buffer = soundFrom(await soundAnswer.arrayBuffer())
  } catch {
    return say(`${song.name} could not be opened.`, true)
  }
  pause()
  Object.assign(player, { id: song.id, buffer, result, offset: 0 })
  $('song-name').textContent = song.name
  $('duration').textContent = clock(buffer.duration)
  $('strip').dataset.beats = result.beats.length
  $('player').hidden = false
  say('')
  draw()
}

function closePlayer() {
  pause()
  Object.assign(player, { id: null, buffer: null, result: null, offset: 0 })
  $('player').hidden = true
}

// Where the playing is in the song, in seconds, by the audio clock.
function position() {
  if (!player.playing) return player.offset
  return Math.min(player.buffer.duration, player.offset + Math.max(0, player.context.currentTime - player.startedAt))
}

// What is coming out of the speakers now is what the clock played a moment ago.
function heard() {
  if (!player.playing) return player.offset
  return Math.max(player.offset, position() - (player.context.outputLatency || 0))
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
  source.onended = () => {
    if (player.source !== source) return
    pause()
    player.offset = 0
    draw()
  }
  // The song and its clicks are placed on the same clock, so they cannot drift apart.
  player.startedAt = context.currentTime + 0.1
  source.start(player.startedAt, player.offset)
  player.source = source
  player.playing = true
  player.nextClick = beatsUntil(player.result.beats, player.offset - 0.0005)
  scheduleClicks()
  player.timer = setInterval(scheduleClicks, 50)
  $('play').textContent = 'Pause'
  requestAnimationFrame(frame)
}

// Hands the clicks of the next moments to the audio clock, each at the time of its beat.
// It looks a second and a half ahead: a browser lets a page that is not in front run its
// timers only once a second, and the clicks must not stop there.
function scheduleClicks() {
  const { context, result } = player
  const until = position() + 1.5
  while (player.nextClick < result.beats.length && result.beats[player.nextClick] < until) {
    const click = context.createBufferSource()
    click.buffer = player.clickSound
    click.connect(player.clickGain)
    click.start(player.startedAt + result.beats[player.nextClick] - player.offset)
    click.onended = () => player.clicks.splice(player.clicks.indexOf(click) >>> 0, 1)
    player.clicks.push(click)
    player.nextClick++
  }
}

function pause() {
  if (!player.playing) return
  player.offset = position()
  player.playing = false
  clearInterval(player.timer)
  const source = player.source
  player.source = null
  source.stop()
  for (const click of player.clicks) click.stop()
  player.clicks = []
  $('play').textContent = 'Play'
  draw()
}

function draw() {
  if (!player.buffer) return
  const canvas = $('strip')
  const scale = window.devicePixelRatio || 1
  const width = Math.round(canvas.clientWidth * scale)
  const height = Math.round(canvas.clientHeight * scale)
  if (canvas.width !== width || canvas.height !== height) Object.assign(canvas, { width, height })
  const colours = getComputedStyle(document.documentElement)
  const pen = canvas.getContext('2d')
  const now = heard()
  const x = (seconds) => Math.round((seconds / player.buffer.duration) * (width - 1)) + 0.5

  pen.clearRect(0, 0, width, height)
  // One tick for every beat.
  pen.strokeStyle = colours.getPropertyValue('--tick').trim()
  pen.lineWidth = 1
  pen.beginPath()
  for (const beat of player.result.beats) {
    pen.moveTo(x(beat), height * 0.3)
    pen.lineTo(x(beat), height * 0.7)
  }
  pen.stroke()
  // The marker, at the playing position.
  pen.strokeStyle = colours.getPropertyValue('--accent').trim()
  pen.lineWidth = 2 * scale
  pen.beginPath()
  pen.moveTo(x(now), 0)
  pen.lineTo(x(now), height)
  pen.stroke()

  $('position').textContent = clock(now)
  $('bpm').textContent = bpmAt(player.result, now) ?? '–'
}

function frame() {
  draw()
  if (player.playing) requestAnimationFrame(frame)
}

$('play').addEventListener('click', () => (player.playing ? pause() : play()))

$('click').addEventListener('change', () => {
  if (player.clickGain) player.clickGain.gain.value = $('click').checked ? 1 : 0
})

// A press on the strip moves the playing position there.
$('strip').addEventListener('click', (event) => {
  if (!player.buffer) return
  const box = $('strip').getBoundingClientRect()
  const wasPlaying = player.playing
  pause()
  player.offset = Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)) * player.buffer.duration
  if (wasPlaying) play()
  draw()
})

window.addEventListener('resize', draw)

// The list is the same in every browser, so it is asked for again every two seconds.
setInterval(() => document.hidden || refresh(), 2000)
refresh()
