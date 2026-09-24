// 1. SEARCH / DISCOVERY — live connectors, called fresh on every button press.
//
// Rules every connector follows:
//   * official/public APIs only, identified User-Agent, bounded request counts
//   * no login-wall bypass, no private groups, no CAPTCHA/anti-bot evasion, no HTML scraping
//     of platforms that forbid it
//   * credentials come from server-side env vars only and never reach the browser
//   * a connector either returns items or throws — failures are reported, never hidden
//
// Each item: { platform, author, authorUrl, title, text, url, postedAt, query, isWebPage, meta }

const UA = process.env.CF_USER_AGENT || "GridironLockerCustomerFinder/1.0 (internal research; contact: owner@gridironlocker.store)";
const TIMEOUT = Number(process.env.CF_SOURCE_TIMEOUT_MS || 15000);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getJson(fetchImpl, url, opts = {}) {
  const res = await fetchImpl(url, { ...opts, headers: { "User-Agent": UA, Accept: "application/json", ...(opts.headers || {}) }, signal: AbortSignal.timeout(TIMEOUT) });
  if (res.status === 429) throw new Error("rate limited (429) — try again shortly");
  if (res.status === 401 || res.status === 403) throw new Error(`access denied (${res.status}) — credentials missing/invalid or endpoint requires auth`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function platformFromUrl(url) {
  const h = (() => { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; } })();
  if (/reddit\.com$|redd\.it$/.test(h)) return "Reddit";
  if (/(^|\.)x\.com$|twitter\.com$/.test(h)) return "X";
  if (/facebook\.com$/.test(h)) return "Facebook";
  if (/bsky\.app$/.test(h)) return "Bluesky";
  if (/threads\.net$/.test(h)) return "Threads";
  if (/quora\.com$/.test(h)) return "Quora";
  if (/forum|board|community|discuss|mgoblog|mgoblue|scout\.com|thewolverine/.test(h)) return `Forum (${h})`;
  return h ? `Web (${h})` : "Web";
}

// Reddit usernames from permalink-style URLs returned by web search engines
function redditAuthorFromText(s) { const m = String(s || "").match(/\bu\/([A-Za-z0-9_-]{3,20})/); return m ? m[1] : null; }

// ---------------------------------------------------------------- Reddit
async function redditToken(fetchImpl) {
  const id = process.env.REDDIT_CLIENT_ID, secret = process.env.REDDIT_CLIENT_SECRET;
  const res = await fetchImpl("https://www.reddit.com/api/v1/access_token", {
    method: "POST",
    headers: { "User-Agent": UA, Authorization: "Basic " + Buffer.from(`${id}:${secret}`).toString("base64"), "Content-Type": "application/x-www-form-urlencoded" },
    body: "grant_type=client_credentials", signal: AbortSignal.timeout(TIMEOUT),
  });
  if (!res.ok) throw new Error(`Reddit OAuth failed (HTTP ${res.status})`);
  return (await res.json()).access_token;
}

function redditQueries(team) {
  const apparel = "(shirt OR hoodie OR sweatshirt OR tee OR merch OR apparel OR crewneck)";
  const intent = `("where can i" OR "where to buy" OR "looking for" OR "anyone know" OR recommendations OR "where did you get" OR "need a")`;
  return [
    { q: `michigan ${apparel} ${intent}`, sub: null, label: "michigan apparel + intent" },
    { q: `wolverines ${apparel}`, sub: null, label: "wolverines apparel" },
    ...team.communities.reddit.filter((s) => s !== "CFB").map((s) => ({ q: apparel, sub: s, label: `r/${s} apparel` })),
    { q: `michigan ${apparel}`, sub: "CFB", label: "r/CFB michigan apparel" },
  ];
}

const reddit = {
  id: "reddit",
  label: "Reddit",
  status() {
    if (process.env.REDDIT_CLIENT_ID && process.env.REDDIT_CLIENT_SECRET) return { enabled: true, mode: "OAuth API" };
    if (process.env.CF_REDDIT_PUBLIC_JSON === "0") return { enabled: false, reason: "Set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET (free 'script' app at reddit.com/prefs/apps)." };
    return { enabled: true, mode: "public JSON (unauthenticated, low rate limit — add OAuth creds for reliability)" };
  },
  async search(team, { fetchImpl }) {
    const oauth = process.env.REDDIT_CLIENT_ID && process.env.REDDIT_CLIENT_SECRET;
    const token = oauth ? await redditToken(fetchImpl) : null;
    const base = oauth ? "https://oauth.reddit.com" : "https://www.reddit.com";
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const items = [];
    let okCalls = 0, lastErr = null;
    for (const { q, sub, label } of redditQueries(team)) {
      const path = sub ? `/r/${sub}/search${oauth ? "" : ".json"}` : `/search${oauth ? "" : ".json"}`;
      const params = new URLSearchParams({ q, sort: "new", t: "month", limit: "50", type: "link", raw_json: "1", ...(sub ? { restrict_sr: "1" } : {}) });
      try {
        const j = await getJson(fetchImpl, `${base}${path}?${params}`, { headers });
        okCalls++;
        for (const c of j?.data?.children || []) {
          const d = c.data || {};
          if (!d.author || d.author === "[deleted]" || d.author === "AutoModerator" || d.stickied || d.promoted) continue;
          items.push({
            platform: "Reddit", author: `u/${d.author}`, authorUrl: `https://www.reddit.com/user/${d.author}`,
            title: d.title, text: d.selftext || "", url: `https://www.reddit.com${d.permalink}`,
            postedAt: d.created_utc ? new Date(d.created_utc * 1000).toISOString() : null,
            query: label, meta: { subreddit: d.subreddit, comments: d.num_comments },
          });
        }
      } catch (e) { lastErr = e; }
      await sleep(oauth ? 700 : 2200); // stay well under Reddit's rate limits
    }
    if (!okCalls) throw lastErr || new Error("no Reddit responses");
    return items;
  },
};

// ---------------------------------------------------------------- X (API v2 recent search)
const x = {
  id: "x",
  label: "X",
  status() {
    return process.env.X_BEARER_TOKEN ? { enabled: true, mode: "API v2 recent search" }
      : { enabled: false, reason: "Set X_BEARER_TOKEN (X API Basic tier or higher). X is not scraped." };
  },
  async search(team, { fetchImpl }) {
    const query = `(michigan OR wolverines OR "go blue") (shirt OR hoodie OR sweatshirt OR tee OR merch OR crewneck) ("where can i" OR "where do i" OR "where to buy" OR "looking for" OR "anyone know" OR "need a" OR "want a" OR recommend) -is:retweet -is:nullcast lang:en`;
    const params = new URLSearchParams({
      query, max_results: "100", "tweet.fields": "created_at,author_id,lang,public_metrics", expansions: "author_id",
      "user.fields": "username,name,description,verified,verified_type,public_metrics",
    });
    const j = await getJson(fetchImpl, `https://api.x.com/2/tweets/search/recent?${params}`, { headers: { Authorization: `Bearer ${process.env.X_BEARER_TOKEN}` } });
    const users = Object.fromEntries((j?.includes?.users || []).map((u) => [u.id, u]));
    const items = [];
    for (const t of j?.data || []) {
      const u = users[t.author_id] || {};
      const followers = u.public_metrics?.followers_count || 0;
      // not looking for influencers/businesses
      if (followers > Number(process.env.CF_MAX_FOLLOWERS || 20000) || u.verified_type === "business" || u.verified_type === "government") continue;
      items.push({
        platform: "X", author: u.username ? `@${u.username}` : null, authorUrl: u.username ? `https://x.com/${u.username}` : null,
        text: t.text, url: `https://x.com/${u.username || "i"}/status/${t.id}`, postedAt: t.created_at, query: "X intent query",
        meta: { bio: u.description || "", followers },
      });
    }
    return items;
  },
};

// ---------------------------------------------------------------- Bluesky
async function bskyAuth(fetchImpl) {
  const res = await fetchImpl("https://bsky.social/xrpc/com.atproto.server.createSession", {
    method: "POST", headers: { "Content-Type": "application/json", "User-Agent": UA },
    body: JSON.stringify({ identifier: process.env.BLUESKY_HANDLE, password: process.env.BLUESKY_APP_PASSWORD }),
    signal: AbortSignal.timeout(TIMEOUT),
  });
  if (!res.ok) throw new Error(`Bluesky login failed (HTTP ${res.status})`);
  return (await res.json()).accessJwt;
}
const bluesky = {
  id: "bluesky",
  label: "Bluesky",
  status() {
    return process.env.BLUESKY_HANDLE && process.env.BLUESKY_APP_PASSWORD ? { enabled: true, mode: "AT Protocol searchPosts (app password)" }
      : { enabled: true, mode: "public AppView searchPosts (may require BLUESKY_HANDLE + BLUESKY_APP_PASSWORD)" };
  },
  async search(team, { fetchImpl }) {
    const authed = process.env.BLUESKY_HANDLE && process.env.BLUESKY_APP_PASSWORD;
    const token = authed ? await bskyAuth(fetchImpl) : null;
    const host = authed ? "https://bsky.social" : "https://public.api.bsky.app";
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const qs = ["michigan shirt", "michigan hoodie", "michigan sweatshirt", "wolverines shirt", "michigan merch"];
    const items = []; let ok = 0, lastErr = null;
    for (const q of qs) {
      try {
        const j = await getJson(fetchImpl, `${host}/xrpc/app.bsky.feed.searchPosts?${new URLSearchParams({ q, sort: "latest", limit: "50", lang: "en" })}`, { headers });
        ok++;
        for (const p of j?.posts || []) {
          const rkey = String(p.uri || "").split("/").pop();
          const handle = p.author?.handle;
          if (!handle || !rkey) continue;
          items.push({
            platform: "Bluesky", author: `@${handle}`, authorUrl: `https://bsky.app/profile/${handle}`,
            text: p.record?.text || "", url: `https://bsky.app/profile/${handle}/post/${rkey}`,
            postedAt: p.record?.createdAt || p.indexedAt || null, query: q, meta: { displayName: p.author?.displayName || "" },
          });
        }
      } catch (e) { lastErr = e; }
      await sleep(400);
    }
    if (!ok) throw lastErr || new Error("no Bluesky responses");
    return items;
  },
};

// ---------------------------------------------------------------- Lemmy (public federated forums)
const lemmy = {
  id: "lemmy",
  label: "Lemmy forums",
  status() { return { enabled: process.env.CF_LEMMY !== "0", mode: `public API (${process.env.CF_LEMMY_INSTANCE || "lemmy.world"})`, reason: "disabled via CF_LEMMY=0" }; },
  async search(team, { fetchImpl }) {
    const inst = process.env.CF_LEMMY_INSTANCE || "lemmy.world";
    const items = []; let ok = 0, lastErr = null;
    for (const [q, type_] of [["michigan shirt", "Posts"], ["michigan hoodie", "Posts"], ["michigan shirt", "Comments"], ["wolverines merch", "Posts"]]) {
      try {
        const j = await getJson(fetchImpl, `https://${inst}/api/v3/search?${new URLSearchParams({ q, type_, sort: "New", limit: "40", listing_type: "All" })}`);
        ok++;
        for (const r of j?.posts || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, title: r.post?.name, text: r.post?.body || "", url: r.post?.ap_id, postedAt: r.post?.published, query: q });
        for (const r of j?.comments || []) items.push({ platform: "Lemmy", author: r.creator?.name, authorUrl: r.creator?.actor_id, text: r.comment?.content || "", url: r.comment?.ap_id, postedAt: r.comment?.published, query: q });
      } catch (e) { lastErr = e; }
      await sleep(500);
    }
    if (!ok) throw lastErr || new Error("no Lemmy responses");
    return items;
  },
};

