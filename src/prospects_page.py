#!/usr/bin/env python3
"""Render the aggregate-only OSINT prospects dashboard.

Reads the committed ``marketing/osint/page/prospects.json`` (aggregate counts
+ salted page-password hash, no PII — written by
``python3 -m marketing.osint build-page``) and emits the internal dashboard:

* ``ops/prospects/index.html`` — the source-side copy, and
* ``site/ops/prospects/index.html`` — the published copy (byte-identical).

The page is robots-disallowed (``/ops/``), carries noindex, is never linked
from public nav or the sitemap, and hides its contents behind a client-side
password gate. Two honesty notes, stated on the page itself:

* the gate deters casual browsing — it is not encryption (anyone reading the
  HTML source sees the same aggregates). Real secrecy comes from the content
  being aggregate-only, which ``marketing/osint/audit.py`` enforces.
* the numbers only change when the owner regenerates them after a collection
  run — ``generated_at`` says how fresh they are.

Usage (single-page regeneration — no full rebuild, no date re-stamps):

    OSINT_PAGE_PASSWORD=... python3 -m marketing.osint build-page
    python3 src/prospects_page.py

``src/build.py`` calls ``render_into()`` from ``sync_ops()`` on every full
rebuild, so CI reproduces the same bytes deterministically. A missing or
invalid JSON renders an honest placeholder instead of failing — the build
must never REQUIRE anything in ``marketing/`` (repo contract §3.4), so this
module reads the file directly and never imports the marketing package. The
template uses relative links only, so the full build's ``relativise()`` pass
leaves the output unchanged.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_JSON = ROOT / "marketing" / "osint" / "page" / "prospects.json"
OPS_OUT = ROOT / "ops" / "prospects" / "index.html"
SITE_OUT = ROOT / "site" / "ops" / "prospects" / "index.html"

#: Must equal marketing.osint.page.SALT_PREFIX (asserted by the test suite —
#: the two live in different packages on purpose, so the sync is by test).
GATE_SALT_PREFIX = "gl-osint-page-v1:"

CSS = """
:root{color-scheme:dark;--ink:#eef5ff;--muted:#93a6c2;--canvas:#070e1a;
--panel:#0f1e36;--line:rgba(178,203,238,.14);--blue:#7cc8ff;--green:#72e0ba;
--amber:#ffb15a;--red:#ff7d7d;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--ink);line-height:1.55}
.wrap{width:min(1000px,calc(100% - 40px));margin:0 auto;padding:36px 0 60px}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.badge{display:inline-block;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;
color:var(--amber);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin-top:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:14px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-size:1.6rem}.stat span{color:var(--muted);font-size:.8rem}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:.92rem}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;font-size:.76rem;text-transform:uppercase;letter-spacing:.06em}
.mut{color:var(--muted)}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
input{background:#0b1526;border:1px solid var(--line);color:var(--ink);
border-radius:8px;padding:9px 12px;font:inherit;min-width:min(300px,100%)}
button{background:var(--blue);border:0;color:#05121f;font-weight:700;border-radius:8px;
padding:10px 18px;cursor:pointer;font:inherit}
.err{color:var(--red);font-weight:600}
h1{margin:.3em 0 .1em}h2{margin:.2em 0 .4em}h3{margin:.2em 0}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:0 18px}
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _table(title: str, mapping: dict, labels: dict | None = None) -> str:
    # Sorted (unlisted bucket last) so rendering is byte-identical no matter
    # what key order the JSON happened to load in.
    rows = ""
    for key, value in sorted(mapping.items(), key=lambda kv: (kv[0] == "other", kv[0])):
        if key == "other":
            label = "Other / unlisted"
        elif labels and key in labels:
            label = labels[key]
        else:
            label = key.replace("_", " ").title()
        rows += f"<tr><td>{esc(label)}</td><td>{value}</td></tr>"
    return f"<div class='card'><h3>{esc(title)}</h3><table>{rows}</table></div>"


def _last_run_html(last_run: dict | None) -> str:
    if not last_run:
        return (
            "<div class='card'><h3>Last collection run</h3>"
            "<p class='mut'>No collection run recorded yet.</p></div>"
        )
    return (
        "<div class='card'><h3>Last collection run</h3><table>"
        f"<tr><td>Mode</td><td>{esc(last_run.get('mode') or '?')}</td></tr>"
        f"<tr><td>Started</td><td>{esc(last_run.get('started_at') or '?')}</td></tr>"
        f"<tr><td>Finished</td><td>{esc(last_run.get('finished_at') or '?')}</td></tr>"
        f"<tr><td>New / updated / unchanged</td><td>"
        f"{last_run.get('new', 0)} / {last_run.get('updated', 0)} / "
        f"{last_run.get('unchanged', 0)}</td></tr>"
        "</table></div>"
    )


