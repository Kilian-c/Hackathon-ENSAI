<!--
  ImportView.svelte : l'écran Import (P1, cahier section 2.7 ; fichier de R4, écrit avec R3).

  Trois outils : « Copier le prompt » (gabarit à coller dans un assistant IA externe, aucun appel IA
  ici), un éditeur validé par POST /api/validate (erreurs par ligne et tests 1, 3, 4, 10), et
  « Créer un lien de partage » (Supabase, lib/share.ts). Le YAML en cours est gardé dans ce navigateur
  (brouillon) : « Ouvrir dans le Laboratoire » l'ouvre par ?brouillon, sans rien enregistrer ailleurs.
-->
<script lang="ts">
  import { ApiError, api } from '../lib/executor'
  import { importPrompt } from '../lib/importPrompt'
  import { loadDraft, saveDraft, saveShared, ShareError, shareUrl, sharingAvailable } from '../lib/share'
  import type { ValidateIssue, ValidateResponse } from '../lib/types.gen'
  import exampleYaml from '../../../experiments/somme_des.yaml?raw'

  const MAX_BYTES = 64 * 1024

  let content = $state(loadDraft() ?? '')
  let theorem = $state('')
  let report = $state<ValidateResponse | null>(null)
  /** Contenu exact au moment de la dernière vérification : le rapport ne vaut que pour lui. */
  let checkedContent = $state<string | null>(null)
  let checking = $state(false)
  let error = $state<string | null>(null)
  let promptCopied = $state(false)
  let dragging = $state(false)
  let sharing = $state(false)
  let shared = $state<{ url: string; content: string } | null>(null)
  let shareCopied = $state(false)
  let textarea = $state<HTMLTextAreaElement | null>(null)
  let gutter = $state<HTMLDivElement | null>(null)

  const lineCount = $derived(Math.max(1, content.split('\n').length))
  const bytes = $derived(new TextEncoder().encode(content).length)
  const upToDate = $derived(report !== null && checkedContent === content)
  const schemaOk = $derived(upToDate && report !== null && report.errors.length === 0)
  const errorLines = $derived(new Set((upToDate ? (report?.errors ?? []) : []).map((e) => e.line).filter((l) => l)))
  const canShare = $derived(schemaOk && sharingAvailable() && !sharing)

  // Brouillon gardé à chaque modification (léger : un seul appel à localStorage).
  $effect(() => {
    saveDraft(content)
  })

  function messageOf(err: unknown): string {
    if (err instanceof ApiError || err instanceof ShareError || err instanceof Error) return err.message
    return 'Une erreur inattendue est survenue.'
  }

  async function check(): Promise<void> {
    if (!content.trim()) {
      error = "Collez d'abord le contenu d'un fichier YAML."
      return
    }
    if (bytes > MAX_BYTES) {
      error = `Le fichier fait ${Math.ceil(bytes / 1024)} Ko : 64 Ko au plus.`
      return
    }
    const sent = content
    checking = true
    error = null
    try {
      report = await api.validate({ raw_content: sent })
      checkedContent = sent
    } catch (err) {
      error = messageOf(err)
    } finally {
      checking = false
    }
  }

  async function copyPrompt(): Promise<void> {
    const text = importPrompt(theorem)
    try {
      await navigator.clipboard.writeText(text)
      promptCopied = true
      setTimeout(() => (promptCopied = false), 2500)
    } catch {
      error = "Votre navigateur n'autorise pas la copie automatique : sélectionnez le texte du prompt à la main."
    }
  }

  function loadExample(): void {
    content = exampleYaml
    report = null
  }

  async function readFile(file: File): Promise<void> {
    if (!/\.ya?ml$/i.test(file.name) && !file.type.startsWith('text/')) {
      error = `« ${file.name} » n'est pas un fichier YAML (.yaml ou .yml).`
      return
    }
    if (file.size > MAX_BYTES) {
      error = `Le fichier « ${file.name} » fait ${Math.ceil(file.size / 1024)} Ko : 64 Ko au plus.`
      return
    }
    content = (await file.text()).replace(/\r\n/g, '\n')
    report = null
    error = null
    await check()
  }

  function onDrop(event: DragEvent): void {
    event.preventDefault()
    dragging = false
    const file = event.dataTransfer?.files[0]
    if (file) void readFile(file)
  }

  function onPick(event: Event): void {
    const input = event.currentTarget as HTMLInputElement
    const file = input.files?.[0]
    if (file) void readFile(file)
    input.value = ''
  }

  /** Place le curseur au début de la ligne citée par une erreur. */
  function goToLine(line: number | null | undefined): void {
    if (!line || !textarea) return
    const lines = content.split('\n')
    const start = lines.slice(0, line - 1).reduce((n, l) => n + l.length + 1, 0)
    const end = start + (lines[line - 1]?.length ?? 0)
    textarea.focus()
    textarea.setSelectionRange(start, end)
    const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 20
    textarea.scrollTop = Math.max(0, (line - 4) * lineHeight)
  }

  function syncGutter(): void {
    if (gutter && textarea) gutter.scrollTop = textarea.scrollTop
  }

  function openInLab(): void {
    saveDraft(content)
    location.href = '?brouillon&v=1'
  }

  async function share(): Promise<void> {
    if (!canShare) return
    sharing = true
    error = null
    try {
      const id = await saveShared(content)
      shared = { url: shareUrl(id), content }
    } catch (err) {
      error = messageOf(err)
    } finally {
      sharing = false
    }
  }

  async function copyShare(): Promise<void> {
    if (!shared) return
    try {
      await navigator.clipboard.writeText(shared.url)
      shareCopied = true
      setTimeout(() => (shareCopied = false), 2000)
    } catch {
      window.prompt('Copiez ce lien :', shared.url)
    }
  }

  /** Erreur de syntaxe YAML : PyYAML la repère parfois une ligne plus bas que la vraie faute (guillemet non fermé). */
  function isSyntaxIssue(issue: ValidateIssue): boolean {
    return issue.message.startsWith('YAML invalide')
  }

  function where(issue: ValidateIssue): string {
    const line = issue.line ? `${isSyntaxIssue(issue) ? 'vers la ligne' : 'ligne'} ${issue.line}` : null
    const parts = [line, issue.path || null].filter(Boolean)
    return parts.join(', ')
  }
