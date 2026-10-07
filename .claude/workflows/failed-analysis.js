export const meta = {
  name: 'failed-analysis',
  description: 'Build CONTRACT.md: the server and the page side by side in wt/server and wt/page, then one integrator on master',
  whenToUse: 'Once, for the task of CONTRACT.md at the base commit named in the script. Not for another task.',
  phases: [
    { title: 'Workers', detail: 'A, the server, then B, the page: two agents at once, each in its own work folder' },
    { title: 'Integrator', detail: 'the join, the merge into master, the flow, the whole run, the records, in 40 minutes by its own clock' },
  ],
}

// The commit of master that holds CONTRACT.md as the workers must build it. Both branches start here.
const BASE = '4390edfc2fdfcd1f6fdbdec7342ad26f87bee5c8'
const MAIN = '<repo>'
const MINUTES = 35
const INTEGRATOR_MINUTES = 40

const WORKERS = [
  {
    key: 'A',
    what: 'the server and the queue',
    folder: 'wt/server',
    branch: 'server',
    port: 8087,
    tmp: '/tmp/claude-1000/e2e-a',
    box: [
      'bachata/queue.py',
      'bachata/store.py',
      'bachata/server.py',
      'bachata/model.py',
      'bachata/queue_test.py',
      'bachata/store_test.py',
      'bachata/server_test.py',
    ],
    build: `What you build, all of it in CONTRACT.md: the queue keeps \`reason\` and \`seconds\` with a failure ("Stored"); a failed song is listed with \`failure\` and no other song gets the key ("Sent"); and the request \`DELETE /api/songs/<id>/result\` with its five answers ("The new request"), with the request added to the list in the header of bachata/server.py.
- ANALYSIS_VERSION stays 5. You do not touch bachata/analysis.py or bachata/fills.py.
- One test reads fixtures/failed_songs.json and does what "The example both sides test against" says of the server's test: every \`listed\`, in order, every \`again\`, and the list after each 204.
- Each of the four reasons has a test that fails when a failure of that kind gets another reason. A test of the reason \`model\` uses a path of its own in a temporary folder: the checkpoints in models/ are never moved, renamed or fetched.
- Your checks: \`.venv/bin/python -m pytest -q bachata/queue_test.py bachata/store_test.py bachata/server_test.py\`, started inside your folder. They run inside the sandbox. You start no browser, and you do not run the song checks (songs_test, entry_test, entry_pairs_test, fills_test).`,
  },
  {
    key: 'B',
    what: 'the page',
    folder: 'wt/page',
    branch: 'page',
    port: 8088,
    tmp: '/tmp/claude-1000/e2e-b',
    box: [
      'web/app.js',
      'web/song.js',
      'web/index.html',
      'web/style.css',
      'web/song.test.js',
      'web/contrast.test.js',
      'e2e/page_test.py',
    ],
    build: `What you build, all of it in CONTRACT.md under "What the page does with it": the failed row says for how long the analysis ran, one sentence for the reason in place of "To try again, delete the song and add the file again", and "Try again" in every failed row, which sends \`DELETE /api/songs/<id>/result\` and does what the section says on 204, 409, 404 and anything else. A \`reason\` the page does not know is read as \`other\`, and a \`seconds\` of null as not known.
- The server of your folder does not have the request or the \`failure\` key: worker A builds them elsewhere and you do not see that work. Your tests of the page answer \`/api/songs\` and the DELETE themselves, as the test \`test_the_list_says_how_long_an_analysis_has_run_and_what_to_do_when_it_failed\` in e2e/page_test.py already answers the list. That test asserts the old sentence: it is yours to change.
- One test answers the list with every \`listed\` of fixtures/failed_songs.json, in order, and does what "The example both sides test against" says of the page's test.
- What can be decided without a browser goes in web/song.js with a test in web/song.test.js. The page has no inline script, no inline style and no eval.
- The flow through the real server is the integrator's, not yours.
- Your checks, started inside your folder: \`node --test web/\`, which runs inside the sandbox; and your tests of e2e/page_test.py, named with -k, which need a browser. NEXT.md, "In the session's sandbox", says Chrome does not start inside the sandbox. Run them once outside it as that section describes, with \`TMPDIR=/tmp/claude-1000/e2e-b BACHATA_TEST_PORT=8088 .venv/bin/python -m pytest e2e/page_test.py -k <your tests>\`. If that command is refused, or the tests are skipped, they are "not run": say so, with the reason, and never report them as passed. You do not run the whole of e2e/page_test.py and you do not run the song checks.`,
  },
]

