import { describe, expect, it } from 'vitest'
import {
  applyPreset,
  brokenHypotheses,
  canonicalState,
  defaultState,
  defaultUi,
  labLink,
  nextDraw,
  parseLink,
  resolveLabLink,
  roundToStep,
  stateKey,
  trainingLink,
} from './state'
import type { ExperimentSpec } from './types.gen'

// Extrait de experiments/regression_lineaire.yaml : seuls les champs lus par state.ts.
const spec = {
  id: 'regression-lineaire',
  params: {
    n: { type: 'number', label: 'n', min: 30, max: 1000, step: 10, default: 150, sweep_values: null },
    beta1: { type: 'number', label: 'pente', min: -3, max: 3, step: 0.1, default: 1.5, sweep_values: null },
    match_summary: { type: 'boolean', label: 'Anscombe', min: null, max: null, step: null, default: false, sweep_values: null },
  },
  hypotheses: {
    hetero: { type: 'continuous', healthy_value: 0, range: [0, 1], step: 0.05, options: null },
    error_law: {
      type: 'choice', healthy_value: 'normal', range: [0, 1], step: null,
      options: { normal: { label: 'Normale' }, student_2: { label: 'Student' } },
    },
    add_leverage: { type: 'boolean', healthy_value: false, range: [0, 1], step: null, options: null },
  },
  generator: { type: 'random', inject: { x: 'x', y: 'y' } },
  methods: [
    { id: 'ols', role: 'method' },
    { id: 'hc3', role: 'correction' },
  ],
} as unknown as ExperimentSpec

describe('forme canonique', () => {
  it('état par défaut : paramètres par défaut, hypothèses saines, graine 42', () => {
    expect(defaultState(spec)).toEqual({
      params: { beta1: 1.5, match_summary: false, n: 150 },
      hypotheses: { add_leverage: false, error_law: 'normal', hetero: 0 },
      extra_points: [],
      seed: 42,
    })
  })

  it('arrondit au pas, borne, et ignore les valeurs invalides', () => {
    const s = canonicalState(spec, {
      params: { n: 157, beta1: 9 },
      hypotheses: { hetero: 0.8333, error_law: 'inconnue', add_leverage: true, fantome: 1 } as never,
      seed: 7,
    })
    expect(s.params).toEqual({ beta1: 3, match_summary: false, n: 160 })
    expect(s.hypotheses).toEqual({ add_leverage: true, error_law: 'normal', hetero: 0.85 })
    expect(s.seed).toBe(7)
  })

  it('deux états équivalents ont la même clé (même cache)', () => {
    const a = canonicalState(spec, { hypotheses: { hetero: 0.8 }, params: { n: 150 } })
    const b = canonicalState(spec, { params: { n: 151 }, hypotheses: { hetero: 0.79 } })
    expect(stateKey(a)).toBe(stateKey(b))
  })

  it('arrondi sans erreur flottante', () => {
    expect(roundToStep(0.30000000000000004, 0.05)).toBe(0.3)
    expect(roundToStep(0.7, 0.1)).toBe(0.7)
  })

  it('points ajoutés : coordonnées de generator.inject, 20 au plus', () => {
    const pts = Array.from({ length: 25 }, (_, i) => ({ x: i, y: -i }))
    const s = canonicalState(spec, { extra_points: [...pts, { x: 1 } as never] })
    expect(s.extra_points).toHaveLength(20)
    expect(s.extra_points[0]).toEqual({ x: 0, y: -0 })
  })
})

describe('graine et préréglages', () => {
  it('seul « Nouveau tirage » change la graine', () => {
    expect(nextDraw(defaultState(spec)).seed).toBe(43)
  })

  it('un contre-exemple remet le reste à l’état sain, garde la graine et efface les points', () => {
    const cur = canonicalState(spec, { hypotheses: { add_leverage: true }, extra_points: [{ x: 1, y: 2 }], seed: 9 })
    const s = applyPreset(spec, cur, { params: { n: 600 }, hypotheses: { hetero: 0.85 } })
    expect(s.hypotheses).toEqual({ add_leverage: false, error_law: 'normal', hetero: 0.85 })
    expect(s.params.n).toBe(600)
    expect(s.seed).toBe(9)
    expect(s.extra_points).toEqual([])
  })

  it('hypothèses cassées', () => {
    expect(brokenHypotheses(spec, canonicalState(spec, { hypotheses: { hetero: 0.5, error_law: 'student_2' } }))).toEqual([
      'hetero',
      'error_law',
    ])
  })
})

