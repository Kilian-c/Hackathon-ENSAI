/**
 * labSource.ts : d'où le Laboratoire tire ses données (R3).
 *
 * Toujours le moteur (lib/executor.ts) : s'il échoue, l'erreur remonte à l'écran. Aucun repli
 * automatique, pour ne jamais montrer des données de démonstration à la place d'un vrai résultat.
 * `?source=fixtures` (développement) force les fixtures de dev/fixtureSource.ts, et l'interface le signale.
 */

import { api, type CallOptions } from './executor'
import type {
  EngineState,
  ExperimentSpec,
  ExperimentSummary,
  RunResult,
  SweepRequest,
  SweepResult,
  TrainingSessionResponse,
} from './types.gen'

export interface LabSource {
  kind: 'api' | 'fixtures'
  run(spec: ExperimentSpec, state: EngineState, opts?: CallOptions): Promise<RunResult>
  /** null : pas de balayage disponible pour cette vue (la vue l'indique). */
  sweep(req: SweepRequest, opts?: CallOptions): Promise<SweepResult | null>
}

const apiSource: LabSource = {
  kind: 'api',
  run: (spec, state, opts) => api.run({ experiment_id: spec.id, raw_content: null, state }, opts),
  sweep: (req, opts) => api.sweep(req, opts),
}

async function fixtures() {
  return import('../dev/fixtureSource')
}

function forcedFixtures(): boolean {
  return typeof location !== 'undefined' && new URLSearchParams(location.search).get('source') === 'fixtures'
}

async function fixtureSource(): Promise<LabSource> {
  const f = await fixtures()
  return { kind: 'fixtures', run: (spec, state) => f.fixtureRun(spec, state), sweep: (req) => f.fixtureSweep(req) }
}

/** Charge la spécification et choisit la source (moteur, ou fixtures si elles sont demandées). */
export async function openExperiment(id: string): Promise<{ spec: ExperimentSpec; source: LabSource }> {
  if (!forcedFixtures()) return { spec: await api.experiment(id), source: apiSource }
  const f = await fixtures()
  return { spec: await f.fixtureSpec(id), source: await fixtureSource() }
}

/** Série d'Entraînement (ou série de démonstration si demandée). `seed` null : le moteur en tire une. */
export async function openSession(
  filter: string,
  seed: number | null,
): Promise<{ session: TrainingSessionResponse; kind: LabSource['kind'] }> {
  if (!forcedFixtures()) {
    return { session: await api.trainingSession({ filter, count: 10, seed }), kind: 'api' }
  }
  return { session: await (await fixtures()).fixtureSession(filter), kind: 'fixtures' }
}

/** Liste des expériences (moteur, ou fixtures si elles sont demandées). */
export async function listExperiments(): Promise<{ items: ExperimentSummary[]; kind: LabSource['kind'] }> {
  if (!forcedFixtures()) return { items: await api.experiments(), kind: 'api' }
  return { items: await (await fixtures()).fixtureExperiments(), kind: 'fixtures' }
}
