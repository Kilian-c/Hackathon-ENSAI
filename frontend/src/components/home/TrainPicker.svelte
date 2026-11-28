<!--
  TrainPicker.svelte : choix des thèmes d'une série d'Entraînement (plan de docs/notes/r1.md, étape 3).

  « Tout » (aucune sélection) ou une ou plusieurs disciplines, lues dans les expériences du moteur : une
  discipline ajoutée dans un YAML apparaît seule. Le lien de la série est rendu par `href` (bind:href) ;
  le dernier choix est gardé dans ce navigateur (confort seulement). Règles : lib/trainChoice.ts.
-->
<script lang="ts">
  import { onMount } from 'svelte'
  import { listExperiments } from '../../lib/labSource'
  import {
    describeSelection,
    disciplineChoices,
    toggleDiscipline,
    trainHref,
    trainingFilter,
    type DisciplineChoice,
  } from '../../lib/trainChoice'

  let { href = $bindable(trainHref('toutes')) }: { href?: string } = $props()

  const STORAGE_KEY = 'crash-test.train.disciplines'

  let choices = $state.raw<DisciplineChoice[]>([])
  let selected = $state.raw<string[]>([])

  const available = $derived(choices.map((c) => c.slug))
  const filter = $derived(trainingFilter(selected, available))

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
      choices = disciplineChoices((await listExperiments()).items)
    } catch {
      choices = [] // moteur injoignable : seul « Commencer une série » (Tout) reste, l'écran de série dira l'erreur
    }
    selected = restore().filter((slug) => choices.some((c) => c.slug === slug))
  })

  function toggle(slug: string): void {
    selected = toggleDiscipline(selected, slug, available)
    remember()
  }

  function everything(): void {
    selected = []
    remember()
  }
</script>

{#if choices.length > 0}
  <div class="picker">
    <p class="label" id="picker-label">Quelles questions ? <span class="muted">Un ou plusieurs thèmes.</span></p>
    <div class="chips" role="group" aria-labelledby="picker-label">
      <button type="button" class="chip" aria-pressed={selected.length === 0} onclick={everything}>Tout</button>
      {#each choices as c (c.slug)}
        <button type="button" class="chip" aria-pressed={selected.includes(c.slug)} onclick={() => toggle(c.slug)}>
          {c.label}
        </button>
      {/each}
    </div>
    <p class="hint" aria-live="polite">{describeSelection(choices, selected)}</p>
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
  .hint {
    margin: var(--ct-space-2) 0 0;
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
</style>
