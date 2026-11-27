/**
 * experiments/schema.json (généré par scripts/export_schema.py --yaml) : le schéma que VS Code utilise
 * pour l'autocomplétion des YAML. Ces tests vérifient qu'il accepte tous les vrais fichiers et refuse
 * les fautes les plus courantes, pour qu'il n'affiche jamais une fausse erreur à un auteur.
 */
import Ajv2020 from 'ajv/dist/2020'
import { describe, expect, it } from 'vitest'
import { parse } from 'yaml'
import schema from '../../../experiments/schema.json'

const files = import.meta.glob<string>(['../../../experiments/*.yaml', '../../../experiments/archives/*.yaml'], {
  query: '?raw',
  import: 'default',
  eager: true,
})

// strict: false : le schéma de Pydantic porte des mots-clés d'annotation (discriminator) qu'ajv ignore.
const validate = new Ajv2020({ strict: false, allErrors: true }).compile(schema)
// YAML 1.2 (schéma core). Le moteur lit en YAML 1.1 (PyYAML), mais le mode 1.1 de `yaml` prend les clés
// `y:` et `n:` pour des booléens, ce que PyYAML ne fait pas. Les deux lectures ne diffèrent que sur
// yes/no/on/off et les exposants sans point (« 1e-3 ») : aucun fichier de experiments/ n'en contient.
const load = (text: string) => parse(text)
const errors = () => (validate.errors ?? []).map((e) => `${e.instancePath} ${e.message}`).join('\n')

describe('experiments/schema.json', () => {
  it('couvre au moins les 11 expériences jouables', () => {
    expect(Object.keys(files).filter((f) => !f.includes('/archives/')).length).toBeGreaterThanOrEqual(11)
  })

  for (const [path, text] of Object.entries(files)) {
    it(`accepte ${path.split('/').slice(-2).join('/')}`, () => {
      const ok = validate(load(text))
      expect(ok, errors()).toBe(true)
    })
  }

  const base = load(files['../../../experiments/somme_des.yaml']) as Record<string, unknown>

  it('refuse une clé inconnue au premier niveau (faute de frappe)', () => {
    expect(validate({ ...base, measure: {} })).toBe(false)
    expect(errors()).toContain('must NOT have additional properties')
  })
  it('refuse une clé obligatoire absente', () => {
    const { title: _title, ...rest } = base
    expect(validate(rest)).toBe(false)
  })
  it('refuse un rôle de méthode inconnu', () => {
    const methods = (base.methods as Record<string, unknown>[]).map((m, i) => (i === 0 ? { ...m, role: 'principale' } : m))
    expect(validate({ ...base, methods })).toBe(false)
  })
})
