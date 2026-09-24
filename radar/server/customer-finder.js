// Private Customer Intent Finder — mounted at /private/customer-finder/ on the Radar host.
// Server-side auth on every route (page + API), noindex everywhere, no secrets to the browser.
import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { verifySession } from "./auth.js";
import * as store from "../lib/customer-finder/store.js";
import { startRun, sourceStatuses, UNAVAILABLE_MSG } from "../lib/customer-finder/engine.js";
import { summary, insights } from "../lib/customer-finder/analytics.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PAGE = path.resolve(__dirname, "../public/customer-finder.html");
export const BASE = "/private/customer-finder";

export function customerFinderRouter({ db = store.openStore(), fetchImpl = globalThis.fetch } = {}) {
  store.markStaleRuns(db);
  const r = express.Router();

  r.use((req, res, next) => {
    res.set("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet");
    res.set("Cache-Control", "no-store, private");
    res.set("Referrer-Policy", "no-referrer");
    next();
  });

  // Auth gate: every route below requires a valid server-side session.
  r.use((req, res, next) => {
    const payload = verifySession(req.cookies?.radar_session || "");
    if (payload) { req.user = payload; return next(); }
    if (req.path.startsWith("/api/")) return res.status(401).json({ error: "Authentication required." });
    return res.redirect(302, `/radar/login?next=${encodeURIComponent(BASE + "/")}`);
  });

  // CSRF: state-changing calls must carry a custom header (cross-site forms can't set it,
  // and no CORS is enabled), on top of the SameSite=Lax session cookie.
  r.use((req, res, next) => {
    if (["POST", "PATCH", "PUT", "DELETE"].includes(req.method) && req.get("X-CF-Request") !== "1") {
      return res.status(403).json({ error: "Missing request header." });
    }
    next();
  });

  r.get("/", (req, res) => res.type("html").send(fs.readFileSync(PAGE, "utf-8")));

  r.get("/api/state", (req, res) => {
    const last = store.lastRun(db);
    res.json({
      summary: summary(db),
      running: store.runningRun(db),
      lastRun: last,
      lastSuccessfulRun: store.lastSuccessfulRun(db),
      sources: sourceStatuses(),
      recentRuns: store.recentRuns(db, 8),
      unavailableMessage: UNAVAILABLE_MSG,
      statuses: store.STATUSES,
    });
  });

  // THE button. Always a new live search; never a reload of stored results.
  r.post("/api/search", (req, res) => {
    const { run, alreadyRunning } = startRun(db, { teamKey: "michigan", fetchImpl });
    res.status(alreadyRunning ? 409 : 202).json({ run, alreadyRunning });
  });

  r.get("/api/runs/:id", (req, res) => {
    const run = store.getRun(db, req.params.id);
    if (!run) return res.status(404).json({ error: "Not found" });
    const leads = run.status === "running" ? [] : store.listLeads(db, { runId: run.id });
    res.json({ run, leads });
  });

  r.get("/api/leads", (req, res) => {
    const intent = ["HOT", "WARM", "ALL"].includes(req.query.intent) ? req.query.intent : "ALL";
    const status = store.STATUSES.includes(req.query.status) ? req.query.status : undefined;
    res.json({ leads: store.listLeads(db, { intent, status, limit: 500 }) });
  });

  r.patch("/api/leads/:id", (req, res) => {
    const { status, notes } = req.body || {};
    let lead = store.getLead(db, req.params.id);
    if (!lead) return res.status(404).json({ error: "Not found" });
    if (status !== undefined) {
      if (!store.STATUSES.includes(status)) return res.status(400).json({ error: "Invalid status" });
      lead = store.updateLeadStatus(db, lead.id, status, req.user?.user);
    }
    if (notes !== undefined) lead = store.updateLeadNotes(db, lead.id, notes);
    res.json({ lead, summary: summary(db) });
  });

  r.get("/api/insights", (req, res) => res.json(insights(db)));

  return r;
}
