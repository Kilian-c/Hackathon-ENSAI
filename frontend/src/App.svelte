<script lang="ts">
  // Navigation par l'URL (lib/state.ts, parseLink) : ?exp=... ouvre le Laboratoire, ?train=... l'Entraînement.
  // Sans paramètre : la galerie d'accueil de R4 (components/home/Gallery.svelte).
  // ?bilan ouvre l'écran Bilan ; ?dev=charts ouvre le banc d'essai des graphiques et la palette.
  import LabView from './components/lab/LabView.svelte'
  import Gallery from './components/home/Gallery.svelte'
  import CalibrationSummary from './components/summary/CalibrationSummary.svelte'
  import TrainingView from './components/training/TrainingView.svelte'
  import { parseLink } from './lib/state'

  const link = parseLink(location.search)
  const query = new URLSearchParams(location.search)
  const dev = query.get('dev')
  const summary = query.has('bilan')
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
  <Gallery />
{/if}

<style>
  .page {
    max-width: 60rem;
    margin: var(--ct-space-8) auto;
    padding: 0 var(--ct-space-6);
  }
</style>
