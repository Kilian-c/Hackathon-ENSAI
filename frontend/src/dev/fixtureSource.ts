/**
 * fixtureSource.ts : source de données de REPLI du Laboratoire (R3), tant que les routes du moteur
 * (GET /api/experiments/{id}, POST /api/run, POST /api/sweep) ne répondent pas.
 *
 * - Spécifications : dev/specs/*.spec.json, produites depuis experiments/*.yaml par le chargeur de R1
 *   (backend/engine/loader.py), donc identiques à ce que renverra GET /api/experiments/{id}.
 * - Résultats : fixtures de R1 (src/fixtures/*.run.json). Aucune table propre à un théorème : on prend
 *   les fixtures dont le préfixe de nom figure dans le nom du YAML, puis, selon l'état, celle où la
 *   méthode principale est Fiable (état sain) ou ne l'est pas (hypothèse cassée).
 * Les résultats ne suivent donc PAS les curseurs finement : l'interface l'affiche dans un bandeau.
 * Chargement paresseux : rien de ceci n'entre dans le paquet principal.
 */

import { disciplineSlug, selectedFromFilter } from '../lib/trainChoice'
import { headlineVerdict } from '../lib/lab'
import { brokenHypotheses } from '../lib/state'
import type {
  EngineState,
  ExperimentSpec,
  ExperimentSummary,
  RunResult,
  SweepRequest,
  SweepResult,
  TrainingSessionResponse,
} from '../lib/types.gen'

const specFiles = import.meta.glob<ExperimentSpec>('./specs/*.spec.json', { import: 'default' })
const runFiles = import.meta.glob<RunResult>('../fixtures/*.run.json', { import: 'default' })
const sweepFiles = import.meta.glob<SweepResult>('../fixtures/*.sweep.json', { import: 'default' })

const stem = (path: string) => path.split('/').pop()!.split('.')[0]

async function allSpecs(): Promise<{ stem: string; spec: ExperimentSpec }[]> {
  return Promise.all(Object.entries(specFiles).map(async ([p, load]) => ({ stem: stem(p), spec: await load() })))
}

async function findSpec(id: string): Promise<{ stem: string; spec: ExperimentSpec } | null> {
  return (await allSpecs()).find((s) => s.spec.id === id) ?? null
}

export async function fixtureExperiments(): Promise<ExperimentSummary[]> {
  return (await allSpecs()).map(({ spec }) => ({
    id: spec.id,
    title: spec.title,
    discipline: spec.discipline,
    level: spec.level,
    concepts: spec.concepts,
  }))
}

export async function fixtureSpec(id: string): Promise<ExperimentSpec> {
  const hit = await findSpec(id)
  if (!hit) throw new Error(`Aucune spécification de démonstration pour « ${id} ».`)
  return hit.spec
}

/** La série de démonstration de R1, restreinte au filtre demandé. */
export async function fixtureSession(filter: string): Promise<TrainingSessionResponse> {
  const session = (await import('../fixtures/training_session.json')).default as unknown as TrainingSessionResponse
  if (filter === 'toutes') return session
  const wanted = selectedFromFilter(filter)
  const kept = new Set(
    (await allSpecs())
      .filter(({ spec }) => spec.id === filter || wanted.includes(disciplineSlug(spec.discipline)))
      .map(({ spec }) => spec.id),
  )
  return {
    ...session,
    id: `${filter}~${session.seed}`,
    filter,
    questions: session.questions.filter((q) => kept.has(q.experiment_id)),
  }
}

export async function fixtureRun(spec: ExperimentSpec, state: EngineState): Promise<RunResult> {
  const own = (await allSpecs()).find((s) => s.spec.id === spec.id)?.stem ?? ''
  const candidates = await Promise.all(
    Object.entries(runFiles)
      .filter(([p]) => own.includes(stem(p).split('_')[0]))
      .map(async ([, load]) => load()),
  )
  if (candidates.length === 0) throw new Error(`Aucune fixture de résultat pour « ${spec.id} ».`)
  const healthy = brokenHypotheses(spec, state).length === 0
  const pick = candidates.find((r) => (headlineVerdict(r) === 'ok') === healthy) ?? candidates[0]
  return pick
}

export async function fixtureSweep(req: SweepRequest): Promise<SweepResult | null> {
  const targets = req.axes.map((a) => a.target).join('|')
  for (const load of Object.values(sweepFiles)) {
    const s = await load()
    if (s.axes.map((a) => a.target).join('|') === targets && (req.measure === null || req.measure === s.measure)) return s
  }
  return null
}
