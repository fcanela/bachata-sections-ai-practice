// What the page works out about a song without the screen or the sound card:
// the type of a file, its id, its name from its tags, the samples to send, what to
// show at a playing position, the count with what the user set, where a loop and its
// clicks fall, and the address of a song. song.test.js checks it.

// What the page decodes to and sends. The server checks the same numbers again.
export const RATE = 44100
export const MIN_SECONDS = 20
export const MAX_SECONDS = 15 * 60
export const MAX_NAME = 200

const ascii = (bytes, at, length) => String.fromCharCode(...bytes.subarray(at, at + length))
const number = (bytes, at, length) => bytes.subarray(at, at + length).reduce((sum, byte) => sum * 256 + byte, 0)
// The sizes in an ID3 tag keep the top bit of every byte clear.
const synchsafe = (bytes, at) => bytes.subarray(at, at + 4).reduce((sum, byte) => sum * 128 + (byte & 0x7f), 0)

// Where the content of the first page of an Ogg file starts: after 27 bytes of header
// and one byte for each of its segments.
const oggStart = (bytes) => 27 + bytes[26]

// 'mp3', 'm4a' or 'opus', from the first bytes of the file and not from its name. null
// for anything else.
export function kindOf(bytes) {
  if (bytes.length < 12) return null
  if (ascii(bytes, 4, 4) === 'ftyp') return 'm4a'
  // Opus comes wrapped in Ogg, and its first page says "OpusHead". Other sound in the
  // same wrapping, Vorbis for one, is not taken.
  if (ascii(bytes, 0, 4) === 'OggS') return bytes.length > 27 && ascii(bytes, oggStart(bytes), 8) === 'OpusHead' ? 'opus' : null
  if (ascii(bytes, 0, 3) === 'ID3') return 'mp3'
  // An mp3 without a tag starts with a frame: eleven set bits, then a layer that is not 0.
  if (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0 && (bytes[1] & 0x06) !== 0) return 'mp3'
  return null
}

// The id of a song: the first 32 hex characters of the SHA-256 of the file.
export function idOf(sha256) {
  return [...new Uint8Array(sha256)].map((byte) => byte.toString(16).padStart(2, '0')).join('').slice(0, 32)
}

// The title and the artist a file carries, each undefined when it has none.
export function tagsOf(bytes) {
  try {
    if (kindOf(bytes) === 'm4a') return m4aTags(bytes)
    if (kindOf(bytes) === 'opus') return opusTags(bytes)
    if (ascii(bytes, 0, 3) === 'ID3') return id3Tags(bytes)
    // The old tag at the end of an mp3: "TAG", then 30 bytes of title and 30 of artist.
    const old = bytes.subarray(bytes.length - 128)
    if (old.length === 128 && ascii(old, 0, 3) === 'TAG') {
      const text = (at) => new TextDecoder('windows-1252').decode(old.subarray(at, at + 30)).split('\0')[0]
      return { title: text(3), artist: text(33) }
    }
  } catch {
    // A tag that cannot be read is no tag: the name then comes from the file name.
  }
  return {}
}

// ID3v2, the tag at the start of an mp3. Versions 2.2, 2.3 and 2.4.
function id3Tags(bytes) {
  const version = bytes[3]
  const flags = bytes[5]
  const end = Math.min(10 + synchsafe(bytes, 6), bytes.length)
  // A tag whose bytes were rewritten to hide false frame starts is rare, and not read here.
  if (version < 2 || version > 4 || flags & 0x80) return {}
  let at = 10
  if (version > 2 && flags & 0x40) at += version === 4 ? synchsafe(bytes, at) : 4 + number(bytes, at, 4)

  const names = version === 2 ? { TT2: 'title', TP1: 'artist' } : { TIT2: 'title', TPE1: 'artist' }
  const header = version === 2 ? 6 : 10
  const tags = {}
  while (at + header <= end && bytes[at] !== 0) {
    const id = ascii(bytes, at, version === 2 ? 3 : 4)
    const size = version === 2 ? number(bytes, at + 3, 3) : version === 4 ? synchsafe(bytes, at + 4) : number(bytes, at + 4, 4)
    at += header
    if (size < 1 || at + size > end) break
    if (names[id]) tags[names[id]] = id3Text(bytes.subarray(at, at + size))
    at += size
  }
  return tags
}

