"""Met à jour foot.db : matchs (avec logos et buteurs) et classements.
1er lancement : toute la saison. Ensuite : 7 jours avant / 14 jours après + les jours jamais lus correctement.
Lancer : python foot.py"""
import csv, io, json, re, sqlite3, sys, time, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
import sources as S
import pages as P

# shortcut: API ESPN non officielle et sans clé, elle peut changer ; passer à football-data.org (clé gratuite) si elle casse.
API = "https://site.api.espn.com/apis"
LIGUES = {"fra.1": "Ligue 1", "eng.1": "Premier League", "esp.1": "La Liga",
          "ita.1": "Serie A", "ger.1": "Bundesliga", "uefa.champions": "Ligue des champions",
          "fra.2": "Ligue 2", "uefa.europa": "Ligue Europa", "uefa.europa.conf": "Ligue Conférence",
          "fra.coupe_de_france": "Coupe de France", "por.1": "Liga Portugal", "ned.1": "Eredivisie",
          # Europe
          "eng.2": "Championship (Angleterre)", "eng.3": "League One (Angleterre)", "eng.4": "League Two (Angleterre)",
          "eng.5": "National League (Angleterre)", "esp.2": "LaLiga 2 (Espagne)", "ger.2": "2. Bundesliga (Allemagne)",
          "ita.2": "Serie B (Italie)", "ned.2": "Eerste Divisie (Pays-Bas)", "sco.1": "Premiership (Écosse)",
          "sco.2": "Championship (Écosse)", "bel.1": "Pro League (Belgique)", "tur.1": "Süper Lig (Turquie)",
          "rus.1": "Premier Liga (Russie)", "aut.1": "Bundesliga (Autriche)", "gre.1": "Super League (Grèce)",
          "swe.1": "Allsvenskan (Suède)", "den.1": "Superliga (Danemark)", "nor.1": "Eliteserien (Norvège)",
          # Amériques
          "usa.1": "MLS (États-Unis)", "usa.usl.1": "USL Championship (États-Unis)", "usa.usl.l1": "USL League One (États-Unis)",
          "mex.1": "Liga MX (Mexique)", "mex.2": "Liga de Expansión (Mexique)", "arg.1": "Liga Profesional (Argentine)",
          "arg.2": "Primera Nacional (Argentine)", "arg.3": "Primera B (Argentine)", "bra.1": "Série A (Brésil)",
          "bra.2": "Série B (Brésil)", "chi.1": "Primera División (Chili)", "uru.1": "Primera División (Uruguay)",
          "col.1": "Primera A (Colombie)", "per.1": "Liga 1 (Pérou)", "par.1": "Primera División (Paraguay)",
          "ecu.1": "LigaPro (Équateur)", "ven.1": "Primera División (Venezuela)", "bol.1": "División Profesional (Bolivie)",
          "hon.1": "Liga Nacional (Honduras)", "crc.1": "Primera División (Costa Rica)", "gua.1": "Liga Nacional (Guatemala)",
          "slv.1": "Primera División (Salvador)",
          # Asie, Océanie, Afrique
          "jpn.1": "J1 League (Japon)", "chn.1": "Super League (Chine)", "aus.1": "A-League (Australie)",
          "ksa.1": "Saudi Pro League (Arabie saoudite)", "ind.1": "Indian Super League (Inde)", "ind.2": "I-League (Inde)",
          "rsa.1": "Premiership (Afrique du Sud)",
          # coupes continentales de clubs
          "conmebol.libertadores": "Copa Libertadores", "conmebol.sudamericana": "Copa Sudamericana",
          "concacaf.champions": "Coupe des champions CONCACAF", "afc.champions": "Ligue des champions AFC",
          "caf.champions": "Ligue des champions CAF", "caf.confed": "Coupe de la Confédération CAF",
          # coupes nationales
          "eng.fa": "FA Cup (Angleterre)", "eng.league_cup": "Coupe de la Ligue (Angleterre)", "eng.trophy": "EFL Trophy (Angleterre)",
          "esp.copa_del_rey": "Coupe du Roi (Espagne)", "ger.dfb_pokal": "Coupe d'Allemagne", "ita.coppa_italia": "Coupe d'Italie",
          "ned.cup": "Coupe des Pays-Bas", "por.taca.portugal": "Coupe du Portugal", "sco.tennents": "Coupe d'Écosse",
          "sco.cis": "Coupe de la Ligue (Écosse)", "usa.open": "US Open Cup (États-Unis)", "arg.copa": "Coupe d'Argentine",
          "bra.copa_do_brazil": "Coupe du Brésil", "chi.copa_chi": "Coupe du Chili", "col.copa": "Coupe de Colombie",
          "bol.copa": "Coupe de Bolivie", "ksa.kings.cup": "Coupe du Roi (Arabie saoudite)",
          # barrages de montée / relégation
          "fra.1.promotion.relegation": "Barrages Ligue 1 / Ligue 2", "ger.playoff.relegation": "Barrages Bundesliga (Allemagne)",
          "ger.2.promotion.relegation": "Barrages 2. Bundesliga (Allemagne)", "rus.1.promotion.relegation": "Barrages (Russie)",
          "bel.promotion.relegation": "Barrages (Belgique)", "por.1.promotion.relegation": "Barrages (Portugal)",
          "sco.1.promotion.relegation": "Barrages Premiership (Écosse)", "sco.2.promotion.relegation": "Barrages Championship (Écosse)",
          "ned.playoff.relegation": "Barrages (Pays-Bas)", "swe.1.promotion.relegation": "Barrages (Suède)",
          "nor.1.promotion.relegation": "Barrages (Norvège)", "chi.1.promotion.relegation": "Barrages (Chili)",
          "bol.ply.rel": "Barrages (Bolivie)", "chn.1.promotion.relegation": "Barrages (Chine)",
          # sélections nationales (ajoutées le 26 novembre 2026)
          "fifa.world": "Coupe du monde", "fifa.worldq.uefa": "Éliminatoires Coupe du monde (Europe)",
          "fifa.worldq.conmebol": "Éliminatoires Coupe du monde (Amérique du Sud)",
          "fifa.worldq.concacaf": "Éliminatoires Coupe du monde (CONCACAF)", "fifa.worldq.caf": "Éliminatoires Coupe du monde (Afrique)",
          "fifa.worldq.afc": "Éliminatoires Coupe du monde (Asie)", "fifa.worldq.ofc": "Éliminatoires Coupe du monde (Océanie)",
          "fifa.wcq.ply": "Barrages intercontinentaux Coupe du monde", "fifa.friendly": "Matchs amicaux internationaux",
          "fifa.olympics": "Tournoi olympique", "uefa.euro": "Euro", "uefa.euroq": "Éliminatoires de l'Euro",
          "uefa.nations": "Ligue des nations UEFA", "global.finalissima": "Finalissima",
          "caf.nations": "Coupe d'Afrique des nations", "caf.nations_qual": "Éliminatoires CAN", "caf.championship": "CHAN (Afrique)",
          "caf.cosafa": "Coupe COSAFA", "conmebol.america": "Copa América", "concacaf.gold": "Gold Cup",
          "concacaf.gold_qual": "Éliminatoires Gold Cup", "concacaf.nations.league": "Ligue des nations CONCACAF",
          "concacaf.central.american.cup": "Coupe d'Amérique centrale", "afc.asian.cup": "Coupe d'Asie des nations",
          "afc.cupq": "Éliminatoires Coupe d'Asie", "aff.championship": "Championnat ASEAN", "afc.saff.championship": "Championnat SAFF",
          "global.gulf_cup": "Coupe du Golfe",
          # clubs : coupes internationales, qualifications, supercoupes, championnats d'État du Brésil
          "fifa.cwc": "Coupe du monde des clubs", "fifa.intercontinental_cup": "Coupe intercontinentale FIFA",
          "uefa.super_cup": "Supercoupe de l'UEFA", "uefa.champions_qual": "Ligue des champions (qualifications)",
          "uefa.europa_qual": "Ligue Europa (qualifications)", "uefa.europa.conf_qual": "Ligue Conférence (qualifications)",
          "afc.champions_qual": "Ligue des champions AFC (qualifications)", "afc.cup": "Ligue des champions AFC Two",
          "afc.cup_qual": "Ligue des champions AFC Two (qualifications)", "conmebol.recopa": "Recopa Sudamericana",
          "concacaf.leagues.cup": "Leagues Cup", "campeones.cup": "Campeones Cup",
          "fra.super_cup": "Trophée des champions", "esp.super_cup": "Supercoupe d'Espagne", "ita.super_cup": "Supercoupe d'Italie",
          "ger.super_cup": "Supercoupe d'Allemagne", "ned.supercup": "Supercoupe des Pays-Bas", "eng.charity": "Community Shield (Angleterre)",
          "arg.supercopa": "Supercoupe d'Argentine", "arg.trofeo_de_la_campeones": "Trophée des champions (Argentine)",
          "arg.supercopa.internacional": "Supercoupe internationale (Argentine)", "arg.copa_de_la_superliga": "Copa de la Superliga (Argentine)",
          "bra.supercopa_do_brazil": "Supercoupe du Brésil", "chi.super_cup": "Supercoupe du Chili", "col.superliga": "Superliga (Colombie)",
          "mex.campeon": "Campeón de Campeones (Mexique)", "par.1.supercopa": "Supercoupe du Paraguay",
          "sco.challenge": "Challenge Cup (Écosse)", "usa.usl.l1.cup": "USL Cup (États-Unis)",
          "bra.camp.paulista": "Campeonato Paulista (Brésil)", "bra.camp.carioca": "Campeonato Carioca (Brésil)",
          "bra.camp.mineiro": "Campeonato Mineiro (Brésil)", "bra.camp.gaucho": "Campeonato Gaúcho (Brésil)",
          # football féminin (équipes suffixées « (F) », voir FEMININ)
          "fifa.wwc": "Coupe du monde féminine", "fifa.wworldq.uefa": "Éliminatoires Coupe du monde féminine (Europe)",
          "fifa.wwcq.ply": "Barrages Coupe du monde féminine", "fifa.friendly.w": "Matchs amicaux internationaux féminins",
          "fifa.w.olympics": "Tournoi olympique féminin", "fifa.w.champions_cup": "Coupe des champions féminine FIFA",
          "uefa.weuro": "Euro féminin", "uefa.w.nations": "Ligue des nations féminine UEFA",
          "uefa.wchampions": "Ligue des champions féminine", "uefa.wchampions_qual": "Ligue des champions féminine (qualifications)",
          "uefa.w.europa": "Coupe d'Europe féminine", "caf.w.nations": "CAN féminine", "conmebol.america.femenina": "Copa América féminine",
          "concacaf.w.gold": "Gold Cup féminine", "concacaf.womens.championship": "Championnat féminin CONCACAF",
          "concacaf.w.champions_cup": "Coupe des champions féminine CONCACAF", "afc.w.asian.cup": "Coupe d'Asie féminine",
          "fifa.shebelieves": "SheBelieves Cup", "global.arnold.clark_cup": "Arnold Clark Cup", "global.pinatar_cup": "Pinatar Cup",
          "global.w.finalissima": "Finalissima féminine",
          "eng.w.1": "Women's Super League (Angleterre)", "eng.w.fa": "FA Cup féminine (Angleterre)",
          "eng.w.league_cup": "Coupe de la Ligue féminine (Angleterre)", "esp.w.1": "Liga F (Espagne)",
          "esp.copa_de_la_reina": "Coupe de la Reine (Espagne)", "fra.w.1": "Première Ligue (France, féminin)",
          "ned.w.1": "Eredivisie féminine (Pays-Bas)", "ned.w.knvb_cup": "Coupe des Pays-Bas féminine", "usa.nwsl": "NWSL (États-Unis)",
          "usa.nwsl.cup": "NWSL Challenge Cup (États-Unis)", "usa.w.usl.1": "USL Super League (États-Unis, féminin)",
          "mex.w.1": "Liga MX Femenil (Mexique)", "aus.w.1": "A-League féminine (Australie)", "can.w.nsl": "Northern Super League (Canada, féminin)"}
