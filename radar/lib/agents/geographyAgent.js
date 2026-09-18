/**
 * GEOGRAPHY AGENT — aggregate/public signals only, never private location.
 */
export const GEO_SEED = {
  "michigan": ["Michigan","Ohio","Illinois","Texas","Florida","California"],
  "cleveland-browns": ["Ohio","Texas","Florida","California","Pennsylvania","Michigan"],
  "green-bay-packers": ["Wisconsin","Illinois","Minnesota","Michigan","Texas"],
  "dallas-cowboys": ["Texas","California","Florida","Oklahoma","Arizona"]
};
export function analyzeGeography(signals){
  // aggregate by team mention; in production would parse public aggregate geo from social platform insights
  const out={};
  for(const s of signals) if(s.team && GEO_SEED[s.team]) out[s.team]=GEO_SEED[s.team];
  return out;
}
