<!--
  MathText.svelte : un texte de mesure où les puissances de dix (« 10^−13,8 ») sont rendues en vrai exposant.
  Rend les formules entre dollars ($…$, $$…$$) et les puissances de dix. Règles et garde-fous : lib/mathText.ts.
-->
<script lang="ts">
  import { splitRich } from '../lib/mathText'
  import Tex from './Tex.svelte'

  let { text }: { text: string } = $props()

  const parts = $derived(splitRich(text))
</script>

{#each parts as part, i (i)}{#if part.kind === 'tex'}<Tex tex={part.tex} display={part.display === true} />{:else}{part.value}{/if}{/each}
