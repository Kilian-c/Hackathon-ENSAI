# Mise en ligne de l'interface (Cloudflare Pages)

## Réglages du projet

| Réglage | Valeur |
|---|---|
| Répertoire racine | `frontend` |
| Commande de build | `npm run build` |
| Dossier publié | `dist` |
| Variable `VITE_API_URL` | adresse du moteur, par exemple `https://mon-moteur.example` |
| Variable `NODE_VERSION` | `24` |

`VITE_API_URL` est lue au moment du build : après l'avoir changée, relancez un déploiement.

La navigation passe par les paramètres de l'URL (`?exp=...`, `?train=...`) : aucune règle de redirection n'est nécessaire.

## Côté moteur

La variable `CORS_ORIGINS` du moteur doit contenir l'adresse de l'interface, sans barre finale
(plusieurs adresses séparées par des virgules). Sans cela, le navigateur bloque tous les appels.

## Vérification après déploiement

1. `<VITE_API_URL>/api/health` répond `{"status":"ok"}`.
2. L'accueil liste les expériences, sans message d'erreur.
3. Une expérience s'ouvre et une série d'Entraînement se prépare.

Avant la démo, ouvrez la page d'accueil quelques minutes à l'avance : un hébergeur gratuit endormi
met un moment à se réveiller.

## Version locale de secours (un seul port, sans Node à l'exécution)

Le moteur sait servir l'interface lui-même : si `frontend/dist` existe, `uvicorn` la sert sur `/` et garde `/api/...` pour l'API. Un seul processus, un seul port, aucun CORS.

1. Construire l'interface **sans** `VITE_API_URL` (elle appelle alors `/api` sur le même serveur) : `cd frontend && npm ci && npm run build`. Si `frontend/.env` définit `VITE_API_URL`, videz-la le temps du build.
2. Lancer : `uv run uvicorn backend.main:app --port 8000`, puis ouvrir `http://127.0.0.1:8000/`.
3. Au démarrage, le moteur charge les expériences (environ 3 s) : le premier clic est ensuite instantané. Le journal dit « Interface servie sur / ».

- `CRASHTEST_DIST=/autre/dossier` désigne un autre dossier construit (par exemple celui d'une copie de secours).
- `dist` est ignoré par git : il ne se récupère pas avec un `git pull`. Pour une machine sans Node, il existe une **branche de secours** `secours-dist` (orpheline : un seul commit, `frontend/dist/` et un README, jamais fusionnable dans `main`). Elle se fabrique avec `uv run python scripts/build_secours.py` (construit sans `VITE_API_URL`, vérifie le résultat, ne touche ni votre branche ni votre arbre de travail, ne pousse jamais ; `--no-build` réutilise un `dist` existant). **À lancer une seule fois, sur la version finale validée.** Pour l'installer sur une autre machine : `git fetch origin secours-dist`, puis `git restore --source=origin/secours-dist --worktree -- frontend/dist` (pas `git checkout origin/secours-dist -- frontend/dist`, qui indexerait les fichiers).
- Un `dist` doit correspondre à la version du moteur : reconstruisez-le après toute modification de l'API ou de l'interface.
- Si le port 8000 est pris, changez `--port` : rien d'autre à régler.

