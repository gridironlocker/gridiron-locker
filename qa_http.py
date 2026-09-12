#!/usr/bin/env python3
"""Live HTTP QA against a running server.

Complements qa_audit.py (static, off-disk) by actually fetching: every
sitemap URL, every internal link, every CTA and every image. Run the site
first, e.g.

    cd site && python3 -m http.server 8123 --bind 0.0.0.0 &
    python3 qa_http.py http://127.0.0.1:8123
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
import urllib.request
import urllib.error

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8123").rstrip("/")
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402

FAIL = []


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "gl-qa/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()


def local(url):
    """Fetch a same-origin URL through the local server."""
    p = urlparse(url)
    return get(BASE + p.path)


# ---------------------------------------------------------- 1. sitemap URLs
locs = [e.text.strip() for e in
        ET.parse(os.path.join(SITE, "sitemap.xml")).getroot()
        .findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
print(f"sitemap URLs: {len(locs)}")
with ThreadPoolExecutor(24) as ex:
    codes = list(ex.map(lambda u: (u, local(u)[0]), locs))
bad = [(u, c) for u, c in codes if c != 200]
print(f"  non-200: {len(bad)}")
for u, c in bad[:10]:
    FAIL.append(f"sitemap URL {c}: {u}")

# ------------------------------------------- 2. every internal link + image
# Crawl from LOCAL paths, not sitemap URLs: the sitemap carries absolute
# gridironlocker.store URLs, and using them as the urljoin base makes every
# relative href resolve off-origin so nothing looks internal.
targets, imgs, remote_imgs = set(), set(), set()
for u, c in codes:
    if c != 200:
        continue
    path = urlparse(u).path
    code, body = local(path)
    if code != 200:
        continue
    text = body.decode("utf-8", "replace")
    for m in re.finditer(r'<a\s[^>]*?href=["\']([^"\']+)["\']', text, re.I):
        h = m.group(1)
        if h.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absu = urljoin(BASE + path, h)
        p = urlparse(absu)
        if p.netloc == urlparse(BASE).netloc:
            targets.add(p.path.split("#")[0] or "/")
        elif "gridironlocker.store" in p.netloc:
            targets.add(p.path.split("#")[0] or "/")
    for m in re.finditer(r"<img\b[^>]*>", text, re.I):
        s = re.search(r"""src=["']([^"']*)["']""", m.group(0), re.I)
        if not s or s.group(1).startswith("data:"):
            continue
        absu = urljoin(BASE + path, s.group(1))
        if urlparse(absu).netloc in ("", urlparse(BASE).netloc):
            imgs.add(urlparse(absu).path)
        else:
            remote_imgs.add(absu)

print(f"internal link targets discovered: {len(targets)}")
with ThreadPoolExecutor(32) as ex:
    res = list(ex.map(lambda t: (t, get(BASE + t)[0]), sorted(targets)))
dead = [(t, c) for t, c in res if c != 200]
print(f"  dead: {len(dead)}")
for t, c in dead[:15]:
    FAIL.append(f"dead internal link {c}: {t}")

print(f"local images referenced: {len(imgs)}")
with ThreadPoolExecutor(32) as ex:
    ires = list(ex.map(lambda t: (t, get(BASE + t)[0]), sorted(imgs)))
ibad = [(t, c) for t, c in ires if c != 200]
print(f"  broken: {len(ibad)}")
for t, c in ibad[:15]:
    FAIL.append(f"broken image {c}: {t}")

# Remote (partner CDN) mockups: hot-linked until dl.py localises them. A
# network error means this sandbox cannot reach the host - that is reported,
# not counted as a broken image.
print(f"remote partner images: {len(remote_imgs)}")
with ThreadPoolExecutor(12) as ex:
    rres = [(t,) + get(t, 20) for t in ex.map(lambda u: u, sorted(remote_imgs))]
rbad = [(t, c) for t, c, _b in rres if c is not None and c != 200]
runreach = [t for t, c, _b in rres if c is None]
print(f"  confirmed broken: {len(rbad)}   unreachable from sandbox: {len(runreach)}")
for t, c in rbad[:10]:
    FAIL.append(f"broken remote image {c}: {t[:120]}")

# ------------------------------------------------- 3. every product CTA
print(f"product CTAs: {len(build.ALL)}")
cta_bad = []
for it in build.ALL:
    code, body = local(f"/shop/{it['slug']}/")
    if code != 200:
        cta_bad.append((it["slug"], f"page {code}"))
        continue
    text = body.decode("utf-8", "replace")
    hrefs = re.findall(r'<a class="btn[^"]*shopnow" href="([^"]+)"', text)
    if not hrefs:
        cta_bad.append((it["slug"], "no SHOP NOW CTA"))
        continue
    for h in set(hrefs):
        if h != it["buy"]:
            cta_bad.append((it["slug"], f"CTA {h} != {it['buy']}"))
print(f"  mismatched/missing: {len(cta_bad)}")
for s, why in cta_bad[:15]:
    FAIL.append(f"CTA {s}: {why}")

# --------------------------------- 4. redirect stubs for retired URLs
stubs = build.retired_slugs()
print(f"retired redirect stubs: {len(stubs)}")
stub_bad = []
for slug, ckey in stubs.items():
    code, body = local(f"/shop/{slug}/")
    if code != 200:
        stub_bad.append((slug, f"HTTP {code}"))
        continue
    text = body.decode("utf-8", "replace")
    tgt = f"/{build.COLLECTIONS[ckey]['slug']}/"
    if f'data-gl-redirect="{tgt}"' not in text:
        stub_bad.append((slug, f"does not forward to {tgt}"))
    if 'content="noindex' not in text:
        stub_bad.append((slug, "not noindex"))
    if tgt not in text:
        stub_bad.append((slug, "no visible link to target"))
    # the target itself must be live
    if local(tgt)[0] != 200:
        stub_bad.append((slug, f"target {tgt} is not 200"))
print(f"  broken: {len(stub_bad)}")
for s, why in stub_bad[:15]:
    FAIL.append(f"stub {s}: {why}")

# --------------------------------------------- 5. mobile / overflow proxies
print("responsive + asset checks")
css_code, css = local("/assets/style.css")
css = css.decode("utf-8", "replace") if css_code == 200 else ""
if css_code != 200:
    FAIL.append(f"stylesheet {css_code}")
# Mobile breakpoints: assert the sheet actually adapts at phone / tablet
# widths rather than demanding one specific pixel value.
bps = sorted({int(w) for w in re.findall(r"max-width:\s*(\d+)px", css)})
if not any(w <= 480 for w in bps):
    FAIL.append(f"stylesheet has no phone-width breakpoint (has {bps})")
if not any(600 <= w <= 1024 for w in bps):
    FAIL.append(f"stylesheet has no tablet-width breakpoint (has {bps})")
print(f"  max-width breakpoints: {bps}")
if "overflow-x" not in css and "overflow-wrap" not in css:
    FAIL.append("stylesheet has no horizontal-overflow guard")

# horizontal-overflow risk: any fixed-width element wider than 360px
wide = re.findall(r"(?:^|[;{\s])width:\s*(\d{3,})px", css)
risky = [w for w in wide if int(w) > 360]
print(f"  fixed widths >360px in CSS: {len(risky)} {sorted(set(risky))[:8]}")

home = local("/")[1].decode("utf-8", "replace")
if 'name="viewport"' not in home:
    FAIL.append("homepage missing viewport meta")

print()
print("=" * 70)
if FAIL:
    print(f"HTTP QA: {len(FAIL)} PROBLEM(S)")
    for f in FAIL[:60]:
        print("  *", f)
    sys.exit(1)
print("HTTP QA: PASS")
