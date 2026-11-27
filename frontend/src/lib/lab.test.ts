import { describe, expect, it } from 'vitest'
import { formatControl, formatMargin, formatMeasure, splitTitle } from './format'
import {
  addPoint,
  allowsPoints,
  axisTitle,
  clearPoints,
  removePoint,
  viewPoints,
  brokenValue,
  currentOnAxes,
  headlineVerdict,
  healAll,
  hypothesisStatus,
  primaryMeasureId,
  setValue,
  sweepRequest,
  toggleMethod,
} from './lab'
import { defaultState, defaultUi } from './state'
import type { ExperimentSpec, RunResult } from './types.gen'
import regressionSpec from '../dev/specs/regression_lineaire.spec.json'
import studentSpec from '../dev/specs/test_student.spec.json'
import penduleSpec from '../dev/specs/pendule_euler.spec.json'
import regHetero from '../fixtures/regression_hetero.run.json'
import regSain from '../fixtures/regression_sain.run.json'

const reg = regressionSpec as unknown as ExperimentSpec
const specs = [reg, studentSpec, penduleSpec] as unknown as ExperimentSpec[]
const NBSP = ' '

describe('format', () => {
  const pct = { unit: '%', scale: 100, decimals: 1 }
  it('pourcentage à la française', () => {
    expect(formatMeasure(0.796, pct)).toBe(`79,6${NBSP}%`)
    expect(formatMargin(0.018021, pct)).toBe(`±${NBSP}3,6`)
  })
  it('valeur absente ou non finie', () => {
    expect(formatMeasure(null, pct)).toBe('—')
    expect(formatMargin(null, pct)).toBeNull()
    expect(formatMargin(0, pct)).toBeNull()
  })
  it('sans unité, signe moins typographique', () => {
    expect(formatMeasure(-0.0044, { unit: '', scale: 1, decimals: 3 })).toBe('−0,004')
  })
  it('titre coupé au premier deux-points', () => {
    expect(splitTitle("Régression linéaire : quand l'IC devient faux")).toEqual({ head: 'Régression linéaire', tail: "quand l'IC devient faux" })
    expect(splitTitle('Tests : a : b')).toEqual({ head: 'Tests', tail: 'a : b' })
    expect(splitTitle('Sans deux-points')).toEqual({ head: 'Sans deux-points', tail: null })
  })
  it('contrôle : décimales tirées du pas', () => {
    expect(formatControl(0.85, 0.05)).toBe('0,85')
    expect(formatControl(150, 10)).toBe('150')
    expect(formatControl(1.2, 0.1)).toBe('1,2')
  })
})

describe('lab : lecture de RunResult', () => {
  it('mesure primaire et badge', () => {
    expect(primaryMeasureId(regHetero as unknown as RunResult)).toBe('coverage')
    expect(headlineVerdict(regHetero as unknown as RunResult)).toBe('broken')
    expect(headlineVerdict(regSain as unknown as RunResult)).toBe('ok')
  })
})

describe('lab : actions sur les états', () => {
  it('la Correction s’affiche et se masque, la méthode principale reste', () => {
    const ui = defaultUi(reg)
    const on = toggleMethod(reg, ui, 'hc3')
    expect(on.methodsOn).toEqual(['ols', 'hc3'])
    expect(toggleMethod(reg, on, 'hc3').methodsOn).toEqual(['ols'])
    expect(toggleMethod(reg, ui, 'ols').methodsOn).toEqual(['ols'])
  })

  it('casser une hypothèse : chaque type a une valeur cassée différente de la saine', () => {
    for (const spec of specs) {
      for (const [id, h] of Object.entries(spec.hypotheses)) {
        expect(brokenValue(h), `${spec.id}.${id}`).not.toEqual(h.healthy_value)
      }
    }
  })

  it('modifier une valeur garde la graine et la forme canonique', () => {
    const s0 = { ...defaultState(reg), seed: 7 }
    const s1 = setValue(reg, s0, 'h', 'hetero', 0.8123)
    expect(s1.seed).toBe(7)
    expect(s1.hypotheses.hetero).toBe(0.8)
    const s2 = setValue(reg, s1, 'p', 'n', 10_000)
    expect(s2.params.n).toBe(1000)
    expect(healAll(reg, s2).hypotheses).toEqual(defaultState(reg).hypotheses)
    expect(healAll(reg, s2).params.n).toBe(1000)
  })

  it('état des hypothèses en mots', () => {
    const h = reg.hypotheses.hetero
    expect(hypothesisStatus(h, 0)).toBe('Respectée')
    expect(hypothesisStatus(h, 0.5)).toBe('Relâchée')
  })

  it('balayage : l’axe balayé est remis à sa valeur saine, donc la requête ne dépend pas du curseur', () => {
    const a = setValue(reg, defaultState(reg), 'h', 'hetero', 0.3)
    const b = setValue(reg, defaultState(reg), 'h', 'hetero', 0.9)
    const ra = sweepRequest(reg, a, ['h.hetero'], null)
    expect(ra).toEqual(sweepRequest(reg, b, ['h.hetero'], null))
    expect(ra.state.hypotheses.hetero).toBe(0)
    expect(ra.axes).toEqual([{ target: 'h.hetero' }])
    expect(currentOnAxes(b, ['h.hetero'])).toEqual({ 'h.hetero': 0.9 })
  })
})

describe('lab : titre de l’axe d’un balayage', () => {
  it('libellés du YAML, jamais l’identifiant', () => {
    expect(axisTitle(reg, 'h.hetero')).toBe(`${reg.hypotheses.hetero.label} : h`)
    expect(axisTitle(reg, 'p.n')).toBe(reg.params.n.label)
    expect(axisTitle(reg, 'h.inconnue')).toBe('h.inconnue')
  })
})

describe('ajout de points', () => {
  const spec = regressionSpec as unknown as ExperimentSpec
  const s0 = defaultState(spec)
  it('la vue du nuage les accepte, les autres non', () => {
    const nuage = spec.views.find((v) => v.allow_point_injection)!.id
    expect(allowsPoints(spec, nuage)).toBe(true)
    expect(allowsPoints(spec, 'inexistante')).toBe(false)
    expect(allowsPoints(studentSpec as unknown as ExperimentSpec, 'puissance')).toBe(false)
  })
  it('pose, arrondit, retire et efface sans toucher au reste de l’état', () => {
    const s1 = addPoint(spec, s0, { x: 4.12345, y: -2.00001 })!
    expect(s1.extra_points).toEqual([{ x: 4.123, y: -2 }])
    expect(s1.seed).toBe(s0.seed)
    const s2 = addPoint(spec, s1, { x: 1, y: 1 })!
    expect(viewPoints(spec, s2)).toEqual([{ x: 4.123, y: -2 }, { x: 1, y: 1 }])
    expect(removePoint(spec, s2, 0).extra_points).toEqual([{ x: 1, y: 1 }])
    expect(clearPoints(spec, s2).extra_points).toEqual([])
  })
  it('refuse le 21e point', () => {
    let s = s0
    for (let i = 0; i < 20; i++) s = addPoint(spec, s, { x: i, y: i })!
    expect(s.extra_points).toHaveLength(20)
    expect(addPoint(spec, s, { x: 0, y: 0 })).toBeNull()
  })
})
