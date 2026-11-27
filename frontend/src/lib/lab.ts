/**
 * lab.ts : règles pures du Laboratoire (R3). Aucune connaissance d'un théorème : tout vient de
 * ExperimentSpec (le YAML validé) et de RunResult.
 */

import type { MethodRole, Verdict } from './roles'
import type { EngineState, ExperimentSpec, Hypothesis, MethodInfo, RunResult, SweepRequest } from './types.gen'
import type { UiState } from './state'
import { canonicalState, injectAxes, MAX_EXTRA_POINTS } from './state'

type HValue = number | boolean | string

/** Identifiant de la mesure primaire (une seule par expérience), ou null. */
export function primaryMeasureId(result: Pick<RunResult, 'measures'>): string | null {
  const hit = Object.entries(result.measures).find(([, m]) => m.primary)
  return hit ? hit[0] : null
}

/** Verdicts de la mesure primaire, par méthode (pour l'équation et le badge). */
export function primaryStates(result: Pick<RunResult, 'measures'>): Record<string, Verdict> {
  const id = primaryMeasureId(result)
  return id ? { ...result.measures[id].states } : {}
}

export function methodWithRole<M extends { role: MethodRole }>(methods: readonly M[], role: MethodRole): M | null {
  return methods.find((m) => m.role === role) ?? null
}

/** Verdict de la méthode principale sur la mesure primaire (badge de l'en-tête), ou null. */
export function headlineVerdict(result: Pick<RunResult, 'measures' | 'methods'>): Verdict | null {
  const principal = methodWithRole(result.methods, 'method')
  return principal ? (primaryStates(result)[principal.id] ?? null) : null
}

/** Afficher ou masquer une méthode : aucun appel au moteur. La méthode principale reste affichée. */
export function toggleMethod(spec: Pick<ExperimentSpec, 'methods'>, ui: UiState, id: string): UiState {
  const principal = methodWithRole(spec.methods, 'method')
  if (principal?.id === id) return ui
  const on = new Set(ui.methodsOn)
  if (on.has(id)) on.delete(id)
  else on.add(id)
  // Ordre du YAML, pour que le lien de partage soit stable.
  return { ...ui, methodsOn: spec.methods.map((m) => m.id).filter((m) => on.has(m)) }
}

/** L'hypothèse est-elle à sa valeur saine ? */
export function isHealthy(h: Hypothesis, value: HValue | undefined): boolean {
  return value === undefined || value === h.healthy_value
}

/**
 * Valeur « cassée » d'une hypothèse, pour le clic dans le panneau Comprendre : l'autre bout du
 * curseur, l'autre position de l'interrupteur, ou la première option qui n'est pas saine.
 */
export function brokenValue(h: Hypothesis): HValue {
  switch (h.type) {
    case 'boolean':
      return !h.healthy_value
    case 'choice': {
      const other = Object.keys(h.options ?? {}).find((k) => k !== h.healthy_value)
      return other ?? h.healthy_value
    }
    case 'continuous': {
      const [min, max] = h.range ?? [0, 1]
      return h.healthy_value === min ? max : min
    }
  }
}

/** Libellé d'état d'une hypothèse (« Respectée » / « Relâchée », ou le nom de l'option choisie). */
export function hypothesisStatus(h: Hypothesis, value: HValue | undefined): string {
  if (h.type === 'choice' && typeof value === 'string') return h.options?.[value]?.label ?? value
  return isHealthy(h, value) ? (h.ok_label ?? 'Respectée') : (h.broken_label ?? 'Relâchée')
}

/** Modifie une valeur de l'état de calcul (hypothèse ou paramètre), sans toucher à la graine. */
export function setValue(
  spec: ExperimentSpec,
  state: EngineState,
  kind: 'h' | 'p',
  id: string,
  value: HValue,
): EngineState {
  return kind === 'h'
    ? canonicalState(spec, { ...state, hypotheses: { ...state.hypotheses, [id]: value } })
    : canonicalState(spec, { ...state, params: { ...state.params, [id]: value as number | boolean } })
}

/** Remet toutes les hypothèses à leur valeur saine (paramètres et graine conservés). */
export function healAll(spec: ExperimentSpec, state: EngineState): EngineState {
  return canonicalState(spec, { ...state, hypotheses: {}, extra_points: [] })
}

