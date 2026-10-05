// The two drawings of a song: the beats around the playing position, large, and every
// beat of the song in rows. A beat is a small square. The one that is sounding gets the
// large square a sign keeps for its pictogram, in the opposite of its ground, with the
// small square inside it.

import { clock } from './song.js'

// The custom properties a drawing reads from :root, by the name it uses for each.
const READ = {
  bandMark: '--band-mark',
  bandLit: '--band-lit',
  bandLitInk: '--band-lit-ink',
  bandNow: '--band-now',
  mark: '--mark',
  lit: '--lit',
  litInk: '--lit-ink',
  hover: '--hover',
  loop: '--loop',
  loopFill: '--loop-fill',
  label: '--ink-soft',
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

// ---- The beats around the playing position

// Eight beats fit the window. The one that is sounding has three before it.
const SHOWN = 8
const BEFORE = 3.5

// Where the window puts things, for a canvas this wide.
export function nowLayout(width) {
  const step = width / SHOWN
  return { step, line: step * BEFORE }
}

// The place the squares pass: two arrowheads, one from the top and one from the bottom.
function nowLine(pen, x, height, size, colours) {
  const reach = Math.max(10, Math.min(18, (height - size * 1.4) / 2 - 6))
  pen.fillStyle = colours.bandNow
  for (const [edge, tip] of [[0, reach], [height, height - reach]]) {
    pen.beginPath()
    pen.moveTo(x - reach, edge)
    pen.lineTo(x + reach, edge)
    pen.lineTo(x, tip)
    pen.closePath()
    pen.fill()
  }
}

// `at` is the playing position among the beats: 3 on the fourth beat, 3.5 half way to
// the fifth. `lit` is the beat that is sounding, or -1, and `pulse` goes from 1 to 0
// after it started: the large square swells with it. A beat that has sounded is fainter.
export function drawNow(canvas, { count, at, lit, pulse }) {
  const { pen, width, height } = sheetOf(canvas)
  const colours = tokens()
  const { step, line } = nowLayout(width)
  const size = Math.min(step * 0.6, height * 0.4)
  nowLine(pen, line, height, size, colours)
  const first = Math.max(0, Math.floor(at - BEFORE - 1))
  const last = Math.min(count - 1, Math.ceil(at + SHOWN - BEFORE + 1))
  for (let beat = first; beat <= last; beat++) {
    const x = line + (beat - at) * step
    if (beat === lit) {
      const side = size * (1.22 + 0.14 * pulse)
      square(pen, x, height / 2, side, colours.bandLit, side * 0.09)
      square(pen, x, height / 2, size * 0.36, colours.bandLitInk)
    } else {
      pen.globalAlpha = beat < lit ? 0.28 : 1
      square(pen, x, height / 2, size * 0.36, colours.bandMark)
      pen.globalAlpha = 1
    }
  }
}

// ---- Every beat of the song

// The rows of a song of `count` beats on a canvas this wide. A row holds as many beats
// as fit, and where it breaks means nothing. The time of a row is written in the margin
// on its left. `seat` is how far down a row its marks are.
export function mapLayout(width, count) {
  const { beat: step, row } = tokens()
  const left = Math.ceil(72 / step) * step
  const perRow = Math.max(1, Math.floor((width - left - step) / step))
  const rows = Math.ceil(count / perRow)
  return { left, top: step, step, row, seat: row / 2, perRow, rows, count, height: 2 * step + rows * row }
}

// The top left corner of the cell of a beat.
const cellOf = (layout, beat) => ({
  x: layout.left + (beat % layout.perRow) * layout.step,
  y: layout.top + Math.floor(beat / layout.perRow) * layout.row,
})

// The beat at a point of the canvas, or -1 where there is none. With `nearest`, a point
// beside the beats gives the closest one: a drag may leave the rows.
export function beatAt(layout, x, y, nearest = false) {
  let column = Math.floor((x - layout.left) / layout.step)
  let row = Math.floor((y - layout.top) / layout.row)
  if (nearest) {
    column = Math.min(Math.max(column, 0), layout.perRow - 1)
    row = Math.min(Math.max(row, 0), layout.rows - 1)
  } else if (column < 0 || column >= layout.perRow || row < 0 || row >= layout.rows) {
    return -1
  }
  const beat = row * layout.perRow + column
  if (beat < layout.count) return beat
  return nearest ? layout.count - 1 : -1
}

// Where the row of a beat starts and ends, top to bottom.
export function rowOf(layout, beat) {
  const top = layout.top + Math.floor(beat / layout.perRow) * layout.row
  return { top, bottom: top + layout.row }
}

// One row's part of a marked range: a band of the sign's yellow while the playing goes
// round it, two dashed rules while it does not, and a black bar where the range starts
// and where it ends.
function loopRun(pen, x, y, width, layout, { opens, closes, on }, colours) {
  const top = y + 5
  const tall = layout.row - 10
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

// `range` is the marked range, { first, last, on }, or null. `on` says whether the
// playing goes round it.
export function drawMap(canvas, layout, { beats, lit, hover, range }) {
  const { pen } = sheetOf(canvas)
  const colours = tokens()

  if (range) {
    // One run for every row the range touches.
    const firstRow = Math.floor(range.first / layout.perRow)
    const lastRow = Math.floor(range.last / layout.perRow)
    for (let row = firstRow; row <= lastRow; row++) {
      const from = Math.max(range.first, row * layout.perRow)
      const to = Math.min(range.last, (row + 1) * layout.perRow - 1)
      const { x, y } = cellOf(layout, from)
      const ends = { opens: from === range.first, closes: to === range.last, on: range.on }
      loopRun(pen, x, y, (to - from + 1) * layout.step, layout, ends, colours)
    }
  }

  pen.font = `500 12px ${colours.font}`
  pen.textAlign = 'right'
  pen.textBaseline = 'middle'
  pen.fillStyle = colours.label
  for (let row = 0; row < layout.rows; row++) {
    const { y } = cellOf(layout, row * layout.perRow)
    pen.fillText(clock(beats[row * layout.perRow]), layout.left - 12, y + layout.seat + 0.5)
  }

  for (let beat = 0; beat < beats.length; beat++) {
    const cell = cellOf(layout, beat)
    const x = cell.x + layout.step / 2
    const y = cell.y + layout.seat
    if (beat === lit) {
      square(pen, x, y, 24, colours.lit, 2)
      square(pen, x, y, 8, colours.litInk)
    } else {
      if (beat === hover) square(pen, x, y, 22, colours.hover)
      square(pen, x, y, 8, colours.mark)
    }
  }
}
