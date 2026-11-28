<!--
  QuestionCard.svelte : l'énoncé, la vue de diagnostic, les choix et les trois crans de confiance (R3).
  Après la réponse, la carte est verrouillée et marque la bonne réponse (icône et mot, jamais la
  couleur seule). À recréer à chaque question ({#key qid}).
-->
<script lang="ts">
  import MathText from '../MathText.svelte'
  import PlotlyChart from '../PlotlyChart.svelte'
  import { CONFIDENCE_LEVELS, confidenceLabel, type Answer, type ConfidenceLevel } from '../../lib/training'
  import type { TrainingQuestion } from '../../lib/types.gen'

  interface Props {
    question: TrainingQuestion
    answer: Answer | null
    /** Titre du théorème de la question, quand il est connu. */
    theorem?: string
    onanswer: (choiceId: string, level: ConfidenceLevel) => void
  }

  let { question, answer, onanswer, theorem }: Props = $props()

  let selected = $state<string | null>(null)
  let level = $state<ConfidenceLevel | null>(null)

  const picked = $derived(answer?.choiceId ?? selected)
  const chosenLevel = $derived(answer?.level ?? level)

  // Diagnostic : seules les méthodes présentes dans la vue, SANS la Référence (elle donnerait la réponse
  // quand l'état à reconnaître est l'état sain).
  const methodsShown = $derived(
    new Set((question.initial_view?.series ?? []).flatMap((s) => (s.method && s.role !== 'reference' ? [s.method] : []))),
  )

  function submit(event: SubmitEvent): void {
    event.preventDefault()
    if (selected && level && !answer) onanswer(selected, level)
  }
</script>

<form class="card" onsubmit={submit}>
  {#if theorem}<p class="theorem">Théorème : {theorem}</p>{/if}
  <h2 id="enonce"><MathText text={question.prompt} /></h2>

  {#if question.initial_view}
    <PlotlyChart view={question.initial_view} methodsOn={methodsShown} showReference={false} height={320} />
  {/if}

  <fieldset disabled={!!answer} aria-labelledby="enonce">
    <div class="choices">
      {#each question.choices as c (c.id)}
        <label
          class="choice"
          class:selected={picked === c.id}
          class:right={!!answer && c.correct}
          class:wrong={!!answer && !c.correct && picked === c.id}
        >
          <input type="radio" name="choix" value={c.id} checked={picked === c.id} onchange={() => (selected = c.id)} />
          <span class="label"><MathText text={c.label} /></span>
          {#if answer && c.correct}
            <span class="mark">✓ Bonne réponse{picked === c.id ? ' (la vôtre)' : ''}</span>
          {:else if answer && picked === c.id}
            <span class="mark">✗ Votre réponse</span>
          {/if}
        </label>
      {/each}
    </div>
  </fieldset>

  {#if answer}
    <p class="muted">Votre confiance : {confidenceLabel(answer.level)}.</p>
  {:else}
    <fieldset>
      <legend>Quelle est votre confiance ?</legend>
      <div class="levels">
        {#each CONFIDENCE_LEVELS as l (l.id)}
          <label class="level" class:selected={chosenLevel === l.id}>
            <input type="radio" name="confiance" value={l.id} checked={chosenLevel === l.id} onchange={() => (level = l.id)} />
            {l.label}
          </label>
        {/each}
      </div>
    </fieldset>
    <div class="submit">
      <button type="submit" disabled={!selected || !level}>Valider ma réponse</button>
      {#if !selected || !level}
        <span class="muted">Choisissez une réponse et un niveau de confiance.</span>
      {/if}
    </div>
  {/if}
</form>

<style>
  .theorem {
    margin: 0;
    font-size: var(--ct-text-sm);
    font-weight: 600;
    color: var(--ct-role-method);
  }
  .card {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  h2 {
    margin: 0;
    font-size: var(--ct-text-lg);
  }
  fieldset {
    border: none;
    margin: 0;
    padding: 0;
    min-width: 0;
  }
  legend {
    padding: 0 0 var(--ct-space-2);
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .choices {
    display: grid;
    gap: var(--ct-space-2);
  }
  .choice,
  .level {
    display: flex;
    align-items: center;
    gap: var(--ct-space-3);
    padding: var(--ct-space-2) var(--ct-space-4);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    cursor: pointer;
  }
  .choice.selected,
  .level.selected {
    border-color: var(--ct-role-method);
  }
  .choice.right {
    border-color: var(--ct-verdict-ok);
  }
  .choice.wrong {
    border-color: var(--ct-verdict-broken);
  }
  fieldset:disabled .choice {
    cursor: default;
  }
  .label {
    flex: 1;
  }
  .mark {
    font-size: var(--ct-text-sm);
    font-weight: 600;
    white-space: nowrap;
  }
  .right .mark {
    color: var(--ct-verdict-ok);
  }
  .wrong .mark {
    color: var(--ct-verdict-broken);
  }
  .levels {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .submit {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-3);
  }
  button {
    font: inherit;
    font-weight: 600;
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-role-method);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-2) var(--ct-space-4);
    cursor: pointer;
  }
  button:disabled {
    border-color: var(--ct-border);
    color: var(--ct-muted);
    cursor: default;
  }
  .muted {
    margin: 0;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
</style>
