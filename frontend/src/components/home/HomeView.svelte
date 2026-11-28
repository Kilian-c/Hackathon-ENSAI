<script lang="ts">
  // Accueil : les deux modes (Entraînement, Laboratoire), tenant sur un écran.
  // La liste des expériences est sur une page à part (?labo, LabGallery.svelte).
  import { LAB_GALLERY_HREF, TRAIN_ALL_HREF } from './experiments'
  import TrainPicker from './TrainPicker.svelte'

  // Lien de la série : « Tout » tant que le choix des thèmes n'a pas changé (TrainPicker le met à jour).
  let trainHref = $state(TRAIN_ALL_HREF)
</script>

<div class="screen">
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
            {#each [[22, 58], [36, 60], [48, 48], [60, 52], [74, 40], [86, 46], [98, 30], [112, 38], [124, 22], [138, 34]] as [cx, cy] (cx)}
              <circle {cx} {cy} r="3.2" class="dot" />
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
  .screen {
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    background: radial-gradient(
        ellipse 70% 45% at 50% 0%,
        color-mix(in srgb, var(--ct-role-method) 13%, transparent),
        transparent 100%
      ),
      var(--ct-bg);
  }
  .home {
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

  @media (prefers-reduced-motion: reduce) {
    .mode {
      transition: none;
    }
    .mode:hover {
      transform: none;
    }
  }
</style>
