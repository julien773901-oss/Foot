"""Sources secondaires pour recouper les scores ESPN.
Chaque source renvoie des matchs TERMINÉS : (ligue, 'AAAA-MM-JJ', domicile, exterieur, buts_dom, buts_ext).
shortcut: ce sont des API gratuites non officielles ; une source qui tombe est juste ignorée (le reste continue)."""
import csv, io, json, re, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

UA = {"User-Agent": "Mozilla/5.0 (base-foot)"}


def get(url, essais=3):
    for i in range(essais):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except Exception as e:
            if i == essais - 1 or getattr(e, "code", None) == 404:
                raise
            time.sleep(20 if getattr(e, "code", None) in (403, 429) else 3 * (i + 1))  # 403/429 = bloqué / trop de requêtes


def tolerant(f):
    """Une page qui échoue renvoie [] au lieu de faire tomber toute la source."""
    def g(*a):
        try:
            return f(*a)
        except Exception as e:
            print(f"[source] {f.__name__} {a}: {e}", file=sys.stderr)
            return []
    return g


# ---------- correspondance des noms d'équipes entre sources ----------
MOTS_VIDES = {"fc", "cf", "ac", "as", "ss", "sc", "sv", "vfb", "vfl", "tsg", "rc", "ogc", "afc", "ud", "cd", "rcd",
              "ssc", "bc", "club", "de", "del", "la", "le", "calcio", "olympique", "stade", "1", "04", "05", "29",
              "1899", "1846", "1907", "1909", "1910", "aj", "fk", "sk", "cp", "sl", "and", "hotspur", "w"}


