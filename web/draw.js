// The two drawings of a song: the ocho that is sounding, large, and the whole song in
// rows of ochos. In the large view a beat is a small square with its count under it.
// Count 1 is an upright bar, and a count 1 the user set has a cap across its top. The
// beat that is sounding gets the large square a sign keeps for its pictogram, in the
// opposite of its ground, with its own mark inside it. In the song a bar is one thing: a
// plate with the count of its first beat on it, and the bar that is sounding is lit whole.

import { OCHO, barOf, clock } from './song.js'

// The custom properties a drawing reads from :root, by the name it uses for each.
const READ = {
  bandMark: '--band-mark',
  bandSounded: '--band-sounded',
  bandLit: '--band-lit',
  bandLitInk: '--band-lit-ink',
  mark: '--mark',
  plate: '--plate',
  ground: '--ground',
  lit: '--lit',
  litInk: '--lit-ink',
  hover: '--hover',
  loop: '--loop',
  loopFill: '--loop-fill',
  label: '--ink-soft',
  ink: '--ink',
  font: '--font',
}

let read = null

// What the style sheet sets: the colours and the typeface, as text.
export function tokens() {
  if (!read) {
    const style = getComputedStyle(document.documentElement)
    read = Object.fromEntries(Object.entries(READ).map(([name, property]) => [name, style.getPropertyValue(property).trim()]))
  }
  return read
}

// Light or dark changed: the properties are read again at the next drawing.
export function forgetTokens() {
  read = null
}

// A canvas with one point of its own for every pixel of the screen, cleared, and a pen
// that draws on it in the page's units.
function sheetOf(canvas) {
  const scale = window.devicePixelRatio || 1
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  const pixels = { width: Math.round(width * scale), height: Math.round(height * scale) }
  if (canvas.width !== pixels.width || canvas.height !== pixels.height) Object.assign(canvas, pixels)
  const pen = canvas.getContext('2d')
  pen.setTransform(scale, 0, 0, scale, 0, 0)
  pen.clearRect(0, 0, width, height)
  return { pen, width, height }
}

function square(pen, x, y, side, colour, corner = 0) {
  pen.beginPath()
  pen.roundRect(x - side / 2, y - side / 2, side, side, corner)
  pen.fillStyle = colour
  pen.fill()
}

// The mark of a beat, `unit` wide, around a point: a square, or for count 1 an upright
// bar. `byHand` adds the cap of a count 1 the user set. A form, never a colour alone.
function mark(pen, x, y, unit, colour, first, byHand) {
  pen.fillStyle = colour
  if (!first) return pen.fillRect(x - unit / 2, y - unit / 2, unit, unit)
  const tall = unit * 2.5
  pen.beginPath()
  pen.rect(x - unit / 2, y - tall / 2, unit, tall)
  if (byHand) {
    pen.rect(x - unit * 1.2, y - tall / 2, unit * 0.7, unit / 2)
    pen.rect(x + unit / 2, y - tall / 2, unit * 0.7, unit / 2)
  }
  pen.fill()
}

// ---- The ocho that is sounding

// Where the large view puts things, for a canvas this wide: eight places, one for each
// count, so a beat stands at the place of its count.
export function nowLayout(width) {
  return { step: width / OCHO }
}

// `ocho` is the ocho to show, { first, last }, or null when the song has no beat.
// `count` is the count of every beat and `byHand` the beats the user set to count 1.
// `lit` is the beat that is sounding, or -1, and `pulse` goes from 1 to 0 after it
// started: the large square swells with it. A beat that has sounded is fainter. An ocho
// of fewer than eight beats leaves the other places empty.
export function drawNow(canvas, { ocho, count, byHand, lit, pulse }) {
  const { pen, width, height } = sheetOf(canvas)
  if (!ocho) return
  const colours = tokens()
  const { step } = nowLayout(width)
  const size = Math.min(step * 0.6, height * 0.4)
  const y = height * 0.42
  pen.font = `700 ${Math.max(16, Math.min(size * 0.5, 44))}px ${colours.font}`
  pen.textAlign = 'center'
  pen.textBaseline = 'top'
  for (let beat = ocho.first; beat <= ocho.last; beat++) {
    const x = (count[beat] - 0.5) * step
    const first = count[beat] === 1
    if (beat === lit) {
      const side = size * (1.22 + 0.14 * pulse)
      square(pen, x, y, side, colours.bandLit, side * 0.09)
      mark(pen, x, y, size * 0.36, colours.bandLitInk, first, byHand.has(beat))
    } else {
      mark(pen, x, y, size * 0.36, beat < lit ? colours.bandSounded : colours.bandMark, first, byHand.has(beat))
    }
    pen.fillStyle = colours.bandMark
    pen.fillText(String(count[beat]), x, y + size * 0.78)
  }
}


// ---- The whole song, a plate for each bar

