<!--
  Inspector.svelte : la fiche d'une observation (cahier, fiche F.6). Posée sur le graphique, elle affiche
  ce que le moteur fournit (lib/inspect.ts) : une ligne absente de la méthode n'apparaît pas.
-->
<script lang="ts">
  import { frNumber } from '../../lib/format'
  import type { Inspection } from '../../lib/inspect'

  interface Props {
    inspection: Inspection
    /** L'observation est un point posé au clic : la fiche permet de le retirer. */
    posed: boolean
    onclose: () => void
    onremove: () => void
  }

  let { inspection, posed, onclose, onremove }: Props = $props()

  const num = (v: number | null) => (v === null ? '—' : frNumber(v, 3))
  const percent = (v: number) => `${frNumber(v * 100, 1)} %`

  function onkeydown(e: KeyboardEvent): void {
    if (e.key === 'Escape') onclose()
  }
</script>

<svelte:window {onkeydown} />

<aside class="inspector" aria-label="Fiche de l'observation">
  <header>
    <h3>{posed ? 'Votre point ajouté' : `Observation ${inspection.index + 1} sur ${inspection.total}`}</h3>
    <button type="button" class="close" onclick={onclose} aria-label="Fermer la fiche">✕</button>
  </header>

  <dl aria-live="polite">
    <div><dt>x</dt><dd>{num(inspection.x)}</dd></div>
    {#if inspection.y !== null}<div><dt>y</dt><dd>{num(inspection.y)}</dd></div>{/if}
    {#if inspection.fitted !== null}<div><dt>Prédiction ŷ</dt><dd>{num(inspection.fitted)}</dd></div>{/if}
    {#if inspection.resid !== null}<div><dt>Résidu y − ŷ</dt><dd>{num(inspection.resid)}</dd></div>{/if}
    {#if inspection.ssrShare !== null}
      <div><dt>Part dans la somme des carrés des résidus</dt><dd>{percent(inspection.ssrShare)}</dd></div>
    {/if}
    {#if inspection.leverage !== null}
      <div class:flagged={inspection.highLeverage}><dt>Levier</dt><dd>{num(inspection.leverage)}</dd></div>
    {/if}
    {#if inspection.cooks !== null}
      <div class:flagged={inspection.influential}><dt>Distance de Cook</dt><dd>{num(inspection.cooks)}</dd></div>
    {/if}
  </dl>

  <ul class="flags">
    {#if inspection.leverageLimit !== null}
      <li class:flagged={inspection.highLeverage}>
        {#if inspection.highLeverage}
          <strong>! Levier élevé</strong> : au-delà de {num(inspection.leverageLimit)} (2 fois le levier moyen).
          Sa position en x pèse beaucoup sur l'ajustement.
        {:else}
          Levier ordinaire (seuil : {num(inspection.leverageLimit)}).
        {/if}
      </li>
    {/if}
    {#if inspection.cooksLimit !== null && inspection.cooks !== null}
      <li class:flagged={inspection.influential}>
        {#if inspection.influential}
          <strong>! Point influent</strong> : distance de Cook au-delà de {num(inspection.cooksLimit)} (4 / n).
          Le retirer changerait nettement l'ajustement.
        {:else}
          Peu influent (seuil de Cook : {num(inspection.cooksLimit)}).
        {/if}
      </li>
    {/if}
  </ul>

  {#if posed}
    <button type="button" class="remove" onclick={onremove}>Retirer ce point</button>
  {/if}
</aside>

<style>
  /* Coin haut gauche du nuage : le moins chargé quand la pente est positive. La fiche se ferme au besoin. */
  .inspector {
    position: absolute;
    top: var(--ct-space-2);
    left: 4.5rem;
    z-index: 5;
    width: min(19rem, calc(100% - 5rem));
    max-height: calc(100% - var(--ct-space-4));
    overflow-y: auto;
    box-sizing: border-box;
    padding: var(--ct-space-3);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    box-shadow: var(--ct-shadow);
    font-size: var(--ct-text-sm);
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--ct-space-2);
  }
  h3 {
    margin: 0;
    font-size: var(--ct-text-md);
  }
  .close {
    padding: 0 var(--ct-space-1);
    border: none;
    background: none;
    color: var(--ct-muted);
    font: inherit;
    cursor: pointer;
  }
  .close:hover {
    color: var(--ct-text);
  }
  dl {
    margin: var(--ct-space-2) 0;
  }
  dl div {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--ct-space-3);
    padding: 1px 0;
    border-bottom: 1px solid var(--ct-border);
  }
  dt {
    color: var(--ct-muted);
  }
  dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  dl div.flagged dt,
  dl div.flagged dd {
    color: var(--ct-verdict-warning);
    font-weight: 600;
  }
  .flags {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-1);
    color: var(--ct-muted);
  }
  .flags li.flagged {
    color: var(--ct-text);
    padding-left: var(--ct-space-2);
    border-left: 3px solid var(--ct-verdict-warning);
  }
  .flags li.flagged strong {
    color: var(--ct-verdict-warning);
  }
  .remove {
    margin-top: var(--ct-space-3);
    padding: var(--ct-space-1) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface-2);
    color: var(--ct-text);
    font: inherit;
    cursor: pointer;
  }
  @media (max-width: 700px) {
    .inspector {
      position: static;
      width: auto;
      margin-top: var(--ct-space-2);
    }
  }
</style>
