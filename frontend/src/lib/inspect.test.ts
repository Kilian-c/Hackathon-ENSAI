import { describe, expect, it } from 'vitest'
import {
  cardSide,
  inspectableCount,
  inspectionFor,
  injectedIndex,
  isObservationSeries,
  nearestTarget,
  selectionFor,
  selectionHolds,
} from './inspect'
import { buildFigure, pointTargets, INJECTED_SUFFIX, OBSERVATION_META, SELECTION_SUFFIX, type ChartOptions } from './plot'
import type { EngineState } from './types.gen'
import type { Series, ViewResult } from './views'

const empty = { method: null, layer: null, low: null, high: null, hit: null, value: null, paths: null, x: null, y: null }
const series = (s: Partial<Series> & Pick<Series, 'id' | 'slot' | 'role'>): Series => ({ ...empty, label: '', ...s })

// Cinq observations ; la dernière, loin à droite, sort du cadre. Somme des leviers = 2.
const x = [0, 1, 2, 3, 10]
const y = [0, 1.5, 1.5, 3, -2]
const fit = [0.5, 1, 1.5, 2, 5.5]
const resid = y.map((v, i) => v - fit[i])
const leverage = [0.3, 0.2, 0.2, 0.2, 1.1]
const cooks = [0.1, 0.05, 0, 0.2, 4]

function view(extra: Series[] = []): ViewResult {
  // Comme le moteur : les abscisses ne sont portées que par la première série.
  const inspect = (key: string, values: number[]) =>
    series({
      id: `nuage.inspect.${key}`, slot: `inspect.${key}`, method: 'ols', role: 'method',
      x: key === 'y' ? x : null, y: values,
    })
  return {
    id: 'nuage', type: 'scatter', title: 'Nuage', mode: null, ui: null,
    axes: { x: [-1, 5], y: [-1, 4] }, shown: 5, total: 5, clipped: 0,
    series: [
      series({ id: 'nuage.xy.gen', slot: 'xy', role: 'data', x, y }),
      series({ id: 'nuage.fit.ols', slot: 'fit', method: 'ols', role: 'method', x, y: fit }),
      series({ id: 'nuage.fit.ols.ref', slot: 'fit', method: 'ols', role: 'reference', x, y: fit }),
      inspect('y', y), inspect('y_hat', fit), inspect('resid', resid),
      inspect('leverage', leverage), inspect('cooks_d', cooks),
      ...extra,
    ],
  }
}

const state = (over: Partial<EngineState> = {}): EngineState => ({
  params: {}, hypotheses: {}, extra_points: [], seed: 42, ...over,
})
const opts = (over: Partial<ChartOptions> = {}): ChartOptions => ({
  methodsOn: new Set(['ols']), showReference: true, ...over,
})

describe('inspecteur : la fiche', () => {
  it('donne les grandeurs de l’observation et les deux seuils', () => {
    const card = inspectionFor(view(), 4)!
    expect(card).toMatchObject({ index: 4, total: 5, x: 10, y: -2, fitted: 5.5, resid: -7.5 })
    expect(card.leverageLimit).toBeCloseTo(0.8) // 2 × la moyenne des leviers = 2p/n avec p = 2 et n = 5
    expect(card.cooksLimit).toBeCloseTo(0.8) // 4 / n
    expect(card.highLeverage).toBe(true)
    expect(card.influential).toBe(true)
    const ordinary = inspectionFor(view(), 1)!
    expect([ordinary.highLeverage, ordinary.influential]).toEqual([false, false])
  })

  it('les parts dans la somme des carrés des résidus font 1', () => {
    const total = [0, 1, 2, 3, 4].reduce((sum, i) => sum + inspectionFor(view(), i)!.ssrShare!, 0)
    expect(total).toBeCloseTo(1)
  })

  it('n’affiche que ce qui est fourni (aucune hypothèse sur la méthode)', () => {
    const partial = view()
    partial.series = partial.series.filter((s) => !['inspect.leverage', 'inspect.cooks_d'].includes(s.slot))
    expect(inspectionFor(partial, 4)).toMatchObject({
      leverage: null, leverageLimit: null, highLeverage: false, cooks: null, cooksLimit: null, influential: false,
    })
  })

  it('refuse un indice hors de l’échantillon et une vue sans inspecteur', () => {
    expect(inspectionFor(view(), 5)).toBeNull()
    expect(inspectionFor(view(), -1)).toBeNull()
    const plain = view()
    plain.series = plain.series.filter((s) => !s.slot.startsWith('inspect.'))
    expect(inspectableCount(plain)).toBe(0)
    expect(inspectionFor(plain, 0)).toBeNull()
  })

  it('reconnaît les observations, jamais la Référence', () => {
    const [data, fitted, reference] = view().series
    expect(isObservationSeries(view(), data)).toBe(true)
    expect(isObservationSeries(view(), { ...data, role: 'reference' })).toBe(false)
    expect(isObservationSeries(view(), { ...fitted, x: [0, 1] })).toBe(false)
    expect(isObservationSeries(view(), reference)).toBe(false)
  })
})

