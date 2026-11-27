# Crash-Test : catalogue d'expériences simples et généralisables

## 1. Pourquoi ce document

Les expériences actuelles (couverture des IC, HC3, Breusch-Pagan, Wilcoxon sous Cauchy) supposent déjà de maîtriser le sujet. Quand on ne les a jamais vues en cours, on ne comprend pas ce que l'écran montre.

Ce document propose :

- des expériences **plus simples**, bâties sur ce que le cours a déjà fait manipuler (le dé, la pièce et le tir à l'arc de `Proba.pdf`, le kNN, la matrice de confusion et la ROC du syllabus, la droite des moindres carrés des slides de régression) ;
- un classement par **archétype** : un archétype fixe le trio méthode + mesure + vue, et chaque expérience ne change que le générateur et les paramètres. Ajouter une expérience, c'est alors écrire un fichier YAML, sans code propre à un théorème.

**Règle de simplicité : une expérience = une image + un seul curseur + une phrase de conclusion.**

## 2. Les niveaux de difficulté

Chaque expérience porte un niveau. C'est le champ `level` déjà présent en clé de premier niveau du YAML (`level: 1`, `2` ou `3`).

| Niveau | Nom | Ce qu'il faut savoir avant |
|---|---|---|
| ① | Découverte | Rien. On comprend l'image en quelques secondes (somme de dés, test médical, k du kNN). |
| ② | Intermédiaire | Une notion du cours (loi binomiale, intervalle de confiance, validation croisée), pas plus. |
| ③ | Avancé | Bien maîtriser le cours (Borel-Cantelli, inversion de la fonction de répartition, fuite de données). Les expériences actuelles du cahier sont de ce niveau. |

Usage dans l'interface, sans code de plus : trier la galerie par niveau ou afficher un badge sur chaque carte. Le jour du pitch et pour les étudiants qui découvrent l'app, on met les ① en avant ; les ③ restent disponibles.

Légende des tableaux : `[ext]` signale une expérience qui demande une vue générique de plus (voir la section 13).

## 3. Idées par cours (vue d'ensemble)

### Probabilités (`Proba.pdf`)

- **Somme de dés** (chap. 10, convolution) : 1 dé donne des barres plates, 2 dés un triangle, 5 dés une cloche. Curseur : nombre de dés, avec la loi théorique en surimpression.
- **Tir à l'arc** (chap. 1 et 4) : des flèches tombent sur une cible, avec à droite l'histogramme du numéro de l'anneau. Une variable aléatoire transforme une mesure en loi.
- **Pièce jusqu'au premier pile** (loi géométrique, déjà dans le cours) : curseur sur p, histogramme de Y avec la courbe q(1−q)ⁿ⁻¹.
- **Dé et loi des grands nombres** : les fréquences de 1 à 6 se stabilisent vers 1/6.
- **Mélange** (§3.2.4) : curseur θ entre une cloche et un pic de Dirac ; le résultat n'est ni discret ni à densité.
- **Indépendance** : nuage uniforme dans un carré ou dans un disque, mesure P(A∩B) comparée à P(A)P(B).

### Apprentissage supervisé (syllabus)

- **Test médical : seuil, matrice de confusion, ROC.** Deux cloches (malades, sains), une barre de seuil que l'on déplace ; la matrice et le point sur la ROC se mettent à jour.
- **kNN : le curseur k.** k = 1 donne une frontière déchiquetée (sur-apprentissage), k = 100 une frontière trop plate. À côté, la courbe d'erreur train/test en U.
- **Biais-variance en cibles de tir.** Quatre cibles : biais faible ou fort, variance faible ou forte.

### Régression (slides)

- **Les carrés des résidus.** On glisse une droite à la main, les carrés grossissent ou rétrécissent ; le total est minimal à la droite MCO.
- **Point levier.** Un point tiré dans le nuage fait pivoter la droite (déjà prévu dans le cahier).

## 4. Archétype 1 : loi d'une statistique

Vue `distribution` avec `theory`. Mesure : écart à la loi théorique.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Somme de k dés | ① | triangle puis cloche | k |
| Moyenne de n variables (TCL) | ② | la cloche apparaît, sauf sous Cauchy | n, loi de départ |
| Binomiale = somme de Bernoulli | ① | barres qui se déforment | n, p |
| Poisson ≈ binomiale | ② | les deux histogrammes se superposent | n grand, p petit |
| Premier pile (géométrique) | ① | décroissance en q(1−q)ⁿ⁻¹ | p |
| Maximum de n uniformes | ② | la loi se colle contre 1 | n |
| Minimum d'exponentielles | ③ | reste exponentielle | n |
| Y = g(X) (X², exp X) | ② | la loi change de forme (théorème de transfert) | choix de g |
| Inversion F⁻¹(U) | ③ | des uniformes deviennent n'importe quelle loi | choix de la loi |
| Mélange θP + (1−θ)Dirac | ② | cloche + pic | θ |
| Moyenne vs médiane + valeur extrême | ① | la moyenne bouge, pas la médiane | point posé au clic |

## 5. Archétype 2 : convergence quand n grandit

Vue `repetitions` (trajectoires). Mesure : écart à la limite.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Fréquence de pile / loi des grands nombres | ① | 30 courbes qui se resserrent | n, p |
| Cauchy : la moyenne ne converge pas | ② | les courbes sautent à jamais | loi |
| Estimer π avec des fléchettes | ① | fréquence dans le disque → π/4 | n |
| Intégrale par Monte Carlo | ② | l'erreur décroît en 1/√n | n, fonction |
| Marche aléatoire | ② | étalement en √n | n, biais |
| Borel-Cantelli (le singe) | ③ | Σ P(Aₙ) fini : événements finis ; infini : infiniment souvent | exposant (1/n² ou 1/n) |

## 6. Archétype 3 : taux d'erreur d'une procédure

Vue `repetitions` (intervalles). Mesure : couverture, niveau ou puissance.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Sondage et marge d'erreur | ① | 100 sondages autour de la vraie proportion | n ; échantillon aléatoire ou volontaires |
| Pièce truquée : test et puissance | ② | puissance qui monte avec n | biais, n |
| 20 tests, un « significatif » | ② | faux positifs par pur hasard | nb de tests |
| IC de la moyenne | ③ | couverture qui chute sous loi asymétrique | loi, n |
| Régression et Student/Wilcoxon | ③ | déjà dans le cahier | à garder en avancé |

## 7. Archétype 4 : conditionnement et indépendance

Vue `bars` ou `population` `[ext]`. Mesure : probabilité conditionnelle.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Test médical d'une maladie rare | ① | la plupart des positifs sont sains | prévalence, sensibilité |
| Monty Hall | ① | changer gagne 2 fois sur 3 | stratégie (choix) |
| Anniversaires | ① | P(deux dates identiques) en fonction de n | n |
| Indépendance : carré ou disque | ② | P(A∩B) ≠ P(A)P(B) | interrupteur |
| Deux dés, grille 6×6 | ① | aire de A∩B vs produit | choix des événements |

## 8. Archétype 5 : compromis de complexité

Vue `curves` / `sensitivity` sur un paramètre balayé (`sweep_values`). Mesure : erreur train et test.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| kNN | ① | courbe d'erreur en U | k |
| Polynôme | ① | sous-ajustement puis sur-ajustement | degré |
| Arbre | ② | l'erreur train tombe à 0, pas le test | profondeur |
| Forêt | ② | la variance baisse, puis plateau | nb d'arbres |
| Lissage à noyau | ③ | courbe trop lisse ou trop nerveuse | bande passante |
| Courbe d'apprentissage | ② | plus de données réduit l'écart train/test | taille du train |
| Plancher de Bayes | ② | aucune méthode ne descend sous le bruit | bruit des étiquettes |
| Cibles biais-variance | ① | 4 nuages de tirs autour de la vraie valeur | complexité |

## 9. Archétype 6 : score et seuil

Vue `distribution` avec `threshold`, plus `curves` pour la ROC.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Seuil, confusion, ROC | ① | la matrice et le point ROC bougent | seuil |
| Séparation des classes et AUC | ② | plus d'écart entre moyennes, plus d'AUC | distance |
| Coûts asymétriques | ② | le seuil optimal se décale | coût FN / FP |
| Déséquilibre : 99 % de précision sans rien faire | ① | l'accuracy trompe | part de la classe rare |
| Comparer deux modèles | ③ | les ROC se croisent | choix du modèle |

## 10. Archétype 7 : hypothèse d'un classifieur cassée

Vue `decision_map` `[ext]`, ou à défaut une courbe d'erreur de test.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| LDA vs QDA | ② | la frontière droite échoue si les covariances diffèrent | rapport des covariances |
| Naive Bayes | ② | échoue si les variables sont corrélées | corrélation ρ |
| kNN et échelle des variables | ① | une variable en mm écrase l'autre ; la normalisation répare | facteur d'échelle |
| Malédiction de la dimension | ② | kNN s'effondre avec des variables de bruit | nb de variables |
| Distances en grande dimension | ③ | toutes les distances deviennent égales | dimension |

## 11. Archétype 8 : données imparfaites

Mesure : biais ou erreur d'une estimation.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Valeurs manquantes : au hasard ou non | ② | moyenne biaisée si ce sont les hauts revenus qui manquent | mécanisme (choix) |
| Fuite de données | ③ | sélectionner les variables avant la validation croisée donne un score trop beau sur du bruit pur | nb de variables |
| Découpage train/test | ① | l'estimation varie selon le découpage | taille du test |
| Encodage catégoriel | ② | 1, 2, 3 impose un faux ordre, le one-hot non | encodage (choix) |

## 12. Archétypes 9 et 10 : régression et dynamique

### Régression

Vue `scatter`, avec `segments` pour les résidus.

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Carrés des résidus | ① | minimum atteint par la droite MCO | pente |
| Levier vs outlier | ① | la droite pivote ou le R² chute | point posé au clic |
| Anscombe | ② | mêmes chiffres, quatre nuages | préréglages |
| Régression vers la moyenne | ② | enfants des grands, un peu moins grands | corrélation |
| Paradoxe de Simpson | ② | tendance inversée par groupe | interrupteur |
| Variable omise | ③ | la pente est faussée | corrélation x₁/x₂ |
| Extrapolation | ② | l'IC est faux hors des données | x max |

### Dynamique (générateur `ode`)

| Expérience | Niv. | Ce qu'on voit | Curseur / hypothèse |
|---|---|---|---|
| Pendule et Euler | ② | déjà dans le cahier | pas Δt |
| Descente de gradient | ① | un pas trop grand fait diverger | pas η |
| Croissance logistique | ② | Euler dérape | pas |
| Épidémie SIR | ② | pic selon R₀ | R₀ |

## 13. Ce qu'il faut ajouter de générique

Aucun de ces ajouts n'est propre à un théorème, donc la règle « pas de code par théorème » est respectée.

1. **Trois méthodes paramétrées** par un champ `kind` dans `args`, chacune enregistrée une seule fois avec `@register_method` :
   - `statistic` : somme, moyenne, max, min, médiane, etc.
   - `classifier` : knn, lda, qda, nb, tree, forest, seuil.
   - `regressor` : ols, poly, knn, tree.

   À elles trois, elles couvrent environ 35 des expériences ci-dessus.
2. **Quatre vues génériques** (P1/P2) :
   - `decision_map` : grille de prédictions.
   - `matrix` : matrice de confusion.
   - `bars` : comparer des taux.
   - `population` : grille de personnes colorées pour Bayes.
3. **Des lois de plus** (`beta`, `poisson`, mélange) en option `expr:` du registre, sans toucher au schéma.
4. **Les hyperparamètres** (k, profondeur, degré) sont des `params` avec `sweep_values`, ce qui existe déjà. Les textes Fiable / Fragile / Rompu se règlent avec `texts` pour parler de « sur-apprentissage » plutôt que d'« hypothèse cassée ».
5. **À vérifier** : que `cumsum` et `argmax` sont dans la liste blanche NumPy, car « premier pile » et la marche aléatoire en ont besoin.

### Ce qui rentre déjà dans le moteur sans toucher aux contrats

| Idée | Vue existante | Curseur |
|---|---|---|
| Somme de dés, géométrique, mélange | `distribution` (avec `theory`) | nb de dés, p, θ |
| LGN du dé | `repetitions` (trajectoires) | n |
| Seuil + ROC | `distribution` (avec `threshold`) + `curves` | seuil |
| U train/test du kNN | `sensitivity` / `curves` | k |
| Carrés des résidus | `scatter` avec `segments` | pente |
| Cibles biais-variance | `scatter` + `truth` | biais, variance |

Les frontières du kNN, les arbres en rectangles et la cible dessinée avec ses anneaux demandent une nouvelle vue générique : à classer en P1/P2.

## 14. Pour que l'app paraisse simple

- Trier la galerie avec le champ `level` (Découverte / Intermédiaire / Avancé). Les expériences actuelles sont « Avancé ».
- Une phrase d'accroche sous chaque graphique, par exemple « Plus vous ajoutez de dés, plus la somme ressemble à une cloche ».
- Un seul curseur visible au départ, les autres repliés.
- Tous les textes de l'interface en français, au vouvoiement.
- Pour le pitch : une démo avec les dés, puis le seuil ROC, se comprend en 10 secondes sans prérequis.

## 15. Par où commencer

Pour vérifier que le schéma YAML tient, écrire d'abord **trois expériences très différentes** :

1. **Somme de dés** (archétype 1) : générateur `random`, méthode `statistic`, vue `distribution`.
2. **Seuil et ROC** (archétype 6) : deux lois de scores, vue `distribution` avec `threshold`, plus `curves`.
3. **Carrés des résidus** (archétype 9) : vue `scatter` avec `segments`.

Si ces trois-là s'écrivent sans changer un contrat, les autres suivent. À chaque expérience, appliquer la règle de R2 : simuler avant d'écrire les seuils (`ok_within`, `broken_beyond`) dans le YAML, et ne jamais écrire de chiffre en dur dans les textes (utiliser `{value}`).
