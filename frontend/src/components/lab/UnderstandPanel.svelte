<!--
  UnderstandPanel.svelte : le panneau « Comprendre » du Laboratoire (R3). Cahier, sections 2.2 et 2.5.
  En tête : le théorème. Puis chaque hypothèse : formule (statement_tex), contrôle, état.
  Un clic sur le nom d'une hypothèse saine la casse et ouvre son explication (why, when_broken).
-->
<script lang="ts">
  import Tex from '../Tex.svelte'
  import HypothesisControl from './HypothesisControl.svelte'
  import { hypothesisStatus, isHealthy } from '../../lib/lab'
  import type { EngineState, ExperimentSpec } from '../../lib/types.gen'

  type Value = number | boolean | string

  interface Props {
    spec: ExperimentSpec
    state: EngineState
    /** Hypothèse dont l'explication est ouverte. */
    open: string | null
    onopen: (id: string | null) => void
    onchange: (id: string, value: Value) => void
    /** Clic sur le nom d'une hypothèse saine : la casser. */
    onbreak: (id: string) => void
  }

  let { spec, state, open, onopen, onchange, onbreak }: Props = $props()

  function clickName(id: string): void {
    const healthy = isHealthy(spec.hypotheses[id], state.hypotheses[id])
    if (healthy) {
      onbreak(id)
      onopen(id)
    } else {
      onopen(open === id ? null : id)
    }
  }
</script>

<section class="understand" aria-labelledby="comprendre-titre">
  <h2 id="comprendre-titre">Comprendre</h2>
  <div class="theorem">
    <strong>{spec.theorem.name}</strong>
    <p>{spec.theorem.statement}</p>
  </div>

  <h3>Hypothèses</h3>
  <ul class="hyps">
    {#each Object.entries(spec.hypotheses) as [id, h] (id)}
      {@const value = state.hypotheses[id]}
      {@const healthy = isHealthy(h, value)}
      <li class:broken={!healthy}>
        <div class="head">
          <button
            type="button"
            class="name"
            aria-expanded={open === id}
            onclick={() => clickName(id)}
            title={healthy ? 'Casser cette hypothèse et voir pourquoi elle compte' : 'Afficher l’explication'}
          >
            <span class="dot" aria-hidden="true">{healthy ? '●' : '✕'}</span>
            {h.label}
          </button>
          <span class="status">{hypothesisStatus(h, value)}</span>
        </div>
        <div class="formula"><Tex tex={h.statement_tex} /></div>
        <HypothesisControl {id} hypothesis={h} {value} onchange={(v) => onchange(id, v)} />
        {#if open === id}
          <dl class="explain">
            <dt>À quoi elle sert</dt>
            <dd>{h.why}</dd>
            <dt>Ce que l'on voit quand elle tombe</dt>
            <dd>{h.when_broken}</dd>
          </dl>
        {/if}
      </li>
    {/each}
  </ul>
</section>

<style>
  .understand {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  h2 {
    margin: 0;
    font-size: var(--ct-text-lg);
  }
  h3 {
    margin: var(--ct-space-2) 0 0;
    font-size: var(--ct-text-md);
    color: var(--ct-muted);
  }
  .theorem p {
    margin: var(--ct-space-1) 0 0;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .hyps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-3);
  }
  .hyps li {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-2);
    padding: var(--ct-space-3);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-left: 3px solid var(--ct-border);
    border-radius: var(--ct-radius);
  }
  .hyps li.broken {
    border-left-color: var(--ct-role-rupture);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--ct-space-2);
  }
  .name {
    font: inherit;
    font-weight: 600;
    text-align: left;
    color: var(--ct-text);
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
  }
  .name:hover {
    text-decoration: underline;
  }
  .dot {
    color: var(--ct-verdict-ok);
    margin-right: var(--ct-space-1);
  }
  .broken .dot,
  .broken .status {
    color: var(--ct-role-rupture);
  }
  .status {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    text-align: right;
  }
  .formula {
    overflow-x: auto;
    overflow-y: hidden;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .explain {
    margin: 0;
    font-size: var(--ct-text-sm);
  }
  .explain dt {
    font-weight: 600;
    margin-top: var(--ct-space-1);
  }
  .explain dd {
    margin: 0;
    color: var(--ct-muted);
  }
</style>
