#!/usr/bin/env python3
"""Set your live site URL in one command, then rebuild.

Usage:
    python3 src/set_site.py https://YOURNAME.github.io/gridiron-locker
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
json.dump(cfg, open(CFG, "w"), indent=2)
print(f"domain: {old}  ->  {url}")

subprocess.run([sys.executable, os.path.join(ROOT, "src/build.py")], check=True)
print("\nDone. The 'site' folder is ready to publish.")
