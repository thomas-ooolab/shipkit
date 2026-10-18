import { test, expect, mock } from 'claude-code/testing'

import { age, parse, prLabel } from './pipeline-pane'

const md = `# Pipeline state — AR-450
## Stages
- [x] 1 spec — /spec-from-ticket AR-450
- [ ] 3 implement — HUMAN GATE
- [ ] 4 review ❌ — x
`

test('parse reads ticket and stage states', () => {
  const p = parse(md)
  expect(p?.ticket).toBe('AR-450')
  expect(p?.stages.map(s => s.state)).toEqual(['done', 'todo', 'failed'])
})

test('parse reads the flow label as written, null when there is no Flow line', () => {
  expect(parse(md)?.flow).toBe(null)
  expect(parse(md.replace('## Stages', 'Flow: bug · Branch: fix/AR-450-x\n## Stages'))?.flow).toBe('bug')
  expect(parse(md.replace('## Stages', 'Flow: refactor, no spec\n## Stages'))?.flow).toBe('refactor, no spec')
})

test('parse reads Status, Next and a stage detail as written', () => {
  const p = parse(
    md.replace(
      '## Stages',
      'Status: waiting-user · 3 open questions block the plan\nNext: /clarify AR-450, then re-run\n## Stages',
    ).replace('- [ ] 3 implement — HUMAN GATE', '- [ ] 3 implement — HUMAN GATE\n  - detail: 3/5 tasks (be 3/3, fe 0/2)'),
    1000,
  )
  expect(p?.status).toEqual({ state: 'waiting-user', text: '3 open questions block the plan' })
  expect(p?.next).toBe('/clarify AR-450, then re-run')
  expect(p?.stages[1].detail).toBe('3/5 tasks (be 3/3, fe 0/2)')
  expect(p?.stages[0].detail).toBe(undefined)
  expect(p?.mtimeMs).toBe(1000)
})

test('parse leaves status and next null when the file has none; an unknown status is ignored', () => {
  expect(parse(md)?.status).toBe(null)
  expect(parse(md)?.next).toBe(null)
  expect(parse(md.replace('## Stages', 'Status: dancing · x\n## Stages'))?.status).toBe(null)
})

test('age words', () => {
  expect([age(10_000), age(5 * 60_000), age(3 * 3_600_000)]).toEqual(['just now', '5m ago', '3h ago'])
})

test('parse returns null for a file that is not a pipeline state', () => {
  expect(parse('nothing')).toBe(null)
})

test('Close button closes the pane on every surface that draws it', async ($, on) => {
  const closed: string[] = []
  on('ui.close', async ($, e) => (closed.push(e.id), { value: undefined }))
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'shipkit', surface, component: 'Pane', requestId: 'pipeline', props: {} })
    await ui.press({ key: 'close' })
    await ui.unmount()
  }
  expect(closed).toEqual(['pipeline', 'pipeline'])
})

// ---- drawing: a fake .shipkit dir answers the pane's fs reads, `/stages` makes it refresh, then the Pane is mounted and its Text read ----

const surfaces = ['terminal', 'desktop'] as const
const NOW = 10_000_000_000
const MIN = 60 * 1000

const full = md
  .replace('## Stages', 'Flow: bug · Branch: fix/AR-450-x\nStatus: waiting-user · 3 open questions block the plan\nNext: /clarify AR-450\n## Stages')
  .replace('- [ ] 3 implement — HUMAN GATE', '- [ ] 3 implement — HUMAN GATE\n  - detail: 3/5 tasks (be 3/3, fe 0/2)')

// `ageMs`: how long ago the file was last written (the pane's `updated … ago`); text null = no state file at all
const world = ($: any, on: any) => {
  let file: { text: string; mtimeMs: number } | null = null
  on('fs.list', async () => ({ value: file ? [{ name: 'pipeline-AR-450.md', kind: 'file', size: 1, mtimeMs: file.mtimeMs, isLink: false }] : [] }))
  on('fs.read', async () => ({ value: file?.text ?? '' }))
  on('ui.open', async () => ({ value: undefined }))
  const clock = mock.clock(on, { now: NOW })
  const draw = async (surface: (typeof surfaces)[number], text: string | null, ageMs = 0) => {
    file = text === null ? null : { text, mtimeMs: NOW - ageMs }
    await $.command.run({ command: 'stages', args: '' })
    return $.ui.mount({ plugin: 'shipkit', surface, component: 'Pane', requestId: 'pipeline', props: {} })
  }
  return Object.assign(draw, { clock })
}
const has = async (ui: any, text: RegExp) => (await ui.find({ type: 'Text', text })) !== undefined