// The text of an ID3 frame: one byte that says how it is written, then the text.
function id3Text(frame) {
  const encodings = ['windows-1252', 'utf-16le', 'utf-16be', 'utf-8']
  let encoding = encodings[frame[0]]
  if (!encoding) return undefined
  let body = frame.subarray(1)
  if (frame[0] === 1) {
    if (body[0] === 0xfe && body[1] === 0xff) encoding = 'utf-16be'
    if ((body[0] === 0xfe && body[1] === 0xff) || (body[0] === 0xff && body[1] === 0xfe)) body = body.subarray(2)
  }
  // The text ends at the first NUL. Version 2.4 puts more values after it.
  return new TextDecoder(encoding).decode(body).split('\0')[0]
}

// The boxes inside a part of an m4a file: four bytes of size, four of type, then the content.
function* boxes(bytes, start, end) {
  let at = start
  while (at + 8 <= end) {
    let size = number(bytes, at, 4)
    let content = at + 8
    if (size === 1) {
      size = number(bytes, at + 8, 8)
      content = at + 16
    } else if (size === 0) {
      size = end - at
    }
    if (size < content - at || at + size > end) return
    yield { type: ascii(bytes, at + 4, 4), start: content, end: at + size }
    at += size
  }
}

// The iTunes tags of an m4a: moov > udta > meta > ilst, then one box per tag.
function m4aTags(bytes) {
  let inside = { start: 0, end: bytes.length }
  for (const type of ['moov', 'udta', 'meta', 'ilst']) {
    inside = [...boxes(bytes, inside.start, inside.end)].find((box) => box.type === type)
    if (!inside) return {}
    // meta has four bytes of version before its boxes, unless it comes from QuickTime.
    if (type === 'meta' && ascii(bytes, inside.start + 4, 4) !== 'hdlr') inside.start += 4
  }
  const names = { '©nam': 'title', '©ART': 'artist' }
  const tags = {}
  for (const tag of boxes(bytes, inside.start, inside.end)) {
    const data = [...boxes(bytes, tag.start, tag.end)].find((box) => box.type === 'data')
    // The content of data: a type, where 1 is UTF-8 text, four more bytes, then the value.
    if (names[tag.type] && data && number(bytes, data.start, 4) === 1) {
      tags[names[tag.type]] = new TextDecoder('utf-8').decode(bytes.subarray(data.start + 8, data.end))
    }
  }
  return tags
}

// The second packet of an Ogg file, put together from the segments it was cut into. A
// page has 27 bytes of header, the lengths of its segments, then the segments. A packet
// ends with a segment shorter than 255 bytes, and may run over many pages.
function secondOggPacket(bytes) {
  const parts = []
  let packet = 0
  for (let at = 0; at + 27 <= bytes.length && ascii(bytes, at, 4) === 'OggS'; ) {
    const lengths = bytes.subarray(at + 27, at + 27 + bytes[at + 26])
    at += 27 + lengths.length
    for (const length of lengths) {
      if (packet === 1) parts.push(bytes.subarray(at, at + length))
      at += length
      if (length < 255 && ++packet > 1) {
        const whole = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0))
        parts.reduce((to, part) => (whole.set(part, to), to + part.length), 0)
        return whole
      }
    }
  }
  return new Uint8Array(0)
}

// The tags of an opus file: its second packet, "OpusTags", then the name of the program
// that wrote it, then texts of the form NAME=value, each with its length before it. The
// names may be in capitals or in small letters. A cover picture is one of those texts.
function opusTags(bytes) {
  const packet = secondOggPacket(bytes)
  if (ascii(packet, 0, 8) !== 'OpusTags') return {}
  const length = (at) => (at + 4 <= packet.length ? new DataView(packet.buffer).getUint32(at, true) : Infinity)
  let at = 12 + length(8)
  const count = length(at)
  at += 4
  const names = { TITLE: 'title', ARTIST: 'artist' }
  const tags = {}
  for (let n = 0; n < count && at + 4 + length(at) <= packet.length; n++) {
    const text = packet.subarray(at + 4, at + 4 + length(at))
    at += 4 + text.length
    const equals = text.indexOf(0x3d)
    const name = equals > 0 && equals <= 6 ? names[ascii(text, 0, equals).toUpperCase()] : undefined
    // Of several titles or artists the first is taken.
    if (name && !(name in tags)) tags[name] = new TextDecoder('utf-8').decode(text.subarray(equals + 1))
  }
  return tags
}

// A name as the server takes it: one line, no longer than 200 characters. Empty when
// nothing is left of it.
export function cleanName(text) {
  const name = (text ?? '').replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim()
  // Cut by characters, as the server counts them, and not in the middle of one.
  return [...name].slice(0, MAX_NAME).join('').trim()
}

// The name of a song: artist and title when the file has both, the title alone, or the
// file name without its extension. Never empty, and never longer than the server takes.
export function nameFor(tags, fileName) {
  const title = cleanName(tags.title)
  const artist = cleanName(tags.artist)
  return cleanName(title && artist ? `${artist} - ${title}` : title) || cleanName(fileName.replace(/\.[^.]*$/, '')) || 'Unnamed song'
}

