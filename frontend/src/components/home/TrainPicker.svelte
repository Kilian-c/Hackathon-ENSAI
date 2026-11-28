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
    <div class="foot">
      <p class="hint" aria-live="polite">
        {#if chosen.length > 0}
          {chosen.length} {chosen.length > 1 ? 'théorèmes choisis' : 'théorème choisi'} sur {MAX_CHOSEN_EXPERIMENTS} au plus.
        {:else}
          {describeSelection(choices, selected)}
        {/if}
      </p>
      <button
        type="button"
        class="toggle"
        aria-expanded={open}
        aria-controls="picker-theorems"
        onclick={() => (open = !open)}
      >
        {open ? 'Masquer les théorèmes' : 'Choisir des théorèmes'}
        {#if chosen.length > 0}<span class="count">{chosen.length}</span>{/if}
        <svg class="chevron" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5 6 7.5 9 4.5" /></svg>
      </button>
    </div>
    {#if open}
      <div class="panel" id="picker-theorems">
        <div class="theorems">
          {#each groups as g (g.slug)}
            <fieldset>
              <legend>{g.label}</legend>
              {#each g.items as e (e.id)}
                <label class="check" class:off={full && !chosen.includes(e.id)}>
                  <input
                    type="checkbox"
                    checked={chosen.includes(e.id)}
                    disabled={full && !chosen.includes(e.id)}
                    onchange={() => pick(e.id)}
                  />
                  <span>{e.title}</span>
                </label>
              {/each}
            </fieldset>
          {/each}
        </div>
        {#if chosen.length > 0}
          <div class="panel-foot">
            <button type="button" class="clear" onclick={() => (chosen = [])}>Tout décocher</button>
          </div>
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
  /* Phrase de sélection et bouton d'ouverture sur une même ligne. */
  .foot {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--ct-space-2) var(--ct-space-3);
    margin-top: var(--ct-space-2);
  }
  .hint {
    margin: 0;
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
    padding: 0.3rem 0.7rem 0.3rem 0.85rem;
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface);
    color: var(--ct-text);
    font: inherit;
    font-size: var(--ct-text-sm);
    font-weight: 600;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
  }
  .toggle:hover,
  .toggle[aria-expanded='true'] {
    border-color: color-mix(in srgb, var(--accent, var(--ct-role-method)) 55%, var(--ct-border));
    background: var(--ct-surface-2);
  }
  .toggle:focus-visible,
  .clear:focus-visible {
    outline: 2px solid var(--ct-focus);
    outline-offset: 2px;
  }
  .count {
    min-width: 1.25rem;
    padding: 0 0.35rem;
    border-radius: 999px;
    background: var(--accent, var(--ct-role-method));
    color: var(--ct-bg);
    font-size: 0.75rem;
    line-height: 1.25rem;
    text-align: center;
  }
  .chevron {
    width: 12px;
    height: 12px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke-linejoin: round;
    transition: transform 0.2s;
  }
  .toggle[aria-expanded='true'] .chevron {
    transform: rotate(180deg);
  }

  /* Liste des théorèmes : un panneau encadré, comme les cartes. */
  .panel {
    margin-top: var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: color-mix(in srgb, var(--ct-bg) 45%, var(--ct-surface));
    animation: panel-in 0.2s ease-out;
  }
  @keyframes panel-in {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
  }
  .theorems {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
    gap: var(--ct-space-3) var(--ct-space-4);
    padding: var(--ct-space-3);
    max-height: 16rem;
    overflow-y: auto;
  }
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
  }
  legend {
    padding: 0 var(--ct-space-2);
    margin-bottom: var(--ct-space-1);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent, var(--ct-role-method));
  }
  .check {
    display: flex;
    gap: var(--ct-space-2);
    align-items: center;
    padding: 0.3rem var(--ct-space-2);
    border-radius: var(--ct-radius);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }
  .check:hover {
    background: var(--ct-surface-2);
    color: var(--ct-text);
  }
  .check:has(input:checked) {
    color: var(--ct-text);
    background: color-mix(in srgb, var(--accent, var(--ct-role-method)) 12%, transparent);
  }
  .check.off {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .check.off:hover {
    background: none;
    color: var(--ct-muted);
  }
  .check input {
    flex: none;
    margin: 0;
    width: 0.95rem;
    height: 0.95rem;
    accent-color: var(--accent, var(--ct-role-method));
    cursor: inherit;
  }
  .panel-foot {
    display: flex;
    justify-content: flex-end;
    padding: var(--ct-space-2) var(--ct-space-3);
    border-top: 1px solid var(--ct-border);
  }
  .clear {
    padding: 0.2rem 0.6rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: none;
    color: var(--ct-muted);
    font: inherit;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .clear:hover {
    color: var(--ct-text);
    background: var(--ct-surface-2);
  }

  @media (prefers-reduced-motion: reduce) {
    .panel {
      animation: none;
    }
    .chevron {
      transition: none;
    }
  }
</style>
