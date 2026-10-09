import test from 'node:test'
import assert from 'node:assert/strict'
import {
  addressOf,
  atIn,
  barOf,
  beatAt,
  barsOf,
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
  placeIn,
  placeLine,
  placeOf,
  placeText,
  songIn,
  tagsOf,
  wrapped,
} from './song.js'

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

const le32 = (value) => [value & 255, (value >>> 8) & 255, (value >>> 16) & 255, value >>> 24]

// One packet of an Ogg file, cut into pages that hold `perPage` segments each. A segment
// is 255 bytes, and a shorter one ends the packet.
function oggPages(packet, perPage = 255) {
  const body = [...bytesOf(...packet)]
  const lacing = [...new Array(Math.floor(body.length / 255)).fill(255), body.length % 255]
  const pages = []
  for (let from = 0, at = 0; from < lacing.length; from += perPage) {
    const segments = lacing.slice(from, from + perPage)
    const size = segments.reduce((sum, length) => sum + length, 0)
    // "OggS", the version, a flag for a page that goes on with a packet, then 20 bytes
    // the page has no use for here: a position, the number of the stream, of the page,
    // and a checksum.
    pages.push(...bytesOf('OggS', [0, from > 0 ? 1 : 0], new Array(20).fill(0), [segments.length], segments, body.slice(at, at + size)))
    at += size
  }
  return pages
}

// An Ogg file with sound of the kind `head` names, tags, and a page of sound.
const ogg = (head, ...tags) => bytesOf(oggPages([head, new Array(11).fill(0)]), ...tags, oggPages([new Array(300).fill(7)]))
const opusTags = (comments, perPage) =>
  oggPages(['OpusTags', le32(4), 'test', le32(comments.length), comments.flatMap((comment) => [...le32(utf8(comment).length), ...utf8(comment)])], perPage)
const opus = (comments = [], perPage) => ogg('OpusHead', opusTags(comments, perPage))

