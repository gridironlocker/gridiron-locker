/**
 * Historical Memory + Outcome Learning — spec §19–20
 * Stores signal snapshots, trend trajectories, cultural moments, tribes, opportunities, sources, outcomes, launches, traffic, conversions, sales, opt-ins.
 * Answers: "What happened the last 5 times a Michigan narrative accelerated like this?"
 */

import fs from "fs";
import path from "path";

const HISTORY_DIR = path.join(path.dirname(new URL(import.meta.url).pathname), "../data/history");

export function trajectoryForPhrase(historySnapshots, phrase){
  // historySnapshots: [{date, signals:[{phrase, volume}]}]
  const series=[];
  for(const snap of historySnapshots){
    const sig = snap.signals?.find(s=> s.phrase?.toLowerCase()===phrase.toLowerCase());
    series.push(sig?.volume ?? 0);
  }
  return series;
}

export function similarTrajectories(history, currentSeries, phrase){
  // finds historic phrases with similar velocity/acceleration shape
  // simplified: cosine-like on delta patterns
  const curDeltas = deltas(currentSeries);
  const results=[];
  for(const entry of history){
    if(entry.phrase===phrase) continue;
    const d = deltas(entry.series);
    if(d.length!==curDeltas.length) continue;
    const sim = cosine(curDeltas, d);
    if(sim>0.6) results.push({ phrase: entry.phrase, team: entry.team, similarity: Math.round(sim*100), outcome: entry.outcome });
  }
  return results.sort((a,b)=>b.similarity-a.similarity).slice(0,5);
}

function deltas(series){
  const out=[]; for(let i=1;i<series.length;i++) out.push(series[i]-series[i-1]); return out;
}
function cosine(a,b){
  let dot=0, na=0, nb=0;
  for(let i=0;i<a.length;i++){ dot+=a[i]*b[i]; na+=a[i]*a[i]; nb+=b[i]*b[i]; }
  const denom = Math.sqrt(na)*Math.sqrt(nb);
  return denom? dot/denom : 0;
}

// Outcome tracking
export function recordOutcome(opportunityId, patch){
  // patch: {acted_on, product_created, landing_page_created, traffic, opt_ins, sales, revenue}
  return { opportunityId, ...patch, updated: new Date().toISOString() };
}

export function outcomeCorrelations(history){
  // which signals correlated with useful outcomes (traffic/sales) historically
  const withAction = history.filter(h=> h.outcome?.acted_on);
  const withSales = withAction.filter(h=> (h.outcome?.sales||0)>0);
  return {
    totalDetected: history.length,
    actedOn: withAction.length,
    withSales: withSales.length,
    conversionRate: withAction.length? Math.round((withSales.length/withAction.length)*100):0,
    avgRevenue: withSales.length? Math.round(withSales.reduce((a,b)=>a+(b.outcome.revenue||0),0)/withSales.length):0
  };
}

export const HISTORY_SEED = [
  { date:"2026-09-02", phrase:"SECOND ACT (early murmur)", team:"michigan", series:[2,4,9,20], outcome:{ acted_on:null, sales:0 } },
  { date:"2026-09-06", phrase:"SECOND ACT (post-Hail Mary)", team:"michigan", series:[20,75,240,700], outcome:{ acted_on:"2026-09-08", sales:12, revenue: 316 } },
  { date:"2026-09-10", phrase:"QB1 BATTLE (Sanders hype)", team:"cleveland-browns", series:[12,28,55,110], outcome:{ acted_on:"2026-09-11", sales:8, revenue: 212 } },
  { date:"2026-08-24", phrase:"SHEDEUR SPOTLIGHT (draft week)", team:"cleveland-browns", series:[8,40,120,80], outcome:{ acted_on:"2026-08-25", sales:19, revenue: 498 } },
  { date:"2026-08-20", phrase:"CHEESEHEAD NOSTALGIA", team:"green-bay-packers", series:[15,18,22,19], outcome:{ acted_on:null, sales:0 } },
];
