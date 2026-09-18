/**
 * Fan Tribe Discovery — spec §9
 * Automatically identify clusters of fans from behavioral/language patterns.
 * Displays TRIBE, SIZE, GROWTH, CORE TOPICS, LANGUAGE, EMOTION, GEOGRAPHY, PRODUCT FIT.
 */

export const TRIBE_SEED = [
  {
    id:"michigan_students",
    team:"michigan",
    name:"Ann Arbor Students",
    size: 4200,
    growth: +18,
    coreTopics: ["Bryce Underwood", "Big House night games", "Michigan vs Everybody"],
    language: ["Go Blue","We","Our house","Second act"],
    emotion: "anticipation",
    geography: "Ann Arbor, MI + campus diaspora",
    productFit: 82,
    evidence: "High identity language ('we/our'), campus event proximity, student-section rituals"
  },
  {
    id:"michigan_alumni",
    team:"michigan",
    name:"Michigan Alumni — National",
    size: 8600,
    growth: +7,
    coreTopics: ["Nostalgia", "NATIONAL CHAMPS 2023", "Legacy captains"],
    language: ["Go Blue","Once a Wolverine","Maize & Blue"],
    emotion: "pride",
    geography: "Michigan, Illinois, Texas, California, Florida",
    productFit: 78,
    evidence: "Alumni vernacular, vintage/throwback resonance, out-of-state shipping clusters"
  },
  {
    id:"michigan_recruiting",
    team:"michigan",
    name:"Recruiting Followers",
    size: 2100,
    growth: +34,
    coreTopics: ["Bryce Underwood era", "QB1 succession", "Five-star narratives"],
    language: ["Year two","New era","Captain"],
    emotion: "anticipation",
    geography: "Digital-native, cross-state",
    productFit: 71,
    evidence: "Acceleration around 'Year Two' + 'Second Act' phrase spread 3 platforms in 72h"
  },
  {
    id:"browns_dawgpound_hardcore",
    team:"cleveland-browns",
    name:"Dawg Pound Hardcore",
    size: 7400,
    growth: +11,
    coreTopics: ["Dawg Pound identity", "Lake Erie toughness", "Defense"],
    language: ["Dawg Pound","Here We Go Brownies","Our Dawgs"],
    emotion: "belonging",
    geography: "Cleveland, Akron, Columbus, + Ohio diaspora in TX/FL",
    productFit: 85,
    evidence: "Highest identity-language density; 'we/our' 3.2× baseline; game-day ritual peaks"
  },
  {
    id:"browns_qb1_debaters",
    team:"cleveland-browns",
    name:"QB1 Debate Community",
    size: 5400,
    growth: +42,
    coreTopics: ["Shedeur vs Watson", "Todd Monken new era", "QB redemption"],
    language: ["QB1","Second act","Let him rip","Expiration date"],
    emotion: "frustration",
    geography: "Cleveland + national NFL discourse",
    productFit: 68,
    evidence: "Volume spike 11→45 mentions (Watson), cross-posted Browns/Reddit/X, comment depth +71%"
  },
  {
    id:"packers_cheesehead_nation",
    team:"green-bay-packers",
    name:"Cheesehead Nation",
    size: 9100,
    growth: +5,
    coreTopics: ["Lambeau folklore", "Go Pack Go", "Community-owned identity"],
    language: ["Go Pack Go","Cheesehead","Lambeau Leap"],
    emotion: "pride",
    geography: "Wisconsin, Illinois, Minnesota (rivalry corridor)",
    productFit: 88,
    evidence: "Strongest statewide geographic concentration; vintage/retro product affinity"
  },
  {
    id:"packers_collectors",
    team:"green-bay-packers",
    name:"Vintage Collectors",
    size: 1600,
    growth: +22,
    coreTopics: ["EST 1919 crests", "All-over retros", "Helmet history"],
    language: ["Vintage","Throwback","EST 1919"],
    emotion: "nostalgia",
    geography: "Wisconsin + national vintage football niche",
    productFit: 74,
    evidence: "Holiday/gift purchase intent; nostalgia-lexicon 2.8× baseline"
  },
  {
    id:"cowboys_starpower",
    team:"dallas-cowboys",
    name:"Star Power — Texas Pride",
    size: 8300,
    growth: +4,
    coreTopics: ["Star logo folklore", "Texas pride", "Doomsday defense heritage"],
    language: ["How 'Bout Them Cowboys","Star Power","Texas"],
    emotion: "confidence",
    geography: "Texas, Oklahoma, California, Florida (largest diaspora)",
    productFit: 80,
    evidence: "Largest out-of-state footprint; 'Texas' co-mentioned in 34% of Dallas signals"
  },
  {
    id:"cowboys_roadtrip",
    team:"dallas-cowboys",
    name:"Road-Trip Game-Day Fans",
    size: 1900,
    growth: +28,
    coreTopics: ["Prime-time road fits", "Stadium pilgrimages", "Tailgate culture"],
    language: ["Game day","On the road","Fit"],
    emotion: "celebration",
    geography: "National — travel-correlated spikes before away games",
    productFit: 76,
    evidence: "Event-proximity spikes T-2 days; 'fit' vocabulary +23% WoW"
  }
];

export function tribesForTeam(team){
  if(!team) return TRIBE_SEED;
  return TRIBE_SEED.filter(t=> t.team===team);
}

export function discoverTribes(signals){
  // In production this clusters by embedding similarity; for now we rank seed tribes by signal overlap.
  const teamCounts={};
  for(const s of signals||[]) teamCounts[s.team]=(teamCounts[s.team]||0)+1;
  return [...TRIBE_SEED].sort((a,b)=>{
    const ca = teamCounts[a.team]||0, cb = teamCounts[b.team]||0;
    if(cb!==ca) return cb-ca;
    return b.growth - a.growth;
  });
}
