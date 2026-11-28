/**
 * calibration.ts : les chiffres de l'écran Bilan (fichier de R4). Cahier, section 2.4 et annexe du
 * score de Brier ; CLAUDE.md, section 10.
 *
 * Fonctions pures sur l'historique de l'Entraînement (lib/training.ts) : score de Brier, réussite par
 * cran, décomposition de Murphy, courbe de calibration et profil de démonstration.
 */

import { CONFIDENCE_LEVELS, HISTORY_KEY, type Answer, type ConfidenceLevel, type History, type Store } from './training'
import type { ViewResult } from './views'

/** Nombre de réponses à partir duquel la courbe (et le diagnostic) ont un sens. */
export const MIN_FOR_CURVE = 20

/** Écart moyen entre confiance et réussite en dessous duquel on se dit bien calibré. */
export const CALIBRATED_WITHIN = 0.1

const KNOWN_LEVELS = new Set<string>(CONFIDENCE_LEVELS.map((l) => l.id))

/**
 * Toutes les réponses enregistrées, de la plus ancienne à la plus récente. Entrées abîmées écartées,
 * y compris un cran inconnu : sinon la réponse compterait dans le score sans apparaître sur aucun bouton.
 */
export function allAnswers(history: History): Answer[] {
  return Object.values(history.series)
    .flatMap((s) => (Array.isArray(s?.answers) ? s.answers : []))
    .filter(
      (a) =>
        typeof a?.correct === 'boolean' &&
        KNOWN_LEVELS.has(a.level) &&
        Number.isFinite(a.p) &&
        a.p >= 0 &&
        a.p <= 1,
    )
    .sort((a, b) => String(a.at).localeCompare(String(b.at)))
}

/**
 * Efface l'historique de l'Entraînement (réponses du Bilan et reprise des séries en cours), et lui seul :
 * le brouillon de l'Import est gardé. false si le navigateur refuse l'écriture (rien n'est alors effacé).
 */
export function clearHistory(store: Store | null): boolean {
  if (!store) return false
  const empty: History = { version: 1, series: {} }
  try {
    store.setItem(HISTORY_KEY, JSON.stringify(empty))
    return true
  } catch {
    return false
  }
}

const mean = (xs: readonly number[]): number => xs.reduce((s, x) => s + x, 0) / xs.length
const successRate = (answers: readonly Answer[]): number => mean(answers.map((a) => (a.correct ? 1 : 0)))

export interface Summary {
  count: number
  correct: number
  /** Part de bonnes réponses. */
  success: number
  /** Confiance annoncée moyenne. */
  confidence: number
  /** Score de Brier : 0 parfait, 1 le pire. */
  brier: number
}

export function summarize(answers: readonly Answer[]): Summary | null {
  if (answers.length === 0) return null
  return {
    count: answers.length,
    correct: answers.filter((a) => a.correct).length,
    success: successRate(answers),
    confidence: mean(answers.map((a) => a.p)),
    brier: mean(answers.map((a) => (a.p - (a.correct ? 1 : 0)) ** 2)),
  }
}

export interface LevelStat {
  level: ConfidenceLevel
  label: string
  count: number
  correct: number
  /** null quand le cran n'a jamais été choisi. */
  success: number | null
  /** Probabilité moyenne annoncée avec ce cran (elle dépend du nombre de choix). */
  confidence: number | null
}

/** Réussite par bouton de confiance, dans l'ordre des boutons. */
export function levelStats(answers: readonly Answer[]): LevelStat[] {
  return CONFIDENCE_LEVELS.map(({ id, label }) => {
    const group = answers.filter((a) => a.level === id)
    const empty = group.length === 0
    return {
      level: id,
      label,
      count: group.length,
      correct: group.filter((a) => a.correct).length,
      success: empty ? null : successRate(group),
      confidence: empty ? null : mean(group.map((a) => a.p)),
    }
  })
}

export type Tendency = 'over' | 'under' | 'calibrated'

/** Trop sûr, trop prudent ou bien calibré, d'après l'écart global entre confiance et réussite. */
export function tendency(confidence: number, success: number): Tendency {
  const gap = confidence - success
  if (gap > CALIBRATED_WITHIN) return 'over'
  return gap < -CALIBRATED_WITHIN ? 'under' : 'calibrated'
}

/** Le cran mis en avant par la phrase d'accroche : « Certain » s'il a servi, sinon le suivant. */
export function headlineLevel(stats: readonly LevelStat[]): LevelStat | null {
  return [...stats].reverse().find((s) => s.count > 0) ?? null
}

