# Théorèmes restants : état d'avancement du catalogue

Écrit par R2 (H7, 20 h) pour la personne qui continue les expériences. Le catalogue complet est dans `docs/catalogue_experiences.md` (copie de la version de Kilian). Ce fichier dit **ce qui est fait** et **ce qu'il faut pour chacune des autres**. Le classement est une estimation : vérifiez en lisant `backend/methods/` avant de vous lancer.

## Ce qui est fait (dans `experiments/`)

| Fichier | Niveau | Méthodes |
|---|---|---|
| `regression_lineaire`, `multicolinearite`, `theoreme_central_limite`, `tests_multiples` | 3, 3, 2, 2 | `ols_ci`, `ols_two`, `clt_mean`, `pairwise_tests` |
| `somme_des`, `moyenne_mediane` | 1 | `statistic` |
| `seuil_roc`, `desequilibre` | 1 | `classifier` (kind « seuil ») |
| `carres_residus` | 1 | `regressor` (ols, manuelle) |

Student et le pendule sont archivés dans `experiments/archives/` (abandonnés).

## Les trois cas

1. **YAML seul** : une méthode existante suffit. Vous n'écrivez qu'un fichier dans `experiments/`.
2. **YAML + une méthode** : écrivez la méthode une fois (`@register_method`, formules fermées NumPy, vectorisées sur l'axe 0), puis réutilisez-la via `kind`. Pas de boucle Python sur les répétitions ; la limite de `/api/run` est de 2 s.
3. **YAML + une vue** : code dans `runner.py` (R1) et en Svelte (R3 / R4). Classé P1/P2 : à ne pas commencer avant que le reste soit vert.

Méthodes existantes : `statistic` (sum, mean, max, min, median), `classifier` (seuil), `regressor` (ols, manuelle), `ols_ci`, `ols_two`, `clt_mean`, `pairwise_tests`, `one_sample_test`, `integrate` (générique depuis H7).

## Les expériences restantes

| Expérience (niveau) | Cas | Remarque |
|---|---|---|
| Premier pile, géométrique (1) | 1 | `statistic` ; `theory` d'une vue `distribution` n'est pas servi (R3) |
| Binomiale = somme de Bernoulli (1) | 1 | `statistic` (sum) |
| Maximum de n uniformes (2), minimum d'exponentielles (3) | 1 | `statistic` (max, min) |
| Mélange θP + (1−θ)Dirac (2) | 1 | option `expr:` pour la loi |
| Y = g(X), inversion F⁻¹(U) (2, 3) | 1 | choix de g ou de la loi par une hypothèse de type `choice` |
| Poisson ≈ binomiale (2) | 2 | loi `poisson` absente du registre (option `expr:`) |
| Séparation et AUC (2), coûts asymétriques (2), comparer deux modèles (3) | 1 | `classifier` ; coûts : à faire lire par `summary` |
| Levier contre aberrant (1, déjà en partie dans `carres_residus`), régression vers la moyenne (2), Simpson (2), variable omise (3), extrapolation (2) | 1 | `regressor` / `ols_ci` ; Anscombe : `ols_match` est une fonction du générateur |
| Fréquence de pile / LGN du dé (1), Cauchy (2), fléchettes pour π (1), intégrale Monte Carlo (2), marche aléatoire (2) | 1 ou 2 | vue en trajectoires (`paths`, servi pour le TCL) ; vérifier que `cumsum` est dans la liste blanche |
| Sondage et marge d'erreur (1), pièce truquée et puissance (2) | 2 | test sur une proportion à écrire |
| 20 tests, un « significatif » (2) | 1 | proche de `tests_multiples` |
| kNN, polynôme, arbre, forêt, courbe d'apprentissage, plancher de Bayes, biais-variance (1 à 2) | 2 | `kind` de plus dans `classifier` / `regressor` ; erreur train / test en vue `sensitivity` |
| kNN et échelle, malédiction de la dimension, distances en grande dimension (1 à 3) | 2 | idem |
| Valeurs manquantes (2), fuite de données (3), découpage train / test (1), encodage catégoriel (2) | 2 | validation croisée à écrire pour la fuite de données |
| Test médical, Monty Hall, anniversaires, indépendance carré / disque (1 à 2) | 3 | vues `population` ou `bars` |
| LDA / QDA, Naive Bayes (2) | 3 | vue `decision_map` pour la frontière ; sinon courbe d'erreur de test |
| Descente de gradient, croissance logistique, SIR (1 à 2) | 3 | générateur `ode`, plus requis en P0 |

## Marche à suivre (valable pour chaque expérience)

1. Partez d'un YAML proche (`seuil_roc.yaml` pour un classifieur, `somme_des.yaml` pour une statistique, `carres_residus.yaml` pour une régression).
2. **Simulez avant d'écrire les seuils** (`ok_within`, `broken_beyond`) : lancez `run()` sur plusieurs états, avec `EngineState(...)`, graine 42. Une marge de moins de 0,03 sur un état de la démonstration est à noter dans la passation.
3. Aucun chiffre en dur dans les textes de mesures (`{value}`) ni dans les `explain` de contre-exemples ou de choix.
4. Au moins 3 questions par expérience (`verify` doit passer sur 90 % de 50 tirages : `CRASHTEST_DRAWS=50 uv run pytest tests/test_experiments.py -k "test_6 and <id>"`).
5. État par défaut en moins de 500 ms (test 9) : réduisez `n` et `repeat` si besoin. Pour `desequilibre`, 1000 × 500 prenait 0,8 s, 600 × 300 prend 0,2 s.
6. Niveau : `level: "1"`, `"2"` ou `"3"`, d'après le catalogue.
7. `uv run pytest -q`, `uv run ruff check .`, puis une note dans `docs/notes/r2.md` et dans `docs/passation.md`.

## Pièges rencontrés

- `bind.threshold` d'une vue `distribution` n'accepte qu'un `p.<id>` : un seuil calculé par une expression ne se dessine pas.
- Une loi du registre n'a pas de taille en argument : les fonctions de tirage ne prennent jamais de taille.
- `ols_match` fige la pente à chaque répétition : sur Anscombe, la couverture vaut 100 % et la vue « intervalles » n'apprend rien.
- Wilcoxon teste le centre de symétrie, pas la moyenne : il ne corrige pas l'asymétrie.
- Ne lancez pas `ruff format backend/engine` : cela reformate des fichiers de contrat.
- Évitez les heredocs Python avec des accents sous Windows : ils sont mal lus. Utilisez l'outil d'édition.
