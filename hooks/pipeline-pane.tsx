import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Pipeline, Stage } from '../types'

const PANE = 'pipeline'
const pipeline = atom({ plugin: 'shipkit', key: 'pipeline' } as const, null as Pipeline)

// "- [x] 3 implement — ..." → done; a line with ❌ → failed
export const parse = (md: string): Pipeline => {
  const ticket = /^# Pipeline state — (.+)$/m.exec(md)?.[1]
  if (!ticket) return null
  const stages: Stage[] = []
  for (const line of md.split('\n')) {
    const m = /^- \[( |x)\] (\S+)\s+(\S+)/.exec(line)
    if (m) stages.push({ id: m[2], name: m[3], state: line.includes('❌') ? 'failed' : m[1] === 'x' ? 'done' : 'todo' })
  }
  return { ticket, stages }
}

// newest .shipkit/pipeline-<ticket>.md under the session cwd (failure notes excluded)
const refresh = async ($: any) => {
  const files = (await $.fs.list('.shipkit').catch(() => []))
    .filter((f: any) => /^pipeline-(?!failure-).+\.md$/.test(f.name))
    .sort((a: any, b: any) => b.mtimeMs - a.mtimeMs)
  const md = files[0] ? await $.fs.read(`.shipkit/${files[0].name}`) : ''
  await update($, pipeline, () => parse(md))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'pipeline', description: 'Show the shipkit pipeline stages in a pane' })
    await refresh($)
    return next(e)
  })

  on('command.run', { command: 'pipeline' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Pipeline' })
    return { text: 'Pipeline pane opened.' }
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const p = await read($, pipeline)
    if (!p) return <Text dimColor>No .shipkit/pipeline-*.md here. Run /run-pipeline &lt;ticket&gt;.</Text>
    const next = p.stages.find(s => s.state !== 'done')
    return (
      <Box flexDirection="column">
        <Text weight="bold">{p.ticket}</Text>
        {p.stages.map(s => (
          <Text
            color={s.state === 'failed' ? 'red' : s.state === 'done' ? 'green' : undefined}
            dimColor={s.state === 'todo' && s !== next}
          >
            {s.state === 'done' ? '✓' : s.state === 'failed' ? '✗' : s === next ? '▸' : '·'} {s.id} {s.name}
          </Text>
        ))}
      </Box>
    )
  })
}
