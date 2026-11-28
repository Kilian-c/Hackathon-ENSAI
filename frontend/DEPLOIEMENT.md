# Mise en ligne

## Hugging Face Spaces : une seule image (choix retenu)

Une seule image Docker (`Dockerfile` à la racine) : l'interface est construite dans l'image, puis le moteur la sert sur `/` et l'API sur `/api`. Une seule adresse à donner au jury, aucun CORS à régler, une seule plateforme. Offre gratuite « CPU basic » : 2 processeurs, 16 Go de mémoire, mise en veille après 48 h sans visite.

### Une fois : créer le Space (à faire par un membre de l'équipe, avec son compte)

1. Sur huggingface.co : **New Space**, nom (par exemple `crash-test`), **SDK : Docker**, modèle **Blank**, matériel **CPU basic (gratuit)**, visibilité au choix.
2. **Settings > Variables and secrets > New variable** (des *variables*, pas des *secrets* : elles sont passées au build de l'image) :
   - `VITE_SUPABASE_URL` : adresse du projet, `https://<projet>.supabase.co` ;
   - `VITE_SUPABASE_ANON_KEY` : la clé **publique** (`anon` ou `sb_publishable_…`). Jamais la clé `service_role` ni `sb_secret_…` : tout ce qui commence par `VITE_` finit dans le JavaScript envoyé aux visiteurs.
   Sans ces deux variables, le site marche et seul le bouton « Créer un lien de partage » est grisé.
3. Se connecter en ligne de commande (jeton « write » créé dans Settings > Access Tokens du compte) :
   `uvx --from huggingface_hub hf auth login`

### À chaque mise en ligne

On envoie les fichiers avec l'outil officiel plutôt qu'avec `git push` : Hugging Face refuse les fichiers binaires dans l'historique git (le PDF du cahier y est), et le Space n'a besoin que du code.

```bash
# depuis la racine du dépôt, sur la version à mettre en ligne (main à jour, tests verts)
SPACE=<compte>/crash-test
uvx --from huggingface_hub hf upload $SPACE . . --repo-type=space   --exclude ".git/*" "**/node_modules/*" "**/.venv/*" "**/__pycache__/*" "**/.env" "**/.env.*"             "frontend/dist/*" "docs/*" "tests/*" "scripts/*" "deploy/*" "experiments/archives/*"             "*.patch" "package-lock.json" "README.md"   --commit-message "Mise en ligne"
uvx --from huggingface_hub hf upload $SPACE deploy/huggingface/README.md README.md --repo-type=space   --commit-message "En-tête du Space"
```

Le second envoi pose `README.md` : son en-tête (`sdk: docker`, `app_port: 7860`) indique à Hugging Face comment lancer le Space. Chaque envoi relance la construction de l'image (environ 3 à 5 minutes : onglet « Logs » du Space).

### Vérifier après la mise en ligne

1. `https://<compte>-crash-test.hf.space/api/health` répond `{"status":"ok"}`.
2. L'accueil s'affiche, la galerie liste les expériences, une expérience s'ouvre, une série d'Entraînement se prépare.
3. Import : un YAML se vérifie ; si Supabase est réglé, « Créer un lien de partage » donne un lien qui se rouvre.
4. Avant la démo, ouvrir la page quelques minutes à l'avance (réveil si le Space dormait).

### Tester l'image en local (Docker Desktop lancé)

```bash
docker build -t crash-test .
docker run --rm -p 7860:7860 crash-test      # puis http://127.0.0.1:7860/
```

Avec Supabase : `docker build -t crash-test --build-arg VITE_SUPABASE_URL=... --build-arg VITE_SUPABASE_ANON_KEY=... .`

---

# Autre possibilité : interface sur Cloudflare Pages, moteur à part


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