# compétitions féminines : ESPN donne aux équipes le même nom que chez les hommes (« Manchester United ») ; on ajoute « (F) »
# pour ne pas mélanger leurs résultats sur les fiches équipes. Non retenus : jeunes (U17 à U23), universitaires (NCAA),
# amicaux de clubs et tournois d'été, tours préliminaires amateurs (FA Cup, Coupe d'Écosse) : beaucoup de pages pour peu d'intérêt.
FEMININ = {"fifa.wwc", "fifa.wworldq.uefa", "fifa.wwcq.ply", "fifa.friendly.w", "fifa.w.olympics", "fifa.w.champions_cup",
           "uefa.weuro", "uefa.w.nations", "uefa.wchampions", "uefa.wchampions_qual", "uefa.w.europa", "caf.w.nations",
           "conmebol.america.femenina", "concacaf.w.gold", "concacaf.womens.championship", "concacaf.w.champions_cup",
           "afc.w.asian.cup", "fifa.shebelieves", "global.arnold.clark_cup", "global.pinatar_cup", "global.w.finalissima",
           "eng.w.1", "eng.w.fa", "eng.w.league_cup", "esp.w.1", "esp.copa_de_la_reina", "fra.w.1", "ned.w.1", "ned.w.knvb_cup",
           "usa.nwsl", "usa.nwsl.cup", "usa.w.usl.1", "mex.w.1", "aus.w.1", "can.w.nsl"}
DB = Path(__file__).with_name("foot.db")


get = S.get  # avec nouvelles tentatives si la source bloque


def buteurs(c, id_dom):
    out = []
    for d in c.get("details", []):
        if not d.get("scoringPlay") or d.get("shootout"):
            continue
        noms = d.get("athletesInvolved") or [{"displayName": "?"}]
        tag = " (csc)" if d.get("ownGoal") else " (pen)" if d.get("penaltyKick") else ""
        out.append({"cote": "dom" if d["team"]["id"] == id_dom else "ext",
                    "min": d["clock"]["displayValue"], "nom": noms[0]["displayName"] + tag})
    return out


def cartons(c, id_dom):
    return [{"cote": "dom" if d["team"]["id"] == id_dom else "ext", "min": d["clock"]["displayValue"],
             "nom": (d.get("athletesInvolved") or [{"displayName": "?"}])[0]["displayName"],
             "type": "R" if d.get("redCard") else "J"}
            for d in c.get("details", []) if d.get("redCard") or d.get("yellowCard")]


def passes(summary):
    """Passeurs décisifs, lus dans la fiche détaillée du match (le 2e participant d'un but)."""
    comp = summary["header"]["competitions"][0]["competitors"]
    id_dom = next(t["team"]["id"] for t in comp if t["homeAway"] == "home")
    out = []
    for k in summary.get("keyEvents", []):
        t = k["type"]["text"]
        if k.get("scoringPlay") and t.startswith("Goal") and "Own" not in t and "Penalty" not in t \
                and len(k.get("participants", [])) > 1:
            out.append({"cote": "dom" if k["team"]["id"] == id_dom else "ext",
                        "min": k.get("clock", {}).get("displayValue", ""), "nom": k["participants"][1]["athlete"]["displayName"]})
    return out


