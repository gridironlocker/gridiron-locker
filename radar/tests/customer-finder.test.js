import { test } from "node:test";
import assert from "node:assert/strict";
import { classify } from "../lib/customer-finder/classifier.js";
import { fingerprint, urlKey, canonicalUrl } from "../lib/customer-finder/dedupe.js";
import { matchProduct } from "../lib/customer-finder/products.js";
import { suggestResponse } from "../lib/customer-finder/responder.js";
import { openStore, listLeads, getRun } from "../lib/customer-finder/store.js";
import { startRun, redact, UNAVAILABLE_MSG } from "../lib/customer-finder/engine.js";

const C = (text, extra = {}) => classify({ text, platform: "Reddit", url: "https://www.reddit.com/r/x/comments/abc/t/", author: "u/fan1", ...extra });

test("brief examples classify correctly", () => {
  assert.equal(C("Where can I find a Michigan shirt like this?").intent, "HOT");
  assert.equal(C("Looking for an affordable Michigan hoodie.").intent, "HOT");
  assert.equal(C("Does anyone know where to buy this Michigan sweatshirt?").intent, "HOT");
  assert.equal(C("I need a new Michigan game-day shirt.").intent, "WARM");
  assert.equal(C("Go Blue!").intent, "LOW");
});

test("sellers, media, other schools are excluded", () => {
  assert.equal(C("New drop! Michigan hoodies available now, use code BLUE10").intent, "EXCLUDED");
  assert.equal(C("Where can I buy a Michigan shirt?", { author: "WolverineApparelCo" }).intent, "EXCLUDED");
  assert.equal(C("Where can I buy a Michigan State Spartans shirt?").intent, "EXCLUDED");
  assert.equal(C("Where can I buy a Michigan shirt?", { url: "https://www.etsy.com/listing/1" }).intent, "EXCLUDED");
  assert.equal(C("Michigan beat Ohio State again, what a game").intent, "LOW");
});

test("dedupe key is stable across tracking params / url variants", () => {
  const a = { platform: "Reddit", url: "https://www.reddit.com/r/uofm/comments/abc123/need_shirt/?utm_source=share", author: "u/x", text: "Need a shirt" };
  const b = { ...a, url: "https://old.reddit.com/r/uofm/comments/abc123/need_shirt" };
  assert.equal(fingerprint(a), fingerprint(b));
  assert.equal(urlKey(a), urlKey(b));
  assert.equal(canonicalUrl("https://twitter.com/a/status/123?s=20"), "x.com/status/123");
});

test("product matching flags hoodie gap and never pitches a tee instead", () => {
  const m = matchProduct("michigan", { apparelType: "hoodie", attributes: [] });
  assert.equal(m.gap, true);
  assert.equal(m.products.length, 0);
  const r = suggestResponse({ intent: "HOT", wants: { apparelType: "hoodie" }, match: m, platform: "Reddit", leadId: "lead_x" });
  assert.equal(r.text, null);
  const v = matchProduct("michigan", { apparelType: "t-shirt", attributes: ["vintage/retro"] });
  assert.equal(v.gap, false);
  assert.match(v.products[0].theme, /retro/);
  const reply = suggestResponse({ intent: "HOT", wants: { apparelType: "t-shirt", attributes: ["vintage/retro"] }, match: v, platform: "Reddit", leadId: "lead_y" });
  assert.match(reply.text, /disclosure|help run|part of the small team/i);
  assert.doesNotMatch(reply.text, /check out my store/i);
});

test("privacy: emails and phones are redacted", () => {
  assert.equal(redact("mail me jo@example.com or 313-555-1212"), "mail me [email removed] or [phone removed]");
});

function fakeSource(payloadFn) {
  return { id: "fake", label: "Fake", status: () => ({ enabled: true, mode: "test" }), search: async () => payloadFn() };
}

test("unavailable when every source fails — no leads added", async () => {
  const db = openStore(":memory:");
  const bad = { id: "b", label: "Bad", status: () => ({ enabled: true }), search: async () => { throw new Error("network down"); } };
  const { run, promise } = startRun(db, { sources: [bad] });
  await promise;
  const r = getRun(db, run.id);
  assert.equal(r.status, "unavailable");
  assert.equal(r.message, UNAVAILABLE_MSG);
  assert.equal(r.new_leads, 0);
  assert.equal(listLeads(db).length, 0);
});

