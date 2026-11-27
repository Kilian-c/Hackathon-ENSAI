<!--
  MethodBench.svelte : le banc de méthodes (R3, P1). Cahier, annexe F, fiche « Banc de méthodes ».

  Un interrupteur par méthode autre que la principale : la Correction (losange vert), puis les
  alternatives (triangle, carré) dans l'ordre du YAML. Afficher ou masquer une méthode ne fait aucun
  appel : toutes les méthodes sont déjà dans RunResult. Sous les interrupteurs, l'explication de
  chaque méthode affichée. Sans correction ni alternative, rien ne s'affiche.
-->
<script lang="ts">
  import { roleColorVar, type DisplayRole } from '../../lib/roles'
  import type { MethodInfo } from '../../lib/types.gen'

  type MethodSpec = Pick<MethodInfo, 'id' | 'label' | 'role' | 'explain'>

  interface Props {
    methods: readonly MethodSpec[]
    roles: Readonly<Record<string, DisplayRole>>
    methodsOn: readonly string[]
    ontoggle: (id: string) => void
  }

  let { methods, roles, methodsOn, ontoggle }: Props = $props()

  /** Marqueur de chaque rôle (annexe E) : la couleur n'est jamais le seul indice. */
  const GLYPH: Partial<Record<DisplayRole, string>> = {
    correction: '◆',
    alternative_1: '▲',
    alternative_2: '■',
  }

  const others = $derived(methods.filter((m) => m.role !== 'method'))
  const shown = $derived(others.filter((m) => methodsOn.includes(m.id) && m.explain))

  function roleOf(m: MethodSpec): DisplayRole {
    return roles[m.id] ?? (m.role === 'correction' ? 'correction' : 'alternative_1')
  }

  function prefix(m: MethodSpec): string {
    return m.role === 'correction' ? 'Correction' : 'Alternative'
  }
</script>

{#if others.length > 0}
  <div class="wrap">
    <div class="bench" role="group" aria-label="Méthodes affichées">
      {#each others as m (m.id)}
        {@const role = roleOf(m)}
        {@const on = methodsOn.includes(m.id)}
        <button
          type="button"
          class="toggle"
          aria-pressed={on}
          style:--role-color={roleColorVar(role)}
          title={on ? 'Masquer cette méthode' : 'Afficher cette méthode à côté de la méthode principale'}
          onclick={() => ontoggle(m.id)}
        >
          <span aria-hidden="true">{GLYPH[role] ?? '●'}</span>
          {prefix(m)} : {m.label}
        </button>
      {/each}
    </div>
    {#each shown as m (m.id)}
      <p class="explain" style:--role-color={roleColorVar(roleOf(m))}>
        <strong>{m.label}.</strong>
        {m.explain}
      </p>
    {/each}
  </div>
{/if}

<style>
  .wrap {
    display: grid;
    gap: var(--ct-space-2);
  }
  .bench {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  .toggle {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-3);
    cursor: pointer;
  }
  .toggle:hover {
    border-color: var(--ct-muted);
  }
  .toggle span {
    color: var(--role-color);
  }
  .toggle[aria-pressed='true'] {
    border-color: var(--role-color);
    color: var(--role-color);
    font-weight: 600;
  }
  .explain {
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    border-left: 3px solid var(--role-color);
    padding-left: var(--ct-space-3);
  }
</style>