const CHECK = {
  type: 'object',
  properties: {
    command: { type: 'string', description: 'The command exactly as it was run, with the folder it was run in' },
    result: { type: 'string', enum: ['passed', 'failed', 'not run'] },
    passed: { type: 'integer' },
    failed: { type: 'integer' },
    skipped: { type: 'integer' },
    note: { type: 'string', description: 'Why tests were skipped, why it was not run, or what failed' },
  },
  required: ['command', 'result', 'note'],
}

const WORKER_RETURN = {
  type: 'object',
  properties: {
    status: {
      type: 'string',
      enum: ['done', 'stopped at the time limit', 'blocked'],
      description: 'done only when everything asked is built and every check that could run passes',
    },
    base_commit: { type: 'string', description: 'git rev-parse HEAD in the work folder, before the first change' },
    folder_was: {
      type: 'string',
      enum: ['made new', 'there and at the base', 'there with work, put back to the base'],
    },
    head_commit: { type: 'string', description: 'git rev-parse HEAD in the work folder at the end' },
    minutes_worked: { type: 'number' },
    changed_files: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          committed: { type: 'boolean' },
          in_box: { type: 'boolean' },
          why_outside: { type: 'string' },
        },
        required: ['path', 'committed', 'in_box'],
      },
    },
    executed_checks: { type: 'array', items: CHECK },
    open_assumptions: { type: 'array', items: { type: 'string' } },
    left_undone: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'status',
    'base_commit',
    'folder_was',
    'head_commit',
    'minutes_worked',
    'changed_files',
    'executed_checks',
    'open_assumptions',
    'left_undone',
  ],
}

const STEP = {
  type: 'object',
  properties: {
    result: { type: 'string', enum: ['passed', 'failed', 'not run'] },
    evidence: { type: 'string', description: 'The command and what it printed at the end, or why it was not run' },
  },
  required: ['result', 'evidence'],
}

const INTEGRATOR_RETURN = {
  type: 'object',
  properties: {
    join: {
      type: 'object',
      properties: {
        holds: { type: 'boolean' },
        conditions: {
          type: 'array',
          items: {
            type: 'object',
            properties: { condition: { type: 'string' }, holds: { type: 'boolean' }, evidence: { type: 'string' } },
            required: ['condition', 'holds', 'evidence'],
          },
        },
      },
      required: ['holds', 'conditions'],
    },
    merge: {
      type: 'object',
      properties: {
        result: { type: 'string', enum: ['merged', 'taken back', 'not done'] },
        commits: { type: 'array', items: { type: 'string' } },
        note: { type: 'string' },
      },
      required: ['result', 'commits', 'note'],
    },
    flow: STEP,
    whole_run: STEP,
    version_and_old_sentence: STEP,
    checks_seen_to_fail: STEP,
    records: { type: 'array', items: { type: 'string' }, description: 'Each record written, with its file' },
    contract_deleted: { type: 'boolean' },
    accepted: { type: 'boolean', description: 'true only when every step above passed and none is "not run"' },
    master_head: { type: 'string' },
    minutes_worked: { type: 'number' },
    changed_files: { type: 'array', items: { type: 'string' } },
    open_for_owner: { type: 'array', items: { type: 'string' } },
  },
  required: [
    'join',
    'merge',
    'flow',
    'whole_run',
    'version_and_old_sentence',
    'checks_seen_to_fail',
    'records',
    'contract_deleted',
    'accepted',
    'master_head',
    'minutes_worked',
    'changed_files',
    'open_for_owner',
  ],
}

