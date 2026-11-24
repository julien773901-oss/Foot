"""Met à jour foot.db : matchs (avec logos et buteurs) et classements.
1er lancement : toute la saison. Ensuite : 7 jours avant / 14 jours après + les jours jamais lus correctement.
Lancer : python foot.py"""
import json, sqlite3, sys, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sources as S

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
          "bol.ply.rel": "Barrages (Bolivie)", "chn.1.promotion.relegation": "Barrages (Chine)"}
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


def participations(summary):
    """Joueurs ayant joué : [(joueur, id_espn, cote, titulaire, entre, sorti)] (les remplaçants restés sur le banc sont exclus)."""
    comp = summary["header"]["competitions"][0]["competitors"]
    id_dom = next(t["team"]["id"] for t in comp if t["homeAway"] == "home")
    out = []
    for eq in summary.get("rosters", []):
        cote = "dom" if eq["team"]["id"] == id_dom else "ext"
        for p in eq.get("roster", []):
            if p.get("starter") or p.get("subbedIn"):
                out.append((p["athlete"]["displayName"], p["athlete"].get("id"), cote,
                            int(bool(p.get("starter"))), int(bool(p.get("subbedIn"))), int(bool(p.get("subbedOut")))))
    return out


FICHE_VERSION = 2  # monter ce numéro force la relecture des fiches (ex. quand on y lit une nouvelle info)
COLS = ["id", "ligue", "date_utc", "domicile", "exterieur", "buts_dom", "buts_ext", "statut", "logo_dom",
        "logo_ext", "buteurs", "cartons", "maj"]


def parse(event, ligue):
    c = event["competitions"][0]
    eq = {t["homeAway"]: t for t in c["competitors"]}
    h, a = eq["home"], eq["away"]
    statut = event["status"]["type"]["name"]
    joue = statut != "STATUS_SCHEDULED"  # pas de score tant que le match n'a pas commencé
    score = lambda t: int(t["score"]) if joue and t.get("score") not in (None, "") else None
    return (event["id"], ligue, event["date"], h["team"]["displayName"], a["team"]["displayName"],
            score(h), score(a), statut, h["team"].get("logo"), a["team"].get("logo"),
            json.dumps(buteurs(c, h["team"]["id"]), ensure_ascii=False),
            json.dumps(cartons(c, h["team"]["id"]), ensure_ascii=False))


PREMIERE_SAISON = 2001  # ESPN n'a rien avant (2001-02 pour les grands championnats, ~2008 pour beaucoup d'autres)
NB_DETAILLEES = 2  # passeurs + compositions seulement pour les saisons récentes (sinon la base dépasse les limites de GitHub)
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
            lignes.append((ligue, groupe["name"], n("rank"), e["team"]["displayName"],
                           (e["team"].get("logos") or [{}])[0].get("href"), n("gamesPlayed"), n("wins"),
                           n("ties"), n("losses"), n("pointsFor"), n("pointsAgainst"), n("points"), saison))
    return lignes


