export type Stage = { id: string; name: string; state: 'done' | 'todo' | 'failed' }
export type Pipeline = { ticket: string; flow: string | null; stages: Stage[] } | null

declare module 'claude-code' {
  interface PluginState {
    'shipkit': { pipeline: Pipeline }
  }
}
