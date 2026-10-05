import test from 'node:test'
import assert from 'node:assert/strict'
import { beatsUntil, bpmAt, channelsFrom16, clock, idOf, interleaved16, kindOf, nameFor, tagsOf } from './song.js'

const bytesOf = (...parts) =>
  Uint8Array.from(parts.flatMap((part) => (typeof part === 'string' ? [...part].map((c) => c.charCodeAt(0)) : [...part])))
const be32 = (value) => [value >>> 24, (value >>> 16) & 255, (value >>> 8) & 255, value & 255]
const synchsafe = (value) => [(value >>> 21) & 127, (value >>> 14) & 127, (value >>> 7) & 127, value & 127]
const utf8 = (text) => [...new TextEncoder().encode(text)]
const utf16 = (text, big) => [...text].flatMap((c) => (big ? [c.charCodeAt(0) >> 8, c.charCodeAt(0) & 255] : [c.charCodeAt(0) & 255, c.charCodeAt(0) >> 8]))
const audio = [0xff, 0xfb, 0x90, 0x64, 0, 0, 0, 0, 0, 0, 0, 0]

// An ID3 tag of version 2.3 or 2.4, from frames given as [id, encoding byte, text bytes].
function id3(version, frames, { padding = 0 } = {}) {
  const body = frames.flatMap(([id, encoding, text]) => [
    ...bytesOf(id),
    ...(version === 4 ? synchsafe(text.length + 1) : be32(text.length + 1)),
    0,
    0,
    encoding,
    ...text,
  ])
  return bytesOf('ID3', [version, 0, 0], synchsafe(body.length + padding), body, new Array(padding).fill(0), audio)
}

const box = (type, ...content) => {
  const body = [...bytesOf(...content)]
  return [...be32(body.length + 8), ...bytesOf(type), ...body]
}
const m4aTag = (type, text) => box(type, box('data', be32(1), be32(0), utf8(text)))
const m4a = (...tags) =>
  bytesOf(
    box('ftyp', 'M4A ', be32(0)),
    box('mdat', audio),
    box('moov', box('mvhd', be32(0)), box('udta', box('meta', be32(0), box('hdlr', be32(0)), box('ilst', ...tags)))),
  )

test('the type of a file comes from its first bytes', () => {
  assert.equal(kindOf(bytesOf(audio)), 'mp3')
  assert.equal(kindOf(id3(3, [])), 'mp3')
  assert.equal(kindOf(m4a()), 'm4a')
  assert.equal(kindOf(bytesOf('RIFF', be32(0), 'WAVEfmt ')), null)
  assert.equal(kindOf(bytesOf('fLaC', be32(0), be32(0))), null)
  assert.equal(kindOf(bytesOf('OggS', be32(0), be32(0))), null)
  assert.equal(kindOf(bytesOf('<!doctype html><html>')), null)
  // The start of an AAC stream looks like an mp3 frame except for its layer.
  assert.equal(kindOf(bytesOf([0xff, 0xf1, 0x50, 0x80], be32(0), be32(0))), null)
  assert.equal(kindOf(bytesOf('ID3')), null)
  assert.equal(kindOf(new Uint8Array(0)), null)
})

test('the id of a song is the first 32 hex characters of its sha256', async () => {
  const sha256 = await crypto.subtle.digest('SHA-256', bytesOf('abc'))
  assert.equal(idOf(sha256), 'ba7816bf8f01cfea414140de5dae2223')
})

test('title and artist are read from an mp3, however the text is written', () => {
  const latin = id3(3, [['TPE1', 0, bytesOf('Grupo Extra')], ['TIT2', 0, [...bytesOf('Me Emborrachar'), 0xe9]]])
  assert.deepEqual(tagsOf(latin), { artist: 'Grupo Extra', title: 'Me Emborracharé' })

  const utf16le = id3(3, [['TIT2', 1, [0xff, 0xfe, ...utf16('Eso Es Amor')]], ['TALB', 0, bytesOf('An album')]])
  assert.deepEqual(tagsOf(utf16le), { title: 'Eso Es Amor' })
  const utf16be = id3(3, [['TIT2', 1, [0xfe, 0xff, ...utf16('Eso Es Amor', true)]]])
  assert.deepEqual(tagsOf(utf16be), { title: 'Eso Es Amor' })
  const utf16beNoMark = id3(4, [['TIT2', 2, utf16('Eso Es Amor', true)]])
  assert.deepEqual(tagsOf(utf16beNoMark), { title: 'Eso Es Amor' })

  const version4 = id3(4, [['TIT2', 3, [...utf8('El Perdedor'), 0, ...utf8('second value')]], ['TPE1', 3, utf8('Aventura')]], { padding: 64 })
  assert.deepEqual(tagsOf(version4), { title: 'El Perdedor', artist: 'Aventura' })

  // A frame of 300 bytes: in version 2.4 its size is written 7 bits to the byte.
  const long = 'x'.repeat(299)
  assert.deepEqual(tagsOf(id3(4, [['TIT2', 3, utf8(long)], ['TPE1', 3, utf8('After it')]])), { title: long, artist: 'After it' })
  assert.deepEqual(tagsOf(id3(3, [['TIT2', 3, utf8(long)], ['TPE1', 3, utf8('After it')]])), { title: long, artist: 'After it' })
})

