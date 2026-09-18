#!/usr/bin/env python3
"""Deep audit of site/ - the gaps qa_audit.py structurally cannot cover.

qa_audit.py validates site/ against build.ALL, and build.ALL is derived from the
same data/ files the pages are built from. That makes it excellent at proving the
site faithfully renders its inputs, and blind to five whole classes of problem:

  1. the inputs themselves are wrong (bad crawl data, stale season facts)
  2. files are deployed that should never be publicly served
  3. a written policy contradicts the shipped output
  4. client-side behaviour that fails silently (forms, opaque fetches)
  5. asset weight / delivery efficiency

Run it read-only:

    python3 qa_deep.py            # human-readable report, exit 1 on any CRITICAL

Companion to qa_audit.py (static, off-disk) and qa_http.py (live HTTP crawl).
Findings introduced by SITE-AUDIT-2026-09-18.md are tagged with their ID.
"""
import base64
import collections
import glob
import html as htmllib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402

FIND = collections.defaultdict(list)
SEV = {}


_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def add(sev, tag, msg):
    FIND[tag].append(msg)
    # a tag bundles one issue + its evidence lines; keep its WORST severity,
    # not the last one appended
    if tag not in SEV or _RANK[sev] < _RANK[SEV[tag]]:
        SEV[tag] = sev


def txt(path, enc="utf-8"):
    with open(path, encoding=enc, errors="replace") as fh:
        return fh.read()


def visible(t):
    b = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", t, flags=re.S)
    return htmllib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b))).strip()


PAGES = {}
for dp, dn, fn in os.walk(SITE):
    dn[:] = [d for d in dn if d != ".git"]
    for f in fn:
        if f.endswith(".html"):
            rel = os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, "/")
            PAGES[rel] = txt(os.path.join(dp, f))
PUBLIC = {r: t for r, t in PAGES.items()
          if not r.startswith(("ops/", "marketing/"))}
LIVE = {i["slug"]: i for i in build.ALL}
STUBS = set(build.retired_slugs())

# ============================================================ C1 internal files
# robots.txt Disallow + noindex are NOT access control. GitHub Pages serves
# everything under site/, so anything copied here is publicly downloadable.
INTERNAL_BAD = (".py", ".sh", ".md", ".csv", ".json", ".txt")
leaked = []
for d in ("marketing", "ops"):
    for p in sorted(glob.glob(os.path.join(SITE, d, "**", "*"), recursive=True)):
        if os.path.isfile(p) and p.endswith(INTERNAL_BAD):
            leaked.append("/" + os.path.relpath(p, SITE).replace(os.sep, "/"))
if leaked:
    add("CRITICAL", "internal-exposure",
        f"{len(leaked)} internal source/data files are deployed and publicly served "
        f"(robots.txt Disallow is not auth):")
    for u in leaked:
        FIND["internal-exposure"].append("    " + u)
# HTML dashboards are a deliberate product decision; the source files are not.
add("CRITICAL", "internal-exposure-src",
    "sync_marketing()/sync_ops() use shutil.copytree of the whole tree - allowlist "
    "the two dashboard HTML files instead (src/build.py:4802, :4821)")

