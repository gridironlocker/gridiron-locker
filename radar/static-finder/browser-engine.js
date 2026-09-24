// In-browser Customer Finder engine for the static (GitHub Pages) build.
// Concatenated after teams.js, classifier.js, dedupe-core.js, match.js, responder.js.
// Mirrors the server API (state / search / runs / leads / insights) over localStorage,
// so the same dashboard UI works unchanged.
//
// Discovery in this build (2026-09 revision, still $0 / no API keys):
//   * Lemmy forums     — keyless public API, still answers (LIVE)
//   * Bluesky Jetstream— public WebSocket firehose, filtered client-side (LIVE stream)
//   * Assisted search  — 10 recent-post searches opened in YOUR logged-in browser,
//                        a "send to Finder" bookmarklet and a paste box (manual, LIVE)
//   * X API / web search — need secret keys: NOT CONFIGURED here (server build only)
//   * Facebook (direct)  — no public search API: not available, private groups never touched
// REMOVED on purpose: Reddit unauthenticated JSON and Bluesky searchPosts — both now
// answer 403 to browser requests, so they are not attempted and never faked.
//
// pipeline = classify → dedupe → match product → draft reply → store   (cfProcess)
// ingestion = create/extend a run with honest counts                   (cfIngest)
//
// Limits of the static build (by design; no server exists):
//   * leads are stored in THIS browser (use Export/Import to move or back them up)
//   * nothing is sent automatically; replies are drafts you copy by hand

const CF_STORE_KEY = "gl_customer_finder_v1";
const CF_ROT_KEY = "gl_cf_query_rotation";
const CF_ENGINE_VERSION = "2.1";
const CF_STATUSES = ["NEW", "REVIEWED", "CONTACTED", "RESPONDED", "CLICKED", "CONVERTED", "DISMISSED"];
const CF_UNAVAILABLE = "Live search unavailable. No new leads were added.";
const CF_MAX_AGE_DAYS = 45;
const CF_MAX_IMPORT_ITEMS = 60;
const CF_STALE_RUN_MS = 5 * 60e3;
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
const cfNow = () => new Date().toISOString();
function cfSignal(ms) { try { return typeof AbortSignal !== "undefined" && AbortSignal.timeout ? AbortSignal.timeout(ms) : undefined; } catch { return undefined; } }

