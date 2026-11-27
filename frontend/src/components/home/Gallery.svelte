<script lang="ts">
  // Galerie d'accueil (R4) : liste des expériences du moteur, filtres par niveau et discipline,
  // recherche, tri ; accès au Laboratoire, à l'Entraînement et au Bilan (?bilan).
  // Les règles (filtres, tri, liens) sont dans gallery.ts, testées par gallery.test.ts.
  import { listExperiments } from '../../lib/labSource'
  import { levelLabel } from '../../lib/format'
  import type { ExperimentSummary } from '../../lib/types.gen'
  import {
    EMPTY_FILTER,
    conceptLabel,
    countLabel,
    disciplineLabel,
    disciplinesOf,
    experimentHref,
    filterAndSort,
    isFiltered,
    levelsOf,
    trainHref,
    type GalleryFilter,
  } from './gallery'

  let experiments = $state<ExperimentSummary[] | null>(null)
  let listKind = $state<'api' | 'fixtures'>('api')
  let listError = $state<string | null>(null)
  let filter = $state<GalleryFilter>({ ...EMPTY_FILTER })

  const levels = $derived(experiments ? levelsOf(experiments) : [])
  const disciplines = $derived(experiments ? disciplinesOf(experiments) : [])
  const shown = $derived(experiments ? filterAndSort(experiments, filter) : [])

  function loadList(): void {
    listError = null
    experiments = null
    listExperiments().then(
      (r) => {
        experiments = r.items
        listKind = r.kind
      },
      (err) => (listError = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'),
    )
  }

  function resetFilters(): void {
    filter = { ...EMPTY_FILTER, sort: filter.sort }
  }

  function setDiscipline(event: Event): void {
    const value = (event.currentTarget as HTMLSelectElement).value
    filter.discipline = value === '' ? null : value
  }

  $effect(() => {
    loadList()
  })
</script>

<main class="page">
  <header class="hero">
    <h1>Crash-Test</h1>
    <p class="lead">Cassez une hypothèse, mesurez ce qui cède, puis réparez.</p>
    <nav class="actions" aria-label="Accès rapides">
      <a class="button primary" href={trainHref('toutes')}>S'entraîner sur toutes les expériences →</a>
      <a class="button" href="?bilan">Voir mon bilan →</a>
      <a class="button" href="?import">Importer une expérience →</a>
    </nav>
  </header>

  {#if listError}
    <p class="error" role="alert">{listError}</p>
    <p><button type="button" class="button" onclick={loadList}>Réessayer</button></p>
  {:else if experiments === null}
    <p class="muted" aria-live="polite">Chargement des expériences…</p>
  {:else if experiments.length === 0}
    <p class="muted">Aucune expérience disponible.</p>
  {:else}
    <section class="filters" aria-label="Filtrer les expériences">
      <div class="chips" role="group" aria-label="Niveau">
        <button type="button" class="chip" aria-pressed={filter.level === null} onclick={() => (filter.level = null)}>
          Tous les niveaux
        </button>
        {#each levels as lv (lv)}
          <button
            type="button"
            class="chip"
            aria-pressed={filter.level === lv}
            onclick={() => (filter.level = filter.level === lv ? null : lv)}
          >
            {levelLabel(lv)}
          </button>
        {/each}
      </div>

      <div class="fields">
        <label>
          <span>Discipline</span>
          <select value={filter.discipline ?? ''} onchange={setDiscipline}>
            <option value="">Toutes</option>
            {#each disciplines as d (d)}
              <option value={d}>{disciplineLabel(d)}</option>
            {/each}
          </select>
        </label>
        <label class="grow">
          <span>Rechercher</span>
          <input type="search" placeholder="Titre ou notion (moyenne, seuil…)" bind:value={filter.search} />
        </label>
        <label>
          <span>Trier par</span>
          <select bind:value={filter.sort}>
            <option value="level">Niveau</option>
            <option value="title">Titre</option>
          </select>
        </label>
      </div>

      <p class="summary">
        <span aria-live="polite">{countLabel(shown.length)}</span>
        {#if isFiltered(filter)}
          · <button type="button" class="link" onclick={resetFilters}>Effacer les filtres</button>
        {/if}
        {#if filter.discipline !== null}
          · <a href={trainHref(`discipline:${filter.discipline}`)}>
            S'entraîner en {disciplineLabel(filter.discipline).toLowerCase()} →
          </a>
        {/if}
      </p>
      {#if listKind === 'fixtures'}
        <p class="muted">Expériences de démonstration (le moteur ne répond pas).</p>
      {/if}
    </section>

    {#if shown.length === 0}
      <p class="muted">Aucune expérience ne correspond à ces filtres.</p>
      <p><button type="button" class="button" onclick={resetFilters}>Effacer les filtres</button></p>
    {:else}
      <ul class="grid">
        {#each shown as e (e.id)}
          <li class="card">
            <div class="meta">
              <span class="badge">{levelLabel(e.level)}</span>
              <span class="muted">{disciplineLabel(e.discipline)}</span>
            </div>
            <h2><a class="title" href={experimentHref(e.id)}>{e.title}</a></h2>
            {#if e.concepts.length > 0}
              <ul class="concepts" aria-label="Notions">
                {#each e.concepts as c (c)}
                  <li>{conceptLabel(c)}</li>
                {/each}
              </ul>
            {/if}
            <div class="card-actions">
              <a class="button primary" href={experimentHref(e.id)}>Ouvrir le Laboratoire</a>
              <a class="button" href={trainHref(e.id)}>S'entraîner</a>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</main>

<style>
  .page {
    max-width: 72rem;
    margin: var(--ct-space-8) auto;
    padding: 0 var(--ct-space-6);
  }
  .hero h1 {
    margin: 0 0 var(--ct-space-2);
    font-size: var(--ct-text-xl);
  }
  .lead {
    margin: 0 0 var(--ct-space-4);
    color: var(--ct-muted);
    font-size: var(--ct-text-lg);
  }
  .actions,
  .card-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .muted {
    color: var(--ct-muted);
  }
  .error {
    color: var(--ct-role-rupture);
  }

  .button {
    display: inline-block;
    padding: var(--ct-space-2) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface);
    color: var(--ct-text);
    font: inherit;
    font-size: var(--ct-text-sm);
    text-decoration: none;
    cursor: pointer;
  }
  .button:hover {
    background: var(--ct-surface-2);
  }
  .button.primary {
    border-color: var(--ct-role-method);
    color: var(--ct-role-method);
  }
  .link {
    padding: 0;
    border: none;
    background: none;
    color: var(--ct-role-method);
    font: inherit;
    text-decoration: underline;
    cursor: pointer;
  }

  .filters {
    margin: var(--ct-space-8) 0 var(--ct-space-4);
    display: grid;
    gap: var(--ct-space-3);
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .chip {
    padding: var(--ct-space-1) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface);
    color: var(--ct-text);
    font: inherit;
    font-size: var(--ct-text-sm);
    cursor: pointer;
  }
  .chip[aria-pressed='true'] {
    border-color: var(--ct-role-method);
    background: var(--ct-surface-2);
    font-weight: 600;
  }
  .fields {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-3);
  }
  .fields label {
    display: grid;
    gap: var(--ct-space-1);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .fields .grow {
    flex: 1 1 14rem;
  }
  .fields select,
  .fields input {
    padding: var(--ct-space-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface);
    color: var(--ct-text);
    font: inherit;
  }
  .summary {
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .summary a {
    color: var(--ct-role-method);
  }

  .grid {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
    gap: var(--ct-space-4);
  }
  .card {
    display: flex;
    flex-direction: column;
    gap: var(--ct-space-3);
    padding: var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .card:hover {
    border-color: var(--ct-role-method);
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-2);
    font-size: var(--ct-text-sm);
  }
  .card h2 {
    margin: 0;
    font-size: var(--ct-text-md);
    line-height: 1.35;
  }
  .title {
    color: var(--ct-text);
    text-decoration: none;
  }
  .title:hover {
    text-decoration: underline;
  }
  .concepts {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-1);
  }
  .concepts li {
    padding: 0 var(--ct-space-2);
    border-radius: var(--ct-radius);
    background: var(--ct-surface-2);
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .card-actions {
    margin-top: auto;
  }

  /* Niveau : badge neutre (les couleurs vert, orange, rouge sont réservées aux verdicts). */
  .badge {
    padding: 0 var(--ct-space-2);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    color: var(--ct-text);
    font-weight: 600;
  }
</style>
