<!--
  MeasureGauge.svelte : la jauge d'une méthode sur la mesure principale (R3).
  Zones Fiable / Fragile / Rompu calculées par lib/guide.ts (règle du verdict), trait de la cible,
  rond creux de la Référence, repère de la valeur. Le verdict est toujours écrit à côté (VerdictBadge) :
  la couleur n'est jamais le seul indice.
-->
<script lang="ts">
  import { verdictColorVar, verdictLabel } from '../../lib/roles'
  import type { Gauge } from '../../lib/guide'

  interface Props {
    gauge: Gauge
    /** Couleur du repère (rôle de la méthode). */
    color: string
    /** Écrire le nom des zones sous la jauge (première jauge seulement). */
    labels?: boolean
    /** Description pour les lecteurs d'écran. */
    description: string
  }

  let { gauge, color, labels = false, description }: Props = $props()

  const pct = (v: number): string => `${(v * 100).toFixed(2)}%`
</script>

<div class="gauge" role="img" aria-label={description}>
  <div class="track">
    <div class="zones">
      {#each gauge.zones as z, i (i)}
        <span class="zone" style:left={pct(z.from)} style:width={pct(z.to - z.from)} style:--c={verdictColorVar(z.verdict)}></span>
      {/each}
    </div>
    <span class="target" style:left={pct(gauge.target)}></span>
    {#if gauge.baseline !== null}
      <span class="ref" style:left={pct(gauge.baseline)}></span>
    {/if}
    {#if gauge.value !== null}
      <span class="marker" style:left={pct(gauge.value)} style:--m={color}></span>
    {/if}
  </div>
  {#if labels}
    <div class="names" aria-hidden="true">
      {#each gauge.zones as z, i (i)}
        {#if z.to - z.from >= 0.12}
          <span style:left={pct((z.from + z.to) / 2)} style:--c={verdictColorVar(z.verdict)}>{verdictLabel(z.verdict)}</span>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .gauge {
    padding: 0.45rem 0 0;
  }
  .track {
    position: relative;
    height: 0.55rem;
    border-radius: 999px;
    background: var(--ct-surface-2);
  }
  .zones {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    overflow: hidden;
  }
  .zone {
    position: absolute;
    top: 0;
    bottom: 0;
    background: color-mix(in srgb, var(--c) 38%, transparent);
  }
  .target {
    position: absolute;
    top: -0.3rem;
    bottom: -0.3rem;
    width: 2px;
    margin-left: -1px;
    background: var(--ct-text);
    opacity: 0.75;
  }
  .ref {
    position: absolute;
    top: 50%;
    width: 0.7rem;
    height: 0.7rem;
    margin: -0.35rem 0 0 -0.35rem;
    border: 2px solid var(--ct-role-reference);
    border-radius: 50%;
    background: var(--ct-surface);
    box-sizing: border-box;
  }
  .marker {
    position: absolute;
    top: 50%;
    width: 1rem;
    height: 1rem;
    margin: -0.5rem 0 0 -0.5rem;
    border: 3px solid var(--m);
    border-radius: 50%;
    background: var(--ct-text);
    box-sizing: border-box;
    box-shadow: 0 0 0 2px var(--ct-surface);
    transition: left 0.25s ease;
  }
  .names {
    position: relative;
    height: 1.1rem;
    margin-top: 0.3rem;
  }
  .names span {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.72rem;
    color: var(--c);
    white-space: nowrap;
  }
</style>