# ================================================== C2 forbidden design terms
# DESIGN-BLUEPRINT.md §2: never a player's face/photo, surname on the chest,
# jersey number, press photography, OR a team logo/wordmark/helmet mark - in
# artwork, title, alt text OR ad copy. §7 makes it a shipping gate. Imported
# partner material never went through it, so the shipped site violates the
# table the repo wrote for itself.
#
# (a) Official team marks deployed as UI icons. This check is by filename
# convention; visual inspection of all four on 2026-09-18 confirmed they are
# reproductions of the registered marks (Browns Dawg Pound bulldog + EST 1946
# wordmark, Packers G-oval, Cowboys star roundel, Michigan block M with the
# (R) symbol visible). They are served on /collections/ with empty alt.
for rel, t in PUBLIC.items():
    for u in set(re.findall(r'src="[^"]*?([a-z0-9-]*logo[a-z0-9]*)\.(?:webp|png|jpg|svg)', t, re.I)):
        if re.search(r"(browns|packers|green-bay|greenbay|dallas|cowboys|michigan|gl-|gridiron)", u, re.I) \
           and not re.search(r"gridiron|gl-", u, re.I):
            add("CRITICAL", "design-law",
                f"{rel}: <img> loads /img/{u}.* - a reproduction of a registered team "
                f"mark used as a UI icon (DESIGN-BLUEPRINT §2 row: 'Team logos, "
                f"wordmarks, helmet marks | Directly claimed IP'), with empty alt")
# (b) Hero banners whose garments depict the helmet/oval/star marks. Filename
# convention + visual inspection; these are the LCP element on / and the four
# collection pages, i.e. the most-viewed images on the site.
heros = {}
for rel, t in PUBLIC.items():
    for u in set(re.findall(r'src="[^"]*?(hero-(?:home|cleveland|greenbay|dallas|michigan))\.', t)):
        heros.setdefault(u, rel)
for u, rel in sorted(heros.items()):
    add("CRITICAL", "design-law",
        f"hero banner /img/{u}.* (LCP on {rel}) shows garments printed with the "
        f"official helmet/oval/star marks - the homepage hero depicts three NFL "
        f"clubs' registered marks on merchandise")
try:
    people = json.load(open(os.path.join(ROOT, "data", "people.json")))
    SURNAMES = {p["name"].split()[-1] for p in people.get("people", [])}
    FIRSTS = {p["name"].split()[0] for p in people.get("people", [])}
except Exception:
    SURNAMES, FIRSTS = set(), set()
SURNAMES = {s for s in SURNAMES if len(s) > 3 and s.lower() not in ("love",)} | {"Love"}
breach = []
for s, i in LIVE.items():
    t = PAGES.get(f"shop/{s}/index.html", "")
    title = re.search(r"<title>(.*?)</title>", t, re.S)
    title = htmllib.unescape(title.group(1)) if title else ""
    name, art = i["name"], (i.get("art") or "")
    kws = " ".join(i.get("kw") or [])
    hits = set()
    for w in SURNAMES | FIRSTS:
        if re.search(r"\b%s\b" % re.escape(w), f"{name} {art} {kws} {title}", re.I):
            hits.add(w)
    if re.search(r"\b\d{1,2}\b", name) and not re.search(r"\b(18|19|20)\d\d\b|est\.?", name, re.I):
        hits.add("jersey-number")
    if re.search(r"action photo|player photo|press photo|portrait of", f"{art} {title}", re.I):
        hits.add("player-PHOTO")
    if hits:
        breach.append((s, name, sorted(hits)))
if breach:
    add("CRITICAL", "design-law",
        f"{len(breach)} live products breach DESIGN-BLUEPRINT §2 "
        f"(no face / no surname / no number / no press photography):")
    for s, n, h in breach:
        FIND["design-law"].append(f"    /shop/{s}/  {n!r}  -> {h}")

# ============================================ C3 analytics vs privacy policy
ga = set()
for rel, t in PUBLIC.items():
    ga |= set(re.findall(r"gtag/js\?id=(G-[A-Z0-9]+|UA-[0-9-]+|AW-[0-9]+)", t))
    ga |= set(re.findall(r"G-[A-Z0-9]{8,}", t))
