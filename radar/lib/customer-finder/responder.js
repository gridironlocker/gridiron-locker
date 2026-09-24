// 6. RESPONSE GENERATION — short, human, relevant suggested replies.
// Drafts only: nothing is ever sent automatically. The operator copies, edits and
// posts it manually in the original public thread. Replies disclose the affiliation
// (platform rules + FTC endorsement guidance) and never use hard-sell language.

function pick(arr, seed) {
  let h = 0;
  for (const c of String(seed)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return arr[h % arr.length];
}

function utm(url, platform, leadId) {
  try {
    const u = new URL(url);
    u.searchParams.set("utm_source", String(platform || "community").toLowerCase().replace(/[^a-z0-9]+/g, "-"));
    u.searchParams.set("utm_medium", "community-reply");
    u.searchParams.set("utm_campaign", "customer-finder");
    u.searchParams.set("utm_content", leadId);
    return u.toString();
  } catch { return url; }
}

export function trackedLink(url, platform, leadId) { return utm(url, platform, leadId); }

export function suggestResponse({ intent, wants, match, platform, leadId }) {
  if (intent !== "HOT" && intent !== "WARM") return null;
  if (!match || match.gap || !match.products?.length) {
    return {
      text: null,
      advice: "No genuinely matching product — don't reply with a pitch. Logged as demand for this product type.",
    };
  }
  const attrs = wants?.attributes || [];
  const type = wants?.apparelType && wants.apparelType !== "fan apparel" ? wants.apparelType : "shirt";
  const first = match.products[0];
  const link = utm(match.products.length > 1 ? match.collectionUrl || first.url : first.url, platform, leadId);
  const disclose = pick(["(Full disclosure, it's a small shop I help run.)", "(Disclosure: I'm part of the small team behind it.)", "(Heads up, I help run it — small independent shop.)"], leadId);

  let opener;
  if (attrs.includes("a specific design they saw")) opener = pick([`That exact one can be hard to track down.`, `Not sure who made that exact one, sorry.`], leadId);
  else if (attrs.includes("unique/non-generic") || attrs.includes("vintage/retro")) opener = pick([`Agree, a lot of the Michigan stuff out there looks the same.`, `Totally get wanting something that isn't the standard block M.`], leadId);
  else if (attrs.includes("affordable")) opener = pick([`Official stuff gets pricey fast.`, `Yeah, the official ${type}s add up quickly.`], leadId);
  else if (attrs.includes("game-day")) opener = pick([`Always need a fresh one for game day.`, `Nothing like a new ${type} for Saturday.`], leadId);
  else opener = pick([`If you're open to independent designs, this might help.`, `A few options if you haven't settled on one yet.`], leadId);

  let body;
  if (attrs.includes("affordable")) body = `We have a few independent Michigan fan tees at $${first.price} that might work`;
  else if (attrs.includes("vintage/retro") || attrs.includes("unique/non-generic")) body = `We do a handful of independent Michigan fan designs — "${first.name}" is probably the closest to what you described`;
  else if (attrs.includes("player-themed")) body = `We have a "${first.name}" design that might be close`;
  else body = `We have some independent Michigan fan ${type}s that might be close to what you're after`;

  const close = intent === "HOT" ? `: ${link} ${disclose}` : `, if it's useful: ${link} ${disclose} No worries if not.`;
  const caveat = match.caveats?.length ? match.caveats.join(" ") : null;
  return { text: `${opener} ${body}${close}`, advice: caveat || "Edit to fit the thread, then post manually. One reply per conversation — don't follow up unless they respond." };
}