test('title and artist are read from the older kinds of mp3 tag', () => {
  const version2 = bytesOf('ID3', [2, 0, 0], synchsafe(23), 'TT2', [0, 0, 6, 0], 'Title', 'TP1', [0, 0, 5, 0], 'Them', audio)
  assert.deepEqual(tagsOf(version2), { title: 'Title', artist: 'Them' })

  const atTheEnd = new Uint8Array(128)
  atTheEnd.set(bytesOf('TAG', 'Old title'), 0)
  atTheEnd.set(bytesOf('Old artist'), 33)
  assert.deepEqual(tagsOf(bytesOf(audio, atTheEnd)), { title: 'Old title', artist: 'Old artist' })
})

test('title and artist are read from an m4a', () => {
  assert.deepEqual(tagsOf(m4a(m4aTag('©nam', 'Me Emborracharé'), m4aTag('©alb', 'An album'), m4aTag('©ART', 'Grupo Extra'))), {
    title: 'Me Emborracharé',
    artist: 'Grupo Extra',
  })
  assert.deepEqual(tagsOf(m4a(m4aTag('©nam', 'Only a title'))), { title: 'Only a title' })
  assert.deepEqual(tagsOf(m4a()), {})
  assert.deepEqual(tagsOf(bytesOf(box('ftyp', 'M4A ', be32(0)), box('mdat', audio))), {})
})

test('a file without tags, or with a broken tag, has none', () => {
  assert.deepEqual(tagsOf(bytesOf(audio)), {})
  assert.deepEqual(tagsOf(id3(3, [])), {})
  // A tag that says it is far longer than the file.
  assert.deepEqual(tagsOf(bytesOf('ID3', [3, 0, 0], synchsafe(100000), 'TIT2', be32(90000), [0, 0, 0], 'cut')), {})
  // A box that says it is longer than the file.
  assert.deepEqual(tagsOf(bytesOf(box('ftyp', 'M4A ', be32(0)), be32(5000), 'moov', be32(0))), {})
  assert.deepEqual(tagsOf(new Uint8Array(0)), {})
})

test('the name is artist and title, the title alone, or the file name without its extension', () => {
  assert.equal(nameFor({ title: 'Me Emborracharé', artist: 'Grupo Extra' }, 'track01.mp3'), 'Grupo Extra - Me Emborracharé')
  assert.equal(nameFor({ title: 'Eso Es Amor' }, 'track02.mp3'), 'Eso Es Amor')
  assert.equal(nameFor({ artist: 'Aventura' }, 'El Perdedor.mp3'), 'El Perdedor')
  assert.equal(nameFor({}, 'Old Town Road (Bachata Remix).final.m4a'), 'Old Town Road (Bachata Remix).final')
  assert.equal(nameFor({ title: '   ', artist: '' }, 'mix.m4a'), 'mix')
  assert.equal(nameFor({}, 'no extension'), 'no extension')
  assert.equal(nameFor({}, '.mp3'), 'Unnamed song')
  assert.equal(nameFor({ title: ' two\r\nlines\tand\0more ' }, 'x.mp3'), 'two lines and more')
})

test('a name is cut to 200 characters, as the server counts them', () => {
  assert.equal(nameFor({ title: 'x'.repeat(500) }, 'x.mp3'), 'x'.repeat(200))
  const cut = nameFor({ title: '🎵'.repeat(300) }, 'x.mp3')
  assert.equal([...cut].length, 200)
  assert.equal(cut, '🎵'.repeat(200))
  assert.equal(nameFor({ title: 'a'.repeat(199) + ' b' }, 'x.mp3'), 'a'.repeat(199))
})

test('samples are sent as 16 bits, left and right in turn', () => {
  const left = Float32Array.from([0, 0.5, -0.5, 1, -1, 1.5, -1.5])
  const right = Float32Array.from([1 / 32768, -1 / 32768, 0.25, 0, 0, 0, 0])
  assert.deepEqual([...interleaved16(left, right)], [0, 1, 16384, -1, -16384, 8192, 32767, 0, -32768, 0, 32767, 0, -32768, 0])
  assert.equal(interleaved16(left, right).byteLength, 7 * 4)
})

test('the stored samples come back as the two channels that were sent', () => {
  const [left, right] = channelsFrom16(Int16Array.from([0, 1, 16384, -1, -32768, 32767]))
  assert.deepEqual([...left], [0, 0.5, -1])
  assert.deepEqual([...right], [1 / 32768, -1 / 32768, 32767 / 32768])
  // There and back gives the same samples, the loud ones included.
  const samples = Int16Array.from({ length: 65536 }, (_, i) => i - 32768)
  assert.deepEqual(interleaved16(...channelsFrom16(samples)), samples)
})

test('the shown tempo is the one of the last beat before the playing position', () => {
  const result = { beats: [1.0, 1.5, 2.0, 2.5], bpm: [120.4, 119.6, 124.5, 90] }
  assert.equal(beatsUntil(result.beats, 0), 0)
  assert.equal(beatsUntil(result.beats, 1.0), 1)
  assert.equal(beatsUntil(result.beats, 2.2), 3)
  assert.equal(beatsUntil(result.beats, 99), 4)
  assert.equal(bpmAt(result, 0), 120)
  assert.equal(bpmAt(result, 1.2), 120)
  assert.equal(bpmAt(result, 1.6), 120)
  assert.equal(bpmAt(result, 2.0), 125)
  assert.equal(bpmAt(result, 99), 90)
  assert.equal(bpmAt({ beats: [], bpm: [] }, 5), null)
})

test('a position is shown as minutes and seconds', () => {
  assert.equal(clock(0), '0:00')
  assert.equal(clock(75.4), '1:15')
  assert.equal(clock(599.99), '9:59')
  assert.equal(clock(-1), '0:00')
})