describe('lien de partage', () => {
  it('aller-retour : URL -> état -> URL', () => {
    const url = '?exp=regression-lineaire&v=1&p.n=300&h.hetero=0.85&seed=42&on=ols,hc3&tab=ic&pts=4.2,-2;5.1,3.3'
    const link = parseLink(url)
    expect(link.kind).toBe('lab')
    if (link.kind !== 'lab') return
    const { engine, ui } = resolveLabLink(spec, link)
    expect(engine.params.n).toBe(300)
    expect(engine.hypotheses.hetero).toBe(0.85)
    expect(engine.extra_points).toEqual([{ x: 4.2, y: -2 }, { x: 5.1, y: 3.3 }])
    expect(ui).toEqual({ methodsOn: ['ols', 'hc3'], tab: 'ic' })
    expect(labLink(spec, engine, ui)).toBe(url)
  })

  it('le lien par défaut est court', () => {
    expect(labLink(spec, defaultState(spec), defaultUi(spec))).toBe('?exp=regression-lineaire&v=1&seed=42')
  })

  it('valeurs invalides ignorées, méthodes inconnues retirées', () => {
    const link = parseLink('?exp=regression-lineaire&p.n=abc&h.add_leverage=1&h.inconnue=3&on=fantome')
    if (link.kind !== 'lab') throw new Error('lien attendu')
    const { engine, ui } = resolveLabLink(spec, link)
    expect(engine.params.n).toBe(150)
    expect(engine.hypotheses.add_leverage).toBe(true)
    expect(ui.methodsOn).toEqual(['ols'])
  })

  it('version inconnue : refus avec un message', () => {
    const link = parseLink('?exp=regression-lineaire&v=2')
    expect(link.kind).toBe('error')
  })

  it('Entraînement et accueil', () => {
    expect(parseLink(trainingLink('regression-lineaire', 123))).toEqual({
      kind: 'training',
      filter: 'regression-lineaire',
      seed: 123,
    })
    expect(parseLink('https://crash-test.example/?train=toutes')).toEqual({ kind: 'training', filter: 'toutes', seed: null })
    expect(parseLink('')).toEqual({ kind: 'home' })
  })
})

describe('expériences importées (P1)', () => {
  it('lit ?share=<id> et ?brouillon comme un Laboratoire importé', () => {
    const shared = parseLink('?share=Ab3_-xYz9QwE&v=1&seed=7')
    expect(shared.kind).toBe('lab')
    if (shared.kind === 'lab') {
      expect(shared.origin).toEqual({ kind: 'share', id: 'Ab3_-xYz9QwE' })
      expect(shared.seed).toBe(7)
    }
    const draft = parseLink('?brouillon&v=1')
    expect(draft.kind === 'lab' && draft.origin).toEqual({ kind: 'draft' })
    expect(parseLink('?import').kind).toBe('import')
    expect(parseLink('?share=abc&v=9').kind).toBe('error')
  })

  it('réécrit le lien avec son origine, sans exp=', () => {
    const ui = defaultUi(spec)
    expect(labLink(spec, defaultState(spec), ui, { kind: 'share', id: 'Ab3_-xYz9QwE' })).toBe(
      '?share=Ab3_-xYz9QwE&v=1&seed=42',
    )
    expect(labLink(spec, defaultState(spec), ui, { kind: 'draft' })).toBe('?brouillon=&v=1&seed=42')
  })
})

describe('étape et hypothèse dans le lien (pont de l’Entraînement)', () => {
  it('écrit et relit stage= et hyp=', () => {
    const ui = { ...defaultUi(spec), stage: 'comprendre', focus: 'hetero' }
    const url = labLink(spec, defaultState(spec), ui)
    expect(url).toContain('stage=comprendre')
    expect(url).toContain('hyp=hetero')
    const link = parseLink(url)
    if (link.kind !== 'lab') throw new Error('lien de Laboratoire attendu')
    const resolved = resolveLabLink(spec, link)
    expect(resolved.ui.stage).toBe('comprendre')
    expect(resolved.ui.focus).toBe('hetero')
  })

  it('ignore une étape ou une hypothèse inconnue', () => {
    const link = parseLink('?exp=regression-lineaire&v=1&stage=nimporte&hyp=zzz')
    if (link.kind !== 'lab') throw new Error('lien de Laboratoire attendu')
    const resolved = resolveLabLink(spec, link)
    expect(resolved.ui.stage).toBeUndefined()
    expect(resolved.ui.focus).toBeUndefined()
  })
})
