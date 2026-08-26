#!/usr/bin/env python3
"""Offline tests for the Viralstyle connection layer.

Runs a throwaway local HTTP server that impersonates the failure modes we
actually see in the wild - 503s, rate limits, captcha interstitials, truncated
SPA shells, dead campaigns - and asserts the layer handles each correctly.

No internet required:  python3 tests/test_viralstyle.py
"""
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import viralstyle as vs  # noqa: E402

GOOD = "<html><body>" + ("<div>product</div>" * 3000) + "</body></html>"   # ~60KB
SHORT = "<html><body>loading…</body></html>"
CAPTCHA = "<html><head><title>Attention Required</title></head><body>" \
          "Please complete the captcha</body></html>" + "x" * 40000

hits = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        hits[path] = hits.get(path, 0) + 1
        n = hits[path]

        def send(code, body):
            b = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        if path == "/ok":
            send(200, GOOD)
        elif path == "/flaky":            # fails twice, then succeeds
            send(200, GOOD) if n > 2 else send(503, "nope")
        elif path == "/ratelimit":        # 429 then success
            send(200, GOOD) if n > 1 else send(429, "slow down")
        elif path == "/captcha":
            send(200, CAPTCHA)
        elif path == "/short":
            send(200, SHORT)
        elif path == "/gone":
            send(404, "not found")
        elif path == "/always500":
            send(500, "boom")
        else:
            send(404, "?")


def run_tests(base):
    passed = failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name} {detail}")

    s = vs.make_session()

    # 1. happy path
    r = vs.fetch(f"{base}/ok", session=s)
    check("valid page returned", r is not None and len(r) > 20000)

    # 2. transient 5xx is retried until success
    hits.clear()
    r = vs.fetch(f"{base}/flaky", session=s, attempts=4)
    check("retries through 503", r is not None, f"hits={hits.get('/flaky')}")

    # 3. rate limit is retried
    hits.clear()
    r = vs.fetch(f"{base}/ratelimit", session=s, attempts=4)
    check("retries through 429", r is not None)

    # 4. captcha interstitial must NOT be mistaken for a real page
    r = vs.fetch(f"{base}/captcha", session=s, attempts=1)
    check("captcha rejected", r is None)

    # 5. truncated SPA shell must NOT count as a product page
    r = vs.fetch(f"{base}/short", session=s, attempts=1)
    check("short body rejected", r is None)

    # 6. 404 returns immediately without burning retries
    hits.clear()
    t0 = time.time()
    r = vs.fetch(f"{base}/gone", session=s, attempts=4)
    check("404 short-circuits", r is None and hits.get("/gone") == 1 and time.time() - t0 < 3,
          f"hits={hits.get('/gone')}")

    # 7. persistent failure gives up and returns None (never raises)
    r = vs.fetch(f"{base}/always500", session=s, attempts=2)
    check("persistent 5xx returns None", r is None)

    # 8. fetch_first falls through bad URLs to a good one
    r = vs.fetch_first([f"{base}/short", f"{base}/captcha", f"{base}/ok"],
                       session=s, attempts=1)
    check("fetch_first falls through to valid URL", r is not None)

    # 9. fetch_first returns None when every strategy fails
    r = vs.fetch_first([f"{base}/short", f"{base}/gone"], session=s, attempts=1)
    check("fetch_first all-fail returns None", r is None)

    # 10. URL strategy builders produce the shapes the crawlers rely on
    pu = vs.product_urls("my-slug")
    check("product_urls includes escaped_fragment first",
          len(pu) == 3 and pu[0].endswith("my-slug?_escaped_fragment_="))
    su = vs.store_urls("Cleveland-Browns", 2)
    check("store_urls builds paged store URLs",
          len(su) == 3 and "/store/kebystore/Cleveland-Browns/2" in su[0])

    return passed, failed


def main():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    print(f"Viralstyle connection-layer tests (local stub on {base})\n")
    try:
        passed, failed = run_tests(base)
    finally:
        srv.shutdown()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
