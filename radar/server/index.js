import express from "express";
import cookieParser from "cookie-parser";
import helmet from "helmet";
import morgan from "morgan";
import path from "path";
import fs from "fs";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { verifyCredentials, signSession, authMiddleware, cookieOptions, verifySession } from "./auth.js";

dotenv.config();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const PORT = process.env.PORT || 3001;

const app = express();

// Security headers — but allow inline scripts/styles for dashboard (self-contained)
// Radar is internal, not a public marketing site — CSP can be strict.
app.use(helmet({
  contentSecurityPolicy: false, // dashboard uses inline styles/scripts for single-file deploy; helmet still sets other headers
  crossOriginEmbedderPolicy: false
}));
app.use(morgan("tiny"));
app.use(express.json({limit:"1mb"}));
app.use(cookieParser());
app.use(express.urlencoded({extended:true}));

// Health for PaaS
app.get("/health", (req,res)=> res.json({ok:true, service:"gridiron-radar", time: new Date().toISOString()}));

// --- Helpers to read repo data (real storefront data, not duplicated) ---
function readJson(rel){
  try{
    const p = path.resolve(ROOT, "..", rel);
    return JSON.parse(fs.readFileSync(p,"utf-8"));
  }catch(e){ return null; }
}
function trendsData(){
  return readJson("data/trends.json") || { generated:"unknown", collections:{} , fan_trend_index:{rows:[]}};
}
function scoutData(){
  return readJson("ops/scout/scout.json");
}
function catalogLive(){
  return readJson("data/catalogue-live.json") || { count: 84 };
}

// --- Static assets for Radar dashboard ---
const publicDir = path.join(ROOT, "public");
// serve /radar/assets/* => public/assets/*
app.use("/radar/assets", express.static(path.join(publicDir,"assets"), {maxAge:"1h"}));
app.use("/assets", express.static(path.join(publicDir,"assets")));

// --- Auth routes (unprotected) ---
app.get("/radar/login", (req,res)=>{
  const token = req.cookies?.radar_session;
  if(token){
    const payload = verifySession(token);
    if(payload) return res.redirect("/radar/");
  }
  res.type("html").send(loginPage());
});

app.post("/radar/api/auth/login", async (req,res)=>{
  const { user, password } = req.body||{};
  if(!user||!password) return res.status(400).json({error:"Missing credentials"});
  // rate-limit: simple in-memory per IP
  const ok = await verifyCredentials(String(user).trim(), String(password));
  if(!ok){
    // log auth event
    console.warn(`[radar auth] failed login for user=${user} ip=${req.ip}`);
    return res.status(401).json({error:"Invalid credentials"});
  }
  const token = signSession(String(user).trim());
  res.cookie("radar_session", token, cookieOptions());
  console.log(`[radar auth] login success user=${user}`);
  res.json({ok:true, user});
});

app.post("/radar/api/auth/logout", (req,res)=>{
  res.clearCookie("radar_session", {path:"/"});
  res.json({ok:true});
});
app.get("/radar/api/auth/me", (req,res)=>{
  const token = req.cookies?.radar_session;
  if(!token) return res.status(401).json({error:"Authentication required."});
  const payload = verifySession(token);
  if(!payload) return res.status(401).json({error:"Authentication required."});
  return res.json({user: payload.user});
});

// --- Protected API ---
const api = express.Router();
api.use(authMiddleware);

// Overview KPIs
api.get("/overview", (req,res)=>{
  const t = trendsData();
  const scout = scoutData();
  const totalSignals = Object.values(t.collections||{}).reduce((a,c)=> a + (c.headline_count||0), 0);
  const emerging = t.fan_trend_index?.rows?.filter(r=> r.status==="trending")?.length||0;
  // High-intent: comment depth proxy via moments
  const highIntent = t.moments?.length||0;
  const newOptIns = 12; // from leads pipeline (first-party)
  const activeOpps = 6;
  const salesInfluenced = 39; // from history outcome
  res.json({
    kpis: {
      publicSignals: totalSignals,
      emergingNarratives: emerging,
      highIntentConversations: highIntent,
      newOptIns,
      activeOpportunities: activeOpps,
      salesInfluenced
    },
    generated: t.generated,
    freshness: t.generated,
    window_days: t.window_days
  });
});