</script>

<main class="import">
  <header class="top">
    <a class="back" href="?">← Accueil</a>
    <h1>Importer une expérience</h1>
    <p class="lead">
      Une expérience est un seul fichier YAML. Faites-le écrire par l'assistant IA de votre choix, vérifiez-le
      ici, puis ouvrez-le dans le Laboratoire ou partagez-le par un lien.
    </p>
  </header>

  <section class="card step" aria-labelledby="step-prompt">
    <h2 id="step-prompt"><span class="num">1</span> Faire écrire le fichier</h2>
    <p class="muted">
      Le prompt contient le format exact, les méthodes disponibles et deux expériences complètes. Collez-le
      dans un assistant IA externe : Crash-Test n'appelle aucune IA.
    </p>
    <div class="row">
      <label class="grow">
        <span class="sr-only">Théorème à illustrer</span>
        <input
          type="text"
          bind:value={theorem}
          placeholder="Théorème à illustrer (facultatif), par exemple : la loi des grands nombres"
        />
      </label>
      <button type="button" class="btn btn-primary" onclick={copyPrompt}>
        {promptCopied ? '✓ Prompt copié' : 'Copier le prompt'}
      </button>
    </div>
  </section>

  <div class="work">
    <section class="card editor-card" aria-labelledby="step-editor">
      <div class="editor-head">
        <h2 id="step-editor"><span class="num">2</span> Coller ou déposer le YAML</h2>
        <div class="row tight">
          <label class="btn btn-ghost file">
            Choisir un fichier
            <input type="file" accept=".yaml,.yml,text/yaml,text/plain" onchange={onPick} />
          </label>
          <button type="button" class="btn btn-ghost" onclick={loadExample}>Charger un exemple</button>
        </div>
      </div>

      <div
        class="editor"
        class:dragging
        role="group"
        aria-label="Éditeur du fichier YAML"
        ondragover={(e) => {
          e.preventDefault()
          dragging = true
        }}
        ondragleave={() => (dragging = false)}
        ondrop={onDrop}
      >
        <div class="gutter" bind:this={gutter} aria-hidden="true">
          {#each { length: lineCount } as _, i (i)}
            <div class:bad={errorLines.has(i + 1)}>{i + 1}</div>
          {/each}
        </div>
        <textarea
          bind:this={textarea}
          bind:value={content}
          onscroll={syncGutter}
          spellcheck="false"
          autocomplete="off"
          wrap="off"
          placeholder="schema_version: 1&#10;id: &quot;mon-experience&quot;&#10;…&#10;&#10;Collez votre fichier ici, ou déposez un fichier .yaml."
          aria-label="Contenu du fichier YAML"
        ></textarea>
        {#if dragging}<div class="drop" aria-hidden="true">Déposez le fichier ici</div>{/if}
      </div>

      <div class="editor-foot">
        <span class="muted small" class:over={bytes > MAX_BYTES}>
          {lineCount} lignes · {(bytes / 1024).toFixed(1).replace('.', ',')} Ko sur 64
        </span>
        <button type="button" class="btn btn-primary" onclick={check} disabled={checking}>
          {checking ? 'Vérification… (quelques secondes)' : 'Vérifier le fichier'}
        </button>
      </div>
    </section>

    <section class="card report" aria-labelledby="step-report" aria-live="polite">
      <h2 id="step-report"><span class="num">3</span> Vérification</h2>

      {#if error}
        <p class="banner error" role="alert">{error}</p>
      {/if}

      {#if !report}
        <p class="muted">
          La vérification lit le fichier, signale chaque erreur avec sa ligne, puis lance quatre tests
          scientifiques par simulation (200 répétitions).
        </p>
      {:else}
        {#if !upToDate}
          <p class="banner warn">Le fichier a changé depuis la vérification : vérifiez-le de nouveau.</p>
        {/if}

        {#if report.errors.length > 0}
          <h3>Erreurs ({report.errors.length})</h3>
          <ul class="issues">
            {#each report.errors as issue, i (i)}
              <li class="issue bad">
                <button type="button" class="link" onclick={() => goToLine(issue.line)} disabled={!issue.line}>
                  <span class="icon" aria-hidden="true">✗</span>
                  <span class="where">{where(issue) || 'fichier'}</span>
                </button>
                <span>{issue.message}</span>
                {#if isSyntaxIssue(issue)}
                  <span class="muted small">(la faute peut aussi être sur la ligne juste au-dessus)</span>
                {/if}
              </li>
            {/each}
          </ul>
        {:else}
          <p class="banner ok">✓ Le format est valide.</p>
        {/if}

        {#if report.warnings.length > 0}
          <h3>Avertissements</h3>
          <ul class="issues">
            {#each report.warnings as issue, i (i)}
              <li class="issue warn">
                <button type="button" class="link" onclick={() => goToLine(issue.line)} disabled={!issue.line}>
                  <span class="icon" aria-hidden="true">!</span>
                  <span class="where">{where(issue) || 'fichier'}</span>
                </button>
                <span>{issue.message}</span>
              </li>
            {/each}
          </ul>
        {/if}

        {#if report.tests.length > 0}
          <h3>Tests scientifiques</h3>
          <ul class="tests">
            {#each report.tests as t (t.id)}
              <li class:passed={t.passed} class:failed={!t.passed}>
                <span class="icon" aria-hidden="true">{t.passed ? '✓' : '✗'}</span>
                <span>
                  <strong>{t.name}</strong>
                  <span class="sr-only">{t.passed ? ' : réussi' : ' : échoué'}</span>
                  {#if t.detail}<span class="detail">{t.detail}</span>{/if}
                </span>
              </li>
            {/each}
          </ul>
          {#if !report.ok && report.errors.length === 0}
            <p class="muted small">
              L'expérience s'ouvre quand même, mais ses verdicts ne démontrent pas encore ce qu'elle annonce.
            </p>
          {/if}
        {/if}
      {/if}

      <div class="actions">
        <button type="button" class="btn btn-primary" onclick={openInLab} disabled={!schemaOk}>
          Ouvrir dans le Laboratoire
        </button>
        <button
          type="button"
          class="btn btn-ghost"
          onclick={share}
          disabled={!canShare}
          title={sharingAvailable() ? undefined : "Le partage n'est pas configuré sur cette installation."}
        >
          {sharing ? 'Enregistrement…' : 'Créer un lien de partage'}
        </button>
      </div>
      {#if !sharingAvailable()}
        <p class="muted small">Le partage par lien n'est pas configuré sur cette installation.</p>
      {/if}

      {#if shared}
        <div class="shared">
          <p>
            Lien créé. Toute personne qui l'a peut ouvrir cette expérience ; le fichier enregistré ne
            changera plus.{#if shared.content !== content} (Il ne contient pas vos dernières modifications.){/if}
          </p>
          <div class="row tight">
            <input type="text" readonly value={shared.url} aria-label="Lien de partage" onfocus={(e) => e.currentTarget.select()} />
            <button type="button" class="btn btn-ghost" onclick={copyShare}>{shareCopied ? '✓ Copié' : 'Copier'}</button>
            <a class="btn btn-ghost" href={shared.url}>Ouvrir</a>
          </div>
        </div>
      {/if}
    </section>
  </div>
</main>

<style>
  .import {
    --accent: var(--ct-role-method);
    max-width: 80rem;
    margin: 0 auto;
    padding: var(--ct-space-6);
    box-sizing: border-box;
  }
  .top {
    margin-bottom: var(--ct-space-6);
  }
  .back {
    color: var(--ct-muted);
    text-decoration: none;
    font-size: var(--ct-text-sm);
  }
  .back:hover {
    color: var(--ct-text);
  }
  h1 {
    margin: var(--ct-space-2) 0 var(--ct-space-2);
    font-size: var(--ct-text-xl);
  }
  .lead {
    margin: 0;
    max-width: 48rem;
    color: var(--ct-muted);
  }
  h2 {
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
    margin: 0;
    font-size: var(--ct-text-lg);
  }
  h3 {
    margin: var(--ct-space-4) 0 var(--ct-space-2);
    font-size: var(--ct-text-md);
  }
  .num {
    display: inline-grid;
    place-items: center;
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--accent) 20%, transparent);
    color: var(--accent);
    font-size: var(--ct-text-sm);
    font-weight: 700;
  }
  .card {
    padding: var(--ct-space-4) var(--ct-space-6);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
    background: var(--ct-surface);
  }
  .step {
    margin-bottom: var(--ct-space-6);
  }
  .step p {
    margin: var(--ct-space-2) 0 var(--ct-space-3);
  }
  .muted {
    color: var(--ct-muted);
  }
  .small {
    font-size: var(--ct-text-sm);
  }
  .row {
    display: flex;
    gap: var(--ct-space-3);
    align-items: center;
    flex-wrap: wrap;
  }
  .row.tight {
    gap: var(--ct-space-2);
  }
  .grow {
    flex: 1 1 20rem;
  }
  input[type='text'] {
    width: 100%;
    box-sizing: border-box;
    padding: 0.55rem 0.75rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-bg);
    color: var(--ct-text);
    font: inherit;
  }
  .shared input[type='text'] {
    flex: 1 1 18rem;
    width: auto;
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-sm);
  }

  .work {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(18rem, 2fr);
    gap: var(--ct-space-6);
    align-items: start;
  }
  @media (max-width: 900px) {
    .work {
      grid-template-columns: 1fr;
    }
  }

  .editor-head,
  .editor-foot {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--ct-space-3);
    flex-wrap: wrap;
  }
  .editor-head {
    margin-bottom: var(--ct-space-3);
  }
  .editor-foot {
    margin-top: var(--ct-space-3);
  }
  .editor {
    position: relative;
    display: flex;
    height: 60vh;
    min-height: 22rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-bg);
    overflow: hidden;
    font-family: var(--ct-font-mono);
    font-size: 0.85rem;
    line-height: 1.5;
  }
  .editor:focus-within {
    border-color: var(--ct-focus);
  }
  .editor.dragging {
    border-color: var(--accent);
  }
  .gutter {
    flex: none;
    min-width: 3rem;
    padding: var(--ct-space-2) var(--ct-space-2) var(--ct-space-2) 0;
    overflow: hidden;
    text-align: right;
    color: var(--ct-muted);
    background: var(--ct-surface);
    border-right: 1px solid var(--ct-border);
    user-select: none;
  }
  .gutter .bad {
    color: var(--ct-verdict-broken);
    font-weight: 700;
  }
  textarea {
    flex: 1;
    margin: 0;
    padding: var(--ct-space-2) var(--ct-space-3);
    border: 0;
    outline: none;
    resize: none;
    background: transparent;
    color: var(--ct-text);
    font: inherit;
    line-height: inherit;
    white-space: pre;
    tab-size: 2;
  }
  .drop {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    color: var(--ct-text);
    font-family: var(--ct-font);
    font-weight: 600;
    pointer-events: none;
  }
  .over {
    color: var(--ct-verdict-broken);
  }

  .report .issues,
  .report .tests {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--ct-space-2);
  }
  .issue {
    display: grid;
    gap: var(--ct-space-1);
    padding: var(--ct-space-2) var(--ct-space-3);
    border-left: 3px solid var(--ct-border);
    background: var(--ct-bg);
    border-radius: var(--ct-radius);
    font-size: var(--ct-text-sm);
  }
  .issue.bad {
    border-left-color: var(--ct-verdict-broken);
  }
  .issue.warn {
    border-left-color: var(--ct-verdict-warning);
  }
  .issue .icon {
    font-weight: 700;
  }
  .issue.bad .icon {
    color: var(--ct-verdict-broken);
  }
  .issue.warn .icon {
    color: var(--ct-verdict-warning);
  }
  .link {
    display: inline-flex;
    gap: var(--ct-space-2);
    justify-self: start;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ct-text);
    font: inherit;
    font-family: var(--ct-font-mono);
    cursor: pointer;
  }
  .link:disabled {
    cursor: default;
  }
  .link:not(:disabled):hover .where {
    text-decoration: underline;
  }
  .tests li {
    display: flex;
    gap: var(--ct-space-2);
    align-items: baseline;
  }
  .tests .icon {
    font-weight: 700;
  }
  .tests .passed .icon {
    color: var(--ct-verdict-ok);
  }
  .tests .failed .icon {
    color: var(--ct-verdict-broken);
  }
  .detail {
    display: block;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }

  .banner {
    margin: var(--ct-space-3) 0 0;
    padding: var(--ct-space-2) var(--ct-space-3);
    border-radius: var(--ct-radius);
    border: 1px solid var(--ct-border);
    font-size: var(--ct-text-sm);
  }
  .banner.ok {
    border-color: var(--ct-verdict-ok);
    color: var(--ct-verdict-ok);
  }
  .banner.warn {
    border-color: var(--ct-verdict-warning);
    color: var(--ct-verdict-warning);
  }
  .banner.error {
    border-color: var(--ct-verdict-broken);
    color: var(--ct-verdict-broken);
  }
  .actions {
    display: flex;
    gap: var(--ct-space-3);
    flex-wrap: wrap;
    margin-top: var(--ct-space-6);
  }
  .shared {
    margin-top: var(--ct-space-4);
    padding-top: var(--ct-space-3);
    border-top: 1px solid var(--ct-border);
  }
  .shared p {
    margin: 0 0 var(--ct-space-2);
    font-size: var(--ct-text-sm);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    padding: 0.55rem 1rem;
    border-radius: var(--ct-radius);
    border: 1px solid transparent;
    font: inherit;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    white-space: nowrap;
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .btn-primary {
    background: var(--accent);
    color: var(--ct-bg);
  }
  .btn-primary:not(:disabled):hover {
    background: color-mix(in srgb, var(--accent) 85%, var(--ct-text));
  }
  .btn-ghost {
    background: transparent;
    color: var(--ct-text);
    border-color: var(--ct-border);
  }
  .btn-ghost:not(:disabled):hover {
    background: var(--ct-surface-2);
  }
  .file input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }
  .file {
    position: relative;
  }
  .file:focus-within {
    outline: 2px solid var(--ct-focus);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
</style>