// The samples to send: 16 bits, left and right in turn.
export function interleaved16(left, right) {
  const samples = new Int16Array(left.length * 2)
  const to16 = (value) => Math.max(-32768, Math.min(32767, Math.round(value * 32768)))
  for (let i = 0; i < left.length; i++) {
    samples[2 * i] = to16(left[i])
    samples[2 * i + 1] = to16(right[i])
  }
  return samples
}

// The stored sound as the server sends it, the same samples, back into the two channels
// a browser plays: numbers from -1 to 1.
export function channelsFrom16(samples) {
  const left = new Float32Array(samples.length / 2)
  const right = new Float32Array(samples.length / 2)
  for (let i = 0; i < left.length; i++) {
    left[i] = samples[2 * i] / 32768
    right[i] = samples[2 * i + 1] / 32768
  }
  return [left, right]
}

// The number of beats at or before a position in seconds.
export function beatsUntil(beats, position) {
  let low = 0
  let high = beats.length
  while (low < high) {
    const middle = (low + high) >> 1
    if (beats[middle] <= position) low = middle + 1
    else high = middle
  }
  return low
}

// The tempo to show at a position: the one of the last beat, or of the first beat before it.
export function bpmAt(result, position) {
  if (result.beats.length === 0) return null
  return Math.round(result.bpm[Math.max(0, beatsUntil(result.beats, position) - 1)])
}

// How many beats an ocho has, and so how far a count goes.
export const OCHO = 8

// The beat nearest to a time in seconds, or -1 when there is no beat.
export function nearestBeat(beats, seconds) {
  const after = beatsUntil(beats, seconds)
  if (after === 0) return beats.length ? 0 : -1
  if (after === beats.length) return after - 1
  return seconds - beats[after - 1] <= beats[after] - seconds ? after - 1 : after
}

// The count of every beat, 1 to 8, with what the user said. `count` is the analysis's.
// `ones` are the times of the beats the user set to count 1: from each of them the count
// runs in eights, up to the next one or to the end of the song. Before the first one the
// count is the analysis's. `byHand` are those beats, in order.
export function countsWith(beats, count, ones) {
  const byHand = [...new Set(ones.map((seconds) => nearestBeat(beats, seconds)))].filter((beat) => beat >= 0).sort((a, b) => a - b)
  const counted = count.slice()
  byHand.forEach((first, i) => {
    const end = i + 1 < byHand.length ? byHand[i + 1] : beats.length
    for (let beat = first; beat < end; beat++) counted[beat] = ((beat - first) % OCHO) + 1
  })
  return { count: counted, byHand }
}

// The ochos of a song: a new one starts wherever the count does not go on from the beat
// before, which is at every count 1. Each is { first, last }, beats, both included. One
// that was cut short, or that started before the song, has fewer than eight beats.
export function ochosOf(count) {
  const ochos = []
  count.forEach((value, beat) => {
    if (beat > 0 && value === count[beat - 1] + 1) ochos[ochos.length - 1].last = beat
    else ochos.push({ first: beat, last: beat })
  })
  return ochos
}

// The bars of a song: a new one starts with every ocho, and at its count 5. Each is
// { first, last }, beats, both included. One whose ocho was cut short, or that started
// before the song, has fewer than four beats.
export function barsOf(count) {
  const bars = []
  count.forEach((value, beat) => {
    if (beat > 0 && value !== 5 && value === count[beat - 1] + 1) bars[bars.length - 1].last = beat
    else bars.push({ first: beat, last: beat })
  })
  return bars
}

// The ocho a beat is in, as its place in ochosOf(), or -1 when there is none.
export function ochoOf(ochos, beat) {
  let low = 0
  let high = ochos.length
  while (low < high) {
    const middle = (low + high) >> 1
    if (ochos[middle].first <= beat) low = middle + 1
    else high = middle
  }
  return low - 1
}

// The bar a beat is in, as its place in barsOf(), or -1 when there is none.
export const barOf = ochoOf

// A loop starts this long before its first beat, and ends as long before the beat after
// its last one. The cut then falls just ahead of an attack and not inside it.
const LOOP_LEAD = 0.02

// The seconds a loop over the beats `first` to `last` plays, both included. From one
// pass to the next the beats stay as far apart as they are in the song.
export function loopOf(beats, first, last, duration) {
  const lead = Math.min(LOOP_LEAD, beats[first])
  // The last beat of a song lasts as long as the one before it.
  const after = last + 1 < beats.length ? beats[last + 1] : last > 0 ? Math.min(duration, 2 * beats[last] - beats[last - 1]) : duration
  return { start: beats[first] - lead, end: after - lead }
}

