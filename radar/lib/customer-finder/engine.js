// Orchestrator: one button press = one fresh, live search run.
//   discover (live) → classify → dedupe → store → match product → draft reply
// Nothing here reads cached search results. If no source answers, the run is
// recorded as "unavailable" and zero leads are added.
import crypto from "crypto";
import { SOURCES } from "./sources.js";
import { classify } from "./classifier.js";
import { fingerprint, urlKey } from "./dedupe.js";
import { matchProduct } from "./products.js";
import { suggestResponse } from "./responder.js";
import { getTeam } from "./teams.js";
import * as store from "./store.js";

export const UNAVAILABLE_MSG = "Live search unavailable. No new leads were added.";
const MAX_AGE_DAYS = Number(process.env.CF_MAX_AGE_DAYS || 45);

// Privacy: never store e-mail addresses or phone numbers found in post text.
export function redact(s) {
  return String(s || "")
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email removed]")
    .replace(/(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b/g, "[phone removed]");
}

function excerpt(item) {
  const body = redact([item.title, item.text].filter(Boolean).join(" — ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
  return body.length > 600 ? body.slice(0, 597) + "…" : body;
}

function tooOld(postedAt) {
  if (!postedAt) return false;
  const t = Date.parse(postedAt);
  return Number.isFinite(t) && Date.now() - t > MAX_AGE_DAYS * 864e5;
}

export function newId(prefix) { return `${prefix}_${crypto.randomBytes(6).toString("hex")}`; }

export function startRun(db, { teamKey = "michigan", fetchImpl = globalThis.fetch, sources = SOURCES } = {}) {
  const active = store.runningRun(db);
  if (active) return { run: active, alreadyRunning: true, promise: null };
  const id = newId("run");
  store.createRun(db, { id, team: teamKey });
  const promise = executeRun(db, id, { teamKey, fetchImpl, sources }).catch((e) => {
    store.finishRun(db, id, { status: "error", sourcesOk: [], sourcesFailed: [{ source: "engine", error: e.message }], candidates: 0, newLeads: 0, duplicates: 0, lowFiltered: 0, excluded: 0, message: `${UNAVAILABLE_MSG} (${e.message})` });
  });
  return { run: store.getRun(db, id), alreadyRunning: false, promise };
}

export async function executeRun(db, runId, { teamKey, fetchImpl, sources }) {
  const team = getTeam(teamKey);
  const sourcesOk = [], sourcesFailed = [], raw = [];

  // 1. DISCOVERY — every enabled connector, in parallel, live.
  const enabled = sources.map((s) => ({ s, st: s.status() }));
  await Promise.all(enabled.map(async ({ s, st }) => {
    if (!st.enabled) { sourcesFailed.push({ source: s.label, skipped: true, error: st.reason }); return; }
    try {
      const items = await s.search(team, { fetchImpl });
      sourcesOk.push({ source: s.label, mode: st.mode, results: items.length });
      raw.push(...items);
    } catch (e) {
      sourcesFailed.push({ source: s.label, error: String(e.message || e).slice(0, 200) });
    }
  }));

  if (!sourcesOk.length) {
    store.finishRun(db, runId, { status: "unavailable", sourcesOk, sourcesFailed, candidates: 0, newLeads: 0, duplicates: 0, lowFiltered: 0, excluded: 0, message: UNAVAILABLE_MSG });
    return store.getRun(db, runId);
  }

  // in-run dedupe (the same post often comes back for several phrases)
  const seenInRun = new Map();
  for (const it of raw) {
    if (!it.url) continue;
    const k = urlKey(it);
    if (!seenInRun.has(k)) seenInRun.set(k, it);
  }

  let newLeads = 0, duplicates = 0, lowFiltered = 0, excluded = 0;
  for (const it of seenInRun.values()) {
    if (tooOld(it.postedAt)) { excluded++; continue; }
    // 2. CLASSIFY
    const c = classify(it, teamKey);
    if (c.intent === "EXCLUDED") { excluded++; continue; }
    if (c.intent === "LOW") { lowFiltered++; continue; } // LOW is counted, not stored (no need to keep people's fan chatter)

    // 3. DEDUPE against every previous run
    const fp = fingerprint(it), uk = urlKey(it);
    const existing = store.findExisting(db, fp, uk);
    if (existing) { store.markSeen(db, existing.id, runId); duplicates++; continue; }

    // 5. PRODUCT MATCH + 6. RESPONSE
    const id = newId("lead");
    const match = matchProduct(teamKey, c.wants);
    const response = suggestResponse({ intent: c.intent, wants: c.wants, match, platform: it.platform, leadId: id });

    // 4. STORE
    store.insertLead(db, {
      id, fingerprint: fp, urlKey: uk, runId, platform: it.platform, author: it.author ? redact(it.author) : null,
      authorUrl: it.authorUrl || null, title: it.title ? redact(it.title) : null, excerpt: excerpt(it), url: it.url,
      postedAt: it.postedAt || null, query: it.query, team: team.label, intent: c.intent, score: c.score,
      reasons: c.reasons, wants: c.wants, apparelType: c.apparelType, product: match, response,
      // Contact channel = the original public conversation. No e-mail harvesting.
      contact: { channel: "Reply in the original public thread", url: it.url, profile: it.authorUrl || null },
    });
    newLeads++;
  }

  store.finishRun(db, runId, {
    status: sourcesFailed.some((f) => !f.skipped) ? "partial" : "success",
    sourcesOk, sourcesFailed, candidates: seenInRun.size, newLeads, duplicates, lowFiltered, excluded,
    message: newLeads ? null : "Search completed. No new HOT/WARM opportunities this time.",
  });
  return store.getRun(db, runId);
}

export function sourceStatuses(sources = SOURCES) {
  return sources.map((s) => ({ id: s.id, label: s.label, ...s.status() }));
}
