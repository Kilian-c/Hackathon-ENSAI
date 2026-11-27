import { describe, expect, it } from 'vitest'
import { animatable, conclusion, endUi, frameStates, pauseIndex } from './autoSweep'
import { defaultState, defaultUi } from './state'
import type { ExperimentSpec, SweepResult } from './types.gen'
import regressionSpec from '../dev/specs/regression_lineaire.spec.json'

const spec = regressionSpec as unknown as ExperimentSpec
const sweep = (values: (number | string)[], warning_at: number | null): Pick<SweepResult, 'axes' | 'critical'> => ({
  axes: [{ target: 'h.hetero', values, labels: values.map(String) }],
  critical: { ols: warning_at === null ? null : { warning_at, broken_at: null } },
})

describe('balayage automatique', () => {
  it('liste les contrôles animables du YAML, dans l’ordre', () => {
    expect(animatable(spec)).toEqual(['h.hetero', 'p.n'])
    expect(animatable({ ...spec, auto_sweep: ['h.inconnue', 'p.n'] })).toEqual(['p.n'])
  })

  it('une image par valeur, le reste de l’état conservé', () => {
    const s0 = { ...defaultState(spec), seed: 7 }
    const frames = frameStates(spec, s0, 'h.hetero', sweep([0, 0.5, 1], null))
    expect(frames.map((f) => f.hypotheses.hetero)).toEqual([0, 0.5, 1])
    expect(frames.every((f) => f.seed === 7 && f.params.n === s0.params.n)).toBe(true)
  })

  it('pause sur la première valeur au-delà du seuil critique', () => {
    expect(pauseIndex(sweep([0, 0.2, 0.4, 0.6], 0.31), 'ols')).toBe(2)
    expect(pauseIndex(sweep([0, 0.2, 0.4], 0.4), 'ols')).toBe(2)
    expect(pauseIndex(sweep([0, 0.2], null), 'ols')).toBeNull()
    expect(pauseIndex(sweep(['normal', 'cauchy'], 0.5), 'ols')).toBeNull()
  })

  it('la Correction s’active à la fin pour une hypothèse, jamais pour un paramètre', () => {
    const ui = defaultUi(spec)
    expect(endUi(spec, ui, 'h.hetero').methodsOn).toContain('hc3')
    expect(endUi(spec, ui, 'p.n')).toBe(ui)
  })

  it('conclut pour un paramètre selon le premier et le dernier verdict', () => {
    const labels = ['30', '1000']
    expect(conclusion(spec, 'p.n', labels, 'broken', 'ok')).toMatch(/répare : .* de Rompu à Fiable/)
    expect(conclusion(spec, 'p.n', labels, 'broken', 'broken')).toMatch(/ne répare pas : .* reste Rompu/)
    expect(conclusion(spec, 'h.hetero', labels, 'broken', 'ok')).toBeNull()
  })
})
