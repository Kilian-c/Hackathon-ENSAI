<!--
  ControlsPanel.svelte : les contrôles de l'étape « Expérimenter » (R3).
  Version compacte : pour chaque hypothèse, son nom, son état et son contrôle ; l'explication
  (when_broken) n'apparaît que lorsqu'elle est cassée, avec un lien vers l'étape Comprendre.
  Puis les paramètres. Le composant ne garde aucun état.
-->
<script lang="ts">
  import HypothesisControl from './HypothesisControl.svelte'
  import ParamControl from './ParamControl.svelte'
  import { hypothesisStatus, isHealthy } from '../../lib/lab'
  import type { EngineState, ExperimentSpec } from '../../lib/types.gen'

  type Value = number | boolean | string

  interface Props {
    spec: ExperimentSpec
    engine: EngineState
    onhypothesis: (id: string, value: Value) => void
    onparam: (id: string, value: number | boolean) => void
    /** Ouvrir l'explication complète d'une hypothèse (étape Comprendre). */
    onexplain: (id: string) => void
    onheal: () => void
  }

  let { spec, engine, onhypothesis, onparam, onexplain, onheal }: Props = $props()

  const anyBroken = $derived(Object.entries(spec.hypotheses).some(([id, h]) => !isHealthy(h, engine.hypotheses[id])))
</script>

<section class="group" aria-labelledby="hyp-ctl">
  <div class="group-head">
    <h2 id="hyp-ctl">Hypothèses</h2>
    {#if anyBroken}
      <button type="button" class="link" onclick={onheal}>Tout rétablir</button>
    {/if}
  </div>
  <ul class="hyps">
    {#each Object.entries(spec.hypotheses) as [id, h] (id)}
      {@const value = engine.hypotheses[id]}
      {@const healthy = isHealthy(h, value)}
      <li class:broken={!healthy}>
        <div class="head">
          <span class="name"><span class="dot" aria-hidden="true">{healthy ? '●' : '✕'}</span>{h.label}</span>
          <span class="status">{hypothesisStatus(h, value)}</span>
        </div>
        <HypothesisControl {id} hypothesis={h} {value} onchange={(v) => onhypothesis(id, v)} />
        {#if !healthy}
          <p class="effect">
            {h.when_broken}
            <button type="button" class="link" onclick={() => onexplain(id)}>Pourquoi ?</button>
          </p>
        {/if}
      </li>
    {/each}
  </ul>
</section>

{#if Object.keys(spec.params).length > 0}
  <section class="group" aria-labelledby="param-ctl">
    <h2 id="param-ctl">Paramètres</h2>
    {#each Object.entries(spec.params) as [id, p] (id)}
      <ParamControl {id} param={p} value={engine.params[id]} onchange={(v) => onparam(id, v)} />
    {/each}
  </section>
{/if}

<style>
  .group {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  .group-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  h2 {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-muted);
  }
  .hyps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-4);
  }
  .hyps li {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-1);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--ct-space-2);
    font-size: var(--ct-text-sm);
  }
  .name {
    font-weight: 600;
  }
  .dot {
    color: var(--ct-verdict-ok);
    margin-right: var(--ct-space-2);
    font-size: 0.7rem;
  }
  .broken .dot,
  .broken .status {
    color: var(--ct-role-rupture);
  }
  .status {
    color: var(--ct-muted);
    text-align: right;
  }
  .effect {
    margin: var(--ct-space-1) 0 0;
    padding-left: var(--ct-space-3);
    border-left: 2px solid var(--ct-role-rupture);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .link {
    padding: 0;
    border: none;
    background: none;
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-role-method);
    cursor: pointer;
  }
  .link:hover {
    text-decoration: underline;
  }
</style>
