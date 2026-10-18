import { atom, read, update } from 'claude-code'
import type { Register, Timer } from 'claude-code'

import type { Pipeline, Stage } from '../types'

const PANE = 'pipeline'
const REFRESH_MS = 5000
const SPIN_MS = 150
const FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
const STALE_MS = 30 * 60 * 1000
const pipeline = atom({ plugin: 'shipkit', key: 'pipeline' } as const, null as Pipeline)
const frame = atom({ plugin: 'shipkit', key: 'frame' } as const, 0)
// stages the person opened (true) or closed (false) by pressing them; a stage not in it follows its default (open when it is next or failed)
const open = atom({ plugin: 'shipkit', key: 'open' } as const, {} as Record<string, boolean>)

// what a pressable shows while the pointer is on it: one calm highlight (white on blue) instead of the host's inversion of
// dim or colored text; `scope` makes a Button and the Text inside it light together
const hov = (scope: string) => ({ scope, backgroundColor: '#2563eb', color: '#ffffff', bold: false, dimColor: false })

// glyph, label, color; a live `running` swaps its glyph for the spinner frame
const STATUS = {
  'waiting-user': ['⏸', 'waiting for you', 'warning'],
  running: ['●', 'running', 'success'],
  failed: ['✗', 'failed', 'error'],
  done: ['✓', 'done', 'success'],
} as const

