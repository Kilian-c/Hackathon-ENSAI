<!-- VerdictBadge.svelte : Fiable / Fragile / Rompu, avec icône et mot (jamais la couleur seule) (R3). -->
<script lang="ts">
  import { verdictColorVar, verdictIcon, verdictLabel, type Verdict } from '../../lib/roles'

  interface Props {
    verdict: Verdict
    large?: boolean
  }

  let { verdict, large = false }: Props = $props()
</script>

<span class="badge" class:large style:--c={verdictColorVar(verdict)}>
  <span aria-hidden="true">{verdictIcon(verdict)}</span>
  {verdictLabel(verdict)}
</span>

<style>
  .badge {
    display: inline-flex;
    gap: var(--ct-space-1);
    align-items: center;
    padding: 0 var(--ct-space-2);
    border: 1px solid var(--c);
    border-radius: 999px;
    color: var(--c);
    font-size: var(--ct-text-sm);
    font-weight: 600;
    white-space: nowrap;
  }
  .large {
    padding: var(--ct-space-1) var(--ct-space-3);
    font-size: var(--ct-text-md);
  }
</style>
