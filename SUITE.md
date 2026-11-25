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
- 65 compétitions (tous les championnats masculins proposés par ESPN + coupes continentales).
  Le recoupement par d'autres sources ne couvre que les 12 d'origine.
- Historique : toutes les saisons depuis 2001-02 (`PREMIERE_SAISON` dans foot.py ; ESPN n'a rien avant,
  et beaucoup de ligues seulement depuis ~2008). Rempli par étapes : `MAX_JOURS` journées par passage,
  du plus récent au plus ancien (~20 passages horaires). Passeurs et compositions : 2 dernières saisons
  seulement (`NB_DETAILLEES`), sinon la base devient trop grosse.

- Coupes nationales et barrages de montée/relégation ESPN ajoutés (fin de LIGUES dans foot.py) : 96 compétitions ESPN.
- Pays absents d'ESPN (~80 pays : Europe, Afrique, Asie, Canada…) + divisions inférieures (3. Liga, National, Serie C…) : lus chez LiveScore
  (`LS_LIGUES` dans sources.py, ids de match « ls… », codes « ls:pays/ligue » dans la page).
  Limites : ~1 an d'historique seulement, pas de compositions ni de statistiques, pas de direct dans la page
  (mise à jour horaire seulement), buteurs/passeurs arrivent à la mise à jour qui suit la fin du match.

- football-data.co.uk (fichiers CSV gratuits, scores seulement) : saisons 1993-94 à 2000-01 pour 22 championnats
  européens, et 2012 à 2025 pour Suisse, Pologne, Roumanie, Irlande, Finlande (ids « fd… », chaque fichier lu une
  seule fois) ; sert aussi à recouper les scores ESPN des 2 dernières saisons. Pas de classement pour ces saisons.
- Refusés : L'Équipe (bloque tout accès automatique), matchendirect.fr (robots.txt interdit Anthropic).
  A Bola autorise les robots mais ferait doublon avec ESPN pour le Portugal.

## Notes LiveScore (24 nov.)
- matchendirect.fr refusé : son robots.txt interdit les robots d'Anthropic.
- API LiveScore (`prod-public-api.livescore.com/v1/api/app/...`) :
  - `date/soccer/AAAAMMJJ/0?locale=en&MD=1` : tous les matchs du jour (Stages[].Ccd/Scd, Events[].Eid, Esd en UTC,
    T1/T2[0].Nm/Img, Tr1/Tr2, Eps = FT / AET / AP / NS / Postp. / Canc.)
  - `stage/soccer/{Ccd}/{Scd}/0?locale=en&MD=1` : saison en cours + `LeagueTable` (rnk, Tnm, Img, pld, win, drw, lst, gf, ga, pts)
  - `incidents/soccer/{Eid}?locale=en` : Incs = {période: [...]}, équipe = champ `Nm` (1 ou 2).
    IT 36 but, 37 penalty marqué, 39 csc (compté pour l'équipe `Nm`, vérifié sur 240 matchs), 63 passe,
    43 jaune, 44 2e jaune, 45 rouge, 38 penalty raté.
  - logos : `https://lsm-static-prod.livescore.com/medium/` + Img
- Codes (Ccd/Scd, les phases « -championship-group », « -relegation-group », « -promotion »… commencent pareil) :
  switzerland super-league, challenge-league, cup · poland ekstraklasa, i-liga, ii-liga, cup ·
  croatia 1st-league, 2nd-league · ukraine premier-league, persha-liga, cup · korea-republic k-league-1, k-league-2, cup ·
  morocco botola-pro · egypt premier-league, 2-division-a, cup, league-cup
- `LeagueTable` : prendre les tables LTT=1 (2 = domicile, 3 = extérieur). Les phases « -championship-group » d'une
  saison finie portent « 25/26 » dans leur nom. La page « date » ne renvoie plus rien au-delà d'environ 1 an.
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
