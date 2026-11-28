<!--
  UnderstandStage.svelte : l'étape « Comprendre » du Laboratoire (R3). Cahier, sections 2.2 et 2.5.
  Une page de lecture : le théorème et son équation ; chaque hypothèse sur une ligne pleine largeur
  (nom, formule, bouton), puis deux blocs côte à côte : à quoi elle sert / ce que l'on voit quand elle
  tombe ; enfin les cas limites en liste compacte. Un bouton casse l'hypothèse (ou charge le cas
  limite) et passe à l'étape « Expérimenter ».
-->
<script lang="ts">
  import DynamicEquation from '../DynamicEquation.svelte'
  import MathText from '../MathText.svelte'
  import Tex from '../Tex.svelte'
  import { disabledNotice } from '../../lib/disabled'
  import { isHealthy } from '../../lib/lab'
  import type { Counterexample, EngineState, ExperimentSpec, RunResult } from '../../lib/types.gen'

  interface Props {
    spec: ExperimentSpec
    engine: EngineState
    result: RunResult | null
    methodsOn: readonly string[]
    /** Hypothèse à mettre en avant (lien reçu de l'Entraînement). */
    focus: string | null
    /** Casser l'hypothèse et passer à l'expérience. */
    ontry: (id: string) => void
    /** Charger un cas limite et passer à l'expérience. */
    onpreset: (c: Counterexample) => void
    /** Passer à l'expérience sans rien changer. */
    onstart: () => void
  }

  let { spec, engine, result, methodsOn, focus, ontry, onpreset, onstart }: Props = $props()

  const hypotheses = $derived(Object.entries(spec.hypotheses))
</script>