/**
 * Requête de balayage d'une vue Sensibilité. L'axe balayé est remis à sa valeur saine (ou par défaut)
 * dans l'état envoyé : bouger le curseur de cet axe ne relance donc pas le balayage, seul le
 * marqueur « état actuel » se déplace (SweepResult.current est remplacé côté interface).
 */
export function sweepRequest(
  spec: ExperimentSpec,
  state: EngineState,
  targets: readonly string[],
  measure: string | null,
): SweepRequest {
  let base: EngineState = state
  for (const t of targets) {
    const [kind, id] = t.split('.', 2)
    if (kind === 'h') base = { ...base, hypotheses: { ...base.hypotheses, [id]: spec.hypotheses[id]?.healthy_value } }
    else if (kind === 'p') base = { ...base, params: { ...base.params, [id]: spec.params[id]?.default } }
  }
  base = canonicalState(spec, base)
  const [first, ...rest] = targets
  return { experiment_id: spec.id, state: base, measure, axes: [{ target: first }, ...rest.map((target) => ({ target }))] }
}

/** Valeur actuelle de chaque axe balayé, lue dans l'état (pour le marqueur de la Sensibilité). */
export function currentOnAxes(state: EngineState, targets: readonly string[]): Record<string, HValue> {
  const out: Record<string, HValue> = {}
  for (const t of targets) {
    const [kind, id] = t.split('.', 2)
    const v = kind === 'h' ? state.hypotheses[id] : kind === 'p' ? state.params[id] : undefined
    if (v !== undefined) out[t] = v
  }
  return out
}

/**
 * Titre de l'axe d'un balayage (« h.hetero », « p.n ») à partir des libellés du YAML. Une hypothèse
 * continue ajoute « : h », la notation de son curseur. Cible inconnue : renvoyée telle quelle.
 */
export function axisTitle(spec: Pick<ExperimentSpec, 'hypotheses' | 'params'>, target: string): string {
  const [kind, id] = target.split('.', 2)
  if (kind === 'h') {
    const h = spec.hypotheses[id]
    if (h) return h.type === 'continuous' ? `${h.label} : h` : h.label
  }
  if (kind === 'p') return spec.params[id]?.label ?? target
  return target
}

/** Libellés des méthodes, pour les légendes. */
export function methodLabels(methods: readonly Pick<MethodInfo, 'id' | 'label'>[]): Record<string, string> {
  return Object.fromEntries(methods.map((m) => [m.id, m.label]))
}

// ---------------------------------------------------------------------------
// Ajout de points par clic (P1, fiche F « Ajout de points par clic »)
// ---------------------------------------------------------------------------

/** La vue accepte-t-elle des points posés au clic ? (YAML : allow_point_injection et generator.inject) */
export function allowsPoints(spec: ExperimentSpec, viewId: string | null): boolean {
  if (!viewId || injectAxes(spec).length === 0) return false
  return spec.views.some((v) => v.id === viewId && v.allow_point_injection)
}

/** Points posés, en coordonnées de la vue (axe x, et y s'il fait partie de generator.inject). */
export function viewPoints(spec: ExperimentSpec, state: EngineState): { x: number; y: number | null }[] {
  const axes = injectAxes(spec)
  if (!axes.includes('x')) return []
  return state.extra_points.map((pt) => ({ x: pt.x, y: axes.includes('y') ? pt.y : null }))
}

/** Arrondi d'une coordonnée posée au clic : un lien de partage court, sans bruit de pixels. */
function roundCoord(v: number): number {
  return Math.round(v * 1000) / 1000 || 0
}

/** Pose un point ; null si le plafond (20 points) est atteint. Les axes absents de inject sont ignorés. */
export function addPoint(spec: ExperimentSpec, state: EngineState, at: { x: number; y: number }): EngineState | null {
  if (state.extra_points.length >= MAX_EXTRA_POINTS) return null
  const axes = injectAxes(spec)
  const coords: Record<string, number> = { x: at.x, y: at.y }
  const point = Object.fromEntries(axes.map((a) => [a, roundCoord(coords[a] ?? 0)]))
  return canonicalState(spec, { ...state, extra_points: [...state.extra_points, point] })
}

/** Retire le point posé d'indice `index`. */
export function removePoint(spec: ExperimentSpec, state: EngineState, index: number): EngineState {
  return canonicalState(spec, { ...state, extra_points: state.extra_points.filter((_, i) => i !== index) })
}

/** Retire tous les points posés. */
export function clearPoints(spec: ExperimentSpec, state: EngineState): EngineState {
  return canonicalState(spec, { ...state, extra_points: [] })
}