function workerPrompt(w) {
  return `You are worker ${w.key} of the graph in CONTRACT.md: ${w.what}. Another worker builds the other side at the same time, in another folder. You do not talk to it and you do not read its folder: the contract is all you share.

The main folder is ${MAIN}. Your work folder is ${MAIN}/${w.folder}, on the branch \`${w.branch}\`. The base commit is ${BASE}.

## First: the clock and the folder

1. Run \`date +%s\` and keep the number. You have ${MINUTES} minutes of work from it. Run it again before every new step. When ${MINUTES} minutes have passed you stop where you are, commit what holds together, and return with the status "stopped at the time limit" and what is left undone. No single command of yours may run longer than 10 minutes.
2. Make sure your work folder is at the base, as CONTRACT.md says under "What the two workers share":
   - If ${w.folder} is not there: from the main folder, \`git worktree add -b ${w.branch} ${w.folder} ${BASE}\` (with \`-B\` if the branch is there without its folder). Then the links to the main folder: \`.venv\`, \`models\`, \`.playwright\`, and under fixtures/audio/ each of \`README.md\`, \`by-ear.json\`, \`dev\`, \`entries\`, \`entry-pairs.json\`. No copy of data/.
   - If it is there: \`git rev-parse HEAD\` and \`git status --short\` inside it. At the base with no work in it: go on. With work in it, committed or not, or on another commit: put it back with \`git reset --hard ${BASE}\` and \`git clean -fd\` inside it, make the links again if they went, and start over. Say which of the three it was.
   - Then \`git rev-parse HEAD\` inside it must print ${BASE}, \`git rev-parse --abbrev-ref HEAD\` must print ${w.branch}, and \`.venv/bin/python -c "import bachata; print(bachata.__file__)"\` must print a path inside your folder. If one of the three does not, stop and return "blocked" with what you saw. The hash you return as base_commit is the one that command printed, not the one written here.
3. From here on every command is run inside your work folder. Read CONTRACT.md there, whole, and fixtures/failed_songs.json. Read in NEXT.md "Rules that are easy to break" and "In the session's sandbox".

## Your box

You write these files and no other:
${w.box.map((path) => `- ${path}`).join('\n')}

${w.build}

## Rules, from "What the two workers share"

- You may commit, on \`${w.branch}\`, inside your folder, staging each file by its path: never \`git add -A\` or \`git add .\`. No checkout, merge, rebase or stash, no change to master or to the other branch, no \`git worktree\` command for another folder, nothing written in the main folder outside ${w.folder}.
- CONTRACT.md and fixtures/failed_songs.json are not changed. Where you find them wrong, short or impossible, you build to them as written or stop, and you say so under open assumptions.
- ACCEPTANCE.md, BRIEF.md, LOG.md and NEXT.md are the integrator's. So is the break-on-purpose skill.
- .venv, models/ and .playwright/ are read only. No \`uv run\`, \`uv sync\` or \`uv add\`; no change to pyproject.toml or uv.lock.
- The owner's library, data/ in the main folder, is neither read nor written. The program is never started without BACHATA_DATA set to a temporary folder.
- Your port is ${w.port} (\`BACHATA_TEST_PORT=${w.port}\`) and your folder for temporary files outside the sandbox is ${w.tmp}.
- You start no other agent and no workflow.
- Write code that reads like the code around it. Every claim you build gets a test that would fail without it.

## What you return

- base_commit and head_commit, folder_was, and minutes_worked.
- changed_files: every path that differs from the base on your branch (\`git diff --name-only ${BASE} HEAD\`) and every path you wrote and did not commit, each with whether it is in your box.
- executed_checks: each command as it was run, with the figures it printed at the end. A check that was skipped, refused or never started is "not run", with the reason. Nothing is reported as passed that you did not see pass.
- open_assumptions: everything you decided that CONTRACT.md does not say, and everything in it or in the example you found wrong.
- left_undone: what was asked and is not built, or built and not checked.
- status is "done" only when all of it is built and every check that could run passes.`
}