def jour(code, ligue, j):
    try:
        if code.startswith("livescore"):  # une seule page par jour pour toutes les ligues lues chez LiveScore
            return S.ls_jour(j), True
        return [parse(ev, ligue) for ev in get(f"{API}/site/v2/sports/soccer/{code}/scoreboard?dates={j}").get("events", [])], True
    except Exception as e:
        print(f"[erreur] {ligue} {j}: {e}", file=sys.stderr)
        return [], False


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
        titulaire INTEGER, entre INTEGER, sorti INTEGER, PRIMARY KEY (match_id, joueur));""")
    for col in ("cartons TEXT", "passes TEXT", "fiche_lue INTEGER"):  # colonnes ajoutées après coup
        try:
            db.execute(f"ALTER TABLE matchs ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # déjà là
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = date.today()
    courante = saison_de(today.isoformat())
    SAISONS = list(range(courante, PREMIERE_SAISON - 1, -1))
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
        debut = min(debut, date(SAISONS[-1], 7, 1))  # + les saisons précédentes (juillet à juin)
        deja = {j for (j,) in db.execute("SELECT jour FROM jours_lus WHERE code=?", (code,))}
        # jours récents + toute journée ancienne jamais lue correctement (rattrape les trous)
        taches += [(code, ligue, j) for i in range((today + timedelta(days=14) - debut).days + 1)
                   if (j := (debut + timedelta(days=i)).strftime("%Y%m%d")) not in deja]
    # pays absents d'ESPN : LiveScore, qui ne garde qu'environ 1 an de matchs
    # le code change avec le nombre de ligues : en ajouter fait relire toutes les journées LiveScore une fois
    ls_code = f"livescore{len(S.LS_LIGUES)}"
    db.execute("DELETE FROM jours_lus WHERE code LIKE 'livescore%' AND code != ?", (ls_code,))
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
    db.executemany(f"INSERT INTO matchs ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))}) "
                   f"ON CONFLICT(id) DO UPDATE SET {','.join(f'{c}=coalesce(excluded.{c}, {c})' if c in ('buteurs', 'cartons') else f'{c}=excluded.{c}' for c in COLS[1:])}",
                   [m + (maintenant,) for m in matchs])

    # fiche détaillée de chaque match terminé (passeurs + qui a joué), 1500 max par passage (la suite au prochain)
    code_de = {v: k for k, v in LIGUES.items()}
    a_faire = (f"(fiche_lue IS NULL OR fiche_lue < {FICHE_VERSION}) AND (statut LIKE '%FULL_TIME%' OR statut LIKE '%FINAL%')"
               f" AND date_utc >= '{debut_recent}'")
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
        db.executemany("INSERT OR IGNORE INTO participations VALUES (?,?,?,?,?,?,?)", [(mid,) + j for j in joueurs])
    reste = db.execute(f"SELECT count(*) FROM matchs WHERE {a_faire}").fetchone()[0]
    print(f"[temps] fiches: {time.time() - t0:.0f} s ({len(lues)} lues, {reste} restantes)")
    cl_lus = set(db.execute("SELECT code, jour FROM jours_lus WHERE code LIKE 'cl:%'").fetchall())
    for saison in SAISONS:
        for code, ligue in LIGUES.items():
            if (f"cl:{code}", str(saison)) in cl_lus:
                continue  # saison ancienne déjà lue : son classement ne bouge plus
            try:
                lignes = classement(code, ligue, saison)
                if saison < courante - 1:
                    db.execute("INSERT OR IGNORE INTO jours_lus VALUES (?,?)", (f"cl:{code}", str(saison)))
            except Exception as e:
                erreurs += 1
                print(f"[erreur] classement {ligue} {saison}: {e}", file=sys.stderr)
                continue  # on garde l'ancien classement plutôt que de l'effacer
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
    etat = {"ESPN": f"{n_tot - (n_ls or 0)} matchs (source principale)", "LiveScore (pays absents d'ESPN)": f"{n_ls or 0} matchs"}
    for nom, lire in [("LiveScore", lambda: S.livescore(jours_lus)),
                      ("TheSportsDB", lambda: S.thesportsdb(recents)),
                      ("openfootball", lambda: [r for a in RECENTES for r in S.openfootball(a)]),
                      ("OpenLigaDB", lambda: [r for a in RECENTES for r in S.openligadb(a)])]:
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
        x["sources"] = ({"LiveScore" if x["id"].startswith("ls") else "ESPN": espn} if espn else {}) | src.get(x["id"], {})
        if not espn and score:  # ESPN n'a pas le score : on prend celui confirmé par 2 autres sources
            x["buts_dom"], x["buts_ext"], x["statut"], x["secours"] = score[0], score[1], "STATUS_FULL_TIME", True
    # un fichier par saison (matchs-2025.json...) ; matchs.json = saison en cours
    clas = table("SELECT * FROM classement ORDER BY ligue, groupe, rang")
    saison_match = {x["id"]: saison_de(x["date_utc"]) for x in m}
    jou = {s: {} for s in SAISONS}
    # qui a joué quoi, chargé seulement par la fiche joueur : {joueur: {"id": id_espn, "m": [[match, cote, "T"|"E", sorti]]}}
    for mid, nom, ide, cote, tit, ent, sor in db.execute(
            "SELECT p.match_id, joueur, id_espn, cote, titulaire, entre, sorti FROM participations p "
            "JOIN matchs m ON m.id = p.match_id ORDER BY m.date_utc"):
        if saison_match.get(mid) in jou:
            jou[saison_match[mid]].setdefault(nom, {"id": ide, "m": []})["m"].append([mid, cote, "T" if tit else "E", sor])
    for s in SAISONS:
        donnees = json.dumps({"maj": maintenant, "saison": s, "saisons": SAISONS, "courante": courante,
                              "ligues": LIGUES | {f"ls:{c}/{s}": nom for (c, s), nom in S.LS_LIGUES.items()},
                              "sources": etat, "matchs": [x for x in m if saison_match[x["id"]] == s],
                              "classement": [c for c in clas if c["saison"] == s]}, ensure_ascii=False)
        joueurs = json.dumps(jou[s], ensure_ascii=False, separators=(",", ":"))
        for suffixe in [f"-{s}"] + ([""] if s == courante else []):
            DB.with_name(f"matchs{suffixe}.json").write_text(donnees, encoding="utf-8")
            DB.with_name(f"joueurs{suffixe}.json").write_text(joueurs, encoding="utf-8")
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
        {"starter": True, "subbedOut": True, "athlete": {"displayName": "A", "id": "1"}},
        {"starter": False, "subbedIn": True, "athlete": {"displayName": "B", "id": "2"}},
        {"starter": False, "athlete": {"displayName": "Banc", "id": "3"}}]}]
    assert saison_de("2026-08-21T18:45Z") == 2026 and saison_de("2026-05-10T18:00Z") == 2025
    assert participations(resume) == [("A", "1", "ext", 1, 0, 1), ("B", "2", "ext", 0, 1, 0)]
    main()
