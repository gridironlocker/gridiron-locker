"""Private local dashboard for the OSINT prospect engine.

``python3 -m marketing.osint ui`` serves the LOCAL prospect database over
HTTP on 127.0.0.1 with a random per-launch token. It is the ONLY component
that ever shows full prospect rows (names, emails, notes) outside the CLI —
and it only ever shows them to whoever holds the token on this machine.

Deliberate limits (this is what keeps it private):

* stdlib-only (``http.server``), single-threaded: one local user, and the
  single SQLite connection is never shared across threads;
* binds 127.0.0.1 by default — ``--host 0.0.0.0`` is only for sandbox/VM
  previews, still token-gated;
* every route requires the token (``?token=`` or ``X-Osint-Token``);
  without it the server returns 403 and touches no data;
* responses are ``Cache-Control: no-store`` and carry noindex;
* NOTHING here writes to ``site/``, ``data/`` or the committed page JSON —
  reads and outreach writes (status/note) stay inside ``OSINT_STATE_DIR``.
"""
from __future__ import annotations

import hmac
import html
import http.server
import json
import secrets
import urllib.parse
import webbrowser

from . import STATUSES, config
from . import report as report_mod

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8520

#: Hard cap on POST bodies (notes are short text, not uploads).
MAX_BODY = 64 * 1024

PER_PAGE = 50

CSS = """
:root{color-scheme:dark;--ink:#eef5ff;--muted:#93a6c2;--canvas:#070e1a;
--panel:#0f1e36;--line:rgba(178,203,238,.14);--blue:#7cc8ff;--green:#72e0ba;
--amber:#ffb15a;--red:#ff7d7d;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--ink);line-height:1.5}
.wrap{width:min(1200px,calc(100% - 40px));margin:0 auto;padding:28px 0 60px}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.top{display:flex;gap:14px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}
.badge{display:inline-block;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;
color:var(--amber);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:14px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-size:1.5rem}.stat span{color:var(--muted);font-size:.8rem}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:.9rem}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.76rem;text-transform:uppercase;letter-spacing:.06em}
.mut{color:var(--muted)}form.inline{display:flex;gap:8px;flex-wrap:wrap;align-items:end}
label{font-size:.78rem;color:var(--muted)}label span{display:block;margin-bottom:2px}
input,select,textarea{background:#0b1526;border:1px solid var(--line);color:var(--ink);
border-radius:8px;padding:7px 10px;font:inherit}textarea{width:100%;min-height:70px}
button{background:var(--blue);border:0;color:#05121f;font-weight:700;border-radius:8px;
padding:8px 14px;cursor:pointer}button.ghost{background:transparent;color:var(--blue);
border:1px solid var(--line)}pre{background:#0b1526;border:1px solid var(--line);
border-radius:8px;padding:10px;overflow:auto;font-size:.8rem;white-space:pre-wrap}
.pager{margin-top:12px;display:flex;gap:12px;align-items:center}
"""


def new_token() -> str:
    """Random per-launch dashboard token (URL-safe, ~22 chars)."""
    return secrets.token_urlsafe(16)


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def maybe_link(value: str) -> str:
    """Render http(s) URLs as links, everything else as plain escaped text."""
    text = "" if value is None else str(value)
    if text.startswith(("https://", "http://")) and '"' not in text and " " not in text:
        return f'<a href="{esc(text)}" rel="noreferrer">{esc(text)}</a>'
    return esc(text)


def layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>{esc(title)} | OSINT Dashboard (private)</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<div class="top"><div><span class="badge">private &middot; local only</span>
<h1 style="margin:.3em 0">{esc(title)}</h1></div></div>
{body}
</div>
</body>
</html>
"""


def _nav(token: str) -> str:
    q = urllib.parse.urlencode({"token": token})
    return (
        f'<p class="mut"><a href="/?{q}">Overview</a> &middot; '
        f'<a href="/prospects?{q}">Prospects</a></p>'
    )


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    server_version = "GlOsintDashboard/1.0"

    @property
    def repo(self):
        # Per-request repository, opened in the serving thread (a SQLite
        # connection cannot cross threads) — set up by do_GET/do_POST.
        return self._repo

    @property
    def token(self) -> str:
        return self.server.osint_token

    # -- plumbing ------------------------------------------------------
    def _query(self) -> dict:
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

    def _authorized(self, extra: dict | None = None) -> bool:
        query = self._query()
        supplied = None
        for source in (extra or {}, query):
            values = source.get("token")
            if values:
                supplied = values[0]
                break
        if supplied is None:
            supplied = self.headers.get("X-Osint-Token")
        if not supplied or not isinstance(supplied, str):
            return False
        try:
            return hmac.compare_digest(supplied, self.token)
        except (TypeError, ValueError):
            return False

    def _send_html(self, title: str, body: str, status: int = 200) -> None:
        data = layout(title, body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _deny(self) -> None:
        self._send_html(
            "Token required",
            "<div class='card'><p>This dashboard is private. Reload with the "
            "per-launch token the <code>ui</code> command printed, e.g. "
            "<code>/?token=&lt;token&gt;</code>, or send it as the "
            "<code>X-Osint-Token</code> header.</p></div>",
            status=403,
        )

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _with_token(self, path: str) -> str:
        sep = "&" if "?" in path else "?"
        return f"{path}{sep}{urllib.parse.urlencode({'token': self.token})}"

    # -- routes --------------------------------------------------------
    def _with_repo(self, func):
        """Open a fresh repository in the serving thread, close it after."""
        repo = self.server.osint_repo_factory()
        self._repo = repo
        try:
            return func()
        finally:
            self._repo = None
            repo.conn.close()

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        parsed = urllib.parse.urlparse(self.path)
        if not self._authorized():
            self._deny()
            return
        self._with_repo(lambda: self._route_get(parsed))

    def _route_get(self, parsed) -> None:
        if parsed.path == "/":
            self._send_html("OSINT overview", self._overview())
        elif parsed.path == "/prospects":
            self._send_html("Prospects", self._prospect_list(self._query()))
        elif parsed.path == "/prospect":
            self._prospect_detail(self._query())
        else:
            self._send_html("Not found", "<div class='card'><p>Unknown path.</p></div>", 404)

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY or length < 0:
            self._send_html("Too large", "<div class='card'><p>Body too large.</p></div>", 413)
            return
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if not self._authorized(form):
            self._deny()
            return
        self._with_repo(lambda: self._route_post(urllib.parse.urlparse(self.path).path, form))

    def _route_post(self, path: str, form: dict) -> None:
        if path == "/prospect/status":
            self._post_status(form)
        elif path == "/prospect/note":
            self._post_note(form)
        else:
            self._send_html("Not found", "<div class='card'><p>Unknown path.</p></div>", 404)

    # -- pages ---------------------------------------------------------
    def _overview(self) -> str:
        stats = report_mod.stats_json(self.repo)
        last_run = self.repo.last_run()
        matches = self.repo.list_matches("POSSIBLE_MATCH")
        cards = "".join(
            f"<div class='stat'><b>{stats['total']}</b><span>prospects</span></div>"
            f"<div class='stat'><b>{stats['with_public_email']}</b><span>with public email</span></div>"
            f"<div class='stat'><b>{stats['verified_email']}</b><span>verified email</span></div>"
            f"<div class='stat'><b>{len(matches)}</b><span>possible matches to review</span></div>"
        )

        def _table(title: str, mapping: dict, labels: dict | None = None) -> str:
            rows = "".join(
                f"<tr><td>{esc((labels or {}).get(key, key))}</td><td>{value}</td></tr>"
                for key, value in sorted(mapping.items(), key=lambda kv: (-kv[1], str(kv[0])))
            ) or "<tr><td class='mut'>none yet</td><td>0</td></tr>"
            return f"<div class='card'><h3 style='margin:0'>{esc(title)}</h3><table>{rows}</table></div>"

        if last_run:
            run_html = (
                f"<div class='card'><h3 style='margin:0'>Last run</h3><p class='mut'>"
                f"{esc(last_run.get('mode') or '?')} &middot; started "
                f"{esc(last_run.get('started_at') or '?')} &middot; "
                f"new {last_run.get('new', 0)}, updated {last_run.get('updated', 0)}, "
                f"unchanged {last_run.get('unchanged', 0)}</p></div>"
            )
        else:
            run_html = (
                "<div class='card'><h3 style='margin:0'>Last run</h3>"
                "<p class='mut'>No collection run recorded yet.</p></div>"
            )
        return (
            _nav(self.token)
            + f"<div class='grid'>{cards}</div>"
            + _table("By team", stats["by_team"], config.TEAM_LABELS)
            + _table("By prospect type", stats["by_type"])
            + _table("By priority", stats["by_priority"])
            + run_html
        )

    def _prospect_list(self, query: dict) -> str:
        def _one(name: str, default: str = "") -> str:
            values = query.get(name)
            return values[0] if values else default

        team = _one("team")
        ptype = _one("type")
        status = _one("status")
        text = _one("q").strip()
        try:
            min_score = max(0, int(_one("min_score", "0") or 0))
        except ValueError:
            min_score = 0
        try:
            page = max(1, int(_one("page", "1") or 1))
        except ValueError:
            page = 1

        rows = self.repo.list_prospects(
            min_score=min_score, team=team or None, limit=2000,
        )
        if ptype:
            rows = [r for r in rows if (r.get("prospect_type") or "") == ptype]
        if status:
            rows = [r for r in rows if (r.get("status") or "") == status]
        if text:
            needle = text.lower()
            rows = [
                r for r in rows
                if needle in " ".join(
                    str(r.get(field) or "") for field in (
                        "display_name", "username", "public_email",
                        "website", "platform",
                    )
                ).lower()
            ]

        total = len(rows)
        pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
        page = min(page, pages)
        visible = rows[(page - 1) * PER_PAGE:page * PER_PAGE]

        def _options(values: list[str], current: str) -> str:
            out = "<option value=''>all</option>"
            for value in values:
                selected = " selected" if value == current else ""
                out += f"<option value='{esc(value)}'{selected}>{esc(value)}</option>"
            return out

        form = (
            "<div class='card'><form class='inline' method='get' action='/prospects'>"
            f"<input type='hidden' name='token' value='{esc(self.token)}'>"
            f"<label><span>Team</span><select name='team'>"
            f"{_options(config.TEAM_SLUGS, team)}</select></label>"
            f"<label><span>Min score</span><input name='min_score' size='4' value='{min_score}'></label>"
            f"<label><span>Search</span><input name='q' value='{esc(text)}' placeholder='name, email, domain…'></label>"
            "<button type='submit'>Filter</button></form></div>"
        )
        def _row_html(r) -> str:
            detail = esc(self._with_token("/prospect?id=%d" % r["id"]))
            name = esc(r.get("display_name") or r.get("username") or "(unnamed)")
            return (
                "<tr>"
                f"<td>{r['id']}</td><td>{r.get('relevance_score', 0)}</td>"
                f"<td>{esc(r.get('priority') or '')}</td>"
                f"<td>{esc(r.get('team') or '')}</td>"
                f"<td>{esc(r.get('prospect_type') or '')}</td>"
                f"<td><a href='{detail}'>{name}</a></td>"
                f"<td>{esc(r.get('public_email') or '—')}</td>"
                f"<td>{esc(r.get('status') or '')}</td>"
                "</tr>"
            )

        body_rows = "".join(_row_html(r) for r in visible) or (
            "<tr><td colspan='8' class='mut'>No prospects match.</td></tr>"
        )
        pager = ""
        if pages > 1:
            base = {k: _one(k) for k in ("team", "type", "status", "q", "min_score") if _one(k)}
            def _link(label: str, target: int) -> str:
                params = {**base, "page": str(target)}
                return f"<a href='{esc(self._with_token('/prospects?' + urllib.parse.urlencode(params)))}'>{label}</a>"
            pager = (
                f"<div class='pager'><span class='mut'>Page {page} of {pages} "
                f"({total} match(es))</span>"
                + (_link("← newer", page - 1) if page > 1 else "")
                + (_link("older →", page + 1) if page < pages else "")
                + "</div>"
            )
        return (
            _nav(self.token) + form
            + f"<div class='card'><h3 style='margin:0'>{total} prospect(s)</h3>"
            f"<table><tr><th>ID</th><th>Score</th><th>Priority</th><th>Team</th>"
            f"<th>Type</th><th>Name</th><th>Email</th><th>Status</th></tr>{body_rows}</table>"
            f"{pager}</div>"
        )

    def _prospect_detail(self, query: dict) -> None:
        try:
            prospect_id = int((query.get("id") or [""])[0])
        except ValueError:
            prospect_id = 0
        prospect = self.repo.get(prospect_id) if prospect_id else None
        if not prospect:
            self._send_html("Not found", "<div class='card'><p>No such prospect.</p></div>", 404)
            return

        fields: list[tuple[str, str]] = [
            ("Name", esc(prospect.get("display_name") or "—")),
            ("Platform", esc(prospect.get("platform") or "—")),
            ("Username", esc(prospect.get("username") or "—")),
            ("Profile", maybe_link(prospect.get("profile_url") or "")),
            ("Website", maybe_link(prospect.get("website") or "")),
            ("Team", esc(prospect.get("team") or "—")),
            ("Type", esc(prospect.get("prospect_type") or "—")),
            ("Email", esc(prospect.get("public_email") or "—")),
            ("Email verified", esc(prospect.get("email_verified") or "—")),
            ("Contact source", esc(prospect.get("contact_source") or "—")),
            ("Scores", f"{prospect.get('relevance_score', 0)} rel / "
                       f"{prospect.get('commercial_score', 0)} comm / "
                       f"{prospect.get('confidence_score', 0)} conf"),
            ("Priority", esc(prospect.get("priority") or "—")),
            ("Status", esc(prospect.get("status") or "—")),
            ("Score reason", esc(prospect.get("score_reason") or "—")),
            ("Source", maybe_link(prospect.get("source_url") or "")),
            ("Discovered", esc(prospect.get("discovered_at") or "—")),
            ("Last seen", esc(prospect.get("last_seen_at") or "—")),
        ]
        rows = "".join(f"<tr><th style='width:150px'>{label}</th><td>{value}</td></tr>" for label, value in fields)
        breakdown = json.dumps(prospect.get("score_breakdown") or {}, indent=2, sort_keys=True)
        options = "".join(
            f"<option value='{s}'{' selected' if s == prospect.get('status') else ''}>{s}</option>"
            for s in STATUSES
        )
        token_field = f"<input type='hidden' name='token' value='{esc(self.token)}'>"
        body = (
            _nav(self.token)
            + f"<div class='card'><h2 style='margin:0'>#{prospect['id']} "
            f"{esc(prospect.get('display_name') or prospect.get('username') or '(unnamed)')}</h2>"
            f"<table>{rows}</table>"
            f"<h3>Score breakdown</h3><pre>{esc(breakdown)}</pre>"
            f"<h3>Notes</h3><pre>{esc(prospect.get('notes') or '(none)')}</pre></div>"
            f"<div class='card'><h3 style='margin-top:0'>Outreach</h3>"
            f"<form class='inline' method='post' action='/prospect/status'>"
            f"{token_field}<input type='hidden' name='id' value='{prospect['id']}'>"
            f"<label><span>Status</span><select name='to'>{options}</select></label>"
            f"<button type='submit'>Update status</button></form>"
            f"<form method='post' action='/prospect/note' style='margin-top:12px'>"
            f"{token_field}<input type='hidden' name='id' value='{prospect['id']}'>"
            f"<label><span>Add note</span><textarea name='text'></textarea></label>"
            f"<p><button type='submit'>Add note</button></p></form></div>"
        )
        self._send_html(f"Prospect #{prospect['id']}", body)

    def _post_status(self, form: dict) -> None:
        try:
            prospect_id = int((form.get("id") or [""])[0])
        except ValueError:
            prospect_id = 0
        target = (form.get("to") or [""])[0]
        if not prospect_id or not self.repo.get(prospect_id):
            self._send_html("Not found", "<div class='card'><p>No such prospect.</p></div>", 404)
            return
        if target not in STATUSES:
            self._send_html("Bad request", "<div class='card'><p>Unknown status.</p></div>", 400)
            return
        self.repo.update_status(prospect_id, target)
        self._redirect(self._with_token(f"/prospect?id={prospect_id}"))

    def _post_note(self, form: dict) -> None:
        try:
            prospect_id = int((form.get("id") or [""])[0])
        except ValueError:
            prospect_id = 0
        text = (form.get("text") or [""])[0].strip()
        if not prospect_id or not self.repo.get(prospect_id):
            self._send_html("Not found", "<div class='card'><p>No such prospect.</p></div>", 404)
            return
        if not text:
            self._send_html("Bad request", "<div class='card'><p>Note text is empty.</p></div>", 400)
            return
        self.repo.add_note(prospect_id, text)
        self._redirect(self._with_token(f"/prospect?id={prospect_id}"))

    def log_message(self, *args) -> None:  # keep the console readable
        pass


def make_server(host: str, port: int, token: str, repo_factory):
    """Build (but do not start) the dashboard server.

    ``repo_factory`` is a zero-argument callable returning a fresh
    ``Repository``. It is called once per request IN the serving thread, so
    no SQLite connection ever crosses a thread boundary. The server itself
    stays single-threaded: this is a one-user local tool.
    """
    server = http.server.HTTPServer((host, port), DashboardHandler)
    server.osint_repo_factory = repo_factory
    server.osint_token = token
    return server


def dashboard_url(host: str, port: int, token: str, path: str = "/") -> str:
    shown = "127.0.0.1" if host == "0.0.0.0" else host
    return f"http://{shown}:{port}{path}?token={token}"


def serve(host: str, port: int, token: str, repo_factory, open_browser: bool = False) -> int:
    try:
        server = make_server(host, port, token, repo_factory)
    except OSError as err:
        print(f"Cannot serve the dashboard on {host}:{port} ({err})")
        return 1
    url = dashboard_url(host, server.server_address[1], token)
    print("OSINT dashboard (private — local database only):")
    print(f"  {url}")
    print("Press Ctrl-C to stop. The token is random per launch; the URL above is the key.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as err:  # noqa: BLE001 — opening a browser must never kill serving
            print(f"(could not open a browser: {err})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()
    return 0
