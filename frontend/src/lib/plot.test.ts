import { describe, expect, it } from 'vitest'
import { pendulumFixture, regressionFixture, regressionMethods, regressionSweep } from '../dev/fakeViews'
import { buildFigure, clampPoints, isVisible, withAlpha, type ChartOptions } from './plot'
import { displayRoles } from './roles'
import type { RunResult, SweepResult } from './types.gen'
import type { Series, ViewResult } from './views'

// Vraies fixtures du moteur (R1, scripts/make_fixtures.py).
const runFixtures = import.meta.glob<RunResult>('../fixtures/*.run.json', { eager: true, import: 'default' })
const sweepFixture = Object.values(
  import.meta.glob<SweepResult>('../fixtures/*.sweep.json', { eager: true, import: 'default' }),
)[0]

const roles = displayRoles(regressionMethods)
const opts = (on: string[], showReference = true): ChartOptions => ({ roles, methodsOn: new Set(on), showReference })
const uids = (view: ViewResult, o: ChartOptions) => buildFigure(view, o)!.data.map((t) => t.uid)

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
  const s = (role: Series['role'], method: string | null): Series => ({
    id: 'v.fit.m', slot: 'fit', method, role, label: '', layer: null,
    x: null, y: null, low: null, high: null, hit: null, value: null, paths: null,
  })
  it('les données du générateur et la vraie valeur sont toujours visibles', () => {
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
    expect((fig.layout.xaxis as { range: number[] }).range).toEqual(reg.views.nuage.axes?.x)
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
    const view: ViewResult = {
      id: 'sens', type: 'sensitivity', title: '', mode: null, axes: { x: null, y: null },
      shown: 11, total: 11, clipped: 0, ui: null, series: [],
    }
    const fig = buildFigure(view, { ...opts(['ols', 'hc3']), sweep, measure: { label: 'Couverture', scale: 100, unit: '%' } })!
    expect(fig.data.filter((t) => String(t.uid).startsWith('sens.mesure.'))).toHaveLength(2)
    expect((fig.layout.annotations as { text: string }[]).map((a) => a.text)).toContain('Seuil critique')
  })

  it('courbes du pendule : une trace par série', () => {
    expect(uids(pendulumFixture(0.6).view, { methodsOn: new Set(['euler']), showReference: true })).toEqual([
      'trajectoire.truth.gen',
      'trajectoire.series.euler',
    ])
  })

  it('type non dessiné : null (vue de secours)', () => {
    expect(buildFigure({ ...reg.views.nuage, type: 'measures_table' }, opts(['ols']))).toBeNull()
    expect(buildFigure({ ...reg.views.nuage, series: [] }, opts(['ols']))).toBeNull() // rien à dessiner
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

describe('vraies fixtures du moteur (R1)', () => {
  const entries = Object.entries(runFixtures)

  it('il y a des fixtures à tester', () => {
    expect(entries.length).toBeGreaterThan(0)
  })

  it.each(entries)('%s : chaque vue se construit, Correction affichée ou non', (_name, run) => {
    const ids = run.methods.map((m) => m.id)
    const principal = run.methods.filter((m) => m.role === 'method').map((m) => m.id)
    for (const view of run.views) {
      for (const on of [principal, ids]) {
        const o: ChartOptions = {
          methodsOn: new Set(on), showReference: true, roles: displayRoles(run.methods),
          sweep: view.type === 'sensitivity' ? sweepFixture : null,
        }
        const fig = buildFigure(view, o)
        if (fig === null) continue // type non encore dessiné : vue de secours
        if (view.type !== 'sensitivity') expect(fig.data.length).toBeGreaterThan(0)
      }
    }
  })

  it('régression hétéroscédastique : le nuage a ses observations neutres et sa Référence', () => {
    const run = Object.entries(runFixtures).find(([n]) => n.includes('regression_hetero'))![1]
    const nuage = run.views.find((v) => v.type === 'scatter')!
    const ids = uids(nuage, { methodsOn: new Set(['ols']), showReference: true })
    expect(ids.some((u) => String(u).includes('.ref'))).toBe(true)
    expect(nuage.series.some((s) => s.role === 'data')).toBe(true)
  })
})

describe('segments', () => {
  const seg: Series = {
    id: 'nuage.segments-0.mco', slot: 'segments', method: 'mco', role: 'method', label: 'Résidus', layer: null,
    x: [1, 2, null], y: null, low: [0, 1, 2], high: [1, 3, 4], hit: null, value: null, paths: null,
  }
  const view = { id: 'nuage', type: 'scatter', series: [seg] } as unknown as ViewResult
  it('dessine un trait vertical par point, séparés par null', () => {
    const fig = buildFigure(view, { methodsOn: new Set(['mco']), showReference: false })!
    expect(fig.data).toHaveLength(1)
    expect(fig.data[0].x).toEqual([1, 1, null, 2, 2, null])
    expect(fig.data[0].y).toEqual([0, 1, null, 1, 3, null])
  })
  it('suit l’affichage de sa méthode', () => {
    const fig = buildFigure(view, { methodsOn: new Set(), showReference: false })!
    expect(fig.data).toHaveLength(0)
  })
})

describe('distribution', () => {
  const base = { layer: null, y: null, low: null, high: null, hit: null, paths: null }
  const view = {
    id: 'scores', type: 'distribution', axes: { x: [-3, 3], y: null },
    series: [
      { ...base, id: 'scores.h1.m', slot: 'h1', method: 'm', role: 'truth', label: 'Malades', x: [0, 1], value: null },
      { ...base, id: 'scores.threshold.m', slot: 'threshold', method: 'm', role: 'rupture', label: 'Seuil', x: null, value: 0.5 },
    ],
  } as unknown as ViewResult
  const fig = buildFigure(view, { methodsOn: new Set(['m']), showReference: false })!
  it('un histogramme de rôle truth reçoit une couleur et un motif', () => {
    const h = fig.data[0] as { marker: { line: { color: unknown }; pattern: { shape: string } } }
    expect(h.marker.line.color).toBeTruthy()
    expect(h.marker.pattern.shape).toBe('-')
  })
  it('le seuil est une ligne verticale en tirets', () => {
    const shapes = fig.layout.shapes as { line: { dash: string } }[]
    expect(shapes[0].line.dash).toBe('dash')
  })
})

describe('points posés', () => {
  const view = {
    id: 'nuage', type: 'scatter', axes: { x: [0, 10], y: [0, 10] },
    series: [{
      id: 'nuage.xy', slot: 'xy', method: null, role: 'data', label: 'Échantillon', layer: null,
      x: [1, 2], y: [1, 2], low: null, high: null, hit: null, value: null, paths: null,
    }],
  } as unknown as ViewResult
  it('ajoute une trace d’étoiles, avec l’indice de chaque point', () => {
    const fig = buildFigure(view, { methodsOn: new Set(), showReference: false, injected: [{ x: 4, y: 5 }, { x: 6, y: 7 }] })!
    const t = fig.data.at(-1) as { uid: string; x: number[]; customdata: number[]; marker: { symbol: string } }
    expect(t.uid).toBe('nuage.points-poses')
    expect(t.x).toEqual([4, 6])
    expect(t.customdata).toEqual([0, 1])
    expect(t.marker.symbol).toContain('star')
  })
  it('sans point posé, aucune trace en plus', () => {
    const fig = buildFigure(view, { methodsOn: new Set(), showReference: false, injected: [] })!
    expect(fig.data.some((t) => String(t.uid).endsWith('.points-poses'))).toBe(false)
  })
})

describe('trajectoires', () => {
  const base = { layer: null, y: null, low: null, high: null, hit: null }
  const view = {
    id: 'faisceau', type: 'repetitions', mode: 'paths', total: 500, shown: 2,
    series: [
      { ...base, id: 'faisceau.paths.moy', slot: 'paths', method: 'moy', role: 'method', label: 'X̄n', x: null, value: null, paths: [[1, 0.5, 0.2], [0, 0.1, null]] },
      { ...base, id: 'faisceau.truth', slot: 'truth', method: null, role: 'truth', label: 'μ', x: null, value: 0, paths: null },
    ],
  } as unknown as ViewResult
  const fig = buildFigure(view, { methodsOn: new Set(['moy']), showReference: false })!
  it('une seule trace par série, trajectoires séparées par null, abscisse 1..n', () => {
    expect(fig.data).toHaveLength(1)
    expect(fig.data[0].x).toEqual([1, 2, 3, null, 1, 2, 3, null])
    expect(fig.data[0].y).toEqual([1, 0.5, 0.2, null, 0, 0.1, null, null])
  })
  it('la vraie valeur est une ligne horizontale', () => {
    const sh = (fig.layout.shapes as { y0: number; xref: string }[])[0]
    expect(sh).toMatchObject({ y0: 0, xref: 'paper' })
  })
  it('masquer la méthode masque ses trajectoires', () => {
    expect(buildFigure(view, { methodsOn: new Set(), showReference: false })!.data).toHaveLength(0)
  })
})
