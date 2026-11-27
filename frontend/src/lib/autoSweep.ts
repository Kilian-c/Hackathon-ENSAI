/**
 * autoSweep.ts : règles pures du balayage automatique (R3, P1). Cahier, annexe F, fiche
 * « Balayage automatique ». Aucune connaissance d'un théorème : tout vient de `auto_sweep` du YAML,
 * de la réponse de /api/sweep (grille et seuil critique) et des verdicts de /api/run.
 *
 * Déroulé (AutoSweepPlayer.svelte) : un appel à /api/sweep donne la grille et `critical.warning_at`,
 * puis un /api/run par valeur (préchargé avant le départ), joué à 600 ms par image ; pause de 2 s
 * sur la première valeur supérieure ou égale au seuil critique ; à la fin, la Correction s'active
 * pour une hypothèse, et une phrase conclut pour un paramètre.
 */

import { methodWithRole, setValue } from './lab'
import { verdictLabel, type Verdict } from './roles'
import type { UiState } from './state'
import type { EngineState, ExperimentSpec, SweepResult } from './types.gen'

export const FRAME_MS = 600
export const PAUSE_MS = 2000

type Value = number | boolean | string

/** Contrôles animables de l'expérience, dans l'ordre des boutons ; ceux qui n'existent pas sont ignorés. */
export function animatable(spec: Pick<ExperimentSpec, 'auto_sweep' | 'hypotheses' | 'params'>): string[] {
  return (spec.auto_sweep ?? []).filter((t) => {
    const [kind, id] = t.split('.', 2)
    if (kind === 'h') return id in spec.hypotheses
    if (kind === 'p') return (spec.params[id]?.sweep_values?.length ?? 0) > 0
    return false
  })
}

/** États de calcul successifs : l'état actuel, avec le contrôle balayé à chaque valeur de la grille. */
export function frameStates(spec: ExperimentSpec, state: EngineState, target: string, sweep: Pick<SweepResult, 'axes'>): EngineState[] {
  const axis = sweep.axes.find((a) => a.target === target) ?? sweep.axes[0]
  if (!axis) return []
  const [kind, id] = target.split('.', 2) as ['h' | 'p', string]
  return axis.values.map((v: Value) => setValue(spec, state, kind, id, v))
}

/**
 * Indice de l'image où l'animation marque une pause : première valeur de la grille supérieure ou
 * égale à `warning_at` de la méthode principale ; null sans seuil critique ou sur un axe non numérique.
 */
export function pauseIndex(sweep: Pick<SweepResult, 'axes' | 'critical'>, principal: string | null): number | null {
  const warningAt = principal ? sweep.critical?.[principal]?.warning_at : null
  const values = sweep.axes[0]?.values ?? []
  if (typeof warningAt !== 'number' || !values.every((v) => typeof v === 'number')) return null
  const i = (values as number[]).findIndex((v) => v >= warningAt - 1e-9)
  return i >= 0 ? i : null
}

/** État d'affichage à la fin : pour une hypothèse, la Correction s'active (jamais pour un paramètre). */
export function endUi(spec: Pick<ExperimentSpec, 'methods'>, ui: UiState, target: string): UiState {
  const correction = methodWithRole(spec.methods, 'correction')
  if (!target.startsWith('h.') || !correction || ui.methodsOn.includes(correction.id)) return ui
  const on = new Set([...ui.methodsOn, correction.id])
  return { ...ui, methodsOn: spec.methods.map((m) => m.id).filter((m) => on.has(m)) }
}

/**
 * Phrase de fin pour un paramètre, selon le verdict de la méthode principale à la première et à la
 * dernière valeur : « … répare » ou « … ne répare pas ». null pour une hypothèse.
 */
export function conclusion(
  spec: Pick<ExperimentSpec, 'params'>,
  target: string,
  labels: readonly string[],
  first: Verdict | null,
  last: Verdict | null,
): string | null {
  const [kind, id] = target.split('.', 2)
  if (kind !== 'p' || !first || !last) return null
  const name = spec.params[id]?.label ?? id
  const from = labels[0] ?? ''
  const to = labels[labels.length - 1] ?? ''
  const range = `« ${name} » de ${from} à ${to}`
  if (first === 'ok' && last === 'ok') return `${range} : la méthode principale reste Fiable sur toute la plage.`
  if (last === 'ok') return `${range} répare : la méthode principale passe de ${verdictLabel(first)} à Fiable.`
  if (first === last) return `${range} ne répare pas : la méthode principale reste ${verdictLabel(last)}.`
  return `${range} ne répare pas : la méthode principale passe de ${verdictLabel(first)} à ${verdictLabel(last)}.`
}
