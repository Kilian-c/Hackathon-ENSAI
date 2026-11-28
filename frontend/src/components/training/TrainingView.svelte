<!--
  TrainingView.svelte : l'Entraînement (R3). Cahier, section 2.3 et annexe C.5 ; CLAUDE.md, section 10.

  Une série (POST /api/training/session), question après question : réponse et cran de confiance,
  correction validée par simulation, puis résultat. Les réponses sont enregistrées dans localStorage
  par identifiant de série : recharger la page reprend la série là où elle en était.
  Le lien ?train=<filtre>&seed=<graine>&v=1 redonne la même série.
-->
<script lang="ts">
  import { onMount, tick, untrack } from 'svelte'
  import QuestionCard from './QuestionCard.svelte'
  import RevealPanel from './RevealPanel.svelte'
  import { listExperiments, openSession, type LabSource } from '../../lib/labSource'
  import { trainingLink, type Link } from '../../lib/state'
  import {
    addAnswer,
    browserStore,
    confidenceLabel,
    filterLabel,
    firstUnanswered,
    loadHistory,
    makeAnswer,
    saveAnswers,
    seriesTitle,
    shortSeriesNotice,
    storedAnswers,
    type Answer,
    type ConfidenceLevel,
  } from '../../lib/training'
  import type { TrainingSessionResponse } from '../../lib/types.gen'

  interface Props {
    link: Extract<Link, { kind: 'training' }>
  }

  let { link }: Props = $props()

  const store = browserStore()

  let session = $state.raw<TrainingSessionResponse | null>(null)
  let kind = $state<LabSource['kind']>('api')
  let answers = $state.raw<Answer[]>([])
  let index = $state(0)
  let loading = $state(true)
  let error = $state<string | null>(null)
  let copied = $state(false)
  let top = $state<HTMLElement>()
  let titles = $state.raw<Record<string, string>>({}) // identifiant d'expérience -> titre du théorème

  const total = $derived(session?.questions.length ?? 0)
  const question = $derived(session?.questions[index] ?? null)
  const answer = $derived(question ? (answers.find((a) => a.qid === question.qid) ?? null) : null)
  const score = $derived(answers.filter((a) => a.correct).length)
  // Série plus courte que demandée : pas assez de questions pour ce choix (aucun contrat en cause).
  const notice = $derived(session && kind === 'api' ? shortSeriesNotice(total, session.filter) : null)

  async function load(seed: number | null): Promise<void> {
    loading = true
    error = null
    try {
      const filter = untrack(() => link.filter)
      const opened = await openSession(filter, seed)
      session = opened.session
      kind = opened.kind
      answers = storedAnswers(loadHistory(store), opened.session)
      index = firstUnanswered(opened.session, answers)
      // La série de démonstration a sa propre graine : on ne réécrit pas le lien demandé.
      if (opened.kind === 'api') history.replaceState(null, '', trainingLink(opened.session.filter, opened.session.seed))
    } catch (err) {
      error = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'
    } finally {
      loading = false
    }
  }

  onMount(() => {
    // Les titres ne sont pas dans la série : un appel de plus, sans effet sur le contrat. Échec = pas de titre.
    listExperiments()
      .then(({ items }) => (titles = Object.fromEntries(items.map((e) => [e.id, e.title]))))
      .catch(() => {})
  })

  onMount(() => {
    void load(link.seed)
  })

  function submit(choiceId: string, level: ConfidenceLevel): void {
    if (!session || !question) return
    answers = addAnswer(answers, makeAnswer(question, choiceId, level))
    saveAnswers(store, session, answers)
  }

  async function next(): Promise<void> {
    index += 1
    await tick()
    top?.scrollIntoView({ block: 'start' })
  }

  /** Série de démonstration uniquement : elle est unique, on doit pouvoir la rejouer. */
  function restart(): void {
    if (!session) return
    answers = []
    saveAnswers(store, session, answers)
    index = 0
  }

  async function copyLink(): Promise<void> {
    if (!session) return
    const url = `${location.origin}${location.pathname}${trainingLink(session.filter, session.seed)}`
    try {
      await navigator.clipboard.writeText(url)
      copied = true
      setTimeout(() => (copied = false), 2000)
    } catch {
      window.prompt('Copiez ce lien :', url)
    }
  }
</script>

