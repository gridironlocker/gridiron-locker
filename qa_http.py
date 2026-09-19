#!/usr/bin/env python3
"""Live HTTP QA against a running server.

Complements qa_audit.py (static, off-disk) by actually fetching: every
sitemap URL, every internal link, every CTA and every image. Run the site
first, e.g.

    cd site && python3 -m http.server 8123 --bind 0.0.0.0 &
    python3 qa_http.py http://127.0.0.1:8123

Import-safe since 2026-09-19 (AGENTS.md §6): the whole run sits in main()
behind a __main__ guard, and BASE - which used to be read from sys.argv at
import time - is a local of main(). Importing this module now only defines
two functions. Same landmine as dl.py, same reason: re-indenting a script
into main() rewrites every line, so the body was moved by machine and diffed
against HEAD statement by statement (SITE-AUDIT-2026-09-18.md §9.8).
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

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")


def protocol_relative_local(ref):
    """True when a ``//``-prefixed reference is a local path dressed as a CDN.

    The same rule, under the same name, as qa_audit.py's function, so the two
    gates grep together. ``//host/path`` is protocol-relative: the browser
    prepends the page's scheme and reads the first label as a hostname. A real
    remote host always contains a dot (``//buyer-experience-gateway.mayzing.com``).
    A first label with no dot (``//img/p/x.webp``, ``//search/``) is not a
    hostname at all - it is a root-relative path that lost its leading slash,
    and the browser goes off-origin to ``https://img/p/x.webp`` even though the
    file is sitting in ``site/img/``.

    This sweep used to hand *every* ``//`` ref straight to ``urljoin``: an href
    like ``//search/`` resolved to netloc "search" - neither this server nor
    gridironlocker.store - so the target was silently dropped from the link
    check, and an ``<img src>`` like ``//img/p/x.webp`` landed in the remote
    bucket, died on DNS and was filed under "unreachable from sandbox", which
    the gate reports but never fails. That is how the PR #121 poisoning (438
    values, 54 of 196 pages) could print ``HTTP QA: PASS`` while "local images
    referenced" collapsed 382 -> 16. Dot-less means local, and local means it
    must exist.
    """
    if not ref.startswith("//"):
        return False
    label = ref[2:].split("/", 1)[0]
    return bool(label) and "." not in label


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "gl-qa/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()


def main(argv=None):
    """Run the live gate against argv[1] (default: the local server)."""
    argv = sys.argv if argv is None else argv
    base = (argv[1] if len(argv) > 1 else "http://127.0.0.1:8123").rstrip("/")
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import build  # noqa: E402  (in here so `import qa_http` has no side effect)

    fail = []

    def local(url):
        """Fetch a same-origin URL through the local server."""
        p = urlparse(url)
        return get(base + p.path)

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
        fail.append(f"sitemap URL {c}: {u}")

    # ------------------------------------------- 2. every internal link + image
    # Crawl from LOCAL paths, not sitemap URLs: the sitemap carries absolute
    # gridironlocker.store URLs, and using them as the urljoin base makes every
    # relative href resolve off-origin so nothing looks internal.
    # The PR #121 shape - a local path whose leading slash was lost - is
    # collected here, images first, and reported as a FAIL of its own. Handing
    # '//search/' straight to urljoin resolves netloc "search", which matches
    # neither this server nor gridironlocker.store, so the target used to be
    # dropped from the link sweep with no line in the report; '//img/x.webp'
    # went to the remote bucket and was filed under "unreachable from sandbox",
    # which is printed but does not fail. Either way the gate said PASS.
    targets, imgs, remote_imgs = set(), set(), set()
    proto_imgs, proto_links = [], []
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
            ref = h
            if protocol_relative_local(h):
                proto_links.append((path, h))
                ref = "/" + h[2:]           # '//search/' -> '/search/'
            absu = urljoin(base + path, ref)
            p = urlparse(absu)
            if p.netloc == urlparse(base).netloc:
                targets.add(p.path.split("#")[0] or "/")
            elif "gridironlocker.store" in p.netloc:
                targets.add(p.path.split("#")[0] or "/")
        for m in re.finditer(r"<img\b[^>]*>", text, re.I):
            s = re.search(r"""src=["']([^"']*)["']""", m.group(0), re.I)
            if not s or s.group(1).startswith("data:"):
                continue
            src = s.group(1)
            if protocol_relative_local(src):
                proto_imgs.append((path, src))
                src = "/" + src[2:]         # '//img/p/x.webp' -> '/img/p/x.webp'
            absu = urljoin(base + path, src)
            if urlparse(absu).netloc in ("", urlparse(base).netloc):
                imgs.add(urlparse(absu).path)
            else:
                remote_imgs.add(absu)

    # The shape itself is the defect, exactly as qa_audit.py treats it: one
    # line naming the page and the ref - the failure has to name the disease,
    # not hide inside the "unreachable from sandbox" counter. The normalised
    # ref also went into targets/imgs above, so a ref pointing at a missing
    # file produces the ordinary dead-link / broken-image line as well.
    for p, r in proto_imgs:
        fail.append(f"protocol-relative local image {r} on {p}")
    for p, r in proto_links:
        fail.append(f"protocol-relative local link {r} on {p}")

    print(f"internal link targets discovered: {len(targets)}")
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(lambda t: (t, get(base + t)[0]), sorted(targets)))
    dead = [(t, c) for t, c in res if c != 200]
    print(f"  dead: {len(dead)}")
    for t, c in dead[:15]:
        fail.append(f"dead internal link {c}: {t}")

    print(f"local images referenced: {len(imgs)}")
    with ThreadPoolExecutor(32) as ex:
        ires = list(ex.map(lambda t: (t, get(base + t)[0]), sorted(imgs)))
    ibad = [(t, c) for t, c in ires if c != 200]
    print(f"  broken: {len(ibad)}")
    for t, c in ibad[:15]:
        fail.append(f"broken image {c}: {t}")

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
        fail.append(f"broken remote image {c}: {t[:120]}")

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
        fail.append(f"CTA {s}: {why}")

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
        fail.append(f"stub {s}: {why}")

    # --------------------------------------------- 5. mobile / overflow proxies
    print("responsive + asset checks")
    css_code, css = local("/assets/style.css")
    css = css.decode("utf-8", "replace") if css_code == 200 else ""
    if css_code != 200:
        fail.append(f"stylesheet {css_code}")
    # Mobile breakpoints: assert the sheet actually adapts at phone / tablet
    # widths rather than demanding one specific pixel value.
    bps = sorted({int(w) for w in re.findall(r"max-width:\s*(\d+)px", css)})
    if not any(w <= 480 for w in bps):
        fail.append(f"stylesheet has no phone-width breakpoint (has {bps})")
    if not any(600 <= w <= 1024 for w in bps):
        fail.append(f"stylesheet has no tablet-width breakpoint (has {bps})")
    print(f"  max-width breakpoints: {bps}")
    if "overflow-x" not in css and "overflow-wrap" not in css:
        fail.append("stylesheet has no horizontal-overflow guard")

    # horizontal-overflow risk: any fixed-width element wider than 360px
    wide = re.findall(r"(?:^|[;{\s])width:\s*(\d{3,})px", css)
    risky = [w for w in wide if int(w) > 360]
    print(f"  fixed widths >360px in CSS: {len(risky)} {sorted(set(risky))[:8]}")

    home = local("/")[1].decode("utf-8", "replace")
    if 'name="viewport"' not in home:
        fail.append("homepage missing viewport meta")

    print()
    print("=" * 70)
    if fail:
        print(f"HTTP QA: {len(fail)} PROBLEM(S)")
        for f in fail[:60]:
            print("  *", f)
        return 1
    print("HTTP QA: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
