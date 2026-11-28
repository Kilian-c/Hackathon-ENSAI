<script lang="ts">
  // Accueil : les deux modes (Entraînement, Laboratoire), tenant sur un écran.
  // La liste des expériences est sur une page à part (?labo, LabGallery.svelte).
  import { LAB_GALLERY_HREF, TRAIN_ALL_HREF } from './experiments'
  import TrainPicker from './TrainPicker.svelte'

  // Lien de la série : « Tout » tant que le choix des thèmes n'a pas changé (TrainPicker le met à jour).
  let trainHref = $state(TRAIN_ALL_HREF)
</script>

<div class="screen">
  <div class="glyphs" aria-hidden="true">
    <span class="glyph" style="--x: 4%; --y: 12%; --s: 3.2rem; --r: -8deg; --d: -0.0s">∑</span>
    <span class="glyph" style="--x: 11%; --y: 34%; --s: 4rem; --r: 6deg; --d: -1.3s">∫</span>
    <span class="glyph" style="--x: 3%; --y: 58%; --s: 2.4rem; --r: -4deg; --d: -2.6s">√n</span>
    <span class="glyph" style="--x: 10%; --y: 80%; --s: 2.6rem; --r: 10deg; --d: -3.9s">σ²</span>
    <span class="glyph" style="--x: 15%; --y: 8%; --s: 2rem; --r: 4deg; --d: -5.2s">π</span>
    <span class="glyph" style="--x: 6%; --y: 90%; --s: 2.2rem; --r: 0deg; --d: -6.5s">x̄</span>
    <span class="glyph" style="--x: 14%; --y: 62%; --s: 2.2rem; --r: -6deg; --d: -7.8s">∞</span>
    <span class="glyph" style="--x: 90%; --y: 10%; --s: 3rem; --r: 8deg; --d: -0.1s">∂</span>
    <span class="glyph" style="--x: 83%; --y: 30%; --s: 2.6rem; --r: -6deg; --d: -1.4s">μ</span>
    <span class="glyph" style="--x: 92%; --y: 48%; --s: 2.8rem; --r: 4deg; --d: -2.7s">β̂</span>
    <span class="glyph" style="--x: 84%; --y: 68%; --s: 2.6rem; --r: 0deg; --d: -4.0s">≈</span>
    <span class="glyph" style="--x: 86%; --y: 86%; --s: 1.8rem; --r: -5deg; --d: -5.3s">𝒩(0,1)</span>
    <span class="glyph" style="--x: 94%; --y: 76%; --s: 2.2rem; --r: 10deg; --d: -6.6s">λ</span>
    <span class="glyph" style="--x: 80%; --y: 6%; --s: 1.8rem; --r: -3deg; --d: -7.9s">eˣ</span>
  </div>
  <main class="home">
    <header class="hero">
      <p class="eyebrow">Réviser par la simulation</p>
      <h1>Crash-Test</h1>
      <p class="tagline">
        Chaque théorème repose sur des hypothèses. Cassez-en une, mesurez ce qui cède, puis réparez.
      </p>
    </header>

    <section class="modes" aria-label="Deux façons de travailler">
      <article class="mode mode-train">
        <div class="mode-art" aria-hidden="true">
          <svg viewBox="0 0 160 80">
            <rect x="8" y="14" width="144" height="14" rx="7" class="track" />
            <rect x="8" y="14" width="96" height="14" rx="7" class="fill-a" />
            <rect x="8" y="36" width="144" height="14" rx="7" class="track" />
            <rect x="8" y="36" width="58" height="14" rx="7" class="fill-b" />
            <rect x="8" y="58" width="144" height="14" rx="7" class="track" />
            <rect x="8" y="58" width="128" height="14" rx="7" class="fill-a" />
          </svg>
        </div>
        <p class="mode-kicker">Mode QCM</p>
        <h2>Entraînement</h2>
        <p class="mode-text">
          Une série de questions sur les idées fausses classiques. Indiquez votre degré de confiance : la
          correction est une simulation, et votre bilan montre si votre confiance est bien placée.
        </p>
        <ul class="mode-points">
          <li>Questions vérifiées par le moteur</li>
          <li>Trois crans de confiance, score de Brier</li>
          <li>Bilan de calibration</li>
        </ul>
        <TrainPicker bind:href={trainHref} />
        <div class="mode-actions">
          <a class="btn btn-primary" href={trainHref}>Commencer une série</a>
          <a class="btn btn-ghost" href="?bilan">Voir mon bilan</a>
        </div>
      </article>

      <article class="mode mode-lab">
        <div class="mode-art" aria-hidden="true">
          <svg viewBox="0 0 160 80">
            <line x1="10" y1="70" x2="150" y2="14" class="line-ref" />
            <line x1="10" y1="62" x2="150" y2="26" class="line-fit" />
            {#each [[22, 58], [36, 60], [48, 48], [60, 52], [74, 40], [86, 46], [98, 30], [112, 38], [124, 22], [138, 34]] as [cx, cy], i (cx)}
              <circle {cx} {cy} r="3.2" class="dot" style:--i={i} />
            {/each}
          </svg>
        </div>
        <p class="mode-kicker">Mode libre</p>
        <h2>Laboratoire</h2>
        <p class="mode-text">
          Manipulez une expérience : dégradez une hypothèse au curseur, observez les mesures passer de
          Fiable à Rompu, puis activez la correction.
        </p>
        <ul class="mode-points">
          <li>Équation qui réagit en direct</li>
          <li>Répétitions, sensibilité, domaine de validité</li>
          <li>Contre-exemples et défis</li>
        </ul>
        <div class="mode-actions">
          <a class="btn btn-primary" href={LAB_GALLERY_HREF}>Choisir une expérience</a>
        </div>
      </article>
    </section>

    <p class="import-link">
      Vous avez écrit votre propre expérience ? <a href="?import">Importer un fichier YAML</a>
    </p>
  </main>
</div>

<style>
  /* Le halo couvre toute la largeur, collé en haut de la fenêtre : pas de bande sombre au-dessus. */
  /* Le halo du fond est global (app.css, sur body) : il couvre aussi les autres pages. */
  .screen {
    position: relative;
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    overflow: hidden;
  }

  /* --- Symboles mathématiques du fond, sur les côtés, purement décoratifs --- */
  .glyphs {
    position: absolute;
    inset: 0;
    pointer-events: none;
    user-select: none;
  }
  .glyph {
    position: absolute;
    left: var(--x);
    top: var(--y);
    font-family: 'Cambria Math', 'STIX Two Math', 'Latin Modern Math', Georgia, serif;
    font-size: var(--s);
    line-height: 1;
    white-space: nowrap;
    color: var(--ct-muted);
    opacity: 0.18;
    transform: rotate(var(--r));
    animation: ct-float 9s ease-in-out infinite alternate;
    animation-delay: var(--d);
  }
  @keyframes ct-float {
    to {
      translate: 0 -10px;
    }
  }
  /* Écran étroit : les cartes prennent toute la largeur, les symboles passeraient dessous. */
  @media (max-width: 1100px) {
    .glyphs {
      display: none;
    }
  }
  .home {
    position: relative;
    width: 100%;
    max-width: 68rem;
    margin: auto;
    padding: var(--ct-space-6);
    box-sizing: border-box;
  }

  /* --- En-tête --- */
  .hero {
    text-align: center;
    margin-bottom: var(--ct-space-8);
  }
  .eyebrow {
    display: inline-block;
    margin: 0 0 var(--ct-space-3);
    padding: var(--ct-space-1) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
    background: var(--ct-surface);
  }
  h1 {
    margin: 0;
    font-size: clamp(2.25rem, 5vw, 3.25rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.05;
  }
  .tagline {
    max-width: 36rem;
    margin: var(--ct-space-3) auto 0;
    font-size: 1.1rem;
    color: var(--ct-muted);
  }

  .import-link {
    margin: var(--ct-space-6) 0 0;
    text-align: center;
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .import-link a {
    color: var(--ct-role-method);
  }

  /* --- Les deux modes --- */
  .modes {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
    gap: var(--ct-space-6);
  }
  .mode {
    --accent: var(--ct-role-method);
    display: flex;
    flex-direction: column;
    padding: var(--ct-space-6) var(--ct-space-8);
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    background:
      linear-gradient(160deg, color-mix(in srgb, var(--accent) 10%, transparent), transparent 55%),
      var(--ct-surface);
    transition:
      border-color 0.15s,
      transform 0.15s;
  }
  .mode:hover {
    border-color: color-mix(in srgb, var(--accent) 55%, var(--ct-border));
    transform: translateY(-2px);
  }
  .mode-lab {
    --accent: var(--ct-role-correction);
  }
  .mode-art {
    height: 3.5rem;
    margin-bottom: var(--ct-space-3);
  }
  .mode-art svg {
    height: 100%;
    width: auto;
  }
  .track {
    fill: var(--ct-surface-2);
  }
  .fill-a {
    fill: var(--accent);
  }
  .fill-b {
    fill: color-mix(in srgb, var(--accent) 45%, transparent);
  }
  .dot {
    fill: var(--ct-plot-data);
  }
  .line-ref {
    stroke: var(--ct-role-reference);
    stroke-width: 1.5;
    stroke-dasharray: 5 4;
  }
  .line-fit {
    stroke: var(--accent);
    stroke-width: 3;
    stroke-linecap: round;
  }
  .mode-kicker {
    margin: 0;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .mode h2 {
    margin: var(--ct-space-1) 0 var(--ct-space-2);
    font-size: var(--ct-text-xl);
    letter-spacing: -0.01em;
  }
  .mode-text {
    margin: 0;
    color: var(--ct-muted);
  }
  .mode-points {
    margin: var(--ct-space-4) 0 var(--ct-space-6);
    padding: 0;
    list-style: none;
    display: grid;
    gap: var(--ct-space-1);
    font-size: var(--ct-text-sm);
  }
  .mode-points li {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
  }
  .mode-points li::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    flex: none;
  }
  .mode-actions {
    margin-top: auto;
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-3);
  }

  /* --- Boutons --- */
  .btn {
    display: inline-flex;
    align-items: center;
    padding: 0.6rem 1.1rem;
    border-radius: var(--ct-radius);
    border: 1px solid transparent;
    font-weight: 600;
    text-decoration: none;
    transition:
      background 0.15s,
      border-color 0.15s;
  }
  .btn-primary {
    background: var(--accent);
    color: var(--ct-bg);
  }
  .btn-primary:hover {
    background: color-mix(in srgb, var(--accent) 85%, var(--ct-text));
  }
  .btn-ghost {
    color: var(--ct-text);
    border-color: var(--ct-border);
  }
  .btn-ghost:hover {
    background: var(--ct-surface-2);
  }

  /* Taille qui suit la hauteur de la fenêtre, sans retirer d'élément : version resserrée
     jusqu'à 1000 px de haut, version complète à partir de 1150 px, et un passage continu entre les deux.
     Chaque valeur vaut clamp(resserrée, resserrée + pente × (hauteur − 1000 px), complète). */
  .screen {
    --fit: (100vh - 1000px);
  }
  .home {
    padding-block: clamp(12px, calc(12px + var(--fit) * 0.08), 24px);
  }
  .hero {
    margin-bottom: clamp(16px, calc(16px + var(--fit) * 0.1067), 32px);
  }
  .eyebrow {
    margin-bottom: clamp(8px, calc(8px + var(--fit) * 0.0267), 12px);
  }
  h1 {
    font-size: clamp(2rem, min(5vw, calc(44px + var(--fit) * 0.0533)), 3.25rem);
  }
  .tagline {
    max-width: 44rem;
    margin-top: clamp(8px, calc(8px + var(--fit) * 0.0267), 12px);
    font-size: clamp(16px, calc(16px + var(--fit) * 0.0107), 17.6px);
  }
  .mode {
    padding: clamp(16px, calc(16px + var(--fit) * 0.0533), 24px)
      clamp(24px, calc(24px + var(--fit) * 0.0533), 32px);
  }
  .mode-art {
    height: clamp(40px, calc(40px + var(--fit) * 0.1067), 56px);
    margin-bottom: clamp(8px, calc(8px + var(--fit) * 0.0267), 12px);
  }
  .mode h2 {
    margin-bottom: clamp(4px, calc(4px + var(--fit) * 0.0267), 8px);
    font-size: clamp(20px, calc(20px + var(--fit) * 0.0533), 28px);
  }
  .mode-text {
    line-height: clamp(1.45em, calc(1.45em + var(--fit) * 0.0053), 1.5em);
  }
  .mode-points {
    margin: clamp(12px, calc(12px + var(--fit) * 0.0267), 16px) 0
      clamp(16px, calc(16px + var(--fit) * 0.0533), 24px);
    gap: clamp(0px, calc(var(--fit) * 0.0267), 4px);
  }
  .import-link {
    margin-top: clamp(12px, calc(12px + var(--fit) * 0.08), 24px);
  }

  /* --- Ouverture : fondu de l'en-tête, puis les deux cartes qui montent l'une après l'autre.
     `backwards` (et non `both`) : une fois l'animation finie, le transform du survol reprend la main. --- */
  @keyframes ct-fade-in {
    from {
      opacity: 0;
    }
  }
  @keyframes ct-rise-in {
    from {
      opacity: 0;
      transform: translateY(24px) scale(0.98);
    }
  }
  @keyframes ct-grow-x {
    from {
      transform: scaleX(0);
    }
  }
  @keyframes ct-draw {
    from {
      stroke-dashoffset: 160;
    }
  }
  @keyframes ct-pop {
    from {
      opacity: 0;
      transform: scale(0);
    }
  }
  .hero {
    animation: ct-fade-in 0.6s ease-out backwards;
  }
  .mode {
    animation: ct-rise-in 0.7s cubic-bezier(0.22, 1, 0.36, 1) backwards;
    animation-delay: 0.15s;
  }
  .mode-lab {
    animation-delay: 0.3s;
  }
  .import-link {
    animation: ct-fade-in 0.6s ease-out 0.6s backwards;
  }
  /* Petits dessins : barres qui se remplissent, droite tracée, points qui apparaissent. */
  .mode .fill-a,
  .mode .fill-b {
    transform-box: fill-box;
    transform-origin: left center;
    animation: ct-grow-x 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.45s backwards;
  }
  .line-fit {
    stroke-dasharray: 160;
    animation: ct-draw 0.9s ease-out 0.55s backwards;
  }
  .dot {
    transform-box: fill-box;
    transform-origin: center;
    animation: ct-pop 0.3s ease-out backwards;
    animation-delay: calc(0.5s + var(--i) * 0.04s);
  }

  @media (prefers-reduced-motion: reduce) {
    .hero,
    .mode,
    .import-link,
    .mode .fill-a,
    .mode .fill-b,
    .line-fit,
    .dot,
    .glyph {
      animation: none;
    }
    .mode {
      transition: none;
    }
    .mode:hover {
      transform: none;
    }
  }
</style>
