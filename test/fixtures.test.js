import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { problems } from '../fixtures/validate.js'

const fixtures = new URL('../fixtures/', import.meta.url)
const read = async (path) => JSON.parse(await readFile(new URL(path, fixtures), 'utf8'))

test('the template and every label file follow the fixture format', async () => {
  const template = await read('template.json')
  assert.deepEqual(problems(template), [], 'template.json')

  for (const name of await readdir(new URL('labels/', fixtures))) {
    if (name.endsWith('.json')) assert.deepEqual(problems(await read(`labels/${name}`)), [], name)
  }

  // The check above means nothing if the validator accepts anything. Dropping the
  // intro from the template leaves the first 8 seconds without a label.
  const withGap = { ...template, sections: template.sections.slice(1) }
  assert.deepEqual(problems(withGap), ['sections[0]: 0 s to 8 s has no label, add an "other" section'])
})