// ---------------------------------------------------------------- Web search engines
function webPhrases(team) {
  // Intent-bearing phrases first; web engines are expensive so stay bounded.
  const intentFirst = team.phrases.filter((p) => /where|looking|recommend/i.test(p));
  const rest = team.phrases.filter((p) => !/where|looking|recommend/i.test(p));
  return [...intentFirst, ...rest].slice(0, Number(process.env.CF_WEB_QUERIES || 10));
}

const brave = {
  id: "brave",
  label: "Brave Search (web + discussions)",
  status() { return process.env.BRAVE_SEARCH_API_KEY ? { enabled: true, mode: "Brave Search API" } : { enabled: false, reason: "Set BRAVE_SEARCH_API_KEY (api.search.brave.com — has a free tier). Surfaces public forums and indexed Facebook/Quora/forum threads." }; },
  async search(team, { fetchImpl }) {
    const items = []; let ok = 0, lastErr = null;
    for (const phrase of webPhrases(team)) {
      try {
        const j = await getJson(fetchImpl, `https://api.search.brave.com/res/v1/web/search?${new URLSearchParams({ q: phrase, freshness: "pm", count: "20", result_filter: "discussions,web", country: "us" })}`,
          { headers: { "X-Subscription-Token": process.env.BRAVE_SEARCH_API_KEY } });
        ok++;
        for (const r of j?.discussions?.results || []) {
          items.push({ platform: platformFromUrl(r.url), author: r.data?.forum_name ? null : redditAuthorFromText(r.description), title: r.data?.title || r.title,
            text: [r.data?.question, r.data?.top_comment, r.description].filter(Boolean).join(" "), url: r.url, postedAt: r.page_age || null, query: phrase, isWebPage: false });
        }
        for (const r of j?.web?.results || []) {
          items.push({ platform: platformFromUrl(r.url), author: redditAuthorFromText(r.description), title: r.title, text: r.description || "", url: r.url, postedAt: r.page_age || null, query: phrase, isWebPage: true });
        }
      } catch (e) { lastErr = e; }
      await sleep(1100); // free tier = 1 req/s
    }
    if (!ok) throw lastErr || new Error("no Brave responses");
    return items;
  },
};

