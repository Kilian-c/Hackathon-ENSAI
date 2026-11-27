import { describe, expect, it } from 'vitest'
import { ApiError } from '../../lib/executor'
import {
  IMPORT_PROMPT,
  MAX_YAML_CHARS,
  checkYaml,
  inputProblem,
  isMissingRoute,
  issuePlace,
  issuesFromError,
  lineCount,
  lineRange,
  looksLikeYaml,
  promptExample,
  sortIssues,
} from './importRules'

describe('import : texte reçu', () => {
  it('refuse un texte vide ou trop long', () => {
    expect(inputProblem('   ')).toBe('Collez ou déposez un fichier YAML.')
    expect(inputProblem('a'.repeat(MAX_YAML_CHARS + 1))).toMatch(/64 au plus/)
    expect(inputProblem('id: "x"')).toBeNull()
  })

  it('reconnaît un fichier YAML déposé', () => {
    expect(looksLikeYaml('exp.yaml', '')).toBe(true)
    expect(looksLikeYaml('exp.YML', '')).toBe(true)
    expect(looksLikeYaml('notes.txt', 'text/plain')).toBe(true)
    expect(looksLikeYaml('image.png', 'image/png')).toBe(false)
  })
})

describe('import : erreurs du moteur', () => {
  const body = {
    detail: {
      message: "Fichier d'expérience invalide.",
      issues: [
        { line: 31, path: 'hypotheses.x.healty_value', message: 'Champ inconnu.' },
        { line: 28, path: 'hypotheses.x.healthy_value', message: 'Champ obligatoire manquant.' },
      ],
    },
  }

  it('lit les erreurs ligne par ligne dans une réponse 422 de /api/run', () => {
    const issues = issuesFromError(new ApiError('…', 422, body))
    expect(issues).toHaveLength(2)
    expect(sortIssues(issues ?? []).map((i) => i.line)).toEqual([28, 31])
  })

  it("ignore les autres erreurs (moteur injoignable, 500, 422 d'une autre forme)", () => {
    expect(issuesFromError(new ApiError('…', 0))).toBeNull()
    expect(issuesFromError(new ApiError('…', 500, body))).toBeNull()
    expect(issuesFromError(new ApiError('…', 422, { detail: [{ loc: ['body'], msg: 'x' }] }))).toBeNull()
    expect(issuesFromError(new Error('…'))).toBeNull()
  })

  it('dit « vers la ligne » pour une erreur de syntaxe (le parseur la voit parfois une ligne plus bas)', () => {
    expect(issuePlace({ line: 38, path: 'a', message: 'Champ inconnu.' })).toBe('Ligne 38')
    expect(issuePlace({ line: 61, path: '', message: 'YAML invalide : expected <block end>' })).toBe('Vers la ligne 61')
    expect(issuePlace({ line: null, path: '', message: 'Fichier trop gros.' })).toBe('Fichier entier')
  })

  it('reconnaît une route /api/validate absente', () => {
    expect(isMissingRoute(new ApiError('…', 404))).toBe(true)
    expect(isMissingRoute(new ApiError('…', 405))).toBe(true)
    expect(isMissingRoute(new ApiError('…', 422))).toBe(false)
  })
})

describe("import : éditeur et prompt", () => {
  it('sélectionne une ligne et compte les lignes', () => {
    const text = 'a: 1\nbb: 2\nccc: 3'
    expect(lineRange(text, 2)).toEqual([5, 10])
    expect(text.slice(...lineRange(text, 3))).toBe('ccc: 3')
    expect(lineRange(text, 99)).toEqual(lineRange(text, 3))
    expect(lineCount(text)).toBe(3)
  })

  it("le prompt contient un exemple complet, sans le texte d'accroche", () => {
    const example = promptExample()
    expect(example.startsWith('schema_version: 1')).toBe(true)
    expect(example).toContain('questions:')
    expect(example).not.toContain('Le théorème que je veux')
    expect(IMPORT_PROMPT).toContain('vouvoiement')
    // Les barres obliques inverses du LaTeX restent simples dans le texte copié.
    expect(example).toContain("'S_k = X_1 + X_2 + \\cdots + X_k'")
  })
})

describe('import : validation', () => {
  const result = { measures: {} } as unknown as import('../../lib/types.gen').RunResult
  const issues422 = new ApiError('…', 422, {
    detail: { message: 'x', issues: [{ line: 3, path: 'id', message: 'Champ obligatoire manquant.' }] },
  })

  it('utilise /api/validate quand la route existe, puis prévisualise', async () => {
    const client = {
      validate: async () => ({ ok: true, errors: [], warnings: [], tests: [{ id: 1, name: 'État sain', passed: true, detail: null }] }),
      run: async () => result,
    }
    const c = await checkYaml(client, 'yaml')
    expect(c).toMatchObject({ mode: 'validate', ok: true, preview: result })
    expect(c.tests).toHaveLength(1)
  })

  it('se replie sur /api/run tant que /api/validate manque', async () => {
    const missing = { validate: async () => Promise.reject(new ApiError('…', 404)) }
    expect(await checkYaml({ ...missing, run: async () => result }, 'yaml')).toMatchObject({ mode: 'run', ok: true, preview: result })
    const refused = await checkYaml({ ...missing, run: async () => Promise.reject(issues422) }, 'yaml')
    expect(refused).toMatchObject({ mode: 'run', ok: false, preview: null })
    expect(refused.errors[0].line).toBe(3)
  })

  it('laisse remonter une panne du moteur', async () => {
    const down = { validate: async () => Promise.reject(new ApiError('injoignable', 0)), run: async () => result }
    await expect(checkYaml(down, 'yaml')).rejects.toThrow('injoignable')
  })
})
