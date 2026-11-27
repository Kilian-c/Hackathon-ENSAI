# Notes de passation (la plus récente en haut)

## H5 (17 h) : écran Bilan fait par R3 (pas une relève)
- **R4 : n'écrivez pas le Bilan, il est fait** et fusionné dans `main` à la demande de R3, **sans votre relecture : relisez après coup**, ce sont vos fichiers : `lib/calibration.ts`, `lib/calibration.test.ts`, `components/summary/CalibrationSummary.svelte`. Ouverture : `?bilan`. Votre galerie devra garder ce lien.

## H5 (17 h) : Entraînement côté moteur, branche `r2/training` (pas une relève)
- Fusionné dans `main` à la demande de R2, **sans relecture de R1 : R1, relisez après coup** (les 4 vérifications de la section 4 étaient vertes). Fait par R2, dans des fichiers de R1 : `backend/engine/training.py` et `POST /api/training/session` (`backend/api/routes.py`), empreinte des YAML dans `backend/api/registry.py` (`content_digest`). Tests : `tests/test_training.py`, tests d'API de la section 12 ajoutés à `tests/test_api.py`. 227 tests verts.
- Règles : `misconception` une fois par série, chaque choix vérifié (`reveal_state` lancé, `verify`, 5 tirages au plus, sinon `dropped`) ; `diagnostic_auto` 2 fois au plus, pathologie cachée différente, libellés tirés des hypothèses (« <hypothèse> : <option ou broken_label> », plus « Hypothèses respectées ») ; `prediction` (P1) non servie.
- Temps : série « toutes » 5,8 s (avec le pendule), une expérience 0,1 à 1,4 s.
- **À décider (équipe)** : Student et le pendule sont toujours dans `experiments/`, donc dans la liste d'accueil et dans les séries « toutes ». Les exclure sans code propre à un théorème = sortir leurs fichiers de `experiments/` quand les tests ne s'en servent plus.
- Pas fait : test 7 (pathologies distinguables, P1).

## H4 (16 h 15) : `r2/runner` fusionnée dans `r3/entrainement-et-cours` (pas une relève)
Cette branche réunit le vrai moteur de R2, l'écran d'Entraînement et les nouvelles expériences : c'est elle qu'il faut fusionner dans `main`. Les 4 expériences ont été rejouées sur le vrai `run()` : mêmes valeurs de la mesure primaire qu'au mini-pipeline.

**Correctifs faits à la fusion, à relire par R1 et R2**
- `backend/methods/__init__.py` importe toutes les méthodes : sans cela, les 3 nouvelles expériences renvoyaient une erreur 500, sans qu'aucun test le signale (d'autres fichiers de test les importaient).
- `backend/engine/sweep.py` : une hypothèse continue est balayée sur la grille de son `step`, sans doublon.
- `tests/test_runner.py` : la vue des intervalles n'attend plus que MCO et HC3 (Newey-West retiré). `tests/_mini_run.py` supprimé, comme sur `r2/runner`.
- `match_summary` retiré de `training_session.json` et de `scripts/make_fixtures.py` (le moteur refusait la correction).
- **R2** : le pendule et Newey-West sont abandonnés (note ci-dessous), n'y passez plus de temps.