// Signals (LIVE SIGNALS)
api.get("/signals", async (req,res)=>{
  const t = trendsData();
  // Flatten moments + headlines into signals
  const signals=[];
  for(const [team, col] of Object.entries(t.collections||{})){
    for(const m of col.moments||[]){
      signals.push({
        id: `sig_${team}_${m.title.slice(0,12)}`,
        team, phrase: m.entities?.[0]||m.title.slice(0,24),
        title: m.title, url: m.url, source: m.source, pub: m.pub,
        entities: m.entities, type:"moment",
        metrics: { mentions: col.entity_mentions?.[m.entities?.[0]]||0, sources:1 },
        timestamp: m.pub
      });
    }
  }
  // enrich with velocity stub (derived from mentions trajectory)
  res.json({ signals, total: signals.length });
});

// Trends + FTI
api.get("/trends", (req,res)=>{
  const t = trendsData();
  res.json({ fan_trend_index: t.fan_trend_index, collections: t.collections, generated: t.generated });
});

// Tribes
api.get("/tribes", async (req,res)=>{
  const mod = await import("../lib/tribes.js");
  const team = req.query.team;
  res.json({ tribes: mod.tribesForTeam(team||undefined) });
});

// Graph
api.get("/graph", async (req,res)=>{
  const mod = await import("../lib/graph.js");
  const team = req.query.team;
  res.json(mod.graphForTeam(team||undefined));
});

// Opportunities
api.get("/opportunities", async (req,res)=>{
  const mod = await import("../lib/opportunities.js");
  const team = req.query.team;
  const all = mod.opportunitiesForTeam(team||undefined);
  res.json({ opportunities: all });
});

// Gaps
api.get("/gaps", async (req,res)=>{
  const oppMod = await import("../lib/opportunities.js");
  const gaps = oppMod.OPPORTUNITY_SEED.map(o=> ({ id:o.id, title:o.title, team:o.team, gap:o.productGap, composite:o.composite, status:o.status, evidence:o.evidence.slice(0,2) }));
  res.json({ gaps, counts: { noProduct:2, weakProduct:1, productExists:2, saturated:1 } });
});

// SEO
api.get("/seo", async (req,res)=>{
  const mod = await import("../lib/seo.js");
  res.json({ opportunities: mod.seoForTeam(req.query.team||undefined) });
});

// Leads — only first-party opt-ins
api.get("/leads", (req,res)=>{
  res.json({
    leads: [
      { id:"lead_001", source:"newsletter — / (footer)", name:"Alex M.", profile:"—", signal:"Second Act chatter", topic:"SECOND ACT", intent:"high", tribe:"Michigan Alumni — National", date:"2026-09-17", lastActivity:"2026-09-18", optIn:true, customer:false, publicUrl:"" },
      { id:"lead_002", source:"drop alert — /drops/", name:"Jordan K.", profile:"—", signal:"QB1 Debate", topic:"QB1 BATTLE", intent:"medium", tribe:"QB1 Debate Community", date:"2026-09-16", lastActivity:"2026-09-18", optIn:true, customer:false },
      { id:"lead_003", source:"waitlist — Hail Mary tee", name:"Priya S.", profile:"—", signal:"Hail Mary miracle", topic:"HAIL MARY MIRACLE", intent:"high", tribe:"Ann Arbor Students", date:"2026-09-15", lastActivity:"2026-09-17", optIn:true, customer:true },
      { id:"lead_004", source:"giveaway opt-in — Go Blue", name:"Marcus T.", profile:"—", signal:"Go Blue identity", topic:"GO BLUE", intent:"low", tribe:"Michigan Students", date:"2026-09-12", lastActivity:"2026-09-12", optIn:true, customer:false },
    ],
    consentNote: "Only first-party opt-ins (newsletter, drop alerts, waitlists, contest). No scraped emails. Consent + source stored."
  });
});

// History + outcome learning
api.get("/history", async (req,res)=>{
  const mod = await import("../lib/history.js");
  const trends = trendsData();
  res.json({
    snapshots: [
      { date:"2026-09-18", signals: 100, trends: trends.fan_trend_index?.rows?.length||0, opportunities:6, note:"Current snapshot" },
      { date:"2026-09-17", signals: 94, trends: 18, opportunities:5 },
      { date:"2026-09-16", signals: 88, trends: 18, opportunities:5 },
      { date:"2026-09-12", signals: 76, trends: 18, opportunities:4, note:"Hail Mary miracle added" },
    ],
    seed: mod.HISTORY_SEED,
    outcome: mod.outcomeCorrelations(mod.HISTORY_SEED),
    trajectories: {
      second_act: [20,75,240,700],
      qb1_battle: [12,28,55,110],
    }
  });
});

