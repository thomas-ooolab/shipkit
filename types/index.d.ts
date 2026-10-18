export type Stage = { id: string; name: string; state: 'done' | 'todo' | 'failed'; details: string[] }
export type Pr = { label: string | null; url: string }
// a wait read from a state file; `ping` is the message the pane's button sends to the agent to nudge whoever is awaited, built from the situation
export type Wait = {
  kind: 'clarify' | 'bugfix' | 'pr'
  text: string
  ping: string | null // the whole message as a fixed template (the fallback); null: no ping now, and `hold` says why
  hold: string | null
  brief: string // what the writer is told: the intent and the facts, as data
  tail: string // the fixed rule appended to whatever the writer drafts
}
export type Status = { state: 'waiting-user' | 'running' | 'failed' | 'done'; text: string }
// what the session model's check of a pipeline reported, field by field; a key that is absent was not checked, so the state file's value stands
export type Collected = {
  status?: Status | null
  next?: string | null
  blockers?: string[]
  stages?: Stage[] // only the stages the state file also lists are taken, by id
  prs?: Pr[]
  oq?: { open: number; total: number } | null
  concerns?: string[]
  clarify?: { pending: boolean; silent: number; rounds: number } | null
  bug?: { open: number; silent: number; pending: boolean } | null
  prLoop?: { waiting: number; total: number; round: number; silent: number; pending: boolean } | null
}
// the check as the pane keeps it, by ticket: while it runs, the last good answer stays (`data`) so the pane keeps showing it
export type Checked = { ticket: string; at: number; running: boolean; data: Collected | null; error: string | null } | null
// what the pane says about its check: how it stands, when, and which values differ from the state file (`stage:<id>`, `detail:<id>:<line>`,
// `status`, `next`, `blockers`, `prs`, `oq`, `concerns`, `waits`)
export type Check = { state: 'running' | 'ok' | 'failed'; at: number; hasData: boolean; diff: string[]; error: string | null }
export type Pipeline = {
  ticket: string
  flow: string | null
  status: Status | null
  next: string | null
  spec: string | null // the Spec: dir; its open-question.md is where the open questions live
  blockers: string[] // `Blocker:` lines the run declared
  oq: { open: number; total: number } | null // the checklist of <spec>/open-question.md; null = no Spec: line, or the file could not be read
  clarify: { pending: boolean; silent: number } | null // read from .shipkit/clarify-<ticket>.md; null = no such file
  concerns: string[] // open PR concerns read from .shipkit/pr-<ticket>.md
  bug: { open: number; silent: number; pending: boolean } | null // /bugfix's state file, when there is one
  prLoop: { waiting: number; total: number; round: number; silent: number; pending: boolean } | null // /pr's state file, when there is one
  prs: Pr[]
  evidence: string | null
  evidenceFile: string | null // the evidence comment inside that dir, when /verify or /bugfix wrote one
  evidenceLatest: string | null // else the newest file in that dir (a screenshot, a data file), when there is any
  pollers: string[] // `Poller:` lines the run declared (waits the pane cannot read from a state file)
  waiting: Wait[] // waits read from /clarify's, /bugfix's and /pr's own state files, while their loop is still open
  mtimeMs: number
  stages: Stage[]
  check: Check | null
} | null

declare module 'claude-code' {
  interface PluginState {
    'shipkit': { pipeline: Pipeline; frame: number; open: Record<string, boolean>; pinged: Record<string, { at: number; sent: boolean }>; drafting: Record<string, string>; halted: Record<string, boolean>; checked: Checked }
  }
}
