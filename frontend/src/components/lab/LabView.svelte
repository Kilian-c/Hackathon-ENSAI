<!--
  LabView.svelte : le Laboratoire (R3). Cahier, sections 2.2, 3.1 et 3.2 ; CLAUDE.md, section 10.

  Une seule expérience à l'écran, entièrement décrite par son YAML (ExperimentSpec) : aucun code
  propre à un théorème. Deux états :
  - engine (EngineState) : part au moteur à chaque changement (regroupé à 100 ms, ancien appel annulé) ;
  - ui (UiState) et showReference : affichage seul, aucun appel.
  Les deux sont recopiés dans l'URL (lien de partage) à chaque changement.
  La graine ne change qu'avec « Nouveau tirage ».
-->
<script lang="ts">
  import { onDestroy } from 'svelte'
  import { SvelteSet } from 'svelte/reactivity'
  import DynamicEquation from '../DynamicEquation.svelte'
  import PlotlyChart from '../PlotlyChart.svelte'
  import ChallengesPanel from './ChallengesPanel.svelte'
  import CounterexampleBar from './CounterexampleBar.svelte'
  import MeasurePanel from './MeasurePanel.svelte'
  import MethodBench from './MethodBench.svelte'
  import ParamControl from './ParamControl.svelte'
  import UnderstandPanel from './UnderstandPanel.svelte'
  import VerdictBadge from './VerdictBadge.svelte'
  import { ApiError, createLatest, type Latest } from '../../lib/executor'
  import {
    axisTitle,
    brokenValue,
    currentOnAxes,
    headlineVerdict,
    healAll,
    methodLabels,
    primaryMeasureId,
    setValue,
    sweepRequest,
    toggleMethod,
  } from '../../lib/lab'
  import { openExperiment, type LabSource } from '../../lib/labSource'
  import { displayRoles } from '../../lib/roles'
  import { applyPreset, brokenHypotheses, labLink, nextDraw, resolveLabLink, type Link, type UiState } from '../../lib/state'
  import type { Counterexample, EngineState, ExperimentSpec, RunResult, SweepRequest, SweepResult } from '../../lib/types.gen'
  import { levelLabel } from '../../lib/format'

  interface Props {
    link: Extract<Link, { kind: 'lab' }>
  }

  let { link }: Props = $props()

  const CHALLENGES_TAB = 'defis'

  let spec = $state<ExperimentSpec | null>(null)
  let source = $state<LabSource | null>(null)
  let engine = $state<EngineState | null>(null)
  let ui = $state<UiState>({ methodsOn: [], tab: null })
  let showReference = $state(true)
  let result = $state<RunResult | null>(null)
  let loading = $state(false)
  let error = $state<string | null>(null)
  let openHyp = $state<string | null>(null)
  let activeCounterexample = $state<Counterexample | null>(null)
  let sweep = $state<SweepResult | null>(null)
  let sweepStatus = $state<'idle' | 'loading' | 'none' | 'error'>('idle')
  let copied = $state(false)

  let runner: Latest<EngineState, RunResult> | null = null
  let sweeper: Latest<SweepRequest, SweepResult | null> | null = null

  // --- Chargement de l'expérience ---
  $effect(() => {
    const id = link.experimentId
    let cancelled = false
    openExperiment(id).then(
      (opened) => {
        if (cancelled) return
        const resolved = resolveLabLink(opened.spec, link)
        runner?.cancel()
        sweeper?.cancel()
        runner = createLatest((s: EngineState, o) => opened.source.run(opened.spec, s, o))
        sweeper = createLatest((r: SweepRequest, o) => opened.source.sweep(r, o))
        spec = opened.spec
        source = opened.source
        engine = resolved.engine
        ui = resolved.ui
        // Lien avec une hypothèse déjà cassée (partage, Entraînement) : Comprendre s'ouvre dessus.
        openHyp = brokenHypotheses(opened.spec, resolved.engine)[0] ?? null
      },
      (err) => {
        if (!cancelled) error = messageOf(err)
      },
    )
    return () => {
      cancelled = true
    }
  })

  onDestroy(() => {
    runner?.cancel()
    sweeper?.cancel()
  })

  function messageOf(err: unknown): string {
    if (err instanceof ApiError || err instanceof Error) return err.message
    return 'Une erreur inattendue est survenue.'
  }

  // --- Calcul : à chaque changement de l'état de calcul ---
  $effect(() => {
    if (!engine || !runner) return
    const state = engine
    loading = true
    runner.call(state).then(
      (res) => {
        if (res === null) return // remplacé par un appel plus récent
        result = res
        error = null
        loading = false
      },
      (err) => {
        error = messageOf(err)
        loading = false
      },
    )
  })

  // --- Défis réussis : retenus ici, quel que soit l'onglet ouvert ---
  const wonChallenges = new SvelteSet<string>()

  $effect(() => {
    for (const c of result?.challenges ?? []) if (c.passed) wonChallenges.add(c.id)
  })

  // --- Lien de partage : recopié dans l'URL (sans nouvelle entrée d'historique) ---
  $effect(() => {
    if (!spec || !engine) return
    history.replaceState(null, '', labLink(spec, engine, ui))
  })

  // --- Onglets : les vues renvoyées par le moteur, puis les Défis ---
  const tabs = $derived([
    ...(result?.views ?? []).map((v) => ({ id: v.id, title: v.title })),
    ...(spec && spec.challenges.length > 0 ? [{ id: CHALLENGES_TAB, title: 'Défis' }] : []),
  ])
  const activeTab = $derived(tabs.some((t) => t.id === ui.tab) ? (ui.tab as string) : (tabs[0]?.id ?? null))
  const activeView = $derived(result?.views.find((v) => v.id === activeTab) ?? null)
  const sweepTargets = $derived(
    activeView?.type === 'sensitivity' ? (spec?.views.find((v) => v.id === activeView.id)?.sweep?.axes ?? []) : [],
  )

  // --- Balayage de la vue Sensibilité (seulement quand elle est ouverte) ---
  const sweepReq = $derived(spec && engine && sweepTargets.length > 0 ? sweepRequest(spec, engine, sweepTargets, null) : null)
  const sweepKey = $derived(sweepReq ? JSON.stringify(sweepReq) : null)

  $effect(() => {
    // Dépendance : sweepKey seulement. Bouger le curseur de l'axe balayé ne relance rien.
    if (!sweepKey || !sweeper) return
    const req = JSON.parse(sweepKey) as SweepRequest
    sweepStatus = 'loading'
    sweeper.call(req).then(
      (res) => {
        // null : appel remplacé par un plus récent, ou pas de balayage pour cette vue (source fixtures).
        if (sweepKey !== JSON.stringify(req)) return
        sweep = res
        sweepStatus = res ? 'idle' : 'none'
      },
      () => {
        sweep = null
        sweepStatus = 'error'
      },
    )
  })

  const sweepShown = $derived(
    sweep && engine && sweepTargets.length > 0 ? { ...sweep, current: currentOnAxes(engine, sweepTargets) } : null,
  )

  // --- Dérivés d'affichage ---
  const methodsOnSet = $derived(new Set(ui.methodsOn))
  const roles = $derived(result ? displayRoles(result.methods) : {})
  const labels = $derived(result ? methodLabels(result.methods) : {})
  const primaryId = $derived(result ? primaryMeasureId(result) : null)
  const sweptMeasure = $derived(result ? (result.measures[sweep?.measure ?? primaryId ?? ''] ?? null) : null)
  const verdict = $derived(result ? headlineVerdict(result) : null)
  const anyBroken = $derived(spec && engine ? brokenHypotheses(spec, engine).length > 0 : false)

  // --- Actions ---
  function changeHypothesis(id: string, value: number | boolean | string): void {
    if (!spec || !engine) return
    engine = setValue(spec, engine, 'h', id, value)
    activeCounterexample = null
  }

  function changeParam(id: string, value: number | boolean): void {
    if (!spec || !engine) return
    engine = setValue(spec, engine, 'p', id, value)
    activeCounterexample = null
  }

  function breakHypothesis(id: string): void {
    if (spec) changeHypothesis(id, brokenValue(spec.hypotheses[id]))
  }

  function pickCounterexample(c: Counterexample): void {
    if (!spec || !engine) return
    engine = applyPreset(spec, engine, { params: c.state.params as EngineState['params'], hypotheses: c.state.hypotheses })
    activeCounterexample = c
    openHyp = Object.keys(c.state.hypotheses)[0] ?? openHyp
  }

  function heal(): void {
    if (!spec || !engine) return
    engine = healAll(spec, engine)
    activeCounterexample = null
  }

  function newDraw(): void {
    if (engine) engine = nextDraw(engine)
  }

  function toggle(id: string): void {
    if (spec) ui = toggleMethod(spec, ui, id)
  }

  function selectTab(id: string): void {
    ui = { ...ui, tab: id }
  }

  async function copyLink(): Promise<void> {
    if (!spec || !engine) return
    const url = `${location.origin}${location.pathname}${labLink(spec, engine, ui)}`
    try {
      await navigator.clipboard.writeText(url)
      copied = true
      setTimeout(() => (copied = false), 2000)
    } catch {
      window.prompt('Copiez ce lien :', url)
    }
  }