async function cfGet(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" }, signal: cfSignal(15000) });
  if (res.status === 429) throw new Error("rate limited (429). Try again in a few minutes");
  if (res.status === 401 || res.status === 403) throw new Error(`access denied (${res.status})`);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

// ---------------------------------------------------------------- shared helpers
function cfUrl(raw) {
  try { const u = new URL(String(raw || "").trim()); return /^https?:$/.test(u.protocol) ? u.toString() : null; } catch { return null; }
}
function cfHost(raw) { try { return new URL(raw).hostname.replace(/^www\./, "").toLowerCase(); } catch { return ""; } }
function cfPlatformFromUrl(url) {
  const h = cfHost(url);
  if (/reddit\.com$|redd\.it$/.test(h)) return "Reddit";
  if (/(^|\.)x\.com$|twitter\.com$/.test(h)) return "X";
  if (/facebook\.com$|fb\.com$/.test(h)) return "Facebook";
  if (/bsky\.app$/.test(h)) return "Bluesky";
  if (/threads\.net$|threads\.com$/.test(h)) return "Threads";
  if (/lemmy|lemmyverse|sh\.itjust\.works/.test(h)) return "Lemmy";
  if (/quora\.com$/.test(h)) return "Quora";
  if (/google\./.test(h)) return "Web (Google)";
  if (/forum|board|community|discuss|mgoblog|mgoblue|scout\.com|thewolverine/.test(h)) return `Forum (${h})`;
  return h ? `Web (${h})` : "Web";
}
function cfTooOld(postedAt) {
  if (!postedAt) return false; // unknown date is not a reason to throw a real post away
  const t = Date.parse(postedAt);
  return Number.isFinite(t) && Date.now() - t > CF_MAX_AGE_DAYS * 864e5;
}

// ================================================================ PIPELINE
// cfProcess(db, runId, rawItems): classify → dedupe → match product → draft reply → store.
// Honest by construction: an item without a real public link is REJECTED (never stored),
// LOW-intent posts are counted but not stored, and a conversation seen in an earlier run
// is counted as "previously seen" and is never shown as new.
async function cfProcess(db, runId, rawItems) {
  const counts = { candidates: 0, new_leads: 0, duplicates: 0, low_filtered: 0, excluded: 0, rejected: 0 };
  const inRun = new Map();
  for (const raw of rawItems || []) {
    const url = cfUrl(raw && raw.url);
    if (!url) { counts.rejected++; continue; }            // no link → cannot verify the post → dropped
    const it = { ...raw, url, platform: raw.platform || cfPlatformFromUrl(url) };
    const k = urlKey(it);
    if (!inRun.has(k)) inRun.set(k, it);                  // same post from several phrases counts once
  }
  counts.candidates = inRun.size;

  const byFp = new Map(db.leads.map((l) => [l.fingerprint, l]));
  const byUk = new Map(db.leads.map((l) => [l.url_key, l]));

  for (const it of inRun.values()) {
    if (cfTooOld(it.postedAt)) { counts.excluded++; continue; }
    const c = classify(it, "michigan");
    if (c.intent === "EXCLUDED") { counts.excluded++; continue; }
    if (c.intent === "LOW") { counts.low_filtered++; continue; }   // counted, not stored (no need to keep fan chatter)

    const fp = await cfHash(fingerprintBasis(it)), uk = urlKey(it);
    const existing = byFp.get(fp) || byUk.get(uk);
    if (existing) {
      if (existing.last_run !== runId) {
        existing.seen_count = (existing.seen_count || 1) + 1;
        existing.last_run = runId;
        existing.last_seen_at = cfNow();
      }
      counts.duplicates++;
      continue;
    }

    const id = cfId("lead");
    const match = matchProduct("michigan", c.wants, CF_CATALOGUE);
    const response = suggestResponse({ intent: c.intent, wants: c.wants, match, platform: it.platform, leadId: id });
    let ex = [it.title, it.text].filter(Boolean).join(" — ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    ex = cfRedact(ex.length > 600 ? ex.slice(0, 597) + "…" : ex);
    const now = cfNow();
    const lead = {
      id, fingerprint: fp, url_key: uk, platform: it.platform,
      author: it.author ? cfRedact(it.author) : null, author_url: it.authorUrl || null,
      title: it.title || null, excerpt: ex, url: it.url, posted_at: it.postedAt || null,
      discovered_at: now, first_run_id: runId, last_run: runId, last_seen_at: now, seen_count: 1,
      query: it.query || null, source_label: it.source_label || null,
      team: "Michigan Wolverines", intent: c.intent, score: c.score, reasons: c.reasons, wants: c.wants,
      apparel_type: c.apparelType, product: match, response,
      contact: { channel: "Reply in the original public thread", url: it.url, profile: it.authorUrl || null },
      status: "NEW", notes: "", updated_at: now,
    };
    db.leads.push(lead);
    byFp.set(fp, lead); byUk.set(uk, lead);
    counts.new_leads++;
  }
  return counts;
}

const CF_INGEST_MODE = {
  "Lemmy forums": "public API (lemmy.world)",
  "Bluesky live stream": "Jetstream firehose (public WebSocket)",
  "Assisted search": "opened/imported by hand from your own browser",
};

function cfNewRun(label) {
  return {
    id: cfId("run"), started_at: cfNow(), finished_at: null, status: "running", team: "michigan",
    trigger: label || "Manual", live: false, batches: [],
    sources_ok: [], sources_failed: [],
    candidates: 0, new_leads: 0, duplicates: 0, low_filtered: 0, excluded: 0, rejected: 0, message: null,
  };
}

// cfIngest(items, label, runId?): create a run (no runId) or extend the one given,
// then run the pipeline over `items` and add up the counts. Nothing is ever faked:
// every number here comes from cfProcess over real, linkable items.
async function cfIngest(items, label, runId) {
  const arr = typeof items === "function" ? items() : (items || []);
  const db = cfLoad();
  let run = runId ? db.runs.find((r) => r.id === runId) : null;
  if (!run) { run = cfNewRun(label); db.runs.push(run); }

  const counts = await cfProcess(db, run.id, arr);
  const at = cfNow();
  run.batches = [...(run.batches || []), { label: label || "Manual", at, ...counts }].slice(-50);
  for (const k of ["candidates", "new_leads", "duplicates", "low_filtered", "excluded", "rejected"]) run[k] = (run[k] || 0) + counts[k];
  run.finished_at = at;
  run.last_batch_at = at;
  const src = label || "Manual";
  const okEntry = run.sources_ok.find((s) => s.source === src);
  if (okEntry) okEntry.results = (okEntry.results || 0) + counts.candidates;
  else run.sources_ok.push({ source: src, mode: CF_INGEST_MODE[src] || "manual ingest", results: counts.candidates });
  if (!run.live) run.status = run.status === "error" ? "error" : "success";
  cfSave(db);

  const result = { run, counts };
  try { if (typeof cfAfterIngest === "function") cfAfterIngest(result); } catch { /* UI hook must never break ingestion */ }
  return result;
}

function cfRunClose(runId, fields = {}) {
  const db = cfLoad();
  const run = db.runs.find((r) => r.id === runId);
  if (!run) return null;
  Object.assign(run, fields, { live: false, finished_at: cfNow() });
  cfSave(db);
  try { if (typeof cfAfterIngest === "function") cfAfterIngest({ run, counts: null }); } catch { /* ignore */ }
  return run;
}

function cfFinish(db, run, fields) { Object.assign(run, fields, { finished_at: cfNow() }); cfSave(db); }

// ================================================================ LIVE SOURCES
// 1. Lemmy — the only automatic connector still answering without keys.
const CF_LEMMY_QUERIES = [["michigan shirt", "Posts"], ["michigan hoodie", "Posts"], ["michigan shirt", "Comments"], ["wolverines merch", "Posts"]];
async function cfLemmySearch() {
  const items = []; let ok = 0, err = null;
  for (const [q, type_] of CF_LEMMY_QUERIES) {
    try {
      const j = await cfGet(`https://lemmy.world/api/v3/search?${new URLSearchParams({ q, type_, sort: "New", limit: "40", listing_type: "All" })}`);
      ok++;
      for (const r of j?.posts || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, title: r.post?.name, text: r.post?.body || "", url: r.post?.ap_id, postedAt: r.post?.published, query: q });
      for (const r of j?.comments || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, text: r.comment?.content || "", url: r.comment?.ap_id, postedAt: r.comment?.published, query: q });
    } catch (e) { err = e; }
    await cfSleep(500);
  }
  if (!ok) throw err || new Error("no response");
  return items;
}