STATS_ESPN = ["totalShots", "shotsOnTarget", "foulsCommitted", "foulsSuffered", "offsides", "saves", "goalsConceded"]
PART_COLS = ["match_id", "joueur", "id_espn", "cote", "titulaire", "entre", "sorti", "poste",
             "tirs", "cadres", "fautes", "subies", "hors_jeu", "arrets", "encaisses"]


def participations(summary):
    """Joueurs ayant joué : [(joueur, id_espn, cote, titulaire, entre, sorti, poste, *STATS_ESPN)]
    (les remplaçants restés sur le banc sont exclus ; stats = None quand ESPN ne les donne pas)."""
    comp = summary["header"]["competitions"][0]["competitors"]
    id_dom = next(t["team"]["id"] for t in comp if t["homeAway"] == "home")
    out = []
    for eq in summary.get("rosters", []):
        cote = "dom" if eq["team"]["id"] == id_dom else "ext"
        for p in eq.get("roster", []):
            if p.get("starter") or p.get("subbedIn"):
                st = {s["name"]: s.get("value") for s in p.get("stats", [])}
                poste = p.get("position", {}).get("abbreviation")
                out.append((p["athlete"]["displayName"], p["athlete"].get("id"), cote,
                            int(bool(p.get("starter"))), int(bool(p.get("subbedIn"))), int(bool(p.get("subbedOut"))),
                            None if poste == "SUB" else poste,
                            *(None if st.get(k) is None else int(st[k]) for k in STATS_ESPN)))
    return out


FICHE_VERSION = 3  # 3 = tirs, fautes, hors-jeu, arrêts... ; monter ce numéro force la relecture des fiches (ex. quand on y lit une nouvelle info)
COLS = ["id", "ligue", "date_utc", "domicile", "exterieur", "buts_dom", "buts_ext", "statut", "logo_dom",
        "logo_ext", "buteurs", "cartons", "maj"]


def parse(event, ligue, feminin=False):
    c = event["competitions"][0]
    eq = {t["homeAway"]: t for t in c["competitors"]}
    h, a = eq["home"], eq["away"]
    nom = lambda t: S.feminin(t["team"]["displayName"]) if feminin else t["team"]["displayName"]
    statut = event["status"]["type"]["name"]
    joue = statut != "STATUS_SCHEDULED"  # pas de score tant que le match n'a pas commencé
    score = lambda t: int(t["score"]) if joue and t.get("score") not in (None, "") else None
    return (event["id"], ligue, event["date"], nom(h), nom(a),
            score(h), score(a), statut, h["team"].get("logo"), a["team"].get("logo"),
            json.dumps(buteurs(c, h["team"]["id"]), ensure_ascii=False),
            json.dumps(cartons(c, h["team"]["id"]), ensure_ascii=False))


PREMIERE_SAISON = 2001  # ESPN n'a rien avant (2001-02 pour les grands championnats, ~2008 pour beaucoup d'autres)
NB_DETAILLEES = 4  # passeurs + compositions seulement pour les saisons récentes : ~13 Mo compressés par saison, limite GitHub 100 Mo
MAX_JOURS = 30000  # journées ESPN lues par passage (~25 min) ; l'historique se remplit en ~20 passages, du plus récent au plus ancien


def saison_de(d):
    """Une saison va de juillet à juin ; on la nomme par son année de départ (2025 = 2025-26)."""
    return int(d[:4]) if int(d[5:7]) >= 7 else int(d[:4]) - 1


def classement(code, ligue, saison):
    lignes = []
    for groupe in get(f"{API}/v2/sports/soccer/{code}/standings?season={saison}").get("children", []):
        for e in groupe["standings"]["entries"]:
            s = {x["name"]: x.get("value") for x in e["stats"]}
            n = lambda k: int(s.get(k) or 0)
            lignes.append((ligue, groupe["name"], n("rank"), S.feminin(e["team"]["displayName"]) if code in FEMININ else e["team"]["displayName"],
                           (e["team"].get("logos") or [{}])[0].get("href"), n("gamesPlayed"), n("wins"),
                           n("ties"), n("losses"), n("pointsFor"), n("pointsAgainst"), n("points"), saison))
    return lignes


def jour(code, ligue, j):
    try:
        if code.startswith("livescore"):  # une seule page par jour pour toutes les ligues lues chez LiveScore
            return S.ls_jour(j), True
        return [parse(ev, ligue, code in FEMININ) for ev in get(f"{API}/site/v2/sports/soccer/{code}/scoreboard?dates={j}").get("events", [])], True
    except Exception as e:
        print(f"[erreur] {ligue} {j}: {e}", file=sys.stderr)
        return [], False


MAX_IDENTITES = 6000  # ~0,4 s par joueur sur 4 fils : ~10 min par passage ; ~27 000 joueurs à lire au départ


POSTES = {"Goalkeeper": "Gardien", "Defender": "Défenseur", "Midfielder": "Milieu", "Forward": "Attaquant"}


def identite(a):
    """Fiche athlète ESPN -> (naissance AAAA-MM-JJ, nationalité, code drapeau, taille cm, poids kg, poste)."""
    drapeau = (a.get("flag") or {}).get("href", "").rsplit("/", 1)[-1].removesuffix(".png") or None
    poste = (a.get("position") or {}).get("name")
    return ((a.get("dateOfBirth") or "")[:10] or None, a.get("citizenship") or None, drapeau,
            round(a["height"] * 2.54) if a.get("height") else None,  # ESPN : pouces et livres
            round(a["weight"] * 0.4536) if a.get("weight") else None, POSTES.get(poste, poste))


PAYS_EN_PLUS = {"USA": "États-Unis", "Côte d'Ivoire": "Côte d'Ivoire", "Congo DR": "RD Congo", "Türkiye": "Turquie",
                "Netherlands": "Pays-Bas", "China PR": "Chine"}  # noms ESPN absents ou mal traduits par Wikidata


def pays_fr():
    """Nom anglais (ESPN) -> nom français, d'après Wikidata (pays avec code ISO + nations du Royaume-Uni).
    shortcut: un pays inconnu reste en anglais ; ajouter son nom dans PAYS_EN_PLUS."""
    q = ('SELECT ?en ?fr WHERE { { ?c wdt:P297 [] } UNION { VALUES ?c { wd:Q21 wd:Q22 wd:Q25 wd:Q26 } } ?c rdfs:label ?fr . '
         'FILTER(lang(?fr)="fr") { ?c rdfs:label ?en } UNION { ?c skos:altLabel ?en } FILTER(lang(?en)="en") }')
    try:
        d = {}
        for b in get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q))["results"]["bindings"]:
            d.setdefault(b["en"]["value"], b["fr"]["value"])
        return d | PAYS_EN_PLUS
    except Exception as e:
        print(f"[erreur] noms de pays Wikidata : {e}", file=sys.stderr)
        return PAYS_EN_PLUS


# ---------- photos des joueurs ----------
# 1) photo ESPN (portrait détouré, même style pour tous) quand elle existe : ~3 % des joueurs seulement ;
# 2) sinon photo de Wikimedia Commons (libre de droits, crédit + lien vers la page du fichier), trouvée par Wikidata :
#    lien direct par l'id ESPN (P3681) ou même date de naissance + nom proche (un seul candidat, sinon rien).
# On stocke seulement l'adresse : les images ne sont pas copiées sur le site (limite de 1 Go).
ESPN_PHOTO = "https://a.espncdn.com/i/headshots/soccer/players/full/{}.png"
COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/"  # redirige vers la miniature (largeurs standard : 250)
MAX_PHOTOS_ESPN = 8000  # vérifications ESPN par passage (~2 min) ; un joueur sans photo est revérifié après 60 jours
WD_UA = {"User-Agent": "base-foot/1.0 (site de statistiques de football)", "Accept": "text/csv"}


