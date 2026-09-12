#!/usr/bin/env python3
"""Full technical / SEO / fulfilment QA audit of the built site.

Reads site/ off disk (no network) and reports every class of defect the
master audit brief asks about. Run after `python3 src/build.py`.

    python3 qa_audit.py            # human report
    python3 qa_audit.py --json     # machine report
"""
import json
import os
import re
import sys
import html as _html
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from urllib.parse import urljoin, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
CFG = json.load(open(os.path.join(ROOT, "src/config.json")))
DOMAIN = CFG["domain"].rstrip("/")
PUBLIC_EXCLUDE = ("/ops/", "/marketing/")

REPORT = defaultdict(list)


def issue(cat, msg):
    REPORT[cat].append(msg)


#: Files that are verification tokens, not pages - they carry no head markup.
NOT_PAGES = re.compile(r"^(google[0-9a-f]+\.html|BingSiteAuth\.xml)$")


def pages():
    """Every public HTML page, as (url_path, abs_file).

    ``index.html`` collapses to its directory URL so paths line up with the
    canonicals, sitemap locs and hrefs the site actually uses.
    """
    out = []
    for base, _dirs, files in os.walk(SITE):
        for f in files:
            if not f.endswith(".html") or NOT_PAGES.match(f):
                continue
            full = os.path.join(base, f)
            rel = "/" + os.path.relpath(full, SITE).replace(os.sep, "/")
            if any(rel.startswith(x) for x in PUBLIC_EXCLUDE):
                continue
            url = re.sub(r"/index\.html$", "/", rel)
            out.append((url, full))
    return sorted(out)


