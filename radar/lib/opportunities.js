/**
 * Opportunity Engine — spec §12
 * Component scores (NOT simplistic popularity): Trend Velocity, Fan Emotion, Conversation Depth, Audience Growth, Cross-Platform, Tribe Strength, Geographic Spread, Event Proximity, Product Fit, Competition, Catalog Coverage, Novelty, Persistence.
 * Status: WATCH / EMERGING / DEVELOPING / ACTIONABLE / SATURATED / DECLINING
 * Shows evidence, never pretends score is objective truth.
 */
import { velocity, acceleration } from "./velocity.js";

export const DIMENSIONS = [
  { key:"velocity", label:"Trend Velocity", desc:"Mention acceleration, not total count" },
  { key:"emotion", label:"Fan Emotion", desc:"Intensity + identity language" },
  { key:"conversationDepth", label:"Conversation Depth", desc:"Comment depth + repetition" },
  { key:"audienceGrowth", label:"Audience Growth", desc:"Unique sources / authors WoW" },
  { key:"crossPlatform", label:"Cross-Platform Spread", desc:"How many platforms carry it" },
  { key:"tribeStrength", label:"Tribe Strength", desc:"Tribe size × growth for this narrative" },
  { key:"geoSpread", label:"Geographic Spread", desc:"Aggregate public geo signals" },
  { key:"eventProximity", label:"Event Proximity", desc:"Days to next game / cultural moment" },
  { key:"productFit", label:"Product Fit", desc:"Does this narrative want to be worn?" },
  { key:"competition", label:"Competition", desc:"How many POD sellers already chase it (inverse)" },
  { key:"catalogCoverage", label:"Catalog Coverage", desc:"Do we already have a strong product? (inverse)" },
  { key:"novelty", label:"Novelty", desc:"New vocabulary vs prior baseline" },
  { key:"persistence", label:"Persistence", desc:"Is it still there 3+ days later?" },
];

export function scoreOpportunity(input){
  // input: raw signals, entities, metrics - returns dimension scores 0-100
  const s = {
    velocity: clamp(input.velocity ?? 50),
    emotion: clamp(input.emotion ?? 50),
    conversationDepth: clamp(input.conversationDepth ?? 50),
    audienceGrowth: clamp(input.audienceGrowth ?? 50),
    crossPlatform: clamp(input.crossPlatform ?? 50),
    tribeStrength: clamp(input.tribeStrength ?? 50),
    geoSpread: clamp(input.geoSpread ?? 50),
    eventProximity: clamp(input.eventProximity ?? 50),
    productFit: clamp(input.productFit ?? 50),
    competition: clamp(input.competition ?? 50), // high = low competition (good)
    catalogCoverage: clamp(input.catalogCoverage ?? 50), // high = weak coverage (opportunity)
    novelty: clamp(input.novelty ?? 50),
    persistence: clamp(input.persistence ?? 50),
  };
  // competition & catalogCoverage are inverted for status logic elsewhere: high competition = bad, high coverage = saturated
  const vals = Object.values(s);
  const composite = Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);
  let status="WATCH";
  if(s.velocity>=70 && s.emotion>=60 && s.crossPlatform>=50 && s.productFit>=65 && s.catalogCoverage>=60){
    status="ACTIONABLE";
  } else if(composite>=60) status="DEVELOPING";
  else if(composite>=42) status="EMERGING";
  else if(composite<22) status="DECLINING";
  if(s.competition<25 && s.catalogCoverage<25) status="SATURATED";
  return { scores: s, composite, status };
}

function clamp(n){ return Math.max(0, Math.min(100, Math.round(n))); }

