<!--
  PlotlyChart.svelte : le composant graphique UNIQUE de Crash-Test (R3).

  Dessine n'importe quelle vue du moteur. La construction des traces est dans lib/plot.ts
  (fonctions pures, testées) ; ce composant ne fait que :
  - appeler Plotly.react() à chaque changement (jamais newPlot : la caméra et le zoom restent) ;
  - afficher le titre, la légende du bas (« 100 affichés sur 500 calculés ») et la vue de secours.

  Usage :
    <PlotlyChart view={result.views[0]} methodsOn={ui.methodsOn} />
    Vue Sensibilité : ajouter sweep, measure, roles={displayRoles(result.methods)} et methodLabels.
-->
<script lang="ts">
  import Plotly from 'plotly.js-dist-min'
  import { onMount } from 'svelte'
  import { buildFigure, type ChartOptions } from '../lib/plot'
  import { PLOTLY_FR } from '../lib/plotlyLocale'
  import type { DisplayRole } from '../lib/roles'
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
    axisLabel?: string
    height?: number
  }

  let {
    view,
    roles = {},
    methodsOn,
    showReference = true,
    sweep = null,
    measure = null,
    methodLabels = {},
    height = 340,
    axisLabel,
  }: Props = $props()

  let el: HTMLDivElement | undefined = $state()

  const figure = $derived.by(() => {
    const opts: ChartOptions = { roles, methodsOn, showReference, sweep, measure, methodLabels, axisLabel }
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

  onMount(() => () => {
    if (el) Plotly.purge(el)
  })
</script>

<figure class="chart">
  <figcaption class="title">{view.title}</figcaption>
  {#if figure}
    <div bind:this={el} class="plot" style:min-height="{height}px"></div>
    {#if figure.caption.length > 0}
      <p class="caption">{figure.caption.join(' · ')}</p>
    {/if}
  {:else}
    <!-- TODO(passation) : remplacer par la vue de secours measures_table quand elle existera. -->
    <p class="fallback">Cette vue ne peut pas encore être affichée ({view.type}).</p>
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
