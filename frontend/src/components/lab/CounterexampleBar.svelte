<!--
  CounterexampleBar.svelte : la barre « Cas limites » (R3). Cahier, fiche F.2.
  Un clic règle tous les contrôles d'un coup (lib/state.ts, applyPreset : valeurs absentes à l'état
  sain, graine conservée, points ajoutés effacés) ; le parent affiche `explain` dans un bandeau.
-->
<script lang="ts">
  import type { Counterexample } from '../../lib/types.gen'

  interface Props {
    counterexamples: Counterexample[]
    active: string | null
    onpick: (c: Counterexample) => void
  }

  let { counterexamples, active, onpick }: Props = $props()
</script>

{#if counterexamples.length > 0}
  <nav class="bar" aria-label="Cas limites">
    <span class="title">Cas limites</span>
    {#each counterexamples as c (c.id)}
      <button type="button" aria-pressed={active === c.id} onclick={() => onpick(c)}>{c.label}</button>
    {/each}
  </nav>
{/if}

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
    align-items: center;
  }
  .title {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    margin-right: var(--ct-space-1);
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    padding: var(--ct-space-1) var(--ct-space-3);
    cursor: pointer;
  }
  button:hover,
  button[aria-pressed='true'] {
    border-color: var(--ct-role-truth);
  }
</style>
