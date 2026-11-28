/**
 * plot.ts : construit la figure Plotly (traces + mise en page) d'une vue (R3).
 *
 * Fonctions pures, sans Svelte, testées par plot.test.ts. PlotlyChart.svelte ne fait que
 * passer le résultat à Plotly.react(). Aucune connaissance d'un théorème : tout vient du type
 * de vue, de l'emplacement de chaque série (lu dans son id) et de son rôle.
 *
 * Règles du cahier (section 3.1, annexe E) appliquées ici :
 * - axes fixes : bornes reçues du moteur (calculées sur la Référence), jamais recalculées ;
 * - points hors cadre dessinés au bord avec un triangle, et comptés ;
 * - jamais la couleur seule : trait, marqueur ou motif propres à chaque rôle ;
 * - identifiants de traces stables (uid = id de la série) pour que Plotly anime proprement.
 */

import { formatMeasure } from './format'
import { cssVar, plotlyStyle, roleColor, verdictColor, verdictIcon, verdictLabel, type DisplayRole, type Verdict } from './roles'
import {
  axisRange,
  bools,
  isGeneratorData,
  nums,
  scalar,
  type MeasureFormat,
  type Num,
  type Range,
  type Series,
  type SweepResult,
  type ViewResult,
} from './views'

export type Trace = Record<string, unknown>
export type Layout = Record<string, unknown>

export interface Figure {
  data: Trace[]
  layout: Layout
  /** Phrases à afficher sous la vue (« 100 affichés sur 500 calculés », « 3 points hors cadre »). */
  caption: string[]
}

export interface ChartOptions {
  /** Méthodes affichées (état d'affichage). */
  methodsOn: ReadonlySet<string>
  /** Afficher la Référence (état sain) en arrière-plan. */
  showReference: boolean
  /** Vue Sensibilité : rôle d'affichage de chaque méthode (roles.displayRoles(RunResult.methods)). */
  roles?: Readonly<Record<string, DisplayRole>>
  /** Vue Sensibilité : résultat du balayage (POST /api/sweep), null pendant le chargement. */
  sweep?: SweepResult | null
  /** Vue Sensibilité : mise en forme de la mesure balayée. */
  measure?: MeasureFormat | null
  /** Vue Sensibilité : libellé de chaque méthode (RunResult.methods[].label), pour la légende. */
  methodLabels?: Readonly<Record<string, string>>
  /** Vue Sensibilité : titre de l'axe balayé (lab.axisTitle), si la vue n'en impose pas un. */
  axisLabel?: string
  /**
   * Points posés au clic (EngineState.extra_points, coordonnées de la vue), dessinés en étoiles
   * par-dessus l'échantillon. Seulement pour une vue qui autorise l'ajout de points.
   */
  injected?: ReadonlyArray<{ x: number; y?: number | null }>
  /** Domaine de validité : titres des deux axes balayés (lab.axisTitle). */
  axisLabels?: readonly [string, string]
}

/**
 * Types de vue que buildFigure sait dessiner (les autres retombent sur la vue de secours
 * measures_table), avec leur usage : repris tel quel par le prompt de l'écran Import.
 */
export const VIEW_TYPES: Readonly<Record<string, string>> = {
  scatter: 'nuage de points et droites (x, y)',
  residuals: 'résidus, avec la ligne 0',
  curves: 'courbes dans l’ordre reçu (temps, itérations)',
  repetitions: 'intervalles par répétition, ou trajectoires (mode: paths)',
  distribution: 'histogrammes superposés, vraie valeur et seuil en lignes verticales',
  sensitivity: 'la mesure primaire selon un contrôle balayé (sweep)',
  validity_domain: 'carte des verdicts sur deux contrôles balayés',
  heatmap: 'matrices côte à côte (paths : une liste par ligne)',
}

/** Réglages du champ libre `ui` d'une vue, lus par ce fichier : repris par le prompt de l'écran Import. */
export const VIEW_UI_KEYS: Readonly<Record<string, string>> = {
  x_title: 'titre de l’axe horizontal',
  y_title: 'titre de l’axe vertical',
  log_x: 'true : axe horizontal en échelle logarithmique',
  log_y: 'true : axe vertical en échelle logarithmique (convergence, erreurs)',
  aspect: '"equal" : repère orthonormé (un cercle reste un cercle)',
  unit_circle: 'true ou un rayon : cercle centré en 0 (plan complexe)',
  marker_size: 'taille des points',
  point_labels: 'liste de noms, un par point (emplacement points)',
  fill_area: 'true : remplit l’aire entre la courbe et l’axe horizontal (une intégrale)',
  zmin: 'heatmap : borne basse de l’échelle de couleur',
  zmax: 'heatmap : borne haute de l’échelle de couleur',
  decimals: 'heatmap : décimales écrites dans les cases (2 par défaut)',
}

/** Identifiant de la trace des points posés : PlotlyChart le reconnaît au clic (pour un retrait). */
export const INJECTED_SUFFIX = '.points-poses'

/** Points posés au clic, en étoiles ; y absent (vue à une dimension) : posés sur l'axe horizontal. */
export function injectedTrace(viewId: string, points: NonNullable<ChartOptions['injected']>): Trace {
  const style = pointsStyle('injected')
  return {
    type: 'scatter',
    uid: `${viewId}${INJECTED_SUFFIX}`,
    name: points.length > 1 ? 'Points posés' : 'Point posé',
    ...style,
    x: points.map((p) => p.x),
    y: points.map((p) => (typeof p.y === 'number' ? p.y : 0)),
    customdata: points.map((_, i) => i),
    hovertemplate: 'Point posé (cliquez pour le retirer)<extra></extra>',
    cliponaxis: false,
  }
}

/** Emplacements dessinés en ligne ; les autres sont des points. */
const LINE_SLOTS = new Set(['fit', 'trend', 'series', 'truth', 'paths'])

