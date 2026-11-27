import { describe, expect, it } from 'vitest'
import { pendulumFixture, regressionFixture, regressionMethods, regressionSweep } from '../dev/fakeViews'
import { buildFigure, clampPoints, gridPosition, isVisible, withAlpha, type ChartOptions } from './plot'
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

describe('Domaine de validité', () => {
  const view = { id: 'validite', type: 'validity_domain', series: [], axes: null } as unknown as ViewResult
  const sweep = {
    axes: [
      { target: 'h.hetero', values: [0, 0.5, 1], labels: ['0', '0,5', '1'] },
      { target: 'p.n', values: [30, 300], labels: ['30', '300'] },
    ],
    measure: 'coverage',
    values: { ols: [[0.95, 0.9, 0.8], [0.95, 0.88, 0.7]], hc3: [[0.95, 0.95, 0.94], [0.95, 0.95, 0.95]] },
    mc_se: {},
    states: { ols: [['ok', 'warning', 'broken'], ['ok', 'broken', 'broken']], hc3: [['ok', 'ok', 'ok'], ['ok', 'ok', 'ok']] },
    critical: null, target: 0.95, ok_within: 0.03, broken_beyond: 0.1, direction: 'below',
    current: { 'h.hetero': 0.25, 'p.n': 300 }, repeat_used: 500, reduced: false, compute_ms: 1,
  } as unknown as SweepResult
  const fig = buildFigure(view, {
    methodsOn: new Set(['ols']), showReference: false, sweep,
    roles: { ols: 'method', hc3: 'correction' }, measure: { label: 'Couverture', unit: '%', scale: 100, decimals: 0 },
  })!
  const map = fig.data[0] as { uid: string; z: number[][]; text: string[][] }

  it('une case par couple, colorée par le verdict de la méthode principale', () => {
    expect(map.uid).toBe('validite.domaine')
    expect(map.z).toEqual([[0, 1, 2], [0, 2, 2]])
  })
  it('chaque case porte l’icône et la valeur (jamais la couleur seule)', () => {
    expect(map.text[0][0]).toMatch(/^✓ 95/)
    expect(map.text[1][2]).toMatch(/^✕ 70/)
  })
  it('l’état actuel est placé entre les cases', () => {
    const cur = fig.data[1] as { x: number[]; y: number[] }
    expect(cur.x).toEqual([0.5])
    expect(cur.y).toEqual([1])
  })
  it('sans balayage à deux axes : en attente', () => {
    expect(buildFigure(view, { methodsOn: new Set(), showReference: false, sweep: null })!.caption).toEqual(['Balayage en cours…'])
  })
})

describe('gridPosition', () => {
  it('exacte, interpolée, ou hors grille', () => {
    expect(gridPosition([30, 100, 300], 100)).toBe(1)
    expect(gridPosition([30, 100, 300], 200)).toBe(1.5)
    expect(gridPosition([30, 100, 300], 5000)).toBeNull()
    expect(gridPosition(['normal', 'cauchy'], 'cauchy')).toBe(1)
  })
})

describe('échelle logarithmique (ui.log_y, ui.log_x)', () => {
  const base = { layer: null, low: null, high: null, hit: null, value: null, paths: null }
  const view = (ui: Record<string, unknown> | null, axes: Record<string, unknown> = {}) =>
    ({
      id: 'conv', type: 'curves', total: 0, shown: 0, axes, ui,
      series: [
        { ...base, id: 'conv.series.jacobi', slot: 'series', method: 'jacobi', role: 'method', label: 'Jacobi', x: [1, 2, 3], y: [1, 0.01, 0] },
      ],
    }) as unknown as ViewResult
  const on = { methodsOn: new Set(['jacobi']), showReference: false }

  it('log_y : axe logarithmique, bornes du moteur converties en log10', () => {
    const fig = buildFigure(view({ log_y: true }, { y: [1e-6, 10] }), on)!
    expect(fig.layout.yaxis).toMatchObject({ type: 'log', range: [-6, 1], autorange: false })
    expect((fig.layout.xaxis as { type?: string }).type).toBeUndefined()
  })
  it('bornes non positives : automatique au lieu du log de 0', () => {
    const fig = buildFigure(view({ log_y: true }, { y: [0, 10] }), on)!
    expect(fig.layout.yaxis).toMatchObject({ type: 'log', autorange: true })
  })
  it('les valeurs ≤ 0 sont comptées en légende (Plotly les tait)', () => {
    expect(buildFigure(view({ log_y: true }), on)!.caption).toContain(
      '1 valeur négative ou nulle non affichée (échelle logarithmique)',
    )
  })
  it('log_x agit sur l’axe horizontal ; sans ui, rien ne change', () => {
    expect((buildFigure(view({ log_x: true }), on)!.layout.xaxis as { type: string }).type).toBe('log')
    const plain = buildFigure(view(null), on)!
    expect((plain.layout.yaxis as { type?: string }).type).toBeUndefined()
    expect(plain.caption).toEqual([])
  })
  it('seul true active le réglage', () => {
    expect((buildFigure(view({ log_y: 'oui' }), on)!.layout.yaxis as { type?: string }).type).toBeUndefined()
  })
})

