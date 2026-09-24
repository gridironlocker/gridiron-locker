// 4. LEAD STORAGE — real persistent storage (SQLite file on RADAR_DATA_DIR).
// Uses Node's built-in node:sqlite (Node >= 22.5), so no native build step.
// Point RADAR_DATA_DIR at a persistent volume in production so leads survive
// rebuilds and redeploys.
import { DatabaseSync } from "node:sqlite";
import fs from "fs";
import path from "path";

export const STATUSES = ["NEW", "REVIEWED", "CONTACTED", "RESPONDED", "CLICKED", "CONVERTED", "DISMISSED"];

let db = null;

export function openStore(file) {
  if (db && !file) return db;
  const target = file || process.env.CF_DB_FILE ||
    path.join(path.resolve(process.env.RADAR_DATA_DIR || "./data"), "customer-finder.db");
  if (target !== ":memory:") fs.mkdirSync(path.dirname(target), { recursive: true });
  const d = new DatabaseSync(target);
  d.exec(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY,
      started_at TEXT NOT NULL,
      finished_at TEXT,
      status TEXT NOT NULL,              -- running | success | partial | unavailable | error
      team TEXT NOT NULL,
      sources_ok TEXT DEFAULT '[]',
      sources_failed TEXT DEFAULT '[]',
      candidates INTEGER DEFAULT 0,
      new_leads INTEGER DEFAULT 0,
      duplicates INTEGER DEFAULT 0,
      low_filtered INTEGER DEFAULT 0,
      excluded INTEGER DEFAULT 0,
      message TEXT
    );
    CREATE TABLE IF NOT EXISTS leads (
      id TEXT PRIMARY KEY,
      fingerprint TEXT NOT NULL UNIQUE,
      url_key TEXT NOT NULL,
      platform TEXT NOT NULL,
      author TEXT,
      author_url TEXT,
      title TEXT,
      excerpt TEXT NOT NULL,
      url TEXT NOT NULL,
      posted_at TEXT,
      discovered_at TEXT NOT NULL,
      first_run_id TEXT NOT NULL,
      last_seen_at TEXT NOT NULL,
      seen_count INTEGER NOT NULL DEFAULT 1,
      query TEXT,
      team TEXT NOT NULL,
      intent TEXT NOT NULL,
      score INTEGER NOT NULL,
      reasons TEXT,
      wants TEXT,
      apparel_type TEXT,
      product TEXT,
      response TEXT,
      contact TEXT,
      status TEXT NOT NULL DEFAULT 'NEW',
      notes TEXT,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS leads_url_key ON leads(url_key);
    CREATE INDEX IF NOT EXISTS leads_run ON leads(first_run_id);
    CREATE TABLE IF NOT EXISTS sightings (
      lead_id TEXT NOT NULL,
      run_id TEXT NOT NULL,
      seen_at TEXT NOT NULL,
      PRIMARY KEY (lead_id, run_id)
    );
    CREATE TABLE IF NOT EXISTS status_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      lead_id TEXT NOT NULL,
      from_status TEXT,
      to_status TEXT NOT NULL,
      at TEXT NOT NULL,
      by_user TEXT
    );
  `);
  if (!file) db = d;
  return d;
}

const J = (v) => JSON.stringify(v ?? null);
const P = (s, dflt = null) => { try { return s == null ? dflt : JSON.parse(s); } catch { return dflt; } };

export function createRun(d, { id, team }) {
  d.prepare(`INSERT INTO runs (id, started_at, status, team) VALUES (?, ?, 'running', ?)`)
    .run(id, new Date().toISOString(), team);
}

export function finishRun(d, id, r) {
  d.prepare(`UPDATE runs SET finished_at=?, status=?, sources_ok=?, sources_failed=?, candidates=?,
      new_leads=?, duplicates=?, low_filtered=?, excluded=?, message=? WHERE id=?`)
    .run(new Date().toISOString(), r.status, J(r.sourcesOk), J(r.sourcesFailed), r.candidates,
      r.newLeads, r.duplicates, r.lowFiltered, r.excluded, r.message || null, id);
}

export function getRun(d, id) { return rowToRun(d.prepare(`SELECT * FROM runs WHERE id=?`).get(id)); }
export function runningRun(d) { return rowToRun(d.prepare(`SELECT * FROM runs WHERE status='running' ORDER BY started_at DESC LIMIT 1`).get()); }
export function lastRun(d) { return rowToRun(d.prepare(`SELECT * FROM runs WHERE status!='running' ORDER BY started_at DESC LIMIT 1`).get()); }
export function lastSuccessfulRun(d) {
  return rowToRun(d.prepare(`SELECT * FROM runs WHERE status IN ('success','partial') ORDER BY started_at DESC LIMIT 1`).get());
}
export function recentRuns(d, n = 10) { return d.prepare(`SELECT * FROM runs ORDER BY started_at DESC LIMIT ?`).all(n).map(rowToRun); }
export function markStaleRuns(d) {
  // A server restart mid-search must not leave a phantom "running" lock.
  d.prepare(`UPDATE runs SET status='error', finished_at=?, message='Interrupted (server restarted). No leads were added by this run.' WHERE status='running'`)
    .run(new Date().toISOString());
}

function rowToRun(r) {
  if (!r) return null;
  return { ...r, sources_ok: P(r.sources_ok, []), sources_failed: P(r.sources_failed, []) };
}

export function findExisting(d, fingerprint, urlKey) {
  return d.prepare(`SELECT id FROM leads WHERE fingerprint=? OR url_key=? LIMIT 1`).get(fingerprint, urlKey) || null;
}

export function markSeen(d, leadId, runId) {
  const now = new Date().toISOString();
  const ins = d.prepare(`INSERT OR IGNORE INTO sightings (lead_id, run_id, seen_at) VALUES (?, ?, ?)`).run(leadId, runId, now);
  if (ins.changes) d.prepare(`UPDATE leads SET last_seen_at=?, seen_count=seen_count+1 WHERE id=?`).run(now, leadId);
}

export function insertLead(d, l) {
  const now = new Date().toISOString();
  d.prepare(`INSERT INTO leads (id, fingerprint, url_key, platform, author, author_url, title, excerpt, url, posted_at,
      discovered_at, first_run_id, last_seen_at, query, team, intent, score, reasons, wants, apparel_type, product,
      response, contact, status, updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'NEW',?)`)
    .run(l.id, l.fingerprint, l.urlKey, l.platform, l.author || null, l.authorUrl || null, l.title || null, l.excerpt,
      l.url, l.postedAt || null, now, l.runId, now, l.query || null, l.team, l.intent, l.score, J(l.reasons),
      J(l.wants), l.apparelType || null, J(l.product), J(l.response), J(l.contact), now);
  d.prepare(`INSERT OR IGNORE INTO sightings (lead_id, run_id, seen_at) VALUES (?, ?, ?)`).run(l.id, l.runId, now);
}

export function listLeads(d, { intent, runId, status, limit = 300 } = {}) {
  const where = [], args = [];
  if (intent && intent !== "ALL") { where.push("intent=?"); args.push(intent); }
  if (runId) { where.push("first_run_id=?"); args.push(runId); }
  if (status) { where.push("status=?"); args.push(status); }
  const sql = `SELECT * FROM leads ${where.length ? "WHERE " + where.join(" AND ") : ""}
    ORDER BY discovered_at DESC, score DESC LIMIT ?`;
  return d.prepare(sql).all(...args, limit).map(rowToLead);
}

export function getLead(d, id) { return rowToLead(d.prepare(`SELECT * FROM leads WHERE id=?`).get(id)); }

export function updateLeadStatus(d, id, status, user) {
  const cur = d.prepare(`SELECT status FROM leads WHERE id=?`).get(id);
  if (!cur) return null;
  const now = new Date().toISOString();
  d.prepare(`UPDATE leads SET status=?, updated_at=? WHERE id=?`).run(status, now, id);
  d.prepare(`INSERT INTO status_events (lead_id, from_status, to_status, at, by_user) VALUES (?,?,?,?,?)`)
    .run(id, cur.status, status, now, user || null);
  return getLead(d, id);
}

export function updateLeadNotes(d, id, notes) {
  d.prepare(`UPDATE leads SET notes=?, updated_at=? WHERE id=?`).run(String(notes).slice(0, 2000), new Date().toISOString(), id);
  return getLead(d, id);
}

function rowToLead(r) {
  if (!r) return null;
  return { ...r, reasons: P(r.reasons, []), wants: P(r.wants, {}), product: P(r.product, null), response: P(r.response, null), contact: P(r.contact, null) };
}
