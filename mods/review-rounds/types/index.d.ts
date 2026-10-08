/** One slice: one srcRoot's change for one PRD (prd is null on the no-PRD path). */
export type Slice = {
  prd: string | null
  srcRoot: string
  rounds: number
  /** Extra rounds the user allowed past the budget with `/review-rounds allow`. */
  extra: number
}

export type Slices = Record<string, Slice>

declare module 'claude-code' {
  interface PluginState {
    'review-rounds': { slices: Slices }
  }
}
