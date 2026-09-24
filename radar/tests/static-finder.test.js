// End-to-end test of the built (encrypted) static Customer Finder page, loaded into jsdom
// with a mocked fetch + WebSocket. Verifies the things that must never be wrong:
//   * the paste box counts honestly (new / previously seen / low / excluded / rejected)
//   * re-pasting the same post is "previously seen", never a new lead
//   * the bookmarklet reads real X and Reddit markup (text + URL + author + date)
//   * only real Michigan apparel-intent posts from the Jetstream firehose become leads
//   * the removed sources (Reddit JSON, Bluesky searchPosts) are never called
//   * no page errors
//
// jsdom is a devDependency; if it is not installed these tests skip (the rest of the
// suite still passes) — run `npm install` in radar/ to enable them.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "../..");
const CF_CODE = "jsdom-test-code";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let JSDOM = null, VirtualConsole = null;
try {
  const jsdom = await import("jsdom");
  JSDOM = jsdom.JSDOM;
  VirtualConsole = jsdom.VirtualConsole;
} catch { /* jsdom not installed → skip below */ }
const maybe = JSDOM ? test : test.skip;

// ---------------------------------------------------------------- build + decrypt
let pageHtml = null;
function plaintextPage() {
  if (pageHtml) return pageHtml;
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cf-build-")), "index.html");
  execFileSync(process.execPath, [path.join(REPO, "radar/static-finder/build.mjs")], { cwd: REPO, env: { ...process.env, CF_CODE, CF_OUT: out }, stdio: "pipe" });
  const gate = fs.readFileSync(out, "utf-8");
  const m = gate.match(/const D=\{s:"([^"]+)",i:"([^"]+)",c:"([^"]+)",n:(\d+)\}/);
  assert.ok(m, "the built page must expose the encrypted payload");
  const buf = Buffer.from(m[3], "base64");
  const key = crypto.pbkdf2Sync(CF_CODE, Buffer.from(m[1], "base64"), Number(m[4]), 32, "sha256");
  const d = crypto.createDecipheriv("aes-256-gcm", key, Buffer.from(m[2], "base64"));
  d.setAuthTag(buf.subarray(buf.length - 16));
  pageHtml = Buffer.concat([d.update(buf.subarray(0, buf.length - 16)), d.final()]).toString("utf-8");
  return pageHtml;
}

// ---------------------------------------------------------------- jsdom helpers
class MockWebSocket {
  static instances = [];
  constructor(url) { this.url = url; this.readyState = 0; MockWebSocket.instances.push(this); setTimeout(() => this.open(), 0); }
  open() { this.readyState = 1; if (this.onopen) this.onopen({}); }
  send() { /* nothing is ever sent to Bluesky */ }
  close() { this.readyState = 3; if (this.onclose) this.onclose({ code: 1000 }); }
  emit(obj) { if (this.onmessage) this.onmessage({ data: JSON.stringify(obj) }); }
  static last() { return MockWebSocket.instances[MockWebSocket.instances.length - 1]; }
}

function finderWindow({ url = "https://gridironlocker.store/private/customer-finder/", fetchImpl } = {}) {
  MockWebSocket.instances = [];
  const errors = [], requests = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(String((e && e.message) || e)));
  const dom = new JSDOM(plaintextPage(), {
    url,
    runScripts: "dangerously",
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.addEventListener("error", (e) => errors.push(String((e.error && e.error.stack) || e.message)));
      window.addEventListener("unhandledrejection", (e) => errors.push("unhandled rejection: " + String(e.reason)));
      try { Object.defineProperty(window, "crypto", { value: globalThis.crypto, configurable: true }); } catch { /* jsdom already has a usable crypto */ }
      window.WebSocket = MockWebSocket;
      window.open = () => ({ opener: null, closed: false, focus() {} });
      window.fetch = async (u, o) => {
        requests.push(String(u));
        if (fetchImpl) return fetchImpl(String(u), o);
        return { ok: false, status: 404, json: async () => ({}) };
      };
    },
  });
  const close = () => { try { dom.window.close(); } catch { /* already gone */ } };
  return { dom, window: dom.window, errors, requests, close, store: () => JSON.parse(dom.window.localStorage.getItem("gl_customer_finder_v1") || '{"runs":[],"leads":[]}') };
}

