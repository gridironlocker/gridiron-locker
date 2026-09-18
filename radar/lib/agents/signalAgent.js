/**
 * SIGNAL AGENT — spec §22
 * Collects raw public signals, normalizes, deduplicates, enriches with entities/phrases.
 * Respects platform API rules / robots / rate limits / terms. No unauthorized scraping.
 */
export function normalizeSignal(raw){
  return {
    id: raw.id||`sig_${Date.now()}`,
    source: raw.source,
    team: raw.team,
    text: (raw.text||raw.title||"").trim(),
    url: raw.url,
    published: raw.published||raw.pub||null,
    metrics: raw.metrics||{},
    normalizedAt: new Date().toISOString()
  };
}

export function collectSignals({ trends, socialSignals }){
  const out=[];
  for(const [team, col] of Object.entries(trends?.collections||{})){
    for(const h of col.headlines||[]){
      out.push(normalizeSignal({ source:"google_news", team, text:h.title, url:h.url, published:h.pub, metrics:{ mentions:1 } }));
    }
  }
  for(const item of socialSignals?.sources?.google_news?.items||[]){
    // already covered above if same feed; dedupe by URL later
  }
  for(const item of socialSignals?.sources?.reddit?.items||[]){
    out.push(normalizeSignal({ source:"reddit", team:item.team, text:item.text, url:item.url, published:item.published, metrics:item.metrics }));
  }
  // Dedupe by URL + first 80 chars
  const seen=new Set(); return out.filter(s=>{ const k=(s.url||s.text.slice(0,80)); if(seen.has(k)) return false; seen.add(k); return true; });
}