// Where the song is after `seconds` of playing that started at the beginning of the
// song, when the playing goes round `loop`. Without a loop it is `seconds` itself.
export function wrapped(seconds, loop) {
  if (!loop || seconds < loop.end) return seconds
  return loop.start + ((seconds - loop.start) % (loop.end - loop.start))
}

// The clicks to hand to the audio clock, up to `until`: one for every beat, on every
// pass of the loop. `from` is where the last call stopped: the next beat, and how many
// times the loop has gone round. Each click says its beat and when it sounds, in the
// same seconds as `until`: the seconds of playing, counted from the start of the song.
export function clicksUntil(beats, loop, from, until) {
  const clicks = []
  const length = loop ? loop.end - loop.start : 0
  let { beat, pass } = from
  for (;;) {
    if (loop && (beat >= beats.length || beats[beat] >= loop.end)) {
      // The end of the range: the next pass starts on the first beat inside it.
      beat = beats.findIndex((time) => time >= loop.start)
      pass++
      // A range with no beat in it has no click.
      if (beat < 0 || beats[beat] >= loop.end) break
    }
    if (beat >= beats.length) break
    const at = beats[beat] + pass * length
    if (at >= until) break
    clicks.push({ beat, at })
    beat++
  }
  return { clicks, next: { beat, pass } }
}

// The place of a beat: its bar, counted from 1 in the order of barsOf(), and which beat
// of that bar it is, from 1. A short bar has beats 1 to n, whatever their count. null
// when the song has no such beat. bachata/places.py does the same for the commands, and
// bachata/places_test.py compares the two.
export function placeOf(bars, beat) {
  const bar = barOf(bars, beat)
  return bar < 0 || beat > bars[bar].last ? null : { bar: bar + 1, beat: beat - bars[bar].first + 1 }
}

// A place as it is written: 24.3 is bar 24, beat 3.
export const placeText = (place) => `${place.bar}.${place.beat}`

// The place a text names. "24.3" is { bar, beat }, and "24" the first beat of that bar.
// "62.4s" is a time, { seconds }: the s is what tells it from a bar. null for anything else.
export function placeIn(text) {
  if (typeof text !== 'string') return null
  const named = /^([1-9][0-9]{0,5})(?:\.([1-9]))?$/.exec(text)
  if (named) return { bar: Number(named[1]), beat: Number(named[2] ?? 1) }
  const timed = /^([0-9]{1,5}(?:\.[0-9]{1,3})?)s$/.exec(text)
  return timed ? { seconds: Number(timed[1]) } : null
}

// The beat at a place, or -1 when the song has no such place. A time names the beat
// nearest to it, as a count 1 set by hand does.
export function beatAt(bars, beats, place, duration) {
  if ('seconds' in place) return place.seconds <= duration ? nearestBeat(beats, place.seconds) : -1
  const bar = bars[place.bar - 1]
  const beat = bar ? bar.first + place.beat - 1 : -1
  return bar && beat <= bar.last ? beat : -1
}

// What to say of a place the song does not have.
export function missing(bars, place) {
  if ('seconds' in place) return bars.length ? `This song ends before ${place.seconds} s.` : 'This song has no beats.'
  if (place.bar > bars.length) return `There is no bar ${place.bar} in this song.`
  return `Bar ${place.bar} has no beat ${place.beat}.`
}

// The address of a song: what follows the address of the page. Loaded with it, the page
// opens that song. With a place, as it is written, the page opens the song there.
export const addressOf = (id, at) => (at ? `?song=${id}&at=${at}` : `?song=${id}`)

// A place in a song as one line to hand to someone else: the name of the song, the bar
// and the beat, the seconds of that beat, which stay true when the bars are counted
// again, and the address that opens the song there. `page` is the address of the page.
export const placeLine = (name, id, place, seconds, page) =>
  `${name}, bar ${placeText(place)} (${seconds.toFixed(2)} s) ${page}${addressOf(id, placeText(place))}`

// The place an address names, as placeIn() gives it, or null.
export const atIn = (search) => placeIn(new URLSearchParams(search).get('at'))

// The song an address names: its id, as the server checks one, or null when the address
// names no song or nothing that could be one.
export function songIn(search) {
  const id = new URLSearchParams(search).get('song')
  return id !== null && /^[0-9a-f]{32}$/.test(id) ? id : null
}

// 75.4 seconds is shown as 1:15.
export function clock(seconds) {
  const whole = Math.max(0, Math.floor(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}
