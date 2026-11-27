<!--
  ResultPanel.svelte : le haut de l'étape « Expérimenter » (R3). Remplace MeasureStrip et MethodBench.

  Deux colonnes :
  - Résultat : la mesure principale, une ligne par méthode affichée (valeur ± 2 mc_se, verdict, jauge
    Fiable / Fragile / Rompu), la cible et la Référence ;
  - Que se passe-t-il ? : la phrase de lib/guide.ts, les hypothèses relâchées (when_broken) et l'étape
    suivante, avec le bouton Correction (banc de méthodes : alternatives en plus petit).
  Afficher ou masquer une méthode ne fait aucun appel : tout est déjà dans RunResult.
-->
<script lang="ts">
  import MeasureGauge from './MeasureGauge.svelte'
  import VerdictBadge from './VerdictBadge.svelte'
  import { formatMargin, formatMeasure } from '../../lib/format'
  import { gauge, gaugeDomain, labGuide, targetFor } from '../../lib/guide'
  import { primaryMeasureId } from '../../lib/lab'
  import { displayRoles, roleColorVar, verdictColorVar, verdictIcon, verdictLabel, type DisplayRole } from '../../lib/roles'
  import type { EngineState, ExperimentSpec, RunResult } from '../../lib/types.gen'

  interface Props {
    spec: ExperimentSpec
    engine: EngineState
    result: RunResult
    methodsOn: readonly string[]
    showReference: boolean
    ontoggle: (methodId: string) => void
    onheal: () => void
    /** Ouvrir l'explication complète d'une hypothèse (étape Comprendre). */
    onexplain: (hypothesisId: string) => void
  }

  let { spec, engine, result, methodsOn, showReference, ontoggle, onheal, onexplain }: Props = $props()

  /** Marqueur de chaque rôle (annexe E) : la couleur n'est jamais le seul indice. */
  const GLYPH: Partial<Record<DisplayRole, string>> = {
    method: '●',
    correction: '◆',
    alternative_1: '▲',
    alternative_2: '■',
  }

  const id = $derived(primaryMeasureId(result))
  const m = $derived(id ? result.measures[id] : null)
  const roles = $derived(displayRoles(result.methods))
  const principal = $derived(result.methods.find((x) => x.role === 'method') ?? null)
  const shown = $derived(result.methods.filter((x) => methodsOn.includes(x.id)))
  const domain = $derived(m ? gaugeDomain(m, shown.map((x) => x.id)) : null)
  const guide = $derived(labGuide(spec, engine, result, methodsOn))

  const correction = $derived(result.methods.find((x) => x.role === 'correction') ?? null)
  const alternatives = $derived(result.methods.filter((x) => x.role === 'alternative'))
  const explained = $derived(shown.filter((x) => x.role !== 'method' && x.explain))
  const principalTarget = $derived(m && principal ? targetFor(m, principal.id) : null)

  function glyph(methodId: string): string {
    return GLYPH[roles[methodId]] ?? '●'
  }
</script>