// All in pixels of the page. The room on the left of a row for its time, and on its right.
const LEFT = 80
const RIGHT = 16
// Between the two plates of an ocho, and between two ochos.
const INSIDE = 2
const BETWEEN = 14
// How high a plate is, how far the top of one row's plates is from the top of the next
// row's, and the room above the plates of the first row and under those of the last.
const HIGH = 30
const PITCH = 62
const EDGE = 28
// A row holds the most ochos, of these, that leave a whole plate at least NARROWEST wide.
// A whole plate is never wider than WIDEST.
const PER_ROW = [8, 4, 2, 1]
const NARROWEST = 44
const WIDEST = 96
// A plate narrower than this has no count written on it.
const ROOM_FOR_COUNT = 14

// The plates of a song on a canvas this wide. `ochos` are its ochos and `bars` its bars,
// each { first, last }. A bar of four beats has a whole plate. One of fewer has a
// narrower plate, so the ochos after it in its row stand further left, and the next row
// starts in line again. `plates` has, for every bar, the left and the top of its plate,
// how wide and how high it is, and the row and the ocho it is in. `rows` has the first
// and the last bar of every row, and `perRow` is how many ochos a row holds.
export function mapLayout(width, ochos, bars) {
  let perRow, whole
  for (perRow of PER_ROW) {
    whole = Math.min(WIDEST, Math.floor((width - LEFT - RIGHT - (perRow - 1) * BETWEEN - perRow * INSIDE) / (2 * perRow)))
    if (whole >= NARROWEST) break
  }
  const plates = []
  const rows = []
  let x = LEFT
  ochos.forEach((ocho, n) => {
    if (n % perRow === 0) {
      rows.push({ first: plates.length, last: plates.length })
      x = LEFT
    }
    const row = rows.length - 1
    // An ocho is one bar or two.
    for (let bar = plates.length; bar < bars.length && bars[bar].first <= ocho.last; bar++) {
      const wide = Math.round((whole * (bars[bar].last - bars[bar].first + 1)) / 4)
      plates.push({ x, y: EDGE + row * PITCH, wide, high: HIGH, row, ocho: n })
      rows[row].last = bar
      x += wide + INSIDE
    }
    x += BETWEEN - INSIDE
  })
  return { perRow, plates, rows, height: EDGE + (rows.length - 1) * PITCH + HIGH + EDGE }
}

// Where the band of a row starts, top to bottom: it is as high as the rows are apart,
// with the plates in its middle, so the bands of two rows meet.
const bandTop = (row) => EDGE + row * PITCH - (PITCH - HIGH) / 2

// The bar a point of the canvas belongs to, as its place in the bars, or -1 where there
// is none. Its row is the one whose band the point is in. In that row it is the bar
// whose plate the point is on, and between two plates the bar whose plate is nearer, the
// left one when both are as near. Left of the first plate of a row and right of its last
// there is no bar. With `nearest`, a point outside the rows takes the nearest row, and
// in it the nearest bar: a drag may leave the rows.
export function barAt(layout, x, y, nearest = false) {
  const { plates, rows } = layout
  if (rows.length === 0) return -1
  let row = Math.floor((y - bandTop(0)) / PITCH)
  if (nearest) row = Math.min(Math.max(row, 0), rows.length - 1)
  else if (row < 0 || row >= rows.length) return -1
  const { first, last } = rows[row]
  if (!nearest && (x < plates[first].x || x >= plates[last].x + plates[last].wide)) return -1
  let closest = first
  let least = Infinity
  for (let bar = first; bar <= last; bar++) {
    const away = Math.max(plates[bar].x - x, x - (plates[bar].x + plates[bar].wide), 0)
    if (away < least) {
      least = away
      closest = bar
    }
  }
  return closest
}

// Where the band of the row of a bar starts and ends, top to bottom.
export function rowOf(layout, bar) {
  const top = bandTop(layout.plates[bar].row)
  return { top, bottom: top + PITCH }
}

// How far under a point the line of a text goes, for the middle of what the text covers
// to be level with the point. A typeface puts the middle of its line elsewhere.
function level(pen, text) {
  const covered = pen.measureText(text)
  return (covered.actualBoundingBoxAscent - covered.actualBoundingBoxDescent) / 2
}

// The count of a bar, with the middle of what it covers on a point, both ways.
function figure(pen, text, x, y) {
  const covered = pen.measureText(text)
  pen.fillText(text, x + (covered.actualBoundingBoxLeft - covered.actualBoundingBoxRight) / 2, y + level(pen, text))
}

// The lid of a count 1 the user set, over a plate or over the block of a lit bar: a
// strip 4 high, 3 above it, and 3 wider than it on each side.
function lid(pen, x, y, wide, colour) {
  pen.fillStyle = colour
  pen.fillRect(x - 3, y - 7, wide + 6, 4)
}

// How far the band of a range reaches beyond a plate, on its left (-1) or on its right
// (1): 8, into the room between two ochos or at the end of a row, and 1 where the other
// plate of its ocho is on that side, into the 2 pixels between them.
const reach = (plates, bar, side) => (plates[bar + side]?.ocho === plates[bar].ocho ? 1 : 8)

