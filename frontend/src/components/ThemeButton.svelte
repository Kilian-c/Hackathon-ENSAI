<!--
  ThemeButton.svelte : bascule rapide clair / sombre, une petite icône ronde à placer dans l'en-tête d'une page.
  Elle montre le thème vers lequel on passe (soleil dans le thème sombre, lune dans le thème clair) et pose un
  choix explicite. Le choix « Auto » reste au pied de page (ThemeToggle.svelte). Règles : lib/theme.svelte.ts.
-->
<script lang="ts">
  import { setTheme, theme } from '../lib/theme.svelte'

  /** Pousse le bouton à droite de sa ligne quand rien d'autre ne le fait. */
  let { push = false }: { push?: boolean } = $props()

  const toLight = $derived(theme.resolved === 'dark')
  const label = $derived(toLight ? 'Passer au thème clair' : 'Passer au thème sombre')
</script>

<button
  type="button"
  class="theme-btn"
  class:push
  aria-label={label}
  title={label}
  onclick={() => setTheme(toLight ? 'light' : 'dark')}
>
  <span aria-hidden="true">{toLight ? '☀' : '☾'}</span>
</button>

<style>
  .theme-btn {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: 1.9rem;
    height: 1.9rem;
    padding: 0;
    border: 1px solid var(--ct-border);
    border-radius: 999px;
    background: var(--ct-surface);
    color: var(--ct-muted);
    font: inherit;
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
  }
  .theme-btn:hover {
    color: var(--ct-text);
    border-color: var(--ct-muted);
  }
  .theme-btn:focus-visible {
    outline: 2px solid var(--ct-focus);
    outline-offset: 2px;
  }
  .push {
    margin-left: auto;
  }
  @media print {
    .theme-btn {
      display: none;
    }
  }
</style>
