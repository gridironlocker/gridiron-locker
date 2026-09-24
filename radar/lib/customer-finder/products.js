// 5. PRODUCT MATCHING — connect a lead to the most relevant real Gridiron Locker product.
// Reads the live catalogue contract (data/catalogue-live.json, the same file the
// storefront build publishes). If the catalogue has nothing that fits what the person
// asked for (e.g. a hoodie when only tees exist), it says so and flags a CATALOG GAP
// rather than pushing an unrelated product.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { matchProduct as matchCore } from "./match.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CATALOGUE = process.env.CF_CATALOGUE_FILE || path.resolve(__dirname, "../../../data/catalogue-live.json");

let cache = null, cacheMtime = 0;
export function loadCatalogue(file = CATALOGUE) {
  try {
    const st = fs.statSync(file);
    if (!cache || st.mtimeMs !== cacheMtime) {
      const j = JSON.parse(fs.readFileSync(file, "utf-8"));
      cache = (j.products || []).filter((p) => p.site_published !== false);
      cacheMtime = st.mtimeMs;
    }
  } catch { cache = cache || []; }
  return cache;
}

export function matchProduct(teamKey, wants, catalogue = loadCatalogue()) {
  return matchCore(teamKey, wants, catalogue);
}
