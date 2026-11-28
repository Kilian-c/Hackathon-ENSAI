<!--
  TrainPicker.svelte : choix des thèmes d'une série d'Entraînement (plan de docs/notes/r1.md, étape 3).

  « Tout » (aucune sélection) ou une ou plusieurs disciplines, lues dans les expériences du moteur : une
  discipline ajoutée dans un YAML apparaît seule. Le lien de la série est rendu par `href` (bind:href) ;
  le dernier choix est gardé dans ce navigateur (confort seulement). Règles : lib/trainChoice.ts.
-->
<script lang="ts">
  import { onMount } from 'svelte'
  import { listExperiments } from '../../lib/labSource'
  import type { ExperimentSummary } from '../../lib/types.gen'
  import {
    MAX_CHOSEN_EXPERIMENTS,
    describeSelection,
    disciplineChoices,
    experimentFilter,
    groupByDiscipline,
    toggleDiscipline,
    toggleExperiment,
    trainHref,
    trainingFilter,
    type DisciplineChoice,
  } from '../../lib/trainChoice'

  let { href = $bindable(trainHref('toutes')) }: { href?: string } = $props()

  const STORAGE_KEY = 'crash-test.train.disciplines'

  let choices = $state.raw<DisciplineChoice[]>([])
  let selected = $state.raw<string[]>([])
  let items = $state.raw<ExperimentSummary[]>([])
  let chosen = $state.raw<string[]>([]) // théorèmes cochés un à un (prioritaires sur les disciplines)
  let open = $state(false)

  const available = $derived(choices.map((c) => c.slug))
  const groups = $derived(groupByDiscipline(items))
  const filter = $derived(experimentFilter(chosen) ?? trainingFilter(selected, available))
  const full = $derived(chosen.length >= MAX_CHOSEN_EXPERIMENTS)

  $effect(() => {
    href = trainHref(filter)
  })

  function remember(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(selected))
    } catch {
      /* stockage refusé : le choix vaut pour cette visite seulement */
    }
  }

  function restore(): string[] {
    try {
      const raw: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
      return Array.isArray(raw) ? raw.filter((s): s is string => typeof s === 'string') : []
    } catch {
      return []
    }
  }

  onMount(async () => {
    try {
      items = (await listExperiments()).items
      choices = disciplineChoices(items)
    } catch {
      items = []
      choices = [] // moteur injoignable : seul « Commencer une série » (Tout) reste, l'écran de série dira l'erreur
    }
    selected = restore().filter((slug) => choices.some((c) => c.slug === slug))
  })

  function toggle(slug: string): void {
    chosen = []
    selected = toggleDiscipline(selected, slug, available)
    remember()
  }

  function everything(): void {
    chosen = []
    selected = []
    remember()
  }

  function pick(id: string): void {
    chosen = toggleExperiment(chosen, id)
  }
</script>

{#if choices.length > 0}
  <div class="picker">
    <p class="label" id="picker-label">Quelles questions ? <span class="muted">Un ou plusieurs thèmes.</span></p>
    <div class="chips" role="group" aria-labelledby="picker-label">
      <button type="button" class="chip" aria-pressed={chosen.length === 0 && selected.length === 0} onclick={everything}>Tout</button>
      {#each choices as c (c.slug)}
        <button type="button" class="chip" aria-pressed={chosen.length === 0 && selected.includes(c.slug)} onclick={() => toggle(c.slug)}>
          {c.label}
        </button>
      {/each}
    </div>
    <p class="hint" aria-live="polite">
      {#if chosen.length > 0}
        {chosen.length} {chosen.length > 1 ? 'théorèmes choisis' : 'théorème choisi'} sur {MAX_CHOSEN_EXPERIMENTS} au plus.
      {:else}
        {describeSelection(choices, selected)}
      {/if}
    </p>
    <button type="button" class="link" aria-expanded={open} onclick={() => (open = !open)}>
      {open ? 'Masquer la liste des théorèmes' : 'Choisir des théorèmes…'}
    </button>
    {#if open}
      <div class="theorems">
        {#each groups as g (g.slug)}
          <fieldset>
            <legend>{g.label}</legend>
            {#each g.items as e (e.id)}
              <label class="check">
                <input
                  type="checkbox"
                  checked={chosen.includes(e.id)}
                  disabled={full && !chosen.includes(e.id)}
                  onchange={() => pick(e.id)}
                />
                {e.title}
              </label>
            {/each}
          </fieldset>
        {/each}
        {#if chosen.length > 0}
          <button type="button" class="link" onclick={() => (chosen = [])}>Tout décocher</button>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .picker {
    margin: var(--ct-space-4) 0 var(--ct-space-3);
  }
  .label {
    margin: 0 0 var(--ct-space-2);
    font-size: var(--ct-text-sm);
    font-weight: 600;
    color: var(--ct-text);
  }
  .muted {
    font-weight: 400;
    color: var(--ct-muted);
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .chip {
    padding: 0.25rem 0.8rem;
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface);
    color: var(--ct-muted);
    font: inherit;
    font-size: var(--ct-text-sm);
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background 0.15s;
  }
  .chip:hover {
    color: var(--ct-text);
    border-color: var(--ct-muted);
  }
  .chip[aria-pressed='true'] {
    color: var(--ct-text);
    font-weight: 600;
    border-color: var(--ct-role-method);
    background: color-mix(in srgb, var(--ct-role-method) 16%, var(--ct-surface));
  }
  .chip:focus-visible {
    outline: 2px solid var(--ct-focus);
    outline-offset: 2px;
  }
  .link {
    margin-top: var(--ct-space-2);
    padding: 0;
    border: 0;
    background: none;
    color: var(--ct-role-method);
    font: inherit;
    font-size: var(--ct-text-sm);
    text-decoration: underline;
    cursor: pointer;
  }
  .theorems {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: var(--ct-space-3);
    margin-top: var(--ct-space-2);
    max-height: 16rem;
    overflow-y: auto;
  }
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
  }
  legend {
    padding: 0;
    font-size: var(--ct-text-sm);
    font-weight: 600;
    color: var(--ct-text);
  }
  .check {
    display: flex;
    gap: var(--ct-space-2);
    align-items: baseline;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .hint {
    margin: var(--ct-space-2) 0 0;
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
</style>
