/**
 * labSource.ts : d'où le Laboratoire tire ses données (R3).
 *
 * Toujours le moteur (lib/executor.ts) : s'il échoue, l'erreur remonte à l'écran. Aucun repli
 * automatique, pour ne jamais montrer des données de démonstration à la place d'un vrai résultat.
 * `?source=fixtures` (développement) force les fixtures de dev/fixtureSource.ts, et l'interface le signale.
 */

import { api, ApiError, type CallOptions } from './executor'
import { importKey } from './share'
import type {
  EngineState,
  ExperimentSpec,
  ExperimentSummary,
  RunResult,
  SweepRequest,
  SweepResult,
  TrainingSessionResponse,
  ValidateResponse,
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

// ---------------------------------------------------------------------------
// Expérience importée (P1) : YAML brut, collé dans l'écran Import ou partagé par Supabase
// ---------------------------------------------------------------------------

/** Erreur de schéma d'un YAML importé : le Laboratoire la montre avec les lignes en cause. */
export class ImportError extends Error {
  readonly report: ValidateResponse
  constructor(report: ValidateResponse) {
    super("Ce fichier d'expérience contient des erreurs : corrigez-le dans l'écran Import.")
    this.name = 'ImportError'
    this.report = report
  }
}

/**
 * Ouvre un YAML importé. /api/validate retient le fichier côté moteur sous sa clé `import-<hash>` :
 * la spécification se lit alors par GET /api/experiments/{clé}, et /api/sweep prend cette clé.
 * /api/run reçoit toujours le YAML lui-même (raw_content). Si le moteur a redémarré et oublié la clé
 * (404), le fichier est validé de nouveau, puis l'appel relancé une fois.
 */
export async function openImported(
  content: string,
): Promise<{ spec: ExperimentSpec; source: LabSource; report: ValidateResponse }> {
  const report = await api.validate({ raw_content: content })
  if (report.errors.length > 0) throw new ImportError(report)
  const key = await importKey(content)
  const spec = await api.experiment(key)
  const again = async <T>(call: () => Promise<T>): Promise<T> => {
    try {
      return await call()
    } catch (err) {
      if (!(err instanceof ApiError) || err.status !== 404) throw err
      await api.validate({ raw_content: content })
      return call()
    }
  }
  const source: LabSource = {
    kind: 'api',
    run: (_spec, state, opts) => api.run({ experiment_id: null, raw_content: content, state }, opts),
    sweep: (req, opts) => again(() => api.sweep({ ...req, experiment_id: key }, opts)),
  }
  return { spec, source, report }
}
