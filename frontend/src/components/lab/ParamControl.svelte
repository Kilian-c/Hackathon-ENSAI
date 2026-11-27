<!--
  ParamControl.svelte : le contrôle d'un paramètre (nombre : curseur ; booléen : case à cocher) (R3).
-->
<script lang="ts">
  import { formatControl } from '../../lib/format'
  import type { Param } from '../../lib/types.gen'

  interface Props {
    id: string
    param: Param
    value: number | boolean
    onchange: (value: number | boolean) => void
  }

  let { id, param: p, value, onchange }: Props = $props()
</script>

<div class="param">
  {#if p.type === 'boolean'}
    <label class="check">
      <input type="checkbox" checked={value as boolean} onchange={(e) => onchange(e.currentTarget.checked)} />
      {p.label}
    </label>
  {:else}
    <label for="p-{id}">{p.label}</label>
    <div class="row">
      <input
        id="p-{id}"
        type="range"
        min={p.min ?? 0}
        max={p.max ?? 1}
        step={p.step ?? 'any'}
        value={value as number}
        oninput={(e) => onchange(Number(e.currentTarget.value))}
      />
      <output for="p-{id}" class="value">{formatControl(value as number, p.step)}</output>
    </div>
  {/if}
</div>

<style>
  .param {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-1);
    font-size: var(--ct-text-sm);
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
  }
  input[type='range'] {
    flex: 1;
    min-width: 0;
    accent-color: var(--ct-role-method);
  }
  .value {
    min-width: 3.5rem;
    font-family: var(--ct-font-mono);
    text-align: right;
  }
  .check {
    display: flex;
    gap: var(--ct-space-2);
    align-items: center;
  }
</style>
