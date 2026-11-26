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
  Wikidata testé : pied fort quasi absent (6 joueurs) → pas utilisé. Photos : voir « Photos des joueurs » plus bas.

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

## Vieilles saisons dans un 2e dépôt : Foot-archives (26 novembre 2026)
- Chaque site GitHub Pages est limité à 1 Go. Les fichiers `matchs-AAAA.json` et `joueurs-AAAA.json` des saisons de plus
  de 5 ans (~250 Mo) sont publiés dans le dépôt `Foot-archives` (son propre site GitHub Pages, branche `main` écrasée),
  plus sur la branche `site`. Le site descend vers ~600 Mo.
- La page (`lireJson()` dans index.html) cherche d'abord le fichier sur le site, puis à l'adresse `ARCHIVES`.
- Envoi vers Foot-archives : une fois par jour (passage de 3 h UTC), ou au lancement à la main / changement de code,
  ou si le dépôt d'archives est vide. Les autres passages gardent ce qui y est déjà.
- Il faut un jeton GitHub dans le secret `ARCHIVES_TOKEN` du dépôt Foot (droit « Contents : lecture et écriture » sur
  Foot-archives seulement). Sans jeton, ou si l'envoi échoue (jeton expiré…), tout reste sur le site comme avant
  (avertissement jaune dans Actions) : penser à RENOUVELER LE JETON avant sa date d'expiration.

## Photos des joueurs (26 novembre 2026)
- Avant : seulement la photo ESPN par id (≈ 4 % des 42 680 joueurs ESPN). Après : ≈ 27 % (≈ 11 500 joueurs).
- 1) Photo ESPN (`a.espncdn.com/i/headshots/...`), vérifiée par une requête HEAD : colonnes `espn_photo` (1/0) et
  `photo_lu` de la table `identites`, `MAX_PHOTOS_ESPN` = 8000 par passage (~3,5 min ; toute la base en ~6 passages),
  un joueur sans photo est revérifié après 60 jours.
- 2) Sinon photo Wikimedia Commons trouvée par Wikidata (`photos_wikidata()`, colonne `commons` = nom du fichier) :
  une requête CSV (~72 000 footballeurs avec photo + date de naissance, ~10-15 s), puis leurs noms (table `wikidata`,
  lus une seule fois ; ~3 min la 1re fois, ~20 s ensuite). Correspondance : id ESPN (P3681) avec nom concordant,
  ou même date de naissance + nom proche (`meme_nom()`) avec un seul candidat (homonymes nés le même jour : rien).
  Le lien P3681 seul n'est pas fiable (6 erreurs sur 1 686), d'où la vérification du nom.
- Les images ne sont PAS copiées sur le site : seulement l'adresse, dans `identites/N.json` (7e valeur = adresse,
  8e = fichier Commons pour le crédit). Commons : `Special:FilePath/<fichier>?width=250` (largeur standard).
- Crédit : « Photo : Commons » (fiche du site) / « Photo : Wikimedia Commons » (page Google), lien vers la page du
  fichier (auteur + licence y sont indiqués). L'API Commons limite trop les requêtes pour lire chaque licence.
- Non utilisé : TheSportsDB (une requête par joueur, déjà « trop de requêtes » sur le recoupement des scores,
  images envoyées par les utilisateurs sans licence claire). Joueurs LiveScore / football-data : pas de date de
  naissance, donc pas de correspondance sûre → pas de photo.

## Plus de compétitions (26 novembre 2026)
- Inventaire : ESPN propose 220 compétitions, le site en lisait 96 ; LiveScore, sur 60 jours de l'année, avait 80 % de
  matchs non lus (surtout doublons d'ESPN, jeunes, réserves, divisions régionales).
- Ajoutées chez ESPN (96, `LIGUES`, 192 au total) : sélections nationales (Coupe du monde + éliminatoires de chaque
  continent, Euro, Ligue des nations, CAN, Copa América, Gold Cup, Coupe d'Asie, amicaux…), qualifications européennes,
  Supercoupes, Coupe du monde des clubs, championnats d'État du Brésil, et 35 compétitions féminines (`FEMININ`).
- Ajoutées chez LiveScore (`LS_LIGUES`) : National League North/South (Angleterre), Liga II (Roumanie), NB II (Hongrie),
  Division 1 Nord/Sud (Suède), Primera C (Argentine), División Intermedia (Paraguay), MLS Next Pro ; championnats
  féminins d'Allemagne, Italie, Suède, Norvège, Danemark, Portugal, Japon, Finlande, Irlande (`LS_FEMININ`).
- Équipes féminines : « Nom (F) » (`S.feminin()`) car ESPN leur donne le même nom que les hommes ; la page garde le
  « (F) » en direct grâce à la liste `feminin` de matchs.json.
- Non retenus : jeunes (U17 à U23), universitaires (NCAA), amicaux de clubs et tournois d'été, tours préliminaires amateurs
  (FA Cup, Coupe d'Écosse), USL League Two (amateur) : beaucoup de pages pour peu d'intérêt, et la taille du site.
- Historique : ~45 000 à 50 000 matchs de plus (~600/an en 2005, ~4 200/an en 2025), lus par `MAX_JOURS` : ~30 passages
  (~1,5 jour) de ~25 min de plus. Classements : lus à 4 en parallèle (~2 400 la 1re fois).
- Taille : ~+45 Mo sur le site. À mettre en ligne SEULEMENT quand les archives (Foot-archives) fonctionnent.
- Autres sources gratuites regardées : rien de plus large que ESPN + LiveScore sans clé ; FBref, Transfermarkt,
  L'Équipe, matchendirect.fr déjà refusés (conditions / robots.txt).

## Pour relancer la base à la main
    python foot.py

## Idée proposée, pas encore choisie
- Appli sur téléphone (icône, plein écran, hors connexion, alertes sur iPhone).
