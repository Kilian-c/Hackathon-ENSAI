<script lang="ts">
  // Squelette de départ : la navigation (Accueil, Laboratoire, Entraînement, Bilan, Import) arrive ici.
  const apiUrl = import.meta.env.VITE_API_URL ?? ''

  let status = $state<'attente' | 'ok' | 'erreur'>('attente')

  $effect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(() => (status = 'ok'))
      .catch(() => (status = 'erreur'))
  })
</script>

<main>
  <h1>Crash-Test</h1>
  <p>Cassez une hypothèse, mesurez ce qui cède, puis réparez.</p>
  <p class="status">
    {#if status === 'attente'}
      Connexion au moteur…
    {:else if status === 'ok'}
      Moteur connecté.
    {:else}
      Le moteur ne répond pas. Lancez-le avec <code>uv run uvicorn backend.main:app --reload --port 8000</code>.
    {/if}
  </p>
</main>

<style>
  main {
    max-width: 60rem;
    margin: 4rem auto;
    padding: 0 1.5rem;
  }
  .status {
    color: var(--ct-muted, #8b949e);
  }
</style>