pol = PUBLIC.get("privacy/index.html", "")
polv = visible(pol)
if ga:
    if re.search(r"privacy-respecting analytics", polv, re.I):
        add("CRITICAL", "privacy",
            f"/privacy/ claims 'privacy-respecting analytics' but the site loads "
            f"{sorted(ga)} on every page")
    if re.search(r"no advertising cookies are set by this site", polv, re.I):
        add("CRITICAL", "privacy",
            "/privacy/ claims 'No advertising cookies are set by this site' - GA4 "
            "sets first-party _ga cookies on this origin")
    if re.search(r"aggregate data only", polv, re.I):
        add("CRITICAL", "privacy",
            "/privacy/ claims 'aggregate data only' - app.js fires event-level hits "
            "(colorway_interaction, custom_design_submit, newsletter_signup)")
    if not re.search(r"google analytics|gtag|GA4", polv, re.I):
        add("CRITICAL", "privacy", "/privacy/ never names Google Analytics")
if not re.search(r"consent|cookie banner|accept all|cookieyes|onetrust|cookiebot",
                 " ".join(PUBLIC.values()), re.I):
    add("CRITICAL", "privacy",
        "no consent mechanism anywhere, despite 'worldwide shipping' targeting "
        "EEA/UK buyers (GDPR/ePrivacy)")

# ========================================================= C4 form fragility
for rel, t in PUBLIC.items():
    for m in re.finditer(r"<form\b[^>]*>", t):
        tag = m.group(0)
        if 'method="POST"' in tag.upper() or "method='POST'" in tag.lower():
            if not re.search(r"\baction=", tag, re.I):
                add("CRITICAL", "forms",
                    f"{rel}: POST form with no action attribute - action is injected "
                    f"by JS, so without JS it submits to the current URL and the "
                    f"message is lost: {tag[:90]}")
            if re.search(r"novalidate", tag, re.I):
                add("HIGH", "forms", f"{rel}: form is novalidate - all validation is JS-only")
jsf = os.path.join(SITE, "assets", "app.js")
js = txt(jsf) if os.path.exists(jsf) else ""
if js:
    if "no-cors" in js:
        add("CRITICAL", "forms",
            f"assets/app.js: {js.count('no-cors')} fetch(es) use mode:'no-cors' - the "
            f"response is opaque, so HTTP 4xx/5xx cannot be detected and the success "
            f"message is shown even when the submission was rejected")
    for m in re.finditer(r"setTimeout\(function\(\)\{if\(!\w+\)\{\}\},\d+\)", js):
        add("CRITICAL", "forms",
            f"assets/app.js: dead timeout guard {m.group(0)} - empty body, so the "
            f"intended mailto fallback never fires")
    if re.search(r'_captcha"?\s*value="false"', " ".join(PUBLIC.values())):
        add("MEDIUM", "forms", "FormSubmit _captcha is disabled on a public endpoint")
b64 = []
if os.path.exists(jsf):
    b64 = re.findall(r'CUSTOM_EMAIL\s*=\s*"([A-Za-z0-9+/=]{12,})"', js)
for tok in set(b64):
    try:
        dec = base64.b64decode(tok).decode()
    except Exception:
        continue
    if "@" in dec:
        add("MEDIUM", "forms",
            f"contact address is base64-'obfuscated' but trivially reversible, and is "
            f"a personal mailbox: {dec}. Base64 is encoding, not anti-harvesting.")

# ============================================ H1 season opener vs headline
try:
    import collections_data as CD
    for k, v in getattr(CD, "SEASON", {}).items():
        op, hl = v.get("opener", ""), v.get("headline", "")
        d_op = re.findall(r"Sept (\d+)", op)
        d_hl = re.findall(r"Sept (\d+)", hl)
        if d_op and d_hl and d_op[0] != d_hl[0]:
            add("HIGH", "season",
                f"{k}: card label says Sept {d_op[0]} ({op!r}) but the headline says "
                f"Sept {d_hl[0]} ({hl!r}) - one card, two different games")
        kd = re.match(r"(\d{4}-\d{2}-\d{2})", v.get("kickoff", ""))
        if kd and d_op and kd.group(1) != f"2026-09-{int(d_op[0]):02d}":
            add("MEDIUM", "season",
                f"{k}: kickoff {kd.group(1)} disagrees with the label 'Sept {d_op[0]}'")