const google = {
  id: "google",
  label: "Google Programmable Search",
  status() { return process.env.GOOGLE_API_KEY && process.env.GOOGLE_CSE_ID ? { enabled: true, mode: "Custom Search JSON API" } : { enabled: false, reason: "Set GOOGLE_API_KEY + GOOGLE_CSE_ID (Programmable Search Engine, 'search the entire web')." }; },
  async search(team, { fetchImpl }) {
    const items = []; let ok = 0, lastErr = null;
    for (const phrase of webPhrases(team)) {
      try {
        const j = await getJson(fetchImpl, `https://www.googleapis.com/customsearch/v1?${new URLSearchParams({ key: process.env.GOOGLE_API_KEY, cx: process.env.GOOGLE_CSE_ID, q: phrase, dateRestrict: "m1", num: "10" })}`);
        ok++;
        for (const r of j?.items || []) {
          const mt = r.pagemap?.metatags?.[0] || {};
          items.push({ platform: platformFromUrl(r.link), author: redditAuthorFromText(r.snippet), title: r.title, text: r.snippet || "", url: r.link,
            postedAt: mt["article:published_time"] || mt["og:updated_time"] || null, query: phrase, isWebPage: true });
        }
      } catch (e) { lastErr = e; }
      await sleep(250);
    }
    if (!ok) throw lastErr || new Error("no Google responses");
    return items;
  },
};

// Facebook has no public post-search API; we do not scrape it or enter groups.
// Public Facebook pages/posts still arrive via the web search engines above.
const facebook = {
  id: "facebook",
  label: "Facebook (direct)",
  status() { return { enabled: false, reason: "No compliant public search API. Public Facebook posts are picked up via web search engines; private groups are never accessed." }; },
  async search() { return []; },
};

export const SOURCES = [reddit, x, bluesky, lemmy, brave, google, facebook];
export const _internals = { platformFromUrl, redditQueries, webPhrases };
