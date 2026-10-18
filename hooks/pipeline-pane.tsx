import { atom, read, update } from 'claude-code'
import type { Register, Timer } from 'claude-code'

import type { Pipeline, Pr, Stage, Wait } from '../types'

const PANE = 'pipeline'
const REFRESH_MS = 5000
const SPIN_MS = 150
const FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
const STALE_MS = 30 * 60 * 1000
const pipeline = atom({ plugin: 'shipkit', key: 'pipeline' } as const, null as Pipeline)
const frame = atom({ plugin: 'shipkit', key: 'frame' } as const, 0)
// stages the person opened (true) or closed (false) by pressing them, keyed `<ticket>:<stage id>` (stage ids repeat across tickets); a stage not in it follows its default (open when it is next or failed)
const open = atom({ plugin: 'shipkit', key: 'open' } as const, {} as Record<string, boolean>)
// when the person last pressed a ping, by `<ticket>:<kind>`: the button rests for PING_REST_MS afterwards instead of inviting a second nudge
const pinged = atom({ plugin: 'shipkit', key: 'pinged' } as const, {} as Record<string, number>)
const PING_REST_MS = 60 * 60 * 1000
const NEXT_REST_MS = 10 * 60 * 1000 // after `[ ok ]` on Next:, so the same step is not sent twice

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

// "- [x] 3 implement — ..." → done; a line with ❌ → failed; each "  - detail: 3/5 tasks" line under it → one line of that stage's details;
// "Flow: <label>" → the label as written; "Status: <running|waiting-user|failed|done> · <why>" and "Next: <action>" → shown as written;
// "Spec: <dir>" → where open-question.md is; each "Blocker: [<stage id>: ]<text>" line → one declared blocker;
// "PRs: <label>=<url> <label>=<url>" (a bare <url> is labelled with its repo), "Evidence: <path>" and each "Poller: <text>" header line
// → context rows (each optional)
export const parse = (md: string, mtimeMs = 0): Pipeline => {
  const ticket = /^# Pipeline state — (.+)$/m.exec(md)?.[1]
  if (!ticket) return null
  const stages: Stage[] = []
  for (const line of md.split('\n')) {
    const m = /^- \[( |x)\] (\S+)\s+(\S+)/.exec(line)
    if (m) stages.push({ id: m[2], name: m[3], state: line.includes('❌') ? 'failed' : m[1] === 'x' ? 'done' : 'todo', details: [] })
    const d = /^\s+- detail:\s*(.+)$/.exec(line)
    if (d && stages.length) stages[stages.length - 1].details.push(d[1].trim())
  }
  const s = /^Status:\s*(waiting-user|running|failed|done)\b[ \t]*(?:·[ \t]*(.+))?$/m.exec(md)
  return {
    ticket,
    flow: /^Flow:\s*([^·\n]+?)\s*(?:·|$)/m.exec(md)?.[1] ?? null,
    status: s ? { state: s[1] as keyof typeof STATUS, text: s[2]?.trim() ?? '' } : null,
    next: /^Next:\s*(.+)$/m.exec(md)?.[1].trim() ?? null,
    spec: /(?:^|·\s*)Spec:\s*([^·\n]+?)\s*(?:·|$)/m.exec(md)?.[1] ?? null,
    blockers: [...md.matchAll(/^Blocker:\s*(.+)$/gm)].map(m => m[1].trim()),
    oq: null,
    clarify: null,
    concerns: [],
    bug: null,
    prLoop: null,
    prs: /^PRs:\s*(.+)$/m.exec(md)?.[1].split(/\s+/).flatMap(parsePr) ?? [],
    evidence: /^Evidence:\s*(.+)$/m.exec(md)?.[1].trim() ?? null,
    evidenceFile: null,
    pollers: [...md.matchAll(/^Poller:\s*(.+)$/gm)].map(m => m[1].trim()),
    waiting: [],
    mtimeMs,
    stages,
  }
}

// "root=https://…" → { label: 'root', url }; a bare "https://…" → { label: <its repo, when the URL names one>, url }; anything else is dropped
export const parsePr = (tok: string): Pr[] => {
  const m = /^(?:([^=\s]+)=)?(https?:\/\/\S+)$/.exec(tok)
  return m ? [{ label: m[1] ?? repoOf(m[2]) ?? null, url: m[2] }] : []
}

