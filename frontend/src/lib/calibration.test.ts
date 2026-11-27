import { describe, expect, it } from 'vitest'
import {
  allAnswers,
  calibrationView,
  demoAnswers,
  experimentStats,
  headlineLevel,
  levelStats,
  murphy,
  summarize,
  tendency,
} from './calibration'
import { buildFigure } from './plot'
import type { Answer, ConfidenceLevel, History } from './training'

function answers(level: ConfidenceLevel, p: number, count: number, right: number, experimentId = 'a'): Answer[] {
  return Array.from({ length: count }, (_, i) => ({
    qid: `${experimentId}/${level}/${i}`,
    experimentId,
    type: 'misconception' as const,
    choiceId: 'a',
    correct: i < right,
    level,
    p,
    at: `2026-01-01T00:00:${String(i).padStart(2, '0')}Z`,
  }))
}

describe('calibration : score de Brier', () => {
  it('les profils du cahier : lucide 0,24 ; trop sûr 0,36 ; ignorant honnête 0,19', () => {
    expect(summarize(answers('fair', 0.6, 10, 6))!.brier).toBeCloseTo(0.24, 10)
    expect(summarize(answers('sure', 0.95, 10, 6))!.brier).toBeCloseTo(0.3625, 10)
    expect(summarize(answers('guess', 0.25, 20, 5))!.brier).toBeCloseTo(0.1875, 10)
  })

  it('sans réponse : rien', () => {
    expect(summarize([])).toBeNull()
    expect(murphy([])).toBeNull()
    expect(headlineLevel(levelStats([]))).toBeNull()
  })

  it('Murphy : calibration − résolution + incertitude redonne le score', () => {
    const all = demoAnswers(['a', 'b'])
    const m = murphy(all)!
    expect(m.calibration - m.resolution + m.uncertainty).toBeCloseTo(summarize(all)!.brier, 10)
  })
})

describe('calibration : crans et expériences', () => {
  it('réussite par bouton ; la phrase d’accroche prend « Certain » en premier', () => {
    const stats = levelStats([...answers('sure', 0.95, 5, 3), ...answers('guess', 0.25, 4, 1)])
    expect(stats.map((s) => [s.level, s.count, s.success])).toEqual([
      ['guess', 4, 0.25],
      ['fair', 0, null],
      ['sure', 5, 0.6],
    ])
    expect(headlineLevel(stats)!.level).toBe('sure')
  })

  it('tendance', () => {
    expect(tendency(0.9, 0.6)).toBe('over')
    expect(tendency(0.4, 0.7)).toBe('under')
    expect(tendency(0.65, 0.6)).toBe('calibrated')
  })

  it('expériences : la moins bien maîtrisée en premier, erreurs « Certain » comptées', () => {
    const rows = experimentStats([...answers('sure', 0.95, 4, 4, 'bien'), ...answers('sure', 0.95, 4, 1, 'mal')])
    expect(rows.map((r) => r.id)).toEqual(['mal', 'bien'])
    expect(rows[0].sureMistakes).toBe(3)
  })

  it('historique : séries réunies, entrées abîmées écartées', () => {
    const good = answers('fair', 0.6, 2, 1)
    const history: History = {
      version: 1,
      series: {
        s1: { filter: 'toutes', seed: 1, contentHash: 'x', size: 3, answers: [...good, { ...good[0], p: Number.NaN }] },
        s2: { filter: 'toutes', seed: 2, contentHash: 'x', size: 1, answers: answers('sure', 0.95, 1, 1, 'b') },
      },
    }
    expect(allAnswers(history)).toHaveLength(3)
  })
})

describe('calibration : démonstration et courbe', () => {
  it('le profil de démonstration montre un étudiant trop sûr de lui', () => {
    const demo = demoAnswers(['a', 'b', 'c', 'd'])
    expect(demo).toHaveLength(32)
    const sure = levelStats(demo).find((s) => s.level === 'sure')!
    expect(sure.success).toBeCloseTo(0.6, 10)
    const s = summarize(demo)!
    expect(tendency(s.confidence, s.success)).toBe('over')
    expect(new Set(demo.map((a) => a.experimentId)).size).toBe(4)
  })

  it('la courbe se dessine, avec le nom des boutons sur les points', () => {
    const view = calibrationView(levelStats(demoAnswers(['a'])))
    const fig = buildFigure(view, { methodsOn: new Set(), showReference: true })!
    expect(fig.data).toHaveLength(3)
    const points = fig.data.find((t) => t.uid === 'bilan.points.vous')!
    expect(points.text).toEqual(['Je devine', 'Plutôt sûr', 'Certain'])
    expect((points.marker as { size: number }).size).toBe(14)
    expect(fig.caption).toEqual([])
  })
})
