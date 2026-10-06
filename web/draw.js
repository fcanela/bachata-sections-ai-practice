// The two drawings of a song: the ocho that is sounding, large, and every beat of the
// song in rows of four ochos. A beat is a small square with its count under it. Count 1
// is an upright bar, and a count 1 the user set has a cap across its top. The beat that
// is sounding gets the large square a sign keeps for its pictogram, in the opposite of
// its ground, with its own mark inside it.

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
  font: '--font',
  beat: '--beat',
  row: '--row',
}

let read = null

// What the style sheet sets: colours as text, and the two sizes of the rows as numbers.
export function tokens() {
  if (!read) {
    const style = getComputedStyle(document.documentElement)
    read = Object.fromEntries(Object.entries(READ).map(([name, property]) => [name, style.getPropertyValue(property).trim()]))
    read.beat = parseFloat(read.beat)
    read.row = parseFloat(read.row)
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

// ---- Every beat of the song

// Marks are never closer than this, in pixels. A row holds four ochos when they fit with
// that, and two or one when they do not.
const CLOSEST = 20
// The room on the left of a row for its time, on its right, and between two ochos.
const LEFT = 80
const RIGHT = 16
const GAP = 12

// The rows of a song on a canvas this wide. `ochos` are its ochos, each { first, last }.
// An ocho of fewer than eight beats takes less room, so the ochos after it in its row
// stand further left, and the next row starts in line again. `x` is the left edge of the
// cell of every beat and `line` the row it is in. `seat` is how far down a row its
// marks are.
export function mapLayout(width, ochos) {
  const { beat: widest, row } = tokens()
  let perRow, step
  for (perRow of [4, 2, 1]) {
    step = Math.min(widest, Math.floor((width - LEFT - RIGHT - (perRow - 1) * GAP) / (perRow * OCHO)))
    if (step >= CLOSEST) break
  }
  step = Math.max(step, 10)
  const x = []
  const line = []
  const rows = []
  ochos.forEach((ocho, n) => {
    if (n % perRow === 0) rows.push({ first: ocho.first, last: ocho.last, end: LEFT })
    const at = rows[rows.length - 1]
    for (let beat = ocho.first; beat <= ocho.last; beat++) {
      x.push(at.end + (beat - ocho.first) * step)
      line.push(rows.length - 1)
    }
    at.last = ocho.last
    at.end += (ocho.last - ocho.first + 1) * step + GAP
  })
  const top = 12
  return { left: LEFT, top, step, row, seat: 16, perRow, rows, count: x.length, x, line, height: 2 * top + rows.length * row }
}

// The middle of the mark of a beat.
export const markOf = (layout, beat) => ({
  x: layout.x[beat] + layout.step / 2,
  y: layout.top + layout.line[beat] * layout.row + layout.seat,
})

// The beat at a point of the canvas, or -1 where there is none. With `nearest`, a point
// beside the beats gives the closest one: a drag may leave the rows.
export function beatAt(layout, x, y, nearest = false) {
  if (layout.count === 0) return -1
  let row = Math.floor((y - layout.top) / layout.row)
  if (nearest) row = Math.min(Math.max(row, 0), layout.rows.length - 1)
  else if (row < 0 || row >= layout.rows.length) return -1
  const { first, last } = layout.rows[row]
  let closest = first
  for (let beat = first; beat <= last; beat++) {
    if (x >= layout.x[beat] && x < layout.x[beat] + layout.step) return beat
    if (Math.abs(x - markOf(layout, beat).x) < Math.abs(x - markOf(layout, closest).x)) closest = beat
  }
  return nearest ? closest : -1
}

// Where the row of a beat starts and ends, top to bottom.
export function rowOf(layout, beat) {
  const top = layout.top + layout.line[beat] * layout.row
  return { top, bottom: top + layout.row }
}

// One row's part of a marked range: a band of the sign's yellow while the playing goes
// round it, two dashed rules while it does not, and a black bar where the range starts
// and where it ends.
function loopRun(pen, x, y, width, layout, { opens, closes, on }, colours) {
  const top = y + 3
  const tall = layout.row - 6
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
    pen.fillRect(x, top, 9, 4)
    pen.fillRect(x, top + tall - 4, 9, 4)
  }
  if (closes) {
    pen.fillRect(x + width - 4, top, 4, tall)
    pen.fillRect(x + width - 9, top, 9, 4)
    pen.fillRect(x + width - 9, top + tall - 4, 9, 4)
  }
}

// `count` is the count of every beat and `byHand` the beats the user set to count 1.
// `range` is the marked range, { first, last, on }, or null. `on` says whether the
// playing goes round it.
export function drawMap(canvas, layout, { beats, count, byHand, lit, hover, range }) {
  const { pen } = sheetOf(canvas)
  const colours = tokens()

  if (range) {
    // One run for every row the range touches.
    for (let row = layout.line[range.first]; row <= layout.line[range.last]; row++) {
      const from = Math.max(range.first, layout.rows[row].first)
      const to = Math.min(range.last, layout.rows[row].last)
      const y = layout.top + row * layout.row
      const ends = { opens: from === range.first, closes: to === range.last, on: range.on }
      loopRun(pen, layout.x[from], y, layout.x[to] + layout.step - layout.x[from], layout, ends, colours)
    }
  }

  pen.textBaseline = 'middle'
  pen.font = `500 12px ${colours.font}`
  pen.textAlign = 'right'
  pen.fillStyle = colours.label
  layout.rows.forEach((row, n) => {
    pen.fillText(clock(beats[row.first]), layout.left - 14, layout.top + n * layout.row + layout.seat + 0.5)
  })

  pen.textAlign = 'center'
  const litSide = Math.min(26, layout.step - 2)
  for (let beat = 0; beat < layout.count; beat++) {
    const { x, y } = markOf(layout, beat)
    const first = count[beat] === 1
    if (beat === lit) {
      square(pen, x, y, litSide, colours.lit, 2)
      mark(pen, x, y, 8, colours.litInk, first, byHand.has(beat))
    } else {
      if (beat === hover) square(pen, x, y, litSide - 2, colours.hover)
      mark(pen, x, y, 8, colours.mark, first, byHand.has(beat))
    }
    pen.font = `${first ? 700 : 500} 12px ${colours.font}`
    pen.fillStyle = first ? colours.ink : colours.label
    pen.fillText(String(count[beat]), x, y + 21.5)
  }
}
