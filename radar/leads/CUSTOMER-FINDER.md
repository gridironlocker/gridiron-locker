# Customer Intent Finder (private)

**URL:** `https://<radar-host>/private/customer-finder/`. It is served only by the Radar app, never by `site/`.
There's no public link and no sitemap entry. The Radar host serves `robots.txt: Disallow: /`, `X-Robots-Tag: noindex` and
`Cache-Control: no-store`. Every page and API request checks the session server-side (bcrypt + signed HttpOnly cookie),
and state-changing calls require a custom CSRF header.

## What one press of 🔄 FIND NEW BUYERS does
1. **Discovery** (`lib/customer-finder/sources.js`): searches every configured connector live, in parallel,
   using only official or public APIs: Reddit, X, Bluesky, Lemmy, Brave Search and Google Programmable Search.
   There's no scraping and no getting around logins or CAPTCHAs. Facebook has no public search API, so public
   Facebook posts only arrive through the web search engines.
2. **Intent classification** (`classifier.js`): the post must mention the team and an apparel item, and the intent
   phrase has to be *about* that apparel. Results are HOT (70 or higher), WARM (40 to 69) or LOW. Sellers, stores,
   media, promo posts, big accounts and other schools are excluded. Every score shows its reasons.
3. **Dedupe** (`dedupe.js`): SHA-256 of platform + canonical URL + author + normalized text, plus a second key of
   platform + canonical URL. A match means "previously seen": it's counted and never shown as new.
4. **Storage** (`store.js`): SQLite at `$RADAR_DATA_DIR/customer-finder.db`. Put this on a persistent volume.
5. **Product match** (`products.js`): reads `data/catalogue-live.json`. If nothing fits (for example a hoodie, when
   Michigan is tees-only today), it flags a **CATALOG GAP** and doesn't write a pitch.
6. **Response draft** (`responder.js`): short, discloses the affiliation, and adds a UTM-tagged link. You copy and
   post it by hand. Nothing is ever sent automatically.
7. **Analytics** (`analytics.js`): funnel counts, plus which phrases, platforms, teams, apparel types and
   conversations lead to replies, clicks and sales. Clicks and conversions come from the status you set
   (and from UTM `utm_campaign=customer-finder`, `utm_content=<lead id>` in your store analytics).

If no connector responds, the run is recorded as `unavailable` with the message
"Live search unavailable. No new leads were added." Old results are never shown as fresh.

## Privacy
The finder doesn't collect, guess or buy email addresses. It removes emails and phone numbers from stored text.
LOW-intent posts are counted but not stored. You contact people through their original public thread.

## Deploy
Run it with Docker on Render, Railway or Fly **with a persistent volume** mounted at `RADAR_DATA_DIR`.
Vercel's filesystem is temporary, so leads wouldn't survive there. Required env: `RADAR_SESSION_SECRET` (32+ chars),
`RADAR_AUTH_PASSWORD_HASH`, and at least one connector key (see `.env.example`).
In production the server won't start without a real session secret, and it refuses the dev password.

## Adding teams
Add an entry to `lib/customer-finder/teams.js` (Browns, Packers, Cowboys) and point the router's `teamKey` at it.

## Static version on the public site (code-protected)
**URL:** `https://gridironlocker.store/private/customer-finder/`. It isn't linked anywhere or listed in the sitemap, and it's marked noindex.

To rebuild after changing the engine or catalogue (the code is never saved in the repo):
```bash
CF_CODE='<access code>' node radar/static-finder/build.mjs
```
`CF_OUT=/path/to/file.html` redirects the output (the test suite uses that so it never touches the committed page).

- The whole dashboard is **encrypted** with AES-256-GCM, using a key derived from the code (PBKDF2, 600k rounds).
  The public file contains only ciphertext and an unlock screen.
- Leads are saved in *that browser* (localStorage), so use **Export backup** and **Import** to move them or keep them safe.
- It isn't true access control. Anyone can download the encrypted file and try to guess the code offline, so a long
  code is much stronger than a short one. To change the code, rerun the build with a new `CF_CODE`.

### What changed in 2026-09 (Free discovery)
The automatic sources that had started answering **403** from a browser were removed rather than worked around:
**Reddit's unauthenticated JSON** and **Bluesky's `searchPosts`**. Nothing is scraped and no login is bypassed;
the keyless **Lemmy** API is the only automatic connector left. Everything else now runs in the operator's own
logged-in browser, from the **Free discovery** panel (`radar/static-finder/assist.html`, injected by `build.mjs`
after `#banner`). The server build in `lib/customer-finder/sources.js` is untouched (it can still use Reddit OAuth,
Bluesky app passwords, X, Brave and Google with real keys).

