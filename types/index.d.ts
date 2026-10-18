export type Stage = { id: string; name: string; state: 'done' | 'todo' | 'failed'; details: string[] }
export type Pr = { label: string | null; url: string }
// a wait read from a state file; `ping` is the message the pane's button sends to the agent to nudge whoever is awaited, built from the situation
export type Wait = {
  kind: 'clarify' | 'bugfix' | 'pr'
  text: string
  ping: string | null // null: no ping now, and `hold` says why
  hold: string | null
}
export type Status = { state: 'waiting-user' | 'running' | 'failed' | 'done'; text: string }
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
  pollers: string[] // `Poller:` lines the run declared (waits the pane cannot read from a state file)
  waiting: Wait[] // waits read from /clarify's, /bugfix's and /pr's own state files, while their loop is still open
  mtimeMs: number
  stages: Stage[]
} | null

declare module 'claude-code' {
  interface PluginState {
    'shipkit': { pipeline: Pipeline; frame: number; open: Record<string, boolean>; pinged: Record<string, number> }
  }
}
