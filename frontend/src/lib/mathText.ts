/**
 * mathText.ts : puissances de dix dans les textes de mesure (« erreur relative de 10^−13,8 »).
 *
 * Les textes des mesures (`texts` d'un YAML) s'affichent en texte simple. Quand une mesure est un logarithme,
 * le YAML écrit `10^{value}` et le moteur remplace `{value}` par le nombre : « 10^−13,8 ». L'interface rend ce
 * motif, et lui seul, en vrai exposant (KaTeX). Le motif est strictement numérique (un signe facultatif, des
 * chiffres, une virgule décimale facultative) : aucun autre texte n'est interprété, et rien d'autre que des
 * chiffres n'est jamais passé à KaTeX.
 */

export type MathPart = { kind: 'text'; value: string } | { kind: 'tex'; tex: string; display?: boolean }

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

/**
 * Formules entre dollars dans un texte de contenu (énoncé d'un théorème, `why`, `when_broken`, explications) :
 * `$\int_0^1 f$` en ligne, `$$\lim_{n} \int f_n$$` centrée, `\$` pour un vrai signe dollar. Un dollar ouvrant
 * est suivi d'un caractère non blanc et un dollar fermant précédé d'un caractère non blanc : « 5 $ et 6 $ »
 * n'est pas une formule. Le texte hors formule passe ensuite par `splitPowers` (10^−4). La formule est rendue
 * par KaTeX en mode sûr (aucune commande `\href`, `\input`...) ; une formule invalide s'affiche en rouge.
 */
const DOLLARS = /(?<!\\)\$\$(?=\S)([^$]*?\S)\$\$|(?<!\\)\$(?=\S)([^$\n]*?\S)\$(?!\d)/g

function unescapeDollars(text: string): string {
  return text.replace(/\\\$/g, '$')
}

export function splitRich(text: string): MathPart[] {
  const parts: MathPart[] = []
  const pushText = (chunk: string): void => {
    if (!chunk) return
    for (const part of splitPowers(chunk)) {
      parts.push(part.kind === 'text' ? { kind: 'text', value: unescapeDollars(part.value) } : part)
    }
  }
  let last = 0
  for (const match of text.matchAll(DOLLARS)) {
    const start = match.index ?? 0
    pushText(text.slice(last, start))
    const display = match[1] !== undefined
    parts.push({ kind: 'tex', tex: (match[1] ?? match[2]).trim(), display })
    last = start + match[0].length
  }
  pushText(text.slice(last))
  return parts
}
