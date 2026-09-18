/**
 * Radar Data Model — structured intelligence types.
 * Every intelligence item carries source, timestamp, confidence, evidence, processing_status.
 * UI distinguishes FACT vs DETECTED SIGNAL vs AI INTERPRETATION vs OPPORTUNITY HYPOTHESIS.
 */
export const LEVELS = ["FACT","DETECTED_SIGNAL","AI_INTERPRETATION","OPPORTUNITY_HYPOTHESIS"];
export const OPPORTUNITY_STATUS = ["WATCH","EMERGING","DEVELOPING","ACTIONABLE","SATURATED","DECLINING"];

export function nowIso(){ return new Date().toISOString(); }

export function makeSignal({
  id, team, kind="cultural_moment", phrase, entities=[], sources=[], volume=0,
  velocity=null, acceleration=null, emotion=null, tribe=null, geography=null,
  evidence=[], confidence=0, status="DETECTED_SIGNAL"
}){
  return {
    id, team, kind, phrase,
    entities, sources,
    metrics: { volume, velocity, acceleration },
    emotion, tribe, geography,
    evidence, confidence, processing_status: "normalized",
    source: sources[0]?.name || "unknown",
    timestamp: nowIso(),
    level: status
  };
}

export function makeOpportunity({
  id, title, team, culturalMoment, phrase, tribe, entities=[],
  scores={}, evidence=[], relatedSignals=[], productGap=null
}){
  // scores: Trend Velocity, Fan Emotion, Conversation Depth, Audience Growth, Cross-Platform, Tribe Strength, Geographic Spread, Event Proximity, Product Fit, Competition, Catalog Coverage, Novelty, Persistence
  const dims = ["velocity","emotion","conversationDepth","audienceGrowth","crossPlatform","tribeStrength","geoSpread","eventProximity","productFit","competition","catalogCoverage","novelty","persistence"];
  const filled = {}; for(const d of dims) filled[d] = scores[d] ?? 0;
  const avg = Math.round(Object.values(filled).reduce((a,b)=>a+b,0)/dims.length);
  let status="WATCH";
  if(avg>=75 && filled.productFit>=70 && filled.catalogCoverage<=40) status="ACTIONABLE";
  else if(avg>=60) status="DEVELOPING";
  else if(avg>=45) status="EMERGING";
  else if(avg>=25) status="WATCH";
  else status="DECLINING";
  // saturated override
  if(filled.competition>75 && filled.catalogCoverage>70) status="SATURATED";
  return {
    id, title, team, culturalMoment, phrase, tribe, entities,
    scores: filled,
    composite: avg,
    status,
    evidence,
    relatedSignals,
    productGap,
    level: "OPPORTUNITY_HYPOTHESIS",
    timestamp: nowIso(),
    outcome: { detected: nowIso(), acted_on:null, product_created:null, landing_page_created:null, traffic:0, opt_ins:0, sales:0, revenue:0, lifecycle:"new" }
  };
}

export function makeTribe({ id, name, size, growth, coreTopics, language, emotion, geography, productFit, evidence }){
  return { id, name, size, growth, coreTopics, language, emotion, geography, productFit, evidence, timestamp: nowIso(), level:"AI_INTERPRETATION" };
}

export function makeHistorySnapshot({ date, signals, trends, opportunities }){
  return { date: date||nowIso().slice(0,10), signals, trends, opportunities, timestamp: nowIso() };
}