<main class="training" bind:this={top}>
  <header>
    <div>
      <a class="back" href="?">← Accueil</a>
      <h1>Entraînement</h1>
      {#if session && total > 0}
        <p class="meta">{seriesTitle(total)} · {filterLabel(session.filter)}</p>
      {/if}
    </div>
    {#if session && total > 0}
      <button type="button" onclick={copyLink}>{copied ? 'Lien copié' : 'Copier le lien de la série'}</button>
    {/if}
  </header>

  {#if loading}
    <p class="muted" aria-live="polite">Préparation de la série… Cela peut prendre quelques secondes.</p>
  {:else if error}
    <p class="error" role="alert">{error}</p>
    <p><button type="button" onclick={() => load(link.seed)}>Réessayer</button></p>
  {:else if session}
    {#if kind === 'fixtures'}
      <p class="banner">Série de démonstration : ces questions ne viennent pas du moteur.</p>
    {/if}
    {#if notice}
      <p class="banner" role="status">{notice}</p>
    {/if}

    {#if total === 0}
      <p class="muted">Aucune question disponible pour ce choix.</p>
    {:else if question}
      <p class="progress">
        Question {index + 1} sur {total}
        <progress max={total} value={answers.length} aria-label="Avancement de la série"></progress>
      </p>
      {#key question.qid}
        <QuestionCard {question} {answer} theorem={titles[question.experiment_id]} onanswer={submit} />
        {#if answer}
          <RevealPanel {question} {answer} />
          <p>
            <button type="button" class="primary" onclick={next}>
              {index + 1 < total ? 'Question suivante' : 'Voir le résultat'}
            </button>
          </p>
        {/if}
      {/key}
    {:else}
      <section class="end" aria-label="Résultat de la série">
        <h2>Série terminée</h2>
        <p class="score">{score} {score > 1 ? 'bonnes réponses' : 'bonne réponse'} sur {total}</p>
        <ol>
          {#each session.questions as q (q.qid)}
            {@const a = answers.find((x) => x.qid === q.qid)}
            <li>
              <span>
                {#if titles[q.experiment_id]}<strong>{titles[q.experiment_id]}</strong> · {/if}{q.prompt}
              </span>
              {#if a}
                <span class="outcome" class:right={a.correct}>
                  {a.correct ? '✓ Juste' : '✗ Faux'} · {confidenceLabel(a.level)}
                </span>
              {/if}
            </li>
          {/each}
        </ol>
        <p class="actions">
          {#if kind === 'api'}
            <button type="button" class="primary" onclick={() => load(null)}>Nouvelle série</button>
          {:else}
            <button type="button" class="primary" onclick={restart}>Recommencer la série</button>
          {/if}
          <a class="summary-link" href="?">Choisir d'autres thèmes</a>
          <a class="summary-link" href="?bilan">Voir mon bilan →</a>
        </p>
        <p class="summary-hint">
          Le bilan compare votre confiance à vos réussites, sur toutes vos séries : score de Brier et courbe
          de calibration.
        </p>
      </section>
    {/if}
  {/if}
</main>

<style>
  .training {
    max-width: 64rem;
    margin: 0 auto;
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-8);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
  }
  header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
    gap: var(--ct-space-4);
  }
  h1 {
    margin: 0;
    font-size: var(--ct-text-xl);
  }
  p {
    margin: 0;
  }
  .back,
  .meta {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .back {
    text-decoration: none;
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
  button.primary {
    font-size: var(--ct-text-md);
    font-weight: 600;
    border-color: var(--ct-role-method);
    padding: var(--ct-space-2) var(--ct-space-4);
  }
  .progress {
    display: flex;
    align-items: center;
    gap: var(--ct-space-3);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  progress {
    flex: 1;
    accent-color: var(--ct-role-method);
  }
  .banner {
    padding: var(--ct-space-2) var(--ct-space-4);
    border: 1px solid var(--ct-verdict-warning);
    border-radius: var(--ct-radius);
    background: var(--ct-surface);
    font-size: var(--ct-text-sm);
  }
  .muted {
    color: var(--ct-muted);
  }
  .error {
    color: var(--ct-role-rupture);
  }
  .end {
    display: grid;
    gap: var(--ct-space-3);
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .end h2 {
    margin: 0;
  }
  .summary-link {
    display: inline-block;
    margin-left: var(--ct-space-3);
    padding: var(--ct-space-2) var(--ct-space-4);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    color: var(--ct-text);
    font-weight: 600;
    text-decoration: none;
  }
  .summary-link:hover {
    background: var(--ct-surface-2);
  }
  .summary-hint {
    margin-top: var(--ct-space-2);
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .score {
    font-size: var(--ct-text-xl);
    font-weight: 600;
  }
  ol {
    margin: 0;
    padding-left: var(--ct-space-6);
    display: grid;
    gap: var(--ct-space-2);
  }
  .outcome {
    display: block;
    font-size: var(--ct-text-sm);
    color: var(--ct-verdict-broken);
  }
  .outcome.right {
    color: var(--ct-verdict-ok);
  }
</style>