except Exception as e:
    print(f"  (season check skipped: {e})")
bsrc = txt(os.path.join(ROOT, "src", "build.py"))
hard = [bsrc[:m.start()].count("\n") + 1
        for m in re.finditer(r"(?:Sept|September)\s+\d+", bsrc)]
if hard:
    add("HIGH", "season",
        f"{len(hard)} hard-coded season dates in src/build.py (lines {hard[:10]}...) "
        f"outside data/collections_data.SEASON - they cannot be updated by refreshing "
        f"the data and will drift every week")

# ================================================= H2 unverified promo codes
# Only explicit promo-code phrasing. A loose "UPPERCASE word near 'checkout'"
# match produces dozens of false positives from product slogans (LOVE, DAWG,
# SUNDAY FUNDAY) and drowns the one real finding.
PROMO = re.compile(
    r"\b(?:use|enter|apply|with)?\s*(?:promo|discount|coupon)?\s*code[\s:]+"
    r"([A-Z][A-Z0-9]{2,14})\b", re.I)
seen_promo = set()
for rel, t in PUBLIC.items():
    v = visible(t)
    for m in PROMO.finditer(v):
        code = m.group(1).upper()
        if code in ("USE", "CODE", "OFF", "NFL", "NCAA", "SNF", "EST", "XML",
                    "SHOP", "SAVE", "YOUR", "ORDER", "AT", "THE", "AND"):
            continue
        if not re.search(r"\d", code) and len(code) > 8:
            continue                      # a word, not a code
        if (rel, code) in seen_promo:
            continue
        seen_promo.add((rel, code))
        add("HIGH", "promo",
            f"{rel}: advertises discount code {code!r} redeemable 'at checkout' - but "
            f"checkout happens on Mayzing/Viralstyle, not on this site. Verify the code "
            f"exists in the partner cart, or the claim cannot be honoured.")

# ================================================ H3 pinterest feed accuracy
csv_p = os.path.join(SITE, "marketing", "pinterest_feed.csv")
if os.path.exists(csv_p):
    import csv as _csv
    rows = list(_csv.DictReader(open(csv_p, encoding="utf-8")))
    ext = sum(1 for r in rows if "gridironlocker.store" not in (r.get("link") or ""))
    dead = []
    for r in rows:
        m = re.search(r"viralstyle\.com/[^/]+/([^/?#]+)", r.get("link") or "") or \
            re.search(r"/shop/([^/]+)/?", r.get("link") or "")
        if m and m.group(1) not in LIVE:
            dead.append(m.group(1))
    sz = sum(1 for r in rows if "S-3XL" in str(r))
    if rows:
        add("HIGH", "feed-csv",
            f"marketing/pinterest_feed.csv is publicly served and {ext}/{len(rows)} rows "
            f"link off-site (to the supplier, bypassing the storefront); "
            f"{len(dead)}/{len(rows)} point at designs with no live page; "
            f"{sz}/{len(rows)} claim 'S-3XL' though 37 catalogue products are S-5XL")

# ================================================ H4 hero weight / responsive
nohero = 0
for p in sorted(glob.glob(os.path.join(SITE, "img", "*"))):
    if os.path.getsize(p) > 200_000 and not p.endswith((".webp", ".avif")):
        add("HIGH", "assets",
            f"{os.path.getsize(p)//1024} KB unoptimised {os.path.splitext(p)[1]} "
            f"at /img/{os.path.basename(p)} - hero/LCP asset")
allhtml = " ".join(PUBLIC.values())
if "srcset" not in allhtml:
    add("HIGH", "assets",
        "0 srcset / 0 sizes / 0 <picture> site-wide - a 375px phone downloads the same "
        "2048px hero as a desktop. Biggest single lever on mobile LCP.")
