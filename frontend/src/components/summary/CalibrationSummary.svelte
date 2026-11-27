<!--
  CalibrationSummary.svelte : l'écran Bilan (fichier de R4). Cahier, section 2.4.
  Dans l'ordre : une phrase lisible, trois chiffres, la confiance face à la réussite (par bouton,
  puis en courbe à partir de 20 réponses), le détail par expérience, et un profil de démonstration.
  Tout vient de l'historique local (lib/training.ts) ; les calculs sont dans lib/calibration.ts.
-->
<script lang="ts">
  import { onMount } from 'svelte'
  import PlotlyChart from '../PlotlyChart.svelte'
  import {
    allAnswers,
    calibrationView,
    demoAnswers,
    experimentStats,
    headlineLevel,
    levelStats,
    MIN_FOR_CURVE,
    murphy,
    summarize,
    tendency,
    type Tendency,
  } from '../../lib/calibration'
  import { frNumber } from '../../lib/format'
  import { listExperiments } from '../../lib/labSource'
  import { LINK_VERSION } from '../../lib/state'
  import { browserStore, loadHistory } from '../../lib/training'

  const history = allAnswers(loadHistory(browserStore()))

  const TENDENCIES: Record<Tendency, { icon: string; title: string; advice: string }> = {
    over: {
      icon: '▼',
      title: 'Plutôt trop sûr de vous',
      advice: 'Votre confiance dépasse votre réussite. Avant de cliquer sur « Certain », cherchez ce qui pourrait vous donner tort.',
    },
    under: {
      icon: '▲',
      title: 'Plutôt trop prudent',
      advice: 'Vous réussissez mieux que vous ne le pensez. Osez annoncer plus de confiance quand vous savez.',
    },
    calibrated: {
      icon: '✓',
      title: 'Bien calibré',
      advice: 'Votre confiance colle à votre réussite : vous savez quand vous savez.',
    },
  }

  let demo = $state(false)
  let titles = $state<Record<string, string>>({})
  let experimentIds = $state<string[]>([])

  const answers = $derived(demo ? demoAnswers(experimentIds) : history)
  const summary = $derived(summarize(answers))
  const levels = $derived(levelStats(answers))
  const headline = $derived(headlineLevel(levels))
  const trend = $derived(
    summary && summary.count >= MIN_FOR_CURVE ? TENDENCIES[tendency(summary.confidence, summary.success)] : null,
  )
  const trendKind = $derived(summary ? tendency(summary.confidence, summary.success) : 'calibrated')
  const remaining = $derived(Math.max(0, MIN_FOR_CURVE - answers.length))
  const experiments = $derived(experimentStats(answers))
  const parts = $derived(murphy(answers))

  const percent = (x: number | null) => (x === null ? '—' : `${frNumber(x * 100, 0)} %`)

  onMount(() => {
    // Les titres sont un confort : sans le moteur, les identifiants s'affichent.
    listExperiments().then(
      (r) => {
        titles = Object.fromEntries(r.items.map((e) => [e.id, e.title]))
        experimentIds = r.items.map((e) => e.id)
      },
      () => {},
    )
  })
</script>

