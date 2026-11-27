<!--
  Tex.svelte : une formule LaTeX rendue par KaTeX (R3).
  Une formule invalide n'interrompt jamais l'écran : KaTeX l'affiche en rouge (throwOnError: false).

  Usage : <Tex tex={'\\Delta t \\ll T_0'} />   ou   <Tex tex={...} display />
-->
<script lang="ts">
  import katex from 'katex'
  import 'katex/dist/katex.min.css'

  interface Props {
    tex: string
    /** Formule centrée sur sa propre ligne (équation dynamique). */
    display?: boolean
  }

  let { tex, display = false }: Props = $props()

  const html = $derived(
    katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: 'ignore', output: 'htmlAndMathml' }),
  )
</script>

<!-- HTML produit par KaTeX à partir du YAML validé (jamais d'une saisie libre). -->
<span class={display ? 'tex display' : 'tex'}>{@html html}</span>

<style>
  .tex.display {
    display: block;
    overflow-x: auto;
    overflow-y: hidden;
  }
</style>