## H4 (16 h) : changement des expériences (pas une relève)
Décision de Kilian : ne montrer que des théorèmes vus en cours. P0 : régression (IC d'une pente), TCL, multicolinéarité, tests multiples. Student/Wilcoxon et pendule sont abandonnés. Aucun fichier de contrat modifié. Vérifié sur le mini-pipeline `tests/_mini_run.py` (graine 42, 500 répétitions), pas sur le moteur.

**R2 (à relire avant fusion, ce sont vos fichiers)**
- Nouveaux : `experiments/{theoreme_central_limite,multicolinearite,tests_multiples}.yaml`, `backend/methods/{clt_mean,ols_two,pairwise_tests}.py`, `tests/test_course_methods.py` ; `_mini_run.py` et `test_method_contract.py` complétés.
- `regression_lineaire.yaml` : textes repris avec le vocabulaire du cours ; retirés : `nw`, les 2 contre-exemples d'Anscombe, `match_summary`.
- Chiffres : TCL à n = 50, part dans ±1,96 : 95 % (sain), 67 % (Student 2 ddl), 30 % (Cauchy), 60 % (rho = 0,7 ; corrigé : 96 %). Colinéarité, n = 100 : X1 détecté 81 % (rho = 0), 38 % (0,8), 12 % (0,95) ; sans X2 : détecté, mais biais 0,28 à 0,95. Tests multiples, n = 120 : faux positif 4 % (2 groupes), 38 % (6), 62 % (10) ; Bonferroni 3 à 4 %.
- TCL : une correction par la médiane a été essayée et retirée (fausse sous loi exponentielle). Rien ne répare la variance infinie : c'est voulu.

**R1**
- Import des méthodes et grille du balayage : faits à la fusion (note ci-dessus).
- Plus besoin du générateur `ode` en P0.
- Tukey : `studentized_range.ppf` prend près de 0,7 s au premier appel d'un couple (groupes, ddl), puis reste en cache ; à surveiller pour la limite de 2 s et le balayage.
- Fixtures à refaire pour les 3 nouvelles ; numéro de ligne ajusté dans `tests/test_engine.py` (`test_unknown_repair_reports_line`).

**R3**
- Les 3 nouvelles expériences n'apparaissent pas encore dans l'interface : il faut le moteur, ou des specs et fixtures de repli. Spec de repli de la régression régénérée.

**R4** : rien à changer, la galerie lit la liste du moteur.

## H3 (15 h) : vérification croisée du travail de R1, R2 et R3 (pas une relève)
Vérifié au commit `82e7663` : YAML, générateur `random` et méthodes concordent (arguments, `bind`, formes). `run()` n'existant pas, les simulations ont été branchées à la main, à la graine 42.

**R1 (moteur)**
- `tests/_mini_run.py` (R2, `bdaa785`, non vérifié ici) reproduit une partie de `run()` pour les tests : à remplacer par le vrai dès qu'il existe.
- `runner.py` n'est plus bloqué : les 3 méthodes sont là. `backend/methods/__init__.py` n'importe rien, donc le registre est vide : importer les 3 modules (dans le runner, ou demander à R2 de le faire dans `__init__.py`), sinon `get_method` échoue.
- `make_fixtures.py` réécrit les méthodes, les seuils et la règle de verdict, et a divergé : `broken_beyond: 0.25` (YAML : 0.30), Wilcoxon sous Cauchy y est Rompu au lieu de Fragile ; `nw`, `bp_pvalue` et les nouvelles questions manquent. À brancher sur les vraies méthodes dès que `run()` existe.
- Pendule : avec un `rhs` passant par `expr.py`, `integrate` prend environ 0,75 s (Euler + RK4) à l'état par défaut et 2,2 s à `t_end = 10`, Référence non comprise (limite : 2 s). Fournir un `rhs` rapide et `ref` (angle seul, sur `t`).
- Une seule entrée par code dans `RunResult.warnings` de préférence (l'interface tolère désormais les doublons).
- Mineur : `state.py` arrondit au pas à partir de 0, `state.ts` à partir du minimum (sans effet avec les YAML actuels) ; `asteval` est inutilisé.

**R2 (maths et contenu)**
- `pend-q2-duree` : l'énoncé dit « un pas pour lequel Euler reste fiable sur 5 s », mais à `pas: 0.4` Euler est Fragile sur 5 s (12,2 %). Proposition : `pas: 0.2` (Fiable à 5 s : 3,7 % ; Fragile de 8 à 10 s : 8,4 à 12,3 %) et `verify: "s.err_angle != 'ok' and m.err_angle.rk4 < 0.05"`.
- Student à n = 5 : Wilcoxon ne peut jamais rejeter (p minimale 0,0625). Il s'affiche Fiable avec 0 % de puissance, et son risque alpha est Rompu même sous loi normale. Proposition : `n` minimum à 10, `sweep_values` à partir de 10.
- Défi `trap-bp-test` : réussi aussi sans hétéroscédasticité, avec `autocorr: true`, n = 30, graine 42. Ajouter `h.hetero > 0` à `when` si ce n'est pas voulu.
- Pendule : à `theta0 = 2.5` et `t_end = 10`, l'état sain est Fragile (16,8 %).
- `relation: break` ne rompt aucune mesure (couverture 87,8 %) : risque sur le test 2 (P1).
- Texte : `when_broken` de `relation` dit « vers 73 % » (réel : 76 %). Le commentaire de `alpha` est déjà corrigé (`0ae458a`).
- `integrate` calcule l'énergie du pendule et suppose 2 variables d'état : une autre équation différentielle donnerait un résultat faux ou une erreur.

**R3 (interface)**
- Corrigé : défis réussis retenus d'un onglet à l'autre, clés des avertissements, specs de repli régénérées, `CLAUDE.md` (section 9) et arborescence du README.
- Reste : zoom qui pourrait passer d'une vue à l'autre (à vérifier au navigateur) ; repli sur les fixtures à désactiver avant la démo.
- 15 h 30 : Entraînement minimal fait (`components/training/`), testé dans un navigateur sur la série de démonstration ; il passera sur le vrai moteur dès que `POST /api/training/session` et `/api/run` répondent.
- TODO(passation), R4 : le Bilan lit l'historique avec `loadHistory(browserStore())` (`lib/training.ts` : par série, chaque réponse a `correct`, `level`, `p`, `at`) ; ajouter le lien vers le Bilan sur l'écran de fin (`TrainingView.svelte`).

## H0 (12 h) : décisions de départ
- Rôles : R3 = Kilian (interface), qui pourra aider R1 ; R4 pourra reprendre une partie de l'interface de R3.
- Une seule route d'Entraînement (`POST /api/training/session`, `seed` facultative), pas de réserve en P0, `count = min(10, disponibles)`. Le cahier décrit encore deux routes GET : le CLAUDE.md fait foi.
- Les 3 YAML de référence sont dans `experiments/`, extraits du `.tex` par script (pas depuis le PDF). Seul changement : `explain` de `cauchy-petit-n` sans chiffre écrit en dur.
- `test_student.yaml` : version du cahier (`h.loi`, `p.delta`, `broken_beyond: 0.25`). R2 vérifie par simulation la marge de Wilcoxon sous Cauchy (passer à 0,30 si la perte dépasse 0,22).
- Questions à ajouter par R2 : au moins 3 par expérience (Student : +1, pendule : +2).
- Dépendances P1 dans la régression (`autocorr`, `relation`, `ols_match`) : à implémenter tôt, ou à retirer du YAML en cas de coupe, pour ne pas faire échouer les tests P0 3 et 4.
- Planning : code figé à H25 (13 h le lendemain), pitch à 17 h.
- Dépôt en place : `uv sync`, `uv run pytest` (2 tests de démarrage), `uv run ruff check .`, `npm run check` et `npm run build` au vert.
