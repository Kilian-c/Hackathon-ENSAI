import { describe, expect, it } from 'vitest'
import { pendulumFixture, regressionFixture, regressionMethods, regressionSweep } from '../dev/fakeViews'
import {
  buildFigure, clampPoints, gridPosition, isVisible, segmentsTrace, shortTickLabels, withAlpha, type ChartOptions, syncInitialRanges,
} from './plot'
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
    expect(r.inside).toEqual({ x: [0], y: [0], index: [0] })
    expect(r.outside.index).toEqual([1, 2, 3]) // positions d'origine ; la valeur manquante (4) est sautée
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
  it('une valeur ≤ 0 est retirée de la ligne (sinon elle plonge jusqu’au bord)', () => {
    const fig = buildFigure(view({ log_y: true }), on)!
    expect(fig.data[0]).toMatchObject({ x: [1, 2], y: [1, 0.01] })
    expect(buildFigure(view(null), on)!.data[0]).toMatchObject({ x: [1, 2, 3], y: [1, 0.01, 0] })
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
    expect(fig.layout.coloraxis).toMatchObject({ cmin: -2, cmax: 2 })
    const axis = fig.layout.coloraxis as { colorscale: unknown[][]; cmin: number; colorbar: { thickness: number } }
    expect(axis.colorscale[1][0]).toBe(0.5)
    for (const t of fig.data) expect(t).toMatchObject({ coloraxis: 'coloraxis' }) // une seule échelle, portée par la mise en page
    // Une seule barre de couleur, dans la mise en page (aucune trace n'en porte) ; pas de bloc legend
    // (Plotly.validate plantait dessus).
    expect(fig.data.map((t) => t.colorbar === undefined)).toEqual([true, true])
    expect(fig.layout.coloraxis).toHaveProperty('colorbar')
    expect(fig.layout.legend).toBeUndefined()
  })
  it('cases carrées sans élargir les bornes : constrain domain sur les deux axes', () => {
    const fig = buildFigure(view([A, P]), { methodsOn: new Set(['gauss', 'pivot']), showReference: false })!
    for (const k of ['xaxis', 'yaxis', 'xaxis2', 'yaxis2']) expect(fig.layout[k]).toMatchObject({ constrain: 'domain' })
  })
  it('valeurs écrites dans les cases (jamais la couleur seule), case vide pour null', () => {
    const fig = buildFigure(view([R], { decimals: 1 }), { methodsOn: new Set(['gauss']), showReference: true })!
    expect(fig.data[0].text).toEqual([['0,5', '0,0'], ['0,0', '']])
    expect((fig.layout.coloraxis as { cmin: number }).cmin).toBe(0)
  })
  it('la Référence suit son interrupteur et se place à droite', () => {
    const o = (ref: boolean) => ({ methodsOn: new Set(['gauss']), showReference: ref })
    expect(buildFigure(view([R, A]), o(true))!.data.map((t) => t.uid)).toEqual(['mat.matrix.gauss', 'mat.matrix.ref'])
    expect(buildFigure(view([R, A]), o(false))!.data.map((t) => t.uid)).toEqual(['mat.matrix.gauss'])
  })
  it('aucune barre de couleur ne dépend de l’identifiant d’une série (un point y casse Plotly)', () => {
    // Plotly nomme la barre d'une trace « cb<uid> » et la retrouve par un sélecteur CSS : avec un uid
    // « mat.matrix.gauss », les points deviennent des séparateurs de classes, les anciennes graduations ne sont
    // jamais effacées et s'empilent à chaque mise à jour. L'échelle doit donc vivre dans layout.coloraxis.
    const fig = buildFigure(view([A, P, R]), { methodsOn: new Set(['gauss', 'pivot']), showReference: true })!
    expect(fig.data.some((t) => String(t.uid).includes('.'))).toBe(true) // les uids gardent leurs points
    for (const t of fig.data) {
      expect(t.showscale).toBeUndefined()
      expect(t.colorbar).toBeUndefined()
      expect(t.coloraxis).toBe('coloraxis')
    }
    expect((fig.layout.coloraxis as { colorbar: unknown }).colorbar).toMatchObject({ thickness: 12 })
  })
  it('bornes imposées par ui.zmin et ui.zmax', () => {
    const fig = buildFigure(view([A], { zmin: -5, zmax: 5 }), { methodsOn: new Set(['gauss']), showReference: false })!
    expect(fig.layout.coloraxis).toMatchObject({ cmin: -5, cmax: 5 })
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

describe('repère orthonormé et cercle unité (ui.aspect, ui.unit_circle)', () => {
  const base = { layer: null, low: null, high: null, hit: null, value: null, paths: null }
  const view = (ui: Record<string, unknown> | null) =>
    ({
      id: 'plan', type: 'scatter', total: 0, shown: 0, axes: { x: [-2, 2], y: [-2, 2] }, ui,
      series: [
        { ...base, id: 'plan.points.qr', slot: 'points', method: 'qr', role: 'method', label: 'λ', x: [0.5, -0.3], y: [0.2, 0.9] },
      ],
    }) as unknown as ViewResult
  const on = { methodsOn: new Set(['qr']), showReference: false }
  const shapes = (ui: Record<string, unknown> | null) => buildFigure(view(ui), on)!.layout.shapes as Record<string, unknown>[]

  it('aspect equal : une unité a la même longueur sur les deux axes, bornes gardées', () => {
    const y = buildFigure(view({ aspect: 'equal' }), on)!.layout.yaxis
    expect(y).toMatchObject({ scaleanchor: 'x', scaleratio: 1, constrain: 'domain', range: [-2, 2] })
    // Sans constrain sur x, Plotly élargit les bornes de x au lieu de resserrer la zone (vu à l'œil).
    expect(buildFigure(view({ aspect: 'equal' }), on)!.layout.xaxis).toMatchObject({ constrain: 'domain', range: [-2, 2] })
  })
  it('sans aspect : aucun ancrage', () => {
    expect((buildFigure(view(null), on)!.layout.yaxis as { scaleanchor?: string }).scaleanchor).toBeUndefined()
  })
  it('unit_circle : cercle de rayon 1 centré en 0, sous les données', () => {
    expect(shapes({ unit_circle: true })).toContainEqual(
      expect.objectContaining({ type: 'circle', x0: -1, y0: -1, x1: 1, y1: 1, layer: 'below' }),
    )
  })
  it('unit_circle à un nombre : rayon donné ; valeur invalide : pas de cercle', () => {
    expect(shapes({ unit_circle: 2 })).toContainEqual(expect.objectContaining({ type: 'circle', x1: 2 }))
    expect(shapes({ unit_circle: -1 }).some((s) => s.type === 'circle')).toBe(false)
    expect(shapes({ unit_circle: 'oui' }).some((s) => s.type === 'circle')).toBe(false)
    expect(shapes(null)).toEqual([])
  })
})

describe('Sensibilité en échelle logarithmique', () => {
  const view = { id: 'sens', type: 'sensitivity', series: [], axes: null, ui: { log_y: true } } as unknown as ViewResult
  const sweep = {
    axes: [{ target: 'p.seuil', values: [0, 0.5, 1], labels: ['0', '0,5', '1'] }],
    measure: 'exces',
    values: { main: [0.001, 0.01, 0] },
    mc_se: { main: [0.0006, 0.002, 0.001] },
    states: { main: ['ok', 'warning', 'ok'] },
    critical: { main: { warning_at: 0.4, broken_at: null } },
    target: 0, ok_within: 0.005, broken_beyond: 0.02, direction: 'above',
    current: { 'p.seuil': 0.5 }, repeat_used: 500, reduced: false, compute_ms: 1,
  } as unknown as SweepResult
  const fig = buildFigure(view, {
    methodsOn: new Set(['main']), showReference: false, sweep, roles: { main: 'method' },
    measure: { label: 'Erreurs en trop', unit: '%', scale: 100, decimals: 1 },
  })!
  const shapes = fig.layout.shapes as Record<string, number | string>[]
  const annotations = fig.layout.annotations as Record<string, number | string>[]

  it('bornes tirées des seules valeurs > 0, marge multiplicative, en log10', () => {
    // Plus petite valeur > 0 : 0,001 - 2 × 0,0006 < 0 est écarté, reste 0,001 (× 100 = 0,1) ; plus grande : 2 (limite de rupture).
    const y = fig.layout.yaxis as { type: string; range: number[] }
    expect(y.type).toBe('log')
    expect(y.range[0]).toBeCloseTo(Math.log10(0.1 / 1.5), 9)
    expect(y.range[1]).toBeCloseTo(Math.log10(2 * 1.5), 9)
  })
  it('formes en unités de données, annotations en log10 (règles de Plotly 4, vérifiées dans le navigateur)', () => {
    const rupture = annotations.find((a) => a.text === 'Rompu au-delà')!
    expect(rupture.y).toBeCloseTo(Math.log10(2), 9)
    const line = shapes.find((s) => s.type === 'line' && s.yref === 'y')!
    expect(line.y0).toBeCloseTo(2, 9)
    const rect = shapes.find((s) => s.type === 'rect')!
    expect(rect.y1).toBeCloseTo(0.5, 9)
    expect(rect.y0).toBeCloseTo(0.1 / 1.5, 9) // bord ≤ 0 ramené au bas de l'axe
  })
  it('la cible à 0 n’a pas de place sur une échelle log : ni ligne ni annotation', () => {
    expect(annotations.some((a) => a.text === 'Cible')).toBe(false)
    expect(shapes.filter((s) => s.type === 'line' && s.yref === 'y')).toHaveLength(1)
  })
  it('le bas de la bande d’erreur ne passe jamais sous 0', () => {
    const low = fig.data.find((t) => String(t.uid).startsWith('sens.bande-bas'))!.y as (number | null)[]
    for (const v of low) if (v !== null) expect(v).toBeGreaterThan(0)
  })
  it('les valeurs ≤ 0 sont comptées sous la vue', () => {
    expect(fig.caption).toEqual(['1 valeur négative ou nulle non affichée (échelle logarithmique)'])
  })
  it('lignes verticales (seuil critique, état actuel) inchangées sans log_x', () => {
    expect(shapes.filter((s) => s.xref === 'x').map((s) => s.x0)).toEqual([0.4, 0.5])
  })
  it('résidus en échelle log : pas de ligne 0', () => {
    const base = { layer: null, low: null, high: null, hit: null, value: null, paths: null }
    const res = {
      id: 'res', type: 'residuals', total: 0, shown: 0, axes: {}, ui: { log_y: true },
      series: [{ ...base, id: 'res.points.m', slot: 'points', method: 'm', role: 'method', label: 'r', x: [1], y: [1] }],
    } as unknown as ViewResult
    expect(buildFigure(res, { methodsOn: new Set(['m']), showReference: false })!.layout.shapes).toEqual([])
  })
})

describe('réinitialiser les axes', () => {
  it('prend les bornes du dernier dessin, pas celles du premier', () => {
    const full = { xaxis: { _rangeInitial0: 1.1, _rangeInitial1: 1.9 }, yaxis: {} as Record<string, unknown> }
    syncInitialRanges(full, { xaxis: { range: [-2.4, -1.6] }, yaxis: { range: [-1, 100] }, height: 340 })
    expect(full.xaxis).toMatchObject({ _rangeInitial0: -2.4, _rangeInitial1: -1.6 })
    expect(full.yaxis).toMatchObject({ _rangeInitial0: -1, _rangeInitial1: 100 })
  })

  it('laisse les axes automatiques et tolère un graphique pas encore prêt', () => {
    const full = { xaxis: { _rangeInitial0: 3 } as Record<string, unknown> }
    syncInitialRanges(full, { xaxis: { autorange: true } })
    expect(full.xaxis).toEqual({ _rangeInitial0: 3 })
    expect(() => syncInitialRanges(undefined, { xaxis: { range: [0, 1] } })).not.toThrow()
  })
})


describe('étiquettes courtes des axes de carte (Domaine de validité)', () => {
  it('retire la précision entre parenthèses, le nom reste lisible', () => {
    expect(shortTickLabels(['Normale', 'Exponentielle (asymétrique)', 'Student à 2 ddl (variance infinie)', 'Cauchy (sans espérance)']))
      .toEqual(['Normale', 'Exponentielle', 'Student à 2 ddl', 'Cauchy'])
  })
  it('laisse les nombres et les étiquettes sans parenthèse tels quels', () => {
    expect(shortTickLabels(['5', '10', '0,5'])).toEqual(['5', '10', '0,5'])
    expect(shortTickLabels(['Oui', 'Non'])).toEqual(['Oui', 'Non'])
  })
  it('garde les étiquettes complètes si le raccourci rendrait deux étiquettes identiques', () => {
    const labels = ['Loi (a)', 'Loi (b)']
    expect(shortTickLabels(labels)).toEqual(labels)
  })
  it('ne vide jamais une étiquette qui n’est qu’une parenthèse', () => {
    expect(shortTickLabels(['(saine)', 'autre'])).toEqual(['(saine)', 'autre'])
  })
})

describe('segments : plusieurs sortes dans une même vue (décomposition SCT, SCE, SCR)', () => {
  const segment = (id: string, label: string, layer: string): Series =>
    ({
      id, slot: 'segments', method: 'ols', role: 'method', label, layer,
      x: [1, 2], low: [0, 0], high: [1, 2], y: null, hit: null, value: null, paths: null,
    }) as unknown as Series
  const style = (t: ReturnType<typeof segmentsTrace>) => JSON.stringify((t as { line: unknown }).line)

  it('trois séries de segments ont trois styles différents (couleur et tireté), nom conservé pour la légende', () => {
    const three = [segment('d.segments-0.ols', 'y - moyenne', 'sct'), segment('d.segments-1.ols', 'prédiction - moyenne', 'sce'), segment('d.segments-2.ols', 'résidu', 'scr')]
    const traces = three.map((s, rank) => segmentsTrace(s, rank, three.length))
    expect(new Set(traces.map(style)).size).toBe(3)
    expect(new Set(traces.map((t) => (t as { line: { dash: string } }).line.dash)).size).toBe(3) // pas la couleur seule
    expect(traces.map((t) => (t as { name: string }).name)).toEqual(['y - moyenne', 'prédiction - moyenne', 'résidu'])
  })
  it('une seule sorte de segments garde le trait habituel (couleur du rôle, pointillé fin)', () => {
    const only = segmentsTrace(segment('c.segments-0.ols', 'résidu', 'scr'))
    expect((only as { line: { dash: string; width: number } }).line).toMatchObject({ dash: 'dot', width: 1 })
    expect(style(segmentsTrace(segment('c.segments-0.ols', 'résidu', 'scr'), 0, 1))).toBe(style(only))
  })
  it('au-delà de trois, les styles reviennent au début sans planter', () => {
    expect(segmentsTrace(segment('x', 'e', 'l'), 3, 4)).not.toBeNull()
  })
})

describe('aire sous la courbe (ui.fill_area)', () => {
  const base = { layer: null, low: null, high: null, hit: null, value: null, paths: null }
  const series = (id: string, role: string, label: string) => ({ ...base, id: `f.series.${id}`, slot: 'series', method: 'rect', role, label, x: [0, 0.5, 1], y: [0, 1, 0.5] })
  const view = (ui: Record<string, unknown> | null) =>
    ({
      id: 'f', type: 'curves', total: 0, shown: 0, axes: {}, ui,
      series: [series('ref', 'reference', 'Référence'), series('rect', 'method', 'f')],
    }) as unknown as ViewResult
  const on = { methodsOn: new Set(['rect']), showReference: true }
  const fills = (ui: Record<string, unknown> | null) =>
    Object.fromEntries(buildFigure(view(ui), on)!.data.map((t) => [String(t.uid), t.fill ?? null]))

  it('remplit l’aire de la courbe jusqu’à l’axe, pas celle de la Référence', () => {
    expect(fills({ fill_area: true })).toEqual({ 'f.series.ref': null, 'f.series.rect': 'tozeroy' })
    const trace = buildFigure(view({ fill_area: true }), on)!.data.find((t) => t.uid === 'f.series.rect')!
    expect(typeof trace.fillcolor).toBe('string') // translucide dans le navigateur (couleur résolue en hexadécimal)
  })
  it('sans le réglage, ou avec false, aucune aire (comportement d’avant)', () => {
    expect(fills(null)).toEqual({ 'f.series.ref': null, 'f.series.rect': null })
    expect(fills({ fill_area: false })).toEqual({ 'f.series.ref': null, 'f.series.rect': null })
  })
})
