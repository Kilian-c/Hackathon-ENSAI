<!--
  MathText.svelte : un texte de mesure où les puissances de dix (« 10^−13,8 ») sont rendues en vrai exposant.
  Règles et garde-fous : lib/mathText.ts (motif strictement numérique ; le reste du texte est affiché tel quel).
-->
<script lang="ts">
  import { splitPowers } from '../lib/mathText'
  import Tex from './Tex.svelte'

  let { text }: { text: string } = $props()

  const parts = $derived(splitPowers(text))
</script>

{#each parts as part, i (i)}{#if part.kind === 'tex'}<Tex tex={part.tex} />{:else}{part.value}{/if}{/each}