</script>

{#if error && !result}
  <div class="state-msg error" role="alert">
    <p>{error}</p>
    <p><button type="button" onclick={() => location.reload()}>Réessayer</button></p>
    <p><a href="?">Revenir à l'accueil</a></p>
  </div>
{:else if !spec || !engine}
  <p class="state-msg">Chargement de l'expérience…</p>
{:else}
  <div class="lab">
    <header class="top">
      <div class="titles">
        <a class="back" href="?">← Expériences</a>
        <h1>{spec.title}</h1>
        <p class="meta">{spec.discipline} · {levelLabel(spec.level)}</p>
      </div>
      <div class="actions">
        {#if verdict}<VerdictBadge {verdict} large />{/if}
        {#if loading}<span class="busy" aria-live="polite">Calcul…</span>{/if}
        <button type="button" onclick={newDraw} title="Tirer de nouveaux échantillons (graine {engine.seed})">
          Nouveau tirage
        </button>
        <button type="button" onclick={copyLink}>{copied ? 'Lien copié' : 'Copier le lien'}</button>
      </div>
    </header>

    {#if source?.kind === 'fixtures'}
      <p class="banner fixtures">
        Données de démonstration : les résultats affichés ne viennent pas du moteur et ne suivent pas
        exactement les curseurs.
      </p>
    {/if}

    <CounterexampleBar counterexamples={spec.counterexamples} active={activeCounterexample?.id ?? null} onpick={pickCounterexample} />
    {#if activeCounterexample}
      <p class="banner counter">
        <strong>{activeCounterexample.label}.</strong>
        {activeCounterexample.explain}
        <button type="button" class="link" onclick={() => (activeCounterexample = null)}>Fermer</button>
      </p>
    {/if}
    {#if error}
      <p class="banner error" role="alert">{error}</p>
    {/if}

    <div class="grid">
      <aside class="left">
        <UnderstandPanel
          {spec}
          state={engine}
          open={openHyp}
          onopen={(id) => (openHyp = id)}
          onchange={changeHypothesis}
          onbreak={breakHypothesis}
        />
        {#if anyBroken}
          <button type="button" class="heal" onclick={heal}>Rétablir toutes les hypothèses</button>
        {/if}
        {#if Object.keys(spec.params).length > 0}
          <section class="params" aria-labelledby="params-titre">
            <h3 id="params-titre">Paramètres</h3>
            {#each Object.entries(spec.params) as [id, p] (id)}
              <ParamControl {id} param={p} value={engine.params[id]} onchange={(v) => changeParam(id, v)} />
            {/each}
          </section>
        {/if}
      </aside>

      <main class="center">
        {#if result}
          <DynamicEquation equation={spec.equation} {result} hypotheses={spec.hypotheses} methodsOn={ui.methodsOn} />
        {/if}

        <!-- Banc de méthodes : la Correction et les alternatives, sans appel au moteur. -->
        <MethodBench methods={spec.methods} {roles} methodsOn={ui.methodsOn} ontoggle={toggle} />
        <div class="toolbar">
          <label class="ref">
            <input type="checkbox" bind:checked={showReference} />
            <span class="ref-mark" aria-hidden="true">┄</span> Référence (état sain)
          </label>
        </div>

        <div class="tabs" role="tablist" aria-label="Vues">
          {#each tabs as t (t.id)}
            <button type="button" role="tab" aria-selected={t.id === activeTab} onclick={() => selectTab(t.id)}>
              {t.title}
            </button>
          {/each}
        </div>

        <div class="view" role="tabpanel">
          {#if activeTab === CHALLENGES_TAB}
            <ChallengesPanel challenges={spec.challenges} results={result?.challenges ?? []} won={wonChallenges} />
          {:else if activeView}
            {#if activeView.type === 'sensitivity' && !sweepShown}
              <p class="muted">
                {sweepStatus === 'loading'
                  ? 'Balayage en cours…'
                  : sweepStatus === 'error'
                    ? 'Le balayage a échoué. Réessayez dans un instant.'
                    : 'Aucun balayage disponible pour cette vue.'}
              </p>
            {:else}
              <!-- Un graphique par vue : le zoom d'une vue ne passe pas à la suivante. -->
              {#key activeView.id}
                <PlotlyChart
                  view={activeView}
                  {result}
                  methodsOn={methodsOnSet}
                  {showReference}
                  sweep={sweepShown}
                  measure={sweptMeasure}
                  {roles}
                  methodLabels={labels}
                  axisLabel={sweepShown ? axisTitle(spec, sweepShown.axes[0].target) : undefined}
                  height={420}
                />
              {/key}
            {/if}
          {:else if !result}
            <p class="muted">Calcul en cours…</p>
          {/if}
        </div>
      </main>

      <aside class="right">
        {#if result}
          <MeasurePanel {result} methodsOn={ui.methodsOn} {showReference} />
        {/if}
      </aside>
    </div>
  </div>
{/if}

<style>
  .lab {
    max-width: 96rem;
    margin: 0 auto;
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-8);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
  }
  .top {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: var(--ct-space-4);
    flex-wrap: wrap;
  }
  h1 {
    margin: 0;
    font-size: var(--ct-text-xl);
  }
  .back,
  .meta {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .back {
    text-decoration: none;
  }
  .meta {
    margin: 0;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-3);
  }
  .busy {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
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
  button:hover {
    border-color: var(--ct-muted);
  }
  .banner {
    margin: 0;
    padding: var(--ct-space-2) var(--ct-space-4);
    border-radius: var(--ct-radius);
    border: 1px solid var(--ct-border);
    background: var(--ct-surface);
    font-size: var(--ct-text-sm);
  }
  .banner.fixtures {
    border-color: var(--ct-verdict-warning);
  }
  .banner.counter {
    border-color: var(--ct-role-truth);
  }
  .banner.error {
    border-color: var(--ct-role-rupture);
    color: var(--ct-role-rupture);
  }
  .link {
    background: none;
    border: none;
    color: var(--ct-muted);
    text-decoration: underline;
    padding: 0 var(--ct-space-1);
  }
  .grid {
    display: grid;
    grid-template-columns: minmax(18rem, 22rem) minmax(0, 1fr) minmax(16rem, 20rem);
    gap: var(--ct-space-4);
    align-items: start;
  }
  @media (max-width: 75rem) {
    .grid {
      grid-template-columns: minmax(16rem, 20rem) minmax(0, 1fr);
    }
    .right {
      grid-column: 1 / -1;
    }
  }
  @media (max-width: 50rem) {
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  .left,
  .center,
  .right {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
    min-width: 0;
  }
  .left {
    padding: var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .params {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  .params h3 {
    margin: var(--ct-space-2) 0 0;
    font-size: var(--ct-text-md);
    color: var(--ct-muted);
  }
  .heal {
    justify-self: start;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-4);
    align-items: center;
  }
  .ref {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
    font-size: var(--ct-text-sm);
  }
  .ref-mark {
    color: var(--ct-role-reference);
    font-weight: 700;
  }
  .tabs {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-1);
    border-bottom: 1px solid var(--ct-border);
  }
  .tabs button {
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    background: none;
    padding: var(--ct-space-2) var(--ct-space-3);
    color: var(--ct-muted);
  }
  .tabs button[aria-selected='true'] {
    color: var(--ct-text);
    border-bottom-color: var(--ct-role-method);
    font-weight: 600;
  }
  .muted {
    color: var(--ct-muted);
  }
  .state-msg {
    max-width: 40rem;
    margin: var(--ct-space-8) auto;
    padding: 0 var(--ct-space-6);
    color: var(--ct-muted);
  }
  .state-msg.error {
    color: var(--ct-role-rupture);
  }
</style>
