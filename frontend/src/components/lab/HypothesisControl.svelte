<!--
  HypothesisControl.svelte : le contrôle d'une hypothèse, selon son type (R3).
  - continuous : curseur h dans range, avec raccourcis vers les deux bornes ;
  - boolean    : interrupteur Respectée / Relâchée (ok_label / broken_label) ;
  - choice     : sélecteur d'option (lois).
  Le composant ne garde aucun état : il reçoit la valeur et signale le changement (onchange).
-->
<script lang="ts">
  import { formatControl } from '../../lib/format'
  import { isHealthy } from '../../lib/lab'
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
      <button type="button" class="ghost" {disabled} onclick={() => onchange(range[0])} title="Aller à {formatControl(range[0], step)}">
        {formatControl(range[0], step)}
      </button>
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
      <button type="button" class="ghost" {disabled} onclick={() => onchange(range[1])} title="Aller à {formatControl(range[1], step)}">
        {formatControl(range[1], step)}
      </button>
      <output for="h-{id}" class="value">h = {formatControl(value as number, step)}</output>
    </div>
  {:else if h.type === 'boolean'}
    <div class="row toggle" role="group" aria-label={h.label}>
      <button type="button" aria-pressed={healthy} {disabled} onclick={() => onchange(h.healthy_value)}>
        {h.ok_label ?? 'Respectée'}
      </button>
      <button type="button" aria-pressed={!healthy} {disabled} onclick={() => onchange(!h.healthy_value)}>
        {h.broken_label ?? 'Relâchée'}
      </button>
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
    gap: var(--ct-space-1);
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
  }
  input[type='range'] {
    flex: 1;
    min-width: 6rem;
    accent-color: var(--ct-role-method);
  }
  .broken input[type='range'] {
    accent-color: var(--ct-role-rupture);
  }
  .value {
    min-width: 4.5rem;
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-sm);
    text-align: right;
  }
  button,
  select {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-2);
    cursor: pointer;
  }
  button:disabled,
  select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .ghost {
    background: transparent;
    font-family: var(--ct-font-mono);
  }
  .toggle button[aria-pressed='true'] {
    border-color: var(--ct-role-method);
    color: var(--ct-role-method);
    font-weight: 600;
  }
  .broken .toggle button[aria-pressed='true'] {
    border-color: var(--ct-role-rupture);
    color: var(--ct-role-rupture);
  }
  select {
    width: 100%;
  }
  .disabled-text {
    margin: 0;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
    font-style: italic;
  }
</style>
