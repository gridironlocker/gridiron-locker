/**
 * OPPORTUNITY AGENT — aggregates signal/tribe/emotion/velocity into scored opportunities.
 */
import { OPPORTUNITY_SEED } from "../opportunities.js";
export function rankOpportunities({ signals, tribes }){
  // In production this would synthesize live signals; for seed we rank pre-scored seed by composite.
  return [...OPPORTUNITY_SEED].sort((a,b)=> (b.composite||0)-(a.composite||0));
}