<div class="understand">
  <section class="theorem">
    <p class="kicker">Le théorème</p>
    <h2>{spec.theorem.name}</h2>
    <p class="statement"><MathText text={spec.theorem.statement} /></p>
    {#if result}
      <div class="equation">
        <DynamicEquation equation={spec.equation} {result} hypotheses={spec.hypotheses} {methodsOn} />
      </div>
    {/if}
  </section>

  <section aria-labelledby="hyp-titre">
    <h3 id="hyp-titre" class="section-title">
      {hypotheses.length > 1 ? `Ses ${hypotheses.length} hypothèses` : 'Son hypothèse'}
    </h3>
    <ol class="hyps">
      {#each hypotheses as [id, h], k (id)}
        {@const healthy = isHealthy(h, engine.hypotheses[id])}
        {@const locked = disabledNotice(h, { hypotheses: engine.hypotheses, params: engine.params })}
        <li class="hyp" class:focus={focus === id} class:broken={!healthy}>
          <div class="hyp-head">
            <span class="num" aria-hidden="true">{k + 1}</span>
            <div class="hyp-title">
              <strong>{h.label}</strong>
              <div class="formula"><Tex tex={h.statement_tex} /></div>
            </div>
            {#if !healthy}<span class="state">✕ Cassée</span>{/if}
            {#if locked === null}
              <button type="button" class="try" onclick={() => ontry(id)}>
                {healthy ? 'Casser cette hypothèse' : "Voir l'effet"} →
              </button>
            {:else}
              <span class="locked" title={locked.replace(/\$/g, '')}>🔒 Non cassable ici</span>
            {/if}
          </div>
          {#if locked !== null}
            <p class="locked-note"><MathText text={locked} /></p>
          {/if}
          <div class="sides">
            <div class="side ok">
              <p class="side-title"><span aria-hidden="true">✓</span> À quoi elle sert</p>
              <p><MathText text={h.why} /></p>
            </div>
            <div class="side ko">
              <p class="side-title"><span aria-hidden="true">✕</span> Ce que l'on voit quand elle tombe</p>
              <p><MathText text={h.when_broken} /></p>
            </div>
          </div>
        </li>
      {/each}
    </ol>
  </section>

  {#if spec.counterexamples.length > 0}
    <section aria-labelledby="cas-titre">
      <h3 id="cas-titre" class="section-title">Cas limites</h3>
      <p class="intro">Des situations toutes prêtes, qui règlent tous les contrôles d'un coup.</p>
      <ul class="cases">
        {#each spec.counterexamples as c (c.id)}
          <li>
            <div>
              <strong>{c.label}</strong>
              <p><MathText text={c.explain} /></p>
            </div>
            <button type="button" class="try" onclick={() => onpreset(c)}>Essayer →</button>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <div class="next">
    <button type="button" class="primary" onclick={onstart}>Passer à l'expérience →</button>
  </div>
</div>

<style>
  .understand {
    max-width: 60rem;
    margin: 0 auto;
    display: grid;
    gap: var(--ct-space-8);
  }

  /* --- Théorème --- */
  .theorem {
    padding: var(--ct-space-6) var(--ct-space-8);
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    background:
      linear-gradient(160deg, color-mix(in srgb, var(--ct-role-method) 9%, transparent), transparent 60%),
      var(--ct-surface);
  }
  .kicker,
  .section-title {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ct-muted);
  }
  .kicker {
    color: var(--ct-role-method);
  }
  .section-title {
    margin-bottom: var(--ct-space-3);
  }
  h2 {
    margin: var(--ct-space-1) 0 var(--ct-space-2);
    font-size: var(--ct-text-xl);
  }
  .statement {
    margin: 0;
    font-size: 1.05rem;
  }
  .equation {
    margin-top: var(--ct-space-4);
    padding-top: var(--ct-space-4);
    border-top: 1px solid var(--ct-border);
  }

  /* --- Hypothèses : une ligne pleine largeur chacune --- */
  .hyps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-4);
  }
  .hyp {
    display: grid;
    gap: var(--ct-space-4);
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-6);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: var(--ct-surface);
  }
  .hyp.focus {
    border-color: var(--ct-role-method);
  }
  .hyp-head {
    display: flex;
    align-items: center;
    gap: var(--ct-space-4);
    flex-wrap: wrap;
  }
  .num {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    flex: none;
    border-radius: 50%;
    background: color-mix(in srgb, var(--ct-verdict-ok) 18%, transparent);
    color: var(--ct-verdict-ok);
    font-weight: 700;
  }
  .broken .num {
    background: color-mix(in srgb, var(--ct-role-rupture) 18%, transparent);
    color: var(--ct-role-rupture);
  }
  .hyp-title {
    flex: 1;
    min-width: 14rem;
    display: flex;
    align-items: baseline;
    gap: var(--ct-space-2) var(--ct-space-4);
    flex-wrap: wrap;
  }
  .hyp-title strong {
    font-size: 1.05rem;
  }
  .formula {
    overflow-x: auto;
    overflow-y: hidden;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .state {
    font-size: var(--ct-text-sm);
    color: var(--ct-role-rupture);
  }
  .sides {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
    gap: var(--ct-space-3);
  }
  .side {
    padding: var(--ct-space-3) var(--ct-space-4);
    border-radius: var(--ct-radius);
    background: var(--ct-bg);
    border-top: 2px solid var(--c);
  }
  .side.ok {
    --c: var(--ct-verdict-ok);
  }
  .side.ko {
    --c: var(--ct-role-rupture);
  }
  .side p {
    margin: 0;
    font-size: var(--ct-text-sm);
    line-height: 1.55;
    color: var(--ct-muted);
  }
  .side .side-title {
    margin-bottom: var(--ct-space-1);
    font-weight: 600;
    color: var(--ct-text);
  }
  .side-title span {
    color: var(--c);
    margin-right: var(--ct-space-1);
  }

  /* --- Cas limites : liste compacte --- */
  .intro {
    margin: calc(-1 * var(--ct-space-2)) 0 var(--ct-space-3);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .cases {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: var(--ct-surface);
  }
  .cases li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--ct-space-6);
    padding: var(--ct-space-3) var(--ct-space-6);
    border-left: 3px solid var(--ct-role-truth);
  }
  .cases li + li {
    border-top: 1px solid var(--ct-border);
  }
  .cases li:first-child {
    border-top-left-radius: var(--ct-radius-lg);
  }
  .cases li:last-child {
    border-bottom-left-radius: var(--ct-radius-lg);
  }
  .cases p {
    margin: var(--ct-space-1) 0 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }

  /* --- Boutons --- */
  button {
    font: inherit;
    cursor: pointer;
  }
  .try {
    flex: none;
    padding: 0.35rem 0.85rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface-2);
    color: var(--ct-text);
    font-size: var(--ct-text-sm);
    font-weight: 600;
  }
  .try:hover {
    border-color: var(--ct-role-method);
    color: var(--ct-role-method);
  }
  .next {
    display: flex;
    justify-content: center;
  }
  .primary {
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: var(--ct-radius);
    background: var(--ct-role-method);
    color: var(--ct-bg);
    font-weight: 600;
  }
  .primary:hover {
    background: color-mix(in srgb, var(--ct-role-method) 85%, var(--ct-text));
  }
  .locked {
    flex: none;
    padding: 0.2rem 0.7rem;
    border: 1px dashed var(--ct-border);
    border-radius: 999px;
    color: var(--ct-muted);
    font-size: 0.8rem;
  }
  .locked-note {
    margin: var(--ct-space-2) 0 0;
    font-size: 0.85rem;
    color: var(--ct-muted);
  }
</style>
