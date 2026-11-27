import { describe, expect, it } from 'vitest'
import { gauge, gaugeDomain, labGuide, robustExpected, targetFor, type GaugeMeasure } from './guide'
import { defaultState } from './state'
import type { EngineState, ExperimentSpec, RunResult } from './types.gen'
import regressionSpec from '../dev/specs/regression_lineaire.spec.json'
import regHetero from '../fixtures/regression_hetero.run.json'
import regSain from '../fixtures/regression_sain.run.json'

const reg = regressionSpec as unknown as ExperimentSpec
const hetero = regHetero as unknown as RunResult
const sain = regSain as unknown as RunResult

function withHyp(values: Record<string, number | boolean | string>): EngineState {
  const s = defaultState(reg)
  return { ...s, hypotheses: { ...s.hypotheses, ...values } }
}

describe('labGuide : que se passe-t-il ?', () => {
  it('état sain : inviter à relâcher une hypothèse', () => {
    const g = labGuide(reg, defaultState(reg), sain, ['ols'])
    expect(g.tone).toBe('ok')
    expect(g.headline).toMatch(/sain/)
    expect(g.causes).toEqual([])
    expect(g.action).toBeNull()
  })

  it('hypothèse relâchée, méthode rompue, correction masquée : proposer la correction', () => {
    const g = labGuide(reg, withHyp({ hetero: 0.8 }), hetero, ['ols'])
    expect(g.tone).toBe('broken')
    expect(g.headline).toMatch(/rompue/)
    expect(g.causes.map((c) => c.id)).toEqual(['hetero'])
    expect(g.causes[0].text).toBe(reg.hypotheses.hetero.when_broken)
    expect(g.action).toBe('correction')
    expect(g.next).toMatch(/correction/)
  })

  it('correction affichée et fiable : elle répare', () => {
    const g = labGuide(reg, withHyp({ hetero: 0.8 }), hetero, ['ols', 'hc3'])
    expect(g.action).toBeNull()
    expect(g.next).toMatch(/répare/)
  })

  it('correction affichée mais rompue : dire ce qu’elle ne répare pas', () => {
    const res = structuredClone(hetero)
    res.measures.coverage.states.hc3 = 'broken'
    const g = labGuide(reg, withHyp({ hetero: 0.8, autocorr: true }), res, ['ols', 'hc3'])
    expect(g.next).toMatch(/ne suffit pas/)
    expect(g.next).toContain(reg.hypotheses.autocorr.label)
    expect(g.next).not.toContain(reg.hypotheses.hetero.label)
  })

  it('hypothèse à laquelle la méthode doit résister (robust_expected)', () => {
    expect(robustExpected(reg.hypotheses.error_law, 'exponential')).toBe(true)
    const g = labGuide(reg, withHyp({ error_law: 'exponential' }), sain, ['ols'])
    expect(g.headline).toMatch(/résiste/)
    expect(g.causes).toHaveLength(1)
  })

  it('méthode rompue sans hypothèse relâchée : ce sont les réglages', () => {
    const g = labGuide(reg, defaultState(reg), hetero, ['ols'])
    expect(g.causes).toEqual([])
    expect(g.context).toMatch(/réglages/)
  })

  it('sans correction : proposer de tout rétablir', () => {
    const noCorr = { ...reg, methods: reg.methods.filter((m) => m.role === 'method') } as ExperimentSpec
    const g = labGuide(noCorr, withHyp({ hetero: 0.8 }), hetero, ['ols'])
    expect(g.action).toBe('heal')
  })

  it('au plus deux explications, les autres sont comptées', () => {
    const g = labGuide(reg, withHyp({ hetero: 0.8, autocorr: true, add_leverage: true }), hetero, ['ols'])
    expect(g.causes).toHaveLength(2)
    expect(g.moreCauses).toBe(1)
  })
})

describe('jauge de la mesure principale', () => {
  const below: GaugeMeasure = {
    target: 0.95,
    direction: 'below',
    ok_within: 0.03,
    broken_beyond: 0.1,
    values: { a: 0.8 },
    baseline: { a: 0.95 },
    unit: '%',
    scale: 100,
  }

  it('cible, seuils et pourcentage borné à 100 %', () => {
    const d = gaugeDomain(below, ['a'])
    expect(d).not.toBeNull()
    const [lo, hi] = d!
    expect(lo).toBeCloseTo(0.75)
    expect(hi).toBeCloseTo(1)
    const g = gauge(below, 'a', d!)!
    expect(g.zones.map((z) => z.verdict)).toEqual(['broken', 'warning', 'ok'])
    // Rompu sous 85 %, Fragile de 85 à 92 %, Fiable au-dessus.
    expect(g.zones[0].to).toBeCloseTo((0.85 - 0.75) / 0.25)
    expect(g.zones[1].to).toBeCloseTo((0.92 - 0.75) / 0.25)
    expect(g.value).toBeCloseTo((0.8 - 0.75) / 0.25)
    expect(g.target).toBeCloseTo(0.8)
  })

  it('le repère tombe dans la zone de son verdict', () => {
    const d = gaugeDomain(below, ['a'])!
    const g = gauge(below, 'a', d)!
    const zone = g.zones.find((z) => g.value! >= z.from && g.value! <= z.to)
    expect(zone?.verdict).toBe('broken')
  })

  it('valeur hors des zones : la jauge s’élargit pour la contenir', () => {
    const m = { ...below, values: { a: 0.4 } }
    const [lo] = gaugeDomain(m, ['a'])!
    expect(lo).toBeLessThan(0.4)
    const g = gauge(m, 'a', gaugeDomain(m, ['a'])!)!
    expect(g.value).toBeGreaterThan(0)
  })

  it('direction both : cinq zones symétriques', () => {
    const m: GaugeMeasure = { ...below, target: 0, direction: 'both', ok_within: 0.04, broken_beyond: 0.08, unit: '', scale: 1, values: { a: 0 }, baseline: { a: 0 } }
    const g = gauge(m, 'a', gaugeDomain(m, ['a'])!)!
    expect(g.zones.map((z) => z.verdict)).toEqual(['broken', 'warning', 'ok', 'warning', 'broken'])
    expect(g.target).toBeCloseTo(0.5)
  })

  it('direction above : Fiable à gauche', () => {
    const m: GaugeMeasure = { ...below, target: 0.05, direction: 'above', ok_within: 0.025, broken_beyond: 0.1, values: { a: 0.4 }, baseline: { a: 0.05 } }
    const g = gauge(m, 'a', gaugeDomain(m, ['a'])!)!
    expect(g.zones.map((z) => z.verdict)).toEqual(['ok', 'warning', 'broken'])
  })

  it('cible « base » : la Référence de chaque méthode', () => {
    const m: GaugeMeasure = { ...below, target: 'base', values: { a: 0.5, b: 0.6 }, baseline: { a: 0.7, b: 0.65 } }
    expect(targetFor(m, 'a')).toBe(0.7)
    expect(targetFor(m, 'b')).toBe(0.65)
    const d = gaugeDomain(m, ['a', 'b'])!
    expect(gauge(m, 'a', d)!.target).not.toBeCloseTo(gauge(m, 'b', d)!.target)
  })

  it('mesure sans cible ni seuils : pas de jauge', () => {
    const m: GaugeMeasure = { ...below, target: null, direction: null, ok_within: null, broken_beyond: null }
    expect(gaugeDomain(m, ['a'])).toBeNull()
    expect(gauge(m, 'a', [0, 1])).toBeNull()
  })
})