// 2. Bluesky — public Jetstream firehose over WebSocket (no login, no API key, no search API).
//    Jetstream v2 first (cursor replay), then the legacy v1 hosts from the brief as fallbacks.
const CF_JS_HOSTS = [
  { host: "jetstream.us-east.bsky.network", path: "/xrpc/network.bsky.jetstream.subscribeEvents", v: 2 },
  { host: "jetstream.us-west.bsky.network", path: "/xrpc/network.bsky.jetstream.subscribeEvents", v: 2 },
  { host: "jetstream2.us-east.bsky.network", path: "/subscribe", v: 1 },
  { host: "jetstream1.us-west.bsky.network", path: "/subscribe", v: 1 },
];
// Cheap prefilter: a post must look like it is about the team AND an apparel item before it
// is worth sending through the real classifier (the firehose is thousands of posts/second).
const CF_TEAM_WORD = /(michigan|wolverine|go blue|umich|ann arbor|maize)/i;
const CF_APPAREL_WORD = /\b(t-?shirts?|tees?|shirts?|hoodies?|hoody|sweatshirts?|sweaters?|crew ?necks?|pullovers?|jerseys?|merch|merchandise|apparel|gear|swag|clothes|clothing|outfit)\b/i;

const cfStream = {
  state: "idle",           // idle | connecting | LIVE | TEMPORARILY UNAVAILABLE | FAILED | stopped
  host: null, hostIndex: 0, error: null, socket: null,
  postsChecked: 0, matched: 0, batches: 0, lastMessageAt: null, lastIngestAt: null, lastCounts: null,
  runId: null, replayMinutes: 0, replayUnavailable: false, startedAt: null,
  buffer: [], batchMs: 1500, attempts: 0, cycles: 0, everOpen: false, stopping: false, watchdog: null, timer: null, flushTimer: null,
};

function cfStreamStatus() {
  const s = cfStream.state;
  if (s === "FAILED") return { enabled: false, reason: `FAILED — ${cfStream.error || "no Jetstream host would connect"}. Press Start radar to retry.` };
  if (s === "TEMPORARILY UNAVAILABLE") return { enabled: true, mode: `TEMPORARILY UNAVAILABLE — reconnecting automatically (${cfStream.error || "stream dropped"})` };
  if (s === "connecting") return { enabled: true, mode: `connecting to ${cfStream.host || "Jetstream"}…` };
  if (s === "LIVE") return { enabled: true, mode: `LIVE · ${cfStream.postsChecked} posts checked · ${cfStream.lastCounts ? cfStream.lastCounts.new_leads : 0} new in the last batch` };
  return { enabled: true, mode: `Jetstream firehose ready — press Start radar to go LIVE (${cfStream.postsChecked} posts checked so far)` };
}
function cfLiveStatus() {
  return {
    state: cfStream.state, host: cfStream.host, error: cfStream.error, postsChecked: cfStream.postsChecked,
    matched: cfStream.matched, batches: cfStream.batches, lastMessageAt: cfStream.lastMessageAt,
    lastIngestAt: cfStream.lastIngestAt, lastCounts: cfStream.lastCounts, runId: cfStream.runId,
    replayMinutes: cfStream.replayMinutes, replayUnavailable: cfStream.replayUnavailable, batchMs: cfStream.batchMs,
  };
}
function cfLiveSetBatchMs(ms) { cfStream.batchMs = Math.max(20, Number(ms) || 1500); return cfStream.batchMs; }

// Both Jetstream shapes: v2 wraps the event in a `payload` envelope, v1 is flat with `commit`.
function cfJetstreamPost(msg) {
  if (!msg || typeof msg !== "object") return null;
  const p = msg.payload && typeof msg.payload === "object" ? msg.payload : msg;
  const isV2 = !!msg.payload;
  const kind = isV2 ? String(p.$type || "").split("#").pop() : String(p.kind || "");
  if (kind !== "commit") return null;
  const rec = isV2 ? p.record : (p.commit && p.commit.record);
  const op = isV2 ? p.operation : (p.commit && p.commit.operation);
  if (op !== "create") return null;
  if (!rec || typeof rec !== "object") return null;
  if (rec.$type && rec.$type !== "app.bsky.feed.post") return null;
  const text = typeof rec.text === "string" ? rec.text : "";
  const did = p.did, rkey = isV2 ? p.rkey : (p.commit && p.commit.rkey);   // v1 nests rkey under commit
  if (!text || !did || !rkey) return null;
  const createdAt = rec.createdAt || (p.time ? new Date(Date.parse(p.time)).toISOString() : null);
  return {
    did, rkey, text, createdAt,
    url: `https://bsky.app/profile/${did}/post/${rkey}`,
    seq: p.seq || null,
    time: p.time || createdAt,
    timeUs: isV2 ? (p.time ? Date.parse(p.time) * 1000 : null) : (p.time_us || null),
    cursor: p.cursor || null,
  };
}

