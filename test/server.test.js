import test from 'node:test'
import assert from 'node:assert/strict'
import { start } from '../server.js'

test('the program serves its page on localhost, with security headers, and nothing else', async (t) => {
  const server = await start(0)
  t.after(() => server.close())
  const { address, port } = server.address()
  assert.equal(address, '127.0.0.1')

  const page = await fetch(`http://127.0.0.1:${port}/`)
  assert.equal(page.status, 200)
  assert.equal(page.headers.get('content-type'), 'text/html; charset=utf-8')
  assert.match(page.headers.get('content-security-policy'), /default-src 'self'/)
  assert.equal(page.headers.get('x-content-type-options'), 'nosniff')
  assert.match(await page.text(), /<title>Bachata sections<\/title>/)

  const other = await fetch(`http://127.0.0.1:${port}/server.js`)
  assert.equal(other.status, 404)
  assert.equal(await other.text(), 'Not found\n')
})
