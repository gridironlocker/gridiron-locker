// 2. INTENT CLASSIFICATION — reads the CONTEXT of a post, not just keywords.
// Deterministic and explainable: every score comes with the reasons behind it.
//
//   HOT  (>= 70): explicitly looking / asking where to buy / asking for recs / immediate need
//   WARM (40-69): clear interest in a specific apparel type/style, no explicit "where to buy"
//   LOW  (< 40) : fan talk without meaningful apparel intent
//   EXCLUDED    : sellers, stores, media, influencers, promo posts, other teams
import { getTeam } from "./teams.js";

const APPAREL = [
  { type: "hoodie", re: /\b(hoodies?|hoody|hoodie's|pullover)\b/i },
  { type: "sweatshirt", re: /\b(sweatshirts?|crew ?necks?|crewnecks?|quarter[- ]zips?|1\/4 zip)\b/i },
  { type: "t-shirt", re: /\b(t[- ]?shirts?|tees?|shirts?|tshirts?|long ?sleeves?)\b/i },
  { type: "fan apparel", re: /\b(merch|merchandise|apparel|gear|clothing|clothes|outfit|jersey|jerseys|swag)\b/i },
];

// Explicit buying/finding intent → HOT
const HOT_PATTERNS = [
  [/\bwhere (can|could|do|should|would) (i|you|we|one) (buy|find|get|order|purchase|grab|pick up)\b/i, "asks where to buy/find"],
  [/\bwhere to (buy|find|get|order|purchase)\b/i, "asks where to buy"],
  [/\b(any ?one|any ?body|does anyone|do you guys|y'?all) know where\b/i, "asks others where to find it"],
  [/\bwhere (did|'d) (you|u|he|she|they) (get|buy|find)\b/i, "asks where someone got it"],
  [/\b(i'?m |i am |im |currently |still )?(looking|searching|hunting) for (a|an|some|the|good|nice|cheap|affordable|decent)?\b/i, "is actively looking"],
  [/\btrying to find\b/i, "is trying to find one"],
  [/\bhelp (me )?(find|finding|locate)\b/i, "asks for help finding one"],
  [/\b(any )?(recommendations?|recs|suggestions?)\b.{0,40}\?|\b(recommend|suggest)\b.{0,40}\?/i, "asks for recommendations"],
  [/\b(best|good|decent) (place|site|store|spot|website)s? (to|for) (buy|get|find)\b/i, "asks for the best place to buy"],
  [/\b(iso|in search of|wtb|want to buy)\b/i, "posted ISO / WTB"],
  [/\bneed (a|an|one|some|new)\b.{0,50}\b(before|for|by) (the |this |next |saturday|sat|game|kickoff|tailgate|homecoming|the ?game)/i, "has an immediate, dated need"],
  [/\b(link|source)\s*\?|\bwho makes (this|that|these)\b/i, "asks for a link/source"],
];

// Clear interest, not yet asking where → WARM
const WARM_PATTERNS = [
  [/\b(i|we) (really |kinda |kind of )?(need|want) (a|an|one|some|new|another)\b/i, "says they need/want one"],
  [/\bi'?d (love|like) (a|an|one|to get)\b/i, "would love one"],
  [/\b(been|i'?ve been) (wanting|meaning to get)\b/i, "has been wanting one"],
  [/\bthinking (about|of) (getting|buying|ordering)\b/i, "is thinking about buying"],
  [/\bshould i (get|buy|order)\b/i, "is deciding whether to buy"],
  [/\bwish i (had|owned|could find)\b/i, "wishes they had one"],
  [/\b(want|need) (one|this|that|it)\b/i, "wants that item"],
  [/\bmy (son|daughter|kid|kids|husband|wife|dad|mom|boyfriend|girlfriend) (needs|wants)\b/i, "shopping for a family member"],
  [/\b(gift|birthday|christmas|present)\b/i, "gift occasion"],
];

// Sellers / businesses / media / influencers / promotion → EXCLUDED
const SELLER_TEXT = [
  /\b(shop|order|buy|get yours) now\b/i, /\b(use|promo|discount) code\b/i, /\blink in (my )?bio\b/i,
  /\b(our|my) (shop|store|etsy|brand|collection|new drop|designs)\b/i, /\b(we|i) just (dropped|launched|released)\b/i,
  /\bavailable now\b/i, /\bfree shipping\b/i, /\b\d{1,2}% off\b/i, /\bdm (me )?(to|for) (order|purchase|pricing)\b/i,
  /\bcheck out my\b/i, /\bnew (drop|arrivals?|collection)\b/i, /\bpre-?orders? (are )?(open|live)\b/i,
  /\bwholesale\b/i, /\bsponsored\b/i, /\baffiliate\b/i, /#(ad|sponsored|etsy|shopsmall|smallbusiness)\b/i,
  /\bgiveaway\b/i, /\bpodcast\b/i, /\bepisode\b/i, /\bpress release\b/i,
];
const SELLER_AUTHOR = /(shop|store|apparel|merch|clothing|boutique|official|news|media|sports?net|podcast|radio|tv|co\b|llc|inc\b|designs?|tees|brand|outfitters|gear|247|rivals|on3|barstool|espn)/i;
const BLOCKED_DOMAINS = /(amazon\.|etsy\.com|ebay\.|fanatics|mgoblueshop|lids\.com|walmart\.|target\.com|dickssportinggoods|homefield|teespring|redbubble|teepublic|zazzle|spreadshirt|nike\.com|shop\.|espn\.|on3\.com|247sports|rivals\.com|mlive\.com|freep\.com|detroitnews|si\.com|foxsports|cbssports|yahoo\.com\/sports|youtube\.com|pinterest\.|tiktok\.com\/@[^/]*(shop|store))/i;

const LOW_FAN_ONLY = /^(go blue!*|hail to the victors!*|let'?s go blue!*)$/i;

export function mentionsTeam(text, team) {
  const t = getTeam(team);
  const hit = t.terms.some((re) => re.test(text));
  if (!hit) return false;
  const other = t.excludeUnlessAlso.some((re) => re.test(text));
  if (other && !t.strongTerms.some((re) => re.test(text))) return false;
  return true;
}

export function detectApparel(text) {
  for (const a of APPAREL) if (a.re.test(text)) return a.type;
  return null;
}

export function detectWants(text, apparelType) {
  const w = { apparelType: apparelType || null, attributes: [] };
  const add = (cond, a) => { if (cond) w.attributes.push(a); };
  add(/\b(cheap|cheaper|affordable|budget|inexpensive|under \$?\d+|not (too )?expensive|reasonabl[ey])/i.test(text), "affordable");
  add(/\b(vintage|retro|throwback|old ?school|90s|80s|distressed)\b/i.test(text), "vintage/retro");
  add(/\b(unique|different|not generic|non-?generic|original|unusual|cool|creative|funny|clever|indie|independent)\b/i.test(text), "unique/non-generic");
  add(/\b(like this|this one|this shirt|this hoodie|this design|the one)\b/i.test(text), "a specific design they saw");
  add(/\b(game[- ]?day|tailgate|saturday|the game|homecoming|kickoff|big house)\b/i.test(text), "game-day");
  add(/\b(student|freshman|alumni|alum|grad|graduation|parent|mom|dad)\b/i.test(text), "student/alumni/family");
  add(/\b(kids?|youth|toddler|baby|infant|son|daughter)\b/i.test(text), "kids/youth");
  add(/\b(women'?s|womens|ladies|girls'?|cropped|crop top)\b/i.test(text), "women's fit");
  add(/\b(plus size|big and tall|xxl|2xl|3xl|4xl|5xl)\b/i.test(text), "extended sizes");
  add(/\b(mccarthy|bryce|underwood|qb ?\d+|harbaugh|moore|jersey number|#\d+)\b/i.test(text), "player-themed");
  add(/\b(gift|birthday|christmas|present)\b/i.test(text), "gift");
  w.summary = summarizeWant(w);
  return w;
}

function summarizeWant(w) {
  const item = w.apparelType && w.apparelType !== "fan apparel" ? `Michigan ${w.apparelType}` : "Michigan fan apparel";
  const attrs = w.attributes.filter((a) => a !== "gift");
  const gift = w.attributes.includes("gift") ? " (as a gift)" : "";
  return attrs.length ? `${item} — ${attrs.join(", ")}${gift}` : `${item}${gift}`;
}

/**
 * classify({text, title, author, url, platform}, teamKey)
 * → { intent: HOT|WARM|LOW|EXCLUDED, score, reasons[], apparelType, wants, excludedReason? }
 */
export function classify(item, teamKey = "michigan") {
  const text = [item.title, item.text].filter(Boolean).join(" \n ").replace(/\s+/g, " ").trim();
  const reasons = [];
  const out = (intent, score, extra = {}) => ({ intent, score: Math.max(0, Math.min(100, Math.round(score))), reasons, ...extra });

  if (!text || text.length < 8) return out("EXCLUDED", 0, { excludedReason: "no readable text" });
  if (item.url && BLOCKED_DOMAINS.test(item.url)) return out("EXCLUDED", 0, { excludedReason: "store/media domain" });
  if (item.author && SELLER_AUTHOR.test(item.author)) return out("EXCLUDED", 0, { excludedReason: `business/media account (${item.author})` });
  const sellerHit = SELLER_TEXT.find((re) => re.test(text));
  if (sellerHit) return out("EXCLUDED", 0, { excludedReason: "promotional / seller language" });
  if (!mentionsTeam(text, teamKey)) return out("EXCLUDED", 0, { excludedReason: "not about this team" });

  const apparelType = detectApparel(text);
  const wants = detectWants(text, apparelType);
  if (LOW_FAN_ONLY.test(text.trim()) || !apparelType) {
    reasons.push(apparelType ? "fan cheer only" : "no apparel mentioned");
    return out("LOW", 10, { apparelType, wants });
  }

  let score = 20; // team + apparel present
  reasons.push(`mentions ${apparelType}`);

  // An intent phrase only counts when its object is apparel ("looking for tickets… my old shirt" ≠ HOT).
  let hot = 0, offTarget = 0;
  for (const [re, why] of HOT_PATTERNS) { const r = aboutApparel(text, re); if (r === true) { hot++; reasons.push(why); } else if (r === "off") offTarget++; }
  let warm = 0;
  for (const [re, why] of WARM_PATTERNS) { const r = aboutApparel(text, re); if (r === true) { warm++; reasons.push(why); } else if (r === "off") offTarget++; }
  if (offTarget && !hot && !warm) reasons.push("asking about something other than apparel");

  const near = proximity(text, apparelType);
  if (hot) score += 50 + Math.min(15, (hot - 1) * 7);
  if (warm) score += hot ? Math.min(8, warm * 4) : 25 + Math.min(12, (warm - 1) * 6);
  if (/\?/.test(text) && (hot || warm)) { score += 6; reasons.push("phrased as a question"); }
  if (wants.attributes.length && (hot || warm)) score += Math.min(8, wants.attributes.length * 3);
  if ((hot || warm) && !near) { score -= 18; reasons.push("intent phrase far from apparel mention"); }
  if (text.length > 1200) { score -= 8; reasons.push("long post — intent less certain"); }
  if (item.isWebPage) { score -= 5; reasons.push("web page snippet (not a direct post)"); }

  const intent = score >= 70 ? "HOT" : score >= 40 ? "WARM" : "LOW";
  if (intent === "LOW" && !hot && !warm) reasons.push("no buying/wanting language");
  return out(intent, score, { apparelType, wants });
}

const APPAREL_ANY = /\b(hoodies?|hoody|pullover|sweatshirts?|crew ?necks?|crewnecks?|quarter[- ]zips?|t[- ]?shirts?|tees?|shirts?|tshirts?|long ?sleeves?|merch|merchandise|apparel|gear|clothing|clothes|outfit|jerseys?|swag)\b/i;
const OTHER_OBJECT = /\b(tickets?|seats?|parking|hotels?|airbnb|restaurants?|bars?|flights?|stream|streams|place to watch|tailgate spot|rides?|tix)\b/i;
function aboutApparel(text, re) {
  const g = new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");
  let m, sawOff = false;
  while ((m = g.exec(text))) {
    const end = m.index + m[0].length;
    if (APPAREL_ANY.test(m[0]) && !OTHER_OBJECT.test(m[0])) return true;
    let after = text.slice(end, end + 90);
    if (/[.!?]\s*$/.test(m[0])) after = ""; // match already closed its sentence
    after = after.split(/[.!?\n](\s|$)/)[0]; // forward object must be in the same sentence
    const before = text.slice(Math.max(0, m.index - 70), m.index);
    const aIdx = after.search(APPAREL_ANY), oIdx = after.search(OTHER_OBJECT);
    if (aIdx >= 0 && (oIdx < 0 || aIdx < oIdx)) return true;
    // backward reference: "this Michigan hoodie — where did you get it?" / "shirt… link?"
    if (oIdx < 0 && APPAREL_ANY.test(before) && !OTHER_OBJECT.test(before)) return true;
    if (oIdx >= 0) sawOff = true;
    if (m[0].length === 0) g.lastIndex++;
  }
  return sawOff ? "off" : false;
}

function proximity(text, apparelType) {
  const lower = text.toLowerCase();
  const a = APPAREL.find((x) => x.type === apparelType);
  const am = a ? lower.search(a.re) : -1;
  if (am < 0) return false;
  const intentRe = /(where|looking|searching|find|buy|get|need|want|recommend|suggest|iso|wtb|link|love|wish|thinking)/gi;
  let m;
  while ((m = intentRe.exec(lower))) if (Math.abs(m.index - am) <= 120) return true;
  return false;
}
