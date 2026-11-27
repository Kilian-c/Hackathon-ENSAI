/**
 * state.ts : état de calcul, état d'affichage, forme canonique et lien de partage (R3).
 * Cahier, sections 2.6 et 4.10 ; CLAUDE.md, sections 8 et 10.
 *
 * Deux états bien séparés :
 * - EngineState (contrat) : paramètres, hypothèses, points ajoutés, graine. C'est le SEUL qui part
 *   au moteur et qui change le résultat.
 * - UiState : méthodes affichées, onglet. Il ne quitte jamais l'interface (aucun appel au moteur).
 * Les deux tiennent dans l'URL, pour qu'un état se partage par un simple lien.
 *
 * Règles :
 * - forme canonique : valeurs par défaut complétées, clés inconnues retirées, nombres bornés et arrondis
 *   au pas du contrôle, clés triées. Deux états équivalents donnent la même requête (et le même cache) ;
 * - la graine ne change JAMAIS quand on bouge un curseur : seul nextDraw() l'incrémente ;
 * - un lien d'une version inconnue (v ≠ 1) est refusé avec un message clair.
 */

import type { EngineState, ExperimentSpec, Hypothesis, Param } from './types.gen'

export const LINK_VERSION = 1
export const DEFAULT_SEED = 42
export const MAX_EXTRA_POINTS = 20

/** État d'affichage : jamais envoyé au moteur. */
export interface UiState {
  /** Méthodes affichées (méthode principale seule par défaut ; la Correction s'ajoute au clic). */
  methodsOn: string[]
  /** Onglet ouvert du Laboratoire (identifiant de vue), null = premier onglet. */
  tab: string | null
}

type Value = number | boolean | string

// ---------------------------------------------------------------------------
// Valeurs par défaut et forme canonique
// ---------------------------------------------------------------------------

/** Arrondi au pas, sans les erreurs flottantes (0.1 + 0.2) : au plus 10 décimales. */
export function roundToStep(value: number, step: number | null | undefined, origin = 0): number {
  if (!step || step <= 0) return value
  const rounded = origin + Math.round((value - origin) / step) * step
  return Number(rounded.toFixed(10))
}

function clamp(value: number, min: number | null | undefined, max: number | null | undefined): number {
  let v = value
  if (typeof min === 'number') v = Math.max(min, v)
  if (typeof max === 'number') v = Math.min(max, v)
  return v
}

/** Valeur canonique d'un paramètre, ou sa valeur par défaut si la valeur reçue est invalide. */
export function canonicalParam(p: Param, raw: unknown): number | boolean {
  if (p.type === 'boolean') return typeof raw === 'boolean' ? raw : p.default
  const n = typeof raw === 'number' && Number.isFinite(raw) ? raw : Number(p.default)
  return roundToStep(clamp(n, p.min, p.max), p.step, p.min ?? 0)
}

/** Valeur canonique d'une hypothèse, ou sa valeur saine si la valeur reçue est invalide. */
export function canonicalHypothesis(h: Hypothesis, raw: unknown): Value {
  switch (h.type) {
    case 'boolean':
      return typeof raw === 'boolean' ? raw : h.healthy_value
    case 'choice':
      return typeof raw === 'string' && h.options && raw in h.options ? raw : h.healthy_value
    case 'continuous': {
      if (typeof raw !== 'number' || !Number.isFinite(raw)) return h.healthy_value
      const [min, max] = h.range ?? [0, 1]
      return roundToStep(clamp(raw, min, max), h.step, min)
    }
  }
}

function sortedRecord<T>(entries: [string, T][]): Record<string, T> {
  return Object.fromEntries(entries.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)))
}

/** Noms des coordonnées d'un point posé au clic (generator.inject), dans l'ordre du YAML. */
export function injectAxes(spec: ExperimentSpec): string[] {
  const inject = 'inject' in spec.generator ? spec.generator.inject : null
  return inject ? Object.keys(inject) : []
}

