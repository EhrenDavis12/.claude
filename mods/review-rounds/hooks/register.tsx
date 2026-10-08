import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Slices } from '../types'
import {
  REVIEWER,
  countRound,
  label,
  limitOf,
  matching,
  overBudget,
  prdIn,
  srcRootsIn,
  type Scope,
} from './logic'

const slices = atom({ plugin: 'review-rounds', key: 'slices' } as const, {} as Slices)
const STORE_KEY = 'slices'

// The active project's srcRoots and prds path, read from the same two files every forge agent reads.
async function scopeOf($: EngineInterface): Promise<Scope> {
  try {
    const { project } = JSON.parse(await $.fs.read('.claude/project/active.json'))
    const manifest = JSON.parse(await $.fs.read(`Docs/${project}/project.json`))
    return { srcRoots: manifest.srcRoots ?? [], prds: manifest.prds ?? null }
  } catch {
    return { srcRoots: [], prds: null }
  }
}

// Self-gate like the forge SessionStart hooks: act only while CLAUDE.md imports the forge system.
async function forgeActive($: EngineInterface) {
  try {
    return /^@\.claude\/systems\/forge\/SYSTEM\.md\s*$/m.test(await $.fs.read('CLAUDE.md'))
  } catch {
    return false
  }
}

async function save($: EngineInterface, fn: (s: Slices) => Slices) {
  const after = await update($, slices, s => fn(s ?? {}))
  await $.store.set(STORE_KEY, after)
  return after
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'review-rounds',
      description: 'Review-round budget: list | allow <srcRoot> | reset <srcRoot|all>',
    })

    // Load across sessions, and drop slices whose PRD is gone: a deleted PRD is a closed-out slice.
    const stored = ((await $.store.get(STORE_KEY)) ?? {}) as Slices
    const current = await read($, slices)
    const merged = Object.keys(current).length > 0 ? current : stored
    const kept: Slices = {}
    for (const [key, s] of Object.entries(merged)) {
      if (s.prd === null || (await $.fs.exists(s.prd))) kept[key] = s
    }
    await save($, () => kept)

    return next(e)
  })

  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (e.subagent_type !== REVIEWER || !(await forgeActive($))) return next(e)

    const scope = await scopeOf($)
    const roots = srcRootsIn(e.prompt, scope)
    const prd = prdIn(e.prompt, scope)

    if (roots.length === 0) {
      return {
        deny:
          `review-rounds: a ${REVIEWER} dispatch must name its srcRoot path (e.g. src/web-notebook) ` +
          'so the round can be counted against its slice. Re-dispatch with the srcRoot in the prompt.',
      }
    }

    const over = overBudget(await read($, slices), prd, roots)
    if (over.length > 0) {
      const names = over.map(label).join(', ')
      return {
        deny:
          `review-rounds: review budget used up for ${names}. Do not dispatch another review round. ` +
          'Sort what is left: blocking findings (data loss, security, a broken core flow, a deadlock) — ' +
          'pause and ask the user whether to ship with it logged, redesign, or allow more rounds; ' +
          'anything else goes under the PRD Follow-ups and the slice moves on. ' +
          'Only the user can grant more rounds, by running /review-rounds allow <srcRoot>.',
      }
    }

    const after = await save($, s => countRound(s, prd, roots))
    const last = roots
      .map(root => Object.values(after).find(s => s.srcRoot === root && s.prd === prd)!)
      .filter(s => s.rounds === limitOf(s))
    if (last.length > 0) $.ui.toast(`Last review round: ${last.map(label).join(', ')}`)

    return next(e)
  })

  on('command.run', { command: 'review-rounds' }, async ($, e) => {
    const [verb = 'list', ...rest] = e.args.trim().split(/\s+/).filter(Boolean)
    const needle = rest.join(' ')
    const current = await read($, slices)

    if (verb === 'list') {
      const rows = Object.values(current).map(label)
      return { text: rows.length > 0 ? rows.join('\n') : 'No review rounds counted.' }
    }

    if ((verb === 'allow' || verb === 'reset') && needle === '') {
      return { text: `Usage: /review-rounds ${verb} <srcRoot>${verb === 'reset' ? ' | all' : ''}` }
    }

    const keys = matching(current, needle)
    if (keys.length === 0) return { text: `No slice matches "${needle}".` }

    if (verb === 'allow') {
      const after = await save($, s => {
        const next = { ...s }
        for (const k of keys) {
          const was = next[k]
          if (was) next[k] = { ...was, extra: was.extra + 1 }
        }
        return next
      })
      const names = keys.flatMap(k => (after[k] ? [label(after[k])] : [])).join(', ')
      return {
        text: `One more round allowed: ${names}`,
        context: [`The user allowed one more ${REVIEWER} round for: ${names}.`],
      }
    }

    if (verb === 'reset') {
      await save($, s => {
        const next = { ...s }
        for (const k of keys) delete next[k]
        return next
      })
      return { text: `Reset ${keys.length} slice(s).` }
    }

    return { text: 'Usage: /review-rounds [list | allow <srcRoot> | reset <srcRoot|all>]' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const list = Object.values(await read($, slices))
    if (e.props.hasSurvey || list.length === 0) return next(e)

    const { Box, Text } = $.ui.resolve(e)

    return (
      <Box flexDirection="column">
        {list.map(s => (
          <Text key={`${s.prd}|${s.srcRoot}`} dimColor={s.rounds < limitOf(s)} bold={s.rounds >= limitOf(s)}>
            Review rounds · {label(s)}
            {s.rounds >= limitOf(s) ? ' — budget used' : ''}
          </Text>
        ))}
      </Box>
    )
  })
}
