// 5. PRODUCT MATCHING (pure core, shared by server + in-browser build)
import { getTeam } from "./teams.js";

const GARMENT_FOR = {
  "t-shirt": /t-?shirt|tee|long sleeve/i,
  hoodie: /hood/i,
  sweatshirt: /sweatshirt|crew|quarter/i,
};

export function matchProduct(teamKey, wants, catalogue = []) {
  const team = getTeam(teamKey);
  const all = catalogue.filter((p) => p.collection === team.collection);
  const type = wants?.apparelType || "fan apparel";
  const attrs = wants?.attributes || [];

  if (!all.length) return { gap: true, category: `${team.label} apparel`, reason: "No products for this team in the catalogue.", products: [] };

  let pool = all, category, gap = false, gapNote = null;
  if (GARMENT_FOR[type]) {
    pool = all.filter((p) => GARMENT_FOR[type].test(p.garment || ""));
    if (!pool.length) {
      gap = true;
      const have = [...new Set(all.map((p) => p.garment).filter(Boolean))].join(", ");
      gapNote = `CATALOG GAP — no ${team.label} ${type} in the catalogue (currently: ${have || "none"}). Log as product demand; don't pitch an unrelated item.`;
      return { gap, category: `${team.label} ${type}s (not stocked)`, reason: gapNote, products: [] };
    }
    category = `${team.label} ${type}s`;
  } else {
    category = `${team.label} fan apparel`;
  }

  const score = (p) => {
    let s = 0;
    const theme = (p.theme || "").toLowerCase();
    const name = (p.name || "").toLowerCase();
    if (attrs.includes("vintage/retro") && (theme === "retro" || /vintage|retro/.test(name))) s += 5;
    if (attrs.includes("unique/non-generic") && theme !== "classic") s += 3;
    if (attrs.includes("unique/non-generic") && /vintage|limited|second act|revenge|everybody/.test(name)) s += 2;
    if (attrs.includes("player-themed") && (theme === "player" || /bryce|19|qb/.test(name))) s += 5;
    if (attrs.includes("game-day") && /go blue|maize|everybody|limited/.test(name)) s += 2;
    if (attrs.includes("affordable")) s += (40 - (p.price_usd || 40)) / 10;
    return s;
  };
  const ranked = [...pool].sort((a, b) => score(b) - score(a) || (a.price_usd || 99) - (b.price_usd || 99));
  const top = ranked.slice(0, 3);
  const minPrice = Math.min(...pool.map((p) => p.price_usd || Infinity));

  let reason = `Matches requested ${type}.`;
  if (attrs.includes("affordable")) { category = `Lower-priced ${category}`; reason += ` Lowest price $${minPrice}.`; }
  if (attrs.includes("vintage/retro") || attrs.includes("unique/non-generic")) {
    category = `Independent / vintage ${team.label} designs`;
    reason += " Person wants something non-generic — showing independent/retro designs.";
  }
  if (attrs.includes("player-themed")) reason += " Player-themed request.";
  const caveats = [];
  if (attrs.includes("kids/youth")) caveats.push("Asked for kids/youth sizing — confirm availability before replying.");
  if (attrs.includes("women's fit")) caveats.push("Asked for a women's fit — confirm cut availability before replying.");
  if (attrs.includes("a specific design they saw")) caveats.push("Wants a specific design they saw — only reply if one of ours is genuinely close.");

  return {
    gap, category, reason, caveats, collectionUrl: team.collectionUrl,
    products: top.map((p) => ({ slug: p.slug, name: p.name, url: p.url, price: p.price_usd, garment: p.garment, theme: p.theme })),
  };
}
