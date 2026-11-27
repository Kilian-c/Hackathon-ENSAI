<!--
  ChallengesPanel.svelte : l'onglet Défis (R3). Cahier, section 3.2.
  Le moteur évalue chaque condition (`when`) et renvoie RunResult.challenges[].passed ; l'interface
  affiche l'objectif, l'indice sur demande, et le message `unlock` une fois le défi réussi.
  Un défi réussi le reste pendant la visite : la liste des défis réussis (`won`) est tenue par
  LabView, car ce panneau est détruit dès qu'on change d'onglet.
-->
<script lang="ts">
  import { SvelteSet } from 'svelte/reactivity'
  import type { Challenge, ChallengeResult } from '../../lib/types.gen'

  interface Props {
    challenges: Challenge[]
    results: ChallengeResult[]
    /** Défis réussis depuis l'ouverture de l'expérience. */
    won: ReadonlySet<string>
  }

  let { challenges, results, won }: Props = $props()

  const hints = new SvelteSet<string>()

  const passedNow = $derived(new Set(results.filter((r) => r.passed).map((r) => r.id)))
</script>

<section class="challenges" aria-label="Défis">
  {#if challenges.length === 0}
    <p class="muted">Cette expérience ne propose pas de défi.</p>
  {/if}
  <ol>
    {#each challenges as c (c.id)}
      <li class:won={won.has(c.id)}>
        <p class="goal">
          <span class="mark" aria-hidden="true">{won.has(c.id) ? '✓' : '○'}</span>
          {c.goal}
          {#if won.has(c.id)}<span class="state">{passedNow.has(c.id) ? 'Réussi' : 'Réussi plus tôt'}</span>{/if}
        </p>
        {#if won.has(c.id)}
          <p class="unlock">{c.unlock}</p>
        {:else if c.hint}
          {#if hints.has(c.id)}
            <p class="hint">{c.hint}</p>
          {:else}
            <button type="button" onclick={() => hints.add(c.id)}>Afficher un indice</button>
          {/if}
        {/if}
      </li>
    {/each}
  </ol>
</section>

<style>
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-3);
  }
  li {
    padding: var(--ct-space-3) var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  li.won {
    border-color: var(--ct-verdict-ok);
  }
  .goal {
    margin: 0;
    display: flex;
    gap: var(--ct-space-2);
    align-items: baseline;
  }
  .mark {
    color: var(--ct-muted);
  }
  .won .mark,
  .state {
    color: var(--ct-verdict-ok);
  }
  .state {
    margin-left: auto;
    font-size: var(--ct-text-sm);
    font-weight: 600;
    white-space: nowrap;
  }
  .unlock,
  .hint {
    margin: var(--ct-space-2) 0 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  button {
    margin-top: var(--ct-space-2);
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-2);
    cursor: pointer;
  }
  .muted {
    color: var(--ct-muted);
  }
</style>
