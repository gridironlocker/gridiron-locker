/**
 * SEO Opportunity Engine — spec §15
 * Connects cultural intelligence to SEO: emerging search language, related phrases, semantic entities, question patterns, long-tail, seasonal, internal-link, landing-page opportunities.
 * Prioritizes differentiated pages supported by actual demand — never thin pages.
 */

export const SEO_SEED = [
  {
    opportunity: "SECOND ACT",
    team: "michigan",
    emergingLanguage: ["second act shirt", "bryce underwood second act tee", "michigan second act apparel"],
    relatedPhrases: ["year two shirt", "captain underwood tee", "ann arbor second act"],
    semanticEntities: ["Bryce Underwood", "Michigan football", "Ann Arbor", "Big House", "Team captain"],
    questionPatterns: ["What does Second Act mean Michigan?", "Who is Michigan captain 2026?"],
    longTail: ["vintage bryce underwood second act crewneck distressed", "michigan year two captain shirt maize navy"],
    seasonal: "Evergreen + event-proximity boost (2 days to UTEP — 'wear it Saturday' window)",
    internalLinks: ["/michigan-wolverines-shirts/", "/2026-season/", "/fan-trend-index/"],
    landingPage: "New differentiated PDP: 'SECOND ACT — Year Two' — Front: 19 / Back: SECOND ACT / Supporting: ANN ARBOR • 2026 / Style: 90s collegiate distressed",
    contentOpportunity: "Editorial: 'What fans mean when they say Second Act' (interview + phrase origin, not product pitch)",
    priority: "HIGH",
    searchIntent: "Fan identity purchase (not gift)"
  },
  {
    opportunity: "QB1 BATTLE — EXPIRATION DATE",
    team: "cleveland-browns",
    emergingLanguage: ["browns qb1 shirt", "shedeur sanders browns shirt", "watson expiration date tee"],
    relatedPhrases: ["let him rip browns shirt", "what can shedeur do shirt", "qb1 battle cleveland"],
    semanticEntities: ["Shedeur Sanders", "Deshaun Watson", "Todd Monken", "Cleveland Browns QB"],
    questionPatterns: ["Who is Browns QB1 2026?", "Will Shedeur start for Browns?"],
    longTail: ["shedeur sanders let him rip cleveland browns fan shirt", "browns qb controversy tee 2026"],
    seasonal: "Time-sensitive — peaks at roster decision + Week 2 narrative",
    internalLinks: ["/cleveland-browns-shirts/", "/drops/", "/fan-trend-index/"],
    landingPage: "Angle without number/face: 'LET HIM RIP' typographic tee (already live — optimize metadata for 'expiration date' co-search)",
    contentOpportunity: "Guide: 'Browns QB1 shirts — what each design says' (buying guide addendum, not thin page)",
    priority: "HIGH",
    searchIntent: "Rivalry / debate purchase",
    caution: "Avoid player-number designs per house rule (slogan only for QB slot)"
  },
  {
    opportunity: "NEW ERA — MONKEN",
    team: "cleveland-browns",
    emergingLanguage: ["new era browns shirt", "todd monken browns tee", "browns new era dawgpound"],
    relatedPhrases: ["dawg pound new era", "cleveland new staff shirt"],
    semanticEntities: ["Todd Monken", "Cleveland Browns", "Dawg Pound"],
    questionPatterns: ["Who is Browns coach 2026?"],
    longTail: ["cleveland browns new era dawgpound graphic tee orange brown"],
    seasonal: "Season-open narrative — best within Weeks 1–3 before it becomes wallpaper",
    internalLinks: ["/cleveland-browns-shirts/"],
    landingPage: "Consider: 'NEW ERA — CLEVELAND' city-mark tee (brown/orange, no coach face per policy)",
    contentOpportunity: "No separate page until volume clears WATCH→EMERGING threshold; monitor",
    priority: "MEDIUM"
  },
  {
    opportunity: "HAIL MARY MIRACLE",
    team: "michigan",
    emergingLanguage: ["michigan hail mary shirt", "michigan miracle tee 2026"],
    relatedPhrases: ["last second win shirt", "western michigan hail mary"],
    semanticEntities: ["Michigan football", "Western Michigan", "Hail Mary"],
    questionPatterns: ["What happened Michigan vs Western Michigan 2026?"],
    longTail: ["michigan hail mary miracle western michigan 2026 fan shirt"],
    seasonal: "Decays fast — bundle with 'Second Act' continuity if re-used",
    internalLinks: ["/michigan-wolverines-shirts/", "/2026-season/"],
    landingPage: "Existence hazard: remarkable but dated — promote via editorial, not new PDP unless persistent",
    contentOpportunity: "Season hub update (already done) + internal link to 'Second Act' PDP as continuity",
    priority: "LOW (monitor)"
  }
];

export function seoForTeam(team){
  if(!team) return SEO_SEED;
  return SEO_SEED.filter(s=> s.team===team);
}
