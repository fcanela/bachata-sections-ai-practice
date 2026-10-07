// The two drawings of a song. The ocho that is sounding, large: a beat is a small square
// with its count under it, count 1 is an upright bar, and a count 1 the user set has a cap
// across its top. The beat that is sounding gets the large square a sign keeps for its
// pictogram, in the opposite of its ground, with its own mark inside it. And the whole
// song in rows of ochos: a plate for each bar, with the count of its first beat on it.

import { OCHO, clock } from './song.js'

// The custom properties a drawing reads from :root, by the name it uses for each.
const READ = {
  bandMark: '--band-mark',
  bandSounded: '--band-sounded',
  bandLit: '--band-lit',
  bandLitInk: '--band-lit-ink',
  mark: '--mark',
  lit: '--lit',
  litInk: '--lit-ink',
  hover: '--hover',
  loop: '--loop',
  loopFill: '--loop-fill',
  label: '--ink-soft',
  ink: '--ink',
  ground: '--ground',
  plate: '--plate',
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

// ---- The whole song

// A bar is four beats, and its plate is this high.
const BAR = 4
const HIGH = 30
// A row holds eight ochos when their plates are this wide or wider, and four, two or one
// when they are not. A plate is never wider than the widest.
const NARROWEST = 44
const WIDEST = 96
// A plate narrower than this has no count written on it.
const WRITTEN = 14
// The room on the left of a row for its time, and on its right.
const LEFT = 80
const RIGHT = 16
// Between the two plates of an ocho, and between two ochos.
const INSIDE = 2
const BETWEEN = 14
// Above the plates of the first row and under those of the last, and from the top of one
// row's plates to the top of the next row's.
const EDGE = 28
const PITCH = 62
// How far the band of a row reaches above its plates and under them, for the pointer.
// The bands of two rows meet.
const REACH = (PITCH - HIGH) / 2
// How far the band of a marked range reaches above the plates and under them, and
// beyond a plate at its side: into the room between two ochos, and inside an ocho.
const BAND = 8
const BAND_INSIDE = 1

// The rows of a song on a canvas this wide. `ochos` are its ochos and `bars` its bars,
// each { first, last }: an ocho is one or two bars. A row holds `perRow` ochos. A short
// bar has a narrower plate, so the ochos after it in its row stand further left, and the
// next row starts in line again. `plates` has the plate of every bar: its left, its top,
// its width and its height, the row it is in and its ocho. `rows` has the first and the
// last bar of every row.
export function mapLayout(width, ochos, bars) {
  let perRow, whole
  for (perRow of [8, 4, 2, 1]) {
    whole = Math.min(WIDEST, Math.floor((width - LEFT - RIGHT - (perRow - 1) * BETWEEN - perRow * INSIDE) / (2 * perRow)))
    if (whole >= NARROWEST) break
  }
  whole = Math.max(whole, BAR)
  const plates = []
  const rows = []
  let end = LEFT
  ochos.forEach((ocho, n) => {
    if (n % perRow === 0) {
      rows.push({ first: plates.length, last: plates.length })
      end = LEFT
    }
    const row = rows.length - 1
    for (let bar = plates.length; bar < bars.length && bars[bar].first <= ocho.last; bar++) {
      const wide = Math.round((whole * (bars[bar].last - bars[bar].first + 1)) / BAR)
      plates.push({ x: end, y: EDGE + row * PITCH, wide, high: HIGH, row, ocho: n })
      rows[row].last = bar
      end += wide + INSIDE
    }
    end += BETWEEN - INSIDE
  })
  return { perRow, whole, plates, rows, height: EDGE + (rows.length - 1) * PITCH + HIGH + EDGE }
}

// The bar at a point of the canvas, or -1 where there is none. A row has the band from
// halfway to the row above to halfway to the row under. In it, a point between two plates
// belongs to the nearer one, the left one when both are as near. Left of the first plate
// of a row and right of its last there is no bar. With `nearest`, a point beside the bars
// gives the nearest row and the nearest bar in it: a drag may leave the rows.
export function barAt(layout, x, y, nearest = false) {
  if (layout.plates.length === 0) return -1
  let row = Math.floor((y - (EDGE - REACH)) / PITCH)
  if (nearest) row = Math.min(Math.max(row, 0), layout.rows.length - 1)
  else if (row < 0 || row >= layout.rows.length) return -1
  const { first, last } = layout.rows[row]
  const { plates } = layout
  const away = (bar) => Math.max(plates[bar].x - x, x - (plates[bar].x + plates[bar].wide), 0)
  if (!nearest && (x < plates[first].x || x >= plates[last].x + plates[last].wide)) return -1
  let closest = first
  for (let bar = first + 1; bar <= last; bar++) if (away(bar) < away(closest)) closest = bar
  return closest
}

// Where the row of a bar starts and ends, top to bottom.
export function rowOf(layout, bar) {
  const top = layout.plates[bar].y - REACH
  return { top, bottom: top + PITCH }
}

// One row's part of a marked range, over the bars `from` to `to`: a band of the sign's
// yellow while the playing goes round it, two dashed rules while it does not, and a
// bracket where the range starts and where it ends. The plates are drawn on it.
function loopRun(pen, layout, from, to, { opens, closes, on }, colours) {
  const { plates } = layout
  // The band stops short of the other plate of an ocho that the range cuts in two.
  const beyond = (bar, side) => (plates[bar + side]?.ocho === plates[bar].ocho ? BAND_INSIDE : BAND)
  const x = plates[from].x - beyond(from, -1)
  const width = plates[to].x + plates[to].wide + beyond(to, 1) - x
  const top = plates[from].y - BAND
  const tall = HIGH + 2 * BAND
  if (on) {
    pen.fillStyle = colours.loopFill
    pen.fillRect(x, top, width, tall)
  } else {
    pen.strokeStyle = colours.loop
    pen.lineWidth = 1.5
    pen.setLineDash([6, 5])
    pen.beginPath()
    pen.moveTo(x, top)
    pen.lineTo(x + width, top)
    pen.moveTo(x, top + tall)
    pen.lineTo(x + width, top + tall)
    pen.stroke()
    pen.setLineDash([])
  }
  pen.fillStyle = colours.loop
  if (opens) {
    pen.fillRect(x, top, 4, tall)
    pen.fillRect(x, top, 10, 4)
    pen.fillRect(x, top + tall - 4, 10, 4)
  }
  if (closes) {
    pen.fillRect(x + width - 4, top, 4, tall)
    pen.fillRect(x + width - 10, top, 10, 4)
    pen.fillRect(x + width - 10, top + tall - 4, 10, 4)
  }
}

// Figures with the middle of their ink, top to bottom, at `y`. The pen says where they
// are from left to right.
function written(pen, text, x, y) {
  const ink = pen.measureText(text)
  pen.fillText(text, x, y + (ink.actualBoundingBoxAscent - ink.actualBoundingBoxDescent) / 2)
}

// The count of a bar in the middle of a box, both ways.
const counted = (pen, text, { x, y, wide, high }) => written(pen, text, x + wide / 2, y + high / 2)

// The lid of a count 1 the user set, over a box: a strip a little above it and a little
// wider than it.
function lid(pen, { x, y, wide }, colour) {
  pen.fillStyle = colour
  pen.fillRect(x - 3, y - 7, wide + 6, 4)
}

// `beats` are the times of the beats, `bars` the bars, `count` the count of every beat
// and `byHand` the beats the user set to count 1. `lit` is the bar that holds the beat
// that is sounding and `hover` the bar under the pointer, each -1 when there is none.
// `range` is the marked range in bars, { first, last, on }, or null. `on` says whether
// the playing goes round it.
export function drawMap(canvas, layout, { beats, bars, count, byHand, lit, hover, range }) {
  const { pen } = sheetOf(canvas)
  const colours = tokens()
  const { plates, rows } = layout

  if (range) {
    // One run for every row the range touches.
    for (let row = plates[range.first].row; row <= plates[range.last].row; row++) {
      const from = Math.max(range.first, rows[row].first)
      const to = Math.min(range.last, rows[row].last)
      loopRun(pen, layout, from, to, { opens: from === range.first, closes: to === range.last, on: range.on }, colours)
    }
  }

  pen.textBaseline = 'alphabetic'
  pen.font = `500 12px ${colours.font}`
  pen.textAlign = 'right'
  pen.fillStyle = colours.label
  rows.forEach((row) => {
    written(pen, clock(beats[bars[row.first].first]), LEFT - 14, plates[row.first].y + HIGH / 2)
  })

  if (hover >= 0 && hover !== lit) {
    const { x, y, wide, high } = plates[hover]
    pen.fillStyle = colours.hover
    pen.fillRect(x - 4, y - 4, wide + 8, high + 8)
  }

  // A first bar and a second bar differ by their fill and by the count written on them.
  pen.textAlign = 'center'
  plates.forEach((plate, bar) => {
    if (bar === lit) return
    const beat = bars[bar].first
    const first = count[beat] <= BAR
    pen.fillStyle = first ? colours.mark : colours.plate
    pen.fillRect(plate.x, plate.y, plate.wide, plate.high)
    if (byHand.has(beat)) lid(pen, plate, colours.mark)
    if (plate.wide < WRITTEN) return
    pen.font = `${first ? 700 : 500} 15px ${colours.font}`
    pen.fillStyle = first ? colours.ground : colours.ink
    counted(pen, String(count[beat]), plate)
  })

  // The bar that is sounding: a block in place of its plate, over the edges of its
  // neighbours, and its lid over the block.
  if (lit >= 0) {
    const plate = plates[lit]
    const block = { x: plate.x - 5, y: plate.y - 6, wide: plate.wide + 10, high: plate.high + 12 }
    const beat = bars[lit].first
    pen.beginPath()
    pen.roundRect(block.x, block.y, block.wide, block.high, 2)
    pen.fillStyle = colours.lit
    pen.fill()
    if (byHand.has(beat)) lid(pen, block, colours.mark)
    pen.font = `700 17px ${colours.font}`
    pen.fillStyle = colours.litInk
    counted(pen, String(count[beat]), block)
  }
}
