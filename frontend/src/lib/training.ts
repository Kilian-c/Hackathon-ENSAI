/**
 * training.ts : règles de l'Entraînement et historique des réponses (R3).
 * Cahier, section 2.3 et annexe C.5 ; CLAUDE.md, section 10.
 *
 * Fonctions pures, plus la lecture et l'écriture de l'historique dans localStorage.
 * L'historique est rangé par identifiant de série ; c'est ce que lira l'écran Bilan (R4).
 * Le score de Brier et la calibration ne sont pas calculés ici (lib/calibration.ts, R4).
 */

import { disciplineLabel, joinLabels, selectedFromFilter } from './trainChoice'
import type { TrainingChoice, TrainingQuestion, TrainingSessionResponse } from './types.gen'

export type ConfidenceLevel = keyof TrainingQuestion['confidence']

/** Les trois crans : l'étudiant voit des mots, la probabilité vient de la question. */
export const CONFIDENCE_LEVELS: readonly { id: ConfidenceLevel; label: string }[] = [
  { id: 'guess', label: 'Je devine' },
  { id: 'fair', label: 'Plutôt sûr' },
  { id: 'sure', label: 'Certain' },
]

export function confidenceLabel(level: ConfidenceLevel): string {
  return CONFIDENCE_LEVELS.find((l) => l.id === level)?.label ?? level
}

export interface Answer {
  qid: string
  experimentId: string
  type: TrainingQuestion['type']
  choiceId: string
  correct: boolean
  level: ConfidenceLevel
  /** Probabilité annoncée (le « p » du score de Brier). */
  p: number
  /** Date de la réponse, au format ISO. */
  at: string
}

export interface SeriesRecord {
  filter: string
  seed: number
  contentHash: string
  size: number
  answers: Answer[]
}

export interface History {
  version: 1
  /** Clé : identifiant de série (`<filtre>~<graine>`). */
  series: Record<string, SeriesRecord>
}

export const HISTORY_KEY = 'crash-test.entrainement.v1'

export type Store = Pick<Storage, 'getItem' | 'setItem'>

/** localStorage, ou null quand le navigateur l'interdit (l'Entraînement marche alors sans mémoire). */
export function browserStore(): Store | null {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

const emptyHistory = (): History => ({ version: 1, series: {} })

/** Historique enregistré ; vide si absent, illisible ou d'une autre version. */
export function loadHistory(store: Store | null): History {
  try {
    const raw = store?.getItem(HISTORY_KEY)
    const parsed = raw ? (JSON.parse(raw) as Partial<History> | null) : null
    if (parsed?.version === 1 && typeof parsed.series === 'object' && parsed.series) return parsed as History
  } catch {
    /* historique illisible : on repart de zéro */
  }
  return emptyHistory()
}

function saveHistory(store: Store | null, history: History): void {
  try {
    store?.setItem(HISTORY_KEY, JSON.stringify(history))
  } catch {
    /* stockage plein ou interdit : la série continue en mémoire */
  }
}

/**
 * Réponses déjà données à cette série. Ignorées si le contenu des expériences a changé depuis
 * (même identifiant, questions différentes).
 */
export function storedAnswers(history: History, session: TrainingSessionResponse): Answer[] {
  const record = history.series[session.id]
  if (!record || record.contentHash !== session.content_hash) return []
  const known = new Set(session.questions.map((q) => q.qid))
  return record.answers.filter((a) => known.has(a.qid))
}

/** Ajoute une réponse à la liste. La première réponse à une question est définitive. */
export function addAnswer(answers: readonly Answer[], answer: Answer): Answer[] {
  return answers.some((a) => a.qid === answer.qid) ? [...answers] : [...answers, answer]
}

export function saveAnswers(store: Store | null, session: TrainingSessionResponse, answers: Answer[]): void {
  const history = loadHistory(store)
  history.series[session.id] = {
    filter: session.filter,
    seed: session.seed,
    contentHash: session.content_hash,
    size: session.questions.length,
    answers,
  }
  saveHistory(store, history)
}

export function makeAnswer(q: TrainingQuestion, choiceId: string, level: ConfidenceLevel, now = new Date()): Answer {
  const choice = q.choices.find((c) => c.id === choiceId)
  if (!choice) throw new Error(`Choix inconnu « ${choiceId} » pour la question ${q.qid}.`)
  return {
    qid: q.qid,
    experimentId: q.experiment_id,
    type: q.type,
    choiceId,
    correct: choice.correct,
    level,
    p: q.confidence[level],
    at: now.toISOString(),
  }
}

/** Position de la première question sans réponse ; le nombre de questions quand la série est finie. */
export function firstUnanswered(session: TrainingSessionResponse, answers: readonly Answer[]): number {
  const done = new Set(answers.map((a) => a.qid))
  const i = session.questions.findIndex((q) => !done.has(q.qid))
  return i < 0 ? session.questions.length : i
}

export function correctChoice(q: TrainingQuestion): TrainingChoice {
  return q.choices.find((c) => c.correct) ?? q.choices[0]
}

/**
 * Choix dont l'état est simulé pour la correction : la réponse choisie si elle est juste,
 * sinon la bonne réponse (CLAUDE.md, section 10).
 */
export function revealChoice(q: TrainingQuestion, choiceId: string): TrainingChoice {
  const picked = q.choices.find((c) => c.id === choiceId)
  return picked?.correct ? picked : correctChoice(q)
}

export function seriesTitle(size: number): string {
  return `Série de ${size} ${size > 1 ? 'questions' : 'question'}`
}

export function filterLabel(filter: string): string {
  if (filter === 'toutes') return 'Toutes les expériences'
  if (filter.startsWith('discipline:')) return joinLabels(selectedFromFilter(filter).map(disciplineLabel))
  return 'Une seule expérience'
}

/** Taille d'une série demandée au moteur (il peut en rendre moins s'il n'y a pas assez de questions). */
export const SERIES_SIZE = 10

/**
 * Message quand la série est plus courte que demandée, faute de questions pour ce choix ; null sinon.
 * Aucun contrat n'est en cause : l'interface compare les questions reçues à celles demandées.
 */
export function shortSeriesNotice(received: number, filter: string): string | null {
  if (received <= 0 || received >= SERIES_SIZE) return null
  const label = filterLabel(filter)
  const questions = received > 1 ? 'questions' : 'question'
  const advice = filter === 'toutes' ? '' : ' Ajoutez une autre discipline pour une série complète.'
  return `Il n'existe que ${received} ${questions} pour « ${label} » : cette série est plus courte que les ${SERIES_SIZE} habituelles.${advice}`
}
