/**
 * plot.ts : construit la figure Plotly (traces + mise en page) d'une vue (R3).
 *
 * Fonctions pures, sans Svelte, testées par plot.test.ts. PlotlyChart.svelte ne fait que
 * passer le résultat à Plotly.react(). Aucune connaissance d'un théorème : tout vient du type
 * de vue, de l'emplacement (`slot`) et du rôle de chaque série.
 *
 * Règles du cahier (section 3.1, annexe E) appliquées ici :
 * - axes fixes : bornes reçues du moteur (calculées sur la Référence), jamais recalculées ;
 * - points hors cadre dessinés au bord avec un triangle, et comptés ;
 * - jamais la couleur seule : trait, marqueur ou motif propres à chaque rôle ;
 * - identifiants de traces stables (uid = id de la série) pour que Plotly anime proprement.
 */

import { cssVar, plotlyStyle, verdictColor, type DisplayRole } from './roles'
import type { MeasureFormat, Num, Range, SweepData, ViewData, ViewSeries } from './views'

export type Trace = Record<string, unknown>
export type Layout = Record<string, unknown>

export interface Figure {
  data: Trace[]
  layout: Layout
  /** Phrases à afficher sous la vue (« 100 affichés sur 500 calculés », « 3 points hors cadre »). */
  caption: string[]
}

export interface ChartOptions {
  /** Rôle d'affichage de chaque méthode (roles.displayRoles). */
  roles: Readonly<Record<string, DisplayRole>>
  /** Méthodes affichées (état d'affichage). */
  methodsOn: ReadonlySet<string>
  /** Afficher la Référence (état sain) en arrière-plan. */
  showReference: boolean
  /** Vue Sensibilité : résultat du balayage (POST /api/sweep), null pendant le chargement. */
  sweep?: SweepData | null
  /** Vue Sensibilité : mise en forme de la mesure balayée. */
  measure?: MeasureFormat | null
  /** Libellé de chaque méthode (RunResult.methods[].label), pour les légendes. */
  methodLabels?: Readonly<Record<string, string>>
}

/** Emplacements dessinés en ligne ; les autres sont des points. */
const LINE_SLOTS = new Set(['fit', 'trend', 'series', 'truth', 'paths'])