/** Motif de remplissage par rôle (histogrammes, barres) : la couleur n'est jamais le seul indice. */
const PATTERN: Partial<Record<DisplayRole, string>> = {
  truth: '-',
  method: '',
  correction: '/',
  alternative_1: 'x',
  alternative_2: '.',
  reference: '',
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

/** Rôle de style d'une série ; null pour les données du générateur (style neutre). */
export function seriesRole(s: Series): DisplayRole | null {
  return isGeneratorData(s) ? null : s.role
}

export function isVisible(s: Series, opts: ChartOptions): boolean {
  if (isGeneratorData(s) || s.role === 'truth' || s.role === 'injected') return true
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

/** Couleur d'un rôle, y compris ceux qui n'ont pas de marqueur (vraie valeur). */
function markerColor(role: DisplayRole): string {
  return roleColor(role)
}

function markerSymbol(role: DisplayRole): string {
  return (plotlyStyle(role, 'markers').marker as { symbol: string }).symbol
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
  return {
    mode: 'markers',
    marker: { ...s.marker, size: role === 'injected' ? 12 : 6, opacity: role === 'reference' ? 0.6 : 0.9 },
  }
}

/** Points d'une série, avec les points hors cadre ramenés au bord (triangles). */
function markerTraces(s: Series, view: ViewResult): { traces: Trace[]; clipped: number } {
  const { inside, outside } = clampPoints(nums(s, 'x'), nums(s, 'y'), axisRange(view, 'x'), axisRange(view, 'y'))
  const style = pointsStyle(seriesRole(s))
  const marker = style.marker as Record<string, unknown>
  // Réglages d'affichage facultatifs de la vue (champ libre `ui`) : taille et nom de chaque point.
  const size = view.ui?.marker_size
  if (typeof size === 'number') marker.size = size
  const labels = view.ui?.point_labels
  const named = s.slot === 'points' && Array.isArray(labels)
  const traces: Trace[] = [
    {
      type: 'scatter', uid: s.id, name: s.label, x: inside.x, y: inside.y, ...style, legendgroup: s.id,
      ...(named ? { mode: 'markers+text', text: labels, textposition: 'bottom center' } : {}),
    },
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

/** Ligne d'une série ; triée par x pour une droite ajustée (qui arrive dans l'ordre des observations). */
function lineTrace(s: Series, sortByX: boolean, log: { x: boolean; y: boolean } = { x: false, y: false }): Trace {
  const role = seriesRole(s)
  const x = nums(s, 'x')
  const y = nums(s, 'y')
  const pairs: [number, number][] = []
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const xi = x[i]
    const yi = y[i]
    // En échelle logarithmique, une valeur ≤ 0 n'a pas de place : Plotly ferait plonger la ligne
    // jusqu'au bord. Elle est retirée (et comptée sous la vue par nonPositiveCount).
    if ((log.x && isNum(xi) && xi <= 0) || (log.y && isNum(yi) && yi <= 0)) continue
    if (isNum(xi) && isNum(yi)) pairs.push([xi, yi])
  }
  if (sortByX) pairs.sort((a, b) => a[0] - b[0])
  const style = role
    ? plotlyStyle(role, 'lines')
    : { mode: 'lines', line: { color: cssVar('--ct-plot-data'), width: 1.5 } }
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

/** Styles des segments quand une vue en porte plusieurs, par rang : gris pointillé, cyan tireté, rouge plein. */
const SEGMENT_STYLES: (() => { color: string; width: number; dash: string })[] = [
  () => ({ color: withAlpha(cssVar('--ct-plot-axis'), 0.95), width: 1.2, dash: 'dot' }),
  () => ({ color: withAlpha(roleColor('alternative_2'), 0.9), width: 1.5, dash: 'dash' }),
  () => ({ color: withAlpha(roleColor('rupture'), 0.9), width: 1.5, dash: 'solid' }),
]

/**
 * Segments (résidus d'une droite, écarts) : un trait vertical par point, de (x, low) à (x, high),
 * réunis dans une seule trace (séparés par null) pour garder un identifiant stable.
 */
export function segmentsTrace(s: Series, rank = 0, count = 1): Trace | null {
  const x = nums(s, 'x')
  const low = nums(s, 'low')
  const high = nums(s, 'high')
  const xs: (number | null)[] = []
  const ys: (number | null)[] = []
  for (let i = 0; i < Math.min(x.length, low.length, high.length); i++) {
    const xi = x[i]
    const a = low[i]
    const b = high[i]
    if (!isNum(xi) || !isNum(a) || !isNum(b)) continue
    xs.push(xi, xi, null)
    ys.push(a, b, null)
  }
  if (xs.length === 0) return null
  const role = seriesRole(s)
  // Un seul type de segments : le trait du rôle de la méthode. Plusieurs (par exemple SCT, SCE et SCR) :
  // un style par rang (couleur ET tireté, jamais la couleur seule), pour qu'on les distingue, légende comprise.
  const line =
    count > 1
      ? SEGMENT_STYLES[rank % SEGMENT_STYLES.length]()
      : { color: withAlpha(role ? markerColor(role) : cssVar('--ct-plot-data'), 0.7), width: 1, dash: 'dot' }
  return {
    type: 'scatter',
    uid: s.id,
    name: s.label,
    mode: 'lines',
    x: xs,
    y: ys,
    line,
    hoverinfo: 'skip',
    legendgroup: s.id,
    connectgaps: false,
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

/**
 * Axe d'une vue. En échelle logarithmique, Plotly attend les bornes en log10 : on les convertit, et
 * des bornes non strictement positives passent en automatique (log de 0 ou d'un négatif).
 */
function axisLayout(range: Range | null | undefined, title?: string, log = false): Trace {
  const grid = cssVar('--ct-plot-grid')
  const r = log ? (range && range[0] > 0 && range[1] > 0 ? [Math.log10(range[0]), Math.log10(range[1])] : null) : range
  return {
    ...(log ? { type: 'log', exponentformat: 'power' } : {}),
    ...(r ? { range: [...r], autorange: false } : { autorange: true }),
    gridcolor: grid,
    zerolinecolor: grid,
    linecolor: grid,
    tickfont: { color: cssVar('--ct-plot-axis') },
    title: title ? { text: title, font: { color: cssVar('--ct-plot-axis'), size: 12 } } : undefined,
  }
}

function uiString(view: ViewResult, key: string): string | undefined {
  const v = view.ui?.[key]
  return typeof v === 'string' ? v : undefined
}

/** Réglage booléen du champ libre `ui` (`log_x`, `log_y`) : absent ou autre chose que true = faux. */
export function uiFlag(view: ViewResult, key: string): boolean {
  return view.ui?.[key] === true
}

function uiNumber(view: ViewResult, key: string): number | undefined {
  const v = view.ui?.[key]
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined
}

/**
 * Repère orthonormé (`ui.aspect: "equal"`) : une unité a la même longueur sur les deux axes, pour
 * qu'un cercle reste un cercle (plan complexe, image du cercle unité par une matrice). Les bornes du
 * moteur sont gardées : c'est la zone de tracé qui se resserre (`constrain: domain`).
 */
function equalAspect(view: ViewResult): { x: Layout; y: Layout } {
  if (uiString(view, 'aspect') !== 'equal') return { x: {}, y: {} }
  // `constrain: domain` sur les DEUX axes : sinon Plotly élargit les bornes de l'axe x au lieu de
  // resserrer la zone de tracé (vérifié à l'œil : x passait de [-1,6 ; 1,6] à [-4,5 ; 4,5]).
  return { x: { constrain: 'domain' }, y: { scaleanchor: 'x', scaleratio: 1, constrain: 'domain' } }
}

/**
 * Cercle centré en 0 (`ui.unit_circle`) : true pour le cercle unité, ou un rayon positif. Dessiné en
 * pointillés neutres sous les données (repère, pas une série : il ne va pas dans la légende).
 */
export function unitCircle(view: ViewResult): Trace | null {
  const v = view.ui?.unit_circle
  const r = v === true ? 1 : typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : null
  if (r === null) return null
  return {
    type: 'circle', xref: 'x', yref: 'y', x0: -r, y0: -r, x1: r, y1: r, layer: 'below',
    line: { color: cssVar('--ct-plot-axis'), dash: 'dot', width: 1 },
  }
}

/**
 * Copie du layout à donner à Plotly : il réécrit le zoom de l'utilisateur DANS l'objet reçu. Sans copie,
 * les bornes du moteur étaient perdues au premier nouveau dessin pendant un zoom, et la réinitialisation
 * revenait au zoom. Les axes et leurs bornes sont copiés ; le reste est partagé.
 */
export function layoutForPlotly(layout: Layout): Layout {
  const copy: Layout = { ...layout }
  for (const [name, axis] of Object.entries(layout)) {
    if (!/^[xy]axis\d*$/.test(name) || typeof axis !== 'object' || axis === null) continue
    const range = (axis as { range?: unknown }).range
    copy[name] = { ...axis, ...(Array.isArray(range) ? { range: [...range] } : {}) }
  }
  return copy
}

/**
 * Plotly retient les bornes du PREMIER dessin et y revient avec « Réinitialiser les axes » ou un
 * double-clic. Quand les bornes du moteur changent (vraie pente, taille d'échantillon, nouveau tirage),
 * ce retour montrait un cadre périmé, parfois vide. Après chaque dessin, on remplace ces bornes initiales
 * par celles de la figure courante. Les axes sans bornes fixes (automatiques) ne sont pas touchés.
 * `fullLayout` est l'état interne de Plotly (`_rangeInitial0` / `_rangeInitial1`, Plotly 4).
 */
export function syncInitialRanges(fullLayout: unknown, layout: Layout): void {
  if (typeof fullLayout !== 'object' || fullLayout === null) return
  const axes = fullLayout as Record<string, Record<string, unknown> | undefined>
  for (const [name, wanted] of Object.entries(layout)) {
    if (!/^[xy]axis\d*$/.test(name)) continue
    const range = (wanted as { range?: unknown } | undefined)?.range
    const axis = axes[name]
    if (!axis || !Array.isArray(range) || range.length !== 2) continue
    axis._rangeInitial0 = range[0]
    axis._rangeInitial1 = range[1]
    axis._autorangeInitial = false
  }
}

export function baseLayout(view: ViewResult, extra: Layout = {}): Layout {
  const aspect = equalAspect(view)
  const xaxis = { ...axisLayout(axisRange(view, 'x'), uiString(view, 'x_title'), uiFlag(view, 'log_x')), ...aspect.x }
  const yaxis = { ...axisLayout(axisRange(view, 'y'), uiString(view, 'y_title'), uiFlag(view, 'log_y')), ...aspect.y }
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
    xaxis,
    yaxis,
    shapes: [],
    annotations: [],
    ...extra,
  }
}

function captionFor(view: ViewResult, clipped: number): string[] {
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
function xyFigure(view: ViewResult, opts: ChartOptions): Figure {
  const data: Trace[] = []
  let clipped = 0
  // Segments d'abord : sous les points et la droite.
  const segmentSeries = view.series.filter((s) => s.slot === 'segments' && isVisible(s, opts))
  segmentSeries.forEach((s, rank) => {
    const t = segmentsTrace(s, rank, segmentSeries.length)
    if (t) data.push(t)
  })
  const visible = view.series.filter(
    (s) => isVisible(s, opts) && s.x != null && s.y != null,
  )
  // Référence d'abord, pour qu'elle reste derrière.
  visible.sort((a, b) => Number(b.role === 'reference') - Number(a.role === 'reference'))
  for (const s of visible) {
    if (LINE_SLOTS.has(s.slot) || view.type === 'curves') {
      // Une courbe dans le temps arrive déjà dans l'ordre ; une droite ajustée doit être triée.
      const line = lineTrace(s, view.type !== 'curves', { x: uiFlag(view, 'log_x'), y: uiFlag(view, 'log_y') })
      // `ui.fill_area` : l'aire entre la courbe et l'axe (l'intégrale). La Référence reste en trait seul.
      if (uiFlag(view, 'fill_area') && s.role !== 'reference') {
        const color = String((line as { line?: { color?: string } }).line?.color ?? cssVar('--ct-plot-data'))
        Object.assign(line, { fill: 'tozeroy', fillcolor: withAlpha(color, 0.22) })
      }
      data.push(line)
    } else {
      const m = markerTraces(s, view)
      data.push(...m.traces)
      clipped += m.clipped
    }
  }
  if (opts.injected && opts.injected.length > 0) data.push(injectedTrace(view.id, opts.injected))
  const shapes: Trace[] = []
  // La ligne 0 et le cercle centré en 0 n'existent pas en échelle logarithmique (et Plotly y attend
  // des coordonnées en log10) : ils ne sont dessinés qu'en échelle linéaire.
  const linear = !uiFlag(view, 'log_x') && !uiFlag(view, 'log_y')
  if (view.type === 'residuals' && linear) {
    shapes.push({
      type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: 0, y1: 0,
      line: { color: cssVar('--ct-plot-axis'), width: 1 },
    })
  }
  const circle = linear ? unitCircle(view) : null
  if (circle) shapes.push(circle)
  const caption = captionFor(view, clipped)
  const hidden = nonPositiveCount(view, visible)
  if (hidden > 0) {
    caption.push(
      hidden === 1
        ? '1 valeur négative ou nulle non affichée (échelle logarithmique)'
        : `${hidden} valeurs négatives ou nulles non affichées (échelle logarithmique)`,
    )
  }
  return { data, layout: baseLayout(view, { shapes }), caption }
}

/** Valeurs qu'une échelle logarithmique ne peut pas placer (≤ 0) : Plotly les tait, on les compte. */
function nonPositiveCount(view: ViewResult, series: Series[]): number {
  const axes = (['x', 'y'] as const).filter((a) => uiFlag(view, `log_${a}`))
  let count = 0
  for (const s of series) {
    for (const a of axes) count += nums(s, a).filter((v) => isNum(v) && v <= 0).length
  }
  return count
}

/** Répétitions (intervalles) : un intervalle par ligne, les ratés en rouge avec une croix. */
function intervalsFigure(view: ViewResult, opts: ChartOptions): Figure {
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const rupture = cssVar('--ct-role-rupture')
  const series = view.series.filter(
    (s) => isVisible(s, opts) && s.low != null && s.high != null,
  )
  const spacing = series.length > 1 ? 0.8 / series.length : 0
  let rows = 0

  series.forEach((s, k) => {
    const role = seriesRole(s) ?? 'method'
    const color = markerColor(role)
    const est = nums(s, 'x') // l'estimation est portée par x
    const low = nums(s, 'low')
    const high = nums(s, 'high')
    const hit = bools(s)
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
        marker: { color: c, symbol: kind === 'ok' ? markerSymbol(role) : 'x', size: kind === 'ok' ? 4 : 7 },
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

  for (const t of view.series.filter((s) => s.role === 'truth')) {
    const v = scalar(t)
    if (v === null) continue
    const line = verticalLine(v, cssVar('--ct-role-truth'), 'solid', t.label)
    shapes.push(line.shape)
    if (line.annotation) annotations.push(line.annotation)
  }

  const layout = baseLayout(view, { shapes, annotations })
  layout.yaxis = {
    ...(layout.yaxis as Trace),
    range: [-1, Math.max(rows, 1)],
    autorange: false,
    showticklabels: false,
    title: undefined,
  }
  return { data, layout, caption: captionFor(view, 0) }
}

/**
 * Répétitions en mode trajectoires (faisceau de X̄_n, LGN et TCL) : chaque série porte `paths`, une
 * liste par trajectoire. Une seule trace par série (trajectoires séparées par null) : un identifiant
 * stable et une seule entrée de légende. Abscisse : `x` de la série s'il existe, sinon 1, 2, …, n.
 * La vraie valeur (rôle truth, scalaire) est une ligne horizontale.
 */
function pathsFigure(view: ViewResult, opts: ChartOptions): Figure {
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const series = view.series.filter((s) => isVisible(s, opts) && Array.isArray(s.paths) && s.paths.length > 0)
  // Référence d'abord, pour qu'elle reste derrière.
  series.sort((a, b) => Number(b.role === 'reference') - Number(a.role === 'reference'))
  let count = 0
  for (const s of series) {
    const paths = s.paths as Num[][]
    const grid = nums(s, 'x')
    const xs: (number | null)[] = []
    const ys: (number | null)[] = []
    for (const path of paths) {
      path.forEach((v, i) => {
        const xi = grid.length === path.length ? grid[i] : i + 1
        xs.push(isNum(xi) ? xi : i + 1)
        ys.push(isNum(v) ? v : null)
      })
      xs.push(null)
      ys.push(null)
    }
    if (s.role !== 'reference') count = Math.max(count, paths.length)
    const role = seriesRole(s) ?? 'method'
    const style = plotlyStyle(role, 'lines') as { line?: Record<string, unknown> }
    data.push({
      type: 'scatter',
      uid: s.id,
      name: s.label,
      mode: 'lines',
      x: xs,
      y: ys,
      line: { ...(style.line ?? {}), width: 1 },
      opacity: role === 'reference' ? 0.35 : 0.55,
      legendgroup: s.id,
      hoverinfo: 'skip',
      connectgaps: false,
    })
  }
  for (const t of view.series.filter((x) => x.role === 'truth')) {
    const v = scalar(t)
    if (v === null) continue
    const color = cssVar('--ct-role-truth')
    shapes.push({ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: v, y1: v, line: { color, width: 1.5 } })
    annotations.push({ xref: 'paper', x: 1, xanchor: 'right', y: v, yanchor: 'bottom', text: t.label, showarrow: false, font: { color, size: 11 } })
  }
  const caption = captionFor(view, 0)
  if (caption.length === 0 && count > 0) caption.push(count === 1 ? '1 trajectoire' : `${count} trajectoires`)
  return { data, layout: baseLayout(view, { shapes, annotations }), caption }
}

/** Distribution : histogrammes superposés, bacs fixés par les bornes de l'axe. */
function distributionFigure(view: ViewResult, opts: ChartOptions): Figure {
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const rx = axisRange(view, 'x')
  const bins = rx ? { start: rx[0], end: rx[1], size: (rx[1] - rx[0]) / 40 } : undefined
  for (const s of view.series.filter((x) => isVisible(x, opts))) {
    const v = scalar(s)
    if (v !== null) {
      // Vraie valeur en orange, seuil en rouge (rôle rupture), le reste en neutre.
      const color = s.role === 'truth' || s.role === 'rupture' ? roleColor(s.role) : cssVar('--ct-plot-axis')
      const line = verticalLine(v, color, s.role === 'truth' ? 'solid' : s.role === 'rupture' ? 'dash' : 'dot', s.label)
      shapes.push(line.shape)
      if (line.annotation) annotations.push(line.annotation)
      continue
    }
    const role = seriesRole(s) ?? 'method'
    const color = markerColor(role)
    data.push({
      type: 'histogram',
      uid: s.id,
      name: s.label,
      x: nums(s, 'x').filter(isNum),
      histnorm: 'probability density',
      xbins: bins,
      autobinx: bins ? false : undefined,
      opacity: role === 'reference' ? 0.35 : 0.6,
      // L'histogramme d'une vraie loi (rôle truth, ex. h1) se distingue par un motif, pas seulement l'orange.
      marker: {
        color: withAlpha(color, role === 'reference' ? 0.25 : 0.55),
        line: { color, width: 1 },
        pattern: { shape: PATTERN[role] ?? '', fgcolor: color, size: 6 },
      },
    })
  }
  if (opts.injected && opts.injected.length > 0) data.push(injectedTrace(view.id, opts.injected.map((p) => ({ x: p.x }))))
  return { data, layout: baseLayout(view, { barmode: 'overlay', shapes, annotations }), caption: captionFor(view, 0) }
}

/** Ligne d'une grille de balayage à un axe (une grille à 2 axes va au Domaine de validité). */
function row(grid: Num[] | Num[][] | undefined): Num[] {
  if (!grid || grid.length === 0 || Array.isArray(grid[0])) return []
  return grid as Num[]
}

/** Cible de la méthode principale : nombre, ou dictionnaire par méthode quand la cible est « base ». */
function targetFor(sweep: SweepResult, method: string | undefined): Num {
  const t = sweep.target
  if (typeof t === 'number') return t
  if (t && method && typeof t[method] === 'number') return t[method]
  return null
}

/** Sensibilité : la mesure selon la perturbation, bande de tolérance, seuil critique. */
function sensitivityFigure(view: ViewResult, opts: ChartOptions): Figure {
  const sweep = opts.sweep
  if (!sweep || sweep.axes.length === 0) {
    return { data: [], layout: baseLayout(view), caption: ['Balayage en cours…'] }
  }
  const roles = opts.roles ?? {}
  const scale = opts.measure?.scale ?? 1
  const unit = opts.measure?.unit ?? ''
  const axis = sweep.axes[0]
  const numeric = axis.values.every((v) => typeof v === 'number')
  const methods = Object.keys(sweep.values).filter((m) => opts.methodsOn.has(m))
  const principal = Object.keys(sweep.values).find((m) => roles[m] === 'method')
  const data: Trace[] = []
  const shapes: Trace[] = []
  const annotations: Trace[] = []
  const scaled = (v: Num | undefined) => (isNum(v) ? v * scale : null)

  const target = targetFor(sweep, principal)
  const { ok_within: ok, broken_beyond: broken, direction } = sweep

  // Échelles logarithmiques (`ui.log_y`, `ui.log_x`) : seules les valeurs > 0 ont une place. Plotly 4
  // n'est pas cohérent sur un axe log (vérifié dans le navigateur) : les FORMES prennent des valeurs
  // en unités de données, les ANNOTATIONS des valeurs en log10.
  const logY = uiFlag(view, 'log_y')
  const logX = uiFlag(view, 'log_x') && numeric
  const posY = (v: number) => !logY || v > 0
  /** Ordonnée d'une forme : la valeur elle-même ; null si l'échelle log ne peut la placer (≤ 0). */
  const shapeY = (v: number): number | null => (logY && v <= 0 ? null : v)
  const shapeX = (v: number): number | null => (logX && v <= 0 ? null : v)
  /** Coordonnée d'une annotation : log10 sur un axe log. */
  const annY = (v: number): number => (logY ? Math.log10(v) : v)
  const annX = (v: number): number => (logX ? Math.log10(v) : v)

  // Bornes verticales : valeurs, marges et cible, pour que la bande de tolérance soit visible.
  const all: number[] = []
  for (const m of methods) {
    const se = row(sweep.mc_se[m])
    row(sweep.values[m]).forEach((v, i) => {
      const e = se[i]
      // La valeur elle-même aussi : en échelle log, le bas de sa bande (≤ 0) est écarté, et le point
      // tomberait sous l'axe si seules les bornes de la bande comptaient.
      if (isNum(v)) all.push(v, v - 2 * (isNum(e) ? e : 0), v + 2 * (isNum(e) ? e : 0))
    })
  }
  if (isNum(target)) all.push(target)
  if (isNum(target) && isNum(broken)) all.push(direction === 'above' ? target + broken : target - broken)
  const bounds = all.filter(posY)
  const lo = bounds.length ? Math.min(...bounds) : 0
  const hi = bounds.length ? Math.max(...bounds) : 1
  let yRange: Range | null
  if (axisRange(view, 'y')) yRange = axisRange(view, 'y')
  else if (logY) yRange = bounds.length ? [(lo * scale) / 1.5, hi * scale * 1.5] : null // marge multiplicative
  else {
    const pad = (hi - lo || 1) * 0.08
    yRange = [(lo - pad) * scale, (hi + pad) * scale]
  }

  for (const m of methods) {
    const role = roles[m] ?? 'method'
    const color = markerColor(role)
    const y = row(sweep.values[m]).map(scaled)
    const se = row(sweep.mc_se[m])
    const name = opts.methodLabels?.[m] ?? m
    const hover = `%{customdata} : %{y:.1f}${unit ? ' ' + unit : ''}<extra></extra>`
    if (numeric) {
      if (se.length > 0) {
        // En échelle log, le bas de la bande peut passer sous 0 : il est ramené au bas de l'axe.
        const floor = logY && yRange ? yRange[0] : null
        const band = (sign: 1 | -1) =>
          y.map((v, i) => {
            if (v === null || !isNum(se[i])) return null
            const b = v + sign * 2 * (se[i] as number) * scale
            return logY && b <= 0 ? floor : b
          })
        const common = { type: 'scatter', x: axis.values, mode: 'lines', line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: m }
        data.push({ ...common, uid: `${view.id}.bande-haut.${m}`, y: band(1) })
        data.push({ ...common, uid: `${view.id}.bande-bas.${m}`, y: band(-1), fill: 'tonexty', fillcolor: withAlpha(color, 0.15) })
      }
      data.push({
        type: 'scatter',
        uid: `${view.id}.mesure.${m}`,
        name,
        legendgroup: m,
        x: axis.values,
        y,
        ...plotlyStyle(role, 'lines+markers'),
        customdata: axis.labels,
        hovertemplate: hover,
      })
    } else {
      data.push({
        type: 'bar',
        uid: `${view.id}.mesure.${m}`,
        name,
        x: axis.labels,
        y,
        customdata: axis.labels,
        hovertemplate: hover,
        error_y: se.length > 0
          ? { type: 'data', array: se.map((v) => (isNum(v) ? 2 * v * scale : 0)), color: cssVar('--ct-plot-axis'), thickness: 1 }
          : undefined,
        marker: {
          color: withAlpha(color, 0.6),
          line: { color, width: 1.5 },
          pattern: { shape: PATTERN[role] ?? '', fgcolor: color, size: 6 },
        },
      })
    }
  }

  // Bande de tolérance (zone Fiable) et limite de rupture, pour la méthode principale.
  // Une ligne horizontale à la hauteur v (en unités affichées), si l'échelle peut la placer.
  const hline = (v: number, line: Trace) => {
    const y = shapeY(v)
    if (y !== null) shapes.push({ type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: y, y1: y, line })
    return y
  }
  if (isNum(target) && isNum(ok)) {
    const t = target * scale
    const o = ok * scale
    const [b0, b1] =
      direction === 'below' ? [t - o, yRange?.[1] ?? null] : direction === 'above' ? [yRange?.[0] ?? null, t + o] : [t - o, t + o]
    // En échelle log, un bord ≤ 0 de la zone Fiable est ramené au bas de l'axe.
    const edge = (v: number | null) => (v === null ? null : logY && v <= 0 ? (yRange?.[0] ?? null) : shapeY(v))
    const [y0, y1] = [edge(b0), edge(b1)]
    if (y0 !== null && y1 !== null) {
      shapes.push({ type: 'rect', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0, y1, fillcolor: withAlpha(verdictColor('ok'), 0.08), line: { width: 0 }, layer: 'below' })
    }
    const ty = hline(t, { color: cssVar('--ct-plot-axis'), dash: 'dot', width: 1 })
    if (ty !== null) {
      annotations.push({ xref: 'paper', x: 1, xanchor: 'right', y: annY(ty), yanchor: 'bottom', text: 'Cible', showarrow: false, font: { color: cssVar('--ct-plot-axis'), size: 11 } })
    }
  }
  if (isNum(target) && isNum(broken)) {
    const limits =
      direction === 'both' ? [target - broken, target + broken] : [direction === 'above' ? target + broken : target - broken]
    const placed = limits.map((b) => hline(b * scale, { color: verdictColor('broken'), dash: 'dash', width: 1 }))
    if (placed[0] !== null) {
      annotations.push({ xref: 'paper', x: 1, xanchor: 'right', y: annY(placed[0]), yanchor: 'top', text: 'Rompu au-delà', showarrow: false, font: { color: verdictColor('broken'), size: 11 } })
    }
  }

  // Seuil critique de la méthode principale, et état actuel.
  if (numeric) {
    const crit = principal ? sweep.critical?.[principal] : null
    const critX = crit && isNum(crit.warning_at) ? shapeX(crit.warning_at) : null
    if (critX !== null) {
      const v = verticalLine(critX, verdictColor('warning'), 'dot', 'Seuil critique')
      shapes.push(v.shape)
      if (v.annotation) annotations.push({ ...v.annotation, x: annX(critX) })
    }
    const current = sweep.current[axis.target]
    const currentX = typeof current === 'number' ? shapeX(current) : null
    if (currentX !== null) shapes.push(verticalLine(currentX, cssVar('--ct-text'), 'solid').shape)
  }

  const caption: string[] = []
  if (logY) {
    const hidden = methods.reduce((n, m) => n + row(sweep.values[m]).filter((v) => isNum(v) && v <= 0).length, 0)
    if (hidden > 0) {
      caption.push(
        hidden === 1
          ? '1 valeur négative ou nulle non affichée (échelle logarithmique)'
          : `${hidden} valeurs négatives ou nulles non affichées (échelle logarithmique)`,
      )
    }
  }
  const ytitle = opts.measure ? `${opts.measure.label}${unit ? ` (${unit})` : ''}` : undefined
  const layout = baseLayout(view, { shapes, annotations, barmode: 'group' })
  layout.yaxis = { ...axisLayout(yRange, ytitle, logY) }
  if (numeric) {
    layout.xaxis = {
      ...axisLayout(axisRange(view, 'x'), uiString(view, 'x_title') ?? opts.axisLabel ?? axis.target, logX),
    }
  }
  return { data, layout, caption }
}

/** Identifiant de la carte du Domaine de validité : PlotlyChart le reconnaît au clic (choix d'une case). */
export const DOMAIN_SUFFIX = '.domaine'

const VERDICT_CODE: Record<Verdict, number> = { ok: 0, warning: 1, broken: 2 }

/**
 * Position (indice éventuellement fractionnaire) d'une valeur sur une grille : interpolée entre deux
 * valeurs numériques voisines, exacte pour une option ou un booléen ; null hors de la grille.
 */
export function gridPosition(values: readonly (number | boolean | string)[], v: number | boolean | string | undefined): number | null {
  if (v === undefined) return null
  const exact = values.findIndex((x) => x === v)
  if (exact >= 0) return exact
  if (typeof v !== 'number' || !values.every((x) => typeof x === 'number')) return null
  const nums = values as number[]
  for (let i = 0; i < nums.length - 1; i++) {
    const [a, b] = [nums[i], nums[i + 1]]
    if ((v - a) * (v - b) <= 0 && a !== b) return i + (v - a) / (b - a)
  }
  return null
}

/**
 * Étiquettes d'un axe de carte : sans la précision entre parenthèses (« Student à 2 ddl (variance infinie) »
 * devient « Student à 2 ddl »), pour qu'elles tiennent sous les cases. Le nom complet reste dans l'infobulle.
 * Si deux étiquettes deviennent identiques, on garde les étiquettes complètes.
 */
export function shortTickLabels(labels: readonly string[]): string[] {
  const short = labels.map((l) => l.replace(/\s*\([^()]*\)\s*$/, '').trim() || l)
  return new Set(short).size === labels.length ? short : [...labels]
}

/** Grille 2D d'un balayage à deux axes, indexée [axe 2][axe 1] ; [] sinon. */
function grid2<T>(g: T[] | T[][] | undefined): T[][] {
  return g && g.length > 0 && Array.isArray(g[0]) ? (g as T[][]) : []
}

/**
 * Domaine de validité : carte des verdicts de la méthode principale sur une grille à deux axes
 * (cases d'au plus 12 × 12). Chaque case porte l'icône du verdict et la valeur : la couleur n'est
 * jamais le seul indice. L'état actuel est marqué d'un repère, placé entre les cases au besoin.
 */
function validityFigure(view: ViewResult, opts: ChartOptions): Figure {
  const sweep = opts.sweep
  if (!sweep || sweep.axes.length < 2) {
    return { data: [], layout: baseLayout(view), caption: ['Balayage en cours…'] }
  }
  const [ax1, ax2] = sweep.axes
  const roles = opts.roles ?? {}
  const principal = Object.keys(sweep.values).find((m) => roles[m] === 'method') ?? Object.keys(sweep.values)[0]
  const states = grid2(sweep.states[principal] as (Verdict | null)[] | (Verdict | null)[][])
  const values = grid2(sweep.values[principal] as Num[] | Num[][])
  const scale = opts.measure?.scale ?? 1
  const decimals = opts.measure?.decimals ?? 2
  const unit = opts.measure?.unit ?? ''
  const fmt = (v: Num) => formatMeasure(v, { unit, scale, decimals })

  const z = states.map((row) => row.map((st) => (st ? VERDICT_CODE[st] : null)))
  const text = states.map((row, j) => row.map((st, i) => (st ? `${verdictIcon(st)} ${fmt(values[j]?.[i] ?? null)}` : '')))
  const hover = states.map((row, j) =>
    row.map((st, i) => `${ax1.labels[i]} · ${ax2.labels[j]} : ${fmt(values[j]?.[i] ?? null)}${st ? ` (${verdictLabel(st)})` : ''}`),
  )
  const [ok, warn, broken] = (['ok', 'warning', 'broken'] as const).map((v) => withAlpha(verdictColor(v), 0.55))
  const data: Trace[] = [
    {
      type: 'heatmap',
      uid: `${view.id}${DOMAIN_SUFFIX}`,
      name: opts.methodLabels?.[principal] ?? principal,
      x: ax1.values.map((_, i) => i),
      y: ax2.values.map((_, j) => j),
      z,
      zmin: 0,
      zmax: 2,
      colorscale: [[0, ok], [1 / 3, ok], [1 / 3, warn], [2 / 3, warn], [2 / 3, broken], [1, broken]],
      showscale: false,
      xgap: 2,
      ygap: 2,
      text,
      texttemplate: '%{text}',
      textfont: { size: ax1.values.length * ax2.values.length > 60 ? 9 : 11, color: cssVar('--ct-text') },
      customdata: hover,
      hovertemplate: '%{customdata}<extra>Cliquez pour régler les deux contrôles</extra>',
      showlegend: false,
    },
  ]
  const cx = gridPosition(ax1.values, sweep.current[ax1.target])
  const cy = gridPosition(ax2.values, sweep.current[ax2.target])
  const caption = ['✓ Fiable · ! Fragile · ✕ Rompu', 'Cliquez sur une case pour régler les deux contrôles']
  if (cx !== null && cy !== null) {
    data.push({
      type: 'scatter',
      uid: `${view.id}.etat-actuel`,
      name: 'État actuel',
      mode: 'markers',
      x: [cx],
      y: [cy],
      marker: { symbol: 'circle-open', size: 22, color: cssVar('--ct-text'), line: { width: 3 } },
      hovertemplate: 'État actuel<extra></extra>',
      showlegend: true,
    })
  } else {
    caption.push("L'état actuel est en dehors de la grille")
  }
  const axis = (ax: typeof ax1, title: string) => ({
    ...axisLayout([-0.5, ax.values.length - 0.5], title),
    tickmode: 'array',
    tickvals: ax.values.map((_, i) => i),
    ticktext: shortTickLabels(ax.labels),
    automargin: true, // la marge s'adapte aux étiquettes : plus de chevauchement avec le titre de l'axe
    showgrid: false,
    zeroline: false,
  })
  const layout = baseLayout(view, {
    xaxis: axis(ax1, opts.axisLabels?.[0] ?? ax1.target),
    yaxis: axis(ax2, opts.axisLabels?.[1] ?? ax2.target),
  })
  return { data, layout, caption }
}

/** Matrices affichées côte à côte dans une vue `heatmap` ; au-delà, elles sont comptées en légende. */
export const MAX_MATRICES = 3
/** Au-delà de cette taille (lignes ou colonnes), les valeurs ne sont plus écrites dans les cases. */
export const MAX_WRITTEN = 12

/**
 * Matrices (vue `heatmap`) : une carte par série visible, côte à côte (A, puis QᵀQ, puis la Référence).
 * Chaque série porte sa matrice dans `paths`, une liste par ligne : `paths[i][j]` = coefficient
 * (i + 1, j + 1). Ligne 1 en haut, comme on écrit une matrice.
 *
 * Une seule échelle de couleur pour toutes les cartes, pour qu'une même couleur veuille dire la même
 * valeur ; divergente et centrée sur 0 quand les signes sont mêlés. Bornes imposables par `ui.zmin`
 * et `ui.zmax`, décimales par `ui.decimals`. Jamais la couleur seule : la valeur est écrite dans
 * chaque case jusqu'à 12 × 12, et toujours donnée au survol.
 */
function heatmapFigure(view: ViewResult, opts: ChartOptions): Figure {
  const all = view.series.filter((s) => isVisible(s, opts) && Array.isArray(s.paths) && s.paths.length > 0)
  // La Référence en dernier : à droite, comme point de comparaison.
  all.sort((a, b) => Number(a.role === 'reference') - Number(b.role === 'reference'))
  const mats = all.slice(0, MAX_MATRICES)
  if (mats.length === 0) {
    return { data: [], layout: baseLayout(view), caption: ['Aucune matrice à afficher pour les méthodes choisies'] }
  }

  let lo = Infinity
  let hi = -Infinity
  for (const s of mats) {
    for (const rowValues of s.paths ?? []) {
      for (const v of rowValues) {
        if (isNum(v)) [lo, hi] = [Math.min(lo, v), Math.max(hi, v)]
      }
    }
  }
  if (!Number.isFinite(lo)) [lo, hi] = [0, 1]
  const mixed = lo < 0 && hi > 0
  const bound = Math.max(Math.abs(lo), Math.abs(hi)) || 1
  const zmin = uiNumber(view, 'zmin') ?? (mixed ? -bound : lo)
  const zmax = uiNumber(view, 'zmax') ?? (mixed ? bound : hi === lo ? lo + 1 : hi)
  const diverging = zmin < 0 && zmax > 0
  const bg = cssVar('--ct-plot-bg')
  const colorscale = diverging
    ? [[0, roleColor('method')], [-zmin / (zmax - zmin), bg], [1, roleColor('truth')]]
    : [[0, bg], [1, roleColor('method')]]
  const decimals = uiNumber(view, 'decimals') ?? 2
  const fmt = (v: Num) => (isNum(v) ? formatMeasure(v, { unit: '', scale: 1, decimals }) : '')

  const gap = 0.08
  const width = (1 - gap * (mats.length - 1)) / mats.length
  const data: Trace[] = []
  const annotations: Trace[] = []
  const axes: Layout = {}
  let large = false
  mats.forEach((s, k) => {
    const suffix = k === 0 ? '' : String(k + 1)
    const rows = s.paths ?? []
    const ncol = Math.max(...rows.map((r) => r.length))
    const written = rows.length <= MAX_WRITTEN && ncol <= MAX_WRITTEN
    large ||= !written
    const z = rows.map((r) => Array.from({ length: ncol }, (_, j) => (isNum(r[j]) ? r[j] : null)))
    data.push({
      type: 'heatmap',
      uid: s.id,
      name: s.label,
      x: Array.from({ length: ncol }, (_, j) => j + 1),
      y: rows.map((_, i) => i + 1),
      z,
      // Échelle de couleur commune à toutes les cartes : portée par la mise en page (`layout.coloraxis`).
      // Une barre attachée à une trace prendrait pour identifiant celui de la série (« matrice.matrix.x »), et
      // Plotly retrouve ses graduations par un sélecteur CSS où chaque point devient un séparateur de
      // classes : il n'efface plus les anciennes et en ajoute un jeu à chaque mise à jour (graduations
      // empilées sur la droite, cartes écrasées).
      coloraxis: 'coloraxis',
      xgap: 1,
      ygap: 1,
      xaxis: `x${suffix}`,
      yaxis: `y${suffix}`,
      customdata: z.map((r) => r.map(fmt)),
      hovertemplate: `${s.label}<br>ligne %{y}, colonne %{x} : %{customdata}<extra></extra>`,
      ...(written
        ? { text: z.map((r) => r.map(fmt)), texttemplate: '%{text}', textfont: { size: ncol > 8 ? 9 : 11, color: cssVar('--ct-text') } }
        : {}),
      showlegend: false,
    })
    const x0 = k * (width + gap)
    const ticks = (count: number) =>
      count <= MAX_WRITTEN ? { tickmode: 'array', tickvals: Array.from({ length: count }, (_, i) => i + 1) } : {}
    axes[`xaxis${suffix}`] = {
      ...axisLayout(null), ...ticks(ncol), domain: [x0, x0 + width], anchor: `y${suffix}`,
      side: 'top', showgrid: false, zeroline: false, constrain: 'domain',
    }
    axes[`yaxis${suffix}`] = {
      ...axisLayout(null), ...ticks(rows.length), anchor: `x${suffix}`, autorange: 'reversed',
      scaleanchor: `x${suffix}`, constrain: 'domain', showgrid: false, zeroline: false,
    }
    annotations.push({
      xref: 'paper', x: x0 + width / 2, xanchor: 'center', yref: 'paper', y: 0, yanchor: 'top', yshift: -8,
      text: s.label, showarrow: false, font: { color: s.role === 'reference' ? cssVar('--ct-plot-axis') : cssVar('--ct-text'), size: 12 },
    })
  })

  const caption = captionFor(view, 0)
  if (all.length > mats.length) caption.push(`${mats.length} matrices affichées sur ${all.length}`)
  if (large) caption.push('Valeurs au survol')
  const coloraxis = {
    colorscale,
    cmin: zmin,
    cmax: zmax,
    colorbar: { tickfont: { color: cssVar('--ct-plot-axis') }, thickness: 12 },
  }
  const layout = baseLayout(view, { ...axes, coloraxis, annotations, showlegend: false, hovermode: 'closest' })
  // Pas de légende (le nom de chaque matrice est écrit dessous) : sans bloc `legend`, Plotly.validate
  // ne bute plus sur une légende masquée.
  delete layout.legend
  layout.margin = { l: 40, r: 16, t: 40, b: 48 }
  return { data, layout, caption }
}

/**
 * Figure d'une vue ; null si elle ne peut pas être dessinée (type non géré, ou aucune série hors
 * Sensibilité, dont les données viennent du balayage) : afficher la vue de secours.
 */
export function buildFigure(view: ViewResult, opts: ChartOptions): Figure | null {
  if (view.type !== 'sensitivity' && view.type !== 'validity_domain' && view.series.length === 0) return null
  switch (view.type) {
    case 'scatter':
    case 'residuals':
    case 'curves':
      return xyFigure(view, opts)
    case 'repetitions':
      return view.mode === 'paths' ? pathsFigure(view, opts) : intervalsFigure(view, opts)
    case 'distribution':
      return distributionFigure(view, opts)
    case 'sensitivity':
      return sensitivityFigure(view, opts)
    case 'validity_domain':
      return validityFigure(view, opts)
    case 'heatmap':
      return heatmapFigure(view, opts)
    default:
      // surface_3d (P1), vector_space (P2), measures_table : autres composants.
      return null
  }
}