function cfStreamPaint() { try { if (typeof cfLivePaint === "function") cfLivePaint(cfLiveStatus()); } catch { /* ignore */ } }

// Batches: the firehose is folded into cfIngest every batchMs (1.5s by default) so the
// pipeline and localStorage are not touched once per post.
function cfStreamScheduleFlush() {
  clearTimeout(cfStream.flushTimer);
  cfStream.flushTimer = setTimeout(() => {
    cfStreamFlush();
    if (["LIVE", "connecting", "TEMPORARILY UNAVAILABLE"].includes(cfStream.state)) cfStreamScheduleFlush();
  }, cfStream.batchMs);
}

function cfStreamFlush() {
  if (!cfStream.buffer.length) return;
  const items = cfStream.buffer.splice(0, cfStream.buffer.length);
  const label = "Bluesky live stream";
  Promise.resolve(cfIngest(items, label, cfStream.runId)).then((r) => {
    cfStream.batches++;
    cfStream.lastIngestAt = cfNow();
    cfStream.lastCounts = r.counts;
    cfStream.runId = r.run.id;
    if (r.run.live !== true) cfRunReopen(r.run.id);
    cfStreamPaint();
  }).catch((e) => { cfStream.error = String(e && e.message || e); cfStreamPaint(); });
}
function cfRunReopen(runId) {
  const db = cfLoad();
  const run = db.runs.find((r) => r.id === runId);
  if (run && !run.live) { run.live = true; run.status = "running"; run.finished_at = null; cfSave(db); }
}

function cfStreamHostUrl(i, cursorUs) {
  const h = CF_JS_HOSTS[i % CF_JS_HOSTS.length];
  const p = h.v === 2
    ? new URLSearchParams({ collections: "app.bsky.feed.post", kinds: "commit" })
    : new URLSearchParams({ wantedCollections: "app.bsky.feed.post" });
  if (cursorUs) p.set("cursor", String(Math.floor(cursorUs)));
  return `wss://${h.host}${h.path}?${p}`;
}

function cfStreamConnect(cursorUs) {
  const WS = (typeof WebSocket !== "undefined" ? WebSocket : (typeof window !== "undefined" ? window.WebSocket : null));
  if (!WS) { cfStream.state = "FAILED"; cfStream.error = "this browser has no WebSocket support"; cfStreamPaint(); return; }
  const i = cfStream.hostIndex % CF_JS_HOSTS.length;
  const url = cfStreamHostUrl(i, cursorUs);
  cfStream.host = CF_JS_HOSTS[i].host;
  cfStream.state = "connecting"; cfStream.error = null; cfStreamPaint();

  let gotMessage = false;
  let ws;
  try { ws = new WS(url); } catch (e) { cfStreamFail(String(e && e.message || e), cursorUs); return; }
  cfStream.socket = ws;
  ws.onopen = () => {
    cfStream.everOpen = true; cfStream.attempts = 0; cfStream.cycles = 0; cfStream.state = "LIVE";
    cfStream.startedAt = cfStream.startedAt || cfNow();
    cfStreamPaint();
  };
  ws.onmessage = (ev) => {
    gotMessage = true;
    cfStream.lastMessageAt = cfNow();
    let msg; try { msg = JSON.parse(typeof ev.data === "string" ? ev.data : String(ev.data)); } catch { return; }
    const post = cfJetstreamPost(msg);
    if (!post) return;
    cfStream.postsChecked++;
    if (post.cursor) cfStream.cursor = post.cursor;
    if (post.timeUs) cfStream.timeUs = post.timeUs;
    if (!(CF_TEAM_WORD.test(post.text) && CF_APPAREL_WORD.test(post.text))) return;
    cfStream.matched++;
    cfStream.buffer.push({
      platform: "Bluesky", author: cfShortDid(post.did), authorUrl: `https://bsky.app/profile/${post.did}`,
      text: post.text, url: post.url, postedAt: post.createdAt || null,
      query: cfStream.replayMinutes && !cfStream.replayDone ? `Jetstream replay (last ${cfStream.replayMinutes} min)` : "Jetstream live stream",
    });
  };
  ws.onerror = () => { /* close always follows; handled there so we reconnect once */ };
  ws.onclose = () => {
    if (cfStream.stopping) return;
    if (cfStream.state === "LIVE" || cfStream.state === "connecting") {
      // A replay cursor can be refused by a host that doesn't hold that much history:
      // fall back to live-only once, and say so instead of pretending we replayed.
      if (!gotMessage && cursorUs) {
        cfStream.replayUnavailable = true;
        cfStreamFail("this host refused the replay cursor", null);
        return;
      }
      cfStreamFail(gotMessage ? "stream dropped" : "connection closed before any data", cursorUs);
    }
  };
}
function cfShortDid(did) { const s = String(did || ""); return s.length > 22 ? s.slice(0, 10) + "…" + s.slice(-6) : s; }

