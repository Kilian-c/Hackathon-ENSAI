/**
 * executor.ts : le client API UNIQUE de l'interface (R3). Aucun autre fichier n'appelle fetch() vers
 * le moteur. Cahier, section 4.11 ; CLAUDE.md, section 10.
 *
 * - Adresse du moteur : VITE_API_URL en ligne ; vide en local (le proxy Vite relaie /api vers le port 8000).
 * - Erreurs : toujours une ApiError avec un message en français (vouvoiement), jamais une exception brute.
 * - Pendant un glissement de curseur : createLatest() regroupe les appels (100 ms) et annule la
 *   requête précédente ; seule la réponse du DERNIER état est rendue (pas de résultat périmé à l'écran).
 * - Petit cache mémoire des réponses de /api/run et /api/sweep, par requête canonique : revenir sur un
 *   état déjà vu est instantané (le moteur a aussi son propre cache).
 */

import type {
  ExperimentSpec,
  ExperimentSummary,
  RunRequest,
  RunResult,
  SweepRequest,
  SweepResult,
  TrainingRequest,
  TrainingSessionResponse,
  ValidateRequest,
  ValidateResponse,
} from './types.gen'

const API_URL: string = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

/**
 * Délais côté interface. Plus longs que ceux du moteur (2 s pour /api/run, 15 s pour /api/sweep) :
 * un hébergeur gratuit endormi peut mettre une trentaine de secondes à se réveiller.
 */
export const TIMEOUT_MS = { short: 45_000, long: 60_000 } as const

export class ApiError extends Error {
  /** Code HTTP (0 : réseau ou délai dépassé). */
  readonly status: number
  /** Détail technique (corps de la réponse), pour la console. */
  readonly detail: unknown

  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** Message en français pour une réponse d'erreur du moteur. */
function errorMessage(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail // le moteur écrit déjà ses messages en français
  if (status === 404) return "Cette expérience n'existe pas (ou plus). Vérifiez le lien."
  if (status === 422) {
    // Erreur de validation Pydantic : on cite le premier champ fautif.
    const first = Array.isArray(detail) ? (detail[0] as { loc?: unknown[]; msg?: string }) : null
    const where = first?.loc?.filter((x) => x !== 'body').join('.')
    return `La requête envoyée au moteur est invalide${where ? ` (champ « ${where} »)` : ''}.`
  }
  if (status === 413) return 'Le fichier envoyé est trop volumineux (64 Ko au plus).'
  if (status === 504 || status === 408) return 'Le calcul a pris trop de temps. Essayez une taille d’échantillon plus petite.'
  if (status >= 500) return 'Le moteur a rencontré une erreur. Réessayez ; si le problème persiste, prévenez l’équipe.'
  return `Le moteur a refusé la requête (code ${status}).`
}

/** Appel HTTP générique, avec délai et annulation. */
async function request<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown,
  opts: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(opts.timeoutMs ?? TIMEOUT_MS.short)
  const signal = opts.signal ? AbortSignal.any([opts.signal, timeout]) : timeout
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (opts.signal?.aborted) throw err // annulation voulue : on la laisse passer telle quelle
    if (timeout.aborted) {
      throw new ApiError('Le moteur ne répond pas à temps. Il se réveille peut-être : réessayez dans quelques secondes.', 0, err)
    }
    throw new ApiError('Impossible de joindre le moteur. Vérifiez votre connexion, ou que le moteur est lancé.', 0, err)
  }
  const text = await res.text()
  let parsed: unknown = null
  let isJson = true
  try {
    parsed = text ? JSON.parse(text) : null
  } catch {
    parsed = text
    isJson = false
  }
  if (!res.ok) throw new ApiError(errorMessage(res.status, parsed), res.status, parsed)
  // En ligne, sans VITE_API_URL, l'hébergeur de l'interface répond sa page HTML avec un code 200.
  if (!isJson) {
    throw new ApiError("La réponse reçue ne vient pas du moteur. Vérifiez l'adresse du moteur.", res.status, parsed)
  }
  return parsed as T
}

// ---------------------------------------------------------------------------
// Cache mémoire (requêtes canoniques -> réponses)
// ---------------------------------------------------------------------------

const CACHE_SIZE = 64
const cache = new Map<string, unknown>()

function cached<T>(key: string, compute: () => Promise<T>): Promise<T> {
  if (cache.has(key)) {
    const hit = cache.get(key) as T
    cache.delete(key) // remis en tête : le moins récemment utilisé part en premier
    cache.set(key, hit)
    return Promise.resolve(hit)
  }
  return compute().then((value) => {
    cache.set(key, value)
    if (cache.size > CACHE_SIZE) cache.delete(cache.keys().next().value as string)
    return value
  })
}