test('the pane draws flow, status badge and reason, stage detail and Next on every surface', async ($, on) => {
  const draw = world($, on)
  for (const surface of surfaces) {
    const ui = await draw(surface, full)
    expect(await has(ui, /AR-450/)).toBe(true)
    expect(await has(ui, /bug/)).toBe(true)
    expect(await has(ui, /waiting for you/)).toBe(true)
    expect(await has(ui, /3 open questions block the plan/)).toBe(true)
    expect(await has(ui, /3\/5 tasks \(be 3\/3, fe 0\/2\)/)).toBe(true)
    expect(await has(ui, /Next: \/clarify AR-450/)).toBe(true)
    expect(await has(ui, /updated just now/)).toBe(true)
    await ui.unmount()
  }
})

test('a state file without Status, Next or detail draws none of those lines', async ($, on) => {
  const draw = world($, on)
  for (const surface of surfaces) {
    const ui = await draw(surface, md)
    expect(await has(ui, /AR-450/)).toBe(true)
    expect(await has(ui, /waiting for you|running|failed|done/)).toBe(false)
    expect(await has(ui, /Next:/)).toBe(false)
    await ui.unmount()
  }
})

test('each status draws its own badge', async ($, on) => {
  const draw = world($, on)
  const badges = { 'waiting-user': /⏸ waiting for you/, running: /⠋ running/, failed: /✗ failed/, done: /✓ done/ } // a fresh run spins: frame 0 is ⠋
  for (const [state, re] of Object.entries(badges)) {
    const ui = await draw('terminal', md.replace('## Stages', `Status: ${state} · why\n## Stages`))
    expect(await has(ui, re)).toBe(true)
    await ui.unmount()
  }
})

test('a pipeline untouched for over 30 minutes warns, unless it is done or every stage is complete', async ($, on) => {
  const draw = world($, on)
  const alive = /is the run still alive/
  const doneStatus = full.replace('Status: waiting-user · 3 open questions block the plan', 'Status: done · shipped')
  const allStages = full.replace(/- \[ \]/g, '- [x]').replace(' ❌', '')
  for (const surface of surfaces) {
    let ui = await draw(surface, full, 40 * MIN)
    expect(await has(ui, /updated 40m ago/)).toBe(true)
    expect(await has(ui, alive)).toBe(true)
    await ui.unmount()

    ui = await draw(surface, full, 5 * MIN)
    expect(await has(ui, /updated 5m ago/)).toBe(true)
    expect(await has(ui, alive)).toBe(false)
    await ui.unmount()

    ui = await draw(surface, doneStatus, 40 * MIN)
    expect(await has(ui, alive)).toBe(false)
    await ui.unmount()

    ui = await draw(surface, allStages, 40 * MIN)
    expect(await has(ui, alive)).toBe(false)
    await ui.unmount()
  }
})

test('no pipeline state draws the hint instead of stages', async ($, on) => {
  const draw = world($, on)
  for (const surface of surfaces) {
    const ui = await draw(surface, null)
    expect(await has(ui, /No \.shipkit\/pipeline-\*\.md here/)).toBe(true)
    expect(await has(ui, /AR-450/)).toBe(false)
    await ui.unmount()
  }
})

const running = md.replace('## Stages', 'Status: running · implementing\n## Stages')

test('a live run animates: the badge and the next-stage marker turn through the spinner frames as the clock moves', async ($, on) => {
  const draw = world($, on)
  const ui = await draw('terminal', running, 1 * MIN)
  expect(await has(ui, /⠋ running/)).toBe(true)
  expect(await has(ui, /⠋ 3 implement/)).toBe(true)
  await draw.clock.advance(150)
  expect(await has(ui, /⠙ running/)).toBe(true)
  expect(await has(ui, /⠙ 3 implement/)).toBe(true)
  await draw.clock.advance(150)
  expect(await has(ui, /⠹ running/)).toBe(true)
  await ui.unmount()
})

test('a run that is not live does not animate: stale, or waiting, failed or done', async ($, on) => {
  const draw = world($, on)
  const still = async (text: string, ageMs: number, badge: RegExp, marker: RegExp) => {
    const ui = await draw('terminal', text, ageMs)
    await draw.clock.advance(450)
    expect(await has(ui, badge)).toBe(true)
    expect(await has(ui, marker)).toBe(true)
    expect(await has(ui, /[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]/)).toBe(false)
    await ui.unmount()
  }
  await still(running, 40 * MIN, /● running/, /▸ 3 implement/)
  await still(full, 1 * MIN, /⏸ waiting for you/, /▸ 3 implement/)
  await still(md.replace('## Stages', 'Status: failed · x\n## Stages'), 1 * MIN, /✗ failed/, /▸ 3 implement/)
  await still(md.replace('## Stages', 'Status: done · x\n## Stages'), 1 * MIN, /✓ done/, /▸ 3 implement/)
})

