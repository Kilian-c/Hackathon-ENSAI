<!--
  MeasurePanel.svelte : les mesures et leurs verdicts, pour chaque méthode affichée (R3).
  Valeur ± 2 erreurs Monte Carlo, verdict (Fiable / Fragile / Rompu), phrase du YAML (texts) et
  valeur de la Référence. Une mesure sans cible est informative : pas de verdict.
-->
<script lang="ts">
  import VerdictBadge from './VerdictBadge.svelte'
  import { formatMargin, formatMeasure } from '../../lib/format'
  import { displayRoles, roleColorVar } from '../../lib/roles'
  import type { RunResult } from '../../lib/types.gen'

  interface Props {
    result: RunResult
    methodsOn: readonly string[]
    showReference: boolean
  }

  let { result, methodsOn, showReference }: Props = $props()

  const roles = $derived(displayRoles(result.methods))
  const shown = $derived(result.methods.filter((m) => methodsOn.includes(m.id)))
  const principal = $derived(result.methods.find((x) => x.role === 'method') ?? null)
  // La mesure primaire d'abord.
  const measures = $derived(Object.entries(result.measures).sort(([, a], [, b]) => Number(b.primary) - Number(a.primary)))
</script>

<section class="measures" aria-label="Mesures">
  {#each measures as [id, m] (id)}
    <article class:primary={m.primary}>
      <h3>{m.label}{#if m.primary}<span class="tag">mesure principale</span>{/if}</h3>
      <ul>
        {#each shown as method (method.id)}
          {@const verdict = m.states[method.id]}
          {@const margin = formatMargin(m.mc_se[method.id], m)}
          <li>
            <span class="who" style:color={roleColorVar(roles[method.id])}>{method.label}</span>
            <span class="val">
              {formatMeasure(m.values[method.id], m)}
              {#if margin}<span class="margin">{margin}</span>{/if}
            </span>
            {#if verdict}<VerdictBadge {verdict} />{/if}
            {#if m.target == null && principal && method.id !== principal.id && m.values[principal.id] != null}
              <!-- Banc de méthodes : le prix d'une méthode robuste se lit sur une mesure sans cible. -->
              <p class="cost">contre {formatMeasure(m.values[principal.id], m)} pour {principal.label}</p>
            {/if}
            {#if m.texts[method.id]}<p class="text">{m.texts[method.id]}</p>{/if}
          </li>
        {/each}
      </ul>
      {#if showReference}
        {#if principal && m.baseline[principal.id] != null}
          <p class="ref">Référence (état sain) : {formatMeasure(m.baseline[principal.id], m)}</p>
        {/if}
      {/if}
    </article>
  {/each}

  {#each Object.entries(result.invalid_rate) as [method, rate] (method)}
    {#if rate > 0.05}
      <p class="warn">
        {result.methods.find((x) => x.id === method)?.label ?? method} : {formatMeasure(rate, { unit: '%', scale: 100, decimals: 1 })}
        de répétitions inexploitables, exclues des mesures.
      </p>
    {/if}
  {/each}
  <!-- Clé par position : le moteur peut envoyer plusieurs avertissements de même code. -->
  {#each result.warnings as w, i (i)}
    <p class="warn">{w.text}</p>
  {/each}
  <p class="foot">
    {#if result.repeat_used > 1}
      Calculé sur {result.repeat_used} répétitions · marge : ± 2 erreurs Monte Carlo.
    {:else}
      Calcul sur une seule trajectoire : pas de marge Monte Carlo.
    {/if}
  </p>
</section>

<style>
  .measures {
    display: grid;
    gap: var(--ct-space-3);
  }
  article {
    padding: var(--ct-space-3);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  article.primary {
    border-color: var(--ct-role-method);
  }
  h3 {
    margin: 0 0 var(--ct-space-2);
    font-size: var(--ct-text-md);
    display: flex;
    gap: var(--ct-space-2);
    align-items: baseline;
    flex-wrap: wrap;
  }
  .tag {
    font-size: var(--ct-text-sm);
    font-weight: 400;
    color: var(--ct-muted);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-2);
  }
  li {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--ct-space-1) var(--ct-space-3);
    align-items: baseline;
  }
  .who {
    grid-column: 1 / -1;
    font-weight: 600;
    font-size: var(--ct-text-sm);
  }
  .val {
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-lg);
  }
  .margin {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .cost {
    grid-column: 1 / -1;
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
  }
  .text {
    grid-column: 1 / -1;
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .ref,
  .foot {
    margin: var(--ct-space-2) 0 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .warn {
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-verdict-warning);
  }
</style>