/** Forme canonique d'un état de calcul (voir l'en-tête). Ne modifie pas l'argument. */
export function canonicalState(spec: ExperimentSpec, state: Partial<EngineState> = {}): EngineState {
  const params = sortedRecord(
    Object.entries(spec.params).map(([id, p]) => [id, canonicalParam(p, state.params?.[id])]),
  )
  const hypotheses = sortedRecord(
    Object.entries(spec.hypotheses).map(([id, h]) => [id, canonicalHypothesis(h, state.hypotheses?.[id])]),
  )
  const axes = injectAxes(spec)
  const extra_points = axes.length === 0
    ? []
    : (state.extra_points ?? [])
        .filter((pt) => axes.every((a) => typeof pt[a] === 'number' && Number.isFinite(pt[a])))
        .slice(0, MAX_EXTRA_POINTS)
        .map((pt) => sortedRecord(axes.map((a) => [a, pt[a]])))
  const seed = Number.isInteger(state.seed) && (state.seed as number) >= 0 ? (state.seed as number) : DEFAULT_SEED
  return { params, hypotheses, extra_points, seed }
}

/** État par défaut d'une expérience : paramètres par défaut, toutes les hypothèses saines. */
export function defaultState(spec: ExperimentSpec, seed = DEFAULT_SEED): EngineState {
  return canonicalState(spec, { seed })
}

/** État d'affichage par défaut : la méthode principale seule (la démo s'ouvre ainsi). */
export function defaultUi(spec: ExperimentSpec): UiState {
  return { methodsOn: spec.methods.filter((m) => m.role === 'method').map((m) => m.id), tab: null }
}

/** Clé stable d'un état canonique (sert au cache de l'interface et à comparer deux états). */
export function stateKey(state: EngineState): string {
  return JSON.stringify(state)
}

/** « Nouveau tirage » : la seule opération qui change la graine. */
export function nextDraw(state: EngineState): EngineState {
  return { ...state, seed: state.seed + 1 }
}

/**
 * Applique un état partiel (contre-exemple, question d'Entraînement) : les valeurs absentes reviennent
 * à l'état sain ou à la valeur par défaut, la graine est conservée, les points ajoutés sont effacés.
 * (Cahier, fiche F.2.)
 */
export function applyPreset(spec: ExperimentSpec, current: EngineState, preset: Partial<EngineState>): EngineState {
  return canonicalState(spec, {
    params: preset.params ?? {},
    hypotheses: preset.hypotheses ?? {},
    extra_points: [],
    seed: current.seed,
  })
}

/** Hypothèses qui ne sont pas à leur valeur saine (pour l'équation, les badges, l'onglet Comprendre). */
export function brokenHypotheses(spec: ExperimentSpec, state: EngineState): string[] {
  return Object.entries(spec.hypotheses)
    .filter(([id, h]) => state.hypotheses[id] !== h.healthy_value)
    .map(([id]) => id)
}

// ---------------------------------------------------------------------------
// Lien de partage (URL)
// ---------------------------------------------------------------------------

/**
 * Ce qu'une URL demande d'ouvrir. Pour le Laboratoire, les valeurs restent du TEXTE tant qu'on n'a
 * pas la spécification de l'expérience : resolveLabLink() les convertit ensuite.
 */
export type Link =
  | { kind: 'home' }
  | { kind: 'error'; message: string }
  | { kind: 'training'; filter: string; seed: number | null }
  | {
      kind: 'lab'
      experimentId: string
      params: Record<string, string>
      hypotheses: Record<string, string>
      points: string | null
      seed: number | null
      on: string[] | null
      tab: string | null
    }

function parseSeed(raw: string | null): number | null {
  if (raw === null || !/^\d+$/.test(raw)) return null
  return Number(raw)
}

/** Lit une URL complète ou sa partie `?...` (location.search). N'a pas besoin du moteur. */
export function parseLink(url: string): Link {
  const q = new URLSearchParams(url.includes('?') ? url.slice(url.indexOf('?') + 1) : url)
  const v = q.get('v')
  if ((q.has('exp') || q.has('train')) && v !== null && v !== String(LINK_VERSION)) {
    return {
      kind: 'error',
      message: `Ce lien a été créé pour une autre version de Crash-Test (version ${v}). Il ne peut pas être ouvert ici : demandez un nouveau lien.`,
    }
  }
  const train = q.get('train')
  if (train) return { kind: 'training', filter: train, seed: parseSeed(q.get('seed')) }
  const exp = q.get('exp')
  if (!exp) return { kind: 'home' }
  const params: Record<string, string> = {}
  const hypotheses: Record<string, string> = {}
  for (const [key, value] of q) {
    if (key.startsWith('p.')) params[key.slice(2)] = value
    else if (key.startsWith('h.')) hypotheses[key.slice(2)] = value
  }
  const on = q.get('on')
  return {
    kind: 'lab',
    experimentId: exp,
    params,
    hypotheses,
    points: q.get('pts'),
    seed: parseSeed(q.get('seed')),
    on: on === null ? null : on.split(',').filter(Boolean),
    tab: q.get('tab'),
  }
}