test('closing the pane stops the animation: the frame stands still until the pane is opened again', async ($, on) => {
  const draw = world($, on)
  on('ui.close', async () => ({ value: undefined }))
  let ui = await draw('terminal', running, 1 * MIN)
  await draw.clock.advance(150)
  expect(await has(ui, /⠙ running/)).toBe(true)
  await ui.press({ key: 'close' })
  await ui.unmount()
  await draw.clock.advance(1350) // nine ticks: a spinner left running would be back at ⠋ now
  ui = await draw('terminal', running, 1 * MIN)
  expect(await has(ui, /⠙ running/)).toBe(true)
  await ui.unmount()
})

// ---- context rows and interaction ----

const rich = full
  .replace('## Stages', 'PRs: https://bitbucket.org/ws/api/pull-requests/12 https://bitbucket.org/ws/web/pull-requests/7\nEvidence: .shipkit/evidence/AR-450/\nPoller: waiting for the reporter (silent 2)\n## Stages')
  .replace('- [x] 1 spec — /spec-from-ticket AR-450', '- [x] 1 spec — /spec-from-ticket AR-450\n  - detail: 14 requirements')

test('parse reads Branch, PRs, Evidence and Poller; PR labels are short', () => {
  const p = parse(rich)
  expect(p?.branch).toBe('fix/AR-450-x')
  expect(p?.prs).toEqual(['https://bitbucket.org/ws/api/pull-requests/12', 'https://bitbucket.org/ws/web/pull-requests/7'])
  expect(p?.evidence).toBe('.shipkit/evidence/AR-450/')
  expect(p?.poller).toBe('waiting for the reporter (silent 2)')
  expect(parse(md)).toMatchObject({ branch: null, prs: [], evidence: null, poller: null })
  expect(parse(md.replace('## Stages', 'Branch: feat/AR-450-y\n## Stages'))?.branch).toBe('feat/AR-450-y')
  expect([prLabel('https://bitbucket.org/ws/api/pull-requests/12'), prLabel('https://github.com/o/r/pull/9'), prLabel('https://x.test/a/b')]).toEqual(['#12', '#9', 'b'])
})

test('the pane draws Branch, Poller, one link per PR and the Evidence row', async ($, on) => {
  const draw = world($, on)
  for (const surface of surfaces) {
    const ui = await draw(surface, rich)
    expect(await has(ui, /Branch: fix\/AR-450-x/)).toBe(true)
    expect(await has(ui, /Poller: waiting for the reporter \(silent 2\)/)).toBe(true)
    expect(await ui.find({ type: 'Link', text: /#12/ })).toBeDefined()
    expect(await ui.find({ type: 'Link', text: /#7/ })).toBeDefined()
    expect((await ui.find({ key: 'evidence' }))?.text).toMatch(/Evidence: \.shipkit\/evidence\/AR-450\//)
    expect(await has(ui, /PRs: #12 #7/)).toBe(true)
    await ui.unmount()
  }
})

test('pressing the Evidence row copies its path', async ($, on) => {
  const draw = world($, on)
  const copied: string[] = []
  on('ui.copy', async (_$, e) => (copied.push(e.text), { value: { isCopied: true } }))
  const ui = await draw('terminal', rich)
  await ui.press({ key: 'evidence' })
  expect(copied).toEqual(['.shipkit/evidence/AR-450/'])
  await ui.unmount()
})

test('a stage detail is open for the next and failed stage, closed otherwise, and a press toggles it', async ($, on) => {
  const draw = world($, on)
  for (const surface of surfaces) {
    const ui = await draw(surface, rich)
    expect(await has(ui, /3\/5 tasks/)).toBe(true) // next stage: open
    expect(await has(ui, /14 requirements/)).toBe(false) // done stage: closed
    await ui.press({ key: 'stage:1' })
    expect(await has(ui, /14 requirements/)).toBe(true)
    await ui.press({ key: 'stage:3' })
    expect(await has(ui, /3\/5 tasks/)).toBe(false)
    await ui.press({ key: 'stage:3' })
    expect(await has(ui, /3\/5 tasks/)).toBe(true)
    await ui.press({ key: 'stage:1' }) // the person's toggles outlive the pane: leave stage 1 as found for the next surface
    await ui.unmount()
  }
  const failed = rich.replace('- [ ] 4 review ❌ — x', '- [ ] 4 review ❌ — x\n  - detail: /review-changes exited 2, rerun it')
  const ui = await draw('terminal', failed)
  expect(await has(ui, /exited 2, rerun it/)).toBe(true) // failed stage: open though it is not the next one
  await ui.unmount()
})
