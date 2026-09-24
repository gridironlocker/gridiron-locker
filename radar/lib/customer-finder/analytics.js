// 7. ANALYTICS — "Where are Gridiron Locker's actual buyers talking?"
// Funnel stages are cumulative: a CONVERTED lead also counts as contacted, responded, clicked.
const RANK = { NEW: 0, REVIEWED: 1, CONTACTED: 2, RESPONDED: 3, CLICKED: 4, CONVERTED: 5, DISMISSED: -1 };

export function summary(db) {
  const rows = db.prepare(`SELECT intent, status, COUNT(*) n FROM leads GROUP BY intent, status`).all();
  const s = { hot: 0, warm: 0, total: 0, contacted: 0, responses: 0, clicks: 0, conversions: 0, dismissed: 0 };
  for (const r of rows) {
    s.total += r.n;
    if (r.intent === "HOT") s.hot += r.n;
    if (r.intent === "WARM") s.warm += r.n;
    const k = RANK[r.status];
    if (k >= 2) s.contacted += r.n;
    if (k >= 3) s.responses += r.n;
    if (k >= 4) s.clicks += r.n;
    if (k >= 5) s.conversions += r.n;
    if (k === -1) s.dismissed += r.n;
  }
  return s;
}

function breakdown(db, expr) {
  return db.prepare(`
    SELECT ${expr} AS key, COUNT(*) AS leads,
      SUM(intent='HOT') AS hot,
      SUM(status IN ('CONTACTED','RESPONDED','CLICKED','CONVERTED')) AS contacted,
      SUM(status IN ('RESPONDED','CLICKED','CONVERTED')) AS responses,
      SUM(status IN ('CLICKED','CONVERTED')) AS clicks,
      SUM(status='CONVERTED') AS conversions
    FROM leads GROUP BY key ORDER BY conversions DESC, clicks DESC, responses DESC, hot DESC, leads DESC LIMIT 12`).all();
}

export function insights(db) {
  const gaps = db.prepare(`SELECT apparel_type AS key, COUNT(*) AS leads FROM leads WHERE json_extract(product,'$.gap')=1 GROUP BY key ORDER BY leads DESC`).all();
  return {
    byPhrase: breakdown(db, "COALESCE(query,'(unknown)')"),
    byPlatform: breakdown(db, "platform"),
    byTeam: breakdown(db, "team"),
    byApparel: breakdown(db, "COALESCE(apparel_type,'fan apparel')"),
    byConversation: db.prepare(`SELECT url AS key, platform, excerpt, status, intent, seen_count FROM leads
      WHERE status IN ('RESPONDED','CLICKED','CONVERTED') ORDER BY CASE status WHEN 'CONVERTED' THEN 0 WHEN 'CLICKED' THEN 1 ELSE 2 END, updated_at DESC LIMIT 10`).all(),
    catalogGaps: gaps,
  };
}
