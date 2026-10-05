// What the page works out about a song without the screen or the sound card:
// the type of a file, its id, its name from its tags, the samples to send, and
// what to show at a playing position. song.test.js checks it.

// What the page decodes to and sends. The server checks the same numbers again.
export const RATE = 44100
export const MIN_SECONDS = 20
export const MAX_SECONDS = 15 * 60
export const MAX_NAME = 200

const ascii = (bytes, at, length) => String.fromCharCode(...bytes.subarray(at, at + length))
const number = (bytes, at, length) => bytes.subarray(at, at + length).reduce((sum, byte) => sum * 256 + byte, 0)
// The sizes in an ID3 tag keep the top bit of every byte clear.
const synchsafe = (bytes, at) => bytes.subarray(at, at + 4).reduce((sum, byte) => sum * 128 + (byte & 0x7f), 0)

// 'mp3' or 'm4a', from the first bytes of the file and not from its name. null for anything else.
export function kindOf(bytes) {
  if (bytes.length < 12) return null
  if (ascii(bytes, 4, 4) === 'ftyp') return 'm4a'
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

// The name of a song: artist and title when the file has both, the title alone, or the
// file name without its extension. Never empty, and never longer than the server takes.
export function nameFor(tags, fileName) {
  const clean = (text) => (text ?? '').replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim()
  const title = clean(tags.title)
  const artist = clean(tags.artist)
  const name = (title && artist ? `${artist} - ${title}` : title) || clean(fileName.replace(/\.[^.]*$/, '')) || 'Unnamed song'
  // Cut by characters, as the server counts them, and not in the middle of one.
  return [...name].slice(0, MAX_NAME).join('').trim()
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

// 75.4 seconds is shown as 1:15.
export function clock(seconds) {
  const whole = Math.max(0, Math.floor(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}
