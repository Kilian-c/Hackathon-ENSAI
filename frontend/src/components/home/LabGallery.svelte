<script lang="ts">
  // Galerie du Laboratoire (?labo) : toutes les expériences, avec recherche et filtres par discipline et
  // par niveau. Tout vient de GET /api/experiments : rien de propre à une expérience.
  import { listExperiments } from '../../lib/labSource'
  import type { ExperimentSummary } from '../../lib/types.gen'
  import { levelLabel } from '../../lib/format'
  import { disciplineLabel, labHref, splitTitle, trainOneHref } from './experiments'

  let experiments = $state<ExperimentSummary[] | null>(null)
  let listKind = $state<'api' | 'fixtures'>('api')
  let listError = $state<string | null>(null)

  let search = $state('')
  let discipline = $state<string | null>(null)
  let level = $state<string | null>(null)

  function loadList(): void {
    listError = null
    listExperiments().then(
      (r) => {
        experiments = [...r.items].sort(
          (a, b) => Number(a.level) - Number(b.level) || a.title.localeCompare(b.title, 'fr'),
        )
        listKind = r.kind
      },
      (err) => (listError = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'),
    )
  }

  $effect(() => {
    loadList()
  })

  const disciplines = $derived(
    [...new Set((experiments ?? []).map((e) => e.discipline))].sort((a, b) =>
      disciplineLabel(a).localeCompare(disciplineLabel(b), 'fr'),
    ),
  )
  const levels = $derived(
    [...new Set((experiments ?? []).map((e) => String(e.level)))].sort((a, b) => Number(a) - Number(b)),
  )

  /** Minuscules sans accents, pour une recherche tolérante. */
  function norm(s: string): string {
    return s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  }

  const shown = $derived.by(() => {
    const q = norm(search.trim())
    return (experiments ?? []).filter(
      (e) =>
        (discipline === null || e.discipline === discipline) &&
        (level === null || String(e.level) === level) &&
        (q === '' || norm([e.title, disciplineLabel(e.discipline), ...e.concepts].join(' ')).includes(q)),
    )
  })

  const filtered = $derived(search.trim() !== '' || discipline !== null || level !== null)

  function resetFilters(): void {
    search = ''
    discipline = null
    level = null
  }
</script>

<main class="page">
  <a class="back" href="?">← Accueil</a>

  <header class="head">
    <p class="kicker">Mode libre</p>
    <h1>Laboratoire</h1>
    <p class="muted">
      Choisissez une expérience : vous pourrez y casser les hypothèses une à une et voir ce qui cède.
    </p>
  </header>

  <div class="toolbar">
    <label class="search">
      <span class="visually-hidden">Rechercher une expérience</span>
      <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><line x1="13" y1="13" x2="18" y2="18" /></svg>
      <input type="search" placeholder="Rechercher un thème, une notion…" bind:value={search} />
    </label>

    <div class="filters">
      {#if disciplines.length > 1}
        <div class="filter" role="group" aria-label="Discipline">
          <span class="filter-label">Discipline</span>
          <div class="chips">
            <button type="button" class="chip" aria-pressed={discipline === null} onclick={() => (discipline = null)}>
              Toutes
            </button>
            {#each disciplines as d (d)}
              <button type="button" class="chip" aria-pressed={discipline === d} onclick={() => (discipline = d)}>
                {disciplineLabel(d)}
              </button>
            {/each}
          </div>
        </div>
      {/if}
      {#if levels.length > 1}
        <div class="filter" role="group" aria-label="Niveau">
          <span class="filter-label">Niveau</span>
          <div class="chips">
            <button type="button" class="chip" aria-pressed={level === null} onclick={() => (level = null)}>
              Tous
            </button>
            {#each levels as l (l)}
              <button type="button" class="chip" aria-pressed={level === l} onclick={() => (level = l)}>
                <span class="pips" aria-hidden="true">
                  {#each [1, 2, 3] as k (k)}<span class="pip" class:on={k <= Number(l)}></span>{/each}
                </span>
                {levelLabel(l)}
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>

  {#if listError}
    <div class="notice" role="alert">
      <p>{listError}</p>
      <button type="button" class="btn-ghost" onclick={loadList}>Réessayer</button>
    </div>
  {:else if experiments === null}
    <div class="grid" aria-busy="true">
      {#each [0, 1, 2, 3, 4, 5] as i (i)}
        <div class="card skeleton"></div>
      {/each}
    </div>
  {:else if experiments.length === 0}
    <p class="muted">Aucune expérience disponible.</p>
  {:else}
    <p class="count muted" aria-live="polite">
      {shown.length}
      {shown.length > 1 ? 'expériences' : 'expérience'}
      {#if listKind === 'fixtures'}· démonstration (le moteur ne répond pas){/if}
      {#if filtered}· <button type="button" class="link" onclick={resetFilters}>Effacer les filtres</button>{/if}
    </p>
    {#if shown.length === 0}
      <div class="empty">
        <p>Aucune expérience ne correspond à ces filtres.</p>
        <button type="button" class="btn-ghost" onclick={resetFilters}>Effacer les filtres</button>
      </div>
    {:else}
      <ul class="grid">
        {#each shown as e, i (e.id)}
          {@const t = splitTitle(e.title)}
          {@const lvl = Number(e.level) || 1}
          <li class="card" style:--i={Math.min(i, 8)}>
            <a class="card-main" href={labHref(e.id)}>
              <span class="card-meta">
                <span class="tag">{disciplineLabel(e.discipline)}</span>
                <span class="level" title="Niveau : {levelLabel(e.level)}">
                  <span class="pips" aria-hidden="true">
                    {#each [1, 2, 3] as k (k)}<span class="pip" class:on={k <= lvl}></span>{/each}
                  </span>
                  {levelLabel(e.level)}
                </span>
              </span>
              <strong class="card-title">{t.head}</strong>
              {#if t.sub}<span class="card-sub">{t.sub}</span>{/if}
            </a>
            <div class="card-foot">
              <a class="card-link" href={labHref(e.id)}>Ouvrir →</a>
              <a class="card-link subtle" href={trainOneHref(e.id)}>S'entraîner dessus</a>
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
    margin: 0 auto;
    padding: var(--ct-space-6);
  }
  .muted {
    color: var(--ct-muted);
  }
  .back {
    color: var(--ct-muted);
    text-decoration: none;
    font-size: var(--ct-text-sm);
  }
  .back:hover {
    color: var(--ct-text);
  }
  .head {
    margin: var(--ct-space-6) 0 var(--ct-space-6);
  }
  .kicker {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-role-correction);
  }
  h1 {
    margin: var(--ct-space-1) 0 var(--ct-space-2);
    font-size: clamp(2rem, 4vw, 2.5rem);
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .head p:last-child {
    margin: 0;
  }

  /* --- Recherche et filtres --- */
  .toolbar {
    display: grid;
    gap: var(--ct-space-4);
    padding: var(--ct-space-4);
    margin-bottom: var(--ct-space-4);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: var(--ct-surface);
  }
  .search {
    position: relative;
    display: block;
  }
  .search svg {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    width: 1rem;
    height: 1rem;
    transform: translateY(-50%);
    fill: none;
    stroke: var(--ct-muted);
    stroke-width: 2;
    stroke-linecap: round;
  }
  .search input {
    width: 100%;
    box-sizing: border-box;
    padding: 0.6rem 0.75rem 0.6rem 2.25rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-bg);
    color: var(--ct-text);
    font: inherit;
  }
  .search input:focus {
    border-color: var(--ct-role-method);
    outline: none;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-4) var(--ct-space-8);
  }
  .filter {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-2) var(--ct-space-3);
  }
  .filter-label {
    font-size: 0.8rem;
    color: var(--ct-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    border: 1px solid var(--ct-border);
    background: var(--ct-bg);
    color: var(--ct-muted);
    font: inherit;
    font-size: var(--ct-text-sm);
    cursor: pointer;
  }
  .chip:hover {
    color: var(--ct-text);
  }
  .chip[aria-pressed='true'] {
    color: var(--ct-text);
    border-color: var(--ct-role-method);
    background: color-mix(in srgb, var(--ct-role-method) 14%, var(--ct-surface));
  }
  .pips {
    display: inline-flex;
    gap: 3px;
  }
  .pip {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ct-border);
  }
  .pip.on {
    background: var(--ct-role-method);
  }
  .count {
    margin: 0 0 var(--ct-space-3);
    font-size: var(--ct-text-sm);
  }
  .link {
    padding: 0;
    border: none;
    background: none;
    color: var(--ct-role-method);
    font: inherit;
    cursor: pointer;
  }
  .link:hover {
    text-decoration: underline;
  }

  /* --- Cartes --- */
  .grid {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
    gap: var(--ct-space-4);
  }
  .card {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: var(--ct-surface);
    transition:
      border-color 0.15s,
      transform 0.15s;
  }
  /* Ouverture comme l'accueil : en-tête et filtres en fondu, puis les cartes montent l'une après l'autre.
     `backwards` : une fois l'animation finie, le transform du survol reprend la main. */
  @keyframes ct-fade-in {
    from {
      opacity: 0;
    }
  }
  @keyframes ct-rise-in {
    from {
      opacity: 0;
      transform: translateY(24px) scale(0.98);
    }
  }
  .back,
  .head {
    animation: ct-fade-in 0.6s ease-out backwards;
  }
  .toolbar {
    animation: ct-fade-in 0.6s ease-out 0.15s backwards;
  }
  .card:not(.skeleton) {
    animation: ct-rise-in 0.7s cubic-bezier(0.22, 1, 0.36, 1) backwards;
    animation-delay: calc(0.2s + var(--i, 0) * 0.06s);
  }
  .card:hover {
    border-color: var(--ct-role-method);
    transform: translateY(-2px);
  }
  .card-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--ct-space-2);
    padding: var(--ct-space-6) var(--ct-space-6) var(--ct-space-4);
    color: var(--ct-text);
    text-decoration: none;
  }
  .card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--ct-space-2);
    margin-bottom: var(--ct-space-1);
    font-size: 0.8rem;
  }
  .tag {
    padding: 0.1rem 0.55rem;
    border-radius: 999px;
    background: var(--ct-surface-2);
    color: var(--ct-muted);
  }
  .level {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
    color: var(--ct-muted);
  }
  .card-title {
    font-size: 1.1rem;
    line-height: 1.3;
  }
  .card-sub {
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .card-foot {
    display: flex;
    justify-content: space-between;
    padding: var(--ct-space-3) var(--ct-space-6);
    border-top: 1px solid var(--ct-border);
    font-size: var(--ct-text-sm);
  }
  .card-link {
    color: var(--ct-role-method);
    text-decoration: none;
    font-weight: 600;
  }
  .card-link.subtle {
    color: var(--ct-muted);
    font-weight: 400;
  }
  .card-link:hover {
    text-decoration: underline;
  }
  .skeleton {
    height: 9.5rem;
    background: linear-gradient(90deg, var(--ct-surface), var(--ct-surface-2), var(--ct-surface));
    background-size: 200% 100%;
    animation: shimmer 1.4s infinite linear;
  }
  @keyframes shimmer {
    to {
      background-position: -200% 0;
    }
  }
  .notice,
  .empty {
    display: flex;
    align-items: center;
    gap: var(--ct-space-4);
    padding: var(--ct-space-4);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .notice {
    border-color: var(--ct-role-rupture);
    color: var(--ct-role-rupture);
  }
  .notice p,
  .empty p {
    margin: 0;
  }
  .btn-ghost {
    padding: 0.45rem 0.9rem;
    border-radius: var(--ct-radius);
    border: 1px solid var(--ct-border);
    background: transparent;
    color: var(--ct-text);
    font: inherit;
    cursor: pointer;
  }
  .btn-ghost:hover {
    background: var(--ct-surface-2);
  }
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  @media (prefers-reduced-motion: reduce) {
    .back,
    .head,
    .toolbar,
    .card:not(.skeleton) {
      animation: none;
    }
    .card {
      transition: none;
    }
    .card:hover {
      transform: none;
    }
    .skeleton {
      animation: none;
    }
  }
</style>
