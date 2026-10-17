import { test, expect } from 'claude-code/testing'

import { parse } from './pipeline-pane'

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