describe('inspecteur : la sélection', () => {
  const posed = state({ extra_points: [{ x: 3, y: 3 }, { x: 10, y: -2 }] }) // 3 générées, 2 posées

  it('reconnaît un point posé : les dernières observations', () => {
    expect(injectedIndex(5, 2, 0)).toBe(3)
    expect(selectionFor(view(), posed, 4)).toMatchObject({ index: 4, base: 3, injected: 1, point: { x: 10, y: -2 } })
    expect(selectionFor(view(), posed, 2)).toMatchObject({ injected: null, point: null })
    expect(selectionFor(view(), posed, 9)).toBeNull()
  })

  it('tient quand une hypothèse change, se ferme quand le tirage ou la taille changent', () => {
    const sel = selectionFor(view(), state(), 2)!
    expect(selectionHolds(sel, view(), state({ hypotheses: { h: 0.8 } }))).toBe(true)
    expect(selectionHolds(sel, view(), state({ seed: 43 }))).toBe(false)
    expect(selectionHolds({ ...sel, base: 4 }, view(), state())).toBe(false)
  })

  it('tient quand on ajoute un point, se ferme quand le point inspecté est retiré', () => {
    const generated = selectionFor(view(), state(), 2)!
    const added = state({ extra_points: [{ x: 10, y: -2 }] })
    const bigger = view()
    bigger.series = bigger.series.map((s) =>
      s.slot.startsWith('inspect.') ? { ...s, x: s.x ? [...x, 11] : null, y: [...s.y!, 0] } : s)
    expect(selectionHolds(generated, bigger, added)).toBe(true)
    const mine = selectionFor(view(), posed, 3)!
    // Le premier point posé est retiré : le second prend son rang, la fiche ne doit pas « glisser ».
    const smaller = view()
    smaller.series = smaller.series.map((s) =>
      s.slot.startsWith('inspect.') ? { ...s, x: s.x ? x.slice(0, 4) : null, y: s.y!.slice(0, 4) } : s)
    expect(selectionHolds(mine, smaller, state({ extra_points: [{ x: 10, y: -2 }] }))).toBe(false)
  })
})

