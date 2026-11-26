# Base Foot : où on en est (22 novembre 2026)

## Ce qui est fait (testé en local, pas encore en ligne)
- `foot.py` : met à jour la base `foot.db` (ESPN : matchs, buteurs, cartons, passeurs, compositions, classements)
  et la recoupe avec `sources.py` (LiveScore, TheSportsDB, openfootball, OpenLigaDB, classement officiel Ligue1.fr).
  Écrit aussi `matchs*.json` et `joueurs*.json`, lus par la page.
- `index.html` : le site. Matchs jour par jour, direct, classements, buteurs, passeurs, stats, pronostics,
  fiches match / équipe / joueur, comparateur, favoris, alertes de buts, recherche, thème, partage.
- `sw.js` : nécessaire pour les notifications sur Android.
- `pages.py` : pages statiques pour Google (voir « Ajouté le 25 novembre »).
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

## Ajouté le 25 novembre 2026
- But : toutes ces données doivent être sur un site public, trouvable sur Google. Pas encore de nom de domaine
  (on pourra en brancher un plus tard : changer `SITE` dans pages.py + le canonical de index.html).
- Correction : statuts LiveScore `AW` (tapis vert) et `Aband.` ; les matchs restaient « en direct ».
- Stats joueurs ESPN par match : tirs, cadrés, fautes commises/subies, hors-jeu, arrêts, buts encaissés, poste
  (colonnes de `participations`, `FICHE_VERSION = 3` : relecture progressive de ~70 000 fiches, ~2 jours).
- `NB_DETAILLEES = 4` (compositions + passeurs sur 4 saisons ; les plus anciennes sont effacées de la base).
  Le recoupement par d'autres sources reste sur 2 saisons.
- Carrière saison par saison : `carrieres/0..63.json` (découpage `paquet()` identique dans foot.py et index.html),
  affichée sur la fiche joueur. Avant les saisons détaillées : buts et cartons seulement (« – » = inconnu).
- Pages pour Google (`pages.py`) : `joueur/`, `equipe/`, `competition/`, `plan.html`, `sitemap.xml` (+ sitemap-N.xml).
  ~108 000 pages, ~300 Mo. Site complet ~700-800 Mo : GitHub Pages refuse au-delà de 1 Go, le workflow
  s'arrête à 950 Mo (l'ancien site reste en ligne). Si ça arrive : alléger les pages joueurs ou sortir foot.db.xz du site.
- Google Search Console : site validé et `sitemap.xml` envoyé le 26 novembre 2026.

- Search Console : balise de vérification dans index.html (ne pas l'enlever).
- Identité des joueurs (fiche du site + pages Google) : naissance, âge, nationalité + drapeau, taille, poids, poste.
  Source : fiche athlète ESPN (`sports.core.api.espn.com/v2/sports/soccer/athletes/{id}`), table `identites`,
  lue une fois par joueur, `MAX_IDENTITES` par passage (~27 000 joueurs : ~5 passages). Fichiers `identites/0..63.json`.
  Pays traduits en français via Wikidata (`pays_fr()`, compléments dans `PAYS_EN_PLUS`).
  Seulement les joueurs avec un id ESPN (compositions des 4 dernières saisons) : rien pour LiveScore / football-data.
  Wikidata testé : pied fort quasi absent (6 joueurs), photos pour ~3 400 joueurs seulement → pas utilisé.

- Direct LiveScore : LiveScore refuse les navigateurs (403 avec un en-tête Origin). La page passe chaque minute par un
  relais Cloudflare (Worker gratuit du propriétaire, https://foot-direct.julien773901.workers.dev/, code dans
  `relais-cloudflare.js`, `RELAIS` dans index.html ; 100 000 appels/jour gratuits). S'il ne répond pas : `direct.py`,
  lancé toutes les 5 min par `.github/workflows/direct.yml`, publie `direct.json` sur la branche `direct`, lu via
  raw.githubusercontent.com (5 à 15 min de retard). Scores + minute seulement (pas de buteurs en direct).
  Pour modifier le relais : dash.cloudflare.com > Workers & Pages > foot-direct > Edit code, coller relais-cloudflare.js.
- Classements en direct (page, `classementDirect`) : ajoute au classement les matchs commencés moins de 1 h 45 avant
  sa lecture (ou après), en cours compris (🔴). Si une équipe a plus de matchs avant la lecture que « J » (play-offs,
  Apertura/Clausura qui portent le nom du championnat), on garde le classement officiel.

- Page restée ouverte : `rafraichir()` relit matchs.json toutes les 10 min et quand l'onglet redevient visible
  (avant, résultats et classements restaient ceux de l'ouverture de la page ; le lendemain, retour sur « aujourd'hui »).

## Correction du 26 novembre 2026 : site trop gros
- Les passages #71 et #72 ont échoué : le site avait atteint 950 Mo (limite du workflow, l'ancien site restait en ligne).
- La base `foot.db.xz` (~50 Mo) est maintenant rangée sur une branche à part `base` (écrasée à chaque passage, pas
  publiée par GitHub Pages) ; le workflow la relit de là (1re fois : encore depuis `site`). Elle est rangée AVANT la
  publication du site : si le site redevient trop gros, le travail de la base n'est plus perdu.
  Lien de téléchargement dans la page : raw.githubusercontent.com/.../base/foot.db.xz.
- `matchs*.json` écrits sans espaces (-9 %, ~34 Mo). Site attendu vers ~820 Mo.

## Pour relancer la base à la main
    python foot.py

## Idée proposée, pas encore choisie
- Appli sur téléphone (icône, plein écran, hors connexion, alertes sur iPhone).
