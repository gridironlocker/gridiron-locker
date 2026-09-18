/**
 * Fan Language Graph — spec §6
 * Dynamic entity/relationship graph discovering players, coaches, teams, rivals, games, stadiums, cities, nicknames, phrases, memes, emotions, narratives, events, fan tribes.
 * Nodes = entities/phrases; Edges = co-occurrence / narrative links.
 */

export const GRAPH_SEED = {
  nodes: [
    // teams
    { id:"michigan", label:"MICHIGAN", type:"team", team:"michigan" },
    { id:"browns", label:"CLEVELAND BROWNS", type:"team", team:"cleveland-browns" },
    { id:"packers", label:"GREEN BAY PACKERS", type:"team", team:"green-bay-packers" },
    { id:"cowboys", label:"DALLAS COWBOYS", type:"team", team:"dallas-cowboys" },
    // michigan cluster
    { id:"bryce_underwood", label:"BRYCE UNDERWOOD", type:"player", team:"michigan" },
    { id:"year_two", label:"YEAR TWO", type:"narrative", team:"michigan" },
    { id:"second_act", label:"SECOND ACT", type:"phrase", team:"michigan" },
    { id:"captain", label:"CAPTAIN", type:"role", team:"michigan" },
    { id:"new_era", label:"NEW ERA", type:"narrative", team:"michigan" },
    { id:"ann_arbor", label:"ANN ARBOR", type:"city", team:"michigan" },
    { id:"big_house", label:"BIG HOUSE", type:"stadium", team:"michigan" },
    { id:"night_games", label:"NIGHT GAMES", type:"ritual", team:"michigan" },
    { id:"go_blue", label:"GO BLUE", type:"chant", team:"michigan" },
    { id:"michigan_vs_everybody", label:"MICHIGAN VS EVERYBODY", type:"chant", team:"michigan" },
    // browns
    { id:"shedeur_sanders", label:"SHEDEUR SANDERS", type:"player", team:"cleveland-browns" },
    { id:"deshaun_watson", label:"DESHAUN WATSON", type:"player", team:"cleveland-browns" },
    { id:"todd_monken", label:"TODD MONKEN", type:"coach", team:"cleveland-browns" },
    { id:"dawg_pound", label:"DAWG POUND", type:"chant", team:"cleveland-browns" },
    { id:"lake_erie", label:"LAKE ERIE", type:"place", team:"cleveland-browns" },
    // packers
    { id:"jordan_love", label:"JORDAN LOVE", type:"player", team:"green-bay-packers" },
    { id:"lambeau", label:"LAMBEAU", type:"stadium", team:"green-bay-packers" },
    { id:"go_pack_go", label:"GO PACK GO", type:"chant", team:"green-bay-packers" },
    { id:"cheesehead", label:"CHEESEHEAD", type:"identity", team:"green-bay-packers" },
    // cowboys
    { id:"dak_prescott", label:"DAK PRESCOTT", type:"player", team:"dallas-cowboys" },
    { id:"star_power", label:"STAR POWER", type:"chant", team:"dallas-cowboys" },
    { id:"doomsday", label:"DOOMSDAY", type:"narrative", team:"dallas-cowboys" },
    { id:"how_bout_them", label:"HOW 'BOUT THEM COWBOYS", type:"chant", team:"dallas-cowboys" },
    // cross-cutting narratives
    { id:"hail_mary", label:"HAIL MARY", type:"moment", team:"michigan" },
    { id:"qb1_battle", label:"QB1 BATTLE", type:"narrative", team:"cleveland-browns" },
    { id:"redemption", label:"REDEMPTION", type:"emotion", team:"cleveland-browns" },
  ],
  edges: [
    { from:"michigan", to:"bryce_underwood", weight:9, label:"QB1" },
    { from:"bryce_underwood", to:"year_two", weight:7, label:"narrative" },
    { from:"year_two", to:"second_act", weight:8, label:"phrase" },
    { from:"second_act", to:"captain", weight:6 },
    { from:"captain", to:"new_era", weight:7 },
    { from:"new_era", to:"ann_arbor", weight:5 },
    { from:"ann_arbor", to:"big_house", weight:6 },
    { from:"big_house", to:"night_games", weight:5 },
    { from:"second_act", to:"go_blue", weight:4 },
    { from:"michigan", to:"michigan_vs_everybody", weight:8 },
    { from:"browns", to:"shedeur_sanders", weight:8 },
    { from:"browns", to:"deshaun_watson", weight:9 },
    { from:"shedeur_sanders", to:"deshaun_watson", weight:7, label:"QB1 battle" },
    { from:"browns", to:"todd_monken", weight:6, label:"new staff" },
    { from:"todd_monken", to:"new_era", weight:5 },
    { from:"browns", to:"dawg_pound", weight:9 },
    { from:"packers", to:"jordan_love", weight:8 },
    { from:"packers", to:"lambeau", weight:7 },
    { from:"packers", to:"go_pack_go", weight:8 },
    { from:"packers", to:"cheesehead", weight:7 },
    { from:"cowboys", to:"dak_prescott", weight:7 },
    { from:"cowboys", to:"star_power", weight:6 },
    { from:"cowboys", to:"doomsday", weight:5 },
    { from:"cowboys", to:"how_bout_them", weight:7 },
    { from:"bryce_underwood", to:"hail_mary", weight:8, label:"Week 1 miracle" },
    { from:"hail_mary", to:"ann_arbor", weight:6 },
    { from:"deshaun_watson", to:"qb1_battle", weight:8 },
    { from:"shedeur_sanders", to:"qb1_battle", weight:8 },
    { from:"qb1_battle", to:"redemption", weight:7 },
  ]
};

export function discoverVocabulary(texts){
  // naive discovery: extract capitalized phrases / quoted phrases / repeated bigrams that are not stopwords
  const all = (texts||[]).join(" ");
  const quoted = [...all.matchAll(/"([^"]{3,30})"|'([^']{3,30})'/g)].map(m=> (m[1]||m[2]).trim().toUpperCase()).slice(0,20);
  const bigrams = [...all.toLowerCase().matchAll(/\b([a-z]{3,})\s+([a-z]{3,})\b/g)].map(m=> m[0]);
  const freq={}; for(const b of bigrams) freq[b]=(freq[b]||0)+1;
  const emerging = Object.entries(freq).filter(([,c])=>c>=2).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([k])=>k.toUpperCase());
  return { quoted, emerging };
}

export function graphForTeam(team){
  if(!team) return GRAPH_SEED;
  const nodes = GRAPH_SEED.nodes.filter(n=> n.team===team || n.type==="team" && n.id===team.replace("-","_") || ["michigan","browns","packers","cowboys"].includes(n.id));
  const nodeIds = new Set(nodes.map(n=>n.id));
  const edges = GRAPH_SEED.edges.filter(e=> nodeIds.has(e.from) && nodeIds.has(e.to));
  return { nodes, edges };
}