describe('inspecteur : le dessin', () => {
  const traces = (o: ChartOptions) => buildFigure(view(), o)!.data as Record<string, unknown>[]

  it('ne dessine jamais les séries inspect.*', () => {
    expect(traces(opts()).some((t) => String(t.uid).includes('.inspect.'))).toBe(false)
  })

  it('pose le numéro d’observation sur les points du cadre et hors cadre, pas sur la droite', () => {
    const drawn = traces(opts({ inspectable: true }))
    const inside = drawn.find((t) => t.uid === 'nuage.xy.gen')!
    const outside = drawn.find((t) => t.uid === 'nuage.xy.gen.hors-cadre')!
    expect(inside.meta).toBe(OBSERVATION_META)
    expect(inside.customdata).toEqual([0, 1, 2, 3])
    expect(outside.meta).toBe(OBSERVATION_META)
    expect(outside.customdata).toEqual([4])
    expect(drawn.filter((t) => t.meta === OBSERVATION_META)).toHaveLength(2)
  })

  it('sans inspecteur (Entraînement), rien ne change', () => {
    const drawn = traces(opts())
    expect(drawn.some((t) => t.meta === OBSERVATION_META)).toBe(false)
    expect(buildFigure(view(), opts())!.layout.hoverdistance).toBeUndefined()
    expect(buildFigure(view(), opts({ inspectable: true }))!.layout.hoverdistance).toBe(8)
  })

  it('entoure l’observation choisie, au bord si elle est hors cadre', () => {
    expect(traces(opts({ inspectable: true })).some((t) => String(t.uid).endsWith(SELECTION_SUFFIX))).toBe(false)
    const ring = traces(opts({ inspectable: true, selected: 2 })).find((t) => t.uid === `nuage${SELECTION_SUFFIX}`)!
    expect([ring.x, ring.y, ring.hoverinfo]).toEqual([[2], [1.5], 'skip'])
    const far = traces(opts({ inspectable: true, selected: 4 })).find((t) => t.uid === `nuage${SELECTION_SUFFIX}`)!
    expect([far.x, far.y]).toEqual([[5], [-1]])
  })

  it('l’étoile annonce le bon geste', () => {
    const star = (o: ChartOptions) => traces(o).find((t) => String(t.uid).endsWith(INJECTED_SUFFIX))!
    const injected = [{ x: 10, y: -2 }]
    expect(String(star(opts({ injected })).hovertemplate)).toContain('retirer')
    expect(String(star(opts({ injected, inspectable: true })).hovertemplate)).toContain('inspecter')
  })
})

describe('inspecteur : le point visé par un clic', () => {
  const targets = () =>
    pointTargets(buildFigure(view(), opts({ inspectable: true, injected: [{ x: 3, y: 3 }] }))!.data as Record<string, unknown>[])
  const identity = (x: number, y: number) => [x * 100, y * 100] as const // 100 px par unité

  it('propose les observations, y compris hors cadre, puis les étoiles', () => {
    expect(targets().map((c) => c.target)).toEqual([
      { index: 0 }, { index: 1 }, { index: 2 }, { index: 3 }, { index: 4 }, { injected: 0 },
    ])
  })

  it('trouve le triangle posé sur le bord, même cliqué juste en dehors du cadre', () => {
    // L'observation 4 (10 ; −2) est ramenée au coin (5 ; −1) : clic 6 px plus bas, hors du cadre.
    expect(nearestTarget(targets(), identity, [500, -106], 8)).toEqual({ index: 4 })
  })

  it('ignore un point que le zoom a sorti du cadre, mais garde ceux du bord', () => {
    // Le triangle est projeté en (500 ; −100) : au-dessus d'un cadre qui commence à 0.
    expect(nearestTarget(targets(), identity, [500, -98], 8, [600, 400])).toBeNull()
    expect(nearestTarget(targets(), identity, [500, -98], 8)).toEqual({ index: 4 })
    // L'étoile (300 ; 300), posée exactement sur le bord d'un cadre de 300 px, reste cliquable.
    expect(nearestTarget(targets(), identity, [303, 303], 8, [300, 300])).toEqual({ injected: 0 })
  })

  it('préfère l’étoile quand elle recouvre une observation, et ignore un clic dans le vide', () => {
    expect(nearestTarget(targets(), identity, [301, 301], 8)).toEqual({ injected: 0 })
    expect(nearestTarget(targets(), identity, [150, 320], 8)).toBeNull()
    expect(nearestTarget(targets(), identity, [100, 160], 8)).toBeNull() // à 10 px : trop loin
    expect(nearestTarget(targets(), identity, [100, 156], 8)).toEqual({ index: 1 })
  })
})

describe('inspecteur : le placement de la fiche', () => {
  it('la pose à l’opposé du point choisi (milieu des bornes de la vue : 2)', () => {
    expect(cardSide(view(), 0)).toBe('right')
    expect(cardSide(view(), 4)).toBe('left')
    expect(cardSide(view(), 10)).toBe('left')
  })

  it('sans bornes, prend le milieu des observations ; sans abscisse, reste à gauche', () => {
    const free = { ...view(), axes: { x: null, y: null } }
    expect(cardSide(free, 4)).toBe('right') // observations de 0 à 10 : milieu 5
    expect(cardSide(view(), null)).toBe('left')
  })
})