// One row's part of a marked range, over the bars `first` to `last` of that row: a band
// of the sign's yellow while the playing goes round it, two dashed rules while it does
// not, and a bracket where the range starts and where it ends.
function loopRun(pen, plates, first, last, { opens, closes, on }, colours) {
  const left = plates[first].x - reach(plates, first, -1)
  const right = plates[last].x + plates[last].wide + reach(plates, last, 1)
  const top = plates[first].y - 8
  const tall = plates[first].high + 16
  if (on) {
    pen.fillStyle = colours.loopFill
    pen.fillRect(left, top, right - left, tall)
  } else {
    pen.strokeStyle = colours.loop
    pen.lineWidth = 1.5
    pen.setLineDash([6, 5])
    pen.beginPath()
    pen.moveTo(left, top)
    pen.lineTo(right, top)
    pen.moveTo(left, top + tall)
    pen.lineTo(right, top + tall)
    pen.stroke()
    pen.setLineDash([])
  }
  pen.fillStyle = colours.loop
  if (opens) {
    pen.fillRect(left, top, 4, tall)
    pen.fillRect(left, top, 10, 4)
    pen.fillRect(left, top + tall - 4, 10, 4)
  }
  if (closes) {
    pen.fillRect(right - 4, top, 4, tall)
    pen.fillRect(right - 10, top, 10, 4)
    pen.fillRect(right - 10, top + tall - 4, 10, 4)
  }
}

// `beats` are the times of the beats, `bars` the bars of the song, `count` the count of
// every beat and `byHand` the beats the user set to count 1. `lit` is the bar that is
// sounding and `hover` the bar under the pointer, each as its place in `bars`, or -1.
// `range` is the marked range in beats, { first, last, on }, or null. `on` says whether
// the playing goes round it.
export function drawMap(canvas, layout, { beats, bars, count, byHand, lit, hover, range }) {
  const { pen } = sheetOf(canvas)
  const colours = tokens()
  const { plates, rows } = layout

  if (range && plates.length) {
    // Every bar that holds a beat of the range is covered whole: one run for every row
    // the range touches. The runs come first, so the plates stand on them.
    const from = barOf(bars, range.first)
    const to = barOf(bars, range.last)
    for (let row = plates[from].row; row <= plates[to].row; row++) {
      const first = Math.max(from, rows[row].first)
      const last = Math.min(to, rows[row].last)
      loopRun(pen, plates, first, last, { opens: first === from, closes: last === to, on: range.on }, colours)
    }
  }

  pen.textBaseline = 'alphabetic'
  pen.font = `500 12px ${colours.font}`
  pen.textAlign = 'right'
  pen.fillStyle = colours.label
  for (const row of rows) {
    const time = clock(beats[bars[row.first].first])
    pen.fillText(time, LEFT - 14, plates[row.first].y + HIGH / 2 + level(pen, time))
  }

  // The halo of the bar under the pointer, behind its plate. A lit bar has none.
  if (hover >= 0 && hover !== lit) {
    const { x, y, wide, high } = plates[hover]
    pen.fillStyle = colours.hover
    pen.fillRect(x - 4, y - 4, wide + 8, high + 8)
  }

  // A plate for each bar, with the count of its first beat. The first bar of an ocho is
  // solid and the second quiet: told apart by the fill and by the count, never by colour
  // alone. Nothing keeps a place for the beats inside a bar.
  pen.textAlign = 'center'
  plates.forEach(({ x, y, wide, high }, bar) => {
    if (bar === lit) return
    const start = bars[bar].first
    const first = count[start] <= OCHO / 2
    pen.fillStyle = first ? colours.mark : colours.plate
    pen.fillRect(x, y, wide, high)
    if (wide >= ROOM_FOR_COUNT) {
      pen.font = `${first ? 700 : 500} 15px ${colours.font}`
      pen.fillStyle = first ? colours.ground : colours.ink
      figure(pen, String(count[start]), x + wide / 2, y + high / 2)
    }
    if (byHand.has(start)) lid(pen, x, y, wide, colours.mark)
  })

  // The bar that is sounding is a block in place of its plate, drawn last, over the
  // edges of its neighbours. A count 1 the user set keeps its lid while its bar sounds.
  if (lit >= 0) {
    const { x, y, wide, high } = plates[lit]
    const start = bars[lit].first
    pen.beginPath()
    pen.roundRect(x - 5, y - 6, wide + 10, high + 12, 2)
    pen.fillStyle = colours.lit
    pen.fill()
    pen.font = `700 17px ${colours.font}`
    pen.fillStyle = colours.litInk
    figure(pen, String(count[start]), x + wide / 2, y + high / 2)
    if (byHand.has(start)) lid(pen, x - 5, y - 6, wide + 10, colours.mark)
  }
}
