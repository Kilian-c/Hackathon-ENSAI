<!--
  MeasuresTable.svelte : la vue de secours « measures_table » (R3). Quand une vue ne peut pas être
  dessinée, on montre les mesures de l'état actuel, par méthode affichée.
-->
<script lang="ts">
  import VerdictBadge from './lab/VerdictBadge.svelte'
  import { formatMargin, formatMeasure } from '../lib/format'
  import type { RunResult } from '../lib/types.gen'

  interface Props {
    result: Pick<RunResult, 'methods' | 'measures'>
    methodsOn: ReadonlySet<string>
  }

  let { result, methodsOn }: Props = $props()

  const shown = $derived(result.methods.filter((m) => methodsOn.has(m.id)))
  // La mesure primaire d'abord.
  const measures = $derived(Object.entries(result.measures).sort(([, a], [, b]) => Number(b.primary) - Number(a.primary)))
</script>

<div class="scroll">
  <table>
    <thead>
      <tr>
        <th scope="col">Mesure</th>
        {#each shown as method (method.id)}
          <th scope="col">{method.label}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each measures as [id, m] (id)}
        <tr>
          <th scope="row">{m.label}</th>
          {#each shown as method (method.id)}
            {@const verdict = m.states[method.id]}
            {@const margin = formatMargin(m.mc_se[method.id], m)}
            <td>
              <span class="val">{formatMeasure(m.values[method.id], m)}</span>
              {#if margin}<span class="margin">{margin}</span>{/if}
              {#if verdict}<VerdictBadge {verdict} />{/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--ct-text-sm);
  }
  th,
  td {
    padding: var(--ct-space-2) var(--ct-space-3);
    border-bottom: 1px solid var(--ct-border);
    text-align: left;
    vertical-align: baseline;
  }
  .val {
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-md);
  }
  .margin {
    color: var(--ct-muted);
  }
</style>
