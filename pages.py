"""Pages statiques lisibles par Google (une par joueur, équipe, compétition) + sitemap.
La page index.html est une appli : Google n'y voit pas les fiches (#joueur=...), d'où ces pages."""
import re, shutil, unicodedata
from html import escape as e
from urllib.parse import quote

SITE = "https://julien773901-oss.github.io/Foot/"  # à changer si on branche un nom de domaine
PAR_SITEMAP = 45000  # Google : 50 000 adresses max par fichier sitemap

CSS = """:root{--bg:#f6f7f9;--card:#fff;--txt:#16181d;--mut:#6b7280;--line:#e5e7eb;--acc:#0a7c4a}
@media (prefers-color-scheme:dark){:root{--bg:#111317;--card:#1a1d23;--txt:#e8eaed;--mut:#9aa0a6;--line:#2a2e36;--acc:#3ccf8e;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:16px}a{color:var(--acc)}h1{margin:.2em 0}.mut{color:var(--mut)}
nav{font-size:14px;margin-bottom:8px}.app{display:inline-block;margin:8px 0;padding:6px 14px;border-radius:99px;background:var(--acc);color:var(--bg);text-decoration:none;font-weight:600}
.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px;margin:8px 0 20px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:center;white-space:nowrap}
th{color:var(--mut);font-weight:600}td.g,th.g{text-align:left}tr:last-child td{border-bottom:0}
ul.l{columns:3 200px;padding-left:18px}footer{margin:24px 0;font-size:13px}
.palm{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 20px}.palm div{width:104px;text-align:center;font-size:12px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 4px}
.palm img{display:block;width:100%;height:64px;object-fit:contain}.palm b{display:block;font-size:18px;color:var(--acc)}
figure.ph{float:right;margin:0 0 8px 12px;text-align:center;font-size:11px;color:var(--mut)}
figure.ph img{width:120px;height:120px;object-fit:cover;object-position:50% 20%;border-radius:50%;background:var(--line);display:block;margin:0 auto 4px}"""


