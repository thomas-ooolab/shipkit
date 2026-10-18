export type Stage = { id: string; name: string; state: 'done' | 'todo' | 'failed'; detail?: string }
export type Status = { state: 'waiting-user' | 'running' | 'failed' | 'done'; text: string }
export type Pipeline = {
  ticket: string
  flow: string | null
  status: Status | null
  next: string | null
  branch: string | null
  prs: string[]
  evidence: string | null
  poller: string | null
  mtimeMs: number
  stages: Stage[]
} | null

declare module 'claude-code' {
  interface PluginState {
    'shipkit': { pipeline: Pipeline; frame: number; open: Record<string, boolean> }
  }
}
