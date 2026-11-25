"""Scores LiveScore en direct -> direct.json (lancé toutes les 5 min par .github/workflows/direct.yml).
LiveScore refuse les appels venant d'un navigateur : la page lit donc ce fichier au lieu de LiveScore."""
import json, sys
from datetime import datetime, timedelta, timezone
import sources as S


def matchs_du_jour(j):
    """[{id, buts_dom, buts_ext, statut, minute}] des ligues suivies pour le jour j (AAAAMMJJ, UTC)."""
    out = []
    for s in S.get(f"{S.LS_API}/date/soccer/{j}/0?locale=en&MD=1").get("Stages", []):
        if not S.ls_ligue_principale(s.get("Ccd"), s.get("Scd") or ""):
            continue
        for e in s.get("Events", []):
            eps = e.get("Eps") or ""
            statut = S.LS_STATUT.get(eps, "STATUS_IN_PROGRESS")  # sinon c'est une minute (ou HT) : en cours
            joue = e.get("Tr1") not in (None, "") and statut not in ("STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_CANCELED")
            out.append({"id": f"ls{e['Eid']}", "buts_dom": int(e["Tr1"]) if joue else None, "buts_ext": int(e["Tr2"]) if joue else None,
                        "statut": statut, "minute": "Mi-temps" if eps == "HT" else eps if statut == "STATUS_IN_PROGRESS" else ""})
    return out


if __name__ == "__main__":
    maintenant = datetime.now(timezone.utc)
    m = []
    for j in {(maintenant - timedelta(hours=3)).strftime("%Y%m%d"), maintenant.strftime("%Y%m%d")}:  # matchs du soir passés minuit
        try:
            m += matchs_du_jour(j)
        except Exception as e:
            print(f"[erreur] LiveScore {j}: {e}", file=sys.stderr)
    with open("direct.json", "w", encoding="utf-8") as f:
        json.dump({"maj": maintenant.isoformat(timespec="seconds"), "matchs": m}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(m)} matchs, dont {sum(x['statut'] == 'STATUS_IN_PROGRESS' for x in m)} en cours")
