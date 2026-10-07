// The colours of the page, in light and in dark: text on its ground meets WCAG AA, and
// the marks a canvas draws stand out from what they are drawn on.

import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const here = new URL('.', import.meta.url)

// The custom properties the style sheet sets on :root, in the first block after `from`.
function propertiesOf(sheet, from) {
  const start = sheet.indexOf(':root {', from)
  assert.notEqual(start, -1)
  const block = sheet.slice(start, sheet.indexOf('}', start))
  return Object.fromEntries([...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((found) => [found[1], found[2].trim()]))
}

function luminance(colour) {
  assert.match(colour, /^#[0-9a-f]{6}$/, colour)
  const [red, green, blue] = [1, 3, 5].map((at) => {
    const part = parseInt(colour.slice(at, at + 2), 16) / 255
    return part <= 0.04045 ? part / 12.92 : ((part + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

function contrast(one, other) {
  const [dark, light] = [luminance(one), luminance(other)].sort((a, b) => a - b)
  return (light + 0.05) / (dark + 0.05)
}

// Text and what it is written on.
const TEXT = [
  ['--ink', '--ground'],
  ['--ink-soft', '--ground'],
  ['--panel-ink', '--panel'],
  ['--panel-soft', '--panel'],
  ['--panel-ink', '--panel-hover'],
  ['--panel-ink', '--panel-current'],
  ['--panel-soft', '--panel-current'],
  ['--refused', '--panel'],
  ['--refused', '--panel-current'],
  ['--accent-ink', '--accent'],
  ['--accent-ink', '--accent-hover'],
  ['--field-ink', '--field'],
  ['--band-ink', '--band'],
  ['--band-soft', '--band'],
  ['--band-mark', '--band'],
  // The count on the plate of a bar of the song, and on the block of the bar that is lit.
  // The plate of a second bar is a ground for its count, faint against the page on
  // purpose: it is not checked as a mark.
  ['--ground', '--mark'],
  ['--ink', '--plate'],
  ['--lit-ink', '--lit'],
]

// A mark, a rule or a focus ring and what it is drawn on.
const MARKS = [
  ['--focus', '--panel'],
  ['--seek-line', '--panel'],
  ['--accent', '--seek-line'],
  ['--panel-ink', '--panel'],
  ['--mark', '--ground'],
  ['--loop', '--ground'],
  ['--band-mark', '--band'],
  ['--band-sounded', '--band'],
  ['--band-lit-ink', '--band-lit'],
]

// The mark of the beat that is sounding stands out from its ground by its own colour, or
// by the colour of what is on it. The block of the bar that is sounding, by its own
// colour or by the colour of its edge.
const LIT = [
  ['--band-lit', '--band-lit-ink', '--band'],
  ['--lit', '--lit-edge', '--ground'],
]

// Light is what :root sets. Dark is what the block for a dark system sets over it.
const sheet = readFileSync(new URL('style.css', here), 'utf8')
const darkAt = sheet.indexOf('@media (prefers-color-scheme: dark)')
assert.notEqual(darkAt, -1)
const light = propertiesOf(sheet, 0)
const modes = { light, dark: { ...light, ...propertiesOf(sheet, darkAt) } }

for (const [mode, colours] of Object.entries(modes)) {
  test(`${mode}: text has a contrast of 4.5 to 1 or more`, () => {
    for (const [ink, ground] of TEXT) {
      const ratio = contrast(colours[ink], colours[ground])
      assert.ok(ratio >= 4.5, `${ink} ${colours[ink]} on ${ground} ${colours[ground]} is ${ratio.toFixed(2)}`)
    }
  })
  test(`${mode}: marks have a contrast of 3 to 1 or more`, () => {
    for (const [mark, ground] of MARKS) {
      const ratio = contrast(colours[mark], colours[ground])
      assert.ok(ratio >= 3, `${mark} ${colours[mark]} on ${ground} ${colours[ground]} is ${ratio.toFixed(2)}`)
    }
    for (const [fill, edge, ground] of LIT) {
      const ratios = [fill, edge].map((name) => contrast(colours[name], colours[ground]))
      assert.ok(Math.max(...ratios) >= 3, `${fill} on ${ground} is ${Math.max(...ratios).toFixed(2)}`)
    }
  })
}

test('light and dark are not the same colours', () => {
  assert.notEqual(modes.light['--ground'], modes.dark['--ground'])
})