function countsText(window, id) {
  const el = window.document.getElementById(id);
  return el ? el.textContent.replace(/\s+/g, " ").trim() : "";
}

// ---------------------------------------------------------------- 1. the page itself
maybe("built page loads in jsdom: panel, searches, statuses, no page errors", async (t) => {
  const f = finderWindow();
  t.after(f.close);
  await sleep(250);
  const doc = f.window.document;
  assert.ok(doc.getElementById("cfAssist"), "the Free discovery panel is in the page");
  assert.equal(doc.querySelectorAll("#cfa-searches .cfa-btn").length, 10, "ten recent-post searches");
  const hrefs = [...doc.querySelectorAll("#cfa-searches .cfa-btn")].map((a) => a.getAttribute("href")).join("\n");
  assert.match(hrefs, /x\.com\/search\?q=.*f=live/);
  assert.match(hrefs, /-filter%3Alinks/);
  assert.match(hrefs, /reddit\.com\/new\/$/m);
  assert.match(hrefs, /reddit\.com\/r\/uofm\/new\/$/m);
  assert.match(hrefs, /t=week/);
  assert.match(hrefs, /t=month/);
  assert.match(hrefs, /tbs=qdr%3Ad/);
  assert.match(hrefs, /tbs=qdr%3Aw/);
  assert.match(hrefs, /-site%3Aetsy\.com/);
  assert.match(hrefs, /-site%3Aamazon\.com/);
  assert.match(hrefs, /-site%3Afanatics\.com/);
  assert.match(hrefs, /facebook\.com\/search\/posts/);
  assert.match(hrefs, /threads\.net\/search/);
  assert.match(hrefs, /bsky\.app\/search/);
  const status = countsText(f.window, "cfa-status");
  assert.match(status, /Lemmy forums/, "Lemmy is listed");
  assert.match(status, /NOT CONFIGURED/, "X / web search show NOT CONFIGURED");
  assert.match(status, /NOT AVAILABLE/, "direct Facebook is not available");
  assert.match(countsText(f.window, "cfa-status"), /Bluesky live stream/);
  assert.match(doc.getElementById("cfa-bm").getAttribute("href"), /^javascript:\(function\(\)/, "bookmarklet built at runtime");
  assert.match(doc.getElementById("cfa-bm").getAttribute("href"), /gridironlocker\.store\/private\/customer-finder\//, "bookmarklet points back at this finder");
  assert.deepEqual(f.errors, [], "no page errors");
});

// ---------------------------------------------------------------- 2. paste box
maybe("paste box counts honestly, and the same post is never new twice", async (t) => {
  const f = finderWindow();
  t.after(f.close);
  await sleep(250);
  const doc = f.window.document;
  const paste = [
    "Where can I buy a Michigan hoodie for my son before Saturday? Any recommendations?",
    "https://www.reddit.com/r/uofm/comments/aaa111/where_hoodie/",
    "",
    "Go Blue!!",
    "https://www.reddit.com/r/uofm/comments/bbb222/go_blue/",
    "",
    "just chatter with no link at all",
  ].join("\n");
  doc.getElementById("cfa-paste").value = paste;
  doc.getElementById("cfa-paste-go").click();
  await sleep(300);
  let text = countsText(f.window, "cfa-paste-result");
  assert.match(text, /Pasted 3 block\(s\)/);
  assert.match(text, /1 new/);
  assert.match(text, /0 previously seen/);
  assert.match(text, /1 low-intent/);
  assert.match(text, /0 excluded/);
  assert.match(text, /1 rejected \(no link\)/);
  assert.match(text, /2 checked/);
  let db = f.store();
  assert.equal(db.leads.length, 1, "only the real Michigan apparel-intent post is stored");
  assert.equal(db.leads[0].intent, "HOT");
  assert.equal(db.leads[0].url, "https://www.reddit.com/r/uofm/comments/aaa111/where_hoodie/");
  assert.equal(db.runs[0].rejected, 1, "the link-less block is counted as rejected, not stored");

  // same three blocks again → nothing may be presented as new
  doc.getElementById("cfa-paste").value = paste;
  doc.getElementById("cfa-paste-go").click();
  await sleep(300);
  text = countsText(f.window, "cfa-paste-result");
  assert.match(text, /0 new/, "re-paste adds no leads");
  assert.match(text, /1 previously seen/);
  assert.match(text, /2 checked/);
  db = f.store();
  assert.equal(db.leads.length, 1, "still one lead in total");
  assert.equal(db.leads[0].seen_count, 2, "the duplicate is recorded as seen again");
  assert.equal(db.runs.length, 2, "each ingest is its own run");
  assert.deepEqual(f.errors, []);
});

// ---------------------------------------------------------------- 3. bookmarklet on mock X / Reddit
maybe("bookmarklet reads X and Reddit markup with text, URL, author and date", async (t) => {
  const f = finderWindow();
  t.after(f.close);
  await sleep(250);

  const xDom = new JSDOM(`<!doctype html><html><body>
    <article>
      <a href="/annarborjen"><span>Ann Arbor Jen</span></a>
      <div data-testid="tweetText">Looking for an affordable Michigan hoodie that isn't generic — any recs?</div>
      <a href="/annarborjen/status/1791234567890123456"><time datetime="2026-09-20T14:03:00.000Z">Sep 20</time></a>
    </article>
    <article>
      <div data-testid="tweetText">Go Blue!</div>
      <a href="/someone/status/1799999999999999999"><time datetime="2026-09-21T09:00:00.000Z">Sep 21</time></a>
    </article>
  </body></html>`, { url: "https://x.com/search?q=michigan+hoodie&f=live" });
  const xItems = f.window.cfExtractInPage(xDom.window.document, xDom.window.location);
  assert.equal(xItems.length, 2, "both tweets are read");
  assert.equal(xItems[0].platform, "X");
  assert.match(xItems[0].text, /affordable Michigan hoodie/);
  assert.equal(xItems[0].url, "https://x.com/annarborjen/status/1791234567890123456");
  assert.equal(xItems[0].author, "@annarborjen");
  assert.equal(xItems[0].postedAt, "2026-09-20T14:03:00.000Z");

  const redditDom = new JSDOM(`<!doctype html><html><body>
    <shreddit-post permalink="/r/uofm/comments/xyz789/need_a_hoodie/" author="blue_mom"
      created-timestamp="2026-09-22T10:00:00.000Z" post-title="Need a hoodie for game day">
      <div slot="text-body">My daughter wants a Michigan crewneck for her birthday, where can I find one that ships fast?</div>
    </shreddit-post>
    <div class="thing" data-permalink="/r/uofm/comments/old111/old_style/" data-author="maizenblue_dad">
      <div class="entry"><div class="tagline"><time datetime="2026-09-19T08:30:00.000Z">Sep 19</time></div>
        <div class="title"><a href="/r/uofm/comments/old111/old_style/">Where to buy a vintage Michigan tee?</a></div>
        <div class="usertext-body"><div class="md">Where to buy a vintage Michigan tee? Everything looks the same.</div></div>
      </div>
    </div>
  </body></html>`, { url: "https://www.reddit.com/r/uofm/new/" });
  const rItems = f.window.cfExtractInPage(redditDom.window.document, redditDom.window.location);
  assert.equal(rItems.length, 2, "shreddit-post and old-reddit .thing are both read");
  assert.equal(rItems[0].platform, "Reddit");
  assert.equal(rItems[0].url, "https://www.reddit.com/r/uofm/comments/xyz789/need_a_hoodie/");
  assert.equal(rItems[0].author, "u/blue_mom");
  assert.equal(rItems[0].postedAt, "2026-09-22T10:00:00.000Z");
  assert.match(rItems[0].text, /Michigan crewneck/);
  assert.equal(rItems[1].url, "https://www.reddit.com/r/uofm/comments/old111/old_style/");
  assert.equal(rItems[1].author, "u/maizenblue_dad");
  assert.match(rItems[1].text, /vintage Michigan tee/);

  // feeding them in is exactly what the bookmarklet does through #import=<json>
  const git = await f.window.cfIngest([...xItems, ...rItems], "Assisted search");
  assert.equal(git.counts.rejected, 0);
  assert.equal(git.counts.new_leads, 3, "the two real intent posts + the vintage tee; “Go Blue!” is low, not a lead");
  assert.equal(git.counts.low_filtered, 1);
  const leads = f.store().leads;
  assert.equal(leads.length, 3);
  const xLead = leads.find((l) => l.platform === "X");
  assert.equal(xLead.author, "@annarborjen");
  assert.equal(xLead.posted_at, "2026-09-20T14:03:00.000Z");
  assert.match(xLead.excerpt, /affordable Michigan hoodie/);
  assert.equal(xLead.url, "https://x.com/annarborjen/status/1791234567890123456");
  assert.deepEqual(f.errors, []);
});

// ---------------------------------------------------------------- 4. #import hash round trip
maybe("the finder ingests #import=<json> on load and clears the hash", async (t) => {
  const items = [{ platform: "X", author: "@jen", text: "Where can I buy a Michigan shirt for the game?", url: "https://x.com/jen/status/123", postedAt: "2026-09-23T12:00:00.000Z" }];
  const url = "https://gridironlocker.store/private/customer-finder/#import=" + encodeURIComponent(JSON.stringify(items));
  const f = finderWindow({ url });
  t.after(f.close);
  await sleep(400);
  const db = f.store();
  assert.equal(db.leads.length, 1, "hash import created the lead");
  assert.equal(db.leads[0].url, "https://x.com/jen/status/123");
  assert.equal(f.window.location.hash, "", "hash cleared so a reload does not re-import");
  assert.deepEqual(f.errors, []);
});

// ---------------------------------------------------------------- 5. Jetstream firehose
maybe("Jetstream mock messages create only real Michigan apparel-intent leads", async (t) => {
  const f = finderWindow();
  t.after(f.close);
  await sleep(250);
  const now = new Date().toISOString();
  f.window.cfLiveSetBatchMs(40);
  f.window.cfLiveStart({ replayMinutes: 30 });
  await sleep(120);
  const ws = MockWebSocket.last();
  assert.ok(ws, "the radar opened a WebSocket");
  assert.match(ws.url, /^wss:\/\/jetstream\.us-east\.bsky\.network\/xrpc\/network\.bsky\.jetstream\.subscribeEvents\?/);
  assert.match(ws.url, /collections=app\.bsky\.feed\.post/);
  assert.match(ws.url, /kinds=commit/);
  assert.match(ws.url, /cursor=\d{16}/, "30-minute replay passes a microsecond cursor");
  await sleep(30);
  assert.equal(f.window.cfLiveStatus().state, "LIVE");

  const post = (did, rkey, text, extra = {}) => ({ $type: "message", payload: { $type: "network.bsky.jetstream.subscribeEvents#commit", did, seq: 1, time: now, operation: "create", collection: "app.bsky.feed.post", rkey, record: { $type: "app.bsky.feed.post", createdAt: now, text }, ...extra } });
  ws.emit(post("did:plc:aaaa1111", "3k1", "Where can I buy a Michigan hoodie for my son before Saturday? Any recommendations?"));
  ws.emit(post("did:plc:aaaa1111", "3k2", "Go Blue!!"));
  ws.emit(post("did:plc:ccco", "3k3", "Michigan State Spartans shirt where can I buy one?"));
  ws.emit({ did: "did:plc:bbbb2222", time_us: 1790000000000000, kind: "commit", commit: { operation: "create", collection: "app.bsky.feed.post", rkey: "3k4", record: { $type: "app.bsky.feed.post", createdAt: now, text: "Looking for a vintage Michigan tee, any recommendations?" } } });
  ws.emit(post("did:plc:aaaa1111", "3k5", "great game last night", { record: { $type: "app.bsky.feed.post", createdAt: now, text: "great game last night" } }));
  ws.emit(post("did:plc:aaaa1111", "3k6", "Michigan shirt now available in my shop, use code BLUE10", { operation: "update" }));
  await sleep(400);

  const s = f.window.cfLiveStatus();
  assert.equal(s.postsChecked, 5, "only created posts are counted");
  assert.equal(s.matched, 3, "prefilter kept the team+apparel posts (the Michigan State one is dropped by the classifier, not the prefilter)");
  let db = f.store();
  assert.equal(db.leads.length, 2, "only the two real intent posts became leads");
  assert.ok(db.leads.every((l) => /Michigan|Michigan hoodie|vintage Michigan tee/.test(l.excerpt)));
  assert.ok(!db.leads.some((l) => /Go Blue/.test(l.excerpt)), "fan chatter is never a lead");
  assert.ok(db.leads.every((l) => l.platform === "Bluesky" && /^https:\/\/bsky\.app\/profile\/did:plc:[a-z0-9]+\/post\/3k\d$/.test(l.url)));
  assert.ok(db.leads.every((l) => l.posted_at), "each lead carries its post date");
  const run = db.runs[0];
  assert.equal(run.new_leads, 2);
  assert.equal(run.excluded, 1, "the Michigan State post is excluded");
  assert.equal(run.rejected, 0);
  assert.equal(run.live, true, "the stream run stays open while streaming");
  assert.equal(run.trigger, "Bluesky live stream");
  const st = await f.window.localApi("/state");
  assert.equal(st.running, null, "a live radar run never puts the dashboard in a fake “searching” state");
  assert.equal(f.window.document.getElementById("find").disabled, false, "the 🔄 button stays usable while the radar streams");

  // the same firehose events again must never look new
  ws.emit(post("did:plc:aaaa1111", "3k1", "Where can I buy a Michigan hoodie for my son before Saturday? Any recommendations?"));
  await sleep(250);
  db = f.store();
  assert.equal(db.leads.length, 2, "no duplicate lead");
  assert.equal(db.runs[0].duplicates, 1, "counted as previously seen");

  const stopped = f.window.cfLiveStop();
  await sleep(60);
  assert.notEqual(stopped.state, "LIVE");
  const closed = f.store().runs[0];
  assert.equal(closed.live, false);
  assert.equal(closed.status, "success");
  assert.match(closed.message, /posts checked/);
  assert.deepEqual(f.errors, []);
});

maybe("Jetstream failure falls back through the hosts, then reports FAILED", async (t) => {
  class DeadSocket {
    static urls = [];
    constructor(url) { DeadSocket.urls.push(url); setTimeout(() => this.onclose && this.onclose({ code: 1006 }), 0); }
    send() {}
    close() {}
  }
  const f = finderWindow();
  t.after(f.close);
  await sleep(250);
  f.window.WebSocket = DeadSocket;
  f.window.cfLiveSetBatchMs(40);
  f.window.cfLiveStart({ replayMinutes: 0 });
  await sleep(4000);
  assert.equal(f.window.cfLiveStatus().state, "FAILED");
  assert.equal(DeadSocket.urls.length, 4, "every host is tried once");
  assert.ok(DeadSocket.urls[0].includes("jetstream.us-east"));
  assert.ok(DeadSocket.urls.some((u) => u.includes("jetstream2.us-east") && u.includes("wantedCollections=")), "legacy v1 host from the brief is a fallback");
  assert.equal(f.store().leads.length, 0, "a failed stream adds no leads");
  assert.equal(f.store().runs[0].status, "error");
  assert.deepEqual(f.errors, []);
});

// ---------------------------------------------------------------- 6. the automatic path
maybe("the 🔄 button only calls Lemmy (Reddit JSON / Bluesky searchPosts are gone) and stores real leads", async (t) => {
  const now = new Date().toISOString();
  const fetchImpl = async (url) => {
    if (url.includes("lemmy.world")) {
      return { ok: true, status: 200, json: async () => ({ posts: [{ creator: { name: "maize_fan", actor_id: "https://lemmy.world/u/maize_fan" }, post: { name: "Where to buy a Michigan sweatshirt in Ann Arbor?", body: "Looking for a Michigan sweatshirt, any recommendations?", ap_id: "https://lemmy.world/post/123456", published: now } }], comments: [] }) };
    }
    return { ok: false, status: 403, json: async () => ({}) };
  };
  const f = finderWindow({ fetchImpl });
  t.after(f.close);
  await sleep(250);
  f.window.document.getElementById("find").click();
  for (let i = 0; i < 40 && !(f.store().runs[0] && f.store().runs[0].status !== "running"); i++) await sleep(250);
  const db = f.store();
  assert.equal(db.leads.length, 1, "the Lemmy post became a lead");
  assert.equal(db.leads[0].platform, "Lemmy");
  assert.equal(db.runs[0].status, "success");
  assert.deepEqual(db.runs[0].sources_ok.map((s) => s.source), ["Lemmy forums"]);
  assert.ok(!f.requests.some((u) => /reddit\.com|searchPosts|api\.bsky|public\.api/.test(u)), "no blocked source is contacted: " + f.requests.join(", "));
  assert.deepEqual(f.errors, []);
});
