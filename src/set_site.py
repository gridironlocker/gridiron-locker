#!/usr/bin/env python3
"""Set your live site URL in one command, then rebuild.

Usage:
    python3 src/set_site.py https://gridironlocker.github.io/gridiron-locker
    python3 src/set_site.py https://www.yourdomain.com

Updates canonical tags, Open Graph URLs, schema.org URLs, robots.txt and sitemap.xml.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "src/config.json")

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

url = sys.argv[1].rstrip("/")
if not re.match(r"^https?://", url):
    print("URL must start with http:// or https://")
    sys.exit(1)

cfg = json.load(open(CFG))
old = cfg["domain"]
cfg["domain"] = url
# `with`, and this one is a correctness fix rather than a warning fix: the very
# next statement spawns src/build.py as a SEPARATE PROCESS which reads
# src/config.json from disk. json.dump(cfg, open(CFG, "w")) relies on CPython's
# refcount dropping the handle - and therefore flushing and closing it - before
# the subprocess starts. That happens to hold on CPython today, but it is not a
# guarantee the language makes, and the failure mode is a whole site rebuilt
# with the old domain in every canonical tag, OG URL, schema block, robots.txt
# and sitemap entry. Closing it explicitly removes the race.
with open(CFG, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, indent=2)
print(f"domain: {old}  ->  {url}")

subprocess.run([sys.executable, os.path.join(ROOT, "src/build.py")], check=True)
print("\nDone. The 'site' folder is ready to publish.")