describe('matrices (vue heatmap)', () => {
  const base = { layer: null, x: null, y: null, low: null, high: null, hit: null, value: null }
  const matrix = (id: string, method: string, role: string, paths: (number | null)[][]) => ({
    ...base, id: `mat.matrix.${id}`, slot: 'matrix', method, role, label: id, paths,
  })
  const view = (series: unknown[], ui: Record<string, unknown> | null = null) =>
    ({ id: 'mat', type: 'heatmap', total: 0, shown: 0, axes: {}, ui, series }) as unknown as ViewResult
  const A = matrix('gauss', 'gauss', 'method', [[2, -1], [-1, 2]])
  const P = matrix('pivot', 'pivot', 'correction', [[1, 0], [0, 1]])
  const R = matrix('ref', 'gauss', 'reference', [[0.5, 0], [0, null]])

  it('une carte par méthode affichée, ligne 1 en haut, indices à partir de 1', () => {
    const fig = buildFigure(view([A, P]), { methodsOn: new Set(['gauss', 'pivot']), showReference: false })!
    expect(fig.data.map((t) => t.uid)).toEqual(['mat.matrix.gauss', 'mat.matrix.pivot'])
    expect(fig.data[0]).toMatchObject({ type: 'heatmap', z: [[2, -1], [-1, 2]], x: [1, 2], y: [1, 2], xaxis: 'x', yaxis: 'y' })
    expect(fig.data[1]).toMatchObject({ xaxis: 'x2', yaxis: 'y2' })
    expect(fig.layout.yaxis).toMatchObject({ autorange: 'reversed', scaleanchor: 'x' })
  })
  it('signes mêlés : échelle commune, divergente et centrée sur 0', () => {
    const fig = buildFigure(view([A, P]), { methodsOn: new Set(['gauss', 'pivot']), showReference: false })!
    for (const t of fig.data) expect(t).toMatchObject({ zmin: -2, zmax: 2 })
    expect((fig.data[0].colorscale as unknown[][])[1][0]).toBe(0.5)
    expect(fig.data.map((t) => t.showscale)).toEqual([false, true])
  })
  it('valeurs écrites dans les cases (jamais la couleur seule), case vide pour null', () => {
    const fig = buildFigure(view([R], { decimals: 1 }), { methodsOn: new Set(['gauss']), showReference: true })!
    expect(fig.data[0].text).toEqual([['0,5', '0,0'], ['0,0', '']])
    expect(fig.data[0].zmin).toBe(0)
  })
  it('la Référence suit son interrupteur et se place à droite', () => {
    const o = (ref: boolean) => ({ methodsOn: new Set(['gauss']), showReference: ref })
    expect(buildFigure(view([R, A]), o(true))!.data.map((t) => t.uid)).toEqual(['mat.matrix.gauss', 'mat.matrix.ref'])
    expect(buildFigure(view([R, A]), o(false))!.data.map((t) => t.uid)).toEqual(['mat.matrix.gauss'])
  })
  it('bornes imposées par ui.zmin et ui.zmax', () => {
    const fig = buildFigure(view([A], { zmin: -5, zmax: 5 }), { methodsOn: new Set(['gauss']), showReference: false })!
    expect(fig.data[0]).toMatchObject({ zmin: -5, zmax: 5 })
  })
  it('grande matrice : valeurs au survol seulement ; au-delà de 3 cartes, le reste est compté', () => {
    const big = matrix('big', 'gauss', 'method', Array.from({ length: 20 }, () => Array(20).fill(1)))
    const fig = buildFigure(view([big]), { methodsOn: new Set(['gauss']), showReference: false })!
    expect(fig.data[0].text).toBeUndefined()
    expect(fig.caption).toContain('Valeurs au survol')
    const many = ['a', 'b', 'c', 'd'].map((m) => matrix(m, m, 'method', [[1]]))
    const fig4 = buildFigure(view(many), { methodsOn: new Set(['a', 'b', 'c', 'd']), showReference: false })!
    expect(fig4.data).toHaveLength(3)
    expect(fig4.caption).toContain('3 matrices affichées sur 4')
  })
  it('méthode masquée : message au lieu d’une figure vide', () => {
    const fig = buildFigure(view([A]), { methodsOn: new Set(), showReference: false })!
    expect(fig.caption).toEqual(['Aucune matrice à afficher pour les méthodes choisies'])
  })
})
