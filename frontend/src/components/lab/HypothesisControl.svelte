<!--
  HypothesisControl.svelte : le contrôle d'une hypothèse, selon son type (R3).
  - continuous : curseur h dans range, avec sa valeur ;
  - boolean    : interrupteur (allumé = hypothèse respectée), suivi de l'état en mots
                 (ok_label / broken_label) ;
  - choice     : sélecteur d'option (lois), l'option saine marquée « (saine) ».
  Le composant ne garde aucun état : il reçoit la valeur et signale le changement (onchange).
-->
<script lang="ts">
  import { formatControl } from '../../lib/format'
  import { hypothesisStatus, isHealthy } from '../../lib/lab'
  import type { Hypothesis } from '../../lib/types.gen'

  type Value = number | boolean | string

  interface Props {
    id: string
    hypothesis: Hypothesis
    value: Value
    onchange: (value: Value) => void
    /** Contrôle grisé (disabled_when), avec sa phrase d'explication. */
    disabledText?: string | null
  }

  let { id, hypothesis: h, value, onchange, disabledText = null }: Props = $props()

  const range = $derived(h.range ?? [0, 1])
  const step = $derived(h.step ?? 0.05)
  const healthy = $derived(isHealthy(h, value))
  const disabled = $derived(disabledText !== null)
</script>

<div class="control" class:broken={!healthy}>
  {#if h.type === 'continuous'}
    <div class="row">
      <input
        id="h-{id}"
        type="range"
        min={range[0]}
        max={range[1]}
        {step}
        value={value as number}
        {disabled}
        aria-label={h.label}
        oninput={(e) => onchange(Number(e.currentTarget.value))}
      />
      <output for="h-{id}" class="value">h = {formatControl(value as number, step)}</output>
    </div>
  {:else if h.type === 'boolean'}
    <div class="row">
      <button
        type="button"
        role="switch"
        class="switch"
        aria-checked={healthy}
        aria-label="{h.label} : {healthy ? 'respectée' : 'relâchée'}"
        title={healthy ? 'Cliquez pour relâcher cette hypothèse' : 'Cliquez pour la rétablir'}
        {disabled}
        onclick={() => onchange(healthy ? !h.healthy_value : h.healthy_value)}
      >
        <span class="knob" aria-hidden="true"></span>
      </button>
      <span class="state">{hypothesisStatus(h, value)}</span>
    </div>
  {:else}
    <select
      id="h-{id}"
      aria-label={h.label}
      value={value as string}
      {disabled}
      onchange={(e) => onchange(e.currentTarget.value)}
    >
      {#each Object.entries(h.options ?? {}) as [key, opt] (key)}
        <option value={key}>{opt.label}{key === h.healthy_value ? ' (saine)' : ''}</option>
      {/each}
    </select>
  {/if}
  {#if disabledText}
    <p class="disabled-text">{disabledText}</p>
  {/if}
</div>

<style>
  .control {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-1);
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--ct-space-3);
  }
  input[type='range'] {
    flex: 1;
    min-width: 4rem;
    margin: 0;
    accent-color: var(--ct-role-method);
  }
  .broken input[type='range'] {
    accent-color: var(--ct-role-rupture);
  }
  .value {
    flex: none;
    min-width: 4.2rem;
    font-family: var(--ct-font-mono);
    font-size: 0.8rem;
    color: var(--ct-muted);
    text-align: right;
  }
  .broken .value {
    color: var(--ct-role-rupture);
  }

  /* --- Interrupteur : allumé (vert, à droite) = respectée ; éteint (rouge, à gauche) = relâchée --- */
  .switch {
    position: relative;
    flex: none;
    width: 2.4rem;
    height: 1.35rem;
    padding: 0;
    border: none;
    border-radius: 999px;
    background: color-mix(in srgb, var(--ct-verdict-ok) 55%, var(--ct-surface-2));
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .switch[aria-checked='false'] {
    background: color-mix(in srgb, var(--ct-role-rupture) 60%, var(--ct-surface-2));
  }
  .knob {
    position: absolute;
    top: 0.175rem;
    left: 1.225rem;
    width: 1rem;
    height: 1rem;
    border-radius: 50%;
    background: var(--ct-text);
    transition: left 0.15s ease;
  }
  .switch[aria-checked='false'] .knob {
    left: 0.175rem;
  }
  .switch:focus-visible {
    outline: 2px solid var(--ct-focus);
    outline-offset: 2px;
  }
  .state {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    line-height: 1.3;
  }
  .broken .state {
    color: var(--ct-role-rupture);
  }

  select {
    width: 100%;
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-2);
    cursor: pointer;
  }
  .broken select {
    border-color: color-mix(in srgb, var(--ct-role-rupture) 60%, var(--ct-border));
  }
  button:disabled,
  select:disabled,
  input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .disabled-text {
    margin: 0;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
    font-style: italic;
  }
</style>
