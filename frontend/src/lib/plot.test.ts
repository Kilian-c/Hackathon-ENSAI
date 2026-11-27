import { describe, expect, it } from 'vitest'
import { pendulumFixture, regressionFixture, regressionMethods, regressionSweep } from '../dev/fakeViews'
import { buildFigure, clampPoints, isVisible, withAlpha, type ChartOptions } from './plot'
import { displayRoles } from './roles'
import type { ViewData, ViewSeries } from './views'

const roles = displayRoles(regressionMethods)
const opts = (on: string[], showReference = true): ChartOptions => ({ roles, methodsOn: new Set(on), showReference })
const uids = (view: ViewData, o: ChartOptions) => buildFigure(view, o)!.data.map((t) => t.uid)

describe('clampPoints', () => {
  it('ramène au bord les points hors cadre, avec un triangle orienté', () => {
    const r = clampPoints([0, 5, -5, 0, null], [0, 0, 0, 9, 1], [-1, 1], [-1, 1])
    expect(r.inside).toEqual({ x: [0], y: [0] })
    expect(r.outside.x).toEqual([1, -1, 0])
    expect(r.outside.y).toEqual([0, 0, 1])
    expect(r.outside.symbol).toEqual(['triangle-right', 'triangle-left', 'triangle-up'])
  })

  it('sans bornes, tout est dans le cadre', () => {
    expect(clampPoints([1e9], [-1e9]).outside.x).toEqual([])
  })
})

describe('isVisible', () => {
  const s = (role: ViewSeries['role'], method: string | null): ViewSeries => ({ id: 'v', slot: 'fit', method, role, label: '' })
  it('les données et la vraie valeur sont toujours visibles', () => {
    expect(isVisible(s('data', null), opts([]))).toBe(true)
    expect(isVisible(s('truth', null), opts([]))).toBe(true)
  })
  it('une méthode masquée et sa Référence disparaissent', () => {
    expect(isVisible(s('correction', 'hc3'), opts(['ols']))).toBe(false)
    expect(isVisible(s('reference', 'hc3'), opts(['ols']))).toBe(false)
  })
  it('la Référence suit son interrupteur', () => {
    expect(isVisible(s('reference', 'ols'), opts(['ols'], false))).toBe(false)
  })
})

describe('buildFigure', () => {
  const reg = regressionFixture(0.8, 42, 200, 100)

  it('Correction affichée : ses intervalles apparaissent, sans autre changement', () => {
    const without = uids(reg.views.ic, opts(['ols']))
    const withCorr = uids(reg.views.ic, opts(['ols', 'hc3']))
    expect(without.some((u) => String(u).startsWith('ic.est.hc3'))).toBe(false)
    expect(withCorr.filter((u) => String(u).startsWith('ic.est.ols'))).toEqual(without)
    expect(withCorr.some((u) => String(u).startsWith('ic.est.hc3'))).toBe(true)
  })

  it('les axes viennent de la vue, et la mise en page garde la caméra (uirevision)', () => {
    const fig = buildFigure(reg.views.nuage, opts(['ols']))!
    expect((fig.layout.xaxis as { range: number[] }).range).toEqual(reg.views.nuage.axes.x)
    expect(fig.layout.uirevision).toBe('keep')
  })

  it('les axes ne bougent pas quand h change (calculés sur la Référence)', () => {
    expect(regressionFixture(0, 42, 50).views.nuage.axes).toEqual(regressionFixture(1, 42, 50).views.nuage.axes)
  })

  it('légende du bas : affichés sur calculés', () => {
    expect(buildFigure(reg.views.ic, opts(['ols']))!.caption).toContain('100 affichés sur 200 calculés')
  })

  it('sensibilité : une courbe par méthode affichée, et le seuil critique', () => {
    const sweep = regressionSweep(0.8, 42, 100)
    const view: ViewData = { id: 'sens', type: 'sensitivity', title: '', axes: {}, shown: 11, total: 11, clipped: 0, series: [] }
    const fig = buildFigure(view, { ...opts(['ols', 'hc3']), sweep, measure: { label: 'Couverture', scale: 100, unit: '%' } })!
    expect(fig.data.filter((t) => String(t.uid).startsWith('sens.mesure.'))).toHaveLength(2)
    expect((fig.layout.annotations as { text: string }[]).map((a) => a.text)).toContain('Seuil critique')
  })

  it('courbes du pendule : une trace par série', () => {
    expect(uids(pendulumFixture(0.6).view, { roles: { euler: 'method', rk4: 'correction' }, methodsOn: new Set(['euler']), showReference: true })).toEqual([
      'trajectoire.truth.gen',
      'trajectoire.series.euler',
    ])
  })

  it('type non dessiné : null (vue de secours)', () => {
    expect(buildFigure({ ...reg.views.nuage, type: 'measures_table' }, opts(['ols']))).toBeNull()
  })
})

describe('fixture : ordres de grandeur du cahier', () => {
  it('couverture MCO effondrée et HC3 réparée à h = 0,8', () => {
    const { coverage } = regressionFixture(0.8, 42, 500)
    expect(coverage.ols).toBeLessThan(0.85)
    expect(coverage.hc3).toBeGreaterThan(0.9)
  })
})

describe('withAlpha', () => {
  it('convertit un hexadécimal en rgba', () => {
    expect(withAlpha('#3fb950', 0.5)).toBe('rgba(63, 185, 80, 0.5)')
    expect(withAlpha('var(--x)', 0.5)).toBe('var(--x)')
  })
})
