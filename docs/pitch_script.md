# Script de pitch Crash-Test : 3 minutes, version solo et version duo

Pitch à 17 h (H29) : 3 minutes, puis 2 minutes de questions. Les chiffres ci-dessous ont été relevés sur le moteur local (graine 42) et vérifiés à l'écran. Le déroulé est le même dans les deux versions ; seule la répartition des rôles change.

Vérifié sur `main` (fusion `3ac526d`) : pytest, ruff, `npm run check` (0 erreur) et `npm test` (263 tests) verts, puis parcours rejoué dans le navigateur contre un moteur et une interface lancés depuis `main`.

## Avant de commencer (H-15 min)

- **Relancer le moteur et l'interface après chaque `git pull`.** Un moteur lancé avant la fusion ne servait que 11 expériences au lieu de 19, et un serveur Vite lancé avant la fusion affichait le Laboratoire sans mise en page. Une fois après un pull : `cd frontend && npm install` (deux dépendances ajoutées, `ajv` et `yaml`).
- Moteur : `OMP_NUM_THREADS=1 uv run uvicorn backend.main:app --port 8000`. Interface : `cd frontend && npm run dev`.
- Navigateur en plein écran (F11), zoom à 80 ou 90 %, console fermée.
- Ouvrir **dans cet ordre** les onglets (l'Entraînement affiche un écran blanc d'environ 3 s au premier chargement : ouvrez-le avant) :
  1. Accueil : `http://localhost:5173/`
  2. Dés : `http://localhost:5173/?exp=somme-de-des&v=1&seed=42`
  3. Régression : `http://localhost:5173/?exp=regression-lineaire&v=1&h.hetero=0.8&seed=42&on=ols&tab=ic`
  4. Entraînement : `http://localhost:5173/?train=regression-lineaire&seed=262&v=1` (la graine 10 ne convient plus depuis les changements du TCL, qui changent les séries ; la graine 262 redonne la même première question avec les choix dans le même ordre ; deux des questions suivantes diffèrent)
  5. Bilan : `http://localhost:5173/?bilan`
- Plan B : la vidéo de secours, ouverte dans un onglet à part. Aucun repli par fixtures n'a été testé.

## Chiffres à connaître

| Écran | Valeurs à l'écran |
|---|---|
| Dés, état sain (`k = 10`) | aplatissement −0,13, « Fiable » |
| Dés, `dépendance = 0,95` | aplatissement −1,22, « Rompu » |
| Régression, `h = 0,8` | classique 79,6 % ± 3,6 « Rompu » ; HC3 96,6 % ± 1,6 « Fiable » ; cible 95 % |
| Sensibilité | courbe bleue qui chute, courbe verte plate ; seuil critique vers `h ≈ 0,34` (Fragile) et `h ≈ 0,62` (Rompu) |
| Entraînement, graine 262 | « Série de 4 questions », bandeau jaune « Il n'existe que 4 questions… » (normal) ; première question à 2 choix, énoncé « (n = 200) », bonne réponse : « Il reste sans biais, mais les intervalles de confiance sont invalides. » ; la simulation de validation, très en dessous de l'énoncé, montre les intervalles empilés avec leurs ratés (son état est propre à la question : ne la comparez pas aux 79,6 % du Laboratoire) |
| Bilan (profil de démonstration) | « Certain » : 60 % de réussite (12 sur 20) ; Brier 0,35 ; 50 % de bonnes réponses (16 sur 32) ; confiance annoncée 81 % |

## Déroulé commun

| Temps | Écran | Action | Message clé |
|---|---|---|---|
| 0:00 à 0:35 | Slide ou accueil | aucune | On apprend les théorèmes, on oublie leurs hypothèses. |
| 0:35 à 0:50 | Accueil | montrer les deux modes | Casser une hypothèse, mesurer ce qui cède, réparer. |
| 0:50 à 1:15 | Dés | glisser « Dés lancés indépendamment » vers la droite | Un curseur, et la cloche disparaît. |
| 1:15 à 2:00 | Régression | intervalles empilés, puis « Afficher la correction », puis « Étude de sensibilité » | 95 % annoncé, 80 % réel ; la correction répare. |
| 2:00 à 2:30 | Entraînement | répondre, cran « Plutôt sûr », valider, faire défiler environ 8 crans de molette jusqu'à la simulation | La correction est une simulation. |
| 2:30 à 2:50 | Bilan | « Voir un profil de démonstration » | Savez-vous quand vous avez raison ? |
| 2:50 à 3:00 | Accueil | aucune | Une expérience = un fichier YAML. |

**Points de contrôle :** à 1:15 vous devez être sur la régression ; à 2:00 sur l'Entraînement. Si vous avez plus de 10 s de retard à 1:15, sautez les dés au prochain passage et ouvrez directement la régression.

---

# Version A : une seule personne

La personne parle et manipule. Elle ne regarde l'écran que quand elle clique.

**0:00 à 0:35, le besoin (slide, pas de clic)**
> « En cours de statistiques, on apprend des théorèmes par cœur, mais pas ce qui se passe quand leurs hypothèses sont fausses. Résultat : on croit un intervalle à 95 % fiable alors qu'il ne l'est pas, et on ne sait pas mesurer si on est sûr de soi à raison. »

**0:35 à 0:50, la réponse (accueil)**
> « Crash-Test, c'est un QCM de révision dont la correction est une simulation. Pour chaque théorème, on casse une hypothèse, on mesure ce qui cède, et on applique la correction. »