def norm(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    s = s.replace("munchen", "munich").replace("saint", "st").replace("-", " ")
    return [t for t in re.findall(r"[a-z0-9]+", s) if t not in MOTS_VIDES] or [s]


def sim(a, b):
    ta, tb = norm(a), norm(b)
    tok = max(1.0 if x == y or (min(len(x), len(y)) >= 4 and (x.startswith(y) or y.startswith(x)))
              else SequenceMatcher(None, x, y).ratio() for x in ta for y in tb)
    return 0.5 * tok + 0.5 * SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()


def apparier(matchs, resultats):
    """matchs: [(id, ligue, 'AAAA-MM-JJ', dom, ext)] ESPN ; resultats: sortie d'une source.
    Renvoie {id: (buts_dom, buts_ext)} pour les correspondances sûres."""
    par_cle = {}
    for r in resultats:
        par_cle.setdefault((r[0], r[1]), []).append(r)
    out = {}
    for mid, ligue, jour, dom, ext in matchs:
        j = date.fromisoformat(jour)
        cands = [r for d in (-1, 0, 1) for r in par_cle.get((ligue, (j + timedelta(days=d)).isoformat()), [])]
        best, score = None, 0
        for r in cands:
            sd, se = sim(dom, r[2]), sim(ext, r[3])
            if sd >= 0.45 and se >= 0.45 and sd + se > score:
                best, score = r, sd + se
        if best and score >= 1.3:
            out[mid] = (best[4], best[5])
    return out


def feminin(nom):
    """Équipe féminine : « Bayern Munich W », « Arsenal Women » ou « Arsenal » (ESPN) -> « Bayern Munich (F) »."""
    nom = re.sub(r"\s+(W|Women|Ladies|Femenil|Femenino|Feminino|Femminile|Féminine|Frauen)$", "", nom.strip())
    return nom if nom.endswith(" (F)") else nom + " (F)"


# ---------- les sources ----------
LS_COMP = {"68": "Ligue 1", "65": "Premier League", "75": "La Liga", "77": "Serie A", "67": "Bundesliga",
           "60": "Ligue des champions", "100": "Ligue 2", "36": "Ligue Europa", "62": "Ligue Conférence",
           "426": "Coupe de France", "79": "Liga Portugal", "64": "Eredivisie"}


# Pour les saisons passées, LiveScore change d'identifiants : on reconnaît alors la compétition par (pays, nom sans "25/26")
LS_NOM = {("France", "Ligue 1"): "Ligue 1", ("England", "Premier League"): "Premier League", ("Spain", "LaLiga"): "La Liga",
          ("Italy", "Serie A"): "Serie A", ("Germany", "Bundesliga"): "Bundesliga", ("France", "Ligue 2"): "Ligue 2",
          ("Portugal", "Primeira Liga"): "Liga Portugal", ("Netherlands", "Eredivisie"): "Eredivisie",
          ("France", "Coupe de France"): "Coupe de France", ("Champions League", "Champions League"): "Ligue des champions",
          ("Europa League", "Europa League"): "Ligue Europa", ("Conference League", "Conference League"): "Ligue Conférence"}


def ls_ligue(s):
    if str(s.get("CompId")) in LS_COMP:
        return LS_COMP[str(s.get("CompId"))]
    for nom in (s.get("CompN"), s.get("Snm")):
        base = re.sub(r"\s+(\d{2}/\d{2}|\d{4}/\d{4})$", "", nom or "")
        if (s.get("Cnm"), base) in LS_NOM:
            return LS_NOM[(s.get("Cnm"), base)]
    return None


def livescore(jours):
    @tolerant
    def un_jour(j):
        d = get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{j.strftime('%Y%m%d')}/0?locale=en&MD=1")
        out = []
        for s in d.get("Stages", []):
            ligue = ls_ligue(s)
            for e in s.get("Events", []) if ligue else []:
                if e.get("Eps") in ("FT", "AET", "AP") and e.get("Tr1") is not None:
                    esd = str(e["Esd"])  # parfois un nombre, parfois du texte
                    jour = f"{esd[:4]}-{esd[4:6]}-{esd[6:8]}"
                    out.append((ligue, jour, e["T1"][0]["Nm"], e["T2"][0]["Nm"], int(e["Tr1"]), int(e["Tr2"])))
        return out
    with ThreadPoolExecutor(3) as pool:
        return [m for r in pool.map(un_jour, jours) for m in r]


# ---------- LiveScore comme source PRINCIPALE pour les pays absents d'ESPN ----------
# shortcut: l'API ne garde qu'environ 1 an de matchs et la saison en cours pour les classements : pas d'historique ancien.
LS_API = "https://prod-public-api.livescore.com/v1/api/app"
LS_LOGO = "https://lsm-static-prod.livescore.com/medium/"
# (Ccd, Scd) -> nom ; les phases (« super-league-championship-group »…) sont rattachées à leur ligue par le début du code
LS_LIGUES = {("switzerland", "super-league"): "Super League (Suisse)", ("switzerland", "challenge-league"): "Challenge League (Suisse)",
             ("switzerland", "cup"): "Coupe de Suisse",
             ("poland", "ekstraklasa"): "Ekstraklasa (Pologne)", ("poland", "i-liga"): "I Liga (Pologne)",
             ("poland", "ii-liga"): "II Liga (Pologne)", ("poland", "cup"): "Coupe de Pologne",
             ("croatia", "1st-league"): "HNL (Croatie)", ("croatia", "2nd-league"): "Prva NL (Croatie)", ("croatia", "cup"): "Coupe de Croatie",
             ("ukraine", "premier-league"): "Premier League (Ukraine)", ("ukraine", "persha-liga"): "Persha Liga (Ukraine)",
             ("ukraine", "cup"): "Coupe d'Ukraine",
             ("korea-republic", "k-league-1"): "K League 1 (Corée du Sud)", ("korea-republic", "k-league-2"): "K League 2 (Corée du Sud)",
             ("korea-republic", "cup"): "Coupe de Corée du Sud",
             ("morocco", "botola-pro"): "Botola Pro (Maroc)", ("morocco", "cup"): "Coupe du Trône (Maroc)",
             ("egypt", "premier-league"): "Premier League (Égypte)", ("egypt", "2-division-a"): "2e division (Égypte)",
             ("egypt", "cup"): "Coupe d'Égypte", ("egypt", "league-cup"): "Coupe de la Ligue (Égypte)",
             # divisions inférieures des pays couverts par ESPN
             ("germany", "3-liga"): "3. Liga (Allemagne)", ("france", "ligue-3"): "National (France)",
             ("italy", "serie-c"): "Serie C (Italie)", ("spain", "primera-division-rfef"): "Primera Federación (Espagne)",
             ("portugal", "segunda-liga"): "Liga 2 (Portugal)", ("belgium", "challenger-pro-league"): "Challenger Pro League (Belgique)",
             ("turkey", "1st-lig"): "1. Lig (Turquie)", ("austria", "2-liga"): "2. Liga (Autriche)",
             ("greece", "super-league-2"): "Super League 2 (Grèce)", ("denmark", "1-division"): "1. Division (Danemark)",
             ("sweden", "superettan"): "Superettan (Suède)", ("norway", "1-division"): "1. Division (Norvège)",
             ("scotland", "league-1"): "League One (Écosse)", ("scotland", "league-2"): "League Two (Écosse)",
             ("japan", "j-league-2"): "J2 League (Japon)", ("japan", "j-league-3"): "J3 League (Japon)",
             ("china", "china-league-one"): "League One (Chine)",
             # Europe : premières divisions
             ("czech-republic", "1st-league"): "Chance Liga (Tchéquie)", ("serbia", "super-liga"): "SuperLiga (Serbie)",
             ("romania", "liga-1"): "Liga 1 (Roumanie)", ("hungary", "nb-i"): "NB I (Hongrie)",
             ("bulgaria", "parva-liga"): "Parva Liga (Bulgarie)", ("slovakia", "fortuna-liga"): "Niké Liga (Slovaquie)",
             ("slovenia", "prva-liga"): "Prva Liga (Slovénie)", ("israel", "premier-league"): "Ligat HaAl (Israël)",
             ("cyprus", "1-division"): "1re division (Chypre)", ("finland", "veikkausliiga"): "Veikkausliiga (Finlande)",
             ("ireland", "league-of-ireland-premier-division"): "Premier Division (Irlande)",
             ("northern-ireland", "premiership"): "Premiership (Irlande du Nord)", ("wales", "cymru-premier"): "Cymru Premier (Pays de Galles)",
             ("iceland", "urvalsdeild"): "Besta deild (Islande)", ("bosnia", "premier-league"): "Premijer Liga (Bosnie)",
             ("albania", "kategoria-superiore"): "Kategoria Superiore (Albanie)", ("macedonia", "1st-league"): "Prva Liga (Macédoine du Nord)",
             ("montenegro", "1-cfl"): "1. CFL (Monténégro)", ("kosovo", "superleague"): "Superliga (Kosovo)",
             ("georgia", "erovnuli-liga"): "Erovnuli Liga (Géorgie)", ("armenia", "premier-league"): "Premier League (Arménie)",
             ("azerbaijan", "premier-league"): "Premier League (Azerbaïdjan)", ("kazakhstan", "premier-league"): "Premier League (Kazakhstan)",
             ("belarus", "premier-league"): "Vysheyshaya Liga (Biélorussie)", ("moldova", "super-liga"): "Super Liga (Moldavie)",
             ("lithuania", "a-lyga"): "A Lyga (Lituanie)", ("latvia", "virsliga"): "Virslīga (Lettonie)",
             ("estonia", "meistriliiga"): "Meistriliiga (Estonie)", ("luxembourg", "national-division"): "Division nationale (Luxembourg)",
             ("malta", "premier-league"): "Premier League (Malte)", ("faroe-islands", "premier-league"): "Premier League (Îles Féroé)",
             ("andorra", "1st-division"): "Primera Divisió (Andorre)", ("san-marino", "campionato"): "Campionato (Saint-Marin)",
             ("gibraltar", "national-league"): "National League (Gibraltar)",
             # Afrique
             ("algeria", "ligue-1"): "Ligue 1 (Algérie)", ("tunisia", "ligue-i"): "Ligue 1 (Tunisie)", ("nigeria", "npfl"): "NPFL (Nigeria)",
             ("ghana", "premier-league"): "Premier League (Ghana)", ("cameroon", "elite-1"): "Elite One (Cameroun)",
             ("kenya", "premier-league"): "Premier League (Kenya)", ("tanzania", "premier-league"): "Premier League (Tanzanie)",
             ("zambia", "super-league"): "Super League (Zambie)", ("botswana", "premier-league"): "Premier League (Botswana)",
             ("benin", "ligue-1"): "Ligue 1 (Bénin)", ("burkina-faso", "ligue-1"): "Ligue 1 (Burkina Faso)",
             ("niger", "super-league"): "Super Ligue (Niger)", ("malawi", "super-league"): "Super League (Malawi)",
             # Asie
             ("iran", "persian-gulf-pro-league"): "Pro League (Iran)", ("iran", "pro-league"): "Pro League (Iran)",
             ("iraq", "iraq-stars-league"): "Stars League (Irak)", ("qatar", "qatar-stars-league"): "Stars League (Qatar)",
             ("united-arab-emirates", "uae-league"): "Pro League (Émirats arabes unis)", ("jordan", "pro-league"): "Pro League (Jordanie)",
             ("kuwait", "premier-league"): "Premier League (Koweït)", ("bahrain", "premier-league"): "Premier League (Bahreïn)",
             ("oman", "professional-league"): "Professional League (Oman)", ("lebanon", "premier-league"): "Premier League (Liban)",
             ("uzbekistan", "superliga"): "Super League (Ouzbékistan)", ("thailand", "thai-league"): "Thai League 1 (Thaïlande)",
             ("vietnam", "v-league"): "V.League 1 (Vietnam)", ("indonesia", "super-league"): "Super League (Indonésie)",
             ("malaysia", "super-league"): "Super League (Malaisie)", ("hong-kong", "premier-league"): "Premier League (Hong Kong)",
             ("singapore", "sg-premier-league"): "Premier League (Singapour)", ("bangladesh", "premier-league"): "Premier League (Bangladesh)",
             ("philippines", "pfl"): "PFL (Philippines)",
             # Amériques, Océanie
             ("canada", "premier-league"): "Premier League (Canada)", ("jamaica", "premier-league"): "Premier League (Jamaïque)",
             ("new-zealand", "national-league"): "National League (Nouvelle-Zélande)",
             # ajoutés le 26 novembre 2026 : divisions inférieures absentes d'ESPN
             ("england", "national-league-north"): "National League North (Angleterre)",
             ("england", "national-league-south"): "National League South (Angleterre)",
             ("romania", "liga-ii"): "Liga II (Roumanie)", ("hungary", "nb-ii"): "NB II (Hongrie)",
             ("sweden", "1st-division-north"): "Division 1 Nord (Suède)", ("sweden", "1st-division-south"): "Division 1 Sud (Suède)",
             ("argentina", "primera-c"): "Primera C (Argentine)", ("paraguay", "division-intermedia"): "División Intermedia (Paraguay)",
             ("usa", "mls-next-pro"): "MLS Next Pro (États-Unis)",
             # championnats féminins absents d'ESPN (Angleterre, Espagne, France, Pays-Bas, États-Unis, Mexique : chez ESPN)
             ("germany", "bundesliga-women"): "Frauen-Bundesliga (Allemagne)", ("italy", "serie-a-women"): "Serie A féminine (Italie)",
             ("sweden", "damallsvenskan-women"): "Damallsvenskan (Suède)", ("norway", "toppserien-women"): "Toppserien (Norvège)",
             ("denmark", "a-liga-women"): "A-Liga féminine (Danemark)", ("portugal", "womens-campeonato-nacional"): "Liga BPI (Portugal, féminin)",
             ("japan", "we-league"): "WE League (Japon)", ("finland", "kansallinen-liiga-women"): "Kansallinen Liiga (Finlande, féminin)",
             ("finland", "womens-kansallinen-liiga"): "Kansallinen Liiga (Finlande, féminin)",
             ("ireland", "womens-national-league"): "Premier Division féminine (Irlande)"}
LS_FEMININ = {nom for (c, sc), nom in LS_LIGUES.items() if "women" in sc or sc == "we-league"}
LS_VUS = set()  # (Ccd, Scd) réellement vus dans les matchs lus : on lit leurs classements
LS_STATUT = {"FT": "STATUS_FULL_TIME", "AET": "STATUS_FINAL_AET", "AP": "STATUS_FINAL_PEN", "NS": "STATUS_SCHEDULED",
             "Postp.": "STATUS_POSTPONED", "Canc.": "STATUS_CANCELED", "Int.": "STATUS_SUSPENDED", "Abd.": "STATUS_ABANDONED", "Aband.": "STATUS_ABANDONED",
             "AW": "STATUS_FINAL_AWARDED"}  # AW = gagné sur tapis vert


def ls_ligue_principale(ccd, scd):
    return next((nom for (c, s), nom in LS_LIGUES.items() if c == ccd and (scd == s or scd.startswith(s + "-"))), None)


def ls_logo(img):
    return LS_LOGO + img if img else None


def ls_jour(j):
    """Matchs d'un jour (AAAAMMJJ, en UTC) des ligues LS_LIGUES, au format des lignes de foot.parse (sans buteurs/cartons :
    ils viennent de ls_fiche ; None = on garde ce qui est déjà en base)."""
    out = []
    for s in get(f"{LS_API}/date/soccer/{j}/0?locale=en&MD=1").get("Stages", []):
        ligue = ls_ligue_principale(s.get("Ccd"), s.get("Scd") or "")
        if ligue:
            LS_VUS.add((s["Ccd"], s["Scd"]))
        for e in s.get("Events", []) if ligue else []:
            esd, statut = str(e["Esd"]), LS_STATUT.get(e.get("Eps"), "STATUS_IN_PROGRESS")  # sinon c'est une minute : en cours
            joue = statut not in ("STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_CANCELED") and e.get("Tr1") not in (None, "")
            t1, t2 = e["T1"][0], e["T2"][0]
            nom = feminin if ligue in LS_FEMININ else str
            out.append(("ls" + str(e["Eid"]), ligue, f"{esd[:4]}-{esd[4:6]}-{esd[6:8]}T{esd[8:10]}:{esd[10:12]}Z",
                        nom(t1["Nm"]), nom(t2["Nm"]), int(e["Tr1"]) if joue else None, int(e["Tr2"]) if joue else None, statut,
                        ls_logo(t1.get("Img")), ls_logo(t2.get("Img")), None, None))
    return out


def ls_fiche(eid):
    """(buteurs, cartons, passes) d'un match, au format de foot.py. Équipe = champ Nm (1 domicile, 2 extérieur) ;
    un csc est rangé dans l'équipe qui en profite (vérifié : les buts recomptés donnent le score sur 240 matchs)."""
    d = get(f"{LS_API}/incidents/soccer/{eid}?locale=en")
    def plat(lst):
        for i in lst:
            yield from (plat(i["Incs"]) if "Incs" in i else [i])
    but, cart, pas = [], [], []
    for per in sorted(d.get("Incs") or {}, key=int):
        for i in plat(d["Incs"][per]):
            it = i.get("IT")
            x = {"cote": "dom" if i.get("Nm") == 1 else "ext", "min": f"{i.get('Min', '')}'" + (f"+{i['MinEx']}'" if i.get("MinEx") else ""),
                 "nom": i.get("Pn") or f"{i.get('Fn', '')} {i.get('Ln', '')}".strip() or "?"}
            if it in (36, 37, 39):
                but.append(x | {"nom": x["nom"] + {37: " (pen)", 39: " (csc)"}.get(it, "")})
            elif it == 63:
                pas.append(x)
            elif it in (43, 44, 45):
                cart.append(x | {"type": "J" if it == 43 else "R"})
    return but, cart, pas


def ls_classements(courante):
    """Classements des phases vues dans les matchs lus ce passage (ls_jour remplit LS_VUS) : une ligue à l'arrêt garde
    son ancien classement. Saison = « 25/26 » dans le nom de la phase, sinon la saison en cours."""
    out = []
    def lire(cs):
        try:
            return cs, get(f"{LS_API}/stage/soccer/{cs[0]}/{cs[1]}/0?locale=en&MD=1", essais=1)["Stages"][0]
        except Exception:
            return cs, None  # phase sans classement (coupe, barrage…)
    with ThreadPoolExecutor(4) as pool:
        stages = list(pool.map(lire, sorted(LS_VUS)))
    for (ccd, scd), st in stages:
        ligue = ls_ligue_principale(ccd, scd)
        if st and ligue:
            m = re.search(r"(\d{2})/\d{2}$", st.get("Snm") or "")
            saison = 2000 + int(m.group(1)) if m else courante
            groupe = re.sub(r"\s*\d{2}/\d{2}$", "", st.get("Snm") or ligue)
            for t in [t for l in (st.get("LeagueTable") or {}).get("L", []) for t in l.get("Tables", []) if t.get("LTT") == 1]:
                for e in t.get("team", []):
                    out.append((ligue, groupe, e["rnk"], feminin(e["Tnm"]) if ligue in LS_FEMININ else e["Tnm"], ls_logo(e.get("Img")), e["pld"], e["win"], e["drw"],
                                e["lst"], e["gf"], e["ga"], e["pts"], saison))
    return out


# ---------- football-data.co.uk : fichiers CSV gratuits, faits pour être téléchargés ----------
# Scores seulement (pas de buteurs). Historique depuis 1993-94 (22 championnats) et depuis 2012 (16 autres pays).
FD = "https://www.football-data.co.uk"
FD_DEBUT = 1993
FD_DIV = {"E0": "Premier League", "E1": "Championship (Angleterre)", "E2": "League One (Angleterre)",
          "E3": "League Two (Angleterre)", "EC": "National League (Angleterre)", "SC0": "Premiership (Écosse)",
          "SC1": "Championship (Écosse)", "SC2": "League One (Écosse)", "SC3": "League Two (Écosse)", "D1": "Bundesliga",
          "D2": "2. Bundesliga (Allemagne)", "I1": "Serie A", "I2": "Serie B (Italie)", "SP1": "La Liga", "SP2": "LaLiga 2 (Espagne)",
          "F1": "Ligue 1", "F2": "Ligue 2", "N1": "Eredivisie", "B1": "Pro League (Belgique)", "P1": "Liga Portugal",
          "T1": "Süper Lig (Turquie)", "G1": "Super League (Grèce)"}
FD_PAYS = {"ARG": "Liga Profesional (Argentine)", "AUT": "Bundesliga (Autriche)", "BRA": "Série A (Brésil)",
           "CHN": "Super League (Chine)", "DNK": "Superliga (Danemark)", "FIN": "Veikkausliiga (Finlande)",
           "IRL": "Premier Division (Irlande)", "JPN": "J1 League (Japon)", "MEX": "Liga MX (Mexique)",
           "NOR": "Eliteserien (Norvège)", "POL": "Ekstraklasa (Pologne)", "ROU": "Liga 1 (Roumanie)",
           "RUS": "Premier Liga (Russie)", "SWE": "Allsvenskan (Suède)", "SWZ": "Super League (Suisse)", "USA": "MLS (États-Unis)"}


def fd_csv(url):
    """Lignes du fichier, ou [] s'il n'existe pas (le site renvoie alors une page HTML)."""
    try:
        brut = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except urllib.error.HTTPError as e:
        if e.code in (300, 404):
            return []
        raise
    try:
        txt = brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        txt = brut.decode("latin-1")  # vieux fichiers
    if not txt.startswith(("Div", "Country")):
        return []
    return list(csv.DictReader(io.StringIO(txt)))


def fd_lignes(rows, ligue):
    out = []
    for r in rows:
        dom, ext = r.get("HomeTeam") or r.get("Home"), r.get("AwayTeam") or r.get("Away")
        bd, be = r.get("FTHG", r.get("HG")), r.get("FTAG", r.get("AG"))
        if not (dom and ext and r.get("Date") and bd not in (None, "") and be not in (None, "")):
            continue
        j, m, a = r["Date"].split("/")
        a = ("19" if int(a) > 50 else "20") + a if len(a) == 2 else a
        out.append((ligue, f"{a}-{m}-{j}", dom, ext, int(float(bd)), int(float(be))))
    return out


def fd_saison(div, annee):
    # le site renvoie parfois le fichier d'une AUTRE division (1993-94 : la Liga à la place de la 2e division écossaise…) :
    # on ne garde que les lignes de la division demandée
    rows = [r for r in fd_csv(f"{FD}/mmz4281/{annee % 100:02d}{(annee + 1) % 100:02d}/{div}.csv") if r.get("Div", div) == div]
    return fd_lignes(rows, FD_DIV[div])


def fd_pays(code):
    return fd_lignes(fd_csv(f"{FD}/new/{code}.csv"), FD_PAYS[code])


def fd_id(r):
    """Identifiant stable d'un match football-data (ligue, date, équipe à domicile)."""
    return "fd" + re.sub(r"[^A-Za-z0-9]", "", f"{r[1]}{r[2]}{r[0]}")[:40]  # ASCII : l'id passe dans l'adresse de la page


TSDB = {"Ligue 1": 4334, "Premier League": 4328, "La Liga": 4335, "Serie A": 4332, "Bundesliga": 4331,
        "Ligue des champions": 4480, "Ligue 2": 4401, "Ligue Europa": 4481, "Ligue Conférence": 5071,
        "Coupe de France": 4484, "Liga Portugal": 4344, "Eredivisie": 4337}


def thesportsdb(jours):
    page = tolerant(lambda u: get(u, essais=1).get("events") or [])  # pas de nouvel essai : source d'appoint, trop lente sinon
    out = []
    for ligue, lid in TSDB.items():
        for j in jours:
            time.sleep(3)  # clé gratuite : limite de requêtes par minute
            for e in page(f"https://www.thesportsdb.com/api/v1/json/123/eventsday.php?d={j}&l={lid}"):
                if e.get("strStatus") in ("FT", "Match Finished", "AET") and e.get("intHomeScore") is not None:
                    out.append((ligue, e["strTimestamp"][:10], e["strHomeTeam"], e["strAwayTeam"],
                                int(e["intHomeScore"]), int(e["intAwayScore"])))
    return out


OPENFOOTBALL = {"Ligue 1": "fr.1", "Premier League": "en.1", "La Liga": "es.1", "Serie A": "it.1", "Bundesliga": "de.1",
                "Liga Portugal": "pt.1", "Eredivisie": "nl.1"}


def openfootball(annee):
    saison = f"{annee}-{str(annee + 1)[2:]}"
    out = []
    for ligue, f in OPENFOOTBALL.items():
        try:
            data = get(f"https://raw.githubusercontent.com/openfootball/football.json/master/{saison}/{f}.json")
        except Exception as e:
            print(f"[source] openfootball {ligue}: {e}", file=sys.stderr)
            continue
        for m in data.get("matches", []):
            sc = m.get("score")
            ft = sc.get("ft") if isinstance(sc, dict) else sc  # deux formats selon les fichiers
            if ft and len(ft) == 2:
                out.append((ligue, m["date"], m["team1"], m["team2"], ft[0], ft[1]))
    return out


def openligadb(annee):
    out = []
    for m in get(f"https://api.openligadb.de/getmatchdata/bl1/{annee}"):
        fin = [r for r in m.get("matchResults", []) if r.get("resultTypeID") == 2]
        if m.get("matchIsFinished") and fin:
            out.append(("Bundesliga", m["matchDateTimeUTC"][:10], m["team1"]["teamName"], m["team2"]["teamName"],
                        fin[0]["pointsTeam1"], fin[0]["pointsTeam2"]))
    return out


def ligue1_officiel():
    """Classement officiel de la LFP : {nom_club: points}."""
    d = get("https://ma-api.ligue1.fr/championship-standings/1/general")
    return {e["clubIdentity"]["name"]: e["points"] for e in d["standings"].values()}


def consensus(espn, autres):
    """espn: (bd, be) ou None ; autres: {source: (bd, be)}.
    Renvoie (score_retenu, ecart). ESPN prime ; sinon majorité d'au moins 2 sources d'accord."""
    tous = list(autres.values()) + ([espn] if espn else [])
    ecart = len(set(map(tuple, tous))) > 1
    if espn:
        return tuple(espn), ecart
    votes = {}
    for v in autres.values():
        votes[tuple(v)] = votes.get(tuple(v), 0) + 1
    v, n = max(votes.items(), key=lambda x: x[1], default=(None, 0))
    return (v if n >= 2 else None), ecart


if __name__ == "__main__":
    assert sim("Paris Saint-Germain", "Paris Saint-Germain FC") > 0.9
    assert sim("Internazionale", "Inter") > 0.7
    assert sim("Bayern Munich", "FC Bayern München") > 0.9
    assert sim("Paris FC", "Paris Saint-Germain") < sim("Paris FC", "Paris FC")
    m = [("1", "Ligue 1", "2026-11-22", "Paris FC", "Angers"), ("2", "Ligue 1", "2026-11-22", "Paris Saint-Germain", "Lens")]
    r = [("Ligue 1", "2026-11-22", "Paris Saint-Germain FC", "RC Lens", 2, 0), ("Ligue 1", "2026-11-22", "Paris FC", "SCO Angers", 4, 0)]
    assert apparier(m, r) == {"1": (4, 0), "2": (2, 0)}
    assert ls_ligue({"CompId": "1086", "Cnm": "France", "Snm": "Ligue 1 25/26"}) == "Ligue 1"
    assert ls_ligue({"CompId": "1079", "Cnm": "Europa League", "Snm": "League Stage", "CompN": "Europa League 25/26"}) == "Ligue Europa"
    assert ls_ligue({"CompId": None, "Cnm": "England", "Snm": "Premier League 2"}) is None
    assert ls_ligue({"CompId": "68"}) == "Ligue 1"
    assert ls_ligue_principale("switzerland", "super-league-championship-group") == "Super League (Suisse)"
    assert ls_ligue_principale("poland", "iii-liga-group-1") is None and ls_ligue_principale("poland", "ii-liga") == "II Liga (Pologne)"
    assert ls_ligue_principale("korea-republic", "k-league-2") == "K League 2 (Corée du Sud)"
    assert ls_ligue_principale("hungary", "nb-ii-2024-2025") == "NB II (Hongrie)" and ls_ligue_principale("hungary", "nb-i") == "NB I (Hongrie)"
    assert ls_ligue_principale("finland", "womens-kansallinen-liiga-championship") in LS_FEMININ
    assert ls_ligue_principale("france", "division-1-women") is None  # déjà chez ESPN (fra.w.1)
    assert feminin("Bayern Munich W") == "Bayern Munich (F)" == feminin("Bayern Munich (F)") and feminin("Arsenal") == "Arsenal (F)"
    assert feminin("Sandvikens IF") == "Sandvikens IF (F)" and feminin("Arsenal Women") == "Arsenal (F)" == feminin("Arsenal Femminile")
    assert fd_lignes([{"Date": "05/08/99", "HomeTeam": "A", "AwayTeam": "B", "FTHG": "2", "FTAG": "1"},
                      {"Date": "13/07/2012", "Home": "C", "Away": "D", "HG": "0", "AG": "1"},
                      {"Date": "14/07/2012", "Home": "E", "Away": "F", "HG": "", "AG": ""}], "L") \
        == [("L", "1999-08-05", "A", "B", 2, 1), ("L", "2012-07-13", "C", "D", 0, 1)]
    assert fd_id(("Ligue 1", "1993-07-23", "Saint-Étienne")) == "fd19930723SainttienneLigue1"
    assert consensus((1, 0), {"a": (1, 0)}) == ((1, 0), False)
    assert consensus((1, 0), {"a": (2, 0)}) == ((1, 0), True)
    assert consensus(None, {"a": (2, 0), "b": (2, 0)}) == ((2, 0), False)
    assert consensus(None, {"a": (2, 0)}) == (None, False)
    print("ok")