def slug(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"


def slugs(noms):
    """nom -> slug unique (les homonymes après accents retirés prennent -2, -3...), stable d'un passage à l'autre."""
    out, pris = {}, {}
    for n in sorted(noms):
        b = slug(n)
        pris[b] = pris.get(b, 0) + 1
        out[n] = b if pris[b] == 1 else f"{b}-{pris[b]}"
    return out


def nom_saison(s):
    return f"{s}-{str(s + 1)[2:]}"


def page(titre, desc, chemin, corps, app):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{SITE}{chemin}">
<link rel="stylesheet" href="../pages.css"></head><body><main>
<nav><a href="../">Base Foot</a> · <a href="../plan.html">Toutes les compétitions</a></nav>
{corps}
<a class="app" href="../{app}">Ouvrir la fiche interactive</a>
<footer class="mut">Base Foot : résultats, classements et statistiques de football. Données ESPN, LiveScore, football-data.co.uk.</footer>
</main></body></html>"""


def table(entetes, lignes):
    th = "".join(f'<th{" class=g" if g else ""}>{e(t)}</th>' for t, g in entetes)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{"".join(lignes)}</tbody></table></div>'


def val(l, i):
    v = l[i] if i < len(l) else None  # lignes de carrière raccourcies (stats absentes en fin de ligne)
    return "–" if v is None else str(v)


def age(naissance, jour):
    return int(jour[:4]) - int(naissance[:4]) - (jour[5:10] < naissance[5:10])


def ligne_identite(v, jour):
    """[naissance, nationalité, drapeau, taille cm, poids kg, poste] -> « Né le 20/12/1998 (27 ans) · France · 1,78 m · ... »"""
    naiss, nat, _, taille, poids, poste = v[:6]
    morceaux = [f"Né le {naiss[8:10]}/{naiss[5:7]}/{naiss[:4]} ({age(naiss, jour)} ans)" if naiss else None, nat,
                f"{taille // 100},{taille % 100:02d} m" if taille else None, f"{poids} kg" if poids else None, poste]
    return " · ".join(x for x in morceaux if x)


def bloc_photo(nom, v):
    """Photo du joueur (adresse ESPN ou Wikimedia Commons, jamais copiée sur le site) + crédit ; "" sans photo."""
    if len(v) < 7 or not v[6]:
        return ""
    credit = (f'<a href="https://commons.wikimedia.org/wiki/File:{quote(v[7].replace(" ", "_"))}">Wikimedia Commons</a>'
              if len(v) > 7 and v[7] else "ESPN")
    return f'<figure class="ph"><img src="{e(v[6])}" alt="Photo de {e(nom)}" width="120" height="120" loading="lazy"><figcaption>Photo : {credit}</figcaption></figure>'


def bloc_palmares(titres, trophees):
    """titres : [[compétition, édition, vainqueur, saisons]] -> cases « photo du trophée, ×N, nom, éditions »."""
    par = {}
    for c, a, *_ in titres:
        par.setdefault(c, set()).add(a)
    if not par:
        return ""
    cases = []
    for c, ans in sorted(par.items(), key=lambda x: (-len(x[1]), x[0])):
        t = trophees.get(c)
        img = f'<img src="{e(t[0])}" alt="Trophée : {e(c)}" loading="lazy">' if t else "🏆"
        cases.append(f"<div>{img}{f'<b>×{len(ans)}</b>' if len(ans) > 1 else ''}{e(c)}<br><span class=mut>{e(', '.join(sorted(ans, reverse=True)[:6]))}</span></div>")
    credit = " Photos des trophées : Wikimedia Commons." if any(trophees.get(c, [None, None])[1] for c in par) else ""
    return f"<h2>Palmarès</h2><div class=palm>{''.join(cases)}</div><p class=mut>Titres trouvés dans la base (classements finaux et finales).{credit}</p>"


def ecrire(racine, m, car, clas, courante, maj, iden=None, palm=None):
    """m : matchs exportés ; car : {joueur: lignes de carrière (format foot.carrieres)} ; clas : classements ;
    iden : {joueur: [naissance, nationalité, drapeau, taille, poids, poste]}."""
    iden = iden or {}
    palm = palm or {"titres": [], "trophees": {}}
    tit_eq = {}
    for t in palm["titres"]:
        tit_eq.setdefault(t[2], []).append(t)
    for d in ("joueur", "equipe", "competition"):
        shutil.rmtree(racine / d, ignore_errors=True)  # un joueur disparu ne doit pas laisser de page morte
        (racine / d).mkdir()
    (racine / "pages.css").write_text(CSS, encoding="utf-8")
    equipes = {x[k] for x in m for k in ("domicile", "exterieur")}
    ligues = {x["ligue"] for x in m}
    sj, se, sl = slugs(car), slugs(equipes), slugs(ligues)
    lien_e = lambda n: f'<a href="../equipe/{se[n]}.html">{e(n)}</a>' if n in se else e(n)
    lien_l = lambda n: f'<a href="../competition/{sl[n]}.html">{e(n)}</a>' if n in sl else e(n)
    lien_j = lambda n: f'<a href="../joueur/{sj[n]}.html">{e(n)}</a>'
    par_equipe, par_ligue = {}, {}  # (saison, joueur, ligne) pour les listes de joueurs
    adresses = []

    # joueurs
    for nom, ls in car.items():
        ls = sorted(ls, key=lambda l: (-l[0], l[2]))
        for l in ls:
            par_equipe.setdefault(l[1], []).append((nom, l))
            par_ligue.setdefault(l[2], []).append((nom, l))
        buts = sum(l[5] for l in ls)
        clubs = list(dict.fromkeys(l[1] for l in ls))
        avec_tirs = any(len(l) > 10 and l[10] is not None for l in ls)
        cols = [("MJ", 3), ("Buts", 5), ("Passes D.", 7), ("Jaunes", 8), ("Rouges", 9)] + ([("Tirs", 10), ("Fautes", 12)] if avec_tirs else [])
        lignes = [f"<tr><td>{nom_saison(l[0])}</td><td class=g>{lien_e(l[1])}</td><td class=g>{lien_l(l[2])}</td>"
                  + "".join(f"<td>{val(l, i)}</td>" for _, i in cols) + "</tr>" for l in ls]
        saisons = sorted({l[0] for l in ls})
        periode = nom_saison(saisons[0]) if len(saisons) == 1 else f"{nom_saison(saisons[0])} à {nom_saison(saisons[-1])}"
        desc = f"{nom} ({', '.join(clubs[:3])}) : {buts} but{'s' * (buts > 1)} en {len(saisons)} saison{'s' * (len(saisons) > 1)} ({periode}). Statistiques saison par saison, club par club."
        idt = ligne_identite(iden[nom], maj) if nom in iden else ""
        vu = {(l[0], l[1], l[2]) for l in ls}
        palmares = bloc_palmares([t for eq_ in {l[1] for l in ls} for t in tit_eq.get(eq_, []) if any((s_, t[2], t[0]) in vu for s_ in t[3])],
                                 palm["trophees"])
        corps = (bloc_photo(nom, iden.get(nom, [])) + f"<h1>{e(nom)}</h1>" + (f"<p>{e(idt)}</p>" if idt else "") + f"<p class=mut>{' · '.join(lien_e(c) for c in clubs[:6])}</p>"
                 f"<p>{e(desc)}</p><h2>Carrière saison par saison</h2>"
                 + palmares + table([("Saison", 0), ("Club", 1), ("Compétition", 1)] + [(t, 0) for t, _ in cols], lignes)
                 + "<p class=mut>« – » = inconnu : nombre de matchs et passes décisives seulement sur les saisons récentes.</p>")
        chemin = f"joueur/{sj[nom]}.html"
        (racine / chemin).write_text(page(f"{nom} : stats et carrière | Base Foot", desc, chemin, corps, f"#joueur={quote(nom)}"), encoding="utf-8")
        adresses.append(chemin)

    # équipes
    matchs_eq = {}
    for x in m:
        for k in ("domicile", "exterieur"):
            matchs_eq.setdefault(x[k], []).append(x)
    clas_eq = {}
    for c in clas:
        clas_eq.setdefault(c["equipe"], {})[(c["saison"], c["ligue"])] = c  # une ligne par saison/compétition (groupes : la dernière)
    score = lambda x: f"{x['buts_dom']}-{x['buts_ext']}" if x["buts_dom"] is not None else "–"
    for eq in equipes:
        ms = matchs_eq.get(eq, [])
        finis = [x for x in ms if "FULL_TIME" in x["statut"] or "FINAL" in x["statut"]][-10:][::-1]
        a_venir = [x for x in ms if x["statut"] == "STATUS_SCHEDULED"][:5]
        ligne_m = lambda x: (f"<tr><td>{x['date_utc'][:10]}</td><td class=g>{lien_l(x['ligue'])}</td><td class=g>{lien_e(x['domicile'])}</td>"
                             f"<td>{score(x)}</td><td class=g>{lien_e(x['exterieur'])}</td></tr>")
        ent_m = [("Date", 0), ("Compétition", 1), ("Domicile", 1), ("Score", 0), ("Extérieur", 1)]
        hist = sorted(clas_eq.get(eq, {}).values(), key=lambda c: (-c["saison"], c["ligue"]))
        joueurs = {}
        for nom, l in par_equipe.get(eq, []):
            if l[0] >= courante - 1:
                j = joueurs.setdefault((l[0], nom), [0, 0])
                j[0] += l[5]
                j[1] += l[3] or 0
        top = sorted(joueurs.items(), key=lambda t: (-t[0][0], -t[1][0], -t[1][1], t[0][1]))[:60]
        ligues_eq = list(dict.fromkeys(x["ligue"] for x in reversed(ms)))[:4]
        desc = f"{eq} : résultats, calendrier, classements et buteurs" + (f" ({', '.join(ligues_eq)})" if ligues_eq else "") + "."
        corps = (f"<h1>{e(eq)}</h1><p>{e(desc)}</p>" + bloc_palmares(tit_eq.get(eq, []), palm["trophees"])
                 + (f"<h2>Prochains matchs</h2>{table(ent_m, [ligne_m(x) for x in a_venir])}" if a_venir else "")
                 + (f"<h2>Derniers résultats</h2>{table(ent_m, [ligne_m(x) for x in finis])}" if finis else "")
                 + (f"<h2>Joueurs (saisons récentes)</h2>" + table([("Saison", 0), ("Joueur", 1), ("Buts", 0), ("MJ", 0)],
                    [f"<tr><td>{nom_saison(s)}</td><td class=g>{lien_j(n)}</td><td>{b}</td><td>{mj or '–'}</td></tr>" for (s, n), (b, mj) in top]) if top else "")
                 + (f"<h2>Classements</h2>" + table([("Saison", 0), ("Compétition", 1), ("Rang", 0), ("Pts", 0), ("J", 0)],
                    [f"<tr><td>{nom_saison(c['saison'])}</td><td class=g>{lien_l(c['ligue'])}</td><td>{c['rang']}</td><td>{c['pts']}</td><td>{c['joues']}</td></tr>" for c in hist]) if hist else ""))
        chemin = f"equipe/{se[eq]}.html"
        (racine / chemin).write_text(page(f"{eq} : résultats, classement, joueurs | Base Foot", desc, chemin, corps, f"#equipe={quote(eq)}"), encoding="utf-8")
        adresses.append(chemin)

    # compétitions
    clas_lg = {}
    for c in clas:
        clas_lg.setdefault(c["ligue"], {}).setdefault(c["saison"], []).append(c)
    for lg in ligues:
        derniere = max(clas_lg.get(lg, {}), default=None)
        cl = clas_lg.get(lg, {}).get(derniere, [])
        buteurs = {}
        saison_b = max((l[0] for _, l in par_ligue.get(lg, [])), default=None)
        for nom, l in par_ligue.get(lg, []):
            if l[0] == saison_b and l[5]:
                buteurs[(nom, l[1])] = buteurs.get((nom, l[1]), 0) + l[5]
        top = sorted(buteurs.items(), key=lambda t: (-t[1], t[0][0]))[:30]
        eqs = sorted({x[k] for x in m if x["ligue"] == lg for k in ("domicile", "exterieur")}) if not cl else []
        desc = f"{lg} : classement, résultats et meilleurs buteurs" + (f" saison {nom_saison(derniere)}" if derniere else "") + "."
        corps = (f"<h1>{e(lg)}</h1><p>{e(desc)}</p>"
                 + (f"<h2>Classement {nom_saison(derniere)}</h2>" + table([("#", 0), ("Équipe", 1), ("J", 0), ("G", 0), ("N", 0), ("P", 0), ("Diff.", 0), ("Pts", 0)],
                    [f"<tr><td>{c['rang']}</td><td class=g>{lien_e(c['equipe'])}</td><td>{c['joues']}</td><td>{c['g']}</td><td>{c['n']}</td><td>{c['p']}</td>"
                     f"<td>{(c['bp'] or 0) - (c['bc'] or 0):+d}</td><td><b>{c['pts']}</b></td></tr>" for c in cl]) if cl else "")
                 + (f"<h2>Meilleurs buteurs {nom_saison(saison_b)}</h2>" + table([("Joueur", 1), ("Club", 1), ("Buts", 0)],
                    [f"<tr><td class=g>{lien_j(n)}</td><td class=g>{lien_e(c)}</td><td>{b}</td></tr>" for (n, c), b in top]) if top else "")
                 + (f"<h2>Équipes</h2><ul class=l>{''.join(f'<li>{lien_e(x)}</li>' for x in eqs)}</ul>" if eqs else ""))
        chemin = f"competition/{sl[lg]}.html"
        (racine / chemin).write_text(page(f"{lg} : classement, résultats, buteurs | Base Foot", desc, chemin, corps, ""), encoding="utf-8")
        adresses.append(chemin)

    # plan du site (lien depuis l'accueil : Google y trouve les compétitions, puis les équipes et les joueurs)
    plan = f"<h1>Toutes les compétitions</h1><ul class=l>{''.join(f'<li>{lien_l(lg)}</li>' for lg in sorted(ligues))}</ul>"
    (racine / "plan.html").write_text(page("Toutes les compétitions de football | Base Foot", "Classements, résultats et buteurs de "
                                           f"{len(ligues)} compétitions de football.", "plan.html", plan, "").replace('href="../', 'href="./'), encoding="utf-8")
    adresses = ["", "plan.html"] + adresses
    jour = maj[:10]
    morceaux = [adresses[i:i + PAR_SITEMAP] for i in range(0, len(adresses), PAR_SITEMAP)]
    for i, mo in enumerate(morceaux):
        (racine / f"sitemap-{i}.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{SITE}{a}</loc><lastmod>{jour}</lastmod></url>" for a in mo) + "</urlset>", encoding="utf-8")
    (racine / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<sitemap><loc>{SITE}sitemap-{i}.xml</loc><lastmod>{jour}</lastmod></sitemap>" for i in range(len(morceaux))) + "</sitemapindex>", encoding="utf-8")
    for f in racine.glob("sitemap-*.xml"):  # anciens morceaux en trop
        if int(f.stem.split("-")[1]) >= len(morceaux):
            f.unlink()
    print(f"[pages] {len(car)} joueurs, {len(equipes)} équipes, {len(ligues)} compétitions, {len(morceaux)} sitemaps")


if __name__ == "__main__":
    assert slug("Kylian Mbappé") == "kylian-mbappe" and slug("Ødegaard!") == "degaard" and slug("") == "x"
    assert slugs(["Nacional", "Nacional!"]) == {"Nacional": "nacional", "Nacional!": "nacional-2"}
    assert val([1, 2], 5) == "–" and val([1, None], 1) == "–" and val([0], 0) == "0"
    assert ligne_identite(["1998-12-20", "France", "fra", 178, 74, "Attaquant"], "2026-11-25") == \
        "Né le 20/12/1998 (27 ans) · France · 1,78 m · 74 kg · Attaquant"
    assert ligne_identite(["2000-11-26", None, None, None, None, None], "2026-11-25") == "Né le 26/11/2000 (25 ans)"
    assert bloc_photo("X", ["2000-01-01", None, None, None, None, None]) == ""
    assert 'src="https://a.espncdn.com/p.png"' in bloc_photo("X", [None] * 6 + ["https://a.espncdn.com/p.png"]) and "Photo : ESPN" in \
        bloc_photo("X", [None] * 6 + ["https://a.espncdn.com/p.png"])
    b = bloc_photo("Pep Biel", [None] * 6 + ["https://commons.wikimedia.org/wiki/Special:FilePath/Pep%20Biel.jpg?width=250", "Pep Biel.jpg"])
    assert 'href="https://commons.wikimedia.org/wiki/File:Pep_Biel.jpg"' in b and 'alt="Photo de Pep Biel"' in b
    assert ligne_identite(["2000-11-26", None, None, None, None, None, "u", "f"], "2026-11-25") == "Né le 26/11/2000 (25 ans)"
    tr = {"Ligue 1": ["https://x/l1.png", None], "Coupe de France": ["https://commons/cdf.jpg", "CDF.jpg"]}
    b = bloc_palmares([["Ligue 1", "2023-24", "PSG", [2023]], ["Ligue 1", "2022-23", "PSG", [2022]], ["Coupe de France", "2023-24", "PSG", [2023]]], tr)
    assert b.index("Ligue 1") < b.index("Coupe de France") and "<b>×2</b>" in b and "Wikimedia Commons" in b and bloc_palmares([], tr) == ""
    print("auto-tests OK")