function integratorPrompt(returns) {
  return `You are the integrator of the graph in CONTRACT.md. You own acceptance. You work in the main folder, ${MAIN}, on \`master\`. The two workers have stopped. The base commit is ${BASE}.

First run \`date +%s\` and keep the number. You have ${INTEGRATOR_MINUTES} minutes of work from it. Run it again before every new step. When ${INTEGRATOR_MINUTES} minutes have passed you stop where you are, commit on master what holds together, and return: every step you did not reach is "not run", with "the time limit" as its reason, and \`accepted\` is false. The whole run alone takes about 16 minutes: do not start it with less than 20 left, and report it "not run" then.

Read CONTRACT.md whole, then in NEXT.md "Rules that are easy to break", "In the session's sandbox" and "Housekeeping". Do the steps in this order and stop where one says to stop. You start no other agent and no workflow.

What the workers returned is at the end of this message. It is what they said. Every condition below is read from git and from a run of your own, not from it.

## 1. The join

The five conditions of the JOIN box. Each is held or not, with what showed it:
- both workers returned;
- \`git merge-base master server\` and \`git merge-base master page\` are both ${BASE}, and master is still at ${BASE};
- no path is in both \`git diff --name-only ${BASE} server\` and \`git diff --name-only ${BASE} page\`, and both work folders have nothing uncommitted;
- \`git diff ${BASE} server -- CONTRACT.md fixtures/failed_songs.json\` and the same for \`page\` print nothing;
- each side's test of the example passes, run by you inside wt/server and inside wt/page.
Say also which changed paths are outside the worker's box in CONTRACT.md.
If one condition does not hold: stop here. Merge nothing, change nothing, and return with every later step "not run".

## 2. The merge

In the main folder: \`git merge --no-ff server\`, then \`git merge --no-ff page\`, each with a message in the manner of \`git log\`. A conflict means the join did not hold: \`git merge --abort\`, put master back where it was before your first merge only if that is your own merge commit of this run, and stop with the result "taken back". No work folder and no branch is removed, and nothing is pushed.

## 3. The flow through the real program and the real page

The one check neither worker could run, as "What the integrator accepts" describes it: a library made on disk in a temporary folder with one song whose result.json is a failure of this version and with a count 1 set by hand; the program started on it; the row says the reason; "Try again" is pressed; the real analysis runs; the song is ready, with the same id, the same place in the list and the same count 1. It is a test in e2e/page_test.py, written by you. It needs a browser, and so a command outside the sandbox: see step 4.

## 4. The whole run

\`TMPDIR=/tmp/claude-1000/e2e-i BACHATA_TEST_PORT=8089 .venv/bin/python -m pytest\`, from the main folder, as one command outside the sandbox, given the time it needs: about 16 minutes. NEXT.md says how the owner allows it. If the command is refused, or the sandbox stops it, or tests of the page are skipped: the whole run is "not run", with the reason, and so is every test of step 3 that did not run. "not run" is never written as passed, here or in any file. Then run what does run inside the sandbox and report that under its own command.
A failing test is repaired when the fault is where the two sides meet, and reported when it is not.

## 5. What else the contract gives you

- ANALYSIS_VERSION is 5, and the sentence "delete the song and add the file again" is in no file but the records.
- The open assumptions of both workers: settle what the contract or the code settles, and put the rest in open_for_owner, each in a sentence the owner can answer. You do not decide for the owner. The sentences of the four reasons are the owner's to word.
- Commit your own work on master, each file staged by its path. There is an untracked file under .claude/workflows/: leave it as it is.
- The checks seen to fail: you do not run the break-on-purpose skill and you break nothing on purpose. The owner asks for it after this workflow. Report the step as "not run", with that reason, and write it so in the records.
- The records: the items in ACCEPTANCE.md with the check behind each; the session in LOG.md with the six decisions of CONTRACT.md and the figures; NEXT.md rewritten, with the work folders wt/server and wt/page under "Housekeeping". An item whose check was not run is written \`[ ]\`, and says "not run".
- CONTRACT.md is deleted only when every step passed and none is "not run". The checks seen to fail are "not run", so CONTRACT.md stays and \`accepted\` is false: say in NEXT.md what is left before it can go.

## What you return

Every step with its result and what showed it, the commits of the merge, master's head at the end, every file you changed, the records you wrote, and what is open for the owner.

## What the workers returned

${JSON.stringify(returns, null, 2)}`
}

phase('Workers')
log(`Base ${BASE.slice(0, 7)}. Worker A, then worker B, side by side. No worker is started a second time.`)
// A barrier: the join needs both. The thunks start in this order, and two is the most that run at once.
const [a, b] = await parallel(
  WORKERS.map((w) => () =>
    agent(workerPrompt(w), { label: `worker ${w.key}: ${w.what}`, phase: 'Workers', schema: WORKER_RETURN }),
  ),
)
const returns = { A: a, B: b }

const stops = []
for (const w of WORKERS) {
  const r = returns[w.key]
  if (!r) stops.push(`worker ${w.key} returned nothing`)
  else if (r.base_commit !== BASE) stops.push(`worker ${w.key} started from ${r.base_commit}, not from the base`)
  else if (r.status !== 'done') stops.push(`worker ${w.key}: ${r.status}`)
}
if (stops.length) {
  for (const stop of stops) log(`Stopped: ${stop}`)
  log('No worker is tried again, and the integrator is not started. Nothing was merged.')
  return { base: BASE, stopped: stops, workers: returns, integrator: null }
}

// What a program can see in the two returns before anyone merges. The integrator reads git for the same.
const paths = (r) => r.changed_files.map((file) => file.path)
const inBoth = paths(a).filter((path) => paths(b).includes(path))
const outside = [...a.changed_files, ...b.changed_files].filter((file) => !file.in_box).map((file) => file.path)
const notRun = [...a.executed_checks, ...b.executed_checks].filter((check) => check.result !== 'passed')
if (inBoth.length) log(`In both lists: ${inBoth.join(', ')}`)
if (outside.length) log(`Outside its worker's box: ${outside.join(', ')}`)
if (notRun.length) log(`${notRun.length} check(s) of the workers failed or were not run`)

phase('Integrator')
const integrator = await agent(integratorPrompt(returns), {
  label: 'integrator: join, merge, flow, whole run, records',
  phase: 'Integrator',
  schema: INTEGRATOR_RETURN,
})
if (!integrator) log('The integrator returned nothing. It is not started a second time: look at master before anything else.')

return { base: BASE, stopped: [], in_both: inBoth, outside_box: outside, workers: returns, integrator }
