// In-browser Customer Finder engine for the static (GitHub Pages) build.
// Concatenated after teams.js, classifier.js, dedupe-core.js, match.js, responder.js.
// Mirrors the server API (state / search / runs / leads / insights) over localStorage,
// so the same dashboard UI works unchanged.
//
// Limits of the static build (by design; no server exists):
//   * only keyless public APIs that allow browser requests (Reddit public JSON, Bluesky, Lemmy)
//   * X / Brave / Google need secret keys and are NOT available here
//   * leads are stored in THIS browser (use Export/Import to move or back them up)

const CF_STORE_KEY = "gl_customer_finder_v1";
const CF_STATUSES = ["NEW", "REVIEWED", "CONTACTED", "RESPONDED", "CLICKED", "CONVERTED", "DISMISSED"];
const CF_UNAVAILABLE = "Live search unavailable. No new leads were added.";
const CF_MAX_AGE_DAYS = 45;
const CF_CATALOGUE = /*CATALOGUE*/[];

function cfLoad() { try { return JSON.parse(localStorage.getItem(CF_STORE_KEY)) || { runs: [], leads: [] }; } catch { return { runs: [], leads: [] }; } }
function cfSave(db) { localStorage.setItem(CF_STORE_KEY, JSON.stringify(db)); }
function cfId(p) { const a = new Uint8Array(6); crypto.getRandomValues(a); return p + "_" + [...a].map((b) => b.toString(16).padStart(2, "0")).join(""); }
async function cfHash(s) { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)); return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join(""); }
function cfRedact(s) {
  return String(s || "").replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email removed]")
    .replace(/(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b/g, "[phone removed]");
}
const cfSleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cfGet(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(15000) });
  if (res.status === 429) throw new Error("rate limited (429). Try again in a few minutes");
  if (res.status === 401 || res.status === 403) throw new Error(`access denied (${res.status})`);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