<section class="result" aria-label="Résultat">
  {#if m}
    <div class="measure">
      <p class="kicker">{m.label}</p>
      <ul class="rows">
        {#each shown as method, k (method.id)}
          {@const verdict = m.states[method.id]}
          {@const margin = formatMargin(m.mc_se[method.id], m)}
          {@const g = domain ? gauge(m, method.id, domain) : null}
          {@const color = roleColorVar(roles[method.id])}
          <li>
            <span class="who" style:color>
              <span aria-hidden="true">{glyph(method.id)}</span>
              {method.label}
            </span>
            <span class="val">
              {formatMeasure(m.values[method.id], m)}
              {#if margin}<span class="margin">{margin}</span>{/if}
            </span>
            {#if verdict}<VerdictBadge {verdict} />{/if}
            {#if g}
              <div class="full">
                <MeasureGauge
                  gauge={g}
                  {color}
                  {showReference}
                  labels={k === 0}
                  description="{method.label} : {formatMeasure(m.values[method.id], m)}{verdict ? `, ${verdictLabel(verdict)}` : ''}"
                />
              </div>
            {/if}
            {#if method.role === 'method' && m.texts[method.id]}
              <p class="full text">{m.texts[method.id]}</p>
            {/if}
          </li>
        {/each}
      </ul>
      <p class="legend">
        {#if principalTarget !== null && m.target !== 'base'}
          <span><span class="tick" aria-hidden="true"></span> Cible : {formatMeasure(principalTarget, m)}</span>
        {/if}
        {#if showReference && principal && m.baseline[principal.id] != null}
          <span><span class="ring" aria-hidden="true"></span> Référence (état sain) : {formatMeasure(m.baseline[principal.id], m)}{m.target === 'base' ? ', la cible' : ''}</span>
        {/if}
      </p>
    </div>
  {/if}

  <div class="guide" style:--tone={guide.tone ? verdictColorVar(guide.tone) : 'var(--ct-border)'}>
    <p class="kicker">Que se passe-t-il ?</p>
    <p class="headline">
      {#if guide.tone}<span class="icon" aria-hidden="true">{verdictIcon(guide.tone)}</span>{/if}
      {guide.headline}
    </p>
    {#each guide.causes as c (c.id)}
      <p class="cause">
        <strong>{c.label}</strong> : {c.text}
        <button type="button" class="link" onclick={() => onexplain(c.id)}>En savoir plus</button>
      </p>
    {/each}
    {#if guide.moreCauses > 0}
      <p class="cause">Et {guide.moreCauses} autre{guide.moreCauses > 1 ? 's' : ''} hypothèse{guide.moreCauses > 1 ? 's' : ''} relâchée{guide.moreCauses > 1 ? 's' : ''}.</p>
    {/if}
    {#if guide.context}<p class="cause">{guide.context}</p>{/if}
    {#if guide.next}<p class="next"><span aria-hidden="true">→</span> {guide.next}</p>{/if}

    {#if correction || alternatives.length > 0 || guide.action === 'heal'}
      <div class="actions">
        {#if correction}
          {@const on = methodsOn.includes(correction.id)}
          <button
            type="button"
            class="correction"
            class:suggested={guide.action === 'correction'}
            aria-pressed={on}
            onclick={() => ontoggle(correction.id)}
          >
            <span aria-hidden="true">◆</span>
            {on ? 'Masquer la correction' : 'Afficher la correction'}
          </button>
        {/if}
        {#if guide.action === 'heal'}
          <button type="button" class="secondary" onclick={onheal}>Tout rétablir</button>
        {/if}
        {#if alternatives.length > 0}
          <span class="alts">
            <span class="alt-title">Comparer aussi :</span>
            {#each alternatives as alt (alt.id)}
              <button
                type="button"
                class="alt"
                aria-pressed={methodsOn.includes(alt.id)}
                style:--role-color={roleColorVar(roles[alt.id])}
                onclick={() => ontoggle(alt.id)}
              >
                <span aria-hidden="true">{glyph(alt.id)}</span>
                {alt.label}
              </button>
            {/each}
          </span>
        {/if}
      </div>
    {/if}
    {#each explained as x (x.id)}
      <p class="explain" style:--role-color={roleColorVar(roles[x.id])}>
        <strong>{x.label}.</strong>
        {x.explain}
      </p>
    {/each}
  </div>
</section>

<style>
  .result {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
    gap: var(--ct-space-4) var(--ct-space-8);
    padding: var(--ct-space-4) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  @media (max-width: 72rem) {
    .result {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  .kicker {
    margin: 0 0 var(--ct-space-2);
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-muted);
  }

  /* --- Résultat --- */
  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-3);
  }
  .rows li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 0 var(--ct-space-3);
  }
  .who {
    font-size: var(--ct-text-sm);
    font-weight: 600;
    min-width: 0;
  }
  .val {
    font-family: var(--ct-font-mono);
    font-size: 1.5rem;
    line-height: 1.1;
    white-space: nowrap;
  }
  .margin {
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
  .full {
    grid-column: 1 / -1;
  }
  .text {
    margin: var(--ct-space-1) 0 0;
    font-size: var(--ct-text-sm);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-1) var(--ct-space-4);
    margin: var(--ct-space-2) 0 0;
    font-size: 0.8rem;
    color: var(--ct-muted);
  }
  .legend > span {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-1);
  }
  .tick {
    display: inline-block;
    width: 2px;
    height: 0.8rem;
    background: var(--ct-text);
    opacity: 0.75;
  }
  .ring {
    display: inline-block;
    width: 0.6rem;
    height: 0.6rem;
    border: 2px solid var(--ct-role-reference);
    border-radius: 50%;
  }

  /* --- Que se passe-t-il ? --- */
  .guide {
    display: grid;
    align-content: start;
    gap: var(--ct-space-2);
    padding-left: var(--ct-space-6);
    border-left: 3px solid var(--tone);
  }
  @media (max-width: 72rem) {
    .guide {
      padding: var(--ct-space-4) 0 0;
      border-left: none;
      border-top: 3px solid var(--tone);
    }
  }
  .guide p {
    margin: 0;
  }
  .guide .kicker {
    margin: 0;
  }
  .headline {
    font-weight: 600;
    font-size: var(--ct-text-md);
  }
  .icon {
    color: var(--tone);
    margin-right: var(--ct-space-1);
  }
  .cause {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    line-height: 1.5;
  }
  .cause strong {
    color: var(--ct-text);
    font-weight: 600;
  }
  .next {
    font-size: var(--ct-text-sm);
    line-height: 1.5;
  }
  .next span {
    color: var(--tone);
    font-weight: 700;
  }

  /* --- Boutons --- */
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-2);
    margin-top: var(--ct-space-1);
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    cursor: pointer;
  }
  .correction {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
    padding: 0.45rem 1rem;
    border: 1px solid var(--ct-role-correction);
    border-radius: var(--ct-radius);
    background: transparent;
    color: var(--ct-role-correction);
    font-weight: 600;
  }
  .correction.suggested,
  .correction:hover {
    background: var(--ct-role-correction);
    color: var(--ct-bg);
  }
  .correction[aria-pressed='true'] {
    background: color-mix(in srgb, var(--ct-role-correction) 15%, transparent);
    color: var(--ct-role-correction);
  }
  .secondary {
    padding: 0.45rem 1rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface-2);
    color: var(--ct-text);
  }
  .alts {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-2);
  }
  .alt-title {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    margin-left: var(--ct-space-2);
  }
  .alt {
    padding: var(--ct-space-1) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface-2);
    color: var(--ct-text);
  }
  .alt span {
    color: var(--role-color);
  }
  .alt[aria-pressed='true'] {
    border-color: var(--role-color);
    color: var(--role-color);
    font-weight: 600;
  }
  .explain {
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    border-left: 3px solid var(--role-color);
    padding-left: var(--ct-space-3);
  }
  .link {
    padding: 0;
    border: none;
    background: none;
    color: var(--ct-role-method);
    white-space: nowrap;
  }
  .link:hover {
    text-decoration: underline;
  }
</style>