/** Vide le cache (ex. après un changement d'expérience importée). */
export function clearCache(): void {
  cache.clear()
}

// ---------------------------------------------------------------------------
// Les routes du moteur
// ---------------------------------------------------------------------------

export interface CallOptions {
  signal?: AbortSignal
}

export const api = {
  /** GET /api/health : le moteur répond-il ? (sert aussi à le réveiller avant la démo). */
  health(opts: CallOptions = {}): Promise<{ status: string }> {
    return request('GET', '/api/health', undefined, opts)
  },

  /** GET /api/experiments : la galerie. */
  experiments(opts: CallOptions = {}): Promise<ExperimentSummary[]> {
    return request('GET', '/api/experiments', undefined, opts)
  },

  /** GET /api/experiments/{id} : contrôles, explications, équation, défis, contre-exemples. */
  experiment(id: string, opts: CallOptions = {}): Promise<ExperimentSpec> {
    return cached(`exp:${id}`, () => request('GET', `/api/experiments/${encodeURIComponent(id)}`, undefined, opts))
  },

  /** POST /api/run : l'état doit être canonique (state.ts) pour profiter du cache. */
  run(req: RunRequest, opts: CallOptions = {}): Promise<RunResult> {
    return cached(`run:${JSON.stringify(req)}`, () => request('POST', '/api/run', req, opts))
  },

  /** POST /api/sweep : Sensibilité (1 axe), Domaine de validité (2 axes, P1). */
  sweep(req: SweepRequest, opts: CallOptions = {}): Promise<SweepResult> {
    return cached(`sweep:${JSON.stringify(req)}`, () =>
      request('POST', '/api/sweep', req, { ...opts, timeoutMs: TIMEOUT_MS.long }),
    )
  },

  /** POST /api/training/session : une série vérifiée (seed absente : le serveur en tire une). */
  trainingSession(req: TrainingRequest, opts: CallOptions = {}): Promise<TrainingSessionResponse> {
    return request('POST', '/api/training/session', req, { ...opts, timeoutMs: TIMEOUT_MS.long })
  },

  /** POST /api/validate (P1) : erreurs par numéro de ligne et tests scientifiques. */
  validate(req: ValidateRequest, opts: CallOptions = {}): Promise<ValidateResponse> {
    return request('POST', '/api/validate', req, { ...opts, timeoutMs: TIMEOUT_MS.long })
  },
}

// ---------------------------------------------------------------------------
// Dernier appel seulement (glissement de curseur)
// ---------------------------------------------------------------------------

export interface Latest<Req, Res> {
  /**
   * Programme un appel. Les appels rapprochés (moins de `delayMs`) sont regroupés : seul le dernier
   * part. Un appel en cours est annulé quand un plus récent part. La promesse d'un appel remplacé se
   * résout avec null (rien à afficher) ; celle du dernier, avec la réponse ; une erreur réelle est levée.
   */
  call(req: Req): Promise<Res | null>
  /** Annule tout (appel programmé et appel en cours), par exemple en quittant la page. */
  cancel(): void
}

export function createLatest<Req, Res>(
  fn: (req: Req, opts: CallOptions) => Promise<Res>,
  delayMs = 100,
): Latest<Req, Res> {
  let timer: ReturnType<typeof setTimeout> | null = null
  let pendingResolve: ((v: Res | null) => void) | null = null
  let inflight: AbortController | null = null
  let generation = 0

  function cancel(): void {
    if (timer) clearTimeout(timer)
    timer = null
    pendingResolve?.(null)
    pendingResolve = null
    inflight?.abort()
    inflight = null
    generation += 1
  }

  function call(req: Req): Promise<Res | null> {
    // L'appel programmé précédent n'est jamais parti : il est remplacé.
    if (timer) clearTimeout(timer)
    pendingResolve?.(null)
    const mine = ++generation
    return new Promise<Res | null>((resolve, reject) => {
      pendingResolve = resolve
      timer = setTimeout(() => {
        timer = null
        pendingResolve = null
        inflight?.abort() // une réponse plus ancienne n'a plus d'intérêt
        const controller = new AbortController()
        inflight = controller
        fn(req, { signal: controller.signal }).then(
          (res) => resolve(mine === generation ? res : null),
          (err) => {
            if (controller.signal.aborted || mine !== generation) resolve(null)
            else reject(err)
          },
        ).finally(() => {
          if (inflight === controller) inflight = null
        })
      }, delayMs)
    })
  }

  return { call, cancel }
}
