<!--
  DevCharts.svelte : banc d'essai PROVISOIRE de PlotlyChart (R3), sur la fixture de dev/fakeViews.ts.
  À retirer quand le Laboratoire existe. Sert à vérifier à l'œil : axes fixes quand h bouge,
  points hors cadre, Correction et Référence qui s'affichent sans recalcul.
-->
<script lang="ts">
  import PlotlyChart from '../components/PlotlyChart.svelte'
  import { displayRoles } from '../lib/roles'
  import type { ViewResult } from '../lib/views'
  import { pendulumFixture, regressionFixture, regressionMethods, regressionSweep } from './fakeViews'

  let hetero = $state(0.8)
  let pas = $state(0.6)
  let seed = $state(42)
  let correction = $state(false)
  let showReference = $state(true)

  const regRoles = displayRoles(regressionMethods)
  const regLabels = Object.fromEntries(regressionMethods.map((m) => [m.id, m.label]))

  const regOn = $derived(new Set(correction ? ['ols', 'hc3'] : ['ols']))
  const penOn = $derived(new Set(correction ? ['euler', 'rk4'] : ['euler']))

  const reg = $derived(regressionFixture(hetero, seed))
  // Le balayage ne dépend pas de h (seul « l'état actuel » bouge) : recalculé seulement avec la graine.
  const sweepBase = $derived(regressionSweep(0, seed))
  const sweep = $derived({ ...sweepBase, current: { 'h.hetero': hetero } })
  const pen = $derived(pendulumFixture(pas))

  const sensView: ViewResult = {
    id: 'sens', type: 'sensitivity', title: 'Étude de sensibilité',
    axes: null, shown: 11, total: 11, clipped: 0, data: { series: [] },
    ui: { x_title: 'Hétéroscédasticité h' },
  }
  const pct = (v: number) => `${(v * 100).toFixed(1).replace('.', ',')} %`
</script>

<section class="dev">
  <h2>Banc d'essai des graphiques (fixture provisoire)</h2>
  <div class="controls">
    <label>Hétéroscédasticité h = {hetero.toFixed(2).replace('.', ',')}
      <input type="range" min="0" max="1" step="0.05" bind:value={hetero} />
    </label>
    <label>Pas du pendule h = {pas.toFixed(2).replace('.', ',')}
      <input type="range" min="0" max="1" step="0.05" bind:value={pas} />
    </label>
    <label><input type="checkbox" bind:checked={correction} /> Correction</label>
    <label><input type="checkbox" bind:checked={showReference} /> Référence</label>
    <button onclick={() => (seed += 1)}>Nouveau tirage</button>
  </div>
  <p class="muted">
    Couverture : MCO {pct(reg.coverage.ols)}, HC3 {pct(reg.coverage.hc3)} · Erreur maximale du pendule :
    Euler {pct(pen.errors.euler)}, RK4 {pct(pen.errors.rk4)} · graine {seed}
  </p>

  <div class="grid">
    <PlotlyChart view={reg.views.nuage} methodsOn={regOn} {showReference} />
    <PlotlyChart view={reg.views.residus} methodsOn={regOn} {showReference} />
    <PlotlyChart view={reg.views.ic} methodsOn={regOn} {showReference} height={420} />
    <PlotlyChart
      view={sensView}
      roles={regRoles}
      methodsOn={regOn}
      {showReference}
      {sweep}
      measure={{ label: 'Taux de couverture réel', unit: '%', scale: 100 }}
      methodLabels={regLabels}
      height={420}
    />
    <PlotlyChart view={reg.views.pentes} methodsOn={regOn} {showReference} />
    <PlotlyChart view={pen.view} methodsOn={penOn} {showReference} />
  </div>
</section>

<style>
  .dev {
    margin-top: var(--ct-space-8);
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-4);
    align-items: center;
  }
  .controls label {
    display: flex;
    gap: var(--ct-space-2);
    align-items: center;
  }
  .muted {
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(28rem, 1fr));
    gap: var(--ct-space-4);
    margin-top: var(--ct-space-4);
  }
</style>
