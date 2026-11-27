<script lang="ts">
  // Squelette de départ : la navigation (Accueil, Laboratoire, Entraînement, Bilan, Import) arrive ici.
  // L'aperçu de la palette sert à vérifier tokens.css et roles.ts ; il disparaîtra avec l'accueil.
  import {
    ALL_ROLES,
    plotlyStyle,
    roleColorVar,
    roleLabel,
    verdictColorVar,
    verdictIcon,
    verdictLabel,
    type Verdict,
  } from './lib/roles'
  import DevCharts from './dev/DevCharts.svelte'

  const apiUrl = import.meta.env.VITE_API_URL ?? ''
  const verdicts: Verdict[] = ['ok', 'warning', 'broken']

  let status = $state<'attente' | 'ok' | 'erreur'>('attente')

  $effect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(() => (status = 'ok'))
      .catch(() => (status = 'erreur'))
  })

  function describe(role: (typeof ALL_ROLES)[number]): string {
    const s = plotlyStyle(role, 'lines+markers') as {
      mode: string
      line?: { dash: string; width: number }
      marker?: { symbol: string }
    }
    const trait = s.line ? `${s.line.dash}, ${s.line.width} px` : 'aucun trait'
    const marqueur = s.marker ? s.marker.symbol : 'aucun marqueur'
    return `${trait} · ${marqueur}`
  }
</script>

<main>
  <h1>Crash-Test</h1>
  <p>Cassez une hypothèse, mesurez ce qui cède, puis réparez.</p>
  <p class="muted">
    {#if status === 'attente'}
      Connexion au moteur…
    {:else if status === 'ok'}
      Moteur connecté.
    {:else}
      Le moteur ne répond pas. Lancez-le avec <code>uv run uvicorn backend.main:app --reload --port 8000</code>.
    {/if}
  </p>

  <section>
    <h2>Palette de sens</h2>
    <ul class="roles">
      {#each ALL_ROLES as role (role)}
        <li>
          <span class="swatch" style:background={roleColorVar(role)}></span>
          <strong style:color={roleColorVar(role)}>{roleLabel(role)}</strong>
          <span class="muted">{describe(role)}</span>
        </li>
      {/each}
    </ul>
    <div class="verdicts">
      {#each verdicts as v (v)}
        <span class="badge" style:--c={verdictColorVar(v)}>{verdictIcon(v)} {verdictLabel(v)}</span>
      {/each}
    </div>
  </section>

  <DevCharts />
</main>

<style>
  main {
    max-width: 80rem;
    margin: var(--ct-space-8) auto;
    padding: 0 var(--ct-space-6);
  }
  .muted {
    color: var(--ct-muted);
  }
  section {
    margin-top: var(--ct-space-8);
    padding: var(--ct-space-4) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .roles {
    list-style: none;
    padding: 0;
    display: grid;
    gap: var(--ct-space-2);
  }
  .roles li {
    display: flex;
    align-items: center;
    gap: var(--ct-space-3);
  }
  .swatch {
    width: 1.25rem;
    height: 1.25rem;
    border-radius: var(--ct-radius);
  }
  .verdicts {
    display: flex;
    gap: var(--ct-space-3);
    margin-top: var(--ct-space-4);
  }
  .badge {
    padding: var(--ct-space-1) var(--ct-space-3);
    border: 1px solid var(--c);
    border-radius: 999px;
    color: var(--c);
    font-size: var(--ct-text-sm);
    font-weight: 600;
  }
</style>
