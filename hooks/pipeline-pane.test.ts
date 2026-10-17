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

test('parse returns null for a file that is not a pipeline state', () => {
  expect(parse('nothing')).toBe(null)
})
