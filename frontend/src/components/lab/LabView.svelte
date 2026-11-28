<!--
  LabView.svelte : le Laboratoire (R3). Cahier, sections 2.2, 3.1 et 3.2 ; CLAUDE.md, section 10.

  Une seule expérience à l'écran, entièrement décrite par son YAML (ExperimentSpec) : aucun code
  propre à un théorème. Trois étapes, une seule visible à la fois, pour alléger l'écran (parcours du
  cahier, section 2.2) : Comprendre (lecture), Expérimenter, Défis.
  Expérimenter montre l'essentiel d'abord : les contrôles à gauche (cas limites et animation repliés),
  puis le Résultat (jauge de la mesure principale, phrase « Que se passe-t-il ? », bouton Correction),
  puis le graphique ; l'équation dynamique et toutes les mesures sont repliées dessous. Deux états :
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
  import Inspector from './Inspector.svelte'
  import {
    cardSide,
    inspectableCount,
    inspectionFor,
    injectedIndex,
    selectionFor,
    selectionHolds,
    type Selection,
  } from '../../lib/inspect'
  import AutoSweepPlayer from './AutoSweepPlayer.svelte'
  import ChallengesPanel from './ChallengesPanel.svelte'
  import ControlsPanel from './ControlsPanel.svelte'
  import CounterexampleBar from './CounterexampleBar.svelte'
  import MeasurePanel from './MeasurePanel.svelte'
  import ResultPanel from './ResultPanel.svelte'
  import UnderstandStage from './UnderstandStage.svelte'
  import { ApiError, createLatest, type Latest } from '../../lib/executor'
  import { equationTerms } from '../../lib/equation'
  import {
    addPoint,
    allowsPoints,
    axisTitle,
    clearPoints,
    brokenValue,
    currentOnAxes,
    healAll,
    methodLabels,
    primaryMeasureId,
    primaryStates,
    removePoint,
    setValue,
    sweepRequest,
    toggleMethod,
    viewPoints,
  } from '../../lib/lab'
  import { ImportError, openExperiment, openImported, type LabSource } from '../../lib/labSource'
  import { loadDraft, loadShared } from '../../lib/share'
  import { displayRoles } from '../../lib/roles'
  import {
    applyPreset,
    brokenHypotheses,
    labLink,
    MAX_EXTRA_POINTS,
    nextDraw,
    resolveLabLink,
    type LabOrigin,
    type Link,
    type UiState,
  } from '../../lib/state'
  import type { Challenge, Counterexample, EngineState, ExperimentSpec, RunResult, SweepRequest, SweepResult } from '../../lib/types.gen'
  import { levelLabel, splitTitle } from '../../lib/format'
  import { disciplineLabel } from '../home/experiments'

  interface Props {
    link: Extract<Link, { kind: 'lab' }>
  }

  let { link }: Props = $props()

  /** Ancien onglet « Défis » (liens partagés avant les étapes) : ouvre l'étape Défis. */
  const CHALLENGES_TAB = 'defis'

  type Stage = 'comprendre' | 'experimenter' | 'defis'
  const STAGES: { id: Stage; title: string }[] = [
    { id: 'comprendre', title: 'Comprendre' },
    { id: 'experimenter', title: 'Expérimenter' },
    { id: 'defis', title: 'Défis' },
  ]
  let stage = $state<Stage>('experimenter')
  /** Défi réussi pendant la visite, annoncé dans l'étape Expérimenter. */
  let justWon = $state<Challenge | null>(null)

  let spec = $state<ExperimentSpec | null>(null)
  let source = $state<LabSource | null>(null)
  let engine = $state<EngineState | null>(null)
  let ui = $state<UiState>({ methodsOn: [], tab: null })
  let showReference = $state(true)
  let result = $state<RunResult | null>(null)
  /** État qui a produit `result` (l'inspecteur s'y réfère : `engine` peut être en avance d'un calcul). */
  let resultState = $state.raw<EngineState | null>(null)
  /** Observation ouverte dans l'inspecteur (lib/inspect.ts). */
  let selection = $state.raw<Selection | null>(null)
  let loading = $state(false)
  let error = $state<string | null>(null)
  let openHyp = $state<string | null>(null)
  let activeCounterexample = $state<Counterexample | null>(null)
  let sweep = $state<SweepResult | null>(null)
  let sweepStatus = $state<'idle' | 'loading' | 'none' | 'error'>('idle')
  let copied = $state(false)
  let pointsFull = $state(false)
  /** Balayage automatique sur un paramètre : bornes des vues figées sur la première image. */
  let frozenAxes = $state<Record<string, RunResult['views'][number]['axes']> | null>(null)
  let animating = $state<string | null>(null)
  /** Taille de la fenêtre et haut de la zone du graphique : le graphique tient dans l'écran. */
  let innerHeight = $state(900)
  let innerWidth = $state(1440)
  let viewBox: HTMLDivElement | undefined = $state()
  let viewTop = $state(0)

  let runner: Latest<EngineState, RunResult> | null = null
  let sweeper: Latest<SweepRequest, SweepResult | null> | null = null

  // --- Chargement de l'expérience (officielle, partagée ou brouillon de l'écran Import) ---
  const origin: LabOrigin = $derived(link.origin ?? { kind: 'official' })
  const imported = $derived(origin.kind !== 'official')

  async function open(): Promise<{ spec: ExperimentSpec; source: LabSource }> {
    if (origin.kind === 'official') return openExperiment(link.experimentId)
    const content = origin.kind === 'share' ? await loadShared(origin.id) : loadDraft()
    if (!content) throw new Error("Aucun brouillon d'expérience dans ce navigateur. Ouvrez l'écran Import pour en coller un.")
    return openImported(content)
  }

  $effect(() => {
    let cancelled = false
    open().then(
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
        if (resolved.ui.tab === CHALLENGES_TAB) stage = 'defis'
        if (resolved.ui.stage === 'comprendre' || resolved.ui.stage === 'defis') stage = resolved.ui.stage
        // Hypothèse demandée par le lien (pont de l'Entraînement), sinon la première cassée.
        openHyp = resolved.ui.focus ?? brokenHypotheses(opened.spec, resolved.engine)[0] ?? null
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
    if (err instanceof ImportError) {
      const first = err.report.errors[0]
      return `${err.message} (${first?.line ? `ligne ${first.line} : ` : ''}${first?.message ?? ''})`
    }
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
        resultState = state
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
    for (const c of result?.challenges ?? []) {
      if (!c.passed || wonChallenges.has(c.id)) continue
      wonChallenges.add(c.id)
      justWon = spec?.challenges.find((x) => x.id === c.id) ?? null
    }
  })

  /** État d'affichage du lien : l'étape ouverte, et l'hypothèse lue dans Comprendre. */
  function uiForLink(): UiState {
    const onStage = stage === 'experimenter' ? null : stage
    return { ...ui, stage: onStage, focus: stage === 'comprendre' ? openHyp : null }
  }

  // --- Lien de partage : recopié dans l'URL (sans nouvelle entrée d'historique) ---
  $effect(() => {
    if (!spec || !engine) return
    history.replaceState(null, '', labLink(spec, engine, uiForLink(), origin))
  })

  // --- Onglets du graphique : les vues renvoyées par le moteur ---
  const tabs = $derived((result?.views ?? []).map((v) => ({ id: v.id, title: v.title })))
  const activeTab = $derived(tabs.some((t) => t.id === ui.tab) ? (ui.tab as string) : (tabs[0]?.id ?? null))
  const activeViewRaw = $derived(result?.views.find((v) => v.id === activeTab) ?? null)
  const activeView = $derived(
    activeViewRaw && frozenAxes?.[activeViewRaw.id] ? { ...activeViewRaw, axes: frozenAxes[activeViewRaw.id] } : activeViewRaw,
  )
  /** La case « Référence » ne s'affiche que si le graphique a une série de Référence à montrer. */
  const viewHasReference = $derived(activeView?.series.some((s) => s.role === 'reference') ?? false)
  const sweepTargets = $derived(
    activeView?.type === 'sensitivity' || activeView?.type === 'validity_domain'
      ? (spec?.views.find((v) => v.id === activeView.id)?.sweep?.axes ?? [])
      : [],
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

  // Seulement le balayage de la vue ouverte : celui d'une autre vue (1 axe ou 2) ne s'affiche jamais.
  const sweepMatches = $derived(
    !!sweep && sweep.axes.length === sweepTargets.length && sweep.axes.every((a, i) => a.target === sweepTargets[i]),
  )
  const sweepShown = $derived(
    sweep && engine && sweepMatches ? { ...sweep, current: currentOnAxes(engine, sweepTargets) } : null,
  )

  // --- Dérivés d'affichage ---
  const methodsOnSet = $derived(new Set(ui.methodsOn))
  const roles = $derived(result ? displayRoles(result.methods) : {})
  const labels = $derived(result ? methodLabels(result.methods) : {})
  const primaryId = $derived(result ? primaryMeasureId(result) : null)
  const sweptMeasure = $derived(result ? (result.measures[sweep?.measure ?? primaryId ?? ''] ?? null) : null)
  /** Termes de l'équation en cause (résumé du bloc repliable « Équation dynamique »). */
  const termTones = $derived.by(() => {
    if (!spec || !result) return { broken: 0, repaired: 0 }
    const terms = equationTerms(spec.equation, result.equation, {
      methods: result.methods,
      primaryStates: primaryStates(result),
      methodsOn: ui.methodsOn,
    })
    return {
      broken: terms.filter((t) => t.tone === 'broken').length,
      repaired: terms.filter((t) => t.tone === 'repaired').length,
    }
  })
  const pointsHere = $derived(spec ? allowsPoints(spec, activeView?.id ?? null) : false)
  const placed = $derived(spec && engine ? viewPoints(spec, engine) : [])
  const titleParts = $derived(splitTitle(spec?.title ?? ''))

  // --- Hauteur du graphique : remplir la fenêtre sans la dépasser (pas de défilement pour le voir) ---
  /** Place gardée sous le graphique (légende du bas, marge du panneau). */
  const CHART_BOTTOM = 64
  const chartHeight = $derived(Math.round(Math.min(780, Math.max(320, innerHeight - viewTop - CHART_BOTTOM))))

  $effect(() => {
    // Remesure quand la fenêtre, l'étape, l'onglet ou les bandeaux du haut changent.
    void [innerHeight, innerWidth, stage, activeTab, result === null, pointsFull, error === null, source?.kind]
    const el = viewBox
    if (!el) return
    const frame = requestAnimationFrame(() => (viewTop = el.getBoundingClientRect().top + window.scrollY))
    return () => cancelAnimationFrame(frame)
  })

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

  /** Depuis Comprendre : casser l'hypothèse (si elle est saine) et passer à l'expérience. */
  function tryHypothesis(id: string): void {
    if (!spec || !engine) return
    if (!brokenHypotheses(spec, engine).includes(id)) changeHypothesis(id, brokenValue(spec.hypotheses[id]))
    openHyp = id
    stage = 'experimenter'
  }

  /** Depuis Expérimenter : l'explication complète de l'hypothèse, dans Comprendre. */
  function explainHypothesis(id: string): void {
    openHyp = id
    stage = 'comprendre'
  }

  function pickCounterexample(c: Counterexample): void {
    if (!spec || !engine) return
    engine = applyPreset(spec, engine, { params: c.state.params as EngineState['params'], hypotheses: c.state.hypotheses })
    activeCounterexample = c
    pointsFull = false
    openHyp = Object.keys(c.state.hypotheses)[0] ?? openHyp
    stage = 'experimenter'
  }

  function heal(): void {
    if (!spec || !engine) return
    engine = healAll(spec, engine)
    activeCounterexample = null
  }

  // --- Ajout de points par clic (fiche F) : toutes les vues se recalculent ---
  function placePoint(at: { x: number; y: number }): void {
    if (!spec || !engine) return
    const next = addPoint(spec, engine, at)
    pointsFull = next === null
    if (next) engine = next
  }

  function unplacePoint(index: number): void {
    if (!spec || !engine) return
    engine = removePoint(spec, engine, index)
    pointsFull = false
  }

  // --- Inspecteur d'observation (fiche F.6) : clic sur un point d'une vue `inspect: true` ---
  const canInspectHere = $derived(activeView ? inspectableCount(activeView) > 0 : false)
  const inspection = $derived(
    canInspectHere && activeView && selection ? inspectionFor(activeView, selection.index) : null,
  )

  // La fiche se ferme si le point disparaît (nouveau tirage, n changé, point posé retiré).
  $effect(() => {
    if (selection && activeView && resultState && !selectionHolds(selection, activeView, resultState)) {
      selection = null
    }
  })

  function inspect(target: { index: number } | { injected: number }): void {
    if (!activeView || !resultState) return
    const index =
      'index' in target
        ? target.index
        : injectedIndex(inspectableCount(activeView), resultState.extra_points.length, target.injected)
    selection = selectionFor(activeView, resultState, index)
  }

  function removeInspected(): void {
    if (selection?.injected == null) return
    unplacePoint(selection.injected)
    selection = null
  }

  function clearAllPoints(): void {
    if (!spec || !engine) return
    engine = clearPoints(spec, engine)
    pointsFull = false
  }

  // --- Balayage automatique (fiche F) ---
  function sweepFrame(state: EngineState, res: RunResult, first: boolean): void {
    engine = state
    result = res
    resultState = state
    activeCounterexample = null
    if (first && animating?.startsWith('p.')) frozenAxes = Object.fromEntries(res.views.map((v) => [v.id, v.axes]))
  }

  function sweepPlaying(target: string | null): void {
    animating = target
    if (target === null) frozenAxes = null
  }

  // --- Domaine de validité : un clic sur une case règle les deux contrôles ---
  function pickCell(i: number, j: number): void {
    if (!spec || !engine || !sweepShown || sweepShown.axes.length < 2) return
    let next = engine
    for (const [axis, k] of [[sweepShown.axes[0], i], [sweepShown.axes[1], j]] as const) {
      const v = axis.values[k]
      if (v === undefined) continue
      const [kind, id] = axis.target.split('.', 2) as ['h' | 'p', string]
      next = setValue(spec, next, kind, id, v)
    }
    engine = next
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
    const url = `${location.origin}${location.pathname}${labLink(spec, engine, uiForLink(), origin)}`
    try {
      await navigator.clipboard.writeText(url)
      copied = true
      setTimeout(() => (copied = false), 2000)
    } catch {
      window.prompt('Copiez ce lien :', url)
    }
  }
</script>

<svelte:window bind:innerHeight bind:innerWidth />

{#if error && !result}
  <div class="state-msg error" role="alert">
    <p>{error}</p>
    <p><button type="button" onclick={() => location.reload()}>Réessayer</button></p>
    <p><a href="?">Revenir à l'accueil</a>{#if imported} · <a href="?import">Ouvrir l'écran Import</a>{/if}</p>
  </div>
{:else if !spec || !engine}
  <p class="state-msg">Chargement de l'expérience…</p>
{:else}
  <div class="lab">
    <header class="top">
      <p class="crumbs">
        {#if imported}
          <a class="back" href="?import">← Import</a>
        {:else}
          <a class="back" href="?labo">← Expériences</a>
        {/if}
        <span>
          {disciplineLabel(spec.discipline)} · {levelLabel(spec.level)}
          {#if origin.kind === 'share'} · Expérience partagée{:else if origin.kind === 'draft'} · Brouillon importé{/if}
        </span>
        {#if origin.kind !== 'draft'}
          <button type="button" class="crumb-btn" onclick={copyLink}>{copied ? '✓ Lien copié' : 'Copier le lien'}</button>
        {/if}
      </p>
      <div class="title-row">
        <h1 title={spec.title}>
          {titleParts.head}{#if titleParts.tail}<span class="subtitle">{` : ${titleParts.tail}`}</span>{/if}
        </h1>
        <nav class="stages" aria-label="Étapes">
          {#each STAGES as st, k (st.id)}
            <button type="button" aria-current={stage === st.id ? 'step' : undefined} onclick={() => (stage = st.id)}>
              <span class="num">{k + 1}</span>
              {st.title}
              {#if st.id === 'defis' && spec.challenges.length > 0}
                <span class="count">{wonChallenges.size} / {spec.challenges.length}</span>
              {/if}
            </button>
          {/each}
        </nav>
      </div>
    </header>

    {#if source?.kind === 'fixtures'}
      <p class="banner fixtures">
        Données de démonstration : les résultats affichés ne viennent pas du moteur et ne suivent pas
        exactement les curseurs.
      </p>
    {/if}
    {#if error}
      <p class="banner error" role="alert">{error}</p>
    {/if}

    {#if stage === 'comprendre'}
      <UnderstandStage
        {spec}
        {engine}
        {result}
        methodsOn={ui.methodsOn}
        focus={openHyp}
        ontry={tryHypothesis}
        onpreset={pickCounterexample}
        onstart={() => (stage = 'experimenter')}
      />
    {:else if stage === 'defis'}
      <section class="challenges-stage">
        <p class="muted">
          Chaque défi se valide tout seul pendant que vous manipulez les contrôles de l'étape
          Expérimenter.
        </p>
        <ChallengesPanel challenges={spec.challenges} results={result?.challenges ?? []} won={wonChallenges} />
        <button type="button" class="primary" onclick={() => (stage = 'experimenter')}>Expérimenter →</button>
      </section>
    {:else}
      <!-- Trois colonnes sur grand écran : contrôles | graphique | résultat ; le graphique tient dans la fenêtre. -->
      <div class="workspace">
        <aside class="side">
          <ControlsPanel {spec} {engine} onhypothesis={changeHypothesis} onparam={changeParam} onheal={heal} />
          <button
            type="button"
            class="ghost draw"
            onclick={newDraw}
            title="Mêmes réglages, nouveaux échantillons (graine {engine.seed})"
          >
            ↻ Nouveau tirage
          </button>
          {#if spec.counterexamples.length > 0 || source}
            <div class="side-block extras">
              <h2 class="extras-title">Pour aller plus loin</h2>
              {#if spec.counterexamples.length > 0}
                <details class="more">
                  <summary>Cas limites ({spec.counterexamples.length})</summary>
                  <CounterexampleBar counterexamples={spec.counterexamples} active={activeCounterexample?.id ?? null} onpick={pickCounterexample} />
                </details>
              {/if}
              {#if source}
                <details class="more">
                  <summary>Animer un contrôle</summary>
                  <AutoSweepPlayer
                    {spec}
                    {engine}
                    {ui}
                    {source}
                    onframe={sweepFrame}
                    onfinish={(u) => (ui = u)}
                    onplaying={sweepPlaying}
                  />
                </details>
              {/if}
            </div>
          {/if}
        </aside>

        <aside class="results" aria-label="Résultat et explications">
          {#if justWon}
            <p class="banner won" role="status">
              <strong>✓ Défi réussi.</strong>
              {justWon.goal}
              <button type="button" class="link" onclick={() => (stage = 'defis')}>Voir les défis</button>
              <button type="button" class="link" onclick={() => (justWon = null)}>Fermer</button>
            </p>
          {/if}
          {#if activeCounterexample}
            <p class="banner counter">
              <strong>Cas limite : {activeCounterexample.label}.</strong>
              {activeCounterexample.explain}
              <button type="button" class="link" onclick={() => (activeCounterexample = null)}>Fermer</button>
            </p>
          {/if}
          {#if result}
            <ResultPanel
              {spec}
              {engine}
              {result}
              methodsOn={ui.methodsOn}
              ontoggle={toggle}
              onheal={heal}
              onexplain={explainHypothesis}
            />
          {/if}
        </aside>

        <section class="main">
          <div class="panel chart">
            <div class="tabs" role="tablist" aria-label="Vues">
              {#each tabs as t (t.id)}
                <button type="button" role="tab" aria-selected={t.id === activeTab} onclick={() => selectTab(t.id)}>
                  {t.title}
                </button>
              {/each}
            </div>
            <div class="chart-tools">
              <span>
                {#if canInspectHere && !pointsHere}
                  Cliquez sur un point pour l'inspecter.
                {/if}
                {#if pointsHere}
                  {canInspectHere
                    ? 'Cliquez sur un point pour l’inspecter, dans le vide pour en ajouter un :'
                    : 'Cliquez pour ajouter un point, sur une étoile pour la retirer :'}
                  <strong>{placed.length} / {MAX_EXTRA_POINTS}</strong>
                  {#if placed.length > 0}
                    <button type="button" class="link" onclick={clearAllPoints}>Tout retirer</button>
                  {/if}
                {/if}
              </span>
              <span class="tools-right">
                {#if loading}<span class="busy" aria-live="polite">Calcul…</span>{/if}
                {#if viewHasReference}
                  <label class="ref" title="La même expérience avec toutes les hypothèses respectées (même graine)">
                    <input type="checkbox" bind:checked={showReference} />
                    <span class="ref-mark" aria-hidden="true">┄</span> Référence (état sain)
                  </label>
                {/if}
              </span>
            </div>

            <div class="view" role="tabpanel" bind:this={viewBox}>
              {#if activeView}
                {#if (activeView.type === 'sensitivity' || activeView.type === 'validity_domain') && !sweepShown}
                  <p class="muted" style:min-height="{chartHeight}px">
                    {sweepStatus === 'loading'
                      ? 'Balayage en cours…'
                      : sweepStatus === 'error'
                        ? 'Le balayage a échoué. Réessayez dans un instant.'
                        : 'Aucun balayage disponible pour cette vue.'}
                  </p>
                {:else}
                  {#if pointsHere && pointsFull}
                    <p class="banner error" role="alert">
                      Vous avez posé {MAX_EXTRA_POINTS} points, le maximum. Retirez-en un pour en poser un autre.
                    </p>
                  {/if}
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
                      height={chartHeight}
                      bare
                      injected={pointsHere ? placed : []}
                      onaddpoint={pointsHere ? placePoint : undefined}
                      onremovepoint={pointsHere ? unplacePoint : undefined}
                      oninspect={canInspectHere ? inspect : undefined}
                      selected={inspection ? inspection.index : null}
                      axisLabels={sweepShown && sweepShown.axes.length >= 2
                        ? [axisTitle(spec, sweepShown.axes[0].target), axisTitle(spec, sweepShown.axes[1].target)]
                        : undefined}
                      onpickcell={activeView.type === 'validity_domain' ? pickCell : undefined}
                    />
                  {/key}
                  {#if inspection && selection}
                    <Inspector
                      {inspection}
                      posed={selection.injected !== null}
                      side={activeView ? cardSide(activeView, inspection.x) : 'left'}
                      onclose={() => (selection = null)}
                      onremove={removeInspected}
                    />
                  {/if}
                {/if}
              {:else}
                <p class="muted" style:min-height="{chartHeight}px">Calcul en cours…</p>
              {/if}
            </div>
          </div>

          {#if result}
            <details class="panel more">
              <summary>
                Équation dynamique
                {#if termTones.broken > 0}
                  <span class="sum-tag broken">✕ {termTones.broken} terme{termTones.broken > 1 ? 's' : ''} en cause</span>
                {:else if termTones.repaired > 0}
                  <span class="sum-tag repaired">✓ corrigée</span>
                {/if}
              </summary>
              <div class="equation">
                <DynamicEquation equation={spec.equation} {result} hypotheses={spec.hypotheses} methodsOn={ui.methodsOn} />
              </div>
            </details>
            <details class="panel more">
              <summary>Toutes les mesures</summary>
              <MeasurePanel {result} methodsOn={ui.methodsOn} />
            </details>
          {/if}
        </section>
      </div>
    {/if}
  </div>
{/if}

<style>
  .lab {
    max-width: 112rem;
    margin: 0 auto;
    padding: var(--ct-space-3) var(--ct-space-6) var(--ct-space-6);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  .top {
    display: grid;
    gap: var(--ct-space-1);
  }
  .crumbs {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--ct-space-3);
    margin: 0;
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
  .back {
    color: var(--ct-muted);
    text-decoration: none;
  }
  .back:hover,
  .crumb-btn:hover {
    color: var(--ct-text);
  }
  .crumb-btn {
    margin-left: auto;
    padding: 0;
    border: none;
    background: none;
    font-size: 0.8rem;
    color: var(--ct-muted);
    text-decoration: underline;
  }
  .title-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--ct-space-2) var(--ct-space-6);
  }
  h1 {
    flex: 1 1 22rem;
    min-width: 0;
    margin: 0;
    font-size: 1.4rem;
    line-height: 1.3;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .subtitle {
    font-weight: 400;
    color: var(--ct-muted);
  }
  .busy {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    cursor: pointer;
  }
  .ghost {
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-3);
  }
  .ghost:hover {
    background: var(--ct-surface-2);
  }
  .primary {
    justify-self: start;
    padding: 0.5rem 1.1rem;
    border: none;
    border-radius: var(--ct-radius);
    background: var(--ct-role-method);
    color: var(--ct-bg);
    font-weight: 600;
  }

  /* --- Étapes --- */
  .stages {
    display: flex;
    gap: var(--ct-space-1);
    padding: var(--ct-space-1);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface);
    flex: none;
  }
  .stages button {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
    padding: 0.25rem 0.85rem;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--ct-muted);
    font-weight: 600;
  }
  .stages button:hover {
    color: var(--ct-text);
  }
  .stages button[aria-current='step'] {
    background: var(--ct-surface-2);
    color: var(--ct-text);
    box-shadow: inset 0 0 0 1px var(--ct-border);
  }
  .num {
    display: grid;
    place-items: center;
    width: 1.3rem;
    height: 1.3rem;
    border-radius: 50%;
    border: 1px solid currentColor;
    font-size: 0.75rem;
  }
  [aria-current='step'] .num {
    background: var(--ct-role-method);
    border-color: var(--ct-role-method);
    color: var(--ct-bg);
  }
  .count {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--ct-muted);
  }

  /* --- Bandeaux --- */
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
  .banner.won {
    border-color: var(--ct-verdict-ok);
  }
  .banner.won strong {
    color: var(--ct-verdict-ok);
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

  /* --- Étape Expérimenter --- */
  .workspace {
    display: grid;
    /* Colonnes latérales proportionnelles à l'écran : le graphique garde la plus grande part. */
    grid-template-columns: clamp(15rem, 20vw, 18rem) minmax(0, 1fr) clamp(18rem, 24vw, 23rem);
    grid-template-areas: 'side main results';
    gap: var(--ct-space-4);
    align-items: start;
  }
  .side {
    grid-area: side;
    position: sticky;
    top: var(--ct-space-3);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
    padding: var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    max-height: calc(100vh - 2 * var(--ct-space-3));
    overflow-y: auto;
    box-sizing: border-box;
  }
  .results {
    grid-area: results;
    position: sticky;
    top: var(--ct-space-3);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
    max-height: calc(100vh - 2 * var(--ct-space-3));
    overflow-y: auto;
  }
  /* Écran moyen (tablette) : le résultat passe au-dessus du graphique. */
  @media (max-width: 64rem) {
    .workspace {
      grid-template-columns: minmax(15rem, 18rem) minmax(0, 1fr);
      grid-template-areas: 'side results' 'side main';
    }
    .results {
      position: static;
      max-height: none;
      overflow: visible;
    }
  }
  @media (max-width: 48rem) {
    .workspace {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas: 'side' 'results' 'main';
    }
    .side {
      position: static;
      max-height: none;
    }
  }
  .draw {
    justify-self: start;
  }
  .side-block {
    padding-top: var(--ct-space-4);
    border-top: 1px solid var(--ct-border);
  }
  .extras {
    display: grid;
    gap: var(--ct-space-3);
  }
  .extras-title {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-muted);
  }
  .main {
    grid-area: main;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
    min-width: 0;
  }
  .panel {
    padding: var(--ct-space-4) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    min-width: 0;
  }
  .equation {
    overflow-x: auto;
  }
  .ref {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
    padding: var(--ct-space-2) 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    white-space: nowrap;
    cursor: pointer;
  }
  .ref-mark {
    color: var(--ct-role-reference);
    font-weight: 700;
  }
  .chart {
    padding-top: 0;
  }
  .tabs {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-1);
    margin: 0 calc(-1 * var(--ct-space-2));
    border-bottom: 1px solid var(--ct-border);
  }
  .chart-tools {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 0 var(--ct-space-4);
    margin-bottom: var(--ct-space-1);
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
  .tools-right {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-4);
    margin-left: auto;
  }
  .tabs button {
    border: none;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 0.55rem var(--ct-space-2) 0.45rem;
    font-size: 0.85rem;
    color: var(--ct-muted);
  }
  .tabs button:hover {
    color: var(--ct-text);
  }
  .tabs button[aria-selected='true'] {
    color: var(--ct-text);
    border-bottom-color: var(--ct-role-method);
    font-weight: 600;
  }
  .view {
    position: relative; /* la fiche de l'inspecteur se pose sur le graphique */
  }
  .view .banner {
    margin-bottom: var(--ct-space-2);
  }
  details.more > summary {
    cursor: pointer;
    font-size: var(--ct-text-sm);
    font-weight: 600;
    color: var(--ct-muted);
  }
  details.panel.more {
    padding-top: var(--ct-space-3);
    padding-bottom: var(--ct-space-3);
  }
  .sum-tag {
    margin-left: var(--ct-space-2);
    font-weight: 400;
  }
  .sum-tag.broken {
    color: var(--ct-role-rupture);
  }
  .sum-tag.repaired {
    color: var(--ct-role-correction);
  }
  details.more > summary:hover {
    color: var(--ct-text);
  }
  details.more[open] > summary {
    margin-bottom: var(--ct-space-3);
  }

  /* --- Étape Défis --- */
  .challenges-stage {
    max-width: 52rem;
    display: grid;
    gap: var(--ct-space-4);
  }
  .challenges-stage > p {
    margin: 0;
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
