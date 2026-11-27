# Tests utilisateurs (R4)

Liste à dérouler avec une personne qui découvre Crash-Test (étudiant, membre d'une autre équipe). Durée visée :
15 minutes. **Ne l'aidez pas** : notez où elle hésite, ce qu'elle dit à voix haute, et le temps de chaque tâche.
Lancez le moteur et l'interface (`README.md`), ouvrez http://localhost:5173/ dans une fenêtre neuve (sans historique).

## Avant de commencer
- Phrase d'accueil, identique pour tous : « C'est une application de révision de statistiques. Faites comme si vous
  la découvriez chez vous ; dites à voix haute ce que vous pensez. »
- Ne montrez pas l'écran avant le début. Chronométrez chaque tâche.

## Tâches (dans l'ordre)

| # | Consigne donnée à la personne | Réussi si… | À observer |
|---|---|---|---|
| 1 | « Trouvez une expérience de niveau Découverte sur les probabilités. » | Elle ouvre « Somme de dés » en moins de 30 s. | Utilise-t-elle les filtres ou fait-elle défiler ? |
| 2 | « Dans cette expérience, cassez une hypothèse. » | Un contrôle d'hypothèse est déplacé et le verdict change. | Comprend-elle « Fiable / Fragile / Rompu » sans aide ? |
| 3 | « Revenez à une situation où tout va bien. » | Elle remet l'hypothèse à sa valeur saine ou utilise la Référence. | Trouve-t-elle la Référence ? |
| 4 | « Ouvrez la régression linéaire et faites que l'intervalle de confiance redevienne juste malgré l'hétéroscédasticité. » | Elle active la Correction (HC3) et le verdict repasse à Fiable. | Le bouton Correction est-il visible ? L'équation qui change de couleur est-elle remarquée ? |
| 5 | « Dans le TCL, avec une loi de Cauchy, suffit-il d'augmenter n pour que la moyenne devienne gaussienne ? » | Elle balaie n (Sensibilité ou balayage automatique) et conclut que non : rien ne répare. | Lit-elle la courbe de Sensibilité ? Compare-t-elle avec la loi exponentielle, qui, elle, marche ? |
| 6 | « Partagez à un ami exactement ce que vous voyez. » | Elle copie le lien ; le lien rouvre le même état. | Trouve-t-elle « Copier le lien » ? |
| 7 | « Faites une série d'entraînement sur une seule expérience. » | Elle termine la série (crans de confiance compris). | Comprend-elle les crans « Je devine / Plutôt sûr / Certain » ? Lit-elle la correction simulée ? |
| 8 | « Après une mauvaise réponse, allez voir dans le Laboratoire pourquoi. » | Elle clique « Ouvrir dans le Laboratoire » et y retrouve l'hypothèse cassée. | — |
| 9 | « Êtes-vous trop sûr de vous ? » | Elle ouvre le Bilan et lit la phrase d'accroche. | Le score de Brier est-il compris ? La courbe (après 20 réponses) ? |
| 10 | « Vérifiez ce fichier YAML. » (donnez l'exemple de l'écran Import avec une faute de frappe) | Elle ouvre Import, colle le texte, clique la ligne fautive et corrige. | Le lien « Importer une expérience » est-il trouvé depuis l'accueil ? |

## Questions de fin (2 minutes)
1. En une phrase, à quoi sert cette application ?
2. Qu'est-ce qui vous a le plus surpris ?
3. À quel moment vous êtes-vous senti perdu ?
4. Sur 10, utiliseriez-vous cet outil pour réviser un partiel ?

## Feuille de relevé (une par personne)

| Tâche | Temps | Réussie (oui / avec aide / non) | Remarque |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |

## Après les tests
- Tout blocage rencontré par 2 personnes ou plus devient une ligne dans `docs/passation.md` (propriétaire du fichier
  concerné, section 3 de `CLAUDE.md`). Après H25 (13 h), seules les corrections de bugs sont permises.
- Les phrases marquantes des testeurs peuvent servir au pitch (avec leur accord).