css = txt(os.path.join(SITE, "assets", "style.css"))
if len(css) > 60_000 and "\n" in css:
    add("MEDIUM", "assets",
        f"render-blocking style.css is {len(css)//1024} KB and unminified")
if re.search(r'fonts\.(googleapis|gstatic)\.com', allhtml):
    add("MEDIUM", "assets",
        "third-party Google Fonts origins - a render-blocking stylesheet plus extra "
        "DNS/TLS on first paint; self-host with font-display:swap")

# ================================================ H5 silently dropped drops
ld = os.path.join(ROOT, "data", "live_drops.json")
if os.path.exists(ld):
    d = json.load(open(ld, encoding="utf-8"))
    items = d.get("drops") or d.get("items") or []
    slugs = [x.get("slug") for x in items if isinstance(x, dict)]
    missing = [s for s in slugs if s and s not in LIVE]
    dp = PAGES.get("drops/index.html", "")
    cards = len(re.findall(r'class="[^"]*drop[^"]*card|class="[^"]*card[^"]*drop', dp))
    if missing:
        add("HIGH", "drops",
            f"/drops/ is fed {len(slugs)} designs but {len(missing)} have no published "
            f"page and are discarded silently: {missing[:8]}")

# ============================================== M1 brand-safety blocklist
ADULT = ["milf", "fuck", "shit", "bitch", "dick", "boob", "porn", "sexy"]
for s, i in LIVE.items():
    hay = (s + " " + i["name"]).lower()
    for w in ADULT:
        if w in hay:
            add("MEDIUM", "brand-safety",
                f"/shop/{s}/ ({i['name']!r}) contains {w!r} - indexed, in the sitemap "
                f"and linked from /search/. Domain-level adult filters (Google "
                f"Shopping, Meta catalogue, Pinterest, processor review) will catch it.")

# ================================================== M2 duplicate designs
def normname(n):
    n = n.lower()
    n = re.sub(r"\b(tee|t-shirt|tshirt|shirt|hoodie|sweatshirt|crewneck|long sleeve|"
               r"mug|beanie|hat|tank)\b", " ", n)
    n = re.sub(r"\b(limited edition|limited|vintage|classic|retro|women's|womens|"
               r"men's|mens)\b", " ", n)
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


by_title = collections.defaultdict(list)
by_norm = collections.defaultdict(list)
for s, i in LIVE.items():
    by_title[i["name"].strip().lower()].append(s)
    k = normname(i["name"])
    if k:
        by_norm[k].append((s, i["name"]))
for t, ss in sorted(by_title.items()):
    if len(ss) > 1:
        add("MEDIUM", "duplicates",
            f"IDENTICAL product name {t!r} on {len(ss)} indexable URLs: "
            + ", ".join(f"/shop/{x}/" for x in ss)
            + " - two SERP results with the same title, competing for one query")
fams = 0
for k, v in sorted(by_norm.items()):
    if len(v) > 1:
        fams += 1
        add("MEDIUM", "duplicates",
            f"near-duplicate design {k!r}: "
            + "; ".join(f"{n} (/shop/{s}/)" for s, n in v))

# ================================================== M3 slug hygiene
TRUNC = re.compile(r"-(f|sty|t-sh|sh|shi|shi-1|st|s|te|gif|fan|famil|long|copy)$")
for s in sorted(LIVE):
    if TRUNC.search(s):
        add("MEDIUM", "slugs",
            f"truncated/CMS-suffixed slug /shop/{s}/ ({LIVE[s]['name']!r})")
    if re.search(r"(?:^|-)([a-z])-(?:[a-z]-){2,}", s):
        add("MEDIUM", "slugs",
            f"letter-exploded slug /shop/{s}/ ({LIVE[s]['name']!r})")
    if len(s) > 45:
        add("LOW", "slugs", f"over-long slug ({len(s)} chars) /shop/{s}/")
