#!/usr/bin/env python3
"""Create site-offline/: a copy of site/ that works by double-clicking index.html
(file:// protocol) - all root-absolute URLs become relative, and directory links
get an explicit index.html because file:// cannot serve directory indexes."""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "site")
DST = os.path.join(ROOT, "site-offline")

if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)

ATTR = re.compile(r'(\s(?:href|src|content)=")(/(?!/)[^"]*)(")')


def fix(html_path):
    rel_dir = os.path.dirname(os.path.relpath(html_path, DST))
    depth = 0 if rel_dir in ("", ".") else len(rel_dir.split(os.sep))
    prefix = "./" if depth == 0 else "../" * depth

    def repl(m):
        pre, url, post = m.groups()
        # leave absolute canonical/OG urls alone (they start with http) - not matched anyway
        path = url.lstrip("/")
        if path.endswith("/") or path == "":
            path += "index.html"
        elif "." not in os.path.basename(path):
            path = path.rstrip("/") + "/index.html"
        return pre + prefix + path + post

    t = open(html_path, encoding="utf-8").read()
    # never rewrite inside JSON-LD / meta absolute URLs (they are full https:// already)
    t = ATTR.sub(repl, t)
    open(html_path, "w", encoding="utf-8").write(t)


n = 0
for base, _, files in os.walk(DST):
    for f in files:
        if f.endswith(".html"):
            fix(os.path.join(base, f))
            n += 1

# css uses no absolute asset urls, but normalise just in case
print(f"offline build ready: {n} pages -> {DST}")
