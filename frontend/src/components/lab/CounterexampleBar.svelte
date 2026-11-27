<!--
  CounterexampleBar.svelte : la liste « Cas limites » (R3). Cahier, fiche F.2.
  Un clic règle tous les contrôles d'un coup (lib/state.ts, applyPreset : valeurs absentes à l'état
  sain, graine conservée, points ajoutés effacés) ; le parent affiche `explain` dans un bandeau.
  Le titre est donné par le parent (bloc repliable de la colonne des contrôles).
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
    <p class="intro">Des situations toutes prêtes, qui règlent tous les contrôles d'un coup.</p>
    {#each counterexamples as c (c.id)}
      <button type="button" aria-pressed={active === c.id} onclick={() => onpick(c)}>{c.label}</button>
    {/each}
  </nav>
{/if}

<style>
  .bar {
    display: grid;
    gap: var(--ct-space-2);
  }
  .intro {
    margin: 0 0 var(--ct-space-1);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    text-align: left;
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-left: 3px solid var(--ct-role-truth);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-2) var(--ct-space-3);
    cursor: pointer;
  }
  button:hover,
  button[aria-pressed='true'] {
    border-color: var(--ct-role-truth);
  }
</style>