for bad, good in (("awar", "aware"), ("dwag", "dawg")):
    for s in sorted(LIVE):
        if bad in s:
            add("MEDIUM", "slugs",
                f"misspelled slug /shop/{s}/ ({bad!r} -> {good!r}). NOTE: the typo "
                f"comes from the partner campaign data, so check whether it is printed "
                f"on the garment before 'fixing' the artwork text.")

# ================================================ M4 boilerplate copy
BOILER = ["that is the brief, not a moodboard", "the printed line stays",
          "with a drink in the other hand", "stays on that side of the argument",
          "do more work than a paragraph ever will", "names a feeling"]
counts = collections.Counter()
for rel, t in PUBLIC.items():
    if not rel.startswith("shop/"):
        continue
    v = visible(t).lower()
    for b in BOILER:
        if b in v:
            counts[b] += 1
for b, n in counts.most_common():
    if n > 10:
        add("MEDIUM", "copy",
            f"identical sentence {b!r} on {n} indexable product pages - thin/duplicate "
            f"content signal")
if any("moodboard" in b or "brief" in b for b in counts):
    add("MEDIUM", "copy",
        "internal design-agency jargon ('brief', 'moodboard') appears in "
        "customer-facing product copy")

# ================================================ M5 feed validity
feed = os.path.join(SITE, "feed.xml")
if os.path.exists(feed):
    f = txt(feed)
    lbd = re.search(r"<lastBuildDate>(.*?)</lastBuildDate>", f)
    if lbd and not re.search(r"[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4}", lbd.group(1)):
        add("MEDIUM", "feed",
            f"<lastBuildDate>{lbd.group(1)}</lastBuildDate> is not RFC 822 - RSS 2.0 "
            f"requires e.g. 'Thu, 18 Sep 2026 00:00:00 GMT'; many parsers reject it")
    items = re.findall(r"<item>(.*?)</item>", f, re.S)
    if items and not any("<pubDate>" in i for i in items):
        add("MEDIUM", "feed",
            f"0/{len(items)} items carry <pubDate> - readers cannot order or date them")
    guids = re.findall(r"<guid[^>]*>(.*?)</guid>", f)
    if guids and all(re.search(r"#\d{4}-\d{2}-\d{2}$", g) for g in guids):
        add("MEDIUM", "feed",
            "every <guid> embeds today's date, so all items look permanently new to "
            "every consumer - aggregators drop feeds that do this")

# ================================================ M6 orphan files
written = set()
orphans = []
for dp, dn, fn in os.walk(SITE):
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), SITE).replace(os.sep, "/")
        if "/" in rel and re.match(r"^(google|bing|a7f3c19b)[a-z0-9]*\.(html|txt|xml)$", f):
            orphans.append("/" + rel)
for o in orphans:
    add("MEDIUM", "orphans",
        f"{o} - verification file stranded inside a content directory; build.py writes "
        f"only the root copy and prunes orphans from site/img/ alone, so it persists "
        f"forever (no title, no meta, not in the sitemap)")

# ================================================ M7 policy contradictions
board = PAGES.get("ops/board/index.html", "")
bv = visible(board)
if "never appear on art, on a public page" in bv:
    # Scope to the Fan Trend Index: it publishes these names as SCORED rows with
    # 0-100 values and mention counts. Prose that explains a player was retired
    # (the legacy_note) is legitimate and deliberately not flagged.
    fti = visible(PUBLIC.get("fan-trend-index/index.html", ""))
    scored = sorted({w for w in (SURNAMES | FIRSTS)
                     if len(w) > 3 and re.search(r"\b%s\b\s+\d{1,3}\b" % re.escape(w), fti)})
    if scored:
        add("LOW", "policy",
            f"ops/board says tracked names 'never appear on art, on a public page, or "
            f"in a caption', but /fan-trend-index/ publishes them as scored rows: "
            f"{scored}")