// Bitbucket ".../<workspace>/<repo>/pull-requests/12", GitHub/GitLab ".../<owner>/<repo>/pull/9" → the repo
export const repoOf = (url: string): string | undefined =>
  /\/([^/]+)\/(?:-\/)?(?:pull-requests|pull|merge_requests)\/\d+/.exec(url)?.[1]

// "https://…/pull-requests/12" → "#12"; any other URL → its last path segment
export const prLabel = (url: string): string => {
  const n = /\/(?:pull-requests|pull|merge_requests)\/(\d+)/.exec(url)?.[1]
  return n ? `#${n}` : (url.split('/').filter(Boolean).pop() ?? url)
}

// the open "- [ ] …" items of a markdown checklist; `section` ("## Concerns") limits it to the lines under that heading
export const openItems = (md: string, section?: string): string[] => {
  let inside = !section
  const out: string[] = []
  for (const line of md.split('\n')) {
    if (/^##\s/.test(line)) inside = !section || line.trim() === section || line.startsWith(`${section} `)
    const m = inside ? /^- \[ \]\s*(.+)$/.exec(line) : null
    if (m) out.push(m[1].trim())
  }
  return out
}

// the stage a declared blocker belongs to: the one its text names ("4: reviewer unreachable", "4 — …"), else the next unfinished stage
export const blockerStage = (text: string, stages: Stage[]): string | undefined => {
  const id = /^(\S+?)\s*[:—]\s+/.exec(text)?.[1]
  return stages.find(s => s.id === id)?.id ?? stages.find(s => s.state !== 'done')?.id
}

// how many items a checklist has, and how many of them are still open ("- [ ]")
export const countItems = (md: string): { open: number; total: number } => {
  const marks = [...md.matchAll(/^- \[( |x)\]/gm)]
  return { open: marks.filter(m => m[1] === ' ').length, total: marks.length }
}

// a `key:` line of a state file holds something: not empty, not `null`, or an indented block follows it
const isSet = (md: string, key: string): boolean => {
  const v = new RegExp(`^${key}:[ \\t]*(.*)$`, 'm').exec(md)?.[1].trim() ?? ''
  return (v !== '' && v !== 'null') || new RegExp(`^${key}:[ \\t]*\\n[ \\t]+\\S`, 'm').test(md)
}

// /clarify's state file: `pending_comment` set = a drafted question is waiting for the user's go-ahead; `silent_ticks` = poll windows with no reply
export const parseClarify = (md: string): { pending: boolean; silent: number; rounds: number } => ({
  pending: isSet(md, 'pending_comment'),
  silent: Number(/^silent_ticks:[ \t]*(\d+)/m.exec(md)?.[1] ?? 0),
  rounds: Number(/^follow_up_rounds:[ \t]*(\d+)/m.exec(md)?.[1] ?? 0),
})

// /bugfix's state file: the concerns still unchecked, and the poll windows the reporter has stayed silent
export const parseBugfix = (md: string): { open: number; silent: number; pending: boolean } => ({
  open: openItems(md, '## Concerns').length,
  pending: isSet(md, 'pending_comment'),
  silent: Number(/^silent_ticks:[ \t]*(\d+)/m.exec(md)?.[1] ?? 0),
})

// /pr's state file: how many PRs have no `lgtm@<sha>` yet (`pending` or `changes`), of how many, the Slack round and the silence
export const parsePrLoop = (md: string): { waiting: number; total: number; round: number; silent: number; pending: boolean } => {
  const states = [...md.matchAll(/^- .+? — (.+)$/gm)].filter(m => md.indexOf(m[0]) > md.indexOf('## PR approvals') && md.indexOf('## PR approvals') >= 0).map(m => m[1].trim())
  return {
    waiting: states.filter(st => !/^lgtm@/.test(st)).length,
    total: states.length,
    round: Number(/^round:[ \t]*(\d+)/m.exec(md)?.[1] ?? 0),
    silent: Number(/^silent_ticks:[ \t]*(\d+)/m.exec(md)?.[1] ?? 0),
    pending: isSet(md, 'pending_action'),
  }
}

// A ping is offered only when it is a sensible next step, and its message says what the situation is:
//  · nothing to ping while a drafted message already waits for the user (a second draft would pile up);
//  · nothing yet while no poll window has passed since the last ask/reply (`silent_ticks` is 0: it resets on every new comment);
//  · the follow-up round cap and a long silence change what the agent is asked to write.
// The text is built only from numbers read from the state files and the ticket key; the agent reads the people and dates itself, drafts, and
// the user confirms before anything is posted.
const windows = (n: number): string => `${n} poll window${n > 1 ? 's' : ''} (24 h each by default)`

// the waits the plugin's skills run, as lines for the pane — only while that loop still has something to wait for:
// /clarify and /bugfix poll Jira (wait-for-jira-comment.sh), /pr polls Slack for the reviewer's verdict (wait-for-slack-reply.sh --until verdict)
export const waitingOn = (a: {
  ticket: string
  oq: { open: number; total: number } | null
  clarify: { silent: number; pending: boolean; rounds: number } | null
  bug: { open: number; silent: number; pending: boolean } | null
  pr: { waiting: number; total: number; round: number; silent: number; pending: boolean } | null
}): Wait[] => {
  const s = (n: number) => (n > 1 ? 's' : '')
  const quiet = (n: number) => (n ? `silent ${n}` : '')
  const parts = (...xs: string[]) => (xs.filter(Boolean).length ? ` (${xs.filter(Boolean).join(', ')})` : '')
  const rule = 'Follow references/jira-comment-rules.md and show me the draft for confirmation before you post it.'
  const gate = (pending: boolean, silent: number, ping: () => string): Pick<Wait, 'ping' | 'hold'> =>
    pending ? { ping: null, hold: 'confirm the drafted message first' } : silent < 1 ? { ping: null, hold: 'too soon: no poll window has passed' } : { ping: ping(), hold: null }
  const out: Wait[] = []
  if (a.clarify && (a.oq?.open ?? 0) > 0) {
    const { open, total } = a.oq!
    const { silent, rounds } = a.clarify
    out.push({
      kind: 'clarify',
      text: `Jira · the PO's answers to ${open} open question${s(open)}${parts(quiet(silent))}`,
      ...gate(a.clarify.pending, silent, () =>
        rounds >= 3
          ? `The PO has been silent for ${windows(silent)} on ${a.ticket}, and the follow-up round cap (3) is already reached, so ${open} of ${total} questions are still open. Draft one short Jira comment that tags the PO and repeats the closing ask only, without any new question, and tell me in your reply (not in the comment) how long it has been since the last ask and whether anyone else on the ticket could answer. ${rule}`
          : `The PO has not answered ${open} of ${total} open questions on ${a.ticket}; they have been silent for ${windows(silent)}. Draft one short Jira comment that tags the PO, says in plain business words that these questions still block the work, and adds no new question${silent >= 3 ? '. Say in your reply (not in the comment) how long it has been since the last ask' : ''}. ${rule}`,
      ),
    })
  }
  if (a.bug && a.bug.open > 0)
    out.push({
      kind: 'bugfix',
      text: `Jira · the reporter's reply on ${a.bug.open} concern${s(a.bug.open)}${parts(quiet(a.bug.silent))}`,
      ...gate(a.bug.pending, a.bug.silent, () =>
        `${a.bug!.open} concern${s(a.bug!.open)} on ${a.ticket} still wait${a.bug!.open > 1 ? '' : 's'} for an answer, and nobody has replied for ${windows(a.bug!.silent)}. Read the state file to see whom each concern waits on (the reporter, or the PO for a product decision), and draft one short Jira comment that tags them and asks for their answer in plain words, adding nothing new. ${rule}`,
      ),
    })
  if (a.pr && a.pr.waiting > 0)
    out.push({
      kind: 'pr',
      text: `Slack · the reviewer's verdict on ${a.pr.waiting} of ${a.pr.total} PR${s(a.pr.total)}${parts(a.pr.round ? `round ${a.pr.round}` : '', quiet(a.pr.silent))}`,
      ...gate(a.pr.pending, a.pr.silent, () =>
        `${a.pr!.waiting} of ${a.pr!.total} PR${s(a.pr!.total)} of ${a.ticket} still have no reviewer verdict (review round ${a.pr!.round || 1}), and the review thread has been quiet for ${windows(a.pr!.silent)}. Ping the reviewer in the PR review thread the way /pr's review loop does, with the links of only the PRs that have no verdict.`,
      ),
    })
  return out
}

// the files that hold an evidence comment, best first: /verify's draft for Jira, then the table /verify --concern wrote for /bugfix
export const EVIDENCE_FILES = ['jira-comment.md', 'concern-evidence.md']

// The `[ ok ]` button on `Next:`: the step the run recorded, sent to the agent as a message built from the situation.
// `Next:` is free text the run wrote (it may carry a condition: "once the reviewer signs off"), so it goes in as a quotation inside a fixed
// frame that makes the agent check that condition against the real state first, and leaves any merge, push or Jira post to its skill's own
// go-ahead. Around it:
//  · no button — with the reason on the line — while a drafted message waits for the user, and, for a /merge step, while a PR has no `lgtm`
//    or a PR concern is open (the merge gate must not be pressed through);
//  · the numbers the pane has read (stage, open questions, PRs without lgtm, open concerns, declared blockers) go into the message;
//  · one sentence for the kind of step: the merge gate, the PO's answers, a bug fix, the PR review, implementation, or none of those.
export const nextStep = (p: NonNullable<Pipeline>): { prompt: string | null; hold: string | null } => {
  const step = (p.next ?? '').replace(/\s+/g, ' ').trim().slice(0, 300)
  if (!/^[A-Z][A-Z0-9]+-\d+$/.test(p.ticket) || !step) return { prompt: null, hold: null }
  const s = (n: number) => (n > 1 ? 's' : '')
  if (p.clarify?.pending || p.bug?.pending || p.prLoop?.pending) return { prompt: null, hold: 'confirm the drafted message first' }
  const merge = /\/merge\b/.test(step)
  if (merge && p.prLoop && p.prLoop.waiting > 0)
    return { prompt: null, hold: `${p.prLoop.waiting} of ${p.prLoop.total} PR${s(p.prLoop.total)} ${p.prLoop.waiting > 1 ? 'have' : 'has'} no lgtm yet` }
  if (merge && p.concerns.length > 0) return { prompt: null, hold: `${p.concerns.length} open PR concern${s(p.concerns.length)}` }
  const stage = p.stages.find(x => x.state !== 'done')
  const facts = [
    stage ? `stage ${stage.id} ${stage.name}` : '',
    p.oq && p.oq.total ? `${p.oq.open} of ${p.oq.total} open questions still open` : '',
    p.prLoop ? `${p.prLoop.waiting} of ${p.prLoop.total} PR${s(p.prLoop.total)} without lgtm` : '',
    p.concerns.length ? `${p.concerns.length} open PR concern${s(p.concerns.length)}` : '',
    p.bug && p.bug.open ? `${p.bug.open} bug concern${s(p.bug.open)} open` : '',
    p.blockers.length ? `${p.blockers.length} declared blocker${s(p.blockers.length)}` : '',
  ].filter(Boolean)
  const kind = merge ? 'merge' : stage?.name === 'clarify' ? 'answers' : stage?.name === 'bugfix' ? 'bugfix' : stage?.name === 'prs' ? 'review' : stage?.name === 'implement' ? 'implement' : 'other'
  const about = {
    merge: 'This is the merge gate: before /merge, confirm that every PR has lgtm for its current head, that no concern is open and that the pipelines are green; ask me if anything is unclear.',
    answers: "This is the step that folds in the PO's answers: read the new Jira comments, update the open-question list and the spec from what the PO decided, then continue.",
    bugfix: 'This is the bug-fix step: apply the decisions already given, fix, prove it with /verify, and stop at a drafted comment for my confirmation.',
    review: "This is the PR review step: follow /pr's review loop for the PRs without a verdict, and do not merge.",
    implement: 'This is the implement step: hand the tasks to workers as /assign does, and do not start a second run if workers are already running.',
    other: '',
  }[kind]
  return {
    prompt: `Carry out the next step recorded for ${p.ticket}: "${step}". Where things stand: ${facts.length ? facts.join('; ') : 'nothing else recorded'}. ${about ? `${about} ` : ''}First check against the real state (git, the PRs, Jira) that whatever it waits for is true; if it is not, tell me what is missing and do nothing else. A merge, a push to a PR branch or a Jira post still needs my explicit go-ahead as its skill says.`,
    hold: null,
  }
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

// the checklist counts of a file: nothing open when it is not there, null when it is there but cannot be read
const countFrom = async ($: any, path: string): Promise<{ open: number; total: number } | null> => {
  if (!(await $.fs.exists(path).catch(() => false))) return { open: 0, total: 0 }
  const md = await $.fs.read(path).catch(() => null)
  return md === null ? null : countItems(md)
}

// a file's text, or null when it is not there or cannot be read
const readIf = async ($: any, path: string): Promise<string | null> =>
  (await $.fs.exists(path).catch(() => false)) ? await $.fs.read(path).catch(() => null) : null

// the open items of a checklist file: [] when the file is not there (nothing open), null when it is there but cannot be read
const openFrom = async ($: any, path: string, section?: string): Promise<string[] | null> => {
  if (!(await $.fs.exists(path).catch(() => false))) return []
  const md = await $.fs.read(path).catch(() => null)
  return md === null ? null : openItems(md, section)
}

// newest .shipkit/pipeline-<ticket>.md under the session cwd (failure notes excluded)
const refresh = async ($: any, withSpin = false) => {
  const files = (await $.fs.list('.shipkit').catch(() => []))
    .filter((f: any) => /^pipeline-(?!failure-).+\.md$/.test(f.name))
    .sort((a: any, b: any) => b.mtimeMs - a.mtimeMs)
  const md = files[0] ? await $.fs.read(`.shipkit/${files[0].name}`) : ''
  const parsed = parse(md, files[0]?.mtimeMs)
  const p = parsed && {
    ...parsed,
    oq: parsed.spec ? await countFrom($, `${parsed.spec}/open-question.md`) : null,
    clarify: null as ReturnType<typeof parseClarify> | null,
    evidenceFile: null as string | null,
    concerns: [] as string[],
  }
  if (p) {
    const [clMd, bugMd, prMd] = await Promise.all(['clarify', 'bugfix', 'pr'].map(k => readIf($, `.shipkit/${k}-${p.ticket}.md`)))
    p.clarify = clMd === null ? null : parseClarify(clMd)
    if (p.evidence) {
      const dir = p.evidence.replace(/\/+$/, '')
      for (const f of EVIDENCE_FILES) if (!p.evidenceFile && (await $.fs.exists(`${dir}/${f}`).catch(() => false))) p.evidenceFile = `${dir}/${f}`
    }
    p.concerns = prMd === null ? [] : openItems(prMd, '## Concerns')
    p.bug = bugMd === null ? null : parseBugfix(bugMd)
    p.prLoop = prMd === null ? null : parsePrLoop(prMd)
    p.waiting = waitingOn({ ticket: p.ticket, oq: p.oq, clarify: p.clarify, bug: p.bug, pr: p.prLoop })
  }
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
    const pings = await read($, pinged)
    const now = await $.clock.now()
    const ns = nextStep(p)
    const nextSince = pings[`${p.ticket}:next`] === undefined ? Infinity : now - pings[`${p.ticket}:next`]
    const spun = FRAMES[(await read($, frame)) % FRAMES.length]
    const [glyph, label, color] = p.status ? STATUS[p.status.state] : [null, null, undefined]
    const badge = p.status ? `${live ? spun : glyph} ${label}` : null
    // blockers sit in the stage they belong to: a declared one in the stage it names (else the next unfinished), an open PR concern in `prs`;
    // a failed stage is its own blocker and already shows as ✗
    const blockedIn = (s: Stage) => p.blockers.filter(b => blockerStage(b, p.stages) === s.id).length + (s.name === 'prs' ? p.concerns.length : 0)
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
        {!next && p.status?.text ? <Text color={color}>{p.status.text}</Text> : null}
        {p.prs.length ? (
          <Text>
            PRs:{' '}
            {p.prs
              .map(pr => [pr.label ? `${pr.label} ` : '', <Link href={pr.url} label={prLabel(pr.url)} />])
              .flatMap((part, i) => (i ? [' · ', ...part] : part))}
          </Text>
        ) : null}
        {p.waiting.map((w, i) => {
          const key = `${p.ticket}:${w.kind}`
          const since = pings[key] === undefined ? Infinity : now - pings[key]
          return (
            <Box>
              <Text dimColor>⏳ {w.text} </Text>
              {w.ping === null ? (
                <Text dimColor>· {w.hold}</Text>
              ) : since < PING_REST_MS ? (
                <Text dimColor>· pinged {age(since)}</Text>
              ) : (
                <Button
                  key={`ping:${i}`}
                  plain
                  hover={hov(`ping:${i}`)}
                  onPress={async () => {
                    await update($, pinged, o => ({ ...o, [key]: now }))
                    await $.prompt.submit({ text: w.ping!, asUser: true })
                  }}
                >
                  <Text dimColor hover={hov(`ping:${i}`)}>
                    [ ping ]
                  </Text>
                </Button>
              )}
            </Box>
          )
        })}
        {p.pollers.map(w => (
          <Text dimColor>⏳ {w}</Text>
        ))}
        {p.stages.map(s => {
          const mark = s.state === 'done' ? '✓' : s.state === 'failed' ? '✗' : s === next ? (live ? spun : '▸') : '·'
          // the clarify row opens up to its summary: the open questions (counted in open-question.md), a drafted question waiting for the user,
          // and how long the PO has been silent (both from /clarify's own state file)
          const more =
            s.name === 'clarify'
              ? [
                  ...(p.spec ? [p.oq === null ? 'OQ: unknown (open-question.md could not be read)' : p.oq.total ? `OQ: ${p.oq.open} open of ${p.oq.total}` : 'OQ: none open'] : []),
                  ...(p.clarify?.pending ? ['✎ draft waiting for you'] : []),
                  ...(p.clarify?.silent ? [`PO silent for ${p.clarify.silent} poll window${p.clarify.silent > 1 ? 's' : ''}`] : []),
                ]
              : []
          const body = [...more, ...s.details]
          // a closed row must not hide a problem: the open questions, a draft or a silent PO on clarify, or a detail line the run flagged
          // with ⚠️ / ⬆️ (a branch that is not on origin yet); blockers have their own ⛔ and a failed stage its ✗
          const attention =
            (s.name === 'clarify' && ((p.oq?.open ?? 0) > 0 || p.clarify?.pending || (p.clarify?.silent ?? 0) > 0)) || s.details.some(d => /⚠️|⬆️/.test(d))
          const toggle = `${p.ticket}:${s.id}`
          const shown = overrides[toggle] ?? (s.state === 'failed' || s === next)
          const row = (
            <Text
              color={s.state === 'failed' ? 'red' : s.state === 'done' ? 'green' : undefined}
              dimColor={s.state === 'todo' && s !== next}
              hover={body.length ? hov(`stage:${s.id}`) : undefined}
            >
              {mark} {s.id} {s.name}
              {blockedIn(s) ? ` · ⛔ ${blockedIn(s)}` : ''}
              {body.length && !shown && attention ? ' ⚠️' : ''}
              {body.length ? (shown ? ' ▴' : ' ▾') : ''}
            </Text>
          )
          return (
            <Box flexDirection="column">
              {body.length ? (
                <Button key={`stage:${s.id}`} plain hover={hov(`stage:${s.id}`)} onPress={() => update($, open, o => ({ ...o, [toggle]: !shown }))}>
                  {row}
                </Button>
              ) : (
                row
              )}
              {s === next && p.status?.text ? <Text color={color}>    {p.status.text}</Text> : null}
              {shown ? body.map(d => <Text dimColor>    {d}</Text>) : null}
            </Box>
          )
        })}
        {p.next ? (
          <Box>
            <Text>Next: {p.next} </Text>
            {p.status?.state !== 'waiting-user' || (ns.prompt === null && ns.hold === null) ? null : ns.prompt === null ? (
              <Text dimColor>· {ns.hold}</Text>
            ) : nextSince < NEXT_REST_MS ? (
              <Text dimColor>· sent {age(nextSince)}</Text>
            ) : (
              <Button
                key="next"
                plain
                hover={hov('next')}
                onPress={async () => {
                  await update($, pinged, o => ({ ...o, [`${p.ticket}:next`]: now }))
                  await $.prompt.submit({ text: ns.prompt!, asUser: true })
                }}
              >
                <Text hover={hov('next')}>[ ok ]</Text>
              </Button>
            )}
          </Box>
        ) : null}
        {p.evidence ? (
          <Button
            key="evidence"
            plain
            hover={hov('evidence')}
            onPress={async press => {
              // the evidence comment, when there is one, opens as a tab in Orca; no file, no Orca (or no process API on this surface): copy the path
              if (p.evidenceFile) {
                try {
                  const r = await $.process.run(['orca', 'file', 'open', p.evidenceFile, '--focus'])
                  if (r.exitCode === 0) return
                } catch {
                  // fall through to the copy
                }
              }
              await $.ui.copy({ text: p.evidence!, surface: press.surface })
            }}
          >
            <Text dimColor hover={hov('evidence')}>
              Evidence: {p.evidence} {p.evidenceFile ? '(review draft comment)' : '(press to copy)'}
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
