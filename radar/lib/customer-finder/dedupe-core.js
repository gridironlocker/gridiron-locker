// 3. DEDUPLICATION (pure core, shared by server + in-browser build) — unique identifier = platform + post URL + author + relevant content.
// A second key (platform + canonical URL) catches the same conversation when the
// text was edited or the snippet differs between search engines.

export function canonicalUrl(raw) {
  try {
    const u = new URL(raw);
    u.hash = "";
    for (const k of [...u.searchParams.keys()]) {
      if (/^(utm_|ref|ref_src|s|t|share_id|context|rdt|si|fbclid|gclid)/i.test(k)) u.searchParams.delete(k);
    }
    let host = u.hostname.toLowerCase().replace(/^(www|old|new|np|m|mobile)\./, "");
    if (host === "twitter.com") host = "x.com";
    if (host === "redd.it") host = "reddit.com";
    let p = u.pathname.replace(/\/+$/, "");
    // reddit: /r/sub/comments/<id>/<slug>/<commentId> → keep id + comment id
    const rm = p.match(/\/comments\/([a-z0-9]+)(?:\/[^/]*)?(?:\/([a-z0-9]+))?/i);
    if (host.endsWith("reddit.com") && rm) p = `/comments/${rm[1]}${rm[2] ? "/" + rm[2] : ""}`;
    const xm = p.match(/\/status(?:es)?\/(\d+)/);
    if (host === "x.com" && xm) p = `/status/${xm[1]}`;
    const qs = u.searchParams.toString();
    return `${host}${p.toLowerCase()}${qs ? "?" + qs : ""}`;
  } catch {
    return String(raw || "").trim().toLowerCase();
  }
}

export function normalizeText(t) {
  return String(t || "").toLowerCase().replace(/https?:\/\/\S+/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 280);
}

export function fingerprintBasis({ platform, url, author, text }) {
  return [String(platform || "").toLowerCase(), canonicalUrl(url), String(author || "").toLowerCase().trim(), normalizeText(text)].join("|");
}

export function urlKey({ platform, url }) {
  return `${String(platform || "").toLowerCase()}|${canonicalUrl(url)}`;
}
