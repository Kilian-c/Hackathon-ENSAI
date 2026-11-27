import { describe, expect, it } from 'vitest'
import {
  addAnswer,
  correctChoice,
  firstUnanswered,
  HISTORY_KEY,
  loadHistory,
  makeAnswer,
  revealChoice,
  saveAnswers,
  seriesTitle,
  storedAnswers,
  type Store,
} from './training'
import type { TrainingSessionResponse } from './types.gen'
import fixture from '../fixtures/training_session.json'

const session = fixture as unknown as TrainingSessionResponse
const [q1, q2] = session.questions
const wrongOf = (q: typeof q1) => q.choices.find((c) => !c.correct)!

function memoryStore(initial: Record<string, string> = {}): Store {
  const data = new Map(Object.entries(initial))
  return {
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => void data.set(k, v),
  }
}

describe('training : réponses', () => {
  it('la probabilité vient de la question, selon le cran', () => {
    const a = makeAnswer(q2, correctChoice(q2).id, 'guess', new Date('2026-11-27T15:00:00Z'))
    expect(a).toMatchObject({ qid: q2.qid, correct: true, level: 'guess', p: q2.confidence.guess })
    expect(a.at).toBe('2026-11-27T15:00:00.000Z')
    expect(makeAnswer(q1, wrongOf(q1).id, 'sure')).toMatchObject({ correct: false, p: 0.95 })
  })

  it('refuse un choix inconnu', () => {
    expect(() => makeAnswer(q1, 'zzz', 'fair')).toThrow()
  })

  it('la correction simule la bonne réponse quand on se trompe', () => {
    expect(revealChoice(q2, wrongOf(q2).id)).toBe(correctChoice(q2))
    expect(revealChoice(q2, correctChoice(q2).id)).toBe(correctChoice(q2))
  })

  it('la première réponse est définitive', () => {
    const first = makeAnswer(q1, wrongOf(q1).id, 'sure')
    const again = makeAnswer(q1, correctChoice(q1).id, 'sure')
    expect(addAnswer([first], again)).toEqual([first])
  })
})

describe('training : historique', () => {
  it('enregistre par série et reprend à la première question sans réponse', () => {
    const store = memoryStore()
    expect(firstUnanswered(session, [])).toBe(0)
    saveAnswers(store, session, [makeAnswer(q1, correctChoice(q1).id, 'fair')])
    const answers = storedAnswers(loadHistory(store), session)
    expect(answers).toHaveLength(1)
    expect(firstUnanswered(session, answers)).toBe(1)
    expect(loadHistory(store).series[session.id].size).toBe(session.questions.length)
  })

  it('série terminée', () => {
    const all = session.questions.map((q) => makeAnswer(q, correctChoice(q).id, 'fair'))
    expect(firstUnanswered(session, all)).toBe(session.questions.length)
  })

  it('ignore les réponses si le contenu des expériences a changé', () => {
    const store = memoryStore()
    saveAnswers(store, session, [makeAnswer(q1, correctChoice(q1).id, 'fair')])
    expect(storedAnswers(loadHistory(store), { ...session, content_hash: 'autre0' })).toEqual([])
  })

  it('survit à un stockage absent, illisible ou plein', () => {
    expect(loadHistory(null).series).toEqual({})
    expect(loadHistory(memoryStore({ [HISTORY_KEY]: 'pas du JSON' })).series).toEqual({})
    expect(loadHistory(memoryStore({ [HISTORY_KEY]: 'null' })).series).toEqual({})
    const full: Store = {
      getItem: () => null,
      setItem: () => {
        throw new Error('plein')
      },
    }
    expect(() => saveAnswers(full, session, [])).not.toThrow()
  })

  it('titre de série au singulier et au pluriel', () => {
    expect(seriesTitle(1)).toBe('Série de 1 question')
    expect(seriesTitle(3)).toBe('Série de 3 questions')
  })
})
