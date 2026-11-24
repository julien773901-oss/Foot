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
- 65 compétitions (tous les championnats masculins proposés par ESPN + coupes continentales), 2 saisons
  (`NB_SAISONS = 2` dans foot.py). Le recoupement par d'autres sources ne couvre que les 12 d'origine.
  Pas chez ESPN : Suisse, Pologne, Croatie, Ukraine, Corée, Maroc, Égypte, etc.
- Sur la branche `site`, la base est stockée compressée (`foot.db.xz`) : GitHub refuse les fichiers > 100 Mo.

## En ligne depuis le 23 novembre 2026
- Site : https://julien773901-oss.github.io/Foot/
- Dépôt : https://github.com/julien773901-oss/Foot (branche `main` = code, `site` = site publié)
- Mises à jour horaires : onglet Actions du dépôt.
- Aperçu local : `python -m http.server 8000` dans ce dossier, puis http://localhost:8000

## Pour relancer la base à la main
    python foot.py

## Idée proposée, pas encore choisie
- Appli sur téléphone (icône, plein écran, hors connexion, alertes sur iPhone).
