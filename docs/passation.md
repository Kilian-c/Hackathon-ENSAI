# Notes de passation (la plus récente en haut)

## H0 (12 h) : décisions de départ
- Rôles : R3 = Kilian (interface), qui pourra aider R1 ; R4 pourra reprendre une partie de l'interface de R3.
- Une seule route d'Entraînement (`POST /api/training/session`, `seed` facultative), pas de réserve en P0, `count = min(10, disponibles)`. Le cahier décrit encore deux routes GET : le CLAUDE.md fait foi.
- Les 3 YAML de référence sont dans `experiments/`, extraits du `.tex` par script (pas depuis le PDF). Seul changement : `explain` de `cauchy-petit-n` sans chiffre écrit en dur.
- `test_student.yaml` : version du cahier (`h.loi`, `p.delta`, `broken_beyond: 0.25`). R2 vérifie par simulation la marge de Wilcoxon sous Cauchy (passer à 0,30 si la perte dépasse 0,22).
- Questions à ajouter par R2 : au moins 3 par expérience (Student : +1, pendule : +2).
- Dépendances P1 dans la régression (`autocorr`, `relation`, `ols_match`) : à implémenter tôt, ou à retirer du YAML en cas de coupe, pour ne pas faire échouer les tests P0 3 et 4.
- Planning : code figé à H25 (13 h le lendemain), pitch à 17 h.
- Dépôt en place : `uv sync`, `uv run pytest` (2 tests de démarrage), `uv run ruff check .`, `npm run check` et `npm run build` au vert.
