<!--
  ThemeToggle.svelte : choix du thème (Auto, Clair, Sombre), discret, en bas de toutes les pages.
  Règles et mémoire du choix : lib/theme.svelte.ts.
-->
<script lang="ts">
  import { setTheme, theme, THEME_CHOICES } from '../lib/theme.svelte'
</script>

<div class="theme" role="group" aria-label="Thème de l'affichage">
  {#each THEME_CHOICES as c (c.id)}
    <button
      type="button"
      aria-pressed={theme.preference === c.id}
      title={c.id === 'auto' ? 'Suivre le réglage du système' : undefined}
      onclick={() => setTheme(c.id)}
    >
      <span aria-hidden="true">{c.icon}</span>
      {c.label}
    </button>
  {/each}
</div>

<style>
  /* Dans le flux, en bas de page : jamais par-dessus un contrôle (le Laboratoire remplit l'écran). */
  .theme {
    width: fit-content;
    margin: var(--ct-space-6) auto var(--ct-space-4);
    display: flex;
    gap: 2px;
    padding: 2px;
    background: var(--ct-surface);
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    box-shadow: var(--ct-shadow);
    opacity: 0.75;
    transition: opacity 0.15s;
  }
  .theme:hover,
  .theme:focus-within {
    opacity: 1;
  }
  button {
    padding: 2px var(--ct-space-2);
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--ct-muted);
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
  }
  button:hover {
    color: var(--ct-text);
  }
  button[aria-pressed='true'] {
    background: var(--ct-surface-2);
    color: var(--ct-text);
    font-weight: 600;
  }
  button:focus-visible {
    outline: 2px solid var(--ct-focus);
    outline-offset: 1px;
  }
  @media print {
    .theme {
      display: none;
    }
  }
</style>
