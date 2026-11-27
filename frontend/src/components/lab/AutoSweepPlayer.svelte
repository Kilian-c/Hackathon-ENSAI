<!--
  AutoSweepPlayer.svelte : le balayage automatique (R3, P1). Cahier, annexe F, fiche
  « Balayage automatique » ; règles pures dans lib/autoSweep.ts.

  Un bouton Lecture par contrôle de `auto_sweep`. Au clic : /api/sweep (grille et seuil critique),
  puis un /api/run par valeur, préchargés avant le départ (barre de progression), joués à 600 ms par
  image, avec une pause de 2 s au seuil critique. Le moindre clic ou la moindre touche arrête
  l'animation et garde l'état affiché. À la fin : la Correction s'active (hypothèse) ou une phrase
  conclut (paramètre).
-->
<script lang="ts">
  import { onDestroy } from 'svelte'
  import { animatable, conclusion, endUi, frameStates, FRAME_MS, PAUSE_MS, pauseIndex } from '../../lib/autoSweep'
  import { axisTitle, headlineVerdict, methodWithRole, sweepRequest } from '../../lib/lab'
  import type { LabSource } from '../../lib/labSource'
  import type { UiState } from '../../lib/state'
  import type { EngineState, ExperimentSpec, RunResult } from '../../lib/types.gen'

  interface Props {
    spec: ExperimentSpec
    engine: EngineState
    ui: UiState
    source: LabSource
    /** Une image : l'état de calcul et son résultat déjà calculé. `first` : première image. */
    onframe: (state: EngineState, result: RunResult, first: boolean) => void
    /** Fin de l'animation (ui : état d'affichage final, Correction activée pour une hypothèse). */
    onfinish: (ui: UiState) => void
    /** L'animation démarre (target) ou s'arrête (null). */
    onplaying: (target: string | null) => void
  }

  let { spec, engine, ui, source, onframe, onfinish, onplaying }: Props = $props()

  const targets = $derived(animatable(spec))
  const principal = $derived(methodWithRole(spec.methods, 'method')?.id ?? null)

  let phase = $state<'idle' | 'loading' | 'playing' | 'paused'>('idle')
  let current = $state<string | null>(null)
  let progress = $state(0)
  let message = $state<string | null>(null)

  let abort: AbortController | null = null
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer(): void {
    if (timer) clearTimeout(timer)
    timer = null
  }

  function listen(on: boolean): void {
    const f = on ? window.addEventListener : window.removeEventListener
    f('pointerdown', interrupt, { capture: true })
    f('keydown', interrupt, { capture: true })
  }

  /** Arrêt : l'état affiché est gardé tel quel. */
  function stop(): void {
    abort?.abort()
    abort = null
    clearTimer()
    listen(false)
    if (phase !== 'idle') onplaying(null)
    phase = 'idle'
    current = null
  }

  let root: HTMLElement | undefined = $state()

  /** Geste de l'étudiant hors du lecteur (ses propres boutons arrêtent ou relancent eux-mêmes). */
  function interrupt(e: Event): void {
    if (root && e.target instanceof Node && root.contains(e.target)) return
    if (phase !== 'idle') stop()
  }

  onDestroy(stop)

  async function play(target: string): Promise<void> {
    stop()
    message = null
    current = target
    phase = 'loading'
    progress = 0
    onplaying(target)
    const ctl = new AbortController()
    abort = ctl
    // Écoute ajoutée après le clic qui lance : seul un geste suivant arrête l'animation.
    setTimeout(() => {
      if (abort === ctl) listen(true)
    }, 0)
    try {
      const sweep = await source.sweep(sweepRequest(spec, engine, [target], null), { signal: ctl.signal })
      if (!sweep) {
        message = "Ce balayage n'est pas disponible."
        stop()
        return
      }
      const states = frameStates(spec, engine, target, sweep)
      const results: RunResult[] = []
      for (const s of states) {
        results.push(await source.run(spec, s, { signal: ctl.signal }))
        if (abort !== ctl) return
        progress = results.length / states.length
      }
      const pause = pauseIndex(sweep, principal)
      const labels = sweep.axes[0]?.labels ?? []
      phase = 'playing'
      const step = (i: number): void => {
        if (abort !== ctl) return
        onframe(states[i], results[i], i === 0)
        if (i === states.length - 1) {
          const first = headlineVerdict(results[0])
          const last = headlineVerdict(results[i])
          message = conclusion(spec, target, labels, first, last)
          const finalUi = endUi(spec, ui, target)
          if (finalUi !== ui) {
            const corr = methodWithRole(spec.methods, 'correction')
            message = corr ? `Correction activée : ${corr.label}.` : null
          }
          stop()
          onfinish(finalUi)
          return
        }
        const wait = i === pause ? PAUSE_MS : FRAME_MS
        phase = i === pause ? 'paused' : 'playing'
        timer = setTimeout(() => step(i + 1), wait)
      }
      step(0)
    } catch {
      if (abort === ctl) {
        message = "Le balayage automatique a échoué. Réessayez dans un instant."
        stop()
      }
    }
  }
</script>

{#if targets.length > 0}
  <section class="player" aria-labelledby="balayage-titre" bind:this={root}>
    <h3 id="balayage-titre">Balayage automatique</h3>
    <div class="buttons">
      {#each targets as t (t)}
        {@const active = current === t}
        <button
          type="button"
          aria-pressed={active}
          onclick={() => (active ? stop() : play(t))}
          title={active ? "Arrêter l'animation" : 'Faire varier ce contrôle de bout en bout'}
        >
          <span aria-hidden="true">{active ? '■' : '▶'}</span>
          {axisTitle(spec, t)}
        </button>
      {/each}
    </div>
    {#if phase === 'loading'}
      <div class="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
        <div class="bar" style:width="{progress * 100}%"></div>
      </div>
      <p class="hint">Préparation des images… Un clic ou une touche arrête l'animation.</p>
    {:else if phase === 'paused'}
      <p class="hint pause">Seuil critique : la méthode principale devient Fragile.</p>
    {:else if phase === 'playing'}
      <p class="hint">Un clic ou une touche arrête l'animation.</p>
    {/if}
    {#if message}<p class="message" aria-live="polite">{message}</p>{/if}
  </section>
{/if}

<style>
  .player {
    display: grid;
    gap: var(--ct-space-2);
  }
  h3 {
    margin: 0;
    font-size: var(--ct-text-md);
    color: var(--ct-muted);
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
  }
  button {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-3);
    cursor: pointer;
  }
  button:hover {
    border-color: var(--ct-muted);
  }
  button[aria-pressed='true'] {
    border-color: var(--ct-role-method);
    color: var(--ct-role-method);
    font-weight: 600;
  }
  .progress {
    height: 4px;
    background: var(--ct-surface-2);
    border-radius: 2px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    background: var(--ct-role-method);
    transition: width 120ms linear;
  }
  .hint,
  .message {
    margin: 0;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .hint.pause {
    color: var(--ct-verdict-warning);
    font-weight: 600;
  }
  .message {
    color: var(--ct-text);
  }
</style>
