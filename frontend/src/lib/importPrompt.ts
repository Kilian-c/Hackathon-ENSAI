/**
 * importPrompt.ts : le texte du bouton « Copier le prompt » de l'écran Import (cahier, section 2.7).
 * Aucun appel IA depuis l'application : l'étudiant colle ce texte dans l'assistant de son choix.
 *
 * Les deux exemples sont les vrais fichiers de experiments/ (importés tels quels au moment du build).
 * METHODS recopie le registre du moteur (backend/methods) : à compléter si une méthode est ajoutée.
 */

import exampleSimple from '../../../experiments/somme_des.yaml?raw'
import exampleFull from '../../../experiments/regression_lineaire.yaml?raw'

const METHODS = `
- classifier(score, label, threshold, kind) -> reps: error, best_error, excess, sens, spec, accuracy, auc ; example: score_neg, score_pos ; curves: fpr, tpr
- clt_mean(x, sigma, rho, kind, alpha) -> reps: z, inside ; example: x ; curves: k, paths
- ols_ci(x, y, truth, alpha, se_type) -> reps: est, low, high, hit, width, bp_pvalue ; example: x, y, y_hat, y_mean, resid, leverage, cooks_d
- ols_two(x1, x2, y, signal, truth, alpha, kind) -> reps: est, low, high, hit, reject, width, vif, pred_error ; example: x1, x2, y, y_hat, resid
- one_sample_test(x0, x1, alpha, kind) -> reps: reject, reject_h1, pvalue, stat ; example: x0
- pairwise_tests(y, groups, alpha, kind) -> reps: any_reject, n_reject, max_stat ; example: group, y, group_mean
- regressor(x, y, kind, slope) -> reps: slope, sse, excess ; example: x, y, y_hat
- statistic(x, kind, continuity) -> reps: stat ; example: x
`.trim()

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
- Générateur random : n, repeat (1000 au plus), variables (30 au plus), chaque variable est une expression. Lois disponibles : law('normal'), law('uniform'), law('exponential'), law('student_2'), law('cauchy'), law('bimodal'), et normal, uniform, bernoulli, ar1(base, rho). @h.<id> donne la loi ou l'expression de l'option choisie.
- Méthodes : exactement 1 role: method, au plus 1 role: correction, au plus 2 role: alternative, 4 au plus. Chaque correction et alternative a un explain et la liste repairs des hypothèses qu'elle répare.
- Mesures : agg (rate, mean, bias, rmse, sd, var, median, quantile, first, summary sur reps.<clé>), une seule primary: true ; target (nombre ou base), direction (below, above, both), ok_within, broken_beyond et texts {ok, warning, broken} avec {value}, jamais un chiffre écrit en dur.
- Espace de noms des expressions : p.<id> paramètre, h.<id> hypothèse, noms nus = variables du générateur, m.<mesure>, s.<mesure> ("ok", "warning", "broken"), base.<mesure>.
- Pas de boucle, pas d'attribut commençant par _, expressions de 300 caractères au plus, fichier de 64 Ko au plus.
- Au moins 3 questions (misconception et diagnostic_auto), comme dans les exemples.

Méthodes disponibles (call: et ses arguments, puis ce qu'elle fournit) — n'en inventez aucune :
${METHODS}

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
