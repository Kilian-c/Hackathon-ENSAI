/**
 * guide.ts : ce que l'étape « Expérimenter » dit en clair à l'étudiant (R3).
 *
 * - labGuide : une phrase « que se passe-t-il ? », les explications des hypothèses relâchées
 *   (when_broken) et l'étape suivante proposée (afficher la correction, tout rétablir...) ;
 * - gauge : la jauge de la mesure principale, découpée en zones Fiable / Fragile / Rompu par la règle
 *   du verdict (CLAUDE.md, section 8), avec la valeur, la cible et la Référence.
 *
 * Règles pures : aucune connaissance d'un théorème, tout vient de ExperimentSpec, EngineState et
 * RunResult. Les mots sont génériques (« la méthode principale », « la correction »).
 */

import { headlineVerdict, isHealthy, methodWithRole, primaryStates } from './lab'
import type { Verdict } from './roles'
import type { EngineState, ExperimentSpec, Hypothesis, MeasureResult, RunResult } from './types.gen'

// ---------------------------------------------------------------------------
// Phrase « que se passe-t-il ? »
// ---------------------------------------------------------------------------

/** Au-delà, les autres hypothèses relâchées sont seulement comptées. */
export const MAX_CAUSES = 2

export interface GuideCause {
  id: string
  label: string
  text: string
}

export interface LabGuide {
  /** Verdict de la méthode principale sur la mesure primaire (null : pas de verdict). */
  tone: Verdict | null
  headline: string
  /** Hypothèses relâchées (MAX_CAUSES au plus), avec leur when_broken. */
  causes: GuideCause[]
  /** Hypothèses relâchées en plus de celles de `causes`. */
  moreCauses: number
  /** Phrase de contexte quand rien n'explique le verdict par une hypothèse. */
  context: string | null
  /** Étape suivante proposée, en une phrase. */
  next: string | null
  /** Bouton proposé avec l'étape suivante. */
  action: 'correction' | 'heal' | null
}

type HValue = number | boolean | string

/** L'hypothèse relâchée est-elle de celles auxquelles la méthode doit résister ? (option d'abord) */
export function robustExpected(h: Hypothesis, value: HValue | undefined): boolean {
  if (h.type === 'choice' && typeof value === 'string') {
    const opt = h.options?.[value]
    if (opt?.robust_expected) return true
  }
  return h.robust_expected
}

function quoted(labels: readonly string[]): string {
  return labels.map((l) => `« ${l} »`).join(', ')
}

export function labGuide(
  spec: Pick<ExperimentSpec, 'hypotheses' | 'methods'>,
  engine: Pick<EngineState, 'hypotheses' | 'extra_points'>,
  result: Pick<RunResult, 'measures' | 'methods'>,
  methodsOn: readonly string[],
): LabGuide {
  const tone = headlineVerdict(result)
  const broken = Object.entries(spec.hypotheses).filter(([id, h]) => !isHealthy(h, engine.hypotheses[id]))
  const causes = broken.slice(0, MAX_CAUSES).map(([id, h]) => ({ id, label: h.label, text: h.when_broken }))
  const base = { tone, causes, moreCauses: Math.max(0, broken.length - MAX_CAUSES), context: null }

  if (tone === null) {
    return { ...base, headline: "Cette expérience n'a pas de verdict à afficher.", next: null, action: null }
  }

  if (tone === 'ok') {
    if (broken.length === 0) {
      return {
        ...base,
        headline: 'Tout est sain : la méthode principale est fiable.',
        next: 'Relâchez une hypothèse dans la colonne de gauche et regardez ce qui cède.',
        action: null,
      }
    }
    const robust = broken.every(([id, h]) => robustExpected(h, engine.hypotheses[id]))
    return robust
      ? {
          ...base,
          headline: `La méthode principale reste fiable : elle résiste ${broken.length > 1 ? 'à ces hypothèses' : 'à cette hypothèse'}.`,
          next: 'Essayez une autre hypothèse pour voir laquelle compte vraiment.',
          action: null,
        }
      : {
          ...base,
          headline: 'La méthode principale tient encore.',
          next: "Accentuez la rupture, ou changez un paramètre, pour voir à partir d'où elle cède.",
          action: null,
        }
  }

  const headline = tone === 'warning' ? 'La méthode principale devient fragile.' : 'La méthode principale est rompue.'
  const context =
    broken.length === 0
      ? `Aucune hypothèse n'est relâchée : ce sont les réglages (paramètres${engine.extra_points.length > 0 ? ', points posés' : ''}) qui font céder la méthode.`
      : null

  const correction = methodWithRole(spec.methods, 'correction')
  if (!correction) {
    return {
      ...base,
      headline,
      context,
      next:
        broken.length > 0
          ? "Aucune correction n'est prévue ici : rétablissez les hypothèses, ou jouez sur les paramètres, pour revenir à un verdict fiable."
          : "Aucune correction n'est prévue ici : ramenez les paramètres vers leur valeur par défaut.",
      action: broken.length > 0 ? 'heal' : null,
    }
  }

  if (!methodsOn.includes(correction.id)) {
    return {
      ...base,
      headline,
      context,
      next: `Affichez la correction, « ${correction.label} », pour voir si elle répare.`,
      action: 'correction',
    }
  }

  const fixed = primaryStates(result)[correction.id] ?? null
  const unrepaired = broken.filter(([id]) => !correction.repairs.includes(id)).map(([, h]) => h.label)
  const notFor = unrepaired.length > 0 ? ` Elle n'est pas faite pour ${quoted(unrepaired)}.` : ''
  const next =
    fixed === 'ok'
      ? 'La correction répare : elle retrouve un verdict fiable. Comparez les deux méthodes sur le graphique.'
      : fixed === 'warning'
        ? `La correction limite les dégâts, mais reste fragile ici.${notFor}`
        : `Même la correction ne suffit pas ici.${notFor}`
  return { ...base, headline, context, next, action: null }
}