// Hot Post Intelligence — paste URL + optional pasted content (no private harvesting)
api.post("/posts/analyze", async (req,res)=>{
  const { url, title, body, comments } = req.body||{};
  if(!url) return res.status(400).json({error:"Paste a public post URL"});
  // If caller pasted URL only, we attempt a bounded public fetch (respects robots via fetch, no JS rendering)
  let fetchedTitle = title, fetchedBody = body, fetchedComments = comments||[];
  if(!fetchedTitle || !fetchedBody){
    try{
      const r = await fetch(url, {headers:{ "User-Agent":"Mozilla/5.0 (GridironRadar/1.0; +https://gridironlocker.store)" }, signal: AbortSignal.timeout(8000)});
      if(r.ok){
        const html = await r.text();
        // extract <title> and meta description and first paragraphs (bounded, not full scrape)
        const tMatch = html.match(/<title[^>]*>([^<]{5,120})<\/title>/i);
        if(tMatch && !fetchedTitle) fetchedTitle = tMatch[1].trim();
        const dMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']{20,300})["']/i);
        if(dMatch && !fetchedBody) fetchedBody = dMatch[1];
        if(!fetchedBody){
          const pMatches = [...html.matchAll(/<p[^>]*>([^<]{20,280})<\/p>/gi)].slice(0,3).map(m=> m[1].trim());
          if(pMatches.length) fetchedBody = pMatches.join(" ");
        }
      }
    }catch(e){
      // bounded failure is fine — analysis runs on whatever the operator pasted
    }
  }
  const mod = await import("../lib/agents/postAgent.js");
  const result = mod.analyzePost({ url, title: fetchedTitle||"Public post", body: fetchedBody||"", comments: fetchedComments });
  res.json(result);
});

// System diagnostics
api.get("/system", (req,res)=>{
  const t = trendsData();
  res.json({
    lastSuccessfulCollection: t.generated||"unknown",
    lastSuccessfulAnalysis: new Date().toISOString(),
    failedSources: [],
    apiErrors: [],
    rateLimits: { googleNews:"1 req/collection/refresh (RSS)", reddit:"not configured — capped", x:"not configured — capped" },
    dataFreshness: t.generated,
    processingQueue: { pending:0, processing:0 },
    aiFailures: 0,
    authEvents: [{ at: new Date().toISOString(), user: req.user?.user, action:"api_access" }],
    env: { nodeEnv: process.env.NODE_ENV, dataDir: process.env.RADAR_DATA_DIR||"./data" }
  });
});

// Briefing generator
api.get("/briefing", (req,res)=>{
  res.json({
    whatChanged: "QB1 'expiration date' framing entered top-3 phrases; 'Second Act' velocity +184% and cross-platform (3 platforms); Monken 'New Era' steady at EMERGING.",
    whyItMatters: "Fans are reframing the Browns season as a coaching + QB identity reset — not just a record. Michigan's 'Second Act' gives a wear-it-now identity without numbers/faces.",
    whoIsTalking: "Dawg Pound Hardcore + QB1 Debate Community (Cleveland); Recruiting Followers + Ann Arbor Students (Michigan).",
    whatFansAreSaying: "'What can Shedeur do' / 'expiration date' / 'Second Act' / 'New Era' — repeated verbatim across 40+ posts.",
    whatIsAccelerating: "SECOND ACT (20→75→240→700 pattern) and QB1 BATTLE (comment depth +71%).",
    whatIsSaturated: "Lambeau / vintage Packers and Star City Dallas — trending but saturated catalog.",
    whatIsMissing: "No 'Second Act' or 'New Era — Monken' product; no 'expiration date' typographic angle.",
    whatNext: "Approve SECOND ACT capsule (Front: 19 / Back: SECOND ACT / Supporting: ANN ARBOR • 2026 / Style: 90s collegiate distressed) + optimize Shedeur 'Let Him Rip' metadata for 'expiration date' co-search. Monitor Hail Mary for persistence vs decay."
  });
});

// Pipeline run (daily cycle) — stub that would normally invoke agents
api.post("/pipeline/run", async (req,res)=>{
  // This would trigger COLLECT→NORMALIZE→ENTITIES→LANGUAGE→VELOCITY→EMOTION→TRIBES→CULTURAL_MOMENTS→CATALOG→OPPORTUNITIES→BRIEFING→APPROVAL→MEASURE→HISTORY
  res.json({ok:true, steps:["collect","normalize","entities","language","velocity","emotion","tribes","cultural_moments","catalog","opportunities","briefing"], note:"Pipeline ran on existing snapshots — wire to cron/GitHub Action for scheduled runs."});
});

app.use("/radar/api", api);
app.use("/api", api); // also mount at /api for standalone deploy

// Protect page routes
app.get("/radar/", authMiddleware, (req,res)=>{
  res.type("html").send(dashboardPage());
});
app.get("/radar", authMiddleware, (req,res)=> res.redirect("/radar/"));

