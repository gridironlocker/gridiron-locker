#!/usr/bin/env python3
"""Offline tests for the crawl fail-safes.

These guard the scenario that actually costs money: a blocked or partial crawl
overwriting a good catalogue, which on the next build would delete live product
pages and their SEO history.

Each test runs the real script in a temp copy of the repo with the network
forced to fail, then asserts the committed data survived.

No internet required:  python3 tests/test_failsafes.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Force every outbound request to fail, simulating a fully blocked edge.
KILL_NET = """
import socket
def _boom(*a, **k):
    raise OSError("network disabled for test")
socket.socket.connect = _boom
socket.create_connection = _boom
"""

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


def sandbox():
    """Temp repo with just the pieces the crawlers touch."""
    d = tempfile.mkdtemp(prefix="gl-test-")
    os.makedirs(os.path.join(d, "data"))
    os.makedirs(os.path.join(d, "src"))
    for f in ("scrape_list.py", "scrape_products.py", "dl.py"):
        shutil.copy(os.path.join(ROOT, f), os.path.join(d, f))
    shutil.copy(os.path.join(ROOT, "src/viralstyle.py"), os.path.join(d, "src/viralstyle.py"))
    for f in ("collections.json", "products.json", "products_live.json"):
        shutil.copy(os.path.join(ROOT, "data", f), os.path.join(d, "data", f))
    open(os.path.join(d, "sitecustomize.py"), "w").write(KILL_NET)
    return d


def run(d, script, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = d
    env["VS_ATTEMPTS"] = "1"
    env["VS_TIMEOUT"] = "3"
    env["VS_POOL_RETRIES"] = "0"
    env["VS_BACKOFF"] = "0"
    env["VS_WORKERS"] = "16"
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, script], cwd=d, env=env,
                          capture_output=True, text=True, timeout=600,
                          encoding="utf-8", errors="replace")


def main():
    print("Crawl fail-safe tests (network forced offline)\n")

    # --- 1. scrape_list.py must not wipe collections when the crawl fails ----
    d = sandbox()
    before = json.load(open(os.path.join(d, "data/collections.json")))
    n_before = {k: len(v["products"]) for k, v in before.items()}
    r = run(d, "scrape_list.py")
    after = json.load(open(os.path.join(d, "data/collections.json")))
    n_after = {k: len(v["products"]) for k, v in after.items()}
    check("scrape_list keeps all collections on total failure",
          n_before == n_after, f"{n_before} -> {n_after}")
    check("scrape_list warns about kept data",
          "keeping" in r.stdout.lower(), r.stdout[-200:])
    shutil.rmtree(d)

    # --- 2. scrape_products.py must keep last-good records ------------------
    d = sandbox()
    before = json.load(open(os.path.join(d, "data/products.json")))
    live_before = sum(1 for v in before.values() if v.get("front"))
    r = run(d, "scrape_products.py")
    after = json.load(open(os.path.join(d, "data/products.json")))
    live_after = sum(1 for v in after.values() if v.get("front"))
    check("scrape_products preserves products with imagery",
          live_after == live_before, f"{live_before} -> {live_after}")
    # Error stubs are only acceptable for campaigns that were ALREADY dead
    # (no imagery in the committed data). A stub over a product that had a
    # front image would delete a live page on the next build.
    had_imagery = {k for k, v in before.items() if v.get("front")}
    bad = [k for k, v in after.items() if v.get("error") and k in had_imagery]
    check("scrape_products writes no error stubs over good data",
          not bad, f"clobbered: {bad}")
    stubs = {k for k, v in after.items() if v.get("error")}
    check("error stubs limited to already-dead campaigns",
          stubs and stubs.isdisjoint(had_imagery), f"stubs={len(stubs)}")
    shutil.rmtree(d)

    # --- 3. dl.py must refuse to shrink products_live.json ------------------
    d = sandbox()
    prods = json.load(open(os.path.join(d, "data/products.json")))
    keep = dict(list(prods.items())[:10])          # simulate a partial crawl
    json.dump(keep, open(os.path.join(d, "data/products.json"), "w"))
    live_before = json.load(open(os.path.join(d, "data/products_live.json")))
    r = run(d, "dl.py")
    live_after = json.load(open(os.path.join(d, "data/products_live.json")))
    check("dl.py aborts on catastrophic shrink",
          len(live_after) == len(live_before),
          f"{len(live_before)} -> {len(live_after)}")
    check("dl.py explains the abort",
          "ABORT" in r.stdout, r.stdout[-200:])
    shutil.rmtree(d)

    # --- 4. trends.py must not zero out mention counts ----------------------
    d = tempfile.mkdtemp(prefix="gl-test-")
    os.makedirs(os.path.join(d, "data"))
    os.makedirs(os.path.join(d, "src"))
    for f in ("trends.py", "viralstyle.py", "collections_data.py"):
        shutil.copy(os.path.join(ROOT, "src", f), os.path.join(d, "src", f))
    shutil.copy(os.path.join(ROOT, "data/trends.json"), os.path.join(d, "data/trends.json"))
    open(os.path.join(d, "sitecustomize.py"), "w").write(KILL_NET)
    before = open(os.path.join(d, "data/trends.json")).read()
    run(d, "src/trends.py")
    after = open(os.path.join(d, "data/trends.json")).read()
    check("trends.py leaves trends.json untouched when all feeds fail",
          before == after)
    shutil.rmtree(d)

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