// ---------------------------------------------------------------------------
// Jauge de la mesure principale
// ---------------------------------------------------------------------------

/** Une zone de la jauge, en fraction de sa longueur (0 à 1). */
export interface GaugeZone {
  from: number
  to: number
  verdict: Verdict
}

export interface Gauge {
  zones: GaugeZone[]
  /** Positions sur la jauge (0 à 1), null si la valeur manque. */
  value: number | null
  target: number
  baseline: number | null
}

export type GaugeMeasure = Pick<
  MeasureResult,
  'target' | 'direction' | 'ok_within' | 'broken_beyond' | 'values' | 'baseline' | 'unit' | 'scale'
>

function finite(v: number | null | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/** Cible de la mesure pour une méthode (`base` : la valeur de cette méthode à l'état sain). */
export function targetFor(m: GaugeMeasure, methodId: string): number | null {
  if (m.target === 'base') return m.baseline[methodId] ?? null
  return finite(m.target) ? m.target : null
}

/** Bornes des zones (en unité brute), dans l'ordre, pour une cible donnée. */
function zoneBreaks(m: GaugeMeasure, t: number): { at: [number, number]; verdict: Verdict }[] | null {
  const ok = m.ok_within
  const bb = m.broken_beyond
  if (!finite(ok) || !finite(bb) || !m.direction) return null
  const inf = Number.NEGATIVE_INFINITY
  const sup = Number.POSITIVE_INFINITY
  switch (m.direction) {
    case 'below':
      return [
        { at: [inf, t - bb], verdict: 'broken' },
        { at: [t - bb, t - ok], verdict: 'warning' },
        { at: [t - ok, sup], verdict: 'ok' },
      ]
    case 'above':
      return [
        { at: [inf, t + ok], verdict: 'ok' },
        { at: [t + ok, t + bb], verdict: 'warning' },
        { at: [t + bb, sup], verdict: 'broken' },
      ]
    case 'both':
      return [
        { at: [inf, t - bb], verdict: 'broken' },
        { at: [t - bb, t - ok], verdict: 'warning' },
        { at: [t - ok, t + ok], verdict: 'ok' },
        { at: [t + ok, t + bb], verdict: 'warning' },
        { at: [t + bb, sup], verdict: 'broken' },
      ]
  }
}

/**
 * Bornes communes des jauges (en unité brute) pour les méthodes affichées : les zones autour de la
 * cible (deux fois le seuil de rupture du côté grave), élargies pour contenir chaque valeur et chaque
 * Référence. Un pourcentage (`%`, échelle 100) reste dans [0, 1] tant que les valeurs y sont.
 * null : la mesure n'a pas de cible ou pas de seuils (mesure informative).
 */
export function gaugeDomain(m: GaugeMeasure, methodIds: readonly string[]): [number, number] | null {
  let lo = Number.POSITIVE_INFINITY
  let hi = Number.NEGATIVE_INFINITY
  const points: number[] = []
  for (const id of methodIds) {
    const t = targetFor(m, id)
    if (t === null || !zoneBreaks(m, t)) continue
    const ok = m.ok_within as number
    const bb = m.broken_beyond as number
    const below = m.direction === 'above' ? Math.max(ok, bb / 2) : 2 * bb
    const above = m.direction === 'below' ? Math.max(ok, bb / 2) : 2 * bb
    lo = Math.min(lo, t - below)
    hi = Math.max(hi, t + above)
    for (const v of [m.values[id], m.baseline[id]]) if (finite(v)) points.push(v)
  }
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return null
  if (m.unit === '%' && m.scale === 100) {
    lo = Math.max(lo, 0)
    hi = Math.min(hi, 1)
  }
  const pmin = Math.min(...points, lo)
  const pmax = Math.max(...points, hi)
  const span = Math.max(pmax - pmin, 1e-9)
  // Une valeur hors des zones : un peu de marge pour que son repère ne colle pas au bord.
  if (pmin < lo) lo = pmin - 0.05 * span
  if (pmax > hi) hi = pmax + 0.05 * span
  if (hi - lo < 1e-9) hi = lo + 1
  return [lo, hi]
}

/** La jauge d'une méthode sur la mesure, dans les bornes `domain` (gaugeDomain). */
export function gauge(m: GaugeMeasure, methodId: string, domain: readonly [number, number]): Gauge | null {
  const t = targetFor(m, methodId)
  if (t === null) return null
  const breaks = zoneBreaks(m, t)
  if (!breaks) return null
  const [lo, hi] = domain
  const pos = (v: number): number => Math.min(1, Math.max(0, (v - lo) / (hi - lo)))
  const zones = breaks
    .map((z) => ({ from: pos(z.at[0]), to: pos(z.at[1]), verdict: z.verdict }))
    .filter((z) => z.to - z.from > 1e-9)
  const value = m.values[methodId]
  const baseline = m.baseline[methodId]
  return {
    zones,
    value: finite(value) ? pos(value) : null,
    target: pos(t),
    baseline: finite(baseline) ? pos(baseline) : null,
  }
}
