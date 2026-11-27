/**
 * fakeViews.ts : FIXTURE PROVISOIRE de R3, pour développer PlotlyChart sans moteur.
 *
 * À SUPPRIMER dès que R1 fournit les vraies fixtures dans src/fixtures/ (make_fixtures.py).
 * Ce n'est PAS le moteur : une petite simulation en TypeScript, juste assez juste pour que les
 * graphiques ressemblent à ce que le moteur renverra (régression hétéroscédastique, MCO contre
 * HC3, et pendule Euler contre RK4). Les vues suivent le contrat (ViewResult, SweepResult de
 * types.gen.ts) et le contenu de Series.data décrit dans lib/views.ts.
 */

import type { Num, Range, Series, SweepResult, ViewResult } from '../lib/views'

type Role = Series['role']

/** Une série au format du contrat : id stable `<vue>.<emplacement>.<methode>`. */
function series(view: string, slot: string, method: string | null, role: Role, label: string, data: Record<string, unknown>): Series {
  const suffix = role === 'reference' ? '.ref' : ''
  return { id: `${view}.${slot}.${method ?? 'gen'}${suffix}`, method, role, label, layer: null, data }
}

/** Une vue au format du contrat. */
function view(
  id: string, type: string, title: string, axes: Record<string, Range>, shown: number, total: number,
  list: Series[], ui: Record<string, unknown> | null = null,
): ViewResult {
  return { id, type, title, axes, shown, total, clipped: 0, ui, data: { series: list } }
}

// --- Aléatoire déterministe (mulberry32 + Box-Muller) ---

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Tirages normaux communs : changer h déforme les mêmes tirages (comme le vrai moteur). */
function normals(seed: number, count: number): Float64Array {
  const u = mulberry32(seed)
  const out = new Float64Array(count)
  for (let i = 0; i < count; i += 2) {
    const r = Math.sqrt(-2 * Math.log(1 - u()))
    const th = 2 * Math.PI * u()
    out[i] = r * Math.cos(th)
    if (i + 1 < count) out[i + 1] = r * Math.sin(th)
  }
  return out
}

function quantile(values: number[], q: number): number {
  const s = [...values].sort((a, b) => a - b)
  const pos = (s.length - 1) * q
  const lo = Math.floor(pos)
  return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (pos - lo)
}

/** Bornes stables : quantiles 0,5 % et 99,5 % de la Référence, plus 10 % de marge (cahier 3.1). */
function stableRange(values: number[]): Range {
  const lo = quantile(values, 0.005)
  const hi = quantile(values, 0.995)
  const pad = (hi - lo) * 0.1
  return [lo - pad, hi + pad]
}

// --- Régression : MCO classique et HC3 ---

const N = 150
const BETA0 = 1
const BETA1 = 1.5
const T975 = 1.976 // quantile de Student à 148 ddl

interface Sample {
  x: number[]
  y: number[]
}

function sample(z: Float64Array, rep: number, h: number): Sample {
  const x: number[] = []
  const y: number[] = []
  const off = rep * 2 * N
  for (let i = 0; i < N; i++) {
    const xi = z[off + i]
    const eps = z[off + N + i] * Math.exp(0.9 * h * xi)
    x.push(xi)
    y.push(BETA0 + BETA1 * xi + eps)
  }
  return { x, y }
}

interface Fit {
  b0: number
  b1: number
  yHat: number[]
  resid: number[]
  se: { ols: number; hc3: number }
}

function fit({ x, y }: Sample): Fit {
  const n = x.length
  const mx = x.reduce((a, b) => a + b, 0) / n
  const my = y.reduce((a, b) => a + b, 0) / n
  let sxx = 0
  let sxy = 0
  for (let i = 0; i < n; i++) {
    sxx += (x[i] - mx) ** 2
    sxy += (x[i] - mx) * (y[i] - my)
  }
  const b1 = sxy / sxx
  const b0 = my - b1 * mx
  const yHat = x.map((xi) => b0 + b1 * xi)
  const resid = y.map((yi, i) => yi - yHat[i])
  const s2 = resid.reduce((a, e) => a + e * e, 0) / (n - 2)
  let hc3 = 0
  for (let i = 0; i < n; i++) {
    const lev = 1 / n + (x[i] - mx) ** 2 / sxx
    hc3 += ((x[i] - mx) ** 2 * resid[i] ** 2) / (1 - lev) ** 2
  }
  return { b0, b1, yHat, resid, se: { ols: Math.sqrt(s2 / sxx), hc3: Math.sqrt(hc3) / sxx } }
}

export interface RegressionFixture {
  views: Record<'nuage' | 'residus' | 'ic' | 'pentes', ViewResult>
  coverage: { ols: number; hc3: number }
}

