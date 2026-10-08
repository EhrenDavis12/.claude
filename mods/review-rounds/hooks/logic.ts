import type { Slice, Slices } from '../types'

// forge's rule: three review rounds per slice, then decide (SYSTEM.md, "The review loop has a budget").
export const BUDGET = 3
export const REVIEWER = 'forge-code-reviewer'

export type Scope = { srcRoots: string[]; prds: string | null }

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export const sliceKey = (prd: string | null, srcRoot: string) => `${prd ?? '-'}|${srcRoot}`

export const limitOf = (slice: Slice) => BUDGET + slice.extra

/** The srcRoots a reviewer prompt names, matched whole so src/micro-notebook never matches src/micro-notebook-auth. */
export function srcRootsIn(prompt: string, scope: Scope): string[] {
  if (scope.srcRoots.length > 0) {
    return scope.srcRoots.filter(root =>
      new RegExp(`(^|[^\\w/-])${escape(root)}(?![\\w-])`).test(prompt),
    )
  }
  // No manifest: fall back to any src/<name> the prompt mentions.
  const found = new Set<string>()
  for (const m of prompt.matchAll(/(?:^|[^\w/-])(src\/[a-z0-9][\w-]*)(?![\w-])/gi)) if (m[1]) found.add(m[1])
  return [...found]
}

/** The first PRD file a reviewer prompt names, or null on the no-PRD path. */
export function prdIn(prompt: string, scope: Scope): string | null {
  const dir = scope.prds ? escape(scope.prds.replace(/\/$/, '')) : '[\\w./-]*PRDs'
  const m = prompt.match(new RegExp(`(${dir}/[\\w.-]+\\.md)`))
  return m?.[1] ?? null
}

/** The slices this dispatch would push past their budget. */
export function overBudget(slices: Slices, prd: string | null, roots: string[]): Slice[] {
  return roots
    .map(root => slices[sliceKey(prd, root)])
    .filter((s): s is Slice => s !== undefined && s.rounds >= limitOf(s))
}

export function countRound(slices: Slices, prd: string | null, roots: string[]): Slices {
  const next = { ...slices }
  for (const root of roots) {
    const key = sliceKey(prd, root)
    const was = next[key] ?? { prd, srcRoot: root, rounds: 0, extra: 0 }
    next[key] = { ...was, rounds: was.rounds + 1 }
  }
  return next
}

/** Slices whose srcRoot (or PRD file name) contains `needle`; every slice for "all". */
export function matching(slices: Slices, needle: string): string[] {
  const n = needle.trim()
  return Object.entries(slices)
    .filter(([, s]) => n === 'all' || s.srcRoot.includes(n) || (s.prd ?? '').includes(n))
    .map(([key]) => key)
}

export const shortRoot = (root: string) => root.replace(/^src\//, '')
export const shortPrd = (prd: string | null) =>
  prd === null ? 'no PRD' : prd.replace(/^.*\//, '').replace(/\.md$/, '')

export const label = (s: Slice) => `${shortRoot(s.srcRoot)} (${shortPrd(s.prd)}) ${s.rounds}/${limitOf(s)}`
