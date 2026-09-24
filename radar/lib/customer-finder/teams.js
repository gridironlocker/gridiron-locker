// Team configuration. V1 = Michigan only. Adding Browns / Packers / Cowboys later
// means adding an entry here (terms + exclusions + phrases + collection slug).
export const TEAMS = {
  michigan: {
    key: "michigan",
    label: "Michigan Wolverines",
    collection: "michigan",
    collectionUrl: "https://gridironlocker.store/michigan-wolverines-shirts/",
    // A post must mention the team to count.
    terms: [/\bmichigan\b/i, /\bwolverines?\b/i, /\bgo blue\b/i, /\bumich\b/i, /\bann arbor\b/i, /\bmaize (and|&|n) blue\b/i, /\bu of m\b/i],
    // ...and must not be clearly about a different school/brand.
    excludeUnlessAlso: [/\bmichigan state\b/i, /\bspartans?\b/i, /\b(western|central|eastern|northern) michigan\b/i,
      /\bmichigan tech\b/i, /\bdetroit (lions|tigers|pistons|red wings)\b/i, /\bgo green\b/i, /\bmsu\b/i],
    strongTerms: [/\bwolverines?\b/i, /\bgo blue\b/i, /\bumich\b/i, /\bmaize (and|&|n) blue\b/i],
    // Search concepts from the brief — the engine searches these, then reads context.
    phrases: [
      "Michigan shirt", "Michigan t-shirt", "Michigan hoodie", "Michigan sweatshirt", "Michigan merch",
      "Michigan merchandise", "Michigan apparel", "where can I buy Michigan shirt", "where can I find Michigan shirt",
      "looking for Michigan shirt", "looking for Michigan hoodie", "Michigan shirt recommendations",
      "Michigan game day shirt", "Michigan fan shirt", "Michigan student shirt", "Michigan college shirt",
    ],
    communities: {
      reddit: ["MichiganWolverines", "uofm", "annarbor", "CFB"],
      lemmy: [],
    },
  },
};

export function getTeam(key) { return TEAMS[key] || TEAMS.michigan; }
