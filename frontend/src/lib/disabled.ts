/**
 * disabled.ts : évalue `disabled_when` d'une hypothèse (un contrôle grisé, avec sa phrase `disabled_text`).
 *
 * Sous-ensemble sûr des expressions du moteur, sans `eval` : constantes (True, False, nombres, textes),
 * `h.<id>` et `p.<id>` (état courant), `==  !=  <  <=  >  >=`, `not`, `and`, `or` et les parenthèses.
 * Une expression que l'on ne sait pas lire n'interdit rien (null) : le contrôle reste utilisable.
 * Usage typique : `disabled_when: "True"` pour une hypothèse que l'on affiche sans pouvoir la casser
 * (par exemple la mesurabilité d'une fonction, qui ne se simule pas).
 */

type Value = number | boolean | string | undefined

export interface DisabledState {
  hypotheses: Readonly<Record<string, Value>>
  params: Readonly<Record<string, Value>>
}

const TOKEN = /\s*(?:(\d+(?:\.\d+)?)|('[^']*'|"[^"]*")|([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?)|(==|!=|<=|>=|<|>|\(|\)))/y

function tokenize(text: string): string[] {
  const tokens: string[] = []
  TOKEN.lastIndex = 0
  while (TOKEN.lastIndex < text.length) {
    const match = TOKEN.exec(text)
    if (!match) {
      if (/^\s*$/.test(text.slice(TOKEN.lastIndex))) break
      throw new Error('caractère inattendu')
    }
    tokens.push(match[1] ?? match[2] ?? match[3] ?? match[4])
  }
  return tokens
}

class Parser {
  private pos = 0
  constructor(
    private readonly tokens: string[],
    private readonly state: DisabledState,
  ) {}

  parse(): Value {
    const value = this.or()
    if (this.pos < this.tokens.length) throw new Error('fin attendue')
    return value
  }

  private peek(): string | undefined {
    return this.tokens[this.pos]
  }

  private take(): string {
    const token = this.tokens[this.pos++]
    if (token === undefined) throw new Error('expression incomplète')
    return token
  }

  private or(): Value {
    let left = this.and()
    while (this.peek() === 'or') {
      this.take()
      const right = this.and()
      left = Boolean(left) || Boolean(right)
    }
    return left
  }

  private and(): Value {
    let left = this.not()
    while (this.peek() === 'and') {
      this.take()
      const right = this.not()
      left = Boolean(left) && Boolean(right)
    }
    return left
  }

  private not(): Value {
    if (this.peek() === 'not') {
      this.take()
      return !this.not()
    }
    return this.comparison()
  }

  private comparison(): Value {
    const left = this.atom()
    const op = this.peek()
    if (op === '==' || op === '!=' || op === '<' || op === '<=' || op === '>' || op === '>=') {
      this.take()
      const right = this.atom()
      switch (op) {
        case '==':
          return left === right
        case '!=':
          return left !== right
        default: {
          if (typeof left !== 'number' || typeof right !== 'number') throw new Error('comparaison de nombres attendue')
          return op === '<' ? left < right : op === '<=' ? left <= right : op === '>' ? left > right : left >= right
        }
      }
    }
    return left
  }

  private atom(): Value {
    const token = this.take()
    if (token === '(') {
      const value = this.or()
      if (this.take() !== ')') throw new Error('parenthèse attendue')
      return value
    }
    if (/^\d/.test(token)) return Number(token)
    if (token.startsWith("'") || token.startsWith('"')) return token.slice(1, -1)
    if (token === 'True' || token === 'true') return true
    if (token === 'False' || token === 'false') return false
    const [scope, name] = token.split('.')
    if (scope === 'h' && name) return this.state.hypotheses[name]
    if (scope === 'p' && name) return this.state.params[name]
    throw new Error(`nom inconnu : ${token}`)
  }
}

/** vrai / faux ; null si l'expression est vide ou illisible (le contrôle reste alors utilisable). */
export function isDisabled(expression: string | null | undefined, state: DisabledState): boolean | null {
  if (!expression || !expression.trim()) return null
  try {
    return Boolean(new Parser(tokenize(expression), state).parse())
  } catch {
    return null
  }
}

/** Phrase à afficher quand le contrôle est grisé : celle du YAML, ou une phrase par défaut. */
export function disabledNotice(
  hypothesis: { disabled_when?: string | null; disabled_text?: string | null },
  state: DisabledState,
): string | null {
  if (isDisabled(hypothesis.disabled_when, state) !== true) return null
  return hypothesis.disabled_text?.trim() || 'Cette hypothèse ne peut pas être modifiée ici.'
}