**Engine (`radar/static-finder/browser-engine.js`)**
- `cfProcess(db, runId, rawItems)` — the pipeline: classify → dedupe → match product → draft reply → store.
- `cfIngest(items, label, runId?)` — creates a run or extends it, with honest counts:
  `new_leads` / `duplicates` (previously seen) / `low_filtered` / `excluded` / **`rejected`** (item had no link).
  A post without a public URL is rejected, never stored and never counted as new.
- `cfLiveStart / cfLiveStop / cfLiveStatus / cfLiveSetBatchMs` — the Bluesky radar (below).

**1 · Assisted search** — 10 recent-post searches opened in a new tab, in your own logged-in browser:
X Latest (`f=live`, `-filter:links`), Reddit New (sitewide + r/uofm), Reddit search `t=week` + r/uofm search
`t=month`, Google forums (`tbs=qdr:d` and `qdr:w`, excluding etsy, amazon and fanatics), Facebook posts,
Threads, Bluesky. The query phrases rotate through four intent pools (direct asks, recommendations, needs,
style) and the rotation is stored in `localStorage` (`gl_cf_query_rotation`); **New query set** advances it.
**Open all searches** opens every one (a blocked-popup count is reported honestly).
*Bluesky's web search needs you to be logged in — logged out, bsky.app says "Search is currently unavailable".*

**2 · 📥 Send to Finder bookmarklet** — built at runtime from `location.origin + pathname`; drag it to the
bookmarks bar. It reads what is on screen: X (`article` → `[data-testid=tweetText]` + the status link that
contains `<time>`), Reddit (new `shreddit-post` / `shreddit-comment` attributes and old-Reddit
`.thing[data-permalink]`), Google results (`h3` + link), and anywhere else the selected text (or the page text)
plus the page URL. It opens the Finder with `#import=<json>` (max 60 items); the Finder ingests it on load,
shows the counts and clears the hash so a reload doesn't double-import.

**3 · Paste box** — one post per blank-line block, and every block must contain its URL. Blocks without a link
are counted as **rejected**. Counts are shown after ingesting.

**4 · Bluesky live radar** — a public **Jetstream** WebSocket (`app.bsky.feed.post` only), prefiltered on
team + apparel words in this tab, batched into `cfIngest` every **1.5 s**, with `postsChecked` /
prefiltered / batches / last-batch counts on screen. Hosts are tried in order:
`jetstream.us-east` (v2) → `jetstream.us-west` (v2) → `jetstream2.us-east` (v1) → `jetstream1.us-west` (v1).
Status is **LIVE**, **TEMPORARILY UNAVAILABLE** (dropped or refused, reconnecting with backoff) or **FAILED**
(every host tried with nothing received; press start to retry). The optional **replay last 30 min** passes a
microsecond `cursor`; if a host refuses that lookback it is retried live-only and the panel says so instead of
pretending it replayed. Authors are shown as their DID (Jetstream does not send handles) — the profile link
still resolves.

**Source status list in the page:** Lemmy forums **LIVE**, Bluesky live stream **LIVE/READY**, Assisted search
**LIVE (manual)**, X API **NOT CONFIGURED**, Web search (Brave/Google API) **NOT CONFIGURED**,
Facebook (direct) **NOT AVAILABLE** (no public post-search API; private groups are never touched).

### Testing the static build
```bash
cd radar && npm install     # jsdom is a devDependency for the page tests
cd radar && npm test        # 10 engine tests + 7 built-page tests (jsdom, mocked fetch + WebSocket)
python3 qa_audit.py         # site QA, TOTAL: 0
```
The built-page tests decrypt the real encrypted output (with `CF_OUT` pointing at a temp file), load it in
jsdom and check: honest paste counts, re-paste = "0 new, 1 previously seen", the bookmarklet on mock X/Reddit
markup (text + URL + author + date), `#import=` handling, Jetstream messages (only real Michigan apparel
intent becomes a lead; fan chatter and other schools never do), the host fallback → FAILED path, that the
🔄 button only calls Lemmy, and that no page errors occur. Without jsdom installed those 7 tests skip and the
original 10 still pass.
