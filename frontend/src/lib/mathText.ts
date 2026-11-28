/**
 * mathText.ts : puissances de dix dans les textes de mesure (« erreur relative de 10^−13,8 »).
 *
 * Les textes des mesures (`texts` d'un YAML) s'affichent en texte simple. Quand une mesure est un logarithme,
 * le YAML écrit `10^{value}` et le moteur remplace `{value}` par le nombre : « 10^−13,8 ». L'interface rend ce
 * motif, et lui seul, en vrai exposant (KaTeX). Le motif est strictement numérique (un signe facultatif, des
 * chiffres, une virgule décimale facultative) : aucun autre texte n'est interprété, et rien d'autre que des
 * chiffres n'est jamais passé à KaTeX.
 */

export type MathPart = { kind: 'text'; value: string } | { kind: 'tex'; tex: string }

/** `10^` (pas à la suite d'un chiffre : « 210^3 » n'est pas 2 fois 10³), un signe facultatif (- ou −), des chiffres. */
const POWER = /(?<![\d.,])10\^\s?([−-]?\d+(?:,\d+)?)/g

/** Exposant en LaTeX : le signe moins typographique, et `{,}` pour que la virgule décimale ne s'espace pas. */
export function exponentTex(exponent: string): string {
  return exponent.replace('−', '-').replace(',', '{,}')
}

/** Découpe un texte en morceaux de texte simple et en puissances de dix (à rendre en formule). */
export function splitPowers(text: string): MathPart[] {
  const parts: MathPart[] = []
  let last = 0
  for (const match of text.matchAll(POWER)) {
    const start = match.index ?? 0
    if (start > last) parts.push({ kind: 'text', value: text.slice(last, start) })
    parts.push({ kind: 'tex', tex: `10^{${exponentTex(match[1])}}` })
    last = start + match[0].length
  }
  if (last < text.length) parts.push({ kind: 'text', value: text.slice(last) })
  return parts
}
