/**
 * importPrompt.ts : le texte du bouton « Copier le prompt » de l'écran Import (cahier, section 2.7).
 * Aucun appel IA depuis l'application : l'étudiant colle ce texte dans l'assistant de son choix.
 *
 * Les deux exemples sont les vrais fichiers de experiments/ (importés tels quels au moment du build).
 * Méthodes, lois, agrégateurs et fonctions viennent de catalog.gen.ts (généré depuis les registres du
 * moteur par scripts/gen_catalog.py) ; types de vue et réglages `ui` viennent de plot.ts. Rien n'est
 * recopié à la main : une méthode ajoutée au moteur apparaît ici après « gen_catalog.py ».
 */

import exampleSimple from '../../../experiments/somme_des.yaml?raw'
import exampleFull from '../../../experiments/regression_lineaire.yaml?raw'
import { CATALOG, type Catalog, type CatalogMethod } from './catalog.gen'
import { VIEW_TYPES, VIEW_UI_KEYS } from './plot'

/**
 * Types de vue que l'interface dessine mais que le moteur ne sert pas encore : tus dans le prompt, pour
 * qu'un assistant ne les propose pas (la vue retomberait sur le tableau de secours).
 */
export const PENDING_VIEWS: ReadonlySet<string> = new Set<string>()

/**
 * Méthodes du moteur que le prompt ne propose pas : `integrate` exige le générateur `ode` (conditions
 * initiales, `rhs`, `derived`), que le prompt ne décrit pas ; un assistant l'appellerait avec le générateur
 * `random` et le YAML serait refusé. Elle reste dans le catalogue : les YAML qui déclarent `ode` marchent.
 */
export const UNAVAILABLE_METHODS: ReadonlySet<string> = new Set(['integrate'])

/** Une ligne par méthode : appel et arguments, valeurs de `kind`, ce qu'elle fournit, à quoi elle sert. */
export function methodLine(m: CatalogMethod): string {
  const args = m.args.map((a) => (a.default === null ? a.name : `${a.name}=${a.default}`)).join(', ')
  const provides = Object.entries(m.provides)
    .map(([block, keys]) => `${block}: ${keys.join(', ')}`)
    .join(' ; ')
  const kinds = m.kinds.length > 0 ? ` [kind : ${m.kinds.join(' | ')}]` : ''
  const doc = m.doc ? ` — ${m.doc}` : ''
  return `- ${m.name}(${args})${kinds} -> ${provides}${doc}`
}

/** Bloc « ce que le moteur sait faire » du prompt, construit depuis le catalogue. */
export function catalogSection(catalog: Catalog = CATALOG): string {
  const laws = catalog.laws.map((l) => `law('${l.name}')`).join(', ')
  const gen = catalog.generator_functions.map((f) => `${f.signature} (${f.doc})`).join(' ; ')
  const aggs = catalog.aggregators.map((a) => a.signature).join(', ')
  const views = Object.entries(VIEW_TYPES)
    .filter(([t]) => !PENDING_VIEWS.has(t))
    .map(([t, d]) => `- ${t} : ${d}`)
    .join('\n')
  const ui = Object.entries(VIEW_UI_KEYS)
    .filter(([, d]) => ![...PENDING_VIEWS].some((v) => d.startsWith(`${v} :`)))
    .map(([k, d]) => `${k} (${d})`)
    .join(' ; ')
  return `Lois du registre (standardisées : moyenne 0 et variance 1 quand elles existent) : ${laws}.
Fonctions du générateur random : ${gen}.
Fonctions des expressions (liste blanche, seul mot-clé permis : axis) : ${catalog.functions.join(', ')} ; constantes : ${catalog.constants.join(', ')}.
Agrégateurs des mesures (f = expression sur reps.<clé>) : ${aggs}.

Méthodes disponibles (call: et ses arguments, puis ce qu'elle fournit) — n'en inventez aucune :
${catalog.methods.filter((m) => !UNAVAILABLE_METHODS.has(m.name)).map(methodLine).join('\n')}

Types de vue (type:) :
${views}
Réglages facultatifs d'une vue (ui:) : ${ui}.`
}

export function importPrompt(theorem: string): string {
  const subject = theorem.trim() || '<décrivez ici le théorème ou la propriété à illustrer>'
  return `Vous allez écrire un fichier d'expérience YAML pour Crash-Test, une application de révision où la correction d'un QCM est une simulation Monte Carlo. Pour un théorème : on casse une hypothèse, on mesure ce qui cède, on applique la correction.

Sujet : ${subject}

Répondez UNIQUEMENT par le fichier YAML complet, sans texte autour.

Règles du format (schema_version: 1) :
- Clés de premier niveau : schema_version, id, title, discipline, level, concepts, theorem, equation, params, hypotheses, counterexamples, generator, methods, measures, challenges, auto_sweep, views, questions. Aucune autre clé.
- Toutes les chaînes de texte entre guillemets. Textes en français, en vouvoyant le lecteur.
- level : "1" (Découverte), "2" (Intermédiaire) ou "3" (Avancé).
- Hypothèses : type continuous (range, step), choice (options avec label et law: ou expr:) ou boolean ; healthy_value, label, category, affects, why, when_broken, statement_tex obligatoires.
- Paramètres : type number (default, min, max, step, sweep_values facultatif) ou boolean.
- Générateur random : n, repeat (1000 au plus), variables (30 au plus), chaque variable est une expression (lois et fonctions ci-dessous).
- Méthodes : exactement 1 role: method, au plus 1 role: correction, au plus 2 role: alternative, 4 au plus. Chaque correction et alternative a un explain et la liste repairs des hypothèses qu'elle répare.
- Mesures : agg (un agrégateur ci-dessous), une seule primary: true ; target (nombre ou base), direction (below, above, both), ok_within, broken_beyond et texts {ok, warning, broken} avec {value}, jamais un chiffre écrit en dur.
- Espace de noms des expressions : p.<id> paramètre, h.<id> hypothèse, noms nus = variables du générateur, m.<mesure>, s.<mesure> ("ok", "warning", "broken"), base.<mesure>.
- Pas de boucle, pas d'attribut commençant par _, expressions de 300 caractères au plus, fichier de 64 Ko au plus.
- Au moins 3 questions (misconception et diagnostic_auto), comme dans les exemples.

${catalogSection()}

Le fichier doit vérifier : à l'état sain, la mesure primaire de la méthode principale est Fiable ; chaque correction ramène à Fiable ou Fragile les hypothèses de son repairs ; chaque contre-exemple rompt au moins une mesure ; chaque hypothèse a why et when_broken.

Exemple simple (niveau 1) :
\`\`\`yaml
${exampleSimple.trim()}
\`\`\`

Exemple complet (régression linéaire) :
\`\`\`yaml
${exampleFull.trim()}
\`\`\`
`
}