function cfStreamFail(reason, cursorUs) {
  cfStream.error = reason;
  cfStream.attempts++;
  if (cfStream.attempts >= CF_JS_HOSTS.length) { cfStream.attempts = 0; cfStream.cycles++; }
  cfStream.hostIndex = (cfStream.hostIndex + 1) % CF_JS_HOSTS.length;
  // One clean sweep of every host with nothing received = FAILED (stop; the operator can retry).
  if (!cfStream.everOpen && cfStream.cycles >= 1) {
    cfStream.state = "FAILED";
    if (cfStream.watchdog) { clearInterval(cfStream.watchdog); cfStream.watchdog = null; }
    clearTimeout(cfStream.flushTimer);
    try { if (cfStream.socket) cfStream.socket.close(); } catch { /* ignore */ }
    cfStream.socket = null;
    if (cfStream.runId) cfRunClose(cfStream.runId, { status: "error", message: `Bluesky live stream failed: ${reason}. No leads were added by the stream.` });
    cfStreamPaint();
    return;
  }
  cfStream.state = "TEMPORARILY UNAVAILABLE";
  const wait = Math.min(15000, 500 * Math.pow(2, cfStream.cycles));   // fail over fast, then back off
  cfStreamPaint();
  cfStream.timer = setTimeout(() => { if (!cfStream.stopping) cfStreamConnect(cursorUs ? cfStream.timeUs || null : null); }, wait);
}

function cfLiveStart(opts = {}) {
  if (cfStream.state === "LIVE" || cfStream.state === "connecting") return cfLiveStatus();
  cfStream.stopping = false;
  cfStream.replayMinutes = Math.max(0, Number(opts.replayMinutes) || 0);
  cfStream.replayDone = false;
  cfStream.everOpen = false; cfStream.attempts = 0; cfStream.cycles = 0;
  const cursorUs = cfStream.replayMinutes ? (Date.now() - cfStream.replayMinutes * 60000) * 1000 : null;
  Promise.resolve(cfIngest([], "Bluesky live stream")).then((r) => {
    cfStream.runId = r.run.id;
    cfRunReopen(r.run.id);
    cfStream.state = "connecting";
    cfStreamConnect(cursorUs);
    cfStreamScheduleFlush();
    cfStreamPaint();
  });
  if (cfStream.watchdog) clearInterval(cfStream.watchdog);
  cfStream.watchdog = setInterval(() => {
    if (cfStream.state !== "LIVE") return;
    const t = Date.parse(cfStream.lastMessageAt || cfStream.startedAt || cfNow());
    if (Date.now() - t > 60000 && cfStream.socket) { try { cfStream.socket.close(); } catch { /* ignore */ } }
  }, 10000);
  return cfLiveStatus();
}

function cfLiveStop(reason = "stopped by the operator") {
  cfStream.stopping = true;
  if (cfStream.watchdog) { clearInterval(cfStream.watchdog); cfStream.watchdog = null; }
  if (cfStream.timer) { clearTimeout(cfStream.timer); cfStream.timer = null; }
  clearTimeout(cfStream.flushTimer);
  try { if (cfStream.socket) cfStream.socket.close(); } catch { /* ignore */ }
  cfStream.socket = null;
  const opened = cfStream.everOpen;
  cfStream.state = opened ? "stopped" : "idle";
  if (cfStream.runId) {
    cfRunClose(cfStream.runId, {
      status: opened ? "success" : "error",
      message: opened
        ? `Bluesky live stream ${reason}. ${cfStream.postsChecked} posts checked, ${cfStream.matched} team+apparel matches.`
        : `Bluesky live stream never connected (${reason}). No leads were added by the stream.`,
    });
  }
  cfStream.replayDone = true;
  cfStreamFlush();
  cfStreamPaint();
  return cfLiveStatus();
}

// 3. Source status list, exactly what the panel and the dashboard connectors card show.
const CF_SOURCES = [
  {
    id: "lemmy", label: "Lemmy forums",
    status: () => ({ enabled: true, mode: "public API (lemmy.world) · LIVE" }),
    search: cfLemmySearch,
  },
  {
    id: "bluesky-stream", label: "Bluesky live stream",
    status: () => cfStreamStatus(),
    search: null,
  },
  {
    id: "assist", label: "Assisted search",
    status: () => ({ enabled: true, mode: "10 recent-post searches in your own browser + bookmarklet + paste · LIVE (manual)" }),
    search: null,
  },
  {
    id: "x", label: "X API",
    status: () => ({ enabled: false, reason: "NOT CONFIGURED — X's API needs a paid key, so the static build never calls it. Use Assisted search → X Latest in your own logged-in browser." }),
    search: null,
  },
  {
    id: "web", label: "Web search (Brave/Google API)",
    status: () => ({ enabled: false, reason: "NOT CONFIGURED — Brave/Google keys only exist in the Radar server build. Use Assisted search → Google forums." }),
    search: null,
  },
  {
    id: "facebook", label: "Facebook (direct)",
    status: () => ({ enabled: false, reason: "Not available — no public post-search API, and private groups are never accessed. Use Assisted search → Facebook posts." }),
    search: null,
  },
];

function cfExecutableSources() { return CF_SOURCES.filter((s) => typeof s.search === "function"); }

