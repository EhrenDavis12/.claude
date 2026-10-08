import type { On } from 'claude-code'
import { describe, expect, test } from 'claude-code/testing'

import { countRound, overBudget, prdIn, srcRootsIn } from '../hooks/logic'

const scope = { srcRoots: ['src/micro-notebook', 'src/micro-notebook-auth', 'src/web-notebook'], prds: 'Docs/RAG/PRDs' }

describe('logic', () => {
  test('srcRoot matches whole, never as a prefix of a longer one', () => {
    expect(srcRootsIn('Review src/micro-notebook-auth only.', scope)).toEqual(['src/micro-notebook-auth'])
    expect(srcRootsIn('Review src/micro-notebook/lib/x.ts and src/web-notebook.', scope)).toEqual([
      'src/micro-notebook',
      'src/web-notebook',
    ])
  })

  test('PRD path is read from the prompt, null when absent', () => {
    expect(prdIn('PRD: Docs/RAG/PRDs/agent-ui.md, srcRoot src/web-notebook', scope)).toBe('Docs/RAG/PRDs/agent-ui.md')
    expect(prdIn('no prd here', scope)).toBe(null)
  })

  test('three rounds use the budget; a 4th is over', () => {
    let s = {}
    for (let i = 0; i < 3; i++) s = countRound(s, 'Docs/RAG/PRDs/a.md', ['src/web-notebook'])
    expect(overBudget(s, 'Docs/RAG/PRDs/a.md', ['src/web-notebook']).length).toBe(1)
    expect(overBudget(s, 'Docs/RAG/PRDs/b.md', ['src/web-notebook']).length).toBe(0)
  })
})

const review = (prompt: string) => ({ tool: 'Agent' as const, subagent_type: 'forge-code-reviewer', description: 'review', prompt })

// The plugin reads CLAUDE.md to see whether forge is active; tests answer that read here.
const forgeOn = (on: On) =>
  on('fs.read', async (_$, e, next) => (e.path.endsWith('/CLAUDE.md') ? { value: '@.claude/systems/forge/SYSTEM.md\n' } : next(e)))

test('the 4th reviewer dispatch on a slice is denied; other agents pass', async ($, on) => {
  forgeOn(on)
  let ran = 0
  const store = new Map<string, unknown>()
  on('store.get', async (_$, e) => ({ value: store.get(e.key) }))
  on('store.set', async (_$, e) => {
    store.set(e.key, e.value)
    return { value: undefined }
  })
  on('tool.call', async () => {
    ran += 1
    return { result: 'ok' }
  })

  const prompt = 'Review src/web-notebook for Docs/RAG/PRDs/agent-ui.md'
  for (let i = 0; i < 3; i++) {
    const r = await $.tool.call(review(prompt))
    expect('deny' in r).toBe(false)
  }
  const fourth = await $.tool.call(review(prompt))
  expect('deny' in fourth).toBe(true)
  expect(ran).toBe(3)

  // A different slice still has its budget, and non-reviewer agents are never counted.
  await $.tool.call(review('Review src/web-notebook for Docs/RAG/PRDs/other.md'))
  await $.tool.call({ tool: 'Agent', subagent_type: 'forge-code-writer', description: 'w', prompt })
  expect(ran).toBe(5)
})

test('a reviewer prompt that names no srcRoot is denied', async ($, on) => {
  forgeOn(on)
  on('tool.call', async () => ({ result: 'ok' }))
  const r = await $.tool.call(review('Review the change.'))
  expect('deny' in r).toBe(true)
})

test('nothing is counted or denied when forge is not the active system', async ($, on) => {
  on('fs.read', async () => ({ value: 'no system import here' }))
  let ran = 0
  on('tool.call', async () => {
    ran += 1
    return { result: 'ok' }
  })
  for (let i = 0; i < 5; i++) await $.tool.call(review('Review the change.'))
  expect(ran).toBe(5)
})