const CF_SOURCES = [
  {
    id: "reddit", label: "Reddit", status: () => ({ enabled: true, mode: "public JSON from your browser" }),
    async search() {
      const apparel = "(shirt OR hoodie OR sweatshirt OR tee OR merch OR apparel OR crewneck)";
      const intent = `("where can i" OR "where to buy" OR "looking for" OR "anyone know" OR recommendations OR "where did you get" OR "need a")`;
      const qs = [
        { q: `michigan ${apparel} ${intent}`, sub: null, label: "michigan apparel + intent" },
        { q: `wolverines ${apparel}`, sub: null, label: "wolverines apparel" },
        { q: apparel, sub: "MichiganWolverines", label: "r/MichiganWolverines apparel" },
        { q: apparel, sub: "uofm", label: "r/uofm apparel" },
        { q: apparel, sub: "annarbor", label: "r/annarbor apparel" },
      ];
      const items = []; let ok = 0, err = null;
      for (const { q, sub, label } of qs) {
        const p = new URLSearchParams({ q, sort: "new", t: "month", limit: "50", type: "link", raw_json: "1", ...(sub ? { restrict_sr: "1" } : {}) });
        try {
          const j = await cfGet(`https://www.reddit.com${sub ? "/r/" + sub : ""}/search.json?${p}`); ok++;
          for (const c of j?.data?.children || []) {
            const d = c.data || {};
            if (!d.author || d.author === "[deleted]" || d.author === "AutoModerator" || d.stickied || d.promoted) continue;
            items.push({ platform: "Reddit", author: `u/${d.author}`, authorUrl: `https://www.reddit.com/user/${d.author}`, title: d.title, text: d.selftext || "",
              url: `https://www.reddit.com${d.permalink}`, postedAt: d.created_utc ? new Date(d.created_utc * 1000).toISOString() : null, query: label });
          }
        } catch (e) { err = e; }
        await cfSleep(2200);
      }
      if (!ok) throw err || new Error("no response");
      return items;
    },
  },
  {
    id: "bluesky", label: "Bluesky", status: () => ({ enabled: true, mode: "public search API" }),
    async search() {
      const items = []; let ok = 0, err = null;
      for (const q of ["michigan shirt", "michigan hoodie", "michigan sweatshirt", "wolverines shirt", "michigan merch"]) {
        try {
          const j = await cfGet(`https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?${new URLSearchParams({ q, sort: "latest", limit: "50", lang: "en" })}`); ok++;
          for (const p of j?.posts || []) {
            const rkey = String(p.uri || "").split("/").pop(), h = p.author?.handle;
            if (!h || !rkey) continue;
            items.push({ platform: "Bluesky", author: "@" + h, authorUrl: `https://bsky.app/profile/${h}`, text: p.record?.text || "",
              url: `https://bsky.app/profile/${h}/post/${rkey}`, postedAt: p.record?.createdAt || p.indexedAt || null, query: q });
          }
        } catch (e) { err = e; }
        await cfSleep(400);
      }
      if (!ok) throw err || new Error("no response");
      return items;
    },
  },
  {
    id: "lemmy", label: "Lemmy forums", status: () => ({ enabled: true, mode: "public API (lemmy.world)" }),
    async search() {
      const items = []; let ok = 0, err = null;
      for (const [q, type_] of [["michigan shirt", "Posts"], ["michigan hoodie", "Posts"], ["michigan shirt", "Comments"], ["wolverines merch", "Posts"]]) {
        try {
          const j = await cfGet(`https://lemmy.world/api/v3/search?${new URLSearchParams({ q, type_, sort: "New", limit: "40", listing_type: "All" })}`); ok++;
          for (const r of j?.posts || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, title: r.post?.name, text: r.post?.body || "", url: r.post?.ap_id, postedAt: r.post?.published, query: q });
          for (const r of j?.comments || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, text: r.comment?.content || "", url: r.comment?.ap_id, postedAt: r.comment?.published, query: q });
        } catch (e) { err = e; }
        await cfSleep(500);
      }
      if (!ok) throw err || new Error("no response");
      return items;
    },
  },
  { id: "x", label: "X", status: () => ({ enabled: false, reason: "Needs a secret API key, so it can't run on the static site (use the Radar server version)." }), async search() { return []; } },
  { id: "web", label: "Web search (Brave/Google)", status: () => ({ enabled: false, reason: "Needs a secret API key, so it can't run on the static site (use the Radar server version)." }), async search() { return []; } },
  { id: "facebook", label: "Facebook (direct)", status: () => ({ enabled: false, reason: "No public search API; private groups are never accessed." }), async search() { return []; } },
];

function cfFinish(db, run, fields) { Object.assign(run, fields, { finished_at: new Date().toISOString() }); cfSave(db); }

