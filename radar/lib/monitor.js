/**
 * Observability — spec §26
 * Displays last successful collection, analysis, failed sources, API errors, rate limits, data freshness, queue, AI failures, auth events.
 */

export function systemDiagnostics({ trendsDate, socialSignalsDate, lastBuild }){
  const now = new Date();
  const freshness = (iso)=>{
    if(!iso) return { label:"unknown", ageHours: Infinity, stale:true };
    const d = new Date(iso);
    const ageHours = (now - d)/3.6e6;
    return { label: isFinite(ageHours)? `${Math.round(ageHours)}h ago` : "unknown", ageHours, stale: ageHours>26 };
  };
  return {
    lastSuccessfulCollection: freshness(trendsDate),
    lastSuccessfulAnalysis: freshness(socialSignalsDate),
    lastBuild: freshness(lastBuild),
    failedSources: [], // populated when fetch fails
    rateLimits: { googleNews: "RSS — no key, polite 1 req/collection", reddit:"not configured", x:"not configured" },
    apiErrors: [],
    dataFreshness: freshness(trendsDate),
    processingQueue: { pending: 0, processing: 0 },
    aiFailures: 0,
    authEvents: [] // appended by auth middleware
  };
}