const METHODS = [
  { id: 'ols', label: 'MCO classique (IC à 95 %)' },
  { id: 'hc3', label: 'Écarts-types robustes de White (HC3)' },
] as const

export const regressionMethods = [
  { id: 'ols', role: 'method' as const, label: METHODS[0].label },
  { id: 'hc3', role: 'correction' as const, label: METHODS[1].label },
]

export function regressionFixture(h: number, seed: number, reps = 500, shown = 100): RegressionFixture {
  const z = normals(seed, reps * 2 * N)
  const cur = sample(z, 0, h)
  const ref = sample(z, 0, 0)
  const fCur = fit(cur)
  const fRef = fit(ref)

  // Répétitions : intervalles MCO et HC3 sur les mêmes échantillons.
  const est: number[] = []
  const bounds = { ols: { low: [] as number[], high: [] as number[] }, hc3: { low: [] as number[], high: [] as number[] } }
  const refBounds: number[] = []
  let hits = { ols: 0, hc3: 0 }
  for (let r = 0; r < reps; r++) {
    const f = fit(sample(z, r, h))
    est.push(f.b1)
    for (const m of ['ols', 'hc3'] as const) {
      const lo = f.b1 - T975 * f.se[m]
      const hi = f.b1 + T975 * f.se[m]
      bounds[m].low.push(lo)
      bounds[m].high.push(hi)
      if (lo <= BETA1 && BETA1 <= hi) hits = { ...hits, [m]: hits[m] + 1 }
    }
    if (r < shown) {
      const fr = fit(sample(z, r, 0))
      refBounds.push(fr.b1 - T975 * fr.se.ols, fr.b1 + T975 * fr.se.ols)
    }
  }

  const axesXY = { x: stableRange(ref.x), y: stableRange(ref.y) }
  const residRange = stableRange(fRef.resid)

  const nuage = view('nuage', 'scatter', 'Nuage et droite ajustée', axesXY, N, N, [
    // Données du générateur : pas de méthode (method: null).
    series('nuage', 'xy', null, 'method', 'Observations', { x: cur.x, y: cur.y }),
    series('nuage', 'fit', 'ols', 'reference', 'Référence (état sain)', { x: ref.x, y: fRef.yHat }),
    // HC3 donne la même droite que les MCO (seule la variance change) : une seule série « fit ».
    series('nuage', 'fit', 'ols', 'method', METHODS[0].label, { x: cur.x, y: fCur.yHat }),
  ])

  const residus = view('residus', 'residuals', 'Résidus', { x: axesXY.x, y: residRange }, N, N, [
    series('residus', 'resid', 'ols', 'reference', 'Référence (état sain)', { x: ref.x, y: fRef.resid }),
    series('residus', 'resid', 'ols', 'method', 'Résidus MCO', { x: cur.x, y: fCur.resid }),
  ], { x_title: 'x', y_title: 'Résidu' })

  const take = <T,>(a: T[]) => a.slice(0, shown)
  const hitOf = (m: 'ols' | 'hc3') => take(bounds[m].low).map((lo, i) => lo <= BETA1 && BETA1 <= bounds[m].high[i])
  const ic = view('ic', 'repetitions', '100 intervalles de confiance empilés', { x: stableRange(refBounds) }, shown, reps, [
    ...(['ols', 'hc3'] as const).map((m, k) =>
      series('ic', 'est', m, k === 0 ? 'method' : 'correction', METHODS[k].label, {
        est: take(est), low: take(bounds[m].low), high: take(bounds[m].high), hit: hitOf(m),
      }),
    ),
    series('ic', 'truth', null, 'truth', 'Vraie pente', { value: BETA1 }),
  ])

  const pentes = view('pentes', 'distribution', 'Distribution des pentes estimées', { x: stableRange(est) }, reps, reps, [
    series('pentes', 'stat', 'ols', 'method', 'Pente estimée (MCO)', { x: est }),
    series('pentes', 'truth', null, 'truth', 'Vraie pente', { value: BETA1 }),
  ])

  return { views: { nuage, residus, ic, pentes }, coverage: { ols: hits.ols / reps, hc3: hits.hc3 / reps } }
}

