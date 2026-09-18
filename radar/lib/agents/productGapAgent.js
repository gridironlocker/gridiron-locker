/**
 * PRODUCT GAP AGENT — compares opportunities vs catalog.
 */
import { OPPORTUNITY_SEED } from "../opportunities.js";
export function findGaps(catalog){
  return OPPORTUNITY_SEED.map(o=> ({ opportunity:o.title, team:o.team, gap:o.productGap, hasProduct:o.productGap!=="TRENDING + NO PRODUCT" }));
}
