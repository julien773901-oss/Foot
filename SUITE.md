# Base Foot : où on en est (22 novembre 2026)

## Ce qui est fait (testé en local, pas encore en ligne)
- `foot.py` : met à jour la base `foot.db` (ESPN : matchs, buteurs, cartons, passeurs, compositions, classements)
  et la recoupe avec `sources.py` (LiveScore, TheSportsDB, openfootball, OpenLigaDB, classement officiel Ligue1.fr).
  Écrit aussi `matchs*.json` et `joueurs*.json`, lus par la page.
- `index.html` : le site. Matchs jour par jour, direct, classements, buteurs, passeurs, stats, pronostics,
  fiches match / équipe / joueur, comparateur, favoris, alertes de buts, recherche, thème, partage.
- `sw.js` : nécessaire pour les notifications sur Android.
- `.github/workflows/maj.yml` : mise à jour automatique toutes les heures sur GitHub ; le site est publié
  sur une branche `site` (écrasée à chaque fois pour garder le dépôt léger).
- 12 compétitions, 2 saisons (`NB_SAISONS = 2` dans foot.py).

## Prochaine étape : la mise en ligne
1. Créer un dépôt **public et vide** sur github.com (par exemple `foot`), puis donner son adresse à Claude.
2. Claude enregistre les fichiers (commit) et les envoie ; c'est toi qui te connectes à GitHub quand la fenêtre s'ouvre.
3. Sur GitHub : Settings → Pages → branche `site` ; vérifier que Actions est activé.
4. Le premier lancement prend environ 10 à 15 minutes. Passeurs et compositions sont complets au bout d'environ 11 mises à jour horaires.

## Pour relancer la base à la main
    python foot.py

## Idée proposée, pas encore choisie
- Appli sur téléphone (icône, plein écran, hors connexion, alertes sur iPhone).
