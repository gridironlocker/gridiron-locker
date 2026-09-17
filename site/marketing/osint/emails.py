"""Public-email extraction and honest validation.

Rules from the engine spec that this module enforces:

* Only emails that are actually published on the page/feed are collected.
* Obfuscated-but-published addresses ("name AT domain DOT com") are decoded —
  the owner published them for contact; decoding is not guessing.
* Email addresses are NEVER generated, guessed or inferred from names.
* Validation never sends email and never speaks SMTP. It checks syntax,
  domain resolvability, MX records (via a tiny stdlib DNS client) and a
  disposable-domain list. Anything uncertain is marked UNVERIFIED.
"""
from __future__ import annotations

import re
import socket
import struct
import time

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")

_AT_TOKENS = re.compile(r"(?i)(?:\[at\]|\(at\)|\{at\}|\[@\]|\(@\)|&#64;|%40|\s@\s|\s+at\s+)")
_DOT_TOKENS = re.compile(r"(?i)(?:\[dot\]|\(dot\)|\{dot\}|\s+dot\s+)")

#: File-ish / code-ish TLDs that mean the regex caught an asset, not an address.
JUNK_TLDS = {
    "png", "jpg", "jpeg", "gif", "webp", "svg", "ico", "js", "css", "scss",
    "woff", "woff2", "ttf", "eot", "html", "htm", "php", "asp", "aspx", "jsp",
    "py", "rb", "go", "rs", "ts", "tsx", "jsx", "json", "xml", "csv", "md",
    "yml", "yaml", "ini", "map", "webmanifest",
}

#: Domains that are placeholders, tracking noise or CMS artefacts, never
#: real published business contacts.
JUNK_DOMAINS = {
    "example.com", "example.org", "example.net", "domain.com", "domain.net",
    "yourdomain.com", "yoursite.com", "mysite.com", "website.com", "site.com",
    "email.com", "test.com", "sample.com", "abc.com", "url.com", "foo.com",
    "sentry.io", "sentry-next.wixpress.com", "wixpress.com", "godaddy.com",
    "squarespace.com", "squarespace-mail.com", "shopify.com", "cloudflare",
    "sentry.wixpress.com", "mozmail.com", "simplelogin.io", "keapmail.com",
}

#: Common disposable email providers (checked by domain, best effort).
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "yopmail.com",
    "temp-mail.org", "tempmail.com", "trashmail.com", "sharklasers.com",
    "getnada.com", "dispostable.com", "maildrop.cc", "fakeinbox.com",
    "throwawaymail.com", "mailnesia.com", "mytemp.email", "moakt.com",
}

#: Role accounts are preferred for business outreach (spec: business emails).
ROLE_LOCALS = {
    "info", "contact", "hello", "hi", "press", "media", "business",
    "bookings", "booking", "advertising", "ads", "sales", "support", "team",
    "admin", "editor", "tips", "inquiries", "enquiries", "partnerships",
    "partners", "collabs", "collab", "shop", "store", "help", "general",
    "office", "mail",
}

_CONTACT_CONTEXT_WORDS = (
    "contact", "business", "inquiry", "inquiries", "press", "reach",
    "email", "e-mail", "collab", "sponsor", "advertis", "booking",
    "partnership", "media", "tips",
)


def _decode_obfuscations(text: str) -> str:
    text = _AT_TOKENS.sub("@", text)
    text = _DOT_TOKENS.sub(".", text)
    return text


def is_plausible(email: str) -> bool:
    """Cheap static sanity check: syntax + not a placeholder/asset artefact."""
    email = email.strip().strip(".").lower()
    if not EMAIL_RE.fullmatch(email):
        return False
    local, _, domain = email.partition("@")
    if domain in JUNK_DOMAINS:
        return False
    tld = domain.rsplit(".", 1)[-1]
    if tld in JUNK_TLDS:
        return False
    if any(domain.endswith("." + bad) for bad in JUNK_DOMAINS):
        return False
    if domain.startswith(".") or ".." in domain or local.startswith(".") or local.endswith("."):
        return False
    if len(email) > 254 or len(local) > 64:
        return False
    return True


