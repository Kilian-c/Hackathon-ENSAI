<!--
  MeasureStrip.svelte : la mesure principale, en grand, au-dessus du graphique (R3).
  Une colonne par méthode affichée : valeur ± 2 mc_se et verdict ; la phrase du YAML (texts) de la
  méthode principale ; la valeur de la Référence. Le détail de toutes les mesures reste dans
  MeasurePanel (repliable).
-->
<script lang="ts">
  import VerdictBadge from './VerdictBadge.svelte'
  import { formatMargin, formatMeasure } from '../../lib/format'
  import { primaryMeasureId } from '../../lib/lab'
  import { displayRoles, roleColorVar } from '../../lib/roles'
  import type { RunResult } from '../../lib/types.gen'

  interface Props {
    result: RunResult
    methodsOn: readonly string[]
    showReference: boolean
  }

  let { result, methodsOn, showReference }: Props = $props()

  const id = $derived(primaryMeasureId(result))
  const m = $derived(id ? result.measures[id] : null)
  const roles = $derived(displayRoles(result.methods))
  const shown = $derived(result.methods.filter((x) => methodsOn.includes(x.id)))
  const principal = $derived(result.methods.find((x) => x.role === 'method') ?? null)
</script>

{#if m}
  <section class="strip" aria-label="Mesure principale">
    <p class="label">{m.label}</p>
    <div class="values">
      {#each shown as method (method.id)}
        {@const verdict = m.states[method.id]}
        {@const margin = formatMargin(m.mc_se[method.id], m)}
        <div class="cell">
          <span class="who" style:color={roleColorVar(roles[method.id])}>{method.label}</span>
          <span class="val">
            {formatMeasure(m.values[method.id], m)}
            {#if margin}<span class="margin">{margin}</span>{/if}
          </span>
          {#if verdict}<VerdictBadge {verdict} />{/if}
        </div>
      {/each}
      {#if showReference && principal && m.baseline[principal.id] != null}
        <div class="cell ref">
          <span class="who">Référence (état sain)</span>
          <span class="val">{formatMeasure(m.baseline[principal.id], m)}</span>
        </div>
      {/if}
    </div>
    {#if principal && m.texts[principal.id]}
      <p class="text">{m.texts[principal.id]}</p>
    {/if}
  </section>
{/if}

<style>
  .strip {
    display: grid;
    gap: var(--ct-space-2);
  }
  .label {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-muted);
  }
  .values {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-3) var(--ct-space-8);
  }
  .cell {
    display: grid;
    gap: var(--ct-space-1);
    justify-items: start;
  }
  .who {
    font-size: var(--ct-text-sm);
    font-weight: 600;
  }
  .ref .who,
  .ref .val {
    color: var(--ct-muted);
  }
  .val {
    font-family: var(--ct-font-mono);
    font-size: 1.6rem;
    line-height: 1.1;
  }
  .margin {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .text {
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
</style>