def parse(path, text):
    """Cheap head-section extractor: no bs4 dependency at audit time."""
    head = text[: text.lower().find("</head>") + 7] if "</head>" in text.lower() else text
    def meta(name, attr="name"):
        m = re.search(r'<meta[^>]+%s=["\']%s["\'][^>]*>' % (attr, re.escape(name)), head, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*%s=["\']%s["\']'
                          % (attr, re.escape(name)), head, re.I)
            return m.group(1) if m else None
        c = re.search(r'content=["\']([^"\']*)["\']', m.group(0))
        return c.group(1) if c else None
    title = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*>', head, re.I)
    canon = None
    if canonical:
        h = re.search(r'href=["\']([^"\']*)["\']', canonical.group(0))
        canon = h.group(1) if h else None
    h1s = re.findall(r"<h1[\s>].*?</h1>|<h1[^>]*/>", text, re.S | re.I)
    h1_text = [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", h))).strip() for h in h1s]
    ld = []
    for m in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            ld.append(json.loads(m.strip()))
        except Exception as e:
            issue("structured-data", f"{path}: invalid JSON-LD ({e})")
    return dict(title=_html.unescape(title.group(1)).strip() if title else None,
                desc=meta("description"), robots=meta("robots"), canonical=canon,
                og_title=meta("og:title", "property"), og_desc=meta("og:description", "property"),
                og_image=meta("og:image", "property"), og_url=meta("og:url", "property"),
                tw_card=meta("twitter:card"), tw_image=meta("twitter:image"),
                h1=h1_text, ld=ld, text=text)


def flatten_ld(node, out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        out.append(node)
        for v in node.values():
            flatten_ld(v, out)
    elif isinstance(node, list):
        for v in node:
            flatten_ld(v, out)
    return out


# --------------------------------------------------------------- load catalogue
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402

MODEL, ALL = build.MODEL, build.ALL
N_ALL = len(ALL)
CATALOG_COUNTS = {k: len(v) for k, v in MODEL.items()}
MAYZING = [i for i in ALL if i["partner"] == "Mayzing"]
VIRAL = [i for i in ALL if i["partner"] == "Viralstyle"]

print(f"catalogue: {N_ALL} products across {len(MODEL)} collections")
for k, n in CATALOG_COUNTS.items():
    print(f"  {k}: {n}")
print(f"  Mayzing {len(MAYZING)} / Viralstyle {len(VIRAL)}\n")

PAGES = pages()
DOCS = {p: parse(p, open(f, encoding="utf-8").read()) for p, f in PAGES}
print(f"public pages audited: {len(PAGES)}\n")

# ------------------------------------------------------------------- 1. counts
COUNT_RE = re.compile(r"(?<![\w-])(\d{1,4})\s+(?:original\s+|fan-made\s+|hand-picked\s+|fan\s+)?"
                      r"(designs|products)\b", re.I)
for path, d in DOCS.items():
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", d["text"], flags=re.S | re.I)
    for m in COUNT_RE.finditer(body):
        n, noun = int(m.group(1)), m.group(2).lower()
        ctx = re.sub(r"\s+", " ", body[max(0, m.start() - 70): m.end() + 30]).strip()
        # "Week 1 designs" / "Game 1 products" is a fixture label, not a count.
        before = body[max(0, m.start() - 12):m.start()]
        if re.search(r"\b(week|day|game|round|phase)\s+$", before, re.I):
            continue
        # Joe's creator locker legitimately shows its own pick count
        if path.startswith("/michigan/joe/") and n != N_ALL and n <= 12:
            continue
        if n in CATALOG_COUNTS.values() or n == N_ALL or n == len(ORDER := build.ORDER):
            continue
        issue("catalogue-count", f"{path}: '{n} {noun}' (catalogue is {N_ALL}) :: {ctx}")

# ------------------------------------------------------- 2. fulfilment accuracy
for it in ALL:
    p = f"/shop/{it['slug']}/"
    if p not in DOCS:
        issue("fulfilment", f"{p}: product page missing from build")
        continue
    d = DOCS[p]
    partner, buy = it["partner"], it["buy"]
    host = urlparse(buy).netloc
    if partner == "Mayzing":
        if "gridironlocker.shop" not in host:
            issue("fulfilment", f"{p}: Mayzing product points at {buy}")
        if re.search(r"viralstyle", d["text"], re.I):
            issue("fulfilment", f"{p}: Mayzing product mentions Viralstyle")
        # Viralstyle's published shipping rate / window must never appear on a
        # Mayzing page, in copy or in structured data.
        if "$4.95" in d["text"] or '"4.95"' in json.dumps(d["ld"]):
            issue("fulfilment", f"{p}: Viralstyle $4.95 US shipping rate shown on Mayzing product")
        if build.VIRALSTYLE_DELIVERY_TIME in d["text"]:
            issue("fulfilment",
                  f"{p}: Viralstyle delivery window shown on Mayzing product")
    else:
        # the mirror image: Mayzing terms must not leak onto Viralstyle pages
        if "Delivery times shown at checkout" in d["text"]:
            issue("fulfilment", f"{p}: Mayzing badge shown on Viralstyle product")
        if "viralstyle.com" not in host:
            issue("fulfilment", f"{p}: Viralstyle product points at {buy}")
        if re.search(r"mayzing", d["text"], re.I):
            issue("fulfilment", f"{p}: Viralstyle product mentions Mayzing")
    # every CTA on the page must go to the product's own checkout URL
    ctas = re.findall(r'href="([^"]+)"[^>]*class="[^"]*\b(?:cta|buy|shop)[^"]*"', d["text"])
    ctas += re.findall(r'class="[^"]*\b(?:cta|buy|shop)[^"]*"[^>]*href="([^"]+)"', d["text"])
    for c in set(ctas):
        if c.startswith("http") and c != buy:
            issue("fulfilment", f"{p}: CTA {c} != catalogue buy URL {buy}")

# ------------------------------------------- 3. shipping / production language
GLOBAL_CLAIMS = [
    (r"[Pp]rinted on demand in the USA", "global 'printed on demand in the USA' claim"),
    (r"[Mm]ade in (?:the )?USA", "global 'made in the USA' claim"),
]
for path, d in DOCS.items():
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", d["text"], flags=re.S | re.I)
    for rx, label in GLOBAL_CLAIMS:
        if re.search(rx, body):
            issue("shipping-claims", f"{path}: {label}")

# ------------------------------------------------------ 4. SEO titles / metas
titles, descs, h1map = Counter(), Counter(), Counter()
for path, d in DOCS.items():
    # Duplicate-title/description checks only make sense across INDEXABLE
    # pages: the retired-URL redirect stubs are noindex and deliberately
    # share a short "moved" title.
    indexable = not (d["robots"] and "noindex" in d["robots"])
    if not d["title"]:
        issue("seo-title", f"{path}: missing <title>")
    else:
        if len(d["title"]) > 65:
            issue("seo-title", f"{path}: title {len(d['title'])} chars (long): {d['title']}")
        if len(d["title"]) < 15:
            issue("seo-title", f"{path}: title too short: {d['title']}")
        if indexable:
            titles[d["title"]] += 1
    if not d["desc"]:
        issue("seo-meta", f"{path}: missing meta description")
    else:
        if len(d["desc"]) > 175:
            issue("seo-meta", f"{path}: description {len(d['desc'])} chars (long)")
        if indexable:
            descs[d["desc"]] += 1
    if len(d["h1"]) != 1:
        issue("seo-h1", f"{path}: {len(d['h1'])} H1s {d['h1'][:3]}")
    if d["h1"]:
        h1map[d["h1"][0]] += 1
    # canonical. A noindex redirect stub (retired product URL) deliberately
    # canonicalises to the page it forwards to - that IS the redirect signal.
    # An INDEXABLE page canonicalising away is the real defect.
    expect = DOMAIN + path
    if not d["canonical"]:
        issue("seo-canonical", f"{path}: no canonical")
    elif d["canonical"] != expect:
        if d["robots"] and "noindex" in d["robots"]:
            if d["canonical"] not in {DOMAIN + p for p in DOCS}:
                issue("seo-canonical",
                      f"{path}: redirect stub canonical not a live page: {d['canonical']}")
        else:
            issue("seo-canonical", f"{path}: canonical {d['canonical']} != {expect}")
    # social
    if not d["og_title"]:
        issue("social", f"{path}: missing og:title")
    if not d["og_desc"]:
        issue("social", f"{path}: missing og:description")
    if not d["og_image"]:
        issue("social", f"{path}: missing og:image")
    if not d["og_url"]:
        issue("social", f"{path}: missing og:url")
    if not d["tw_card"]:
        issue("social", f"{path}: missing twitter:card")
for t, c in titles.items():
    if c > 1:
        issue("seo-title", f"duplicate <title> x{c}: {t}")
for s, c in descs.items():
    if c > 1:
        issue("seo-meta", f"duplicate meta description x{c}: {s[:90]}...")

# ------------------------------------------------------- 5. structured data
for path, d in DOCS.items():
    nodes = flatten_ld(d["ld"])
    types = {n.get("@type") for n in nodes if isinstance(n.get("@type"), str)}
    for n in nodes:
        t = n.get("@type")
        if t == "Product":
            if not n.get("name"):
                issue("structured-data", f"{path}: Product without name")
            if not n.get("image"):
                issue("structured-data", f"{path}: Product without image")
            off = n.get("offers")
            if not off:
                issue("structured-data", f"{path}: Product without Offer")
            else:
                for o in (off if isinstance(off, list) else [off]):
                    if o.get("priceCurrency") not in ("USD",):
                        issue("structured-data", f"{path}: Offer currency {o.get('priceCurrency')}")
                    if o.get("availability") not in (
                            "https://schema.org/InStock", "https://schema.org/OutOfStock"):
                        issue("structured-data", f"{path}: bad availability {o.get('availability')}")
                    if not o.get("url", "").startswith("http"):
                        issue("structured-data", f"{path}: Offer url not absolute")
            if d["h1"] and n.get("name") and n["name"].strip() != d["h1"][0].strip():
                issue("structured-data",
                      f"{path}: Product name '{n['name']}' != H1 '{d['h1'][0]}'")
        if t == "AggregateRating":
            issue("structured-data",
                  f"{path}: AggregateRating present (no genuine review data on this store)")
        if t == "Offer":
            sd = n.get("shippingDetails")
            rp = n.get("hasMerchantReturnPolicy")
            slug = path.strip("/").split("/")[-1]
            item = next((i for i in ALL if i["slug"] == slug), None)
            if item and item["partner"] == "Mayzing":
                if sd:
                    issue("structured-data",
                          f"{path}: Mayzing Offer carries Viralstyle shippingDetails")
                if rp:
                    issue("structured-data",
                          f"{path}: Mayzing Offer carries Viralstyle return policy")
        if t == "BreadcrumbList":
            items = n.get("itemListElement") or []
            if not items:
                issue("structured-data", f"{path}: empty BreadcrumbList")
            for li in items:
                if li.get("item") and not li["item"].startswith(DOMAIN):
                    issue("structured-data", f"{path}: breadcrumb off-domain {li['item']}")

# ------------------------------------------------------ 6. links + 404s
KNOWN = set(DOCS.keys()) | {"/"}
EAGER_IMGS = {}
EXISTING_FILES = set()
for base, _dirs, files in os.walk(SITE):
    for f in files:
        EXISTING_FILES.add("/" + os.path.relpath(os.path.join(base, f), SITE).replace(os.sep, "/"))


def resolves(target, base="/"):
    """True when an href/src points at something that exists in site/.

    The build emits relative hrefs (``./collections/``) so the tree also works
    off GitHub Pages subpaths and from disk; those are resolved against the
    linking page exactly as a browser would.
    """
    t = target.split("#")[0].split("?")[0]
    if not t:
        return True
    if t.startswith("/"):
        cand = t
    else:
        cand = urlparse(urljoin(base, t)).path
    if cand in KNOWN or cand.rstrip("/") + "/index.html" in EXISTING_FILES:
        return True
    return cand in EXISTING_FILES


REMOTE_IMGS = {}
for path, d in DOCS.items():
    for m in re.finditer(r"<a\s[^>]*?href=[\"']([^\"']+)[\"']", d["text"], re.I):
        href = m.group(1)
        if href.startswith(("mailto:", "tel:", "javascript:")) or href.startswith("#"):
            continue
        if href.startswith(("http://", "https://")):
            u = urlparse(href)
            if u.netloc == urlparse(DOMAIN).netloc:
                if not resolves(u.path, path):
                    issue("links", f"{path}: internal link 404 -> {href}")
            continue
        if href.startswith("//"):
            continue
        if not resolves(href, path):
            issue("links", f"{path}: broken internal link -> {href}")
    # images - match the whole tag so trailing alt/loading attrs are seen
    eager = 0
    for m in re.finditer(r"<img\b[^>]*>", d["text"], re.I):
        tag = m.group(0)
        s = re.search(r"""src=["']([^"']*)["']""", tag, re.I)
        if not s:
            issue("images", f"{path}: <img> with no src")
            continue
        src = s.group(1)
        if src.startswith("data:"):
            continue
        if src.startswith(("http://", "https://", "//")):
            REMOTE_IMGS.setdefault(src, []).append(path)
            continue
        if not resolves(src, path):
            issue("images", f"{path}: broken image -> {src}")
        if "alt=" not in tag.lower():
            issue("images", f"{path}: <img> without alt -> {src}")
        elif re.search(r"""alt=["']\s*["']""", tag, re.I):
            # alt="" is correct for a decorative mark that sits beside
            # equivalent visible text (the team portraits do). Only flag it
            # when nothing textual follows inside the same container.
            after = d["text"][m.end(): m.end() + 400]
            label = re.sub(r"<[^>]+>", " ", after)
            if not re.sub(r"\s+", "", label).strip():
                issue("images",
                      f"{path}: decorative alt=\"\" with no adjacent text -> {src}")
        if "loading=" not in tag.lower() and "fetchpriority" not in tag.lower():
            eager += 1
    if eager:
        EAGER_IMGS[path] = eager

# --------------------------------------------------- 7. sitemap + robots
sm = os.path.join(SITE, "sitemap.xml")
if not os.path.exists(sm):
    issue("sitemap", "sitemap.xml missing")
else:
    tree = ET.parse(sm)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text.strip() for e in tree.getroot().findall(".//s:loc", ns)]
    if not locs:
        issue("sitemap", "sitemap has no <loc> entries")
    dupes = [u for u, c in Counter(locs).items() if c > 1]
    for u in dupes:
        issue("sitemap", f"duplicate URL in sitemap: {u}")
    for u in locs:
        p = urlparse(u)
        if u.startswith(DOMAIN):
            path = p.path
            if path not in KNOWN and path.rstrip("/") + "/index.html" not in EXISTING_FILES:
                issue("sitemap", f"sitemap URL 404s: {u}")
            d = DOCS.get(path)
            if d and d["robots"] and "noindex" in d["robots"]:
                issue("sitemap", f"sitemap contains noindex page: {u}")
            if d and d["canonical"] and d["canonical"] != u:
                issue("sitemap", f"sitemap URL != canonical: {u} vs {d['canonical']}")
        else:
            issue("sitemap", f"off-domain sitemap URL: {u}")
    # every indexable page should be in the sitemap
    missing = [p for p, d in DOCS.items()
               if not (d["robots"] and "noindex" in d["robots"])
               and p not in ("/404.html",) and DOMAIN + p not in locs]
    for p in sorted(missing):
        issue("sitemap", f"indexable page missing from sitemap: {p}")

rb = os.path.join(SITE, "robots.txt")
if not os.path.exists(rb):
    issue("robots", "robots.txt missing")
else:
    txt = open(rb).read()
    if "Sitemap:" not in txt:
        issue("robots", "robots.txt has no Sitemap directive")
    for line in txt.splitlines():
        if line.strip().startswith("Sitemap:"):
            u = line.split(":", 1)[1].strip()
            if not u.startswith(DOMAIN):
                issue("robots", f"robots.txt sitemap not on domain: {u}")
    for dis in re.findall(r"^Disallow:\s*(\S+)", txt, re.M):
        for p in DOCS:
            if p.startswith(dis) and not (DOCS[p]["robots"] and "noindex" in DOCS[p]["robots"]):
                issue("robots", f"robots.txt blocks indexable page {p} via {dis}")

# ------------------------------------ 8. exposed internal / developer content
LEAK_PATTERNS = [
    (r"\bpython3?\s+\S+\.py\b", "python command"),
    (r"\b[a-z_0-9]+\.py\b(?!\s*[a-z])", ".py filename"),
    (r"\b[a-z_0-9]+\.csv\b", "CSV filename"),
    (r"\bdata/[a-z_0-9]+\.json\b", "internal data path"),
    (r"\bsrc/[a-z_0-9]+\.py\b", "source path"),
    (r"\bnpm (?:run|install)\b", "build command"),
    (r"\bgit (?:push|commit|checkout)\b", "git command"),
]
for path, d in DOCS.items():
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", d["text"], flags=re.S | re.I)
    visible = _html.unescape(re.sub(r"<[^>]+>", " ", body))
    for rx, label in LEAK_PATTERNS:
        for m in re.finditer(rx, visible):
            ctx = re.sub(r"\s+", " ", visible[max(0, m.start() - 60): m.end() + 60]).strip()
            issue("internal-content", f"{path}: {label} exposed -> {m.group(0)} :: {ctx}")

# --------------------------------------------------- 9. IP / brand language
BAD_IP = [
    (r"\bofficial(?:ly)?\s+(?:licensed|affiliated|endorsed|partner)\b(?!.*not)",
     "possible official-affiliation claim"),
]
for path, d in DOCS.items():
    visible = _html.unescape(re.sub(r"<[^>]+>", " ", d["text"]))
    for rx, label in BAD_IP:
        for m in re.finditer(rx, visible, re.I):
            ctx = re.sub(r"\s+", " ", visible[max(0, m.start() - 90): m.end() + 90]).strip()
            if re.search(r"\bnot\b|\bnever\b|\bno\b|\bunofficial\b|\bindependent\b", ctx, re.I):
                continue
            issue("ip-language", f"{path}: {label} :: {ctx}")

# ----------------------------------------------------------------- 10. output
if "--json" in sys.argv:
    print(json.dumps({k: v for k, v in REPORT.items()}, indent=1))
    sys.exit(0)

order = ["fulfilment", "catalogue-count", "shipping-claims", "seo-title", "seo-h1", "seo-meta",
         "seo-canonical", "structured-data", "links", "images", "sitemap", "robots",
         "social", "internal-content", "ip-language"]
total = 0
print("=" * 78)
for cat in order:
    items = REPORT.get(cat, [])
    total += len(items)
    flag = "PASS" if not items else f"{len(items)} ISSUE(S)"
    print(f"{cat:<20} {flag}")
print("=" * 78)
print(f"TOTAL: {total}")
print(f"unique remote images: {len(REMOTE_IMGS)} "
      f"({sum(1 for u in REMOTE_IMGS if 'mayzing.com' in u)} on the Mayzing CDN)")
print(f"pages with un-hinted (eager) <img>: {len(EAGER_IMGS)}\n")
for cat in order:
    if not REPORT.get(cat):
        continue
    print(f"\n--- {cat} ({len(REPORT[cat])}) ---")
    for m in REPORT[cat][:60]:
        print(f"  * {m}")
    if len(REPORT[cat]) > 60:
        print(f"  ... and {len(REPORT[cat]) - 60} more")