def _gate_script() -> str:
    # The salt prefix below must stay identical to
    # marketing.osint.page.SALT_PREFIX (test-enforced).
    return """
<script>
(function(){
var gate=document.getElementById("gate"),content=document.getElementById("content"),
pw=document.getElementById("pw"),go=document.getElementById("go"),err=document.getElementById("gate-err");
function show(){content.hidden=false;gate.hidden=true;}
function fail(msg){err.textContent=msg;err.hidden=false;}
async function hex(str){
var buf=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(str));
return Array.from(new Uint8Array(buf)).map(function(b){return b.toString(16).padStart(2,"0");}).join("");
}
async function unlock(){
err.hidden=true;
try{
var digest=await hex("GATE_SALT_PREFIX_PLACEHOLDER"+pw.value);
if(digest===gate.getAttribute("data-pass-sha256")){
try{sessionStorage.setItem("gl-osint-prospects","1");}catch(e){}
show();
}else{fail("Wrong password.");}
}catch(e){fail("Could not verify (this gate needs a secure context).");}
}
if(!window.crypto||!crypto.subtle){
fail("Password verification needs a secure context — open the store URL.");
go.disabled=true;
return;
}
try{if(sessionStorage.getItem("gl-osint-prospects")==="1"){show();return;}}catch(e){}
go.addEventListener("click",unlock);
pw.addEventListener("keydown",function(e){if(e.key==="Enter"){unlock();}});
})();
</script>
""".replace("GATE_SALT_PREFIX_PLACEHOLDER", GATE_SALT_PREFIX)


def render(data: dict | None) -> str:
    """Render the full dashboard HTML (placeholder when data is None)."""
    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#070e1a">
<title>Prospect Pipeline | Ops | Gridiron Locker</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<p class="mut"><a href="../">← Ops index</a></p>
<p><span class="badge">internal &middot; aggregate only</span></p>
<h1>Prospect pipeline</h1>
"""
    foot = "</div>\n</body>\n</html>\n"
    if not data:
        return head + (
            "<!-- osint-page-placeholder: no page data generated yet -->\n"
            "<div class='card'><h2>Not generated yet</h2>"
            "<p class='mut'>No prospect aggregates have been published. "
            "On the machine that runs collection:</p>"
            "<p><code>OSINT_PAGE_PASSWORD=... python3 -m marketing.osint build-page</code><br>"
            "<code>python3 src/prospects_page.py</code></p></div>\n"
        ) + foot

    totals = data.get("totals", {})
    labels = data.get("team_labels", {})
    cards = (
        f"<div class='stat'><b>{totals.get('prospects', 0)}</b><span>prospects tracked</span></div>"
        f"<div class='stat'><b>{totals.get('with_public_email', 0)}</b><span>with public email</span></div>"
        f"<div class='stat'><b>{totals.get('verified_email', 0)}</b><span>verified email</span></div>"
        f"<div class='stat'><b>{totals.get('suppressed_identities', 0)}</b><span>suppressed identities</span></div>"
    )
    content = (
        f"<p class='mut'>Aggregate counts as of {esc(data.get('generated_at') or '?')} "
        f"(no names, emails or URLs are published on this page).</p>"
        f"<div class='grid'>{cards}</div>"
        "<div class='cols'>"
        + _table("By team", data.get("by_team", {}), labels)
        + _table("By prospect type", data.get("by_type", {}))
        + "</div><div class='cols'>"
        + _table("By priority", data.get("by_priority", {}))
        + _table("By outreach status", data.get("by_status", {}))
        + "</div>"
        + _last_run_html(data.get("last_run"))
        + "<div class='card'><h3>About this page</h3><p class='mut'>"
        "Counts only — prospect identities stay in the private local database. "
        "The gate deters casual browsing; it is not encryption. "
        "Regenerate after each collection run with "
        "<code>build-page</code> + <code>src/prospects_page.py</code>."
        "</p></div>"
    )
    gate = (
        f"<div class='card' id='gate' data-pass-sha256='{esc(data.get('password_sha256') or '')}'>"
        "<h2>Restricted</h2>"
        "<p class='mut'>The prospect pipeline is owner-only. Enter the page password.</p>"
        "<div class='row'><input type='password' id='pw' autocomplete='off' "
        "placeholder='Page password' aria-label='Page password'>"
        "<button id='go' type='button'>Unlock</button></div>"
        "<p class='err' id='gate-err' hidden></p></div>"
    )
    return head + gate + f"<div id='content' hidden>\n{content}\n</div>\n" + _gate_script() + foot


def load_data(path: Path | None = None) -> dict | None:
    """Read page data without importing the marketing package (build decoupling).

    Returns None when the file is missing or invalid — the caller renders the
    placeholder. Never raises for content problems.
    """
    target = Path(path) if path else PAGE_JSON
    try:
        obj = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("totals"), dict):
        return None
    return obj


def render_into(path: Path | str) -> Path:
    """Render from the committed JSON (or placeholder) into ``path``."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(load_data()), encoding="utf-8")
    return out


def main() -> int:
    data = load_data()
    if data is None:
        print(f"warning: {PAGE_JSON} missing or invalid — emitting placeholder")
    for target in (OPS_OUT, SITE_OUT):
        rendered = render_into(target)
        print(f"emitted {rendered} ({rendered.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
