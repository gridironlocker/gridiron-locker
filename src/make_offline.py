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

# src/build.py now emits canonical directory links ("../collections/") so that
# the published site exposes exactly one crawlable URL per page. file:// cannot
# serve a directory index, so the offline copy - and only the offline copy -
# expands those back to an explicit index.html. Both the root-absolute form
# (belt and braces, in case a page ever ships one) and the relative form the
# build actually produces are matched.
ATTR = re.compile(r'(\s(?:href|src|content)=")((?:/(?!/)|\.{1,2}/)[^"]*)(")')


def fix(html_path):
    rel_dir = os.path.dirname(os.path.relpath(html_path, DST))
    depth = 0 if rel_dir in ("", ".") else len(rel_dir.split(os.sep))
    prefix = "./" if depth == 0 else "../" * depth

    def repl(m):
        pre, url, post = m.groups()
        # leave absolute canonical/OG urls alone (they start with http) - not matched anyway
        # keep any ?query#fragment tail after the filename, not before it
        cut = len(url)
        for ch in "?#":
            i = url.find(ch)
            if i != -1:
                cut = min(cut, i)
        path, tail = url[:cut], url[cut:]

        if path.startswith("/"):
            path = prefix + path.lstrip("/")   # root-absolute -> relative to this page
        # already-relative links ("./x/", "../x/") keep the depth build.py gave them

        if path.endswith("/") or path in ("", "."):
            path += "index.html"
        elif "." not in os.path.basename(path):
            path = path.rstrip("/") + "/index.html"
        return pre + path + tail + post

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