// Seed opportunities — each is a cultural moment before it becomes a product keyword
export const OPPORTUNITY_SEED = [
  {
    id:"opp_second_act",
    title:"SECOND ACT",
    team:"michigan",
    culturalMoment:"Bryce Underwood's Year Two — redemption narrative + captaincy",
    phrase:"Second Act",
    tribe:"Recruiting Followers + Ann Arbor Students",
    entities:["Bryce Underwood","Year Two","Captain","Ann Arbor","Big House"],
    scores: { velocity:84, emotion:78, conversationDepth:71, audienceGrowth:66, crossPlatform:68, tribeStrength:72, geoSpread:64, eventProximity:82, productFit:86, competition:74, catalogCoverage:78, novelty:81, persistence:69 },
    evidence: [
      "Fans repeatedly using 'Second Act' to frame Underwood's second-year + captain storyline (11 headlines, 2,400+ engagements)",
      "Velocity +184% (20→75→240→700 pattern isolated in Reddit + X cluster; not headline-volume alone)",
      "Identity language high ('we/our/Go Blue/This is Michigan' in 34% of posts)",
      "Cross-platform: Google News + Reddit (r/MichiganWolverines, r/CFB) + X; 3 platforms",
      "Event proximity: Michigan vs UTEP in 2 days — prime drop window",
      "Existing catalog: no 'Second Act' product; closest is 'Bet M' — weak coverage"
    ],
    productGap: "TRENDING + NO PRODUCT",
    status:"ACTIONABLE",
    composite:76
  },
  {
    id:"opp_qb1_battle",
    title:"QB1 BATTLE — EXPIRATION DATE",
    team:"cleveland-browns",
    culturalMoment:"Shedeur Sanders vs Deshaun Watson — 'expiration date' framing",
    phrase:"Expiration Date",
    tribe:"QB1 Debate Community + Dawg Pound Hardcore",
    entities:["Shedeur Sanders","Deshaun Watson","Todd Monken","QB1"],
    scores: { velocity:91, emotion:88, conversationDepth:82, audienceGrowth:74, crossPlatform:72, tribeStrength:69, geoSpread:58, eventProximity:88, productFit:62, competition:44, catalogCoverage:51, novelty:76, persistence:61 },
    evidence: [
      "Cleveland.com: 'Browns reporters aren't asking if Watson can turn it around anymore — they're asking when Shedeur starts'",
      "Cluster: 41% player breakout / 24% new era / 18% rivalry / 10% nostalgia / 7% game-day culture (4,200 engagements sampled)",
      "Velocity: Watson 25→45 mentions headlined, but Shedeur comment depth +71% (fans, not journalists, driving it)",
      "'Expiration date' + 'What can Shedeur do' rapidly spreading as distinct phrasing"
    ],
    productGap: "TRENDING + WEAK PRODUCT",
    status:"ACTIONABLE",
    composite:71
  },
  {
    id:"opp_new_era_monken",
    title:"NEW ERA — MONKEN",
    team:"cleveland-browns",
    culturalMoment:"Todd Monken takes over as HC — 'new era' co-mentioned with Dawg Pound re-identity",
    phrase:"New Era",
    tribe:"Dawg Pound Hardcore",
    entities:["Todd Monken","Dawg Pound","New Era"],
    scores: { velocity:66, emotion:64, conversationDepth:58, audienceGrowth:52, crossPlatform:51, tribeStrength:61, geoSpread:43, eventProximity:77, productFit:71, competition:68, catalogCoverage:82, novelty:84, persistence:48 },
    evidence: [
      "6 headline mentions (Monken) — accelerating but lower absolute volume than QB1 battle",
      "Narrative gap: no 'Monken / New Era' product in locker — vintage 'New Era' city language exists but not coach-anchored",
      "Co-mentioned with 'Dawg Pound' re-identity posts before Tampa Bay Week 2"
    ],
    productGap: "TRENDING + NO PRODUCT",
    status:"EMERGING",
    composite:66
  },
  {
    id:"opp_hail_mary miracle",
    title:"HAIL MARY MIRACLE",
    team:"michigan",
    culturalMoment:"Week 1 Hail Mary vs Western Michigan — last-second mythology",
    phrase:"Hail Mary",
    tribe:"Michigan Students + Alumni — National",
    entities:["Bryce Underwood","Hail Mary","Big House","Western Michigan"],
    scores: { velocity:72, emotion:81, conversationDepth:68, audienceGrowth:59, crossPlatform:64, tribeStrength:77, geoSpread:71, eventProximity:44, productFit:79, competition:58, catalogCoverage:44, novelty:62, persistence:57 },
    evidence: [
      "Season hub result: 'last-second Hail Mary win over Western Michigan' — high emotional intensity, nostalgia loop",
      "Persistence risk: miracle moments decay fast after next game unless tied to 'Second Act' continuity",
      "Nostalgia + celebration + pride co-detected"
    ],
    productGap: "TRENDING + PRODUCT EXISTS",
    status:"DEVELOPING",
    composite:68
  },
  {
    id:"opp_lambeau_layers",
    title:"LAMBEAU LAYERS",
    team:"green-bay-packers",
    culturalMoment:"Late-afternoon divisional cold-weather ritual — 'layers' conversation emerging",
    phrase:"Lambeau Layers",
    tribe:"Cheesehead Nation",
    entities:["Lambeau","Go Pack Go","Minnesota rivalry"],
    scores: { velocity:41, emotion:52, conversationDepth:44, audienceGrowth:38, crossPlatform:36, tribeStrength:66, geoSpread:49, eventProximity:69, productFit:74, competition:62, catalogCoverage:38, novelty:71, persistence:52 },
    evidence:[
      "Seasonal opportunity: September layers → January layers; steady not spiky — persistence-driven",
      "Product gap saturated: many vintage/Lambeau products exist — needs differentiated angle"
    ],
    productGap:"TRENDING + SATURATED MARKET",
    status:"WATCH",
    composite:52
  },
  {
    id:"opp_star_city",
    title:"STAR CITY",
    team:"dallas-cowboys",
    culturalMoment:"Texas pride minimalism — 'Star City' as city-identity shorthand (v. 'Doomsday')",
    phrase:"Star City",
    entities:["Dallas","Texas","Star Power"],
    scores: { velocity:38, emotion:47, conversationDepth:41, audienceGrowth:36, crossPlatform:33, tribeStrength:58, geoSpread:62, eventProximity:61, productFit:69, competition:55, catalogCoverage:47, novelty:68, persistence:44 },
    evidence:[
      "Vintage Texas capsule (Week1 SLATE: 'Star City' palette #8FA0B8 on #0B1B33) — evergreen, not accelerating",
      "Doomsday heritage vs Star City minimalism — competing narratives, neither accelerating"
    ],
    productGap:"TRENDING + PRODUCT EXISTS",
    status:"WATCH",
    composite:48
  }
];

export function opportunitiesForTeam(team){
  if(!team) return OPPORTUNITY_SEED;
  return OPPORTUNITY_SEED.filter(o=> o.team===team);
}
