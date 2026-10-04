import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'

// The page is read once at startup. A request never becomes a file path.
const page = await readFile(new URL('./web/index.html', import.meta.url))

const securityHeaders = {
  'Content-Security-Policy':
    "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
}

// Listens on the loopback interface only, so other machines cannot reach it.
export function start(port) {
  const server = createServer((req, res) => {
    if (req.method === 'GET' && req.url === '/') {
      res.writeHead(200, { ...securityHeaders, 'Content-Type': 'text/html; charset=utf-8' })
      res.end(page)
    } else {
      res.writeHead(404, { ...securityHeaders, 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('Not found\n')
    }
  })
  return new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(port, '127.0.0.1', () => resolve(server))
  })
}

if (import.meta.main) {
  const server = await start(Number(process.env.PORT ?? 8080))
  console.log(`Bachata sections: http://127.0.0.1:${server.address().port}`)
}