// The dashboard's 🔄 button: runs every automatic connector that still works (Lemmy).
async function cfExecute(runId) {
  const db = cfLoad();
  const run = db.runs.find((r) => r.id === runId);
  const ok = [], failed = [], raw = [];
  for (const s of CF_SOURCES) {
    const st = s.status();
    if (typeof s.search !== "function") {
      if (!st.enabled) failed.push({ source: s.label, skipped: true, error: st.reason });
      continue;
    }
    try {
      const it = await s.search();
      ok.push({ source: s.label, mode: st.mode, results: it.length });
      raw.push(...it);
    } catch (e) { failed.push({ source: s.label, error: String((e && e.message) || e).slice(0, 200) }); }
  }
  const db2 = cfLoad();
  const run2 = db2.runs.find((r) => r.id === runId) || run;
  if (!ok.length) return cfFinish(db2, run2, { status: "unavailable", sources_ok: ok, sources_failed: failed, message: CF_UNAVAILABLE });

  const counts = await cfProcess(db2, runId, raw);
  run2.batches = [...(run2.batches || []), { label: ok.map((s) => s.source).join(", "), at: cfNow(), ...counts }].slice(-50);
  cfFinish(db2, run2, {
    status: failed.some((f) => !f.skipped) ? "partial" : "success",
    sources_ok: ok, sources_failed: failed, ...counts,
    message: counts.new_leads ? null : "Search completed. No new HOT/WARM opportunities this time.",
  });
}

// ================================================================ ASSISTED DISCOVERY
// Intent pool: direct asks, recommendation asks, need statements, style asks.
const CF_INTENT_POOL = {
  direct: ["where can I buy a Michigan shirt", "where to buy a Michigan hoodie", "where can I find Michigan merch", "Michigan shirt where do I get one"],
  recommendations: ["Michigan shirt recommendations", "best Michigan hoodie", "any recommendations for a Michigan sweatshirt", "Michigan tee suggestions"],
  need: ["need a Michigan crewneck", "looking for a Michigan sweatshirt", "ISO vintage Michigan tee", "want a Michigan game day shirt"],
  style: ["unique Michigan shirt", "vintage Michigan tee", "affordable Michigan hoodie", "non generic Michigan shirt"],
};
const CF_ASSIST_GROUPS = ["direct", "recommendations", "need", "style"];

function cfRotation() { try { return Number(JSON.parse(localStorage.getItem(CF_ROT_KEY) || "{}").i) || 0; } catch { return 0; } }
function cfNewQuerySet() { const i = cfRotation() + 1; try { localStorage.setItem(CF_ROT_KEY, JSON.stringify({ i })); } catch { /* ignore */ } return i; }
function cfPoolPhrase(group, slot) {
  const pool = CF_INTENT_POOL[group] || CF_INTENT_POOL.direct;
  return pool[(cfRotation() + slot) % pool.length];
}
function cfGoogleQuery(phrase, when) {
  return `https://www.google.com/search?${new URLSearchParams({ q: `${phrase} forum -site:etsy.com -site:amazon.com -site:fanatics.com`, tbs: `qdr:${when}` })}`;
}

// The 10 recent-post searches, opened in the operator's own logged-in browser.
// (The brief's 9: X, Reddit new sitewide + r/uofm (t=week / t=month), Google forums
//  (qdr:d + qdr:w), Facebook posts, Threads, Bluesky — Reddit spans four of them here.)
function cfAssistSearches() {
  const p = (g, s) => cfPoolPhrase(g, s);
  return [
    { id: "x", label: "X · Latest", hint: p("direct", 0), url: `https://x.com/search?q=${encodeURIComponent(`${p("direct", 0)} -filter:links`)}&f=live` },
    { id: "reddit-new", label: "Reddit · New (sitewide)", hint: "newest posts, no query", url: "https://www.reddit.com/new/" },
    { id: "reddit-uofm-new", label: "Reddit · r/uofm New", hint: "newest posts, no query", url: "https://www.reddit.com/r/uofm/new/" },
    { id: "reddit-week", label: "Reddit · search past week", hint: p("recommendations", 1), url: `https://www.reddit.com/search/?${new URLSearchParams({ q: p("recommendations", 1), sort: "new", t: "week" })}` },
    { id: "reddit-uofm-month", label: "Reddit · r/uofm past month", hint: p("need", 2), url: `https://www.reddit.com/r/uofm/search/?${new URLSearchParams({ q: p("need", 2), restrict_sr: "on", sort: "new", t: "month" })}` },
    { id: "google-day", label: "Google · forums past day", hint: p("style", 3), url: cfGoogleQuery(p("style", 3), "d") },
    { id: "google-week", label: "Google · forums past week", hint: p("need", 0), url: cfGoogleQuery(p("need", 0), "w") },
    { id: "facebook", label: "Facebook · posts", hint: p("direct", 1), url: `https://www.facebook.com/search/posts/?q=${encodeURIComponent(p("direct", 1))}` },
    { id: "threads", label: "Threads · search", hint: p("recommendations", 2), url: `https://www.threads.net/search?q=${encodeURIComponent(p("recommendations", 2))}&serp_type=default` },
    { id: "bluesky", label: "Bluesky · search", hint: p("style", 1), url: `https://bsky.app/search?q=${encodeURIComponent(p("style", 1))}` },
  ];
}

