<script lang="ts">
  // Navigation par l'URL (lib/state.ts, parseLink) : ?exp=... ouvre le Laboratoire, ?train=... l'Entraînement.
  // L'accueil ci-dessous est PROVISOIRE (une liste simple) : la galerie de R4 (components/home/) le remplacera.
  // ?bilan ouvre l'écran Bilan ; ?dev=charts ouvre le banc d'essai des graphiques et la palette.
  import LabView from './components/lab/LabView.svelte'
  import CalibrationSummary from './components/summary/CalibrationSummary.svelte'
  import TrainingView from './components/training/TrainingView.svelte'
  import { listExperiments } from './lib/labSource'
  import { LINK_VERSION, parseLink } from './lib/state'
  import type { ExperimentSummary } from './lib/types.gen'

  const link = parseLink(location.search)
  const query = new URLSearchParams(location.search)
  const dev = query.get('dev')
  const summary = query.has('bilan')

  let experiments = $state<ExperimentSummary[] | null>(null)
  let listKind = $state<'api' | 'fixtures'>('api')
  let listError = $state<string | null>(null)

  function loadList(): void {
    listError = null
    listExperiments().then(
      (r) => {
        experiments = r.items
        listKind = r.kind
      },
      (err) => (listError = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'),
    )
  }

  $effect(() => {
    if (link.kind === 'home' && !dev && !summary) loadList()
  })
</script>

{#if dev === 'charts'}
  {#await import('./dev/DevPage.svelte') then m}
    <m.default />
  {/await}
{:else if summary}
  <CalibrationSummary />
{:else if link.kind === 'lab'}
  <LabView {link} />
{:else if link.kind === 'error'}
  <main class="page">
    <h1>Lien non valable</h1>
    <p>{link.message}</p>
    <p><a href="?">Revenir à l'accueil</a></p>
  </main>
{:else if link.kind === 'training'}
  <TrainingView {link} />
{:else}
  <main class="page">
    <h1>Crash-Test</h1>
    <p>Cassez une hypothèse, mesurez ce qui cède, puis réparez.</p>
    <p><a href="?train=toutes&v={LINK_VERSION}">S'entraîner avec des questions →</a></p>
    <p><a href="?bilan">Voir mon bilan →</a></p>
    {#if listError}
      <p class="error" role="alert">{listError}</p>
      <p><button type="button" onclick={loadList}>Réessayer</button></p>
    {:else if experiments === null}
      <p class="muted">Chargement des expériences…</p>
    {:else if experiments.length === 0}
      <p class="muted">Aucune expérience disponible.</p>
    {:else}
      {#if listKind === 'fixtures'}
        <p class="muted">Expériences de démonstration.</p>
      {/if}
      <ul class="list">
        {#each experiments as e (e.id)}
          <li>
            <a href="?exp={encodeURIComponent(e.id)}&v={LINK_VERSION}">
              <strong>{e.title}</strong>
              <span class="muted">{e.discipline} · {e.level}</span>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  </main>
{/if}

<style>
  .page {
    max-width: 60rem;
    margin: var(--ct-space-8) auto;
    padding: 0 var(--ct-space-6);
  }
  .muted {
    color: var(--ct-muted);
  }
  .error {
    color: var(--ct-role-rupture);
  }
  .list {
    list-style: none;
    padding: 0;
    display: grid;
    gap: var(--ct-space-3);
  }
  .list a {
    display: grid;
    gap: var(--ct-space-1);
    padding: var(--ct-space-3) var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    color: var(--ct-text);
    text-decoration: none;
  }
  .list a:hover {
    border-color: var(--ct-role-method);
  }
</style>