// "- [x] 3 implement — ..." → done; a line with ❌ → failed; "  - detail: 3/5 tasks" under it → that stage's detail;
// "Flow: <label>" → the label as written; "Status: <running|waiting-user|failed|done> · <why>" and "Next: <action>" → shown as written;
// "Branch:", "PRs: <url> <url>", "Evidence: <path>" and "Poller: <text>" header lines → context rows (each optional)
export const parse = (md: string, mtimeMs = 0): Pipeline => {
  const ticket = /^# Pipeline state — (.+)$/m.exec(md)?.[1]
  if (!ticket) return null
  const stages: Stage[] = []
  for (const line of md.split('\n')) {
    const m = /^- \[( |x)\] (\S+)\s+(\S+)/.exec(line)
    if (m) stages.push({ id: m[2], name: m[3], state: line.includes('❌') ? 'failed' : m[1] === 'x' ? 'done' : 'todo' })
    const d = /^\s+- detail:\s*(.+)$/.exec(line)
    if (d && stages.length) stages[stages.length - 1].detail = d[1].trim()
  }
  const s = /^Status:\s*(waiting-user|running|failed|done)\b[ \t]*(?:·[ \t]*(.+))?$/m.exec(md)
  return {
    ticket,
    flow: /^Flow:\s*([^·\n]+?)\s*(?:·|$)/m.exec(md)?.[1] ?? null,
    status: s ? { state: s[1] as keyof typeof STATUS, text: s[2]?.trim() ?? '' } : null,
    next: /^Next:\s*(.+)$/m.exec(md)?.[1].trim() ?? null,
    branch: /(?:^|·\s*)Branch:\s*([^·\n]+?)\s*(?:·|$)/m.exec(md)?.[1] ?? null,
    prs: /^PRs:\s*(.+)$/m.exec(md)?.[1].split(/\s+/).filter(u => /^https?:\/\//.test(u)) ?? [],
    evidence: /^Evidence:\s*(.+)$/m.exec(md)?.[1].trim() ?? null,
    poller: /^Poller:\s*(.+)$/m.exec(md)?.[1].trim() ?? null,
    mtimeMs,
    stages,
  }
}

// "https://…/pull-requests/12" → "#12"; any other URL → its last path segment
export const prLabel = (url: string): string => {
  const n = /\/(?:pull-requests|pull|merge_requests)\/(\d+)/.exec(url)?.[1]
  return n ? `#${n}` : (url.split('/').filter(Boolean).pop() ?? url)
}

export const age = (ms: number): string => {
  const m = Math.floor(ms / 60000)
  return m < 1 ? 'just now' : m < 60 ? `${m}m ago` : `${Math.floor(m / 60)}h ago`
}

let ticker: Timer | null = null // a pane left open keeps up with a pipeline running in another session
let spinner: Timer | null = null // turns the `frame` atom while a live run is on screen

const stop = () => {
  ticker?.cancel()
  spinner?.cancel()
  ticker = spinner = null
}

// only while the pane is open (ticker set): start the spinner for a live run, stop it otherwise
const syncSpin = ($: any, live: boolean) => {
  if (live && ticker && !spinner) spinner = $.clock.every(SPIN_MS, () => update($, frame, (n: number) => n + 1))
  if (!live && spinner) {
    spinner.cancel()
    spinner = null
  }
}

// a run is live while it says `running` and its file was touched within STALE_MS; only a live run animates
export const isLive = (p: Pipeline, ageMs: number): boolean => p?.status?.state === 'running' && ageMs <= STALE_MS

// newest .shipkit/pipeline-<ticket>.md under the session cwd (failure notes excluded)
const refresh = async ($: any, withSpin = false) => {
  const files = (await $.fs.list('.shipkit').catch(() => []))
    .filter((f: any) => /^pipeline-(?!failure-).+\.md$/.test(f.name))
    .sort((a: any, b: any) => b.mtimeMs - a.mtimeMs)
  const md = files[0] ? await $.fs.read(`.shipkit/${files[0].name}`) : ''
  const p = parse(md, files[0]?.mtimeMs)
  await update($, pipeline, () => p)
  if (withSpin) syncSpin($, isLive(p, files[0] ? (await $.clock.now()) - files[0].mtimeMs : Infinity))
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'stages', description: 'Show the shipkit pipeline stages in a pane' })
    await refresh($)
    return next(e)
  })

  on('command.run', { command: 'stages' }, async $ => {
    ticker ??= $.clock.every(REFRESH_MS, () => refresh($, true))
    await refresh($, true)
    await $.ui.open({ id: PANE, title: 'Stages' })
    return { text: 'Stages pane opened.' }
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($, true)
    return next(e)
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) stop()
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    stop()
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Link, Text } = $.ui.resolve(e)
    const close = (
      <Button
        key="close"
        label="Close"
        role="dismiss"
        hover={hov('close')}
        onPress={() => {
          stop() // the plugin's own $.ui.close skips its own ui.close hook
          $.ui.close({ id: PANE })
        }}
      >
        <Text dimColor hover={hov('close')}>
          Close
        </Text>
      </Button>
    )
    const p = await read($, pipeline)
    if (!p)
      return (
        <Box flexDirection="column">
          <Text dimColor>No .shipkit/pipeline-*.md here. Run /run-pipeline &lt;ticket&gt;.</Text>
          {close}
        </Box>
      )
    const next = p.stages.find(s => s.state !== 'done')
    const ago = p.mtimeMs ? (await $.clock.now()) - p.mtimeMs : 0
    const live = isLive(p, ago)
    const overrides = await read($, open)
    const spun = FRAMES[(await read($, frame)) % FRAMES.length]
    const [glyph, label, color] = p.status ? STATUS[p.status.state] : [null, null, undefined]
    const badge = p.status ? `${live ? spun : glyph} ${label}` : null
    const stale = ago > STALE_MS && p.status?.state !== 'done' && next !== undefined
    return (
      <Box flexDirection="column">
        <Box>
          <Text weight="bold">
            {p.ticket}{' '}
          </Text>
          {p.flow && <Text dimColor>· {p.flow} </Text>}
          {badge && <Text color={color}>{badge} </Text>}
          {close}
        </Box>
        {p.status?.text ? <Text color={color}>{p.status.text}</Text> : null}
        {p.branch ? <Text dimColor>Branch: {p.branch}</Text> : null}
        {p.prs.length ? (
          <Text>
            PRs:{' '}
            {p.prs.map(u => (
              <Link href={u} label={prLabel(u)} />
            )).flatMap((l, i) => (i ? [' ', l] : [l]))}
          </Text>
        ) : null}
        {p.poller ? <Text dimColor>Poller: {p.poller}</Text> : null}
        {p.stages.map(s => {
          const mark = s.state === 'done' ? '✓' : s.state === 'failed' ? '✗' : s === next ? (live ? spun : '▸') : '·'
          const shown = overrides[s.id] ?? (s.state === 'failed' || s === next)
          const row = (
            <Text
              color={s.state === 'failed' ? 'red' : s.state === 'done' ? 'green' : undefined}
              dimColor={s.state === 'todo' && s !== next}
              hover={s.detail ? hov(`stage:${s.id}`) : undefined}
            >
              {mark} {s.id} {s.name}
              {s.detail ? (shown ? ' −' : ' +') : ''}
            </Text>
          )
          return (
            <Box flexDirection="column">
              {s.detail ? (
                <Button key={`stage:${s.id}`} plain hover={hov(`stage:${s.id}`)} onPress={() => update($, open, o => ({ ...o, [s.id]: !shown }))}>
                  {row}
                </Button>
              ) : (
                row
              )}
              {s.detail && shown ? <Text dimColor>    {s.detail}</Text> : null}
            </Box>
          )
        })}
        {p.next ? <Text>Next: {p.next}</Text> : null}
        {p.evidence ? (
          <Button key="evidence" plain hover={hov('evidence')} onPress={press => $.ui.copy({ text: p.evidence!, surface: press.surface })}>
            <Text dimColor hover={hov('evidence')}>
              Evidence: {p.evidence} (press to copy)
            </Text>
          </Button>
        ) : null}
        {p.mtimeMs ? (
          <Text color={stale ? 'warning' : undefined} dimColor={!stale}>
            updated {age(ago)}
            {stale ? ' — nothing has moved, is the run still alive?' : ''}
          </Text>
        ) : null}
      </Box>
    )
  })
}