async function cfExecute(runId) {
  const db = cfLoad(); const run = db.runs.find((r) => r.id === runId);
  const ok = [], failed = [], raw = [];
  await Promise.all(CF_SOURCES.map(async (s) => {
    const st = s.status();
    if (!st.enabled) { failed.push({ source: s.label, skipped: true, error: st.reason }); return; }
    try { const it = await s.search(); ok.push({ source: s.label, mode: st.mode, results: it.length }); raw.push(...it); }
    catch (e) { failed.push({ source: s.label, error: String(e.message || e).slice(0, 200) }); }
  }));
  const db2 = cfLoad(); const run2 = db2.runs.find((r) => r.id === runId) || run;
  if (!ok.length) return cfFinish(db2, run2, { status: "unavailable", sources_ok: ok, sources_failed: failed, message: CF_UNAVAILABLE });

  const inRun = new Map();
  for (const it of raw) if (it.url && !inRun.has(urlKey(it))) inRun.set(urlKey(it), it);
  let newLeads = 0, dup = 0, low = 0, exc = 0;
  const byFp = new Map(db2.leads.map((l) => [l.fingerprint, l])), byUk = new Map(db2.leads.map((l) => [l.url_key, l]));
  for (const it of inRun.values()) {
    const t = Date.parse(it.postedAt || "");
    if (Number.isFinite(t) && Date.now() - t > CF_MAX_AGE_DAYS * 864e5) { exc++; continue; }
    const c = classify(it, "michigan");
    if (c.intent === "EXCLUDED") { exc++; continue; }
    if (c.intent === "LOW") { low++; continue; }
    const fp = await cfHash(fingerprintBasis(it)), uk = urlKey(it);
    const ex = byFp.get(fp) || byUk.get(uk);
    if (ex) { if (ex.last_run !== runId) { ex.seen_count++; ex.last_run = runId; ex.last_seen_at = new Date().toISOString(); } dup++; continue; }
    const id = cfId("lead");
    const match = matchProduct("michigan", c.wants, CF_CATALOGUE);
    const response = suggestResponse({ intent: c.intent, wants: c.wants, match, platform: it.platform, leadId: id });
    let ex2 = [it.title, it.text].filter(Boolean).join(" — ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    ex2 = cfRedact(ex2.length > 600 ? ex2.slice(0, 597) + "…" : ex2);
    const now = new Date().toISOString();
    const lead = { id, fingerprint: fp, url_key: uk, platform: it.platform, author: it.author ? cfRedact(it.author) : null, author_url: it.authorUrl || null,
      title: it.title || null, excerpt: ex2, url: it.url, posted_at: it.postedAt || null, discovered_at: now, first_run_id: runId, last_run: runId,
      last_seen_at: now, seen_count: 1, query: it.query, team: "Michigan Wolverines", intent: c.intent, score: c.score, reasons: c.reasons, wants: c.wants,
      apparel_type: c.apparelType, product: match, response, contact: { channel: "Reply in the original public thread", url: it.url }, status: "NEW", notes: "", updated_at: now };
    db2.leads.push(lead); byFp.set(fp, lead); byUk.set(uk, lead); newLeads++;
  }
  cfFinish(db2, run2, { status: failed.some((f) => !f.skipped) ? "partial" : "success", sources_ok: ok, sources_failed: failed, candidates: inRun.size,
    new_leads: newLeads, duplicates: dup, low_filtered: low, excluded: exc, message: newLeads ? null : "Search completed. No new HOT/WARM opportunities this time." });
}

const CF_RANK = { NEW: 0, REVIEWED: 1, CONTACTED: 2, RESPONDED: 3, CLICKED: 4, CONVERTED: 5, DISMISSED: -1 };
function cfSummary(db) {
  const s = { hot: 0, warm: 0, total: 0, contacted: 0, responses: 0, clicks: 0, conversions: 0, dismissed: 0 };
  for (const l of db.leads) { s.total++; if (l.intent === "HOT") s.hot++; if (l.intent === "WARM") s.warm++; const k = CF_RANK[l.status];
    if (k >= 2) s.contacted++; if (k >= 3) s.responses++; if (k >= 4) s.clicks++; if (k >= 5) s.conversions++; if (k === -1) s.dismissed++; }
  return s;
}
function cfBreak(db, keyFn) {
  const m = new Map();
  for (const l of db.leads) { const k = keyFn(l); const r = m.get(k) || { key: k, leads: 0, hot: 0, contacted: 0, responses: 0, clicks: 0, conversions: 0 }; const rk = CF_RANK[l.status];
    r.leads++; if (l.intent === "HOT") r.hot++; if (rk >= 2) r.contacted++; if (rk >= 3) r.responses++; if (rk >= 4) r.clicks++; if (rk >= 5) r.conversions++; m.set(k, r); }
  return [...m.values()].sort((a, b) => b.conversions - a.conversions || b.clicks - a.clicks || b.responses - a.responses || b.hot - a.hot || b.leads - a.leads).slice(0, 12);
}

// Same routes as the server API.
async function localApi(path, opts = {}) {
  const db = cfLoad();
  const method = opts.method || "GET";
  const sorted = [...db.runs].sort((a, b) => b.started_at.localeCompare(a.started_at));
  // a run left "running" by a closed tab is stale
  for (const r of db.runs) if (r.status === "running" && Date.now() - Date.parse(r.started_at) > 5 * 60e3) Object.assign(r, { status: "error", message: "Interrupted (tab closed). No leads were added by this run." });
  if (path === "/state") {
    return { summary: cfSummary(db), running: sorted.find((r) => r.status === "running") || null, lastRun: sorted.find((r) => r.status !== "running") || null,
      lastSuccessfulRun: sorted.find((r) => r.status === "success" || r.status === "partial") || null,
      sources: CF_SOURCES.map((s) => ({ id: s.id, label: s.label, ...s.status() })), recentRuns: sorted.slice(0, 8), unavailableMessage: CF_UNAVAILABLE, statuses: CF_STATUSES };
  }
  if (path === "/search" && method === "POST") {
    const active = sorted.find((r) => r.status === "running");
    if (active) return { run: active, alreadyRunning: true };
    const run = { id: cfId("run"), started_at: new Date().toISOString(), finished_at: null, status: "running", team: "michigan", sources_ok: [], sources_failed: [],
      candidates: 0, new_leads: 0, duplicates: 0, low_filtered: 0, excluded: 0, message: null };
    db.runs.push(run); cfSave(db);
    cfExecute(run.id).catch((e) => { const d = cfLoad(); const r = d.runs.find((x) => x.id === run.id); cfFinish(d, r, { status: "error", message: `${CF_UNAVAILABLE} (${e.message})` }); });
    return { run, alreadyRunning: false };
  }
  let m;
  if ((m = path.match(/^\/runs\/(.+)$/))) {
    const run = db.runs.find((r) => r.id === m[1]);
    return { run, leads: run && run.status !== "running" ? db.leads.filter((l) => l.first_run_id === run.id) : [] };
  }
  if (path.startsWith("/leads") && method === "GET") {
    const q = new URLSearchParams(path.split("?")[1] || "");
    let leads = db.leads.slice().sort((a, b) => b.discovered_at.localeCompare(a.discovered_at));
    if (q.get("intent") && q.get("intent") !== "ALL") leads = leads.filter((l) => l.intent === q.get("intent"));
    if (q.get("status")) leads = leads.filter((l) => l.status === q.get("status"));
    return { leads };
  }
  if ((m = path.match(/^\/leads\/(.+)$/)) && method === "PATCH") {
    const body = JSON.parse(opts.body || "{}"); const lead = db.leads.find((l) => l.id === m[1]);
    if (body.status && CF_STATUSES.includes(body.status)) lead.status = body.status;
    if (body.notes !== undefined) lead.notes = String(body.notes).slice(0, 2000);
    lead.updated_at = new Date().toISOString(); cfSave(db);
    return { lead, summary: cfSummary(db) };
  }
  if (path === "/insights") {
    return { byPhrase: cfBreak(db, (l) => l.query || "(unknown)"), byPlatform: cfBreak(db, (l) => l.platform), byTeam: cfBreak(db, (l) => l.team),
      byApparel: cfBreak(db, (l) => l.apparel_type || "fan apparel"),
      byConversation: db.leads.filter((l) => CF_RANK[l.status] >= 3).slice(0, 10).map((l) => ({ key: l.url, platform: l.platform, excerpt: l.excerpt, status: l.status })),
      catalogGaps: Object.entries(db.leads.filter((l) => l.product?.gap).reduce((a, l) => ((a[l.apparel_type] = (a[l.apparel_type] || 0) + 1), a), {})).map(([key, leads]) => ({ key, leads })) };
  }
  throw new Error("Unknown route " + path);
}

function cfExport() {
  const blob = new Blob([localStorage.getItem(CF_STORE_KEY) || '{"runs":[],"leads":[]}'], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `customer-finder-backup-${new Date().toISOString().slice(0, 10)}.json`; a.click();
}
function cfImport(file) {
  file.text().then((t) => { const j = JSON.parse(t); if (!Array.isArray(j.leads) || !Array.isArray(j.runs)) throw new Error("Not a backup file");
    const cur = cfLoad(); const have = new Set(cur.leads.map((l) => l.fingerprint)), runs = new Set(cur.runs.map((r) => r.id));
    cur.leads.push(...j.leads.filter((l) => !have.has(l.fingerprint))); cur.runs.push(...j.runs.filter((r) => !runs.has(r.id))); cfSave(cur); location.reload();
  }).catch((e) => alert("Import failed: " + e.message));
}