test("second search marks same conversation as previously seen", async () => {
  const db = openStore(":memory:");
  const now = new Date().toISOString();
  const posts = [
    { platform: "Reddit", author: "u/momof3", url: "https://www.reddit.com/r/uofm/comments/aaa/x/", text: "Where can I buy an affordable Michigan shirt for my son before Saturday?", postedAt: now, query: "q" },
    { platform: "Reddit", author: "u/fan", url: "https://www.reddit.com/r/uofm/comments/bbb/x/", text: "Go Blue!", postedAt: now, query: "q" },
  ];
  let a = startRun(db, { sources: [fakeSource(() => posts)] }); await a.promise;
  let r1 = getRun(db, a.run.id);
  assert.equal(r1.new_leads, 1); assert.equal(r1.low_filtered, 1); assert.equal(r1.status, "success");
  const extra = { platform: "Reddit", author: "u/newfan", url: "https://www.reddit.com/r/uofm/comments/ccc/x/", text: "Looking for a vintage Michigan tee, any recommendations?", postedAt: now, query: "q" };
  let b = startRun(db, { sources: [fakeSource(() => [...posts, extra])] }); await b.promise;
  const r2 = getRun(db, b.run.id);
  assert.equal(r2.new_leads, 1); assert.equal(r2.duplicates, 1);
  assert.equal(listLeads(db, { runId: b.run.id })[0].author, "u/newfan");
  assert.equal(listLeads(db).length, 2);
});

test("old posts are not presented as fresh", async () => {
  const db = openStore(":memory:");
  const old = { platform: "Reddit", author: "u/a", url: "https://www.reddit.com/r/uofm/comments/zzz/x/", text: "Where can I buy a Michigan hoodie?", postedAt: "2024-01-01T00:00:00Z" };
  const s = startRun(db, { sources: [fakeSource(() => [old])] }); await s.promise;
  assert.equal(getRun(db, s.run.id).new_leads, 0);
});

test("intent must be about apparel, not tickets etc.", () => {
  assert.equal(C("Looking for tickets to the Michigan game this weekend, any recommendations? Will be wearing my old shirt lol").intent, "LOW");
  assert.equal(C("Any recommendations for a Michigan hoodie?").intent, "HOT");
  assert.equal(C("Love this Michigan hoodie. Where did you get it?").intent, "HOT");
  assert.equal(C("Just got my new Michigan hoodie, love it! Go Blue").intent, "LOW");
  assert.equal(C("My daughter wants a Michigan crewneck for her birthday").intent, "WARM");
});

test("live connectors parse documented API shapes (mocked fetch)", async () => {
  const { SOURCES } = await import("../lib/customer-finder/sources.js");
  process.env.X_BEARER_TOKEN = "t"; process.env.BRAVE_SEARCH_API_KEY = "k"; process.env.CF_WEB_QUERIES = "1";
  const now = Math.floor(Date.now() / 1000);
  const fetchImpl = async (url) => {
    const u = String(url); let body = {};
    if (u.includes("reddit.com")) body = { data: { children: [{ data: { author: "blue_mom", title: "Where can I buy a Michigan hoodie for my son?", selftext: "", permalink: "/r/uofm/comments/q1/where/", created_utc: now } }] } };
    else if (u.includes("api.x.com")) body = { data: [{ id: "99", author_id: "1", text: "anyone know where to buy a michigan sweatshirt?", created_at: new Date().toISOString() }, { id: "100", author_id: "2", text: "where can i buy michigan shirt", created_at: new Date().toISOString() }], includes: { users: [{ id: "1", username: "annarborjen", public_metrics: { followers_count: 200 } }, { id: "2", username: "bigsportsguy", public_metrics: { followers_count: 900000 } }] } };
    else if (u.includes("bsky")) body = { posts: [{ uri: "at://did:plc:abc/app.bsky.feed.post/3kx", author: { handle: "fan.bsky.social" }, record: { text: "looking for a michigan tee", createdAt: new Date().toISOString() } }] };
    else if (u.includes("brave")) body = { discussions: { results: [{ url: "https://www.mgoblog.com/forum/shirt", title: "Where to buy a Michigan shirt?", description: "Looking for a non-generic Michigan shirt" }] }, web: { results: [] } };
    else if (u.includes("lemmy")) body = { posts: [], comments: [] };
    return { ok: true, status: 200, json: async () => body };
  };
  const team = (await import("../lib/customer-finder/teams.js")).getTeam("michigan");
  const byId = Object.fromEntries(SOURCES.map((s) => [s.id, s]));
  const r = await byId.reddit.search(team, { fetchImpl });
  assert.equal(r[0].author, "u/blue_mom"); assert.match(r[0].url, /reddit\.com\/r\/uofm\/comments\/q1/);
  const x = await byId.x.search(team, { fetchImpl });
  assert.equal(x.length, 1, "influencer filtered"); assert.equal(x[0].url, "https://x.com/annarborjen/status/99");
  const b = await byId.bluesky.search(team, { fetchImpl });
  assert.equal(b[0].url, "https://bsky.app/profile/fan.bsky.social/post/3kx");
  const w = await byId.brave.search(team, { fetchImpl });
  assert.match(w[0].platform, /Forum/);
  delete process.env.X_BEARER_TOKEN; delete process.env.BRAVE_SEARCH_API_KEY;
});