export interface Murphy {
  /** Écart entre confiance et réussite (à minimiser). */
  calibration: number
  /** Capacité à distinguer ce que l'on sait de ce que l'on ignore (à maximiser). */
  resolution: number
  /** Difficulté des questions. */
  uncertainty: number
}

/** Brier = calibration − résolution + incertitude, les réponses étant groupées par valeur de p. */
export function murphy(answers: readonly Answer[]): Murphy | null {
  if (answers.length === 0) return null
  const overall = successRate(answers)
  const groups = new Map<number, Answer[]>()
  for (const a of answers) groups.set(a.p, [...(groups.get(a.p) ?? []), a])
  let calibration = 0
  let resolution = 0
  for (const [p, group] of groups) {
    const observed = successRate(group)
    const weight = group.length / answers.length
    calibration += weight * (p - observed) ** 2
    resolution += weight * (observed - overall) ** 2
  }
  return { calibration, resolution, uncertainty: overall * (1 - overall) }
}

export interface ExperimentStat extends Summary {
  id: string
  /** Réponses fausses données en cliquant « Certain ». */
  sureMistakes: number
}

/** Une ligne par expérience, la moins bien maîtrisée (Brier le plus haut) en premier. */
export function experimentStats(answers: readonly Answer[]): ExperimentStat[] {
  const ids = [...new Set(answers.map((a) => a.experimentId))]
  return ids
    .map((id) => {
      const group = answers.filter((a) => a.experimentId === id)
      return {
        id,
        ...(summarize(group) as Summary),
        sureMistakes: group.filter((a) => a.level === 'sure' && !a.correct).length,
      }
    })
    .sort((a, b) => b.brier - a.brier)
}

/**
 * La courbe de calibration, au format d'une vue pour PlotlyChart : la diagonale (calibration parfaite)
 * et un point par bouton utilisé, en pourcentages.
 */
export function calibrationView(stats: readonly LevelStat[]): ViewResult {
  const used = stats.filter((s) => s.success !== null && s.confidence !== null)
  const empty = { method: null, layer: null, low: null, high: null, hit: null, value: null, paths: null }
  const x = used.map((s) => (s.confidence as number) * 100)
  const y = used.map((s) => (s.success as number) * 100)
  return {
    id: 'bilan-calibration',
    type: 'scatter',
    title: 'Courbe de calibration',
    mode: null,
    axes: { x: [0, 105], y: [-5, 112] },
    shown: used.length,
    total: used.length,
    clipped: 0,
    ui: {
      x_title: 'Confiance annoncée (%)',
      y_title: 'Réussite réelle (%)',
      marker_size: 14,
      point_labels: used.map((s) => s.label),
    },
    series: [
      { ...empty, id: 'bilan.series.ideal', slot: 'series', role: 'reference', label: 'Calibration parfaite', x: [0, 100], y: [0, 100] },
      { ...empty, id: 'bilan.series.vous', slot: 'series', role: 'method', label: 'Votre courbe', x, y },
      { ...empty, id: 'bilan.points.vous', slot: 'points', role: 'method', label: 'Vos boutons', x, y },
    ],
  }
}

/**
 * Profil de démonstration (soutenance) : 32 réponses d'un étudiant trop sûr de lui. Il n'est jamais
 * enregistré. Les réponses sont réparties entre les expériences fournies.
 */
export function demoAnswers(experimentIds: readonly string[]): Answer[] {
  const ids = experimentIds.length > 0 ? experimentIds : ['demonstration']
  // [cran, nombre de réponses, dont justes]
  const plan: [ConfidenceLevel, number, number][] = [
    ['sure', 20, 12],
    ['fair', 8, 3],
    ['guess', 4, 1],
  ]
  const out: Answer[] = []
  for (const [level, count, right] of plan) {
    for (let i = 0; i < count; i++) {
      const n = out.length
      const k = n % 2 === 0 ? 2 : 4
      const p = level === 'sure' ? 0.95 : level === 'guess' ? 1 / k : (1 / k + 0.95) / 2
      // Les bonnes réponses sont étalées sur le cran, donc sur les expériences.
      const correct = Math.floor(((i + 1) * right) / count) > Math.floor((i * right) / count)
      out.push({
        qid: `demo/${n}`,
        experimentId: ids[n % ids.length],
        type: 'misconception',
        choiceId: 'a',
        correct,
        level,
        p,
        at: new Date(Date.UTC(2026, 0, 1, 0, n)).toISOString(),
      })
    }
  }
  return out
}
