// Relais Cloudflare (Worker) : LiveScore refuse les navigateurs, ce relais lit LiveScore à leur place.
// À coller dans le Worker sur dash.cloudflare.com (le site l'appelle chaque minute pendant les matchs).
// Appel : https://<relais>.workers.dev/?j=AAAAMMJJ  ->  [[id LiveScore, buts dom, buts ext, statut ou minute], ...]
// Ne relaie que la liste des matchs d'un jour (pas un relais ouvert vers n'importe quelle adresse).
export default {
  async fetch(req) {
    const j = new URL(req.url).searchParams.get("j") || "";
    const cors = { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" };
    if (!/^\d{8}$/.test(j)) return new Response('"j=AAAAMMJJ attendu"', { status: 400, headers: cors });
    const src = await fetch(`https://prod-public-api.livescore.com/v1/api/app/date/soccer/${j}/0?locale=en&MD=1`,
      { headers: { "User-Agent": "Mozilla/5.0 (base-foot)" }, cf: { cacheTtl: 30, cacheEverything: true } });  // 30 s de cache
    if (!src.ok) return new Response(`"LiveScore ${src.status}"`, { status: 502, headers: cors });
    const out = [];
    for (const s of (await src.json()).Stages || [])
      for (const e of s.Events || []) out.push([String(e.Eid), e.Tr1 ?? null, e.Tr2 ?? null, e.Eps ?? ""]);
    return new Response(JSON.stringify(out), { headers: { ...cors, "Cache-Control": "public, max-age=30" } });
  },
};
