<!--
  ImportView.svelte : l'écran Import (R4), ouvert par ?import. Cahier, « Créer une expérience sans payer d'API ».
  1. Copier le prompt (à coller dans un assistant IA externe : aucun appel IA depuis l'application).
  2. Coller ou déposer un YAML, le vérifier : erreurs ligne par ligne (POST /api/validate, ou /api/run en repli).
  3. Prévisualiser les mesures de l'état par défaut (vue de secours MeasuresTable).
  Les règles sont dans components/import/importRules.ts.
  TODO(passation) : ouvrir le YAML importé dans le Laboratoire et le lien de partage (Supabase) ne sont pas
  faits : le Laboratoire a besoin de l'ExperimentSpec, qu'aucune route ne renvoie pour un raw_content.
-->
<script lang="ts">
  import MeasuresTable from './MeasuresTable.svelte'
  import { api } from '../lib/executor'
  import {
    IMPORT_PROMPT,
    MAX_YAML_CHARS,
    checkYaml,
    inputProblem,
    isSyntaxIssue,
    issuePlace,
    lineCount,
    lineRange,
    looksLikeYaml,
    promptExample,
    type ImportCheck,
  } from './import/importRules'
  import type { ValidateIssue } from '../lib/types.gen'

  const DRAFT_KEY = 'crash-test.import.draft'

  function readDraft(): string {
    try {
      return globalThis.localStorage?.getItem(DRAFT_KEY) ?? ''
    } catch {
      return ''
    }
  }

  let text = $state(readDraft())
  let check = $state<ImportCheck | null>(null)
  let checkedText = $state<string | null>(null)
  let busy = $state(false)
  let failure = $state<string | null>(null)
  let copyStatus = $state<'idle' | 'copied' | 'failed'>('idle')
  let dragging = $state(false)
  let editor = $state<HTMLTextAreaElement | null>(null)
  let gutter = $state<HTMLPreElement | null>(null)

  const problem = $derived(inputProblem(text))
  const lines = $derived(lineCount(text))
  const sizeKo = $derived((text.length / 1024).toFixed(1).replace('.', ','))
  const outdated = $derived(check !== null && checkedText !== text)
  const errorLines = $derived(new Set((check?.errors ?? []).map((i) => i.line).filter((l) => l !== null)))
  const allMethods = $derived(new Set(check?.preview?.methods.map((m) => m.id) ?? []))

  $effect(() => {
    // Brouillon gardé dans ce navigateur seulement (confort : rien n'est envoyé).
    const value = text
    try {
      globalThis.localStorage?.setItem(DRAFT_KEY, value)
    } catch {
      /* stockage refusé : tant pis, l'écran marche sans */
    }
  })

  async function copyPrompt(): Promise<void> {
    try {
      await navigator.clipboard.writeText(IMPORT_PROMPT)
      copyStatus = 'copied'
    } catch {
      copyStatus = 'failed'
    }
  }

  async function verify(): Promise<void> {
    if (problem || busy) return
    busy = true
    failure = null
    const sent = text
    try {
      check = await checkYaml(api, sent)
      checkedText = sent
    } catch (err) {
      check = null
      failure = err instanceof Error ? err.message : 'Une erreur inattendue est survenue.'
    } finally {
      busy = false
    }
  }

  function goToLine(issue: ValidateIssue): void {
    if (!editor || issue.line === null) return
    const [start, end] = lineRange(text, issue.line)
    editor.focus()
    editor.setSelectionRange(start, end)
    const lineHeight = parseFloat(getComputedStyle(editor).lineHeight) || 20
    // La ligne visée au tiers de la hauteur de l'éditeur, pour garder un peu de contexte au-dessus.
    editor.scrollTop = Math.max(0, (issue.line - 1) * lineHeight - editor.clientHeight / 3)
    syncGutter()
  }

  function syncGutter(): void {
    if (gutter && editor) gutter.scrollTop = editor.scrollTop
  }

  async function readFile(file: File | undefined): Promise<void> {
    if (!file) return
    if (!looksLikeYaml(file.name, file.type)) {
      failure = `« ${file.name} » n'est pas un fichier YAML (.yaml ou .yml).`
      return
    }
    if (file.size > MAX_YAML_CHARS * 4) {
      failure = `« ${file.name} » est trop volumineux : le moteur accepte 64 Ko au plus.`
      return
    }
    failure = null
    text = await file.text()
    check = null
  }

  function onDrop(event: DragEvent): void {
    event.preventDefault()
    dragging = false
    void readFile(event.dataTransfer?.files[0])
  }

  function onPick(event: Event): void {
    const input = event.currentTarget as HTMLInputElement
    void readFile(input.files?.[0])
    input.value = ''
  }

  function loadExample(): void {
    text = promptExample()
    check = null
    failure = null
  }
</script>

<main class="import">
  <header>
    <a class="back" href="?">← Accueil</a>
    <h1>Importer une expérience</h1>
    <p class="muted">
      Une expérience est un seul fichier YAML. Faites-le écrire par l'assistant IA de votre choix, puis vérifiez-le
      ici : le moteur le lit, signale chaque erreur avec sa ligne et lance une première simulation.
    </p>
  </header>

  <section class="card step" aria-labelledby="etape-1">
    <h2 id="etape-1"><span class="num">1</span> Copiez le prompt</h2>
    <p>
      Collez-le dans un assistant IA, en ajoutant à la fin le théorème que vous voulez illustrer. Il contient les
      règles du format et un exemple complet.
    </p>
    <div class="row">
      <button type="button" class="button primary" onclick={copyPrompt}>Copier le prompt</button>
      {#if copyStatus === 'copied'}
        <span class="ok" role="status">Prompt copié.</span>
      {:else if copyStatus === 'failed'}
        <span class="error" role="status">La copie a été refusée : sélectionnez le texte ci-dessous.</span>
      {/if}
    </div>
    <details open={copyStatus === 'failed'}>
      <summary>Voir le prompt</summary>
      <textarea class="prompt" readonly rows="10" aria-label="Prompt à copier" value={IMPORT_PROMPT}></textarea>
    </details>
  </section>

  <section class="card step" aria-labelledby="etape-2">
    <h2 id="etape-2"><span class="num">2</span> Collez ou déposez le YAML</h2>
    <div class="row">
      <label class="button">
        Choisir un fichier
        <input type="file" accept=".yaml,.yml,text/yaml,text/plain" onchange={onPick} hidden />
      </label>
      <button type="button" class="button" onclick={loadExample}>Charger l'exemple</button>
      <span class="muted size">{lines} {lines > 1 ? 'lignes' : 'ligne'} · {sizeKo} Ko sur 64</span>
    </div>

    <div
      class="editor"
      class:dragging
      role="group"
      aria-label="Éditeur YAML"
      ondragover={(e) => {
        e.preventDefault()
        dragging = true
      }}
      ondragleave={() => (dragging = false)}
      ondrop={onDrop}
    >
      <pre class="gutter" bind:this={gutter} aria-hidden="true">{#each { length: lines } as _, i (i)}<span
            class:bad={errorLines.has(i + 1)}>{i + 1}</span
          >{'\n'}{/each}</pre>
      <textarea
        bind:this={editor}
        bind:value={text}
        onscroll={syncGutter}
        spellcheck="false"
        autocomplete="off"
        wrap="off"
        placeholder="schema_version: 1&#10;id: &quot;mon-experience&quot;&#10;…  (ou déposez un fichier .yaml ici)"
        aria-label="Contenu YAML de l'expérience"
      ></textarea>
    </div>

    <div class="row">
      <button type="button" class="button primary" onclick={verify} disabled={problem !== null || busy}>
        {busy ? 'Vérification…' : 'Vérifier'}
      </button>
      {#if problem && text !== ''}
        <span class="error">{problem}</span>
      {:else if outdated}
        <span class="muted">Le texte a changé depuis la dernière vérification.</span>
      {/if}
    </div>
    {#if failure}
      <p class="error" role="alert">{failure}</p>
    {/if}
  </section>

  {#if check}
    <section class="card step" aria-labelledby="etape-3" aria-live="polite">
      <h2 id="etape-3"><span class="num">3</span> Résultat</h2>

      {#if check.ok}
        <p class="verdict ok"><strong>✓ Fichier accepté par le moteur.</strong></p>
      {:else}
        <p class="verdict error">
          <strong>✗ {check.errors.length} {check.errors.length > 1 ? 'erreurs' : 'erreur'}</strong> : cliquez sur une
          ligne pour la retrouver dans l'éditeur.
        </p>
        <ul class="issues">
          {#each check.errors as issue, i (i)}
            <li>
              <button type="button" class="link" onclick={() => goToLine(issue)} disabled={issue.line === null}>
                {issuePlace(issue)}
              </button>
              {#if issue.path}<code>{issue.path}</code>{/if}
              <span>{issue.message}</span>
              {#if isSyntaxIssue(issue)}
                <span class="muted">(la faute peut aussi être sur la ligne juste au-dessus)</span>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}

      {#if check.warnings.length > 0}
        <h3>Avertissements</h3>
        <ul class="issues">
          {#each check.warnings as issue, i (i)}
            <li>
              <button type="button" class="link" onclick={() => goToLine(issue)} disabled={issue.line === null}>
                {issuePlace(issue)}
              </button>
              <span>{issue.message}</span>
            </li>
          {/each}
        </ul>
      {/if}

      {#if check.mode === 'validate' && check.tests.length > 0}
        <h3>Tests scientifiques</h3>
        <ul class="tests">
          {#each check.tests as t (t.id)}
            <li class:failed={!t.passed}>
              <span aria-hidden="true">{t.passed ? '✓' : '✗'}</span>
              <span class="sr">{t.passed ? 'Réussi' : 'Échoué'} :</span>
              Test {t.id} · {t.name}{#if t.detail}<span class="muted"> : {t.detail}</span>{/if}
            </li>
          {/each}
        </ul>
      {:else if check.mode === 'run'}
        <p class="muted">
          Seule la lecture du fichier a été vérifiée : les tests scientifiques (état sain Fiable, corrections qui
          réparent, contre-exemples qui cassent…) ne sont pas encore disponibles sur ce moteur.
        </p>
      {/if}

      {#if check.preview}
        <h3>Prévisualisation : l'état par défaut</h3>
        <MeasuresTable result={check.preview} methodsOn={allMethods} />
        {#each check.preview.warnings as w (w.code)}
          <p class="muted">⚠ {w.text}</p>
        {/each}
      {/if}
    </section>
  {/if}
</main>

<style>
  .import {
    max-width: 60rem;
    margin: 0 auto;
    padding: var(--ct-space-4) var(--ct-space-6) var(--ct-space-8);
    display: grid;
    gap: var(--ct-space-4);
  }
  h1 {
    margin: var(--ct-space-2) 0;
    font-size: var(--ct-text-xl);
  }
  h2 {
    margin: 0 0 var(--ct-space-3);
    font-size: var(--ct-text-lg);
    display: flex;
    align-items: center;
    gap: var(--ct-space-2);
  }
  h3 {
    margin: var(--ct-space-4) 0 var(--ct-space-2);
    font-size: var(--ct-text-md);
  }
  .back {
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .muted {
    color: var(--ct-muted);
  }
  .error {
    color: var(--ct-verdict-broken);
  }
  .ok {
    color: var(--ct-verdict-ok);
  }
  .card {
    padding: var(--ct-space-4);
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius-lg);
  }
  .num {
    display: inline-grid;
    place-items: center;
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 50%;
    border: 1px solid var(--ct-border);
    font-size: var(--ct-text-sm);
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--ct-space-2);
    margin: var(--ct-space-2) 0;
  }
  .size {
    margin-left: auto;
    font-size: var(--ct-text-sm);
  }
  .button {
    display: inline-block;
    padding: var(--ct-space-2) var(--ct-space-3);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-surface-2);
    color: var(--ct-text);
    font: inherit;
    font-size: var(--ct-text-sm);
    cursor: pointer;
  }
  .button.primary {
    border-color: var(--ct-role-method);
    color: var(--ct-role-method);
  }
  .button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .link {
    padding: 0;
    border: none;
    background: none;
    color: var(--ct-role-method);
    font: inherit;
    font-weight: 600;
    text-decoration: underline;
    cursor: pointer;
  }
  .link:disabled {
    color: var(--ct-text);
    text-decoration: none;
    cursor: default;
  }
  details summary {
    cursor: pointer;
    color: var(--ct-muted);
    font-size: var(--ct-text-sm);
  }
  .prompt {
    width: 100%;
    box-sizing: border-box;
    margin-top: var(--ct-space-2);
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-sm);
    background: var(--ct-bg);
    color: var(--ct-text);
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
  }

  .editor {
    display: flex;
    height: 26rem;
    border: 1px solid var(--ct-border);
    border-radius: var(--ct-radius);
    background: var(--ct-bg);
    overflow: hidden;
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-sm);
    line-height: 1.5;
  }
  .editor.dragging {
    border: 2px dashed var(--ct-role-method);
  }
  .gutter {
    margin: 0;
    padding: var(--ct-space-2);
    min-width: 2.5rem;
    text-align: right;
    color: var(--ct-muted);
    background: var(--ct-surface);
    border-right: 1px solid var(--ct-border);
    overflow: hidden;
    user-select: none;
    font: inherit;
    line-height: inherit;
  }
  .gutter .bad {
    color: var(--ct-verdict-broken);
    font-weight: 700;
  }
  .editor textarea {
    flex: 1;
    min-width: 0;
    margin: 0;
    padding: var(--ct-space-2);
    border: none;
    resize: none;
    background: transparent;
    color: var(--ct-text);
    font: inherit;
    line-height: inherit;
    white-space: pre;
    overflow: auto;
  }
  .editor textarea:focus {
    outline: 2px solid var(--ct-focus);
    outline-offset: -2px;
  }

  .verdict {
    margin: 0 0 var(--ct-space-2);
  }
  .issues,
  .tests {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: var(--ct-space-2);
  }
  .issues li {
    display: flex;
    flex-wrap: wrap;
    gap: var(--ct-space-2);
    align-items: baseline;
  }
  .issues code {
    font-family: var(--ct-font-mono);
    font-size: var(--ct-text-sm);
    color: var(--ct-muted);
  }
  .tests li {
    color: var(--ct-verdict-ok);
  }
  .tests li.failed {
    color: var(--ct-verdict-broken);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