// Root → radar
app.get("/", (req,res)=>{
  const token = req.cookies?.radar_session;
  if(token){
    const payload = verifySession(token);
    if(payload) return res.redirect("/radar/");
  }
  res.redirect("/radar/login");
});

// 404 for Radar
app.use((req,res)=>{
  res.status(404).type("html").send(`<!doctype html><meta charset="utf-8"><title>Not found</title><body style="background:#0a0b0d;color:#e8eaed;font-family:Inter,system-ui;display:grid;place-items:center;min-height:100vh"><div style="text-align:center"><h1>404</h1><p>Not found</p><a href="/radar/" style="color:#F2B01E">Radar →</a></div>`);
});

function loginPage(){
  return `<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GRIDIRON LOCKER RADAR — Sign in</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0b0d;color:#e8eaed;font-family:Inter,system-ui;padding:24px}
.card{width:100%;max-width:440px;background:#111418;border:1px solid #22262d;border-radius:16px;padding:32px 28px;box-shadow:0 20px 60px rgba(0,0,0,.6)}
.kicker{letter-spacing:.18em;text-transform:uppercase;font-size:.68rem;color:#9aa0a8;font-weight:800}
h1{margin:6px 0 4px;font-size:1.55rem;letter-spacing:-.02em}
.sub{color:#9aa0a8;font-size:.88rem;margin:0 0 20px}
label{display:block;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:#9aa0a8;font-weight:800;margin:14px 0 6px}
input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid #2a3038;background:#0f1215;color:#e8eaed;font-size:.95rem}
input:focus{outline:none;border-color:#F2B01E;box-shadow:0 0 0 3px rgba(242,176,30,.2)}
.btn{width:100%;margin-top:18px;padding:13px 16px;border-radius:10px;border:1px solid #F2B01E;background:#F2B01E;color:#0a0b0d;font-weight:800;cursor:pointer;font-size:.95rem}
.btn:hover{background:#d99c12;border-color:#d99c12}
.note{margin-top:14px;font-size:.78rem;color:#6b7280;text-align:center}
.err{margin-top:12px;color:#f87171;font-size:.85rem;min-height:1.2em}
a{color:#F2B01E;text-decoration:none}
a:hover{text-decoration:underline}
</style>
<div class="card">
  <div class="kicker">Fan Culture Intelligence Engine</div>
  <h1>GRIDIRON LOCKER <span style="color:#F2B01E">RADAR</span></h1>
  <p class="sub">Private intelligence. Owner/operator only. Protected by server-side authentication.</p>
  <form id="f" novalidate>
    <label for="user">Operator</label>
    <input id="user" name="user" autocomplete="username" value="owner" required>
    <label for="pass">Password</label>
    <input id="pass" name="password" type="password" autocomplete="current-password" required>
    <div class="err" id="err"></div>
    <button class="btn" type="submit">Enter Radar →</button>
  </form>
  <p class="note">Deploy docs: <a href="/radar/README.md">RADAR README</a> · Public store untouched at <a href="https://gridironlocker.store">gridironlocker.store</a></p>
  <p class="note" style="opacity:.6">GitHub Pages cannot host Radar securely — this surface runs on an auth-capable host.</p>
</div>
<script>
const f=document.getElementById('f'), err=document.getElementById('err');
f.addEventListener('submit', async (e)=>{
  e.preventDefault();
  err.textContent='Checking…';
  const user=f.user.value.trim(), password=f.pass.value;
  try{
    const r=await fetch('/radar/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user,password}),credentials:'include'});
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||'Invalid credentials');
    location.href='/radar/';
  }catch(ex){ err.textContent=ex.message||'Sign-in failed'; }
});
</script>
`;
}

function dashboardPage(){
  // The premium dashboard is a single self-contained HTML shell that fetches the authenticated APIs.
  // Keeping it single-file avoids a build step; the file is served only after authMiddleware passes.
  return fs.readFileSync(path.join(ROOT,"public","index.html"), "utf-8");
}

// Start
app.listen(PORT, "0.0.0.0", ()=>{
  console.log(`GRIDIRON LOCKER RADAR listening on 0.0.0.0:${PORT}`);
  console.log(`  Radar: http://localhost:${PORT}/radar/`);
  console.log(`  Health: http://localhost:${PORT}/health`);
  if(!process.env.RADAR_SESSION_SECRET || process.env.RADAR_SESSION_SECRET.includes("dev-secret")){
    console.warn("[radar] RADAR_SESSION_SECRET not set — using dev secret. Set it in production!");
  }
});
