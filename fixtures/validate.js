// Reference fixtures: the sections of a song, taken from the reference material.
//
//   fixtures/labels/<slug>.json   one file per song, committed
//   fixtures/audio/<file>         the recording those labels describe, never committed
//   fixtures/template.json        a made-up example of the format, not a song
//
// The format, which problems() checks:
// - Times are seconds from the start of the audio file. Labels only hold for that exact
//   recording, so the file's sha256 and duration are part of the fixture.
// - start_s is the time of the section's first beat, end_s the time of its last beat.
// - type is derecho, majao, mambo or other. `other` is any part of the song that is
//   none of the three: an intro, a break, another rhythm.
// - Sections are in order, do not overlap and cover the whole song. Wherever the
//   reference does not say derecho, majao or mambo it says `other`, which is what lets
//   a check tell an invented section from a part nobody labelled.

const TYPES = ['derecho', 'majao', 'mambo', 'other']

// A section ends on its last beat and the next one starts on the following beat, so
// neighbours are one beat apart. A longer gap means part of the song has no label.
const MAX_GAP_S = 1

// Returns what is wrong with a fixture, one line per problem. Empty when it is valid.
export function problems(fixture) {
  const found = []
  const text = (value) => typeof value === 'string' && value.trim() !== ''

  if (!text(fixture.title)) found.push('title: missing')
  if (!text(fixture.artist)) found.push('artist: missing')
  if (!text(fixture.source)) found.push('source: missing, say where the labels came from')

  const audio = fixture.audio ?? {}
  if (!/^[^/\\]+$/.test(audio.file ?? '')) {
    found.push('audio.file: must be the name of a file in fixtures/audio/')
  }
  if (!/^[0-9a-f]{64}$/.test(audio.sha256 ?? '')) {
    found.push('audio.sha256: must be 64 lowercase hex characters')
  }
  if (!(Number.isFinite(audio.duration_s) && audio.duration_s > 0)) {
    found.push('audio.duration_s: must be a positive number of seconds')
    return found
  }

  const sections = Array.isArray(fixture.sections) ? fixture.sections : []
  if (sections.length === 0) {
    found.push('sections: must be a non-empty list')
    return found
  }

  let covered = 0
  sections.forEach((section, i) => {
    const at = `sections[${i}]`
    if (!TYPES.includes(section.type)) found.push(`${at}.type: must be one of ${TYPES.join(', ')}`)
    if (!Number.isFinite(section.start_s) || !Number.isFinite(section.end_s)) {
      found.push(`${at}: start_s and end_s must be numbers`)
      return
    }
    if (section.start_s >= section.end_s) found.push(`${at}: start_s must be before end_s`)
    if (section.start_s < covered) found.push(`${at}: starts before the previous section ends`)
    if (section.start_s - covered > MAX_GAP_S) {
      found.push(`${at}: ${covered} s to ${section.start_s} s has no label, add an "other" section`)
    }
    covered = Math.max(covered, section.end_s)
  })
  if (covered > audio.duration_s) found.push('sections: end after the audio does')
  if (audio.duration_s - covered > MAX_GAP_S) {
    found.push(`sections: ${covered} s to the end has no label, add an "other" section`)
  }
  return found
}
