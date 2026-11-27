<script lang="ts">
  // Navigation par l'URL (lib/state.ts, parseLink) : ?exp=... ouvre le Laboratoire, ?train=... l'Entraînement.
  // L'accueil ci-dessous est PROVISOIRE (une liste simple) : la galerie de R4 (components/home/) le remplacera.
  // ?dev=charts ouvre le banc d'essai des graphiques et la palette.
  import LabView from './components/lab/LabView.svelte'
  import TrainingView from './components/training/TrainingView.svelte'
  import { listExperiments } from './lib/labSource'
  import { LINK_VERSION, parseLink } from './lib/state'
  import type { ExperimentSummary } from './lib/types.gen'

  const link = parseLink(location.search)
  const dev = new URLSearchParams(location.search).get('dev')

  let experiments = $state<ExperimentSummary[] | null>(null)
  let listKind = $state<'api' | 'fixtures'>('api')

  $effect(() => {
    if (link.kind !== 'home' || dev) return
    listExperiments().then(
      (r) => {
        experiments = r.items
        listKind = r.kind
      },
      () => (experiments = []),
    )
  })
</script>

{#if dev === 'charts'}
  {#await import('./dev/DevPage.svelte') then m}
    <m.default />
  {/await}
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
    {#if experiments === null}
      <p class="muted">Chargement des expériences…</p>
    {:else if experiments.length === 0}
      <p class="muted">Aucune expérience disponible. Vérifiez que le moteur est lancé.</p>
    {:else}
      {#if listKind === 'fixtures'}
        <p class="muted">Le moteur ne répond pas : expériences de démonstration.</p>
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
