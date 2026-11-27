/**
 * lab.ts : règles pures du Laboratoire (R3). Aucune connaissance d'un théorème : tout vient de
 * ExperimentSpec (le YAML validé) et de RunResult.
 */

import type { MethodRole, Verdict } from './roles'
import type { EngineState, ExperimentSpec, Hypothesis, MethodInfo, RunResult, SweepRequest } from './types.gen'
import type { UiState } from './state'
import { canonicalState } from './state'

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

/** Libellés des méthodes, pour les légendes. */
export function methodLabels(methods: readonly Pick<MethodInfo, 'id' | 'label'>[]): Record<string, string> {
  return Object.fromEntries(methods.map((m) => [m.id, m.label]))
}