/** Motif de remplissage par rôle (histogrammes, barres) : la couleur n'est jamais le seul indice. */
const PATTERN: Partial<Record<DisplayRole, string>> = {
  method: '',
  correction: '/',
  alternative_1: 'x',
  alternative_2: '.',
  reference: '',
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

export function seriesRole(s: ViewSeries, roles: ChartOptions['roles']): DisplayRole | null {
  if (s.role === 'reference') return 'reference'
  if (s.role === 'truth') return 'truth'
  if (s.role === 'data') return null
  if (s.method && roles[s.method]) return roles[s.method]
  return s.role === 'alternative' ? 'alternative_1' : s.role
}

export function isVisible(s: ViewSeries, opts: ChartOptions): boolean {
  if (s.role === 'data' || s.role === 'truth') return true
  const methodShown = s.method === null || opts.methodsOn.has(s.method)
  return s.role === 'reference' ? opts.showReference && methodShown : methodShown
}

function isNum(v: Num | undefined): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/** Couleur hexadécimale avec transparence (pour les bandes) ; renvoie la couleur telle quelle sinon. */
export function withAlpha(color: string, alpha: number): string {
  const m = /^#([0-9a-f]{6})$/i.exec(color)
  if (!m) return color
  const n = parseInt(m[1], 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}

export interface Clamped {
  inside: { x: number[]; y: number[] }
  outside: { x: number[]; y: number[]; symbol: string[] }
}

/** Sépare les points dans le cadre de ceux qui en sortent ; ces derniers sont ramenés au bord. */
export function clampPoints(x: Num[], y: Num[], rx?: Range | null, ry?: Range | null): Clamped {
  const out: Clamped = { inside: { x: [], y: [] }, outside: { x: [], y: [], symbol: [] } }
  const n = Math.min(x.length, y.length)
  for (let i = 0; i < n; i++) {
    const xi = x[i]
    const yi = y[i]
    if (!isNum(xi) || !isNum(yi)) continue
    let cx = xi
    let cy = yi
    let symbol: string | null = null
    if (ry) {
      if (yi > ry[1]) [cy, symbol] = [ry[1], 'triangle-up']
      else if (yi < ry[0]) [cy, symbol] = [ry[0], 'triangle-down']
    }
    if (rx) {
      if (xi > rx[1]) [cx, symbol] = [rx[1], symbol ?? 'triangle-right']
      else if (xi < rx[0]) [cx, symbol] = [rx[0], symbol ?? 'triangle-left']
    }
    if (symbol) {
      out.outside.x.push(cx)
      out.outside.y.push(cy)
      out.outside.symbol.push(symbol)
    } else {
      out.inside.x.push(cx)
      out.inside.y.push(cy)
    }
  }
  return out
}

function pointsStyle(role: DisplayRole | null): Trace {
  if (role === null) {
    return { mode: 'markers', marker: { color: cssVar('--ct-plot-data'), size: 5, opacity: 0.75 } }
  }
  const s = plotlyStyle(role, 'markers') as { mode: string; marker: Record<string, unknown> }
  return { mode: 'markers', marker: { ...s.marker, size: 6, opacity: role === 'reference' ? 0.6 : 0.9 } }
}

/** Points d'une série, avec les points hors cadre ramenés au bord (triangles). */
function markerTraces(s: ViewSeries, role: DisplayRole | null, view: ViewData): { traces: Trace[]; clipped: number } {
  const { inside, outside } = clampPoints(s.x ?? [], s.y ?? [], view.axes.x, view.axes.y)
  const style = pointsStyle(role)
  const marker = style.marker as Record<string, unknown>
  const traces: Trace[] = [
    { type: 'scatter', uid: s.id, name: s.label, x: inside.x, y: inside.y, ...style, legendgroup: s.id },
  ]
  if (outside.x.length > 0) {
    traces.push({
      type: 'scatter',
      uid: `${s.id}.hors-cadre`,
      name: `${s.label} (hors cadre)`,
      mode: 'markers',
      x: outside.x,
      y: outside.y,
      marker: { color: marker.color, symbol: outside.symbol, size: 10, line: { width: 0 } },
      cliponaxis: false, // le triangle est posé sur le bord : ne pas le couper
      showlegend: false,
      legendgroup: s.id,
      hovertemplate: 'Point hors cadre<extra></extra>',
    })
  }
  return { traces, clipped: outside.x.length }
}

/** Ligne d'une série, triée par x (une droite ajustée arrive dans l'ordre des observations). */
function lineTrace(s: ViewSeries, role: DisplayRole | null): Trace {
  const pairs: [number, number][] = []
  const x = s.x ?? []
  const y = s.y ?? []
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const xi = x[i]
    const yi = y[i]
    if (isNum(xi) && isNum(yi)) pairs.push([xi, yi])
  }
  if (s.slot !== 'series') pairs.sort((a, b) => a[0] - b[0])
  const style = role ? plotlyStyle(role, 'lines') : { mode: 'lines', line: { color: cssVar('--ct-plot-data'), width: 1.5 } }
  return {
    type: 'scatter',
    uid: s.id,
    name: s.label,
    x: pairs.map((p) => p[0]),
    y: pairs.map((p) => p[1]),
    ...style,
    mode: 'lines',
    legendgroup: s.id,
  }
}

/** Ligne verticale (vraie valeur, seuil) sous forme de forme Plotly, avec son libellé. */
function verticalLine(x: number, color: string, dash: string, text?: string): { shape: Trace; annotation?: Trace } {
  return {
    shape: { type: 'line', xref: 'x', yref: 'paper', x0: x, x1: x, y0: 0, y1: 1, line: { color, dash, width: 1.5 } },
    annotation: text
      ? { x, xref: 'x', y: 1, yref: 'paper', yanchor: 'bottom', text, showarrow: false, font: { color, size: 11 } }
      : undefined,
  }
}

// ---------------------------------------------------------------------------
// Mise en page commune
// ---------------------------------------------------------------------------

function axisLayout(range: Range | null | undefined, title?: string): Trace {
  const grid = cssVar('--ct-plot-grid')
  return {
    ...(range ? { range: [...range], autorange: false } : { autorange: true }),
    gridcolor: grid,
    zerolinecolor: grid,
    linecolor: grid,
    tickfont: { color: cssVar('--ct-plot-axis') },
    title: title ? { text: title, font: { color: cssVar('--ct-plot-axis'), size: 12 } } : undefined,
  }
}

export function baseLayout(view: ViewData, extra: Layout = {}): Layout {
  const ui = view.ui ?? {}
  return {
    uirevision: 'keep',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: cssVar('--ct-plot-bg'),
    font: { family: cssVar('--ct-font'), color: cssVar('--ct-text'), size: 12 },
    separators: ', ',
    // Légende ancrée au bas de la figure (et non de la zone de tracé) : elle ne chevauche jamais
    // le titre de l'axe x, quelle que soit la hauteur.
    margin: { l: 56, r: 16, t: 24, b: 84 },
    showlegend: true,
    legend: {
      orientation: 'h', x: 0, xanchor: 'left', yref: 'container', y: 0, yanchor: 'bottom',
      font: { color: cssVar('--ct-plot-axis') },
    },
    hovermode: 'closest',
    xaxis: axisLayout(view.axes.x, typeof ui.x_title === 'string' ? ui.x_title : undefined),
    yaxis: axisLayout(view.axes.y, typeof ui.y_title === 'string' ? ui.y_title : undefined),
    shapes: [],
    annotations: [],
    ...extra,
  }
}

function captionFor(view: ViewData, clipped: number): string[] {
  const out: string[] = []
  if (view.total > view.shown) out.push(`${view.shown} affichés sur ${view.total} calculés`)
  const c = Math.max(clipped, view.clipped ?? 0)
  if (c > 0) out.push(c === 1 ? '1 point hors cadre' : `${c} points hors cadre`)
  return out
}

// ---------------------------------------------------------------------------
// Vues
// ---------------------------------------------------------------------------

/** Nuage, résidus, courbes : chaque série est une ligne ou des points selon son emplacement. */
function xyFigure(view: ViewData, opts: ChartOptions): Figure {
  const data: Trace[] = []
  let clipped = 0
  const visible = view.series.filter((s) => isVisible(s, opts) && s.x && s.y)
  // Référence d'abord, pour qu'elle reste derrière.
  visible.sort((a, b) => Number(b.role === 'reference') - Number(a.role === 'reference'))
  for (const s of visible) {
    const role = seriesRole(s, opts.roles)
    if (LINE_SLOTS.has(s.slot) || view.type === 'curves') {
      data.push(lineTrace(s, role))
    } else {
      const m = markerTraces(s, role, view)
      data.push(...m.traces)
      clipped += m.clipped
    }
  }
  const shapes: Trace[] = []
  if (view.type === 'residuals') {
    shapes.push({
      type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 0, y1: 0,
      line: { color: cssVar('--ct-plot-axis'), width: 1 },
    })
  }
  return { data, layout: baseLayout(view, { shapes }), caption: captionFor(view, clipped) }
}

/** Répétitions (intervalles) : un intervalle par ligne, les ratés en rouge avec une croix. */
function intervalsFigure(view: ViewData, opts: ChartOptions): Figure {
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const rupture = cssVar('--ct-role-rupture')
  const series = view.series.filter((s) => isVisible(s, opts) && s.low && s.high && s.x)
  const spacing = series.length > 1 ? 0.8 / series.length : 0
  let rows = 0

  series.forEach((s, k) => {
    const role = seriesRole(s, opts.roles) ?? 'method'
    const color = (plotlyStyle(role, 'markers').marker as { color: string }).color
    const symbol = (plotlyStyle(role, 'markers').marker as { symbol: string }).symbol
    const est = s.x ?? []
    const low = s.low ?? []
    const high = s.high ?? []
    const hit = s.hit ?? []
    rows = Math.max(rows, est.length)
    const groups = { ok: [] as number[], miss: [] as number[] }
    est.forEach((e, i) => {
      if (isNum(e) && isNum(low[i]) && isNum(high[i])) (hit[i] ? groups.ok : groups.miss).push(i)
    })
    for (const [kind, idx] of Object.entries(groups) as ['ok' | 'miss', number[]][]) {
      const c = kind === 'ok' ? color : rupture
      data.push({
        type: 'scatter',
        mode: 'markers',
        uid: `${s.id}.${kind === 'ok' ? 'couvre' : 'rate'}`,
        name: kind === 'ok' ? s.label : `${s.label} : ratés`,
        legendgroup: s.id,
        x: idx.map((i) => est[i]),
        y: idx.map((i) => i + k * spacing),
        customdata: idx.map((i) => [low[i], high[i], i + 1]),
        hovertemplate: 'Répétition %{customdata[2]} : [%{customdata[0]:.3f} ; %{customdata[1]:.3f}]<extra></extra>',
        marker: { color: c, symbol: kind === 'ok' ? symbol : 'x', size: kind === 'ok' ? 4 : 7 },
        error_x: {
          type: 'data',
          symmetric: false,
          array: idx.map((i) => (high[i] as number) - (est[i] as number)),
          arrayminus: idx.map((i) => (est[i] as number) - (low[i] as number)),
          color: c,
          thickness: role === 'correction' ? 2 : 1.2,
          width: 0,
        },
      })
    }
  })

  for (const t of view.series.filter((s) => s.role === 'truth' && isNum(s.value))) {
    const v = verticalLine(t.value as number, cssVar('--ct-role-truth'), 'solid', t.label)
    shapes.push(v.shape)
    if (v.annotation) annotations.push(v.annotation)
  }

  const layout = baseLayout(view, { shapes, annotations })
  layout.yaxis = { ...(layout.yaxis as Trace), range: [-1, Math.max(rows, 1)], autorange: false, showticklabels: false, title: undefined }
  return { data, layout, caption: captionFor(view, 0) }
}

/** Distribution : histogrammes superposés, bacs fixés par les bornes de l'axe. */
function distributionFigure(view: ViewData, opts: ChartOptions): Figure {
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const rx = view.axes.x
  const bins = rx ? { start: rx[0], end: rx[1], size: (rx[1] - rx[0]) / 40 } : undefined
  for (const s of view.series.filter((x) => isVisible(x, opts))) {
    if (isNum(s.value)) {
      const color = s.role === 'truth' ? cssVar('--ct-role-truth') : cssVar('--ct-plot-axis')
      const v = verticalLine(s.value, color, s.role === 'truth' ? 'solid' : 'dot', s.label)
      shapes.push(v.shape)
      if (v.annotation) annotations.push(v.annotation)
      continue
    }
    const role = seriesRole(s, opts.roles) ?? 'method'
    const color = (plotlyStyle(role, 'markers').marker as { color: string }).color
    data.push({
      type: 'histogram',
      uid: s.id,
      name: s.label,
      x: (s.x ?? []).filter(isNum),
      histnorm: 'probability density',
      xbins: bins,
      autobinx: bins ? false : undefined,
      opacity: role === 'reference' ? 0.35 : 0.6,
      marker: {
        color: withAlpha(color, role === 'reference' ? 0.25 : 0.55),
        line: { color, width: 1 },
        pattern: { shape: PATTERN[role] ?? '', fgcolor: color, size: 6 },
      },
    })
  }
  return { data, layout: baseLayout(view, { barmode: 'overlay', shapes, annotations }), caption: captionFor(view, 0) }
}

/** Sensibilité : la mesure selon la perturbation, bande de tolérance, seuil critique. */
function sensitivityFigure(view: ViewData, opts: ChartOptions): Figure {
  const sweep = opts.sweep
  if (!sweep || sweep.axes.length === 0) {
    return { data: [], layout: baseLayout(view), caption: ['Balayage en cours…'] }
  }
  const scale = opts.measure?.scale ?? 1
  const unit = opts.measure?.unit ?? ''
  const axis = sweep.axes[0]
  const numeric = axis.values.every((v) => typeof v === 'number')
  const methods = Object.keys(sweep.values).filter((m) => opts.methodsOn.has(m))
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const scaled = (v: Num | undefined) => (isNum(v) ? v * scale : null)

  // Bornes verticales : valeurs, marges et cible, pour que la bande de tolérance soit visible.
  const all: number[] = []
  for (const m of methods) {
    sweep.values[m].forEach((v, i) => {
      const se = sweep.mc_se[m]?.[i]
      if (isNum(v)) all.push(v - 2 * (isNum(se) ? se : 0), v + 2 * (isNum(se) ? se : 0))
    })
  }
  const { target, ok_within: ok, broken_beyond: broken, direction } = sweep
  if (isNum(target)) all.push(target)
  if (isNum(target) && isNum(broken)) all.push(direction === 'above' ? target + broken : target - broken)
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const pad = (hi - lo || 1) * 0.08
  const yRange: Range = view.axes.y ?? [(lo - pad) * scale, (hi + pad) * scale]

  for (const m of methods) {
    const role = opts.roles[m] ?? 'method'
    const style = plotlyStyle(role, 'lines+markers')
    const color = (style.marker as { color: string } | undefined)?.color ?? cssVar('--ct-role-method')
    const y = sweep.values[m].map(scaled)
    const se = sweep.mc_se[m]
    if (numeric) {
      if (se) {
        const upper = y.map((v, i) => (v === null || !isNum(se[i]) ? null : v + 2 * (se[i] as number) * scale))
        const lower = y.map((v, i) => (v === null || !isNum(se[i]) ? null : v - 2 * (se[i] as number) * scale))
        data.push({ type: 'scatter', uid: `${view.id}.bande-haut.${m}`, x: axis.values, y: upper, mode: 'lines', line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: m })
        data.push({ type: 'scatter', uid: `${view.id}.bande-bas.${m}`, x: axis.values, y: lower, mode: 'lines', line: { width: 0 }, fill: 'tonexty', fillcolor: withAlpha(color, 0.15), showlegend: false, hoverinfo: 'skip', legendgroup: m })
      }
      data.push({
        type: 'scatter',
        uid: `${view.id}.mesure.${m}`,
        name: opts.methodLabels?.[m] ?? m,
        legendgroup: m,
        x: axis.values,
        y,
        ...style,
        customdata: axis.labels,
        hovertemplate: `%{customdata} : %{y:.1f}${unit ? ' ' + unit : ''}<extra></extra>`,
      })
    } else {
      data.push({
        type: 'bar',
        uid: `${view.id}.mesure.${m}`,
        name: opts.methodLabels?.[m] ?? m,
        x: axis.labels,
        y,
        error_y: se ? { type: 'data', array: se.map((v) => (isNum(v) ? 2 * v * scale : 0)), color: cssVar('--ct-plot-axis'), thickness: 1 } : undefined,
        marker: {
          color: withAlpha(color, 0.6),
          line: { color, width: 1.5 },
          pattern: { shape: PATTERN[role] ?? '', fgcolor: color, size: 6 },
        },
        hovertemplate: `%{x} : %{y:.1f}${unit ? ' ' + unit : ''}<extra></extra>`,
      })
    }
  }

  // Bande de tolérance (zone Fiable) et limite de rupture.
  if (isNum(target) && isNum(ok)) {
    const t = target * scale
    const o = ok * scale
    const [y0, y1] =
      direction === 'below' ? [t - o, yRange[1]] : direction === 'above' ? [yRange[0], t + o] : [t - o, t + o]
    shapes.push({ type: 'rect', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0, y1, fillcolor: withAlpha(verdictColor('ok'), 0.08), line: { width: 0 }, layer: 'below' })
    shapes.push({ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: t, y1: t, line: { color: cssVar('--ct-plot-axis'), dash: 'dot', width: 1 } })
    annotations.push({ xref: 'paper', x: 1, xanchor: 'right', y: t, yanchor: 'bottom', text: 'Cible', showarrow: false, font: { color: cssVar('--ct-plot-axis'), size: 11 } })
  }
  if (isNum(target) && isNum(broken)) {
    const limits = direction === 'both' ? [target - broken, target + broken] : [direction === 'above' ? target + broken : target - broken]
    for (const b of limits) {
      shapes.push({ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: b * scale, y1: b * scale, line: { color: verdictColor('broken'), dash: 'dash', width: 1 } })
    }
    annotations.push({ xref: 'paper', x: 1, xanchor: 'right', y: limits[0] * scale, yanchor: 'top', text: 'Rompu au-delà', showarrow: false, font: { color: verdictColor('broken'), size: 11 } })
  }

  // Seuil critique de la méthode principale, et état actuel.
  if (numeric) {
    const principal = methods.find((m) => opts.roles[m] === 'method')
    const crit = principal ? sweep.critical[principal] : null
    if (crit && isNum(crit.warning_at)) {
      const v = verticalLine(crit.warning_at, verdictColor('warning'), 'dot', 'Seuil critique')
      shapes.push(v.shape)
      if (v.annotation) annotations.push(v.annotation)
    }
    const current = sweep.current[axis.target]
    if (typeof current === 'number') {
      shapes.push(verticalLine(current, cssVar('--ct-text'), 'solid').shape)
    }
  }

  const ytitle = opts.measure ? `${opts.measure.label}${unit ? ` (${unit})` : ''}` : undefined
  const layout = baseLayout(view, { shapes, annotations, barmode: 'group' })
  layout.yaxis = { ...axisLayout(yRange, ytitle) }
  if (numeric) layout.xaxis = { ...axisLayout(view.axes.x ?? null, (view.ui?.x_title as string) ?? axis.target) }
  return { data, layout, caption: [] }
}

/** Figure d'une vue ; null si le type n'est pas (encore) dessiné : afficher la vue de secours. */
export function buildFigure(view: ViewData, opts: ChartOptions): Figure | null {
  switch (view.type) {
    case 'scatter':
    case 'residuals':
    case 'curves':
      return xyFigure(view, opts)
    case 'repetitions':
      // TODO(passation) : mode « trajectoires » (LGN et TCL, P1).
      return view.mode === 'paths' ? xyFigure(view, opts) : intervalsFigure(view, opts)
    case 'distribution':
      return distributionFigure(view, opts)
    case 'sensitivity':
      return sensitivityFigure(view, opts)
    default:
      // validity_domain (P1), surface_3d (P1), vector_space (P2), measures_table : autres composants.
      return null
  }
}