function parseBool(raw: string): boolean | undefined {
  if (raw === '1' || raw === 'true') return true
  if (raw === '0' || raw === 'false') return false
  return undefined
}

function parseNumber(raw: string): number | undefined {
  const n = Number(raw.replace(',', '.'))
  return raw.trim() !== '' && Number.isFinite(n) ? n : undefined
}

/** Points ajoutés : « 4.2,-2.0;5.1,3.3 », une coordonnée par axe de generator.inject. */
export function parsePoints(raw: string | null, axes: string[]): EngineState['extra_points'] {
  if (!raw || axes.length === 0) return []
  return raw
    .split(';')
    .map((chunk) => chunk.split(',').map(Number))
    .filter((coords) => coords.length === axes.length && coords.every(Number.isFinite))
    .map((coords) => Object.fromEntries(axes.map((a, i) => [a, coords[i]])))
}

/** Convertit un lien de Laboratoire en états, avec la spécification (valeurs invalides ignorées). */
export function resolveLabLink(
  spec: ExperimentSpec,
  link: Extract<Link, { kind: 'lab' }>,
): { engine: EngineState; ui: UiState } {
  const params: Record<string, number | boolean> = {}
  for (const [id, raw] of Object.entries(link.params)) {
    const p = spec.params[id]
    const v = p?.type === 'boolean' ? parseBool(raw) : p ? parseNumber(raw) : undefined
    if (v !== undefined) params[id] = v
  }
  const hypotheses: Record<string, Value> = {}
  for (const [id, raw] of Object.entries(link.hypotheses)) {
    const h = spec.hypotheses[id]
    const v = !h ? undefined : h.type === 'boolean' ? parseBool(raw) : h.type === 'continuous' ? parseNumber(raw) : raw
    if (v !== undefined) hypotheses[id] = v
  }
  const engine = canonicalState(spec, {
    params,
    hypotheses,
    extra_points: parsePoints(link.points, injectAxes(spec)),
    seed: link.seed ?? DEFAULT_SEED,
  })
  const known = new Set(spec.methods.map((m) => m.id))
  const ui = defaultUi(spec)
  const on = link.on?.filter((id) => known.has(id))
  return { engine, ui: { methodsOn: on && on.length > 0 ? on : ui.methodsOn, tab: link.tab } }
}

function formatValue(v: Value): string {
  return typeof v === 'boolean' ? (v ? '1' : '0') : String(v)
}

/**
 * URL lisible d'un état de Laboratoire. Seules les valeurs qui diffèrent du défaut sont écrites,
 * pour que le lien reste court et se tape en démo : ?exp=regression-lineaire&v=1&h.hetero=0.85&seed=42
 */
export function labLink(spec: ExperimentSpec, engine: EngineState, ui: UiState): string {
  const base = defaultState(spec)
  const q = new URLSearchParams({ exp: spec.id, v: String(LINK_VERSION) })
  for (const [id, v] of Object.entries(engine.params)) if (v !== base.params[id]) q.set(`p.${id}`, formatValue(v))
  for (const [id, v] of Object.entries(engine.hypotheses)) {
    if (v !== base.hypotheses[id]) q.set(`h.${id}`, formatValue(v))
  }
  q.set('seed', String(engine.seed))
  const defaultOn = defaultUi(spec).methodsOn
  if (ui.methodsOn.join(',') !== defaultOn.join(',')) q.set('on', ui.methodsOn.join(','))
  if (ui.tab) q.set('tab', ui.tab)
  const axes = injectAxes(spec)
  if (engine.extra_points.length > 0) {
    q.set('pts', engine.extra_points.map((pt) => axes.map((a) => pt[a]).join(',')).join(';'))
  }
  // Virgules, points-virgules et points restent lisibles dans le lien.
  return `?${q.toString().replace(/%2C/g, ',').replace(/%3B/g, ';')}`
}

/** URL d'une série d'Entraînement : ?train=<filtre>&seed=<graine>&v=1 */
export function trainingLink(filter: string, seed: number): string {
  return `?train=${encodeURIComponent(filter)}&seed=${seed}&v=${LINK_VERSION}`
}