def photo_espn(id_espn):
    """1 si ESPN a la photo, 0 sinon, None si on ne sait pas (erreur réseau : nouvel essai au prochain passage)."""
    try:
        urllib.request.urlopen(urllib.request.Request(ESPN_PHOTO.format(id_espn), method="HEAD", headers=S.UA), timeout=20)
        return 1
    except Exception as e:
        return 0 if getattr(e, "code", None) in (403, 404) else None


def sparql(q, essais=3):
    """Requête Wikidata en POST (listes VALUES trop longues pour une adresse), réponse en CSV (4 fois plus légère que
    le JSON : la grosse requête tient sous la limite de 60 s). Renvoie une liste de {colonne: valeur} ("" = absente)."""
    d = urllib.parse.urlencode({"query": q}).encode()
    for i in range(essais):
        try:
            txt = urllib.request.urlopen(urllib.request.Request("https://query.wikidata.org/sparql", data=d, headers=WD_UA),
                                         timeout=120).read().decode()
            return list(csv.DictReader(io.StringIO(txt), strict=True))
        except Exception:  # réponse coupée, serveur surchargé…
            if i == essais - 1:
                raise
            time.sleep(30)


def photo(id_espn, espn, commons):
    """[adresse, fichier Commons] pour l'export ; ESPN d'abord ; [] sans photo."""
    if espn == 1:
        return [ESPN_PHOTO.format(id_espn)]
    return [COMMONS + urllib.parse.quote(commons) + "?width=250", commons] if commons else []


