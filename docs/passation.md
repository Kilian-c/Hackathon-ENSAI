# Notes de passation (la plus récente en haut)

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