try:
    ppl = json.load(open(os.path.join(ROOT, "data", "people.json")))
    if "must not be used or mentioned" in ppl.get("rules", ""):
        fti = visible(PUBLIC.get("fan-trend-index/index.html", ""))
        for p in ppl.get("people", []):
            # only a SCORED row counts; explanatory prose about a retirement is fine
            if p.get("status") == "current":
                continue
            if re.search(r"\b%s\b\s+\d{1,3}\b" % re.escape(p["name"]), fti):
                add("LOW", "policy",
                    f"people.json says non-current people must not be promoted, but the "
                    f"public trend index carries a scored row for {p['name']!r} "
                    f"(status={p.get('status')!r})")
except Exception:
    pass

# ================================================ M8 hot-linked partner images
remote = collections.Counter()
for rel, t in PUBLIC.items():
    for u in re.findall(r'<img[^>]+src="(https?://[^"]+)"', t):
        remote[re.sub(r"[?].*$", "", u).split("/")[2]] += 1
signed = sum(1 for rel, t in PUBLIC.items()
             for u in re.findall(r'<img[^>]+src="(https?://[^"]+sig:[^"]+)"', t))
if signed:
    uniq = len({u for rel, t in PUBLIC.items()
                for u in re.findall(r'<img[^>]+src="(https?://[^"]+sig:[^"]+)"', t)})
    add("MEDIUM", "hotlink",
        f"{signed} <img> tags ({uniq} unique) hot-link a partner CDN with signed URLs. "
        f"If the signatures expire or the host rate-limits, they all break at once, and "
        f"qa_http.py reports them as 'unreachable from sandbox' so the gate stays green. "
        f"Run dl.py to self-host (add its __main__ guard first).")

# ================================================ L-a11y / SEO residue
for rel, t in PUBLIC.items():
    hs = [int(m.group(1)) for m in re.finditer(r"<h([1-6])[^>]*>", t, re.I)]
    for a, b in zip(hs, hs[1:]):
        if b - a > 1:
            add("LOW", "a11y", f"{rel}: heading level jumps h{a} -> h{b}")
            break
    d = re.search(r'name="description" content="([^"]*)"', t)
    if d and len(d.group(1)) > 165:
        add("LOW", "seo", f"{rel}: meta description {len(d.group(1))} chars (>165)")
    for m in re.finditer(r'<img\b[^>]*>', t, re.I):
        a = re.search(r'\balt="(.*?)"', m.group(0), re.S)
        if a and not a.group(1).strip() and 'role="presentation"' not in m.group(0):
            add("LOW", "a11y", f"{rel}: empty alt with no role=presentation")

# ============================================================ report
ORDER = ["internal-exposure", "internal-exposure-src", "design-law", "privacy", "forms",
         "season", "promo", "feed-csv", "assets", "drops", "brand-safety", "duplicates",
         "slugs", "copy", "feed", "orphans", "policy", "hotlink", "a11y", "seo"]
RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
print(f"catalogue: {len(LIVE)} live designs, {len(STUBS)} redirect stubs, "
      f"{len(PUBLIC)} public HTML pages")
print("=" * 78)
tot = collections.Counter()
crit = 0
for tag in ORDER:
    if tag not in FIND:
        continue
    sev = SEV[tag]
    n = len(FIND[tag])
    tot[sev] += 1                      # one issue per tag; n = evidence lines
    if sev == "CRITICAL":
        crit += 1
    print(f"\n[{sev}] {tag} ({n})")
    for m in FIND[tag][:25]:
        print("   ", m)
    if n > 25:
        print(f"    ... and {n - 25} more")
print("\n" + "=" * 78)
print("qa_deep: " + "  ".join(f"{k}={v}" for k, v in
                              sorted(tot.items(), key=lambda kv: RANK[kv[0]])))
if not tot:
    print("qa_deep: PASS - no findings")
sys.exit(1 if crit else 0)