def clean_address(raw: str) -> str | None:
    """Normalise one candidate address; None when implausible."""
    candidate = _decode_obfuscations(raw).strip().strip("<>").strip('"').strip(".")
    candidate = candidate.split("?", 1)[0].strip()
    match = EMAIL_RE.search(candidate)
    if not match:
        return None
    address = match.group(0).lower()
    return address if is_plausible(address) else None


def extract_from_text(text: str) -> list[str]:
    """All plausible, actually-published addresses in a text blob."""
    seen: list[str] = []
    decoded = _decode_obfuscations(text)
    for match in EMAIL_RE.finditer(decoded):
        address = match.group(0).lower()
        if is_plausible(address) and address not in seen:
            seen.append(address)
    return seen


def extract_from_page(html: bytes | str, page_url: str = "") -> list[dict]:
    """Extract candidate public business emails from an HTML page.

    Returns a list of {email, in_mailto, context_hit} dicts, best first:
    mailto: links and addresses near contact words outrank stray matches.
    """
    from .http import parse_html  # local import avoids a cycle at import time

    parser = parse_html(html)
    candidates: dict[str, dict] = {}

    for raw in parser.mailto_links:
        address = clean_address(raw)
        if address and address not in candidates:
            candidates[address] = {"email": address, "in_mailto": True, "context_hit": True}

    text = parser.text
    lowered = text.lower()
    for address in extract_from_text(text):
        if address in candidates:
            continue
        idx = lowered.find(address)
        window = lowered[max(0, idx - 120): idx + len(address) + 120]
        candidates[address] = {
            "email": address,
            "in_mailto": False,
            "context_hit": any(w in window for w in _CONTACT_CONTEXT_WORDS),
        }

    def rank(item: dict) -> tuple:
        return (item["in_mailto"], item["context_hit"], address_role_rank(item["email"]))

    return sorted(candidates.values(), key=rank, reverse=True)


def address_role_rank(email: str) -> int:
    """3 = role account, 2 = personal-looking at own domain, 1 = other."""
    local, _, domain = email.partition("@")
    if local in ROLE_LOCALS:
        return 3
    site = domain.split(".")[0]
    if local and site and local.startswith(site):
        return 2
    return 1


# --------------------------------------------------------------------------
# Minimal stdlib DNS client — MX and A lookups without third-party deps.
# It sends one UDP query with recursion-desired to the system resolver(s)
# and parses the response (including name compression). Anything unexpected
# returns an empty list, which callers treat as UNVERIFIED.
# --------------------------------------------------------------------------

_DNS_RESOLVERS: list[str] | None = None


