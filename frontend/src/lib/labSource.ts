/**
 * labSource.ts : d'où le Laboratoire tire ses données (R3).
 *
 * Par défaut, le moteur (lib/executor.ts). Si le moteur ne sait pas encore servir l'expérience
 * (route absente, moteur arrêté), on bascule UNE FOIS, au chargement, sur les fixtures de
 * dev/fixtureSource.ts, et l'interface le signale. `?source=fixtures` force les fixtures.
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

/** Charge la spécification et choisit la source (moteur, ou fixtures en repli). */
export async function openExperiment(id: string): Promise<{ spec: ExperimentSpec; source: LabSource }> {
  if (!forcedFixtures()) {
    try {
      return { spec: await api.experiment(id), source: apiSource }
    } catch (err) {
      console.warn('Moteur indisponible pour cette expérience : bascule sur les fixtures.', err)
    }
  }
  const f = await fixtures()
  return { spec: await f.fixtureSpec(id), source: await fixtureSource() }
}

/**
 * Série d'Entraînement (moteur, ou série de démonstration en repli). `seed` null : le moteur en tire une.
 */
export async function openSession(
  filter: string,
  seed: number | null,
): Promise<{ session: TrainingSessionResponse; kind: LabSource['kind'] }> {
  if (!forcedFixtures()) {
    try {
      return { session: await api.trainingSession({ filter, count: 10, seed }), kind: 'api' }
    } catch (err) {
      console.warn('Moteur indisponible pour l’Entraînement : bascule sur les fixtures.', err)
    }
  }
  return { session: await (await fixtures()).fixtureSession(filter), kind: 'fixtures' }
}

/** Liste des expériences (moteur, ou fixtures en repli). */
export async function listExperiments(): Promise<{ items: ExperimentSummary[]; kind: LabSource['kind'] }> {
  if (!forcedFixtures()) {
    try {
      return { items: await api.experiments(), kind: 'api' }
    } catch {
      /* repli ci-dessous */
    }
  }
  return { items: await (await fixtures()).fixtureExperiments(), kind: 'fixtures' }
}