def mots(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", s)


def meme_nom(a, b):
    """« Jesé » / « Jesé Rodríguez », « Hannes Van Der Bruggen » / « Hannes van der Bruggen », translittérations proches."""
    ma, mb = mots(a), mots(b)
    if not ma or not mb:
        return False
    return set(ma) <= set(mb) or set(mb) <= set(ma) or SequenceMatcher(None, " ".join(ma), " ".join(mb)).ratio() >= 0.85


def apparier_photos(joueurs, wd, noms):
    """joueurs : {id_espn: (nom, naissance)} ; wd : {qid: (naissance, fichier Commons, {ids ESPN})} ; noms : {qid: [noms]}.
    Renvoie {id_espn: fichier Commons}. Lien par id ESPN accepté seulement si le nom concorde (quelques erreurs dans Wikidata)."""
    par_espn = {e: q for q, (_, _, es) in wd.items() for e in es}
    par_date = {}
    for q, (d, _, _) in wd.items():
        par_date.setdefault(d, []).append(q)
    out = {}
    for e, (nom, naiss) in joueurs.items():
        q = par_espn.get(e)
        if q and any(meme_nom(nom, n) for n in noms.get(q, [])):
            out[e] = wd[q][1]
            continue
        cands = [q for q in par_date.get(naiss, []) if any(meme_nom(nom, n) for n in noms.get(q, []))] if naiss else []
        if len(cands) == 1:  # deux homonymes nés le même jour : on ne choisit pas
            out[e] = wd[cands[0]][1]
    return out


def photos_wikidata(db, joueurs):
    """Footballeurs Wikidata avec photo + date de naissance (~72 000, une requête de ~15 s), puis leurs noms
    (seulement ceux qui peuvent correspondre ; gardés en base, table wikidata : on ne relit que les nouveaux)."""
    wd = {}
    for b in sparql("SELECT ?p ?d ?img ?espn WHERE { ?p wdt:P106 wd:Q937857 ; wdt:P18 ?img ; wdt:P569 ?d . OPTIONAL { ?p wdt:P3681 ?espn } }"):
        q = b["p"].rsplit("/", 1)[1]
        if "Special:FilePath/" not in b["img"]:
            continue  # valeur « inconnue » de Wikidata, pas un fichier Commons
        x = wd.setdefault(q, (b["d"][:10], urllib.parse.unquote(b["img"].rsplit("Special:FilePath/", 1)[1]), set()))
        if b["espn"]:
            x[2].add(b["espn"])
    dates, ids = {n for _, n in joueurs.values()}, set(joueurs)
    utiles = {q for q, (d, _, es) in wd.items() if d in dates or es & ids}
    noms = {q: json.loads(n) for q, n in db.execute("SELECT qid, noms FROM wikidata")}
    a_lire = sorted(utiles - set(noms))
    for i in range(0, len(a_lire), 3000):  # ~10 s par paquet ; ~11 paquets la 1re fois, presque rien ensuite
        lus = {q: set() for q in a_lire[i:i + 3000]}
        for b in sparql("SELECT ?p ?l WHERE { VALUES ?p { %s } { ?p rdfs:label ?l } UNION { ?p skos:altLabel ?l } "
                        'FILTER(lang(?l) IN ("en","fr","es","de","it","pt","mul")) }' % " ".join("wd:" + q for q in lus)):
            lus[b["p"].rsplit("/", 1)[1]].add(b["l"])
        db.executemany("INSERT OR REPLACE INTO wikidata VALUES (?,?)", [(q, json.dumps(sorted(v), ensure_ascii=False)) for q, v in lus.items()])
        noms |= {q: sorted(v) for q, v in lus.items()}
    return apparier_photos(joueurs, wd, noms)


NB_PAQUETS = 64  # carrières découpées en 64 fichiers : la fiche joueur n'en charge qu'un


def paquet(nom):
    return sum(map(ord, nom)) % NB_PAQUETS  # même calcul dans index.html (codePointAt)


def carrieres(m, saison_match, parts, debut_detail):
    """{joueur: [[saison, équipe, compétition, MJ, tit., buts, pen., PD, J, R, tirs, cadrés, fautes, subies, HJ, arrêts, encaissés]]}
    MJ/tit. = None sans composition ; PD = None avant les saisons détaillées ; stats = None quand ESPN ne les donne pas."""
    par_id, lignes = {x["id"]: x for x in m}, {}
    def ligne(nom, mt, cote):
        s = saison_match[mt["id"]]
        cle = (nom, s, mt["domicile"] if cote == "dom" else mt["exterieur"], mt["ligue"])
        return lignes.setdefault(cle, [s, cle[2], cle[3], None, None, 0, 0, None if s < debut_detail else 0, 0, 0] + [None] * 7)
    for mid, nom, _, cote, tit, _, _, *st in parts:
        if mid in par_id:
            l = ligne(nom, par_id[mid], cote)
            l[3], l[4] = (l[3] or 0) + 1, (l[4] or 0) + tit
            for i, v in enumerate(st, 10):
                if v is not None:
                    l[i] = (l[i] or 0) + v
    for x in m:
        for champ in ("buteurs", "passes", "cartons"):
            for e in x[champ]:
                if e["nom"].endswith(" (csc)"):
                    continue
                l = ligne(e["nom"].removesuffix(" (pen)"), x, e["cote"])
                if champ == "buteurs":
                    l[5] += 1
                    l[6] += e["nom"].endswith(" (pen)")
                elif champ == "passes":
                    l[7] = (l[7] or 0) + 1
                else:
                    l[9 if e.get("type") == "R" else 8] += 1
    out = {}
    for (nom, *_), l in lignes.items():
        out.setdefault(nom, []).append(l)
    return out


def ecrire_carrieres(m, saison_match, parts, debut_detail):
    dossier = DB.with_name("carrieres")
    dossier.mkdir(exist_ok=True)
    pq = [{} for _ in range(NB_PAQUETS)]
    for nom, ls in carrieres(m, saison_match, parts, int(debut_detail[:4])).items():
        for l in ls:
            while l[-1] is None:  # stats absentes en fin de ligne : fichiers bien plus légers
                l.pop()
        pq[paquet(nom)][nom] = sorted(ls, key=lambda l: (l[0], l[2]))
    for i, d in enumerate(pq):
        (dossier / f"{i}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {n: ls for d in pq for n, ls in d.items()}


def main():
    db = sqlite3.connect(DB)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS matchs (id TEXT PRIMARY KEY, ligue TEXT, date_utc TEXT, domicile TEXT,
        exterieur TEXT, buts_dom INTEGER, buts_ext INTEGER, statut TEXT, logo_dom TEXT, logo_ext TEXT,
        buteurs TEXT, maj TEXT);
    CREATE TABLE IF NOT EXISTS classement (ligue TEXT, groupe TEXT, rang INTEGER, equipe TEXT, logo TEXT,
        joues INTEGER, g INTEGER, n INTEGER, p INTEGER, bp INTEGER, bc INTEGER, pts INTEGER, maj TEXT,
        pts_officiel INTEGER);
    CREATE TABLE IF NOT EXISTS scores_sources (match_id TEXT, source TEXT, buts_dom INTEGER, buts_ext INTEGER,
        maj TEXT, PRIMARY KEY (match_id, source));
    CREATE TABLE IF NOT EXISTS jours_lus (code TEXT, jour TEXT, PRIMARY KEY (code, jour));
    CREATE TABLE IF NOT EXISTS participations (match_id TEXT, joueur TEXT, id_espn TEXT, cote TEXT,
        titulaire INTEGER, entre INTEGER, sorti INTEGER, PRIMARY KEY (match_id, joueur));
    CREATE TABLE IF NOT EXISTS identites (id_espn TEXT PRIMARY KEY, joueur TEXT, lu TEXT, naissance TEXT, nationalite TEXT,
        drapeau TEXT, taille INTEGER, poids INTEGER, poste TEXT);
    CREATE TABLE IF NOT EXISTS wikidata (qid TEXT PRIMARY KEY, noms TEXT);""")
    for table, col in [("matchs", "cartons TEXT"), ("matchs", "passes TEXT"), ("matchs", "fiche_lue INTEGER")] + \
            [("participations", f"{c} {'TEXT' if c == 'poste' else 'INTEGER'}") for c in PART_COLS[7:]] + \
            [("identites", "espn_photo INTEGER"), ("identites", "photo_lu TEXT"), ("identites", "commons TEXT")]:  # colonnes ajoutées après coup
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # déjà là
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = date.today()
    courante = saison_de(today.isoformat())
    SAISONS = list(range(courante, S.FD_DEBUT - 1, -1))  # avant 2001 : football-data.co.uk seulement
    RECENTES = SAISONS[:NB_DETAILLEES]
    debut_recent = f"{RECENTES[-1]}-07-01"
    try:
        db.execute("ALTER TABLE classement ADD COLUMN saison INTEGER")
        db.execute("UPDATE classement SET saison=?", (courante,))  # anciennes lignes = saison en cours
    except sqlite3.OperationalError:
        pass
    stable = (today - timedelta(days=7)).strftime("%Y%m%d")  # avant : les scores ne bougent plus
    taches = []
    for code, ligue in LIGUES.items():
        try:
            debut = date.fromisoformat(get(f"{API}/site/v2/sports/soccer/{code}/scoreboard")["leagues"][0]["season"]["startDate"][:10])
        except Exception as e:
            print(f"[erreur] début de saison {ligue}: {e}", file=sys.stderr)
            debut = today - timedelta(days=7)
        debut = min(debut, date(PREMIERE_SAISON, 7, 1))  # + les saisons précédentes (juillet à juin)
        deja = {j for (j,) in db.execute("SELECT jour FROM jours_lus WHERE code=?", (code,))}
        # jours récents + toute journée ancienne jamais lue correctement (rattrape les trous)
        taches += [(code, ligue, j) for i in range((today + timedelta(days=14) - debut).days + 1)
                   if (j := (debut + timedelta(days=i)).strftime("%Y%m%d")) not in deja]
    # pays absents d'ESPN : LiveScore, qui ne garde qu'environ 1 an de matchs
    # le code change avec le nombre de ligues : en ajouter fait relire toutes les journées LiveScore une fois
    ls_code = f"livescore{len(S.LS_LIGUES)}"
    db.execute("DELETE FROM jours_lus WHERE code LIKE 'livescore%' AND code != ?", (ls_code,))
    # un match resté « en cours » depuis la veille (statut inconnu, passage raté) : on relit sa journée
    db.execute("DELETE FROM jours_lus WHERE code=? AND jour IN (SELECT replace(substr(date_utc, 1, 10), '-', '') FROM matchs"
               " WHERE id LIKE 'ls%' AND statut='STATUS_IN_PROGRESS' AND date_utc < ?)",
               (ls_code, (today - timedelta(days=1)).isoformat()))
    deja = {j for (j,) in db.execute("SELECT jour FROM jours_lus WHERE code=?", (ls_code,))}
    debut = date.fromisoformat(debut_recent)
    taches += [(ls_code, None, j) for i in range((today + timedelta(days=14) - debut).days + 1)
               if (j := (debut + timedelta(days=i)).strftime("%Y%m%d")) not in deja]
    taches.sort(key=lambda t: t[2], reverse=True)  # le plus récent d'abord : les jours récents passent à chaque fois
    print(f"[historique] {len(taches)} journées à lire, {min(len(taches), MAX_JOURS)} ce passage")
    taches = taches[:MAX_JOURS]
    t0 = time.time()
    with ThreadPoolExecutor(4) as pool:
        res = list(pool.map(lambda t: jour(*t), taches))
    print(f"[temps] ESPN: {time.time() - t0:.0f} s")
    erreurs = sum(not ok for _, ok in res)
    matchs = [m for r, _ in res for m in r]
    db.executemany("INSERT OR IGNORE INTO jours_lus VALUES (?,?)",
                   [(t[0], t[2]) for t, (_, ok) in zip(taches, res) if ok and t[2] < stable])
    # mise à jour sans effacer les passeurs déjà lus
    upsert = (f"INSERT INTO matchs ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))}) "
              f"ON CONFLICT(id) DO UPDATE SET {','.join(f'{c}=coalesce(excluded.{c}, {c})' if c in ('buteurs', 'cartons') else f'{c}=excluded.{c}' for c in COLS[1:])}")
    db.executemany(upsert, [m + (maintenant,) for m in matchs])

    # football-data.co.uk comme source principale là où personne d'autre n'a les matchs : avant 2001 (ESPN n'a rien)
    # et, pour les ligues LiveScore, avant sa fenêtre d'un an. Chaque fichier n'est lu qu'une fois (saisons finies).
    noms_ls = set(S.LS_LIGUES.values())
    fd_lus = {c for (c,) in db.execute("SELECT code FROM jours_lus WHERE jour='fd'")}
    lots = [(f"fd:{d}:{a}", lambda d=d, a=a: S.fd_saison(d, a)) for d in S.FD_DIV for a in range(S.FD_DEBUT, PREMIERE_SAISON)]
    lots += [(f"fd:{c}", lambda c=c: [r for r in S.fd_pays(c) if r[1] < debut_recent])
             for c, nom in S.FD_PAYS.items() if nom in noms_ls]
    lots = [l for l in lots if l[0] not in fd_lus]
    def lire_lot(lot):
        try:
            return lot[0], lot[1]()
        except Exception as e:
            print(f"[erreur] football-data {lot[0]}: {e}", file=sys.stderr)
            return lot[0], None  # nouvel essai au prochain passage
    with ThreadPoolExecutor(4) as pool:
        for cle, lignes in pool.map(lire_lot, lots):
            if lignes is None:
                continue
            # shortcut: le fichier n'a pas toujours l'heure ; midi UTC garde la bonne date partout
            db.executemany(upsert, [(S.fd_id(r), r[0], f"{r[1]}T12:00Z", r[2], r[3], r[4], r[5], "STATUS_FULL_TIME",
                                     None, None, "[]", "[]", maintenant) for r in lignes])
            db.execute("INSERT OR IGNORE INTO jours_lus VALUES (?, 'fd')", (cle,))
    if lots:
        print(f"[football-data] {len(lots)} fichiers d'historique lus")

    # fiche détaillée de chaque match terminé (passeurs + qui a joué), 1500 max par passage (la suite au prochain)
    code_de = {v: k for k, v in LIGUES.items()}
    # football-data n'a pas de fiche ; LiveScore n'a rien de nouveau depuis la version 2 (pas de stats joueurs)
    a_faire = (f"(fiche_lue IS NULL OR fiche_lue < (CASE WHEN id LIKE 'ls%' THEN 2 ELSE {FICHE_VERSION} END))"
               f" AND (statut LIKE '%FULL_TIME%' OR statut LIKE '%FINAL%') AND date_utc >= '{debut_recent}' AND id NOT LIKE 'fd%'")
    # compositions des saisons sorties de la fenêtre : effacées, sinon la base grossit d'une saison chaque année
    db.execute("DELETE FROM participations WHERE match_id IN (SELECT id FROM matchs WHERE date_utc < ?)", (debut_recent,))
    a_lire = db.execute(f"SELECT id, ligue FROM matchs WHERE {a_faire} ORDER BY date_utc DESC LIMIT 1500").fetchall()
    def fiche(m):
        try:
            if m[0].startswith("ls"):  # LiveScore : buteurs, cartons et passeurs viennent de la fiche ; pas de compositions
                b, c, p = S.ls_fiche(m[0][2:])
                return m[0], p, [], json.dumps(b, ensure_ascii=False), json.dumps(c, ensure_ascii=False)
            s = get(f"{API}/site/v2/sports/soccer/{code_de[m[1]]}/summary?event={m[0]}")
            return m[0], passes(s), participations(s), None, None
        except Exception as e:
            print(f"[erreur] fiche {m}: {e}", file=sys.stderr)
            return m[0], None, None, None, None
    t0 = time.time()
    with ThreadPoolExecutor(4) as pool:
        lues = [r for r in pool.map(fiche, a_lire) if r[1] is not None]
    for mid, p, joueurs, but, cart in lues:
        db.execute("UPDATE matchs SET passes=?, fiche_lue=?, buteurs=coalesce(?, buteurs), cartons=coalesce(?, cartons) WHERE id=?",
                   (json.dumps(p, ensure_ascii=False), FICHE_VERSION, but, cart, mid))
        db.execute("DELETE FROM participations WHERE match_id=?", (mid,))
        db.executemany(f"INSERT OR IGNORE INTO participations ({','.join(PART_COLS)}) VALUES ({','.join('?' * len(PART_COLS))})",
                       [(mid,) + j for j in joueurs])
    reste = db.execute(f"SELECT count(*) FROM matchs WHERE {a_faire}").fetchone()[0]
    print(f"[temps] fiches: {time.time() - t0:.0f} s ({len(lues)} lues, {reste} restantes)")

    # identité des joueurs ESPN (naissance, nationalité, taille...), lue une seule fois par joueur, MAX_IDENTITES par passage
    ids = db.execute("SELECT id_espn, max(joueur) FROM participations WHERE id_espn IS NOT NULL AND id_espn NOT IN "
                     f"(SELECT id_espn FROM identites) GROUP BY id_espn LIMIT {MAX_IDENTITES}").fetchall()
    def lire_identite(x):
        try:
            return (x[0], x[1], maintenant) + identite(get(f"https://sports.core.api.espn.com/v2/sports/soccer/athletes/{x[0]}"))
        except Exception as e:
            print(f"[erreur] identité {x}: {e}", file=sys.stderr)
            return (x[0], x[1], maintenant) + (None,) * 6  # pas relu à chaque passage
    t0 = time.time()
    with ThreadPoolExecutor(4) as pool:
        db.executemany("INSERT OR REPLACE INTO identites (id_espn, joueur, lu, naissance, nationalite, drapeau, taille, poids, poste) "
                       "VALUES (?,?,?,?,?,?,?,?,?)", pool.map(lire_identite, ids))
    print(f"[temps] identités: {time.time() - t0:.0f} s ({len(ids)} lues)")
    # photos ESPN : jamais vérifiée, ou absente depuis plus de 60 jours (ESPN en ajoute pour les joueurs en activité)
    ids = [i for (i,) in db.execute("SELECT id_espn FROM identites WHERE photo_lu IS NULL OR (espn_photo = 0 AND photo_lu < ?) "
                                    f"ORDER BY photo_lu IS NOT NULL, lu DESC LIMIT {MAX_PHOTOS_ESPN}", ((today - timedelta(days=60)).isoformat(),))]
    t0 = time.time()
    with ThreadPoolExecutor(8) as pool:
        vus = [(v, maintenant, i) for i, v in zip(ids, pool.map(photo_espn, ids)) if v is not None]
    db.executemany("UPDATE identites SET espn_photo=?, photo_lu=? WHERE id_espn=?", vus)
    print(f"[temps] photos ESPN: {time.time() - t0:.0f} s ({len(vus)} vérifiées, {sum(v for v, _, _ in vus)} trouvées)")
    # photos Wikimedia Commons via Wikidata (toutes recalculées : Wikidata s'enrichit chaque jour)
    t0 = time.time()
    try:
        trouvees = photos_wikidata(db, {i: (n, d) for i, n, d in db.execute("SELECT id_espn, joueur, naissance FROM identites")})
        db.execute("UPDATE identites SET commons=NULL")
        db.executemany("UPDATE identites SET commons=? WHERE id_espn=?", [(f, i) for i, f in trouvees.items()])
        print(f"[temps] photos Wikidata: {time.time() - t0:.0f} s ({len(trouvees)} joueurs)")
    except Exception as e:
        erreurs += 1
        print(f"[erreur] photos Wikidata (on garde les anciennes) : {e}", file=sys.stderr)
    n_photos = db.execute("SELECT count(*), sum(espn_photo = 1), sum(espn_photo = 1 OR commons IS NOT NULL) FROM identites").fetchone()
    cl_lus = set(db.execute("SELECT code, jour FROM jours_lus WHERE code LIKE 'cl:%'").fetchall())
    # saison ancienne déjà lue : son classement ne bouge plus ; lus à 4 en parallèle (~2 400 la 1re fois après un ajout de ligues)
    a_lire = [(code, ligue, saison) for saison in SAISONS if saison >= PREMIERE_SAISON for code, ligue in LIGUES.items()
              if (f"cl:{code}", str(saison)) not in cl_lus]
    def lire_classement(t):
        try:
            return t, classement(*t)
        except Exception as e:
            print(f"[erreur] classement {t[1]} {t[2]}: {e}", file=sys.stderr)
            return t, None  # on garde l'ancien classement plutôt que de l'effacer
    t0 = time.time()
    with ThreadPoolExecutor(4) as pool:
        cl_res = list(pool.map(lire_classement, a_lire))
    print(f"[temps] classements: {time.time() - t0:.0f} s ({len(a_lire)} lus)")
    for (code, ligue, saison), lignes in cl_res:
        if lignes is None:
            erreurs += 1
            continue
        if saison < courante - 1:
            db.execute("INSERT OR IGNORE INTO jours_lus VALUES (?,?)", (f"cl:{code}", str(saison)))
        db.execute("DELETE FROM classement WHERE ligue=? AND saison=?", (ligue, saison))
        db.executemany("INSERT INTO classement (ligue, groupe, rang, equipe, logo, joues, g, n, p, bp, bc, pts, saison, maj) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [l + (maintenant,) for l in lignes])
    try:
        lignes = S.ls_classements(courante)
        for ligue, saison in {(l[0], l[12]) for l in lignes}:
            db.execute("DELETE FROM classement WHERE ligue=? AND saison=?", (ligue, saison))
        db.executemany("INSERT INTO classement (ligue, groupe, rang, equipe, logo, joues, g, n, p, bp, bc, pts, saison, maj) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [l + (maintenant,) for l in lignes])
    except Exception as e:
        erreurs += 1
        print(f"[erreur] classements LiveScore: {e}", file=sys.stderr)

    # recoupement : chaque source secondaire confirme (ou contredit) les scores
    # (saisons récentes seulement : les autres sources n'ont pas tout l'historique, et ce serait trop long)
    jours_lus = sorted({d for t in taches if (d := datetime.strptime(t[2], "%Y%m%d").date()).isoformat() >= debut_recent})
    recents = [(today - timedelta(days=d)).isoformat() for d in range(2)]  # TheSportsDB gratuit est lent : 2 jours
    a_verifier = db.execute("SELECT id, ligue, substr(date_utc,1,10), domicile, exterieur FROM matchs").fetchall()
    n_ls, n_tot = db.execute("SELECT sum(id LIKE 'ls%'), count(*) FROM matchs").fetchone()
    n_fd = db.execute("SELECT count(*) FROM matchs WHERE id LIKE 'fd%'").fetchone()[0]
    etat = {"ESPN": f"{n_tot - (n_ls or 0) - n_fd} matchs (source principale)", "LiveScore (pays absents d'ESPN)": f"{n_ls or 0} matchs",
            "football-data.co.uk (historique)": f"{n_fd} matchs"}
    for nom, lire in [("LiveScore", lambda: S.livescore(jours_lus)),
                      ("TheSportsDB", lambda: S.thesportsdb(recents)),
                      ("openfootball", lambda: [r for a in RECENTES[:2] for r in S.openfootball(a)]),
                      ("OpenLigaDB", lambda: [r for a in RECENTES[:2] for r in S.openligadb(a)]),
                      ("football-data.co.uk", lambda: [r for a in RECENTES[:2] for d in S.FD_DIV for r in S.fd_saison(d, a)])]:
        t0 = time.time()
        try:
            trouves = S.apparier(a_verifier, lire())
            print(f"[temps] {nom}: {time.time() - t0:.0f} s")
        except Exception as e:
            erreurs += 1
            etat[nom] = "indisponible"
            print(f"[erreur] source {nom}: {e}", file=sys.stderr)
            continue
        db.executemany("INSERT OR REPLACE INTO scores_sources VALUES (?,?,?,?,?)",
                       [(k, nom, v[0], v[1], maintenant) for k, v in trouves.items()])
        total = db.execute("SELECT count(*) FROM scores_sources WHERE source=?", (nom,)).fetchone()[0]
        etat[nom] = f"{total} scores confirmés au total"
    try:
        officiel = S.ligue1_officiel()
        for (eq,) in db.execute("SELECT equipe FROM classement WHERE ligue='Ligue 1' AND saison=?", (courante,)).fetchall():
            nom = max(officiel, key=lambda n: S.sim(eq, n))
            if S.sim(eq, nom) >= 0.6:
                db.execute("UPDATE classement SET pts_officiel=? WHERE ligue='Ligue 1' AND equipe=? AND saison=?", (officiel[nom], eq, courante))
        etat["Ligue1.fr (officiel)"] = f"classement de {len(officiel)} clubs"
    except Exception as e:
        erreurs += 1
        etat["Ligue1.fr (officiel)"] = "indisponible"
        print(f"[erreur] source Ligue1.fr: {e}", file=sys.stderr)
    db.commit()

    # export lu par la page web (index.html)
    def table(sql):
        cur = db.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur]
    m = table(f"SELECT {','.join(COLS)}, passes FROM matchs ORDER BY date_utc")
    src = {}
    for mid, nom, bd, be in db.execute("SELECT match_id, source, buts_dom, buts_ext FROM scores_sources"):
        src.setdefault(mid, {})[nom] = [bd, be]
    for x in m:
        for k in ("buteurs", "cartons", "passes"):
            x[k] = json.loads(x[k] or "[]")
        fini = "FULL_TIME" in x["statut"] or "FINAL" in x["statut"]  # FINAL_PEN = tirs au but, FINAL_AET = prolongation
        espn = [x["buts_dom"], x["buts_ext"]] if fini else None
        score, x["ecart"] = S.consensus(espn, src.get(x["id"], {}))
        principale = {"ls": "LiveScore", "fd": "football-data.co.uk"}.get(x["id"][:2], "ESPN")
        x["sources"] = ({principale: espn} if espn else {}) | src.get(x["id"], {})
        if not espn and score:  # ESPN n'a pas le score : on prend celui confirmé par 2 autres sources
            x["buts_dom"], x["buts_ext"], x["statut"], x["secours"] = score[0], score[1], "STATUS_FULL_TIME", True
    # un fichier par saison (matchs-2025.json...) ; matchs.json = saison en cours
    clas = table("SELECT * FROM classement ORDER BY ligue, groupe, rang")
    saison_match = {x["id"]: saison_de(x["date_utc"]) for x in m}
    jou = {s: {} for s in SAISONS}
    # qui a joué quoi, chargé seulement par la fiche joueur :
    # {joueur: {"id": id_espn, "p": poste, "m": [[match, cote, "T"|"E", sorti, *stats (si ESPN les donne)]]}}
    parts = db.execute("SELECT p.match_id, joueur, id_espn, cote, titulaire, sorti, poste, tirs, cadres, fautes, subies, "
                       "hors_jeu, arrets, encaisses FROM participations p JOIN matchs m ON m.id = p.match_id ORDER BY m.date_utc").fetchall()
    for mid, nom, ide, cote, tit, sor, poste, *st in parts:
        if saison_match.get(mid) in jou:
            j = jou[saison_match[mid]].setdefault(nom, {"id": ide, "m": []})
            j["m"].append([mid, cote, "T" if tit else "E", sor] + (st if any(v is not None for v in st) else []))
            if poste:
                j["p"] = poste
    car = ecrire_carrieres(m, saison_match, parts, debut_recent)
    # identités par nom (homonymes : le dernier lu l'emporte), même découpage que les carrières
    pays = pays_fr()
    # [naissance, nationalité, drapeau, taille, poids, poste, adresse de la photo, fichier Commons (pour le crédit)]
    iden = {}
    for nom, *v, ide, ep, cm in db.execute("SELECT joueur, naissance, nationalite, drapeau, taille, poids, poste, id_espn, espn_photo, commons "
                                           "FROM identites WHERE coalesce(naissance, nationalite, poste) IS NOT NULL OR espn_photo = 1 "
                                           "OR commons IS NOT NULL ORDER BY lu"):
        iden[nom] = [v[0], pays.get(v[1], v[1])] + v[2:] + photo(ide, ep, cm)
    (dossier := DB.with_name("identites")).mkdir(exist_ok=True)
    pq = [{} for _ in range(NB_PAQUETS)]
    for nom, v in iden.items():
        pq[paquet(nom)][nom] = v
    for i, d in enumerate(pq):
        (dossier / f"{i}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for s in SAISONS:
        donnees = json.dumps({"maj": maintenant, "saison": s, "saisons": SAISONS, "courante": courante,
                              "ligues": LIGUES | {f"ls:{c}/{s}": nom for (c, s), nom in S.LS_LIGUES.items()},
                              "feminin": sorted({LIGUES[c] for c in FEMININ} | S.LS_FEMININ),
                              "sources": etat, "matchs": [x for x in m if saison_match[x["id"]] == s],
                              "classement": [c for c in clas if c["saison"] == s]}, ensure_ascii=False, separators=(",", ":"))  # sans espaces : -9 %
        joueurs = json.dumps(jou[s], ensure_ascii=False, separators=(",", ":"))
        for suffixe in [f"-{s}"] + ([""] if s == courante else []):
            DB.with_name(f"matchs{suffixe}.json").write_text(donnees, encoding="utf-8")
            DB.with_name(f"joueurs{suffixe}.json").write_text(joueurs, encoding="utf-8")
    P.ecrire(DB.parent, m, car, clas, courante, maintenant, iden)
    print(f"[photos] {n_photos[2] or 0} joueurs avec photo sur {n_photos[0]} (ESPN : {n_photos[1] or 0}, les autres : Wikimedia Commons)")
    print(f"{len(taches)} jours lus, {len(matchs)} matchs mis à jour, {erreurs} erreurs -> {DB}")


if __name__ == "__main__":
    # auto-test du parseur
    fake = {"id": "1", "date": "2026-01-01T20:00Z", "status": {"type": {"name": "STATUS_SCHEDULED"}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "team": {"id": "10", "displayName": "A"}, "score": "0"},
                {"homeAway": "away", "team": {"id": "20", "displayName": "B"}, "score": "0"}]}]}
    assert parse(fake, "L")[5:7] == (None, None)
    fake["status"]["type"]["name"] = "STATUS_FULL_TIME"
    fake["competitions"][0]["competitors"][0]["score"] = "1"
    fake["competitions"][0]["details"] = [{"scoringPlay": True, "ownGoal": True, "team": {"id": "10"},
        "clock": {"displayValue": "9'"}, "athletesInvolved": [{"displayName": "X"}]}]
    p = parse(fake, "L")
    assert p[5:7] == (1, 0) and json.loads(p[10]) == [{"cote": "dom", "min": "9'", "nom": "X (csc)"}]
    fake["competitions"][0]["details"] = [{"redCard": True, "team": {"id": "20"}, "clock": {"displayValue": "50'"},
                                           "athletesInvolved": [{"displayName": "Y"}]}]
    assert json.loads(parse(fake, "L")[11]) == [{"cote": "ext", "min": "50'", "nom": "Y", "type": "R"}]
    resume = {"header": {"competitions": [{"competitors": [{"homeAway": "home", "team": {"id": "10"}}]}]},
              "keyEvents": [{"type": {"text": "Goal"}, "scoringPlay": True, "team": {"id": "10"}, "clock": {"displayValue": "5'"},
                             "participants": [{"athlete": {"displayName": "X"}}, {"athlete": {"displayName": "Z"}}]},
                            {"type": {"text": "Penalty - Scored"}, "scoringPlay": True, "team": {"id": "20"},
                             "participants": [{"athlete": {"displayName": "P"}}, {"athlete": {"displayName": "Q"}}]}]}
    assert passes(resume) == [{"cote": "dom", "min": "5'", "nom": "Z"}]
    resume["rosters"] = [{"team": {"id": "20"}, "roster": [
        {"starter": True, "subbedOut": True, "athlete": {"displayName": "A", "id": "1"}, "position": {"abbreviation": "G"},
         "stats": [{"name": "saves", "value": 3.0}, {"name": "totalShots", "value": 0.0}]},
        {"starter": False, "subbedIn": True, "athlete": {"displayName": "B", "id": "2"}, "position": {"abbreviation": "SUB"}},
        {"starter": False, "athlete": {"displayName": "Banc", "id": "3"}}]}]
    assert parse(fake, "L", True)[3:5] == ("A (F)", "B (F)")
    assert "fifa.world" not in FEMININ and FEMININ <= set(LIGUES)
    assert saison_de("2026-08-21T18:45Z") == 2026 and saison_de("2026-05-10T18:00Z") == 2025
    pa = participations(resume)
    assert pa == [("A", "1", "ext", 1, 0, 1, "G", 0, None, None, None, None, 3, None),
                  ("B", "2", "ext", 0, 1, 0, None) + (None,) * 7]
    # carrière : 2 matchs de A (1 composition, 1 but sur penalty), un csc ignoré, saison ancienne sans PD
    mt = [{"id": "1", "date_utc": "2025-09-01", "domicile": "D", "exterieur": "E", "ligue": "L",
           "buteurs": [{"cote": "ext", "nom": "A (pen)"}, {"cote": "dom", "nom": "A (csc)"}], "passes": [], "cartons": []},
          {"id": "2", "date_utc": "2010-09-01", "domicile": "E", "exterieur": "F", "ligue": "L",
           "buteurs": [], "passes": [], "cartons": [{"cote": "dom", "nom": "A", "type": "J"}]}]
    c = carrieres(mt, {"1": 2025, "2": 2010}, [("1",) + pa[0][:5] + pa[0][6:]], 2025)["A"]  # forme de l'export : sans « entre »
    assert c == [[2025, "E", "L", 1, 1, 1, 1, 0, 0, 0, 0, None, None, None, None, 3, None],
                 [2010, "E", "L", None, None, 0, 0, None, 1, 0] + [None] * 7], c
    assert paquet("Kylian Mbappé") == sum(map(ord, "Kylian Mbappé")) % 64
    assert identite({"dateOfBirth": "1998-12-20T08:00Z", "citizenship": "France", "height": 70.0, "weight": 163.0,
                     "position": {"name": "Forward"}, "flag": {"href": "https://a.espncdn.com/i/teamlogos/countries/500/fra.png"}}) \
        == ("1998-12-20", "France", "fra", 178, 74, "Attaquant")
    assert identite({}) == (None,) * 6
    assert meme_nom("Jesé", "Jesé Rodríguez") and meme_nom("Hannes Van Der Bruggen", "Hannes van der Bruggen")
    assert meme_nom("Viktor Tsygankov", "Viktor Tsyhankov") and not meme_nom("Christian Alemán", "Brayan Palmezano")
    wd = {"Q1": ("1990-01-01", "A.jpg", {"10"}), "Q2": ("1995-05-05", "B.jpg", set()), "Q3": ("1995-05-05", "C.jpg", set()),
          "Q4": ("2000-02-02", "D.jpg", {"40"}), "Q5": ("1999-09-09", "E.jpg", set())}
    noms = {"Q1": ["Jean Dupont"], "Q2": ["Paul Martin"], "Q3": ["Paul Martin"], "Q4": ["Autre Joueur"], "Q5": ["Luis Pérez"]}
    # 10 : lien ESPN + nom ; 20 : deux homonymes même jour -> rien ; 40 : lien ESPN mais nom différent -> rien ; 50 : date + nom
    assert apparier_photos({"10": ("Jean Dupont", "1991-01-01"), "20": ("Paul Martin", "1995-05-05"), "40": ("Marc Leroy", "2000-02-02"),
                            "50": ("Luis Perez", "1999-09-09"), "60": ("Sans Date", None)}, wd, noms) == {"10": "A.jpg", "50": "E.jpg"}
    assert photo("7", 1, "X.jpg") == [ESPN_PHOTO.format("7")] and photo("7", 0, None) == []
    assert photo("7", 0, "Joe Bloggs é.jpg") == [COMMONS + "Joe%20Bloggs%20%C3%A9.jpg?width=250", "Joe Bloggs é.jpg"]
    main()