<main class="summary">
  <header>
    <div>
      <a class="back" href="?">← Accueil</a>
      <h1>Votre bilan</h1>
      <p class="muted">Savez-vous quand vous avez raison ?</p>
    </div>
    <div class="actions">
      <a class="button primary" href="?train=toutes&v={LINK_VERSION}">S'entraîner</a>
    </div>
  </header>

  {#if demo}
    <p class="banner" role="status">
      <span><strong>Profil de démonstration</strong> : ces réponses sont fictives et ne sont pas enregistrées.</span>
      <button type="button" onclick={() => (demo = false)}>Revenir à mes réponses</button>
    </p>
  {/if}

  {#if !summary || !headline}
    <section class="card empty">
      <h2>Aucune réponse pour l'instant</h2>
      <p>
        Répondez à une série en indiquant votre confiance. Vous verrez ici si elle correspond à vos résultats.
      </p>
      <p><a class="button primary" href="?train=toutes&v={LINK_VERSION}">Commencer une série</a></p>
    </section>
  {:else}
    <section class="card hero" aria-label="En une phrase">
      <p class="sentence">
        Quand vous dites <em>«&nbsp;{headline.label}&nbsp;»</em>, vous avez raison dans
        <strong>{percent(headline.success)}</strong> des cas.
      </p>
      <p class="muted">
        {headline.correct} sur {headline.count} avec ce bouton, pour une confiance annoncée de {percent(headline.confidence)}.
      </p>
      {#if trend}
        <p class="trend {trendKind}">
          <strong><span aria-hidden="true">{trend.icon}</span> {trend.title}.</strong>
          {trend.advice}
        </p>
      {/if}
    </section>

    <dl class="tiles">
      <div class="card">
        <dt>Score de Brier</dt>
        <dd>{frNumber(summary.brier, 2)}</dd>
        <dd class="hint">0 est parfait, 1 est le pire. Plus il est bas, mieux c'est.</dd>
      </div>
      <div class="card">
        <dt>Bonnes réponses</dt>
        <dd>{percent(summary.success)}</dd>
        <dd class="hint">{summary.correct} sur {summary.count}</dd>
      </div>
      <div class="card">
        <dt>Confiance annoncée</dt>
        <dd>{percent(summary.confidence)}</dd>
        <dd class="hint">En moyenne, à comparer à votre réussite.</dd>
      </div>
    </dl>

    <div class="columns">
      <section class="card" aria-labelledby="titre-crans">
        <h2 id="titre-crans">Bouton par bouton</h2>
        <p class="legend" aria-hidden="true">
          <span><span class="swatch"></span> Réussite réelle</span>
          <span><span class="tick"></span> Confiance annoncée</span>
        </p>
        <ul class="levels">
          {#each levels as l (l.level)}
            <li>
              <div class="row">
                <strong>{l.label}</strong>
                <span class="muted">{l.count} {l.count > 1 ? 'réponses' : 'réponse'}</span>
              </div>
              {#if l.success !== null && l.confidence !== null}
                <div class="meter" aria-hidden="true">
                  <span class="fill" style:width="{l.success * 100}%"></span>
                  <span class="mark" style:left="{l.confidence * 100}%"></span>
                </div>
                <p class="values">Réussite {percent(l.success)} · annoncée {percent(l.confidence)}</p>
              {:else}
                <div class="meter" aria-hidden="true"></div>
                <p class="values muted">Pas encore utilisé.</p>
              {/if}
            </li>
          {/each}
        </ul>
      </section>

      <section class="curve" aria-label="Courbe de calibration">
        {#if remaining === 0}
          <PlotlyChart view={calibrationView(levels)} methodsOn={new Set()} height={360} />
          <p class="muted note">
            Un point sous la diagonale signale un excès de confiance ; au-dessus, un excès de prudence.
          </p>
        {:else}
          <div class="card locked">
            <h2>Courbe de calibration</h2>
            <p class="big">Encore {remaining} {remaining > 1 ? 'questions' : 'question'}</p>
            <progress max={MIN_FOR_CURVE} value={answers.length} aria-label="Réponses avant la courbe"></progress>
            <p class="muted">Avant {MIN_FOR_CURVE} réponses, la courbe serait surtout du hasard.</p>
          </div>
        {/if}
      </section>
    </div>

    <section class="card" aria-labelledby="titre-experiences">
      <h2 id="titre-experiences">Par expérience</h2>
      <p class="muted">La moins bien maîtrisée en premier.</p>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Expérience</th>
              <th scope="col">Réussite</th>
              <th scope="col">Confiance</th>
              <th scope="col">Brier</th>
              <th scope="col">Erreurs en «&nbsp;Certain&nbsp;»</th>
              <th scope="col"><span class="sr">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {#each experiments as e (e.id)}
              <tr>
                <th scope="row">{titles[e.id] ?? e.id}</th>
                <td>{percent(e.success)} <span class="muted">({e.correct}/{e.count})</span></td>
                <td>{percent(e.confidence)}</td>
                <td>{frNumber(e.brier, 2)}</td>
                <td class:alert={e.sureMistakes > 0}>{e.sureMistakes}</td>
                <td class="links">
                  <a href="?exp={encodeURIComponent(e.id)}&v={LINK_VERSION}">Revoir</a>
                  <a href="?train={encodeURIComponent(e.id)}&v={LINK_VERSION}">S'entraîner</a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    {#if parts}
      <details class="card">
        <summary>Pour aller plus loin : de quoi est fait votre score</summary>
        <p class="formula">
          {frNumber(summary.brier, 3)} = {frNumber(parts.calibration, 3)} − {frNumber(parts.resolution, 3)} +
          {frNumber(parts.uncertainty, 3)}
        </p>
        <ul class="parts">
          <li><strong>Calibration ({frNumber(parts.calibration, 3)})</strong> : l'écart entre confiance et réussite. À réduire.</li>
          <li><strong>Résolution ({frNumber(parts.resolution, 3)})</strong> : votre capacité à distinguer ce que vous savez de ce que vous ignorez. À augmenter.</li>
          <li><strong>Incertitude ({frNumber(parts.uncertainty, 3)})</strong> : la difficulté des questions, indépendante de votre confiance.</li>
        </ul>
      </details>
    {/if}
  {/if}

  {#if !demo}
    <p class="demo"><button type="button" onclick={() => (demo = true)}>Voir un profil de démonstration</button></p>
  {/if}
</main>

<style>
  .summary {
    max-width: 68rem;
    margin: 0 auto;
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-8);
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ct-space-4);
  }
  header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-end;
    gap: var(--ct-space-4);
  }
  h1 {
    margin: 0;
    font-size: var(--ct-text-xl);
  }
  h2 {
    margin: 0;
    font-size: var(--ct-text-lg);
  }
  p,
  dl,
  dd,
  ul {
    margin: 0;
  }
  ul {
    padding: 0;
    list-style: none;
  }
  .back,
  .muted,
  .note {
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .back {
    text-decoration: none;
  }
  .card {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-content: start;
    gap: var(--ct-space-3);
    padding: var(--ct-space-4) var(--ct-space-6);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  button,
  .button {
    font: inherit;
    font-size: var(--ct-text-sm);
    color: var(--ct-text);
    background: var(--ct-surface-2);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    padding: var(--ct-space-1) var(--ct-space-3);
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
  }
  .button.primary {
    font-size: var(--ct-text-md);
    font-weight: 600;
    border-color: var(--ct-role-method);
    padding: var(--ct-space-2) var(--ct-space-4);
  }
  .banner {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: var(--ct-space-3);
    padding: var(--ct-space-2) var(--ct-space-4);
    border: 1px dashed var(--ct-verdict-warning);
    border-radius: var(--ct-radius);
    font-size: var(--ct-text-sm);
  }
  .hero {
    border-left: 4px solid var(--ct-role-method);
  }
  .sentence {
    font-size: var(--ct-text-xl);
    line-height: 1.35;
  }
  .sentence em {
    font-style: normal;
    font-weight: 600;
  }
  .sentence strong {
    color: var(--ct-role-method);
  }
  .trend {
    padding: var(--ct-space-2) var(--ct-space-3);
    border: 1px solid var(--ct-verdict-warning);
    border-radius: var(--ct-radius);
  }
  .trend strong {
    color: var(--ct-verdict-warning);
  }
  .trend.calibrated {
    border-color: var(--ct-verdict-ok);
  }
  .trend.calibrated strong {
    color: var(--ct-verdict-ok);
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
    gap: var(--ct-space-4);
  }
  .tiles .card {
    gap: var(--ct-space-1);
  }
  dt {
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  dd {
    font-size: 2.5rem;
    font-weight: 600;
    line-height: 1.2;
  }
  dd.hint {
    font-size: var(--ct-text-sm);
    font-weight: 400;
    color: var(--ct-muted);
  }
  .columns {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(24rem, 100%), 1fr));
    gap: var(--ct-space-4);
  }
  .curve {
    display: grid;
    align-content: start;
    gap: var(--ct-space-2);
    min-width: 0;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-4);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .legend > span {
    display: inline-flex;
    align-items: center;
    gap: var(--ct-space-2);
  }
  .swatch {
    width: 1.5rem;
    height: 0.6rem;
    border-radius: 3px;
    background: var(--ct-role-method);
  }
  .tick {
    width: 3px;
    height: 1rem;
    background: var(--ct-text);
  }
  .levels {
    display: grid;
    gap: var(--ct-space-4);
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .meter {
    position: relative;
    height: 0.75rem;
    margin: var(--ct-space-2) 0;
    background: var(--ct-surface-2);
    border-radius: 4px;
  }
  .fill {
    position: absolute;
    inset: 0 auto 0 0;
    background: var(--ct-role-method);
    border-radius: 4px;
  }
  .mark {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 3px;
    margin-left: -1.5px;
    background: var(--ct-text);
    box-shadow: 0 0 0 2px var(--ct-surface);
  }
  .values {
    font-size: var(--ct-text-sm);
  }
  .locked {
    justify-items: center;
    text-align: center;
    height: 100%;
    align-content: center;
    box-sizing: border-box;
  }
  .big {
    font-size: var(--ct-text-xl);
    font-weight: 600;
  }
  progress {
    width: min(18rem, 100%);
    accent-color: var(--ct-role-method);
  }
  .scroll {
    position: relative; /* le texte masqué de l'en-tête reste dans la zone défilante */
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--ct-text-sm);
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    padding: var(--ct-space-2) var(--ct-space-3);
    border-bottom: 1px solid var(--ct-border);
    text-align: left;
  }
  thead th {
    color: var(--ct-muted);
    font-weight: 400;
  }
  .alert {
    color: var(--ct-verdict-broken);
    font-weight: 600;
  }
  .links {
    white-space: nowrap;
  }
  .links a {
    color: var(--ct-role-method);
    margin-right: var(--ct-space-3);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  details summary {
    cursor: pointer;
    font-weight: 600;
  }
  .formula {
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-lg);
  }
  .parts {
    display: grid;
    gap: var(--ct-space-2);
    font-size: var(--ct-text-sm);
  }
  .demo {
    text-align: right;
  }
  .demo button {
    color: var(--ct-muted);
    background: none;
    border-color: transparent;
  }
</style>