// Paste box: one post per blank-line block, every block must include its link.
function cfParsePaste(raw) {
  const blocks = String(raw || "").split(/\n\s*\n+/).map((b) => b.trim()).filter(Boolean);
  const items = []; let rejected = 0;
  for (const block of blocks) {
    const m = block.match(/https?:\/\/[^\s"'<>)\]]+/);
    if (!m) {
      // no link → cannot verify → handed to cfIngest anyway, which counts it as rejected
      rejected++;
      items.push({ platform: "Pasted (no link)", author: null, title: null, text: block.replace(/\s+/g, " ").trim(), url: null, postedAt: null, query: "Pasted by hand" });
      continue;
    }
    const url = m[0].replace(/[.,;:]+$/, "");
    const body = block.replace(/\s+/g, " ").trim();
    const lines = block.split("\n").map((s) => s.trim()).filter(Boolean);
    const author = (body.match(/(?:^|\s)(u\/[A-Za-z0-9_-]{3,20}|@[A-Za-z0-9_.-]{2,40})/) || [])[1] || null;
    const date = (body.match(/\b(\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)\b/) || [])[1] || null;
    items.push({
      platform: cfPlatformFromUrl(url), author, authorUrl: null,
      title: lines.length > 1 ? lines[0] : null, text: body, url,
      postedAt: date, query: "Pasted by hand",
    });
  }
  return { items, rejected, blocks: blocks.length };
}

// Bookmarklet: reads whatever is on screen in the page you are looking at.
// Runs in THAT page (not here), so it is written as one self-contained function.
function cfExtractInPage(doc, loc) {
  function txt(el) { return el ? String(el.innerText || el.textContent || "").replace(/\s+/g, " ").trim() : ""; }
  function abs(href) { try { return new URL(href, loc.href).toString(); } catch (e) { return ""; } }
  function host() { try { return new URL(loc.href).hostname.replace(/^www\./, "").toLowerCase(); } catch (e) { return ""; } }
  function plat() {
    var h = host();
    if (/(^|\.)x\.com$|(^|\.)twitter\.com$/.test(h)) return "X";
    if (/(^|\.)reddit\.com$|redd\.it$/.test(h)) return "Reddit";
    if (/google\./.test(h)) return "Web (Google)";
    if (/(^|\.)facebook\.com$/.test(h)) return "Facebook";
    if (/bsky\.app$/.test(h)) return "Bluesky";
    if (/threads\.net$/.test(h)) return "Threads";
    return h ? "Web (" + h + ")" : "Web";
  }
  function dateOf(el) {
    if (!el || !el.querySelector) return null;
    var t = el.querySelector("time");
    if (!t) return null;
    return t.getAttribute("datetime") || txt(t) || null;
  }
  var items = [], h = host(), platform = plat();
  function unwrap(u) {
    try {
      var x = new URL(u, loc.href);
      if (/google\./.test(x.hostname) && x.pathname === "/url") return x.searchParams.get("q") || x.searchParams.get("url") || u;
      return x.toString();
    } catch (e) { return ""; }
  }
  function push(o) {
    if (!o || !o.text || !o.url) return;
    items.push({
      platform: platform, author: o.author || null, authorUrl: o.authorUrl || null, title: o.title || null,
      text: o.text, url: unwrap(o.url) || o.url, postedAt: o.postedAt || null, query: "Bookmarklet · " + platform,
    });
  }

  if (platform === "X") {
    var arts = doc.querySelectorAll("article");
    for (var i = 0; i < arts.length; i++) {
      var a = arts[i];
      var body = a.querySelector('[data-testid="tweetText"]');
      if (!body) continue;
      var links = a.querySelectorAll('a[href*="/status/"]'), status = null, j;
      for (j = 0; j < links.length; j++) if (links[j].querySelector("time")) { status = links[j]; break; }
      if (!status) continue;
      var handle = null, anchors = a.querySelectorAll('a[href]');
      for (j = 0; j < anchors.length; j++) {
        var href = anchors[j].getAttribute("href") || "";
        if (/^\/[A-Za-z0-9_]{2,20}$/.test(href)) { handle = href.slice(1); break; }
      }
      push({
        text: txt(body), url: status.getAttribute("href"),
        author: handle ? "@" + handle : null, authorUrl: handle ? "/" + handle : null,
        postedAt: dateOf(status) || dateOf(a),
      });
    }
  } else if (platform === "Reddit") {
    var posts = doc.querySelectorAll("shreddit-post, shreddit-comment");
    for (var k = 0; k < posts.length; k++) {
      var p = posts[k];
      var author = p.getAttribute("author") || p.getAttribute("comment-author") || null;
      var dt = p.getAttribute("created-timestamp") || p.getAttribute("comment-created-timestamp") || null;
      var bodyEl = p.querySelector('[slot="text-body"], [slot="comment"], [id$="-post-rtjson-content"]');
      push({
        title: p.getAttribute("post-title") || null,
        text: txt(bodyEl) || txt(p.querySelector('[slot="title"]')) || txt(p),
        url: p.getAttribute("permalink") || p.getAttribute("content-href") || p.getAttribute("comment-permalink") || "",
        author: author ? "u/" + author : null, authorUrl: author ? "https://www.reddit.com/user/" + author : null, postedAt: dt,
      });
    }
    var old = doc.querySelectorAll(".thing[data-permalink]");
    for (var q = 0; q < old.length; q++) {
      var t = old[q];
      var u = t.getAttribute("data-author") || null;
      var tagline = t.querySelector(".tagline");
      var time = tagline ? tagline.querySelector("time") : null;
      push({
        title: txt(t.querySelector(".title a")) || null,
        text: txt(t.querySelector(".usertext-body")) || txt(t.querySelector(".md")) || txt(t.querySelector(".title")),
        url: t.getAttribute("data-permalink") || "",
        author: u ? "u/" + u : null, authorUrl: u ? "https://www.reddit.com/user/" + u : null,
        postedAt: time ? (time.getAttribute("datetime") || txt(time)) : null,
      });
    }
  } else if (platform === "Web (Google)") {
    var blocks = doc.querySelectorAll("div.MjjYud, div.g, div[data-snc], div.Gx5Zad");
    for (var b = 0; b < blocks.length; b++) {
      var blk = blocks[b], h3 = blk.querySelector("h3");
      var link = (h3 && h3.closest("a")) || blk.querySelector("a[href^='http'], a[href^='/url?']");
      if (!h3 || !link) continue;
      var snip = blk.querySelector(".VwiC3b, .lEBKkf, .aCOpRe, .MUxGbd, span");
      push({ title: txt(h3), text: txt(snip) || txt(blk), url: link.getAttribute("href"), postedAt: dateOf(blk) });
    }
  }

  if (!items.length) {
    var sel = "";
    try { sel = String((doc.getSelection && doc.getSelection()) || "").trim(); } catch (e) { sel = ""; }
    var text = sel || txt(doc.body).slice(0, 1500);
    push({ text: text, url: loc.href, title: doc.title || null, query: "Bookmarklet · selection" });
  }
  return items.slice(0, 60);
}

function cfBookmarkletHref(origin, pathname) {
  const base = String(origin || "").replace(/\/+$/, "") + String(pathname || "/");
  const code = "(function(){try{var X=" + cfExtractInPage.toString() + ";" +
    "var r=X(document,location)||[];r=r.slice(0," + CF_MAX_IMPORT_ITEMS + ");" +
    "if(!r.length){alert('Customer Finder: nothing readable on this page. Select the post text and try again.');return;}" +
    "var u=" + JSON.stringify(base) + "+'#import='+encodeURIComponent(JSON.stringify(r));" +
    "var w=window.open(u,'_blank');if(!w){location.href=u;}" +
    "}catch(e){alert('Customer Finder bookmarklet error: '+e.message);}})()";
  return "javascript:" + code;
}

// The bookmarklet opens the finder with #import=<json>; we ingest it once, then clear the hash.
async function cfIngestHash() {
  const raw = String((typeof location !== "undefined" && location.hash) || "");
  if (raw.indexOf("#import=") !== 0) return null;
  const body = raw.slice(8);
  let parsed = null;
  try { parsed = JSON.parse(body); } catch { try { parsed = JSON.parse(decodeURIComponent(body)); } catch { parsed = null; } }
  try { history.replaceState(null, "", location.pathname + location.search); } catch { try { location.hash = ""; } catch { /* ignore */ } }
  if (!Array.isArray(parsed) || !parsed.length) return null;
  return cfIngest(parsed.slice(0, CF_MAX_IMPORT_ITEMS), "Assisted search");
}

// ================================================================ API (same routes as the server)
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
  const sorted = [...db.runs].sort((a, b) => String(b.started_at).localeCompare(String(a.started_at)));
  // a run left "running" by a closed tab is stale (a live stream run is not: it reconnects)
  for (const r of db.runs) if (r.status === "running" && !r.live && Date.now() - Date.parse(r.started_at) > CF_STALE_RUN_MS) Object.assign(r, { status: "error", message: "Interrupted (tab closed). No leads were added by this run." });
  // A live stream run stays "running" while it collects, but it must never disable the
  // dashboard's own search button or make the page look like a search is in flight.
  const inFlight = (r) => r.status === "running" && !r.live;
  if (path === "/state") {
    return {
      engine_version: CF_ENGINE_VERSION, summary: cfSummary(db), running: sorted.find(inFlight) || null,
      lastRun: sorted.find((r) => r.status !== "running") || null,
      lastSuccessfulRun: sorted.find((r) => r.status === "success" || r.status === "partial") || null,
      sources: CF_SOURCES.map((s) => ({ id: s.id, label: s.label, ...s.status() })),
      stream: cfLiveStatus(),
      recentRuns: sorted.slice(0, 8), unavailableMessage: CF_UNAVAILABLE, statuses: CF_STATUSES,
    };
  }
  if (path === "/search" && method === "POST") {
    const active = sorted.find(inFlight);
    if (active) return { run: active, alreadyRunning: true };
    const run = cfNewRun(cfExecutableSources().map((s) => s.label).join(", "));
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
    lead.updated_at = cfNow(); cfSave(db);
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