**0:50 à 1:15, les dés (onglet 2)**
- Montrer la cloche (« Fiable », −0,13).
- Glisser « Dés lancés indépendamment » vers la droite, près du bout (0,95 est le point visé ; au pire, rechargez `&h.dependance=0.95`).
> « Dix dés indépendants : une cloche. Je fais dépendre chaque dé de son voisin : la cloche disparaît, le verdict passe à Rompu. »

**1:15 à 2:00, la régression (onglet 3)**
- 1:15 : montrer les intervalles empilés. Les croix rouges sont les intervalles qui ratent la valeur vraie.
> « Nous voulons 95 % de couverture. Quand la variance n'est pas constante, on tombe à 79,6 %. »
- 1:30 : cliquer « Afficher la correction ». Lire 96,6 %, « Fiable » dans le panneau de droite. Le graphique devient alors un mur vert où les ratés disparaissent : ne le commentez pas, passez tout de suite à la sensibilité.
> « Avec les écarts-types corrigés, HC3, on revient à 96,6 %. »
- 1:42 : cliquer « Étude de sensibilité ».
> « Ici, la courbe bleue s'effondre quand l'hétéroscédasticité augmente ; la verte reste plate. On voit à quel moment la méthode cède. »

**2:00 à 2:30, l'Entraînement (onglet 4)**
- Choisir « Il reste sans biais, mais les intervalles de confiance sont invalides. », puis « Plutôt sûr », puis « Valider ma réponse ». Le bouton « Valider ma réponse » peut demander un petit défilement.
- Faire défiler jusqu'à la simulation (les 100 intervalles, environ 8 crans de molette).
> « À chaque question, on indique sa confiance. La réponse n'est pas écrite à l'avance : le moteur la rejoue en simulation, sous vos yeux. »

**2:30 à 2:50, le Bilan (onglet 5)**
- Cliquer « Voir un profil de démonstration ».
> « Ce profil dit "Certain" et a raison 6 fois sur 10. Le Bilan le mesure : score de Brier de 0,35. On apprend aussi à se calibrer. »

**2:50 à 3:00, la clôture (accueil)**
> « Chaque expérience est un simple fichier YAML : on étend le catalogue sans écrire de code. »

**Risque propre à cette version :** parler et cliquer en même temps. Répétez les clics jusqu'à ce qu'ils soient automatiques, et ne commentez jamais pendant un chargement.

---

# Version B : deux personnes

**Personne 1 (orateur)** parle et tient le fil. **Personne 2 (opérateur)** manipule l'écran. Convention : 1 dit « à vous » pour passer la main, 2 dit « voilà » quand l'écran est prêt. Le duo permet que l'orateur regarde le jury.

| Temps | Orateur (1) | Opérateur (2) |
|---|---|---|
| 0:00 à 0:35 | Dit le besoin (même texte que la version A). | Affiche le slide, attend. |
| 0:35 à 0:50 | Dit la réponse et présente les deux modes. | Affiche l'accueil. |
| 0:50 à 1:15 | « Dix dés indépendants : une cloche. » | Glisse le curseur ; l'histogramme s'aplatit. |
| | « Dépendants : la cloche disparaît. » | Laisse l'écran fixe 3 s. |
| 1:15 à 1:30 | « Nous voulons 95 %. On tombe à 79,6 %. » | Affiche l'onglet 3 (intervalles empilés). |
| 1:30 à 1:42 | « Avec HC3, on revient à 96,6 %. » | Clique « Afficher la correction ». |
| 1:42 à 2:00 | « La courbe bleue s'effondre, la verte reste plate. » | Clique « Étude de sensibilité ». |
| 2:00 à 2:30 | Lit la question, annonce « Plutôt sûr », commente la simulation. | Clique la réponse, le cran, valide, descend sur la simulation. |
| 2:30 à 2:50 | « Ce profil dit Certain et a raison 6 fois sur 10. » | Clique « Voir un profil de démonstration ». |
| 2:50 à 3:00 | Dit la clôture. | Revient à l'accueil. |

**Avantage de cette version :** l'orateur ne regarde pas l'écran, la voix reste continue pendant les clics, et il y a un relais si l'un des deux perd le fil.

**Risque propre à cette version :** le décalage entre ce que dit l'orateur et ce que montre l'écran. Répétez avec un chronomètre et fixez les « à vous ».

---

# Comparaison

| Critère | Solo | Duo |
|---|---|---|
| Fluidité de l'enchaînement | demande de l'entraînement | meilleure, si la coordination est répétée |
| Contact visuel avec le jury | faible (regard sur l'écran) | bon |
| Risque de blanc pendant un chargement | élevé | faible : l'orateur comble |
| Préparation nécessaire | un seul parcours à mémoriser | un parcours plus des signaux de passage |
| Questions du jury | un seul répondant | deux répondants, un par domaine (moteur, interface) |

# À ne pas oublier

- Rejoué à l'écran sur `main` : la régression (intervalles, correction, sensibilité), l'Entraînement (graine 10, validation ; passé à la graine 262 ensuite, à rejouer à l'écran) et le Bilan. Le curseur des dés n'a été testé que par lien direct (`h.dependance=0.95`) et par chargement de la page, pas par glissement.
- Les erreurs de console vues pendant les tests venaient de l'extension de portefeuille du navigateur (`evmAsk.js`), pas de l'application.
- La taille de l'écran du projecteur est inconnue : testez en plein écran avant le pitch.
- Le chronométrage ci-dessus est une estimation, pas une mesure : chronométrez une répétition complète.