test('the type of a file comes from its first bytes', () => {
  assert.equal(kindOf(bytesOf(audio)), 'mp3')
  assert.equal(kindOf(id3(3, [])), 'mp3')
  assert.equal(kindOf(m4a()), 'm4a')
  assert.equal(kindOf(opus()), 'opus')
  // Other sound in the wrapping of opus is not taken: Vorbis, and a film.
  assert.equal(kindOf(ogg('\x01vorbis')), null)
  assert.equal(kindOf(ogg('\x80theora')), null)
  assert.equal(kindOf(bytesOf('OggS', new Array(22).fill(0), [1, 19], 'Opus')), null)
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

test('title and artist are read from an opus file, however their names are written', () => {
  assert.deepEqual(tagsOf(opus(['TITLE=Me Emborracharé', 'ARTIST=Grupo Extra', 'ALBUM=Colores'])), { title: 'Me Emborracharé', artist: 'Grupo Extra' })
  // ffmpeg writes the names in small letters.
  assert.deepEqual(tagsOf(opus(['encoder=Lavf62', 'artist=Jiory', 'title=Eso Es Amor'])), { title: 'Eso Es Amor', artist: 'Jiory' })
  assert.deepEqual(tagsOf(opus(['Title=A = B'])), { title: 'A = B' })
  // Of two artists the first is taken. A text without a name, or with another, is passed over.
  assert.deepEqual(tagsOf(opus(['=nothing', 'no name', 'ARTIST=First', 'ARTIST=Second', 'SUBTITLE=x'])), { artist: 'First' })
  assert.deepEqual(tagsOf(opus()), {})
})

test('the tags of an opus file are read across its pages', () => {
  // A cover picture among the tags makes them run over many pages. Here a page holds
  // two segments, and the title comes after a text of 2,000 bytes.
  const picture = `METADATA_BLOCK_PICTURE=${'A'.repeat(2000)}`
  const file = opus(['artist=Aventura', picture, 'title=Por un Segundo'], 2)
  assert.ok(file.length > 2000)
  assert.deepEqual(tagsOf(file), { title: 'Por un Segundo', artist: 'Aventura' })
  // Tags that end exactly at the end of a segment have an empty one after them.
  const exact = opus([`title=${'x'.repeat(255 - 8 - 8 - 4 - 4 - 6)}`])
  assert.equal(tagsOf(exact).title.length, 255 - 8 - 8 - 4 - 4 - 6)
})

test('a file without tags, or with a broken tag, has none', () => {
  // An opus file cut short inside its tags, one whose tags say they are longer than they
  // are, and one with something else where its tags should be.
  const whole = opus(['title=Cut'])
  assert.deepEqual(tagsOf(whole.subarray(0, 60)), {})
  assert.deepEqual(tagsOf(ogg('OpusHead', oggPages(['OpusTags', le32(4), 'test', le32(1), le32(5000), 'title=Short']))), {})
  assert.deepEqual(tagsOf(ogg('OpusHead', oggPages(['NotTags!', le32(0), le32(0)]))), {})
  assert.deepEqual(tagsOf(ogg('OpusHead')), {})
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

test('a typed name is made one line and cut like a name from a tag', () => {
  assert.equal(cleanName('  Me\tEmborracharé \r\n (mix) '), 'Me Emborracharé (mix)')
  assert.equal(cleanName(' \n '), '')
  assert.equal(cleanName(undefined), '')
  assert.equal([...cleanName('🎵'.repeat(300))].length, 200)
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

const near = (value, expected) => assert.ok(Math.abs(value - expected) < 1e-9, `${value} is not ${expected}`)

test('a loop over some beats lasts exactly from its first beat to the beat after its last', () => {
  const beats = [0.5, 1.0, 1.5, 2.1, 2.6, 3.1]
  const loop = loopOf(beats, 1, 3, 10)
  near(loop.end - loop.start, 2.6 - 1.0)
  // It starts a moment before the first beat, so the cut is not inside an attack.
  assert.ok(loop.start < 1.0 && loop.start > 0.9)
  // The last beat of the song lasts as long as the one before it, and no longer than the song.
  near(loopOf(beats, 4, 5, 10).end - loopOf(beats, 4, 5, 10).start, 3.6 - 2.6)
  near(loopOf(beats, 4, 5, 3.3).end - loopOf(beats, 4, 5, 3.3).start, 3.3 - 2.6)
  // A first beat at the very start of the song leaves no room before it.
  assert.deepEqual(loopOf([0, 0.5, 1.0], 0, 0, 10), { start: 0, end: 0.5 })
  near(loopOf([0.01, 0.51, 1.01], 0, 1, 10).start, 0)
  near(loopOf([0.01, 0.51, 1.01], 0, 1, 10).end, 1.0)
  // A song with one beat only: the loop runs to the end of the song.
  assert.deepEqual(loopOf([4], 0, 0, 10), { start: 3.98, end: 9.98 })
})

test('the position of a looping song goes round the loop', () => {
  const loop = { start: 2, end: 5 }
  assert.equal(wrapped(1.5, loop), 1.5)
  assert.equal(wrapped(4.5, loop), 4.5)
  assert.equal(wrapped(5, loop), 2)
  assert.equal(wrapped(6.5, loop), 3.5)
  assert.equal(wrapped(12.5, loop), 3.5)
  assert.equal(wrapped(12.5, null), 12.5)
})

test('every beat gets one click, at its own time', () => {
  const beats = [0.5, 1.0, 1.5, 2.0]
  const first = clicksUntil(beats, null, { beat: 0, pass: 0 }, 1.2)
  assert.deepEqual(first.clicks, [{ beat: 0, at: 0.5 }, { beat: 1, at: 1.0 }])
  // The next call goes on where this one stopped, and the song ends with its last beat.
  const rest = clicksUntil(beats, null, first.next, 99)
  assert.deepEqual(rest.clicks, [{ beat: 2, at: 1.5 }, { beat: 3, at: 2.0 }])
  assert.deepEqual(clicksUntil(beats, null, rest.next, 999).clicks, [])
  // Playing from the middle: the beats before that point get none.
  assert.deepEqual(clicksUntil(beats, null, { beat: 2, pass: 0 }, 99).clicks.map((click) => click.beat), [2, 3])
})

test('on every pass of a loop each beat inside it gets one click, at its own time', () => {
  const beats = [0.5, 1.0, 1.5, 2.1, 2.6, 3.1, 3.6]
  const loop = loopOf(beats, 2, 4, 10)
  const length = loop.end - loop.start
  near(length, 3.1 - 1.5)

  // The playing starts before the loop: the beats on the way in sound once.
  let placed = clicksUntil(beats, loop, { beat: 0, pass: 0 }, 2.0)
  assert.deepEqual(placed.clicks.map((click) => click.beat), [0, 1, 2])
  const clicks = [...placed.clicks]
  // Handed over in small steps, as the page does, nothing is lost and nothing comes twice.
  for (let until = 2.3; until < 12; until += 0.3) {
    placed = clicksUntil(beats, loop, placed.next, until)
    clicks.push(...placed.clicks)
  }
  assert.deepEqual(clicks.slice(0, 11).map((click) => click.beat), [0, 1, 2, 3, 4, 2, 3, 4, 2, 3, 4])
  for (const [n, click] of clicks.entries()) {
    const pass = n < 5 ? 0 : Math.floor((n - 5) / 3) + 1
    near(click.at, beats[click.beat] + pass * length)
    // The song is on that beat when the click sounds.
    near(wrapped(click.at, loop), beats[click.beat])
  }
  // The clicks of the loop are as far apart as the beats are, across the turn as well.
  near(clicks[5].at - clicks[4].at, 3.1 - 2.6)
  assert.ok(clicks.length >= 5 + 3 * 5)

  // A range with no beat in it has no click, and the call still returns.
  assert.deepEqual(clicksUntil(beats, { start: 1.1, end: 1.4 }, { beat: 2, pass: 0 }, 99).clicks, [])
  assert.deepEqual(clicksUntil(beats, { start: 5, end: 6 }, { beat: 7, pass: 0 }, 99).clicks, [])
})

test('a position is shown as minutes and seconds', () => {
  assert.equal(clock(0), '0:00')
  assert.equal(clock(75.4), '1:15')
  assert.equal(clock(599.99), '9:59')
  assert.equal(clock(-1), '0:00')
})

// A beat every half second from 1.0 s, counted in eights from the first one.
const steady = (length) => Array.from({ length }, (_, n) => 1 + n * 0.5)
const eights = (length, first = 0) => Array.from({ length }, (_, n) => ((((n - first) % 8) + 8) % 8) + 1)

test('the beat nearest to a time', () => {
  const beats = steady(4)
  assert.equal(nearestBeat(beats, 0), 0)
  assert.equal(nearestBeat(beats, 1.2), 0)
  assert.equal(nearestBeat(beats, 1.3), 1)
  assert.equal(nearestBeat(beats, 2.5), 3)
  assert.equal(nearestBeat(beats, 99), 3)
  assert.equal(nearestBeat([], 1), -1)
})

test('without a beat set by hand the count is the one of the analysis', () => {
  const counted = countsWith(steady(20), eights(20), [])
  assert.deepEqual(counted.count, eights(20))
  assert.deepEqual(counted.byHand, [])
})

test('from a beat set to count 1 the count runs in eights', () => {
  const beats = steady(30)
  // The user says the thirteenth beat is count 1: the bar before it is left alone.
  const analysed = eights(30)
  const counted = countsWith(beats, analysed, [beats[12]])
  assert.deepEqual(counted.count.slice(0, 12), [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4])
  assert.deepEqual(counted.count.slice(12), eights(18))
  assert.deepEqual(counted.byHand, [12])
  // What the analysis counted is not changed: the page counts from it again at every change.
  assert.deepEqual(analysed, eights(30))
})

test('each beat set by hand holds up to the next one', () => {
  const beats = steady(40)
  const counted = countsWith(beats, eights(40, 2), [beats[21], beats[5]])
  // Before the first one, the analysis: a song that starts inside a bar.
  assert.deepEqual(counted.count.slice(0, 5), [7, 8, 1, 2, 3])
  assert.deepEqual(counted.count.slice(5, 21), eights(16))
  assert.deepEqual(counted.count.slice(21), eights(19))
  assert.deepEqual(counted.byHand, [5, 21])
})

test('a time kept by the server finds its beat again after another analysis', () => {
  // The beats moved by 20 ms, and the time sits between two of them.
  const beats = steady(16).map((time) => time + 0.02)
  const counted = countsWith(beats, eights(16), [3.0, 3.01, 99])
  assert.deepEqual(counted.byHand, [4, 15])
  assert.equal(counted.count[4], 1)
  assert.deepEqual(countsWith([], [], [1]).byHand, [])
})

test('an ocho starts at every count 1 and may be short', () => {
  assert.deepEqual(ochosOf(eights(20)), [{ first: 0, last: 7 }, { first: 8, last: 15 }, { first: 16, last: 19 }])
  // A song that starts inside a bar, and a half phrase made by a beat set by hand.
  const count = [7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8, 1]
  const ochos = ochosOf(count)
  assert.deepEqual(ochos, [
    { first: 0, last: 1 },
    { first: 2, last: 9 },
    { first: 10, last: 13 },
    { first: 14, last: 21 },
    { first: 22, last: 22 },
  ])
  assert.deepEqual(ochosOf([]), [])
  // Two beats set by hand side by side: each is an ocho of its own.
  assert.deepEqual(ochosOf([1, 1, 2]), [{ first: 0, last: 0 }, { first: 1, last: 2 }])

  assert.deepEqual([0, 1, 2, 9, 10, 13, 14, 22].map((beat) => ochoOf(ochos, beat)), [0, 0, 1, 1, 2, 2, 3, 4])
  assert.equal(ochoOf([], 3), -1)
})

// A bar, as barsOf() gives one.
const bar = (first, last) => ({ first, last })

test('a bar starts with every ocho and at its count 5', () => {
  assert.deepEqual(barsOf(eights(16)), [bar(0, 3), bar(4, 7), bar(8, 11), bar(12, 15)])
  // Every ocho starts a bar, the short ones too.
  const count = [7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8, 1]
  const starts = barsOf(count).map((one) => one.first)
  for (const ocho of ochosOf(count)) assert.ok(starts.includes(ocho.first), `the ocho at ${ocho.first} starts no bar`)
  // And nothing else starts one: a bar starts on the first beat, on a count 5, or where the count does not go on.
  assert.deepEqual(starts, [0, 2, 6, 10, 14, 18, 22])
  // A count that jumps to something that is neither 1 nor 5 does not go on either: a bar starts there.
  assert.deepEqual(barsOf([1, 2, 3, 7, 8, 1, 2]), [bar(0, 2), bar(3, 4), bar(5, 6)])
})

test('a song that starts inside a bar has a short first bar, and a song may end on one', () => {
  assert.deepEqual(barsOf(eights(12, 2)), [bar(0, 1), bar(2, 5), bar(6, 9), bar(10, 11)])
  assert.deepEqual(barsOf(eights(7, 5)), [bar(0, 0), bar(1, 4), bar(5, 6)])
  assert.deepEqual(barsOf(eights(18)), [bar(0, 3), bar(4, 7), bar(8, 11), bar(12, 15), bar(16, 17)])
})

test('a beat set by hand starts a bar wherever it is', () => {
  const beats = steady(24)
  const withOnes = (...set) => countsWith(beats, eights(24), set.map((beat) => beats[beat])).count
  // On a count 5: the bar before it is left alone, a first bar with no second.
  const swapped = withOnes(12)
  assert.deepEqual(barsOf(swapped), [bar(0, 3), bar(4, 7), bar(8, 11), bar(12, 15), bar(16, 19), bar(20, 23)])
  assert.deepEqual(barsOf(swapped).map((one) => swapped[one.first]), [1, 5, 1, 1, 5, 1])
  // Inside a bar: that bar is cut, and a bar starts on the beat.
  const cut = withOnes(10)
  assert.deepEqual(barsOf(cut), [bar(0, 3), bar(4, 7), bar(8, 9), bar(10, 13), bar(14, 17), bar(18, 21), bar(22, 23)])
  assert.deepEqual(barsOf(cut).map((one) => cut[one.first]), [1, 5, 1, 1, 5, 1, 5])
  // Two set side by side each start one.
  assert.deepEqual(barsOf(withOnes(5, 6)).slice(0, 5), [bar(0, 3), bar(4, 4), bar(5, 5), bar(6, 9), bar(10, 13)])
})

test('every beat is in exactly one bar, and a song with no beat has none', () => {
  const count = [7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8, 1]
  const bars = barsOf(count)
  assert.deepEqual(bars.flatMap((one) => Array.from({ length: one.last - one.first + 1 }, (_, n) => one.first + n)), count.map((_, beat) => beat))
  // And the bar of a beat is found again from the beat.
  assert.deepEqual(count.map((_, beat) => barOf(bars, beat)), [0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6])
  assert.equal(barOf(bars, -1), -1)
  assert.deepEqual(barsOf([]), [])
  assert.equal(barOf([], 3), -1)
})

test('every beat has one place, a bar and a beat from 1, and the place leads back to it', () => {
  const count = [7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8, 1]
  const beats = steady(count.length)
  const bars = barsOf(count)
  const places = count.map((_, beat) => placeText(placeOf(bars, beat)))
  assert.deepEqual(places.slice(0, 7), ['1.1', '1.2', '2.1', '2.2', '2.3', '2.4', '3.1'])
  assert.equal(places.at(-1), '7.1')
  assert.equal(new Set(places).size, count.length)
  places.forEach((text, beat) => assert.equal(beatAt(bars, beats, placeIn(text), 60), beat))
  // No beat, no place.
  assert.equal(placeOf(bars, -1), null)
  assert.equal(placeOf(bars, count.length), null)
  assert.equal(placeOf([], 0), null)
})

test('a short bar has beats 1 to n, and no more', () => {
  const beats = steady(24)
  // A count 1 set on the eleventh beat cuts the third bar to two beats: counts 1 and 2, then 1 again.
  const cut = barsOf(countsWith(beats, eights(24), [beats[10]]).count)
  assert.deepEqual(placeOf(cut, 9), { bar: 3, beat: 2 })
  assert.deepEqual(placeOf(cut, 10), { bar: 4, beat: 1 })
  assert.equal(beatAt(cut, beats, { bar: 3, beat: 2 }, 60), 9)
  assert.equal(beatAt(cut, beats, { bar: 3, beat: 3 }, 60), -1)
  assert.equal(missing(cut, { bar: 3, beat: 3 }), 'Bar 3 has no beat 3.')
  // A song that starts inside a bar: its first two beats are 1.1 and 1.2, with counts 7 and 8.
  const late = barsOf(eights(12, 2))
  assert.deepEqual(placeOf(late, 1), { bar: 1, beat: 2 })
  assert.equal(beatAt(late, steady(12), { bar: 1, beat: 3 }, 60), -1)
  // The bars end with the song.
  const whole = barsOf(eights(16))
  assert.equal(beatAt(whole, steady(16), { bar: 4, beat: 4 }, 60), 15)
  assert.equal(beatAt(whole, steady(16), { bar: 5, beat: 1 }, 60), -1)
  assert.equal(missing(whole, { bar: 5, beat: 1 }), 'There is no bar 5 in this song.')
  // The last bar is in the song: what it lacks is the beat.
  assert.equal(beatAt(whole, steady(16), { bar: 4, beat: 5 }, 60), -1)
  assert.equal(missing(whole, { bar: 4, beat: 5 }), 'Bar 4 has no beat 5.')
  assert.equal(beatAt([], [], { bar: 1, beat: 1 }, 60), -1)
})

test('a place is read from 24.3, from 24 and from 62.4s, and from nothing else', () => {
  assert.deepEqual(placeIn('24.3'), { bar: 24, beat: 3 })
  assert.deepEqual(placeIn('24'), { bar: 24, beat: 1 })
  assert.deepEqual(placeIn('1.1'), { bar: 1, beat: 1 })
  assert.deepEqual(placeIn('62.4s'), { seconds: 62.4 })
  assert.deepEqual(placeIn('62s'), { seconds: 62 })
  assert.deepEqual(placeIn('0s'), { seconds: 0 })
  const refused = ['0', '24.0', '0.3', '24.3.1', '-1', '-1.2', '1e3', '024', '24.', '.3', '24.10', '24,3', ' 24.3', '24.3 ']
  refused.push('62.4 s', '62.4S', '62.4sec', 's', '-3s', '1e3s', '62.s', '62.4444s', '1:02', 'bar 24', 'abc', '', '1234567', '123456s')
  for (const text of refused) assert.equal(placeIn(text), null, `"${text}" was read`)
  for (const other of [null, undefined, 24.3, ['24.3']]) assert.equal(placeIn(other), null)
})

test('a time names the beat nearest to it, up to the end of the song', () => {
  const beats = steady(16)
  const bars = barsOf(eights(16))
  assert.equal(beatAt(bars, beats, { seconds: 0 }, 9), 0)
  assert.equal(beatAt(bars, beats, { seconds: 3.2 }, 9), 4)
  assert.equal(beatAt(bars, beats, { seconds: 3.3 }, 9), 5)
  assert.equal(beatAt(bars, beats, { seconds: 9 }, 9), 15)
  assert.equal(beatAt(bars, beats, { seconds: 9.001 }, 9), -1)
  assert.equal(missing(bars, { seconds: 9.5 }), 'This song ends before 9.5 s.')
  assert.equal(beatAt([], [], { seconds: 3 }, 9), -1)
  assert.equal(missing([], { seconds: 3 }), 'This song has no beats.')
})

test('the address of a song can carry a place', () => {
  const id = 'ab01'.repeat(8)
  assert.equal(addressOf(id, '24.3'), `?song=${id}&at=24.3`)
  assert.equal(addressOf(id, null), `?song=${id}`)
  assert.equal(songIn(addressOf(id, '24.3')), id)
  assert.deepEqual(atIn(addressOf(id, '24.3')), { bar: 24, beat: 3 })
  assert.deepEqual(atIn(addressOf(id, '24')), { bar: 24, beat: 1 })
  assert.deepEqual(atIn(addressOf(id, '62.4s')), { seconds: 62.4 })
  assert.equal(atIn(addressOf(id)), null)
  assert.equal(atIn(`?song=${id}&at=`), null)
  assert.equal(atIn(`?song=${id}&at=x`), null)
  assert.equal(atIn(`?song=${id}&at=24.3&at=5`).bar, 24)
})

test('a place is handed over as one line, with its seconds and the address that opens it', () => {
  const id = 'ab01'.repeat(8)
  const line = placeLine('Romeo Santos - Sus Huellas', id, { bar: 24, beat: 3 }, 62.408, 'http://127.0.0.1:8080/')
  assert.equal(line, `Romeo Santos - Sus Huellas, bar 24.3 (62.41 s) http://127.0.0.1:8080/?song=${id}&at=24.3`)
  assert.equal(placeLine('A', id, { bar: 1, beat: 1 }, 0.5, 'http://localhost/'), `A, bar 1.1 (0.50 s) http://localhost/?song=${id}&at=1.1`)
  // The address in the line opens the song at the place the line says.
  assert.deepEqual(atIn(new URL(line.split(' ').at(-1)).search), { bar: 24, beat: 3 })
  assert.equal(songIn(new URL(line.split(' ').at(-1)).search), id)
})

test('a song has an address of its own', () => {
  const id = 'ab01'.repeat(8)
  assert.equal(addressOf(id), `?song=${id}`)
  assert.equal(songIn(addressOf(id)), id)
  assert.equal(songIn(`?from=mail&song=${id}`), id)
  // No song, or something that cannot be the id of one.
  assert.equal(songIn(''), null)
  assert.equal(songIn('?song='), null)
  assert.equal(songIn('?song=../../etc/passwd'), null)
  assert.equal(songIn(`?song=${id.toUpperCase()}`), null)
  assert.equal(songIn(`?song=${id}0`), null)
  assert.equal(songIn(`?song=${id.slice(1)}`), null)
})