def _resolvers() -> list[str]:
    global _DNS_RESOLVERS
    if _DNS_RESOLVERS is None:
        found = []
        try:
            with open("/etc/resolv.conf", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip().startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            found.append(parts[1])
        except OSError:
            pass
        _DNS_RESOLVERS = found or ["1.1.1.1", "8.8.8.8"]
    return _DNS_RESOLVERS


def _encode_qname(name: str) -> bytes:
    return b"".join(
        bytes([len(label)]) + label.encode("idna" if not label.isascii() else "ascii")
        for label in name.split(".")
    ) + b"\x00"


def _read_name(payload: bytes, offset: int) -> tuple[str, int]:
    labels: list[bytes] = []
    jumps = 0
    while True:
        if offset >= len(payload):
            return "", offset
        length = payload[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:  # compression pointer
            if offset + 1 >= len(payload):
                return "", offset
            pointer = ((length & 0x3F) << 8) | payload[offset + 1]
            offset += 2
            jumps += 1
            if jumps > 8:
                return "", offset
            sub, _ = _read_name(payload, pointer)
            labels.append(sub.encode())
            return b".".join(labels).decode(), offset
        labels.append(payload[offset + 1: offset + 1 + length])
        offset += 1 + length
    return b".".join(labels).decode(), offset


def dns_lookup(name: str, qtype: int = 15, timeout: float = 3.0) -> "list[str] | None":
    """Query MX (qtype 15) or A (qtype 1) records.

    Returns a list of records, [] when the resolver answered with none, or
    None when the query could not be made/answered at all (offline etc.) —
    callers must treat None as "unknown", never as "no records".
    """
    query_id = int(time.time()) & 0xFFFF
    header = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
    question = _encode_qname(name) + struct.pack(">HH", qtype, 1)
    packet = header + question
    for resolver in _resolvers():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(packet, (resolver, 53))
                data, _ = sock.recvfrom(4096)
        except OSError:
            continue
        try:
            _, flags, qd, an, _, _ = struct.unpack(">HHHHHH", data[:12])
            if not (flags & 0x8000):
                continue  # this resolver did not answer; try the next
            offset = 12
            for _ in range(qd):
                _, offset = _read_name(data, offset)
                offset += 4
            records: list[str] = []
            for _ in range(an):
                _, offset = _read_name(data, offset)
                rtype, _rclass, _ttl, rdlen = struct.unpack(">HHIH", data[offset: offset + 10])
                offset += 10
                rdata = data[offset: offset + rdlen]
                if rtype == qtype and qtype == 15 and rdlen >= 3:
                    pref = struct.unpack(">H", rdata[:2])[0]
                    exchange, _ = _read_name(data, offset + 2)
                    records.append(f"{pref} {exchange.rstrip('.')}")
                elif rtype == qtype and qtype == 1 and rdlen == 4:
                    records.append(socket.inet_ntoa(rdata))
                offset += rdlen
            return records
        except (struct.error, UnicodeError):
            return None
    return None


# --------------------------------------------------------------------------
# Validation verdicts
# --------------------------------------------------------------------------

#: Verdicts, best to worst. VERIFIED_* mean the checks we can honestly run
# passed. UNVERIFIED means we could not check (e.g. no DNS available). We
# never claim an inbox exists — that would require sending mail.
VERDICTS = [
    "VERIFIED_MX",       # syntax OK, domain resolves, MX records exist
    "VERIFIED_DOMAIN",   # syntax OK, domain resolves (A record), no MX seen
    "UNVERIFIED",        # syntax OK, DNS check unavailable/inconclusive
    "DISPOSABLE",        # known disposable mailbox domain
    "INVALID_DOMAIN",    # domain does not resolve
    "INVALID_SYNTAX",
]


def validate(email: str, dns: bool = True) -> dict:
    """Honest validation. Never sends email; SMTP is never touched."""
    email = email.strip().lower()
    result = {
        "email": email,
        "syntax_ok": False,
        "domain_resolves": None,
        "mx_present": None,
        "disposable": False,
        "verdict": "INVALID_SYNTAX",
        "method": "syntax",
    }
    if not is_plausible(email):
        return result
    result["syntax_ok"] = True
    _, _, domain = email.partition("@")
    if domain in DISPOSABLE_DOMAINS or any(
        domain.endswith("." + d) for d in DISPOSABLE_DOMAINS
    ):
        result["disposable"] = True
        result["verdict"] = "DISPOSABLE"
        result["method"] = "disposable-domain-list"
        return result
    if not dns:
        result["verdict"] = "UNVERIFIED"
        result["method"] = "syntax-only"
        return result
    mx = dns_lookup(domain, qtype=15)
    if mx is None:
        # Query failed (offline / resolver unreachable): be honest.
        result["verdict"] = "UNVERIFIED"
        result["method"] = "dns-unavailable"
        return result
    if mx:
        result["mx_present"] = True
        result["domain_resolves"] = True
        result["verdict"] = "VERIFIED_MX"
        result["method"] = "dns-mx"
        return result
    a = dns_lookup(domain, qtype=1)
    if a is None:
        result["verdict"] = "UNVERIFIED"
        result["method"] = "dns-unavailable"
        return result
    if a:
        result["domain_resolves"] = True
        result["mx_present"] = False
        result["verdict"] = "VERIFIED_DOMAIN"
        result["method"] = "dns-a"
        return result
    # Both queries were ANSWERED with no records: no A, no MX.
    result["domain_resolves"] = False
    result["verdict"] = "INVALID_DOMAIN"
    result["method"] = "dns-empty-answer"
    return result


def mask(email: str) -> str:
    """Redact an address for logs and CI output: local part hidden."""
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"***@{domain}"
