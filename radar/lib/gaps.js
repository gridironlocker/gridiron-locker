/**
 * Product Gap Detection — spec §14
 * Compares detected opportunities against Gridiron Locker catalog.
 * Status: TRENDING+NO_PRODUCT / TRENDING+WEAK_PRODUCT / TRENDING+PRODUCT_EXISTS / TRENDING+SATURATED
 */

// Live catalog counts per team (derived from data/catalogue-live.json semantics; kept in sync via sync script)
const CATALOG = {
  "michigan": 18,
  "cleveland-browns": 19,
  "green-bay-packers": 37,
  "dallas-cowboys": 10
};

export function gapForOpportunity(opp){
  // opp.productGap already classified; this enriches with design counts + shoppability
  const teamCount = CATALOG[opp.team]||0;
  const hasProduct = opp.productGap !== "TRENDING + NO PRODUCT";
  return {
    gap: opp.productGap,
    teamCount,
    hasProduct,
    recommendation: gapRecommendation(opp.productGap),
    designsInTeam: teamCount
  };
}

function gapRecommendation(gap){
  switch(gap){
    case "TRENDING + NO PRODUCT": return "Create new design — open whitespace, low competition";
    case "TRENDING + WEAK PRODUCT": return "Refresh / re-tag / improve existing design — demand exceeds execution";
    case "TRENDING + PRODUCT EXISTS": return "Promote existing design — optimize listing + SEO, no new art needed";
    case "TRENDING + SATURATED MARKET": return "Differentiate heavily or pass — market already served";
    default: return "Investigate";
  }
}

export function allGaps(){
  // imported dynamically to avoid circular
  return import("./opportunities.js").then(m=> m.OPPORTUNITY_SEED.map(o=> ({ opportunity:o.title, team:o.team, ...gapForOpportunity(o) })));
}

export const GAP_COUNTS = {
  noProduct: 2,
  weakProduct: 1,
  productExists: 2,
  saturated: 1
};
