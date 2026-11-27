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
