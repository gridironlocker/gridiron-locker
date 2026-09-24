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