/** Balayage de h (11 points) : couverture MCO et HC3, avec le seuil critique interpolé. */
export function regressionSweep(h: number, seed: number, reps = 300): SweepResult {
  const hs = Array.from({ length: 11 }, (_, i) => i / 10)
  const z = normals(seed, reps * 2 * N)
  const values: Record<string, Num[]> = { ols: [], hc3: [] }
  for (const hv of hs) {
    const c = { ols: 0, hc3: 0 }
    for (let r = 0; r < reps; r++) {
      const f = fit(sample(z, r, hv))
      for (const m of ['ols', 'hc3'] as const) {
        if (Math.abs(f.b1 - BETA1) <= T975 * f.se[m]) c[m] += 1
      }
    }
    values.ols.push(c.ols / reps)
    values.hc3.push(c.hc3 / reps)
  }
  const target = 0.95
  const ok = 0.03
  const broken = 0.1
  const state = (v: Num) =>
    v === null ? null : target - v <= ok ? ('ok' as const) : target - v > broken ? ('broken' as const) : ('warning' as const)
  const crossing = (vals: Num[], limit: number): Num => {
    for (let i = 1; i < vals.length; i++) {
      const a = vals[i - 1] as number
      const b = vals[i] as number
      if (a >= limit && b < limit) return hs[i - 1] + ((a - limit) / (a - b)) * (hs[i] - hs[i - 1])
    }
    return null
  }
  const se = (vals: Num[]) => vals.map((v) => (v === null ? null : Math.sqrt((v * (1 - v)) / reps)))
  return {
    axes: [{ target: 'h.hetero', values: hs, labels: hs.map((v) => v.toFixed(1).replace('.', ',')) }],
    measure: 'coverage',
    values,
    mc_se: { ols: se(values.ols), hc3: se(values.hc3) },
    states: { ols: values.ols.map(state), hc3: values.hc3.map(state) },
    critical: {
      ols: { warning_at: crossing(values.ols, target - ok), broken_at: crossing(values.ols, target - broken) },
      hc3: null,
    },
    target, ok_within: ok, broken_beyond: broken, direction: 'below',
    current: { 'h.hetero': h },
    repeat_used: reps,
    reduced: false,
    compute_ms: 0,
  }
}

// --- Pendule : Euler explicite et RK4 ---

export const pendulumMethods = [
  { id: 'euler', role: 'method' as const, label: 'Euler explicite' },
  { id: 'rk4', role: 'correction' as const, label: "Runge-Kutta d'ordre 4" },
]

type Scheme = 'euler' | 'rk4'

function integrate(theta0: number, tEnd: number, dt: number, scheme: Scheme, grid: number[]): number[] {
  const f = (th: number, om: number): [number, number] => [om, -9.81 * Math.sin(th)]
  let th = theta0
  let om = 0
  let t = 0
  const out: number[] = []
  let g = 0
  let prev: [number, number] = [0, th]
  while (g < grid.length) {
    while (g < grid.length && grid[g] <= t) {
      // Interpolation linéaire entre le pas précédent et le pas courant.
      const [tp, thp] = prev
      out.push(t === tp ? th : thp + ((th - thp) * (grid[g] - tp)) / (t - tp))
      g++
    }
    if (t > tEnd) break
    prev = [t, th]
    if (scheme === 'euler') {
      const [a, b] = f(th, om)
      th += dt * a
      om += dt * b
    } else {
      const k1 = f(th, om)
      const k2 = f(th + (dt / 2) * k1[0], om + (dt / 2) * k1[1])
      const k3 = f(th + (dt / 2) * k2[0], om + (dt / 2) * k2[1])
      const k4 = f(th + dt * k3[0], om + dt * k3[1])
      th += (dt / 6) * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
      om += (dt / 6) * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    }
    t += dt
  }
  return out
}

export function pendulumFixture(pas: number, theta0 = 1.2, tEnd = 5): { view: ViewResult; errors: Record<Scheme, number> } {
  const grid = Array.from({ length: 400 }, (_, i) => (i * tEnd) / 399)
  const dt = 10 ** (-3.5 + 2.5 * pas)
  const truth = integrate(theta0, tEnd, 1e-3, 'rk4', grid)
  const euler = integrate(theta0, tEnd, dt, 'euler', grid)
  const rk4 = integrate(theta0, tEnd, dt, 'rk4', grid)
  const err = (a: number[]) => Math.max(...a.map((v, i) => Math.abs(v - truth[i]))) / theta0
  return {
    view: view('trajectoire', 'curves', 'Angle au cours du temps', { x: [0, tEnd], y: [-theta0 * 1.6, theta0 * 1.6] }, 400, 400, [
      series('trajectoire', 'truth', null, 'truth', 'Solution de référence', { x: grid, y: truth }),
      series('trajectoire', 'series', 'euler', 'method', 'Euler explicite', { x: grid, y: euler }),
      series('trajectoire', 'series', 'rk4', 'correction', "Runge-Kutta d'ordre 4", { x: grid, y: rk4 }),
    ], { x_title: 'Temps (s)', y_title: 'Angle (rad)' }),
    errors: { euler: err(euler), rk4: err(rk4) },
  }
}
