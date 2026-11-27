<!--
  PlotlyChart.svelte : le composant graphique UNIQUE de Crash-Test (R3).

  Dessine n'importe quelle vue du moteur. La construction des traces est dans lib/plot.ts
  (fonctions pures, testées) ; ce composant ne fait que :
  - appeler Plotly.react() à chaque changement (jamais newPlot : la caméra et le zoom restent) ;
  - afficher le titre, la légende du bas (« 100 affichés sur 500 calculés ») et, si la vue ne peut pas
    être dessinée, la vue de secours (tableau des mesures, quand `result` est fourni).

  Usage :
    <PlotlyChart view={result.views[0]} {result} methodsOn={ui.methodsOn} />
    Vue Sensibilité : ajouter sweep, measure, roles={displayRoles(result.methods)} et methodLabels.
    Dans un panneau qui porte déjà le titre (onglets du Laboratoire) : bare (ni titre ni cadre).
    Ajout de points (fiche F) : passer injected, onaddpoint et onremovepoint. Un clic dans le cadre
    pose un point (coordonnées de données) ; un clic sur une étoile la retire ; un glissement
    (zoom) ne pose rien.
-->
<script lang="ts">
  import Plotly from 'plotly.js-dist-min'
  import { onMount } from 'svelte'
  import MeasuresTable from './MeasuresTable.svelte'
  import { buildFigure, DOMAIN_SUFFIX, INJECTED_SUFFIX, type ChartOptions } from '../lib/plot'
  import { PLOTLY_FR } from '../lib/plotlyLocale'
  import type { DisplayRole } from '../lib/roles'
  import type { RunResult } from '../lib/types.gen'
  import type { MeasureFormat, SweepResult, ViewResult } from '../lib/views'

  interface Props {
    view: ViewResult
    methodsOn: ReadonlySet<string>
    showReference?: boolean
    /** Vue Sensibilité : résultat du balayage, mesure, rôles et libellés des méthodes. */
    sweep?: SweepResult | null
    measure?: MeasureFormat | null
    roles?: Readonly<Record<string, DisplayRole>>
    methodLabels?: Readonly<Record<string, string>>
    /** Mesures de l'état actuel, pour la vue de secours. */
    result?: Pick<RunResult, 'methods' | 'measures'> | null
    axisLabel?: string
    height?: number
    /** Points posés au clic (coordonnées de la vue) ; sans onaddpoint, le clic ne fait rien. */
    injected?: ReadonlyArray<{ x: number; y?: number | null }>
    onaddpoint?: (point: { x: number; y: number }) => void
    onremovepoint?: (index: number) => void
    /** Domaine de validité : titres des deux axes, et clic sur une case (indices sur l'axe 1 et l'axe 2). */
    axisLabels?: readonly [string, string]
    onpickcell?: (i: number, j: number) => void
    /** Sans titre ni cadre : le parent affiche déjà le nom de la vue (onglet). */
    bare?: boolean
  }

  let {
    view,
    roles = {},
    methodsOn,
    showReference = true,
    sweep = null,
    measure = null,
    methodLabels = {},
    result = null,
    height = 340,
    axisLabel,
    injected = [],
    onaddpoint,
    onremovepoint,
    axisLabels,
    onpickcell,
    bare = false,
  }: Props = $props()

  let el: HTMLDivElement | undefined = $state()

  const figure = $derived.by(() => {
    const opts: ChartOptions = { roles, methodsOn, showReference, sweep, measure, methodLabels, axisLabel, injected, axisLabels }
    return buildFigure(view, opts)
  })

  const config: Partial<Plotly.Config> & { locales: typeof PLOTLY_FR } = {
    displaylogo: false,
    responsive: true,
    locale: 'fr',
    locales: PLOTLY_FR,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
  }

  $effect(() => {
    if (!el || !figure) return
    Plotly.react(el, figure.data as Plotly.Data[], { ...figure.layout, height } as Partial<Plotly.Layout>, config)
  })

  // --- Ajout de points par clic ---
  // Plotly n'émet plotly_click que sur un point : le clic dans le vide est lu sur le conteneur et
  // converti en coordonnées de données par les axes de Plotly (p2d). plotly_click part avant le
  // clic du navigateur : un clic sur une étoile la retire et n'en pose pas une autre.
  interface PlotAxis { _offset: number; _length: number; p2d: (px: number) => number }
  type PlotDiv = HTMLDivElement & {
    _fullLayout?: { xaxis?: PlotAxis; yaxis?: PlotAxis }
    on?: (event: string, cb: (e: { points?: { data?: { uid?: string }; customdata?: unknown; x?: unknown; y?: unknown }[] }) => void) => void
  }

  let downAt: { x: number; y: number } | null = null
  let removedJustNow = false

  function onPointerDown(e: PointerEvent): void {
    downAt = { x: e.clientX, y: e.clientY }
  }

  function onClick(e: MouseEvent): void {
    if (!onaddpoint || !el) return
    if (removedJustNow) {
      removedJustNow = false
      return
    }
    // Un glissement (zoom, déplacement) n'est pas un clic.
    if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 4) return
    const div = el as PlotDiv
    const xa = div._fullLayout?.xaxis
    const ya = div._fullLayout?.yaxis
    if (!xa || !ya) return
    const box = el.getBoundingClientRect()
    const px = e.clientX - box.left - xa._offset
    const py = e.clientY - box.top - ya._offset
    // Hors de la zone de tracé (légende, axes, barre d'outils) : rien.
    if (px < 0 || px > xa._length || py < 0 || py > ya._length) return
    const x = xa.p2d(px)
    const y = ya.p2d(py)
    if (Number.isFinite(x) && Number.isFinite(y)) onaddpoint({ x, y })
  }

  let listening = false
  $effect(() => {
    if (!el || !figure || listening) return
    const div = el as PlotDiv
    if (!div.on) return
    listening = true
    div.on('plotly_click', (ev) => {
      const pt = ev.points?.[0]
      const uid = String(pt?.data?.uid ?? '')
      if (pt && uid.endsWith(DOMAIN_SUFFIX) && typeof pt.x === 'number' && typeof pt.y === 'number') {
        onpickcell?.(pt.x, pt.y)
        return
      }
      if (pt && String(pt.data?.uid ?? '').endsWith(INJECTED_SUFFIX) && typeof pt.customdata === 'number') {
        removedJustNow = true
        onremovepoint?.(pt.customdata)
      }
    })
  })

  onMount(() => () => {
    if (el) Plotly.purge(el)
  })
</script>

<figure class="chart" class:bare>
  {#if !bare}<figcaption class="title">{view.title}</figcaption>{/if}
  {#if figure}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div
      bind:this={el}
      class="plot"
      class:injectable={!!onaddpoint}
      style:min-height="{height}px"
      onpointerdown={onPointerDown}
      onclick={onClick}
    ></div>
    {#if figure.caption.length > 0}
      <p class="caption">{figure.caption.join(' · ')}</p>
    {/if}
  {:else}
    {#if result}
      <p class="fallback">Ce graphique n'est pas encore disponible : voici les mesures de l'état actuel.</p>
      <MeasuresTable {result} {methodsOn} />
    {:else}
      <p class="fallback">Ce graphique n'est pas encore disponible.</p>
    {/if}
  {/if}
</figure>

<style>
  .chart {
    margin: 0;
    padding: var(--ct-space-3) var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .chart.bare {
    padding: 0;
    border: none;
    background: none;
  }
  .injectable :global(.nsewdrag) {
    cursor: crosshair;
  }
  .title {
    font-weight: 600;
    margin-bottom: var(--ct-space-2);
  }
  .caption,
  .fallback {
    margin: var(--ct-space-2) 0 0;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
</style>
