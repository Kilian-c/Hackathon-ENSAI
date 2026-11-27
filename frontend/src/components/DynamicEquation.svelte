<!--
  DynamicEquation.svelte : l'équation clé de l'expérience, à termes nommés (R3).
  Cahier, section 3.2 ; règle de couleur dans lib/equation.ts (testée).

  Aucun appel au moteur : tout vient du YAML (spec.equation), de RunResult (violated_by, verdicts de la
  mesure primaire) et de l'état d'affichage (methodsOn). Un terme rouge est aussi souligné, et la
  légende dit en mots ce qui se passe : la couleur n'est jamais le seul indice.

  Usage :
    <DynamicEquation equation={spec.equation} {result} hypotheses={spec.hypotheses} methodsOn={ui.methodsOn} />
-->
<script lang="ts">
  import Tex from './Tex.svelte'
  import { buildEquationTex, equationTerms, type TermDisplay } from '../lib/equation'
  import { primaryStates } from '../lib/lab'
  import type { Equation, Hypothesis, RunResult } from '../lib/types.gen'

  interface Props {
    equation: Equation
    result: Pick<RunResult, 'equation' | 'methods' | 'measures'>
    hypotheses: Readonly<Record<string, Pick<Hypothesis, 'label'>>>
    methodsOn: readonly string[]
  }

  let { equation, result, hypotheses, methodsOn }: Props = $props()

  const displays = $derived(
    equationTerms(equation, result.equation, {
      methods: result.methods,
      primaryStates: primaryStates(result),
      methodsOn,
    }),
  )
  const tex = $derived(buildEquationTex(equation, displays))

  const correction = $derived(result.methods.find((m) => m.role === 'correction') ?? null)

  function names(d: TermDisplay): string {
    return d.violatedBy.map((id) => `« ${hypotheses[id]?.label ?? id} »`).join(', ')
  }

  /** Une phrase par terme en cause, en clair. */
  const notes = $derived(
    displays
      .filter((d) => d.tone !== 'neutral')
      .map((d) => ({
        tone: d.tone,
        text:
          d.tone === 'repaired'
            ? `Terme corrigé par ${correction?.label ?? 'la Correction'} : l'écart se referme malgré ${names(d)}.`
            : d.corrected
              ? `Terme corrigé, mais la Correction ne suffit pas encore : ${names(d)}.`
              : `Ce terme n'est plus valable : hypothèse relâchée, ${names(d)}.`,
      })),
  )
</script>

<div class="equation" aria-live="polite">
  <Tex {tex} display />
  {#if notes.length > 0}
    <ul class="notes">
      {#each notes as note, i (i)}
        <li class={note.tone}>
          <span aria-hidden="true">{note.tone === 'repaired' ? '✓' : '✕'}</span>
          {note.text}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .equation {
    padding: var(--ct-space-3) var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    font-size: var(--ct-text-lg);
  }
  .notes {
    list-style: none;
    margin: var(--ct-space-2) 0 0;
    padding: 0;
    font-size: var(--ct-text-sm);
  }
  .notes li {
    display: flex;
    gap: var(--ct-space-2);
  }
  .broken {
    color: var(--ct-role-rupture);
  }
  .repaired {
    color: var(--ct-role-correction);
  }
</style>
