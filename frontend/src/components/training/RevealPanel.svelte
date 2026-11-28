<!--
  RevealPanel.svelte : la correction d'une question (R3). Cahier, annexe C.5.
  Explication, texte when_broken de l'hypothèse, puis validation par simulation : /api/run sur
  reveal.state, vue focus_view, mesures, et pont vers le Laboratoire (nouvel onglet : la série reste
  ouverte). À recréer à chaque question ({#key qid}).
-->
<script lang="ts">
  import MathText from '../MathText.svelte'
  import PlotlyChart from '../PlotlyChart.svelte'
  import MeasurePanel from '../lab/MeasurePanel.svelte'
  import { methodWithRole, toggleMethod } from '../../lib/lab'
  import { openExperiment, type LabSource } from '../../lib/labSource'
  import { canonicalState, defaultUi, labLink, type UiState } from '../../lib/state'
  import { correctChoice, revealChoice, type Answer } from '../../lib/training'
  import type { ExperimentSpec, RunResult, TrainingQuestion } from '../../lib/types.gen'

  interface Props {
    question: TrainingQuestion
    answer: Answer
  }

  let { question, answer }: Props = $props()

  const picked = $derived(question.choices.find((c) => c.id === answer.choiceId))
  const right = $derived(correctChoice(question))
  const reveal = $derived(revealChoice(question, answer.choiceId).reveal)

  let spec = $state<ExperimentSpec | null>(null)
  let kind = $state<LabSource['kind']>('api')
  let ui = $state<UiState | null>(null)
  let result = $state<RunResult | null>(null)
  let error = $state<string | null>(null)
  let showReference = $state(true)
  let attempt = $state(0)

  $effect(() => {
    void attempt // « Réessayer » relance le calcul
    const id = question.experiment_id
    const target = reveal
    let cancelled = false
    error = null
    openExperiment(id)
      .then(async (opened) => {
        const res = await opened.source.run(opened.spec, canonicalState(opened.spec, target.state))
        if (cancelled) return
        spec = opened.spec
        kind = opened.source.kind
        ui = defaultUi(opened.spec)
        result = res
      })
      .catch((err) => {
        if (!cancelled) error = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'
      })
    return () => {
      cancelled = true
    }
  })

  // La vue demandée ; à défaut, la première qui se dessine sans balayage.
  const view = $derived.by(() => {
    const drawable = result?.views.filter((v) => v.type !== 'sensitivity') ?? []
    return drawable.find((v) => v.id === reveal.focus_view) ?? drawable[0] ?? null
  })
  const hypothesis = $derived(spec && question.hypothesis ? (spec.hypotheses[question.hypothesis] ?? null) : null)
  const correction = $derived(spec ? methodWithRole(spec.methods, 'correction') : null)
  const correctionOn = $derived(!!correction && !!ui && ui.methodsOn.includes(correction.id))
  const labUrl = $derived(
    spec && ui
      ? labLink(spec, canonicalState(spec, reveal.state), {
          ...ui,
          tab: view?.id ?? null,
          // Cahier, section 3.4 : le Laboratoire s'ouvre sur Comprendre, à l'hypothèse de la question.
          stage: question.hypothesis ? 'comprendre' : null,
          focus: question.hypothesis,
        })
      : null,
  )

  function toggleCorrection(): void {
    if (spec && ui && correction) ui = toggleMethod(spec, ui, correction.id)
  }
</script>

<section class="reveal" aria-label="Correction de la question">
  <div class="feedback" class:right={answer.correct} role="status">
    <h3>{answer.correct ? '✓ Bonne réponse' : '✗ Ce n’est pas la bonne réponse'}</h3>
    {#if picked}<p><MathText text={picked.explain} /></p>{/if}
    {#if !answer.correct}
      <p><strong>La bonne réponse : <MathText text={right.label} />.</strong> <MathText text={right.explain} /></p>
    {/if}
  </div>

  {#if hypothesis}
    <div class="why">
      <h4>Quand l'hypothèse « {hypothesis.label} » est cassée</h4>
      <p><MathText text={hypothesis.when_broken} /></p>
    </div>
  {/if}

  <h3>La simulation le montre</h3>
  {#if error}
    <p class="error" role="alert">
      {error}
      <button type="button" onclick={() => (attempt += 1)}>Réessayer</button>
    </p>
  {:else if !result || !ui}
    <p class="muted">Simulation en cours…</p>
  {:else}
    {#if kind === 'fixtures'}
      <p class="banner">
        Données de démonstration : le moteur ne sert pas encore cette expérience. Le graphique ne correspond pas
        exactement à la situation de la question.
      </p>
    {/if}
    <div class="toolbar">
      {#if correction}
        <button type="button" class="correction" aria-pressed={correctionOn} onclick={toggleCorrection}>
          <span aria-hidden="true">◆</span> Correction : {correction.label}
        </button>
      {/if}
      <label>
        <input type="checkbox" bind:checked={showReference} />
        Référence (état sain)
      </label>
    </div>
    <div class="grid">
      {#if view}
        <PlotlyChart {view} {result} methodsOn={new Set(ui.methodsOn)} {showReference} height={380} />
      {/if}
      <MeasurePanel {result} methodsOn={ui.methodsOn} {showReference} />
    </div>
    <p>
      <a class="lab-link" href={labUrl} target="_blank" rel="noopener">Ouvrir dans le Laboratoire ↗</a>
    </p>
  {/if}
</section>

<style>
  .reveal {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  h3,
  h4,
  p {
    margin: 0;
  }
  h3 {
    font-size: var(--ct-text-lg);
  }
  h4 {
    font-size: var(--ct-text-md);
    color: var(--ct-muted);
  }
  .feedback,
  .why {
    display: grid;
    gap: var(--ct-space-2);
    padding: var(--ct-space-3) var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .feedback {
    border-color: var(--ct-verdict-broken);
  }
  .feedback h3 {
    color: var(--ct-verdict-broken);
  }
  .feedback.right {
    border-color: var(--ct-verdict-ok);
  }
  .feedback.right h3 {
    color: var(--ct-verdict-ok);
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-4);
    font-size: var(--ct-text-sm);
  }
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(16rem, 20rem);
    gap: var(--ct-space-4);
    align-items: start;
  }
  @media (max-width: 60rem) {
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-3);
    cursor: pointer;
  }
  .correction[aria-pressed='true'] {
    border-color: var(--ct-role-correction);
    color: var(--ct-role-correction);
    font-weight: 600;
  }
  .banner {
    padding: var(--ct-space-2) var(--ct-space-4);
    border: 1px solid var(--ct-verdict-warning);
    border-radius: var(--ct-radius);
    font-size: var(--ct-text-sm);
  }
  .muted {
    color: var(--ct-muted);
  }
  .error {
    color: var(--ct-role-rupture);
  }
  .lab-link {
    color: var(--ct-role-method);
    font-weight: 600;
  }
</style>
