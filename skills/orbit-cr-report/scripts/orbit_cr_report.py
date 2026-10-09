#!/usr/bin/env python3
"""
orbit_cr_report.py — Fetch an Orbit query, parse CRs, and render a report.

Fetches all CRs from an Orbit saved query, groups them by "Found on Product"
(target), sorts each group by age (oldest first), and shows the current
Software Image status for each CR.

Auth: Orbit uses Windows Negotiate/NTLM. The script tries, in order:
  1. requests-kerberos  (Kerberos ticket from klist)
  2. requests-ntlm      (NTLM with --user / ORBIT_USER + ORBIT_PASS)
  3. requests-negotiate (generic Negotiate)
  4. Session cookie     (--cookie / ORBIT_COOKIE env var)

Usage:
    python3 orbit_cr_report.py [OPTIONS]

Options:
    --query-id  INT     Orbit query ID (default: 111043)
    --url       URL     Orbit base URL (default: https://orbit-sd)
    --user      STR     DOMAIN\\username for NTLM (or set ORBIT_USER)
    --password  STR     Password for NTLM (or set ORBIT_PASS)
    --cookie    STR     Session cookie string (or set ORBIT_COOKIE)
    --output    FORMAT  Output format: table (default), json, csv, markdown
    --sort      FIELD   Sort within each target group: age (default), cr, status
    --max-age   DAYS    Highlight CRs older than N days (default: 90)
    --target    STR     Filter to a specific target product (substring match)
    --status    STR     Filter to a specific SW image status (substring match)
    --no-color          Disable ANSI colour output
    --verbose           Show HTTP request details
"""

import argparse
import csv
import datetime
import io
import json
import os
import sys
import textwrap
from typing import Optional

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
USE_COLOR = True

def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

RED    = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
GREEN  = lambda t: _c("32", t)
CYAN   = lambda t: _c("36", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _make_session(user: Optional[str], password: Optional[str], cookie: Optional[str]):
    """Return a requests.Session with the best available auth."""
    try:
        import requests
    except ImportError:
        _die("'requests' library not found. Install with: pip3 install requests")

    session = requests.Session()
    session.verify = False  # internal CA — suppress SSL warnings

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    if cookie:
        # Cookie-based auth (paste from browser)
        for part in cookie.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                session.cookies.set(k.strip(), v.strip())
        return session

    if user and password:
        # NTLM
        try:
            from requests_ntlm import HttpNtlmAuth
            session.auth = HttpNtlmAuth(user, password)
            return session
        except ImportError:
            pass
        # Fallback: basic auth (unlikely to work but worth trying)
        session.auth = (user, password)
        return session

    # Try Kerberos
    try:
        from requests_kerberos import HTTPKerberosAuth, OPTIONAL
        session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
        return session
    except ImportError:
        pass

    # Try generic Negotiate
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth
        session.auth = HttpNegotiateAuth()
        return session
    except ImportError:
        pass

    _warn("No auth library found. Trying unauthenticated (will likely get 401).")
    _warn("Install one of: requests-kerberos, requests-ntlm, requests-negotiate-sspi")
    return session


# ---------------------------------------------------------------------------
# Orbit API fetch
# ---------------------------------------------------------------------------

ORBIT_QUERY_ENDPOINTS = [
    # Try JSON API endpoints in order
    "/api/query/{qid}/results",
    "/api/v1/query/{qid}/results",
    "/api/v2/query/{qid}/results",
    "/query/{qid}/export?format=json",
    "/query/{qid}?format=json",
    "/query/{qid}/results.json",
]

ORBIT_EXPORT_ENDPOINTS = [
    "/query/{qid}/export?format=csv&allFields=true",
    "/query/{qid}/export?format=csv",
    "/query/{qid}.csv",
]


def fetch_query(base_url: str, query_id: int, session, verbose: bool = False) -> list:
    """
    Fetch all CRs from an Orbit saved query.
    Returns a list of dicts, one per CR.
    """
    base_url = base_url.rstrip("/")

    # Try JSON endpoints first
    for tmpl in ORBIT_QUERY_ENDPOINTS:
        url = base_url + tmpl.format(qid=query_id)
        if verbose:
            print(f"  Trying: {url}", file=sys.stderr)
        try:
            resp = session.get(url, timeout=30,
                               headers={"Accept": "application/json"})
            if resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "")
                if "json" in ct:
                    data = resp.json()
                    return _normalise_json(data)
                elif "csv" in ct or "text" in ct:
                    return _parse_csv(resp.text)
        except Exception as exc:
            if verbose:
                print(f"    Error: {exc}", file=sys.stderr)

    # Try CSV export endpoints
    for tmpl in ORBIT_EXPORT_ENDPOINTS:
        url = base_url + tmpl.format(qid=query_id)
        if verbose:
            print(f"  Trying CSV: {url}", file=sys.stderr)
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return _parse_csv(resp.text)
        except Exception as exc:
            if verbose:
                print(f"    Error: {exc}", file=sys.stderr)

    # Last resort: scrape the HTML query page
    url = base_url + f"/query/{query_id}"
    if verbose:
        print(f"  Trying HTML scrape: {url}", file=sys.stderr)
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return _scrape_html(resp.text)
        elif resp.status_code == 401:
            _die(
                "401 Unauthorized from Orbit.\n"
                "  Options:\n"
                "    1. Run with --cookie '<paste from browser DevTools>'\n"
                "    2. Run with --user 'DOMAIN\\\\username' --password 'pass'\n"
                "    3. Obtain a Kerberos ticket: kinit sauravk@QUALCOMM.COM\n"
                "       then install: pip3 install requests-kerberos"
            )
    except Exception as exc:
        _die(f"Failed to reach Orbit: {exc}")

    _die("Could not retrieve data from any Orbit endpoint.")


def _normalise_json(data) -> list:
    """Normalise various Orbit JSON response shapes into a flat list of dicts."""
    if isinstance(data, list):
        return data
    # Common wrappers
    for key in ("results", "items", "crs", "defects", "records", "data"):
        if isinstance(data, dict) and key in data:
            val = data[key]
            if isinstance(val, list):
                return val
    if isinstance(data, dict):
        return [data]
    return []


def _parse_csv(text: str) -> list:
    """Parse a CSV export from Orbit into a list of dicts."""
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _scrape_html(html: str) -> list:
    """
    Best-effort HTML scrape of an Orbit query results page.
    Looks for a <table> with CR data.
    """
    try:
        import re
        # Find table headers
        headers = re.findall(r'<th[^>]*>(.*?)</th>', html, re.S | re.I)
        headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
        # Find table rows
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
        result = []
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S | re.I)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            if cells and len(cells) == len(headers):
                result.append(dict(zip(headers, cells)))
        return result
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Field normalisation
# ---------------------------------------------------------------------------

# Map of common Orbit field name variants → canonical name
FIELD_MAP = {
    # CR identifier
    "cr": "cr_id", "cr id": "cr_id", "cr#": "cr_id", "id": "cr_id",
    "defect id": "cr_id", "defect": "cr_id", "number": "cr_id",
    # Title / summary
    "title": "title", "summary": "title", "subject": "title",
    "description": "title", "headline": "title",
    # Found on product / target
    "found on product": "target", "found_on_product": "target",
    "foundonproduct": "target", "product": "target",
    "target": "target", "platform": "target", "device": "target",
    # Software image status
    "software image status": "sw_status", "sw image status": "sw_status",
    "softwareimagestatus": "sw_status", "sw_image_status": "sw_status",
    "image status": "sw_status", "build status": "sw_status",
    "status": "sw_status",
    # Age / date
    "age": "age_days", "age (days)": "age_days", "days open": "age_days",
    "opened date": "opened_date", "open date": "opened_date",
    "created": "opened_date", "created date": "opened_date",
    "date opened": "opened_date", "submission date": "opened_date",
    # Severity
    "severity": "severity", "priority": "severity",
    # Assignee
    "assignee": "assignee", "assigned to": "assignee", "owner": "assignee",
    # State
    "state": "state", "cr state": "state", "defect state": "state",
    "resolution": "state",
    # Component
    "component": "component", "subsystem": "component",
    "area": "component", "module": "component",
}


def normalise_cr(raw: dict) -> dict:
    """Map raw field names to canonical names."""
    out = {}
    for k, v in raw.items():
        canonical = FIELD_MAP.get(k.lower().strip(), k.lower().strip())
        out[canonical] = str(v).strip() if v is not None else ""
    # Compute age_days from opened_date if not present
    if "age_days" not in out or not out["age_days"]:
        if "opened_date" in out and out["opened_date"]:
            out["age_days"] = str(_days_since(out["opened_date"]))
    return out


def _days_since(date_str: str) -> int:
    """Parse a date string and return days since then."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            return (datetime.datetime.now() - dt).days
        except ValueError:
            continue
    return 0


# ---------------------------------------------------------------------------
# SW Image status colour coding
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "analysis":   YELLOW,
    "analysing":  YELLOW,
    "in analysis":YELLOW,
    "fixed":      GREEN,
    "fix ready":  GREEN,
    "build":      CYAN,
    "in build":   CYAN,
    "building":   CYAN,
    "integrated": CYAN,
    "closed":     DIM,
    "duplicate":  DIM,
    "not a bug":  DIM,
    "wontfix":    DIM,
    "open":       lambda t: _c("35", t),   # magenta
    "new":        lambda t: _c("35", t),
    "assigned":   lambda t: _c("35", t),
}

def _colour_status(status: str) -> str:
    key = status.lower().strip()
    for k, fn in STATUS_COLORS.items():
        if k in key:
            return fn(status)
    return status


def _colour_age(age_str: str, max_age: int) -> str:
    try:
        days = int(age_str)
        if days > max_age:
            return RED(age_str)
        elif days > max_age // 2:
            return YELLOW(age_str)
        return age_str
    except ValueError:
        return age_str


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_table(groups: dict, max_age: int) -> None:
    """Render a human-readable table grouped by target."""
    total = sum(len(v) for v in groups.values())
    print(BOLD(f"\n{'═'*72}"))
    print(BOLD(f"  Orbit CR Report  —  {total} CRs across {len(groups)} targets"))
    print(BOLD(f"{'═'*72}\n"))

    for target, crs in sorted(groups.items()):
        print(BOLD(CYAN(f"▶  {target}")) + DIM(f"  ({len(crs)} CRs)"))
        print(DIM("─" * 72))

        # Column widths
        w_cr     = max(6,  max(len(c.get("cr_id","")) for c in crs))
        w_age    = max(5,  max(len(c.get("age_days","")) for c in crs))
        w_status = max(12, max(len(c.get("sw_status","")) for c in crs))
        w_title  = max(10, 72 - w_cr - w_age - w_status - 8)

        hdr = (f"  {'CR':<{w_cr}}  {'Age':>{w_age}}d  "
               f"{'SW Image Status':<{w_status}}  {'Title':<{w_title}}")
        print(DIM(hdr))
        print(DIM("  " + "─" * (w_cr + w_age + w_status + w_title + 8)))

        for cr in crs:
            cr_id   = cr.get("cr_id", "?")
            age     = cr.get("age_days", "?")
            status  = cr.get("sw_status", "—")
            title   = cr.get("title", "")
            title   = textwrap.shorten(title, width=w_title, placeholder="…")

            age_col    = _colour_age(age, max_age)
            status_col = _colour_status(status)

            print(f"  {cr_id:<{w_cr}}  {age_col:>{w_age}}d  "
                  f"{status_col:<{w_status}}  {title}")
        print()


def render_markdown(groups: dict, max_age: int) -> None:
    total = sum(len(v) for v in groups.values())
    print(f"# Orbit CR Report\n")
    print(f"**Total:** {total} CRs across {len(groups)} targets\n")
    for target, crs in sorted(groups.items()):
        print(f"## {target}  ({len(crs)} CRs)\n")
        print(f"| CR | Age (days) | SW Image Status | Title |")
        print(f"|---|---|---|---|")
        for cr in crs:
            cr_id  = cr.get("cr_id", "?")
            age    = cr.get("age_days", "?")
            status = cr.get("sw_status", "—")
            title  = cr.get("title", "").replace("|", "\\|")
            print(f"| {cr_id} | {age} | {status} | {title} |")
        print()


def render_json(groups: dict) -> None:
    out = {target: crs for target, crs in sorted(groups.items())}
    print(json.dumps(out, indent=2))


def render_csv_out(groups: dict) -> None:
    writer = csv.DictWriter(sys.stdout,
                            fieldnames=["target", "cr_id", "age_days",
                                        "sw_status", "title", "severity",
                                        "state", "assignee", "component"],
                            extrasaction="ignore")
    writer.writeheader()
    for target, crs in sorted(groups.items()):
        for cr in crs:
            cr["target"] = target
            writer.writerow(cr)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def group_and_sort(crs: list, sort_by: str,
                   target_filter: Optional[str],
                   status_filter: Optional[str]) -> dict:
    """Group CRs by target, apply filters, sort within each group."""
    groups: dict = {}
    for cr in crs:
        target = cr.get("target", "Unknown").strip() or "Unknown"
        if target_filter and target_filter.lower() not in target.lower():
            continue
        sw_status = cr.get("sw_status", "").strip()
        if status_filter and status_filter.lower() not in sw_status.lower():
            continue
        groups.setdefault(target, []).append(cr)

    # Sort within each group
    for target in groups:
        if sort_by == "age":
            groups[target].sort(
                key=lambda c: int(c.get("age_days", 0) or 0), reverse=True
            )
        elif sort_by == "cr":
            groups[target].sort(key=lambda c: c.get("cr_id", ""))
        elif sort_by == "status":
            groups[target].sort(key=lambda c: c.get("sw_status", ""))

    return groups


def print_summary(groups: dict, max_age: int) -> None:
    """Print a one-line summary per target."""
    print(BOLD("\nSummary by target:"))
    for target, crs in sorted(groups.items()):
        old = sum(1 for c in crs if int(c.get("age_days", 0) or 0) > max_age)
        statuses: dict = {}
        for c in crs:
            s = c.get("sw_status", "unknown").strip() or "unknown"
            statuses[s] = statuses.get(s, 0) + 1
        status_str = ", ".join(f"{s}:{n}" for s, n in sorted(statuses.items()))
        old_str = RED(f" ({old} old)") if old else ""
        print(f"  {CYAN(target):<40} {len(crs):>3} CRs{old_str}  [{status_str}]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _die(msg: str) -> None:
    print(f"\n{RED('ERROR:')} {msg}\n", file=sys.stderr)
    sys.exit(1)

def _warn(msg: str) -> None:
    print(f"{YELLOW('WARN:')} {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orbit_cr_report",
        description="Fetch an Orbit query and report CRs grouped by target with SW Image status.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Auth examples:
              # Kerberos (if you have a ticket):
              kinit sauravk@QUALCOMM.COM
              python3 orbit_cr_report.py

              # NTLM:
              python3 orbit_cr_report.py --user 'QUALCOMM\\\\sauravk' --password 'mypass'

              # Browser cookie (paste from DevTools → Application → Cookies):
              python3 orbit_cr_report.py --cookie 'ASP.NET_SessionId=abc123; .ASPXAUTH=xyz'

              # Environment variables:
              export ORBIT_USER='QUALCOMM\\\\sauravk'
              export ORBIT_PASS='mypass'
              python3 orbit_cr_report.py

            Output examples:
              python3 orbit_cr_report.py --output markdown > report.md
              python3 orbit_cr_report.py --output csv > report.csv
              python3 orbit_cr_report.py --output json > report.json
              python3 orbit_cr_report.py --target QCS9075 --status analysis
        """),
    )
    p.add_argument("--query-id", type=int, default=111043,
                   help="Orbit query ID (default: 111043)")
    p.add_argument("--url", default="https://orbit-sd",
                   help="Orbit base URL (default: https://orbit-sd)")
    p.add_argument("--user", default=os.environ.get("ORBIT_USER"),
                   help="DOMAIN\\\\username for NTLM auth")
    p.add_argument("--password", default=os.environ.get("ORBIT_PASS"),
                   help="Password for NTLM auth")
    p.add_argument("--cookie", default=os.environ.get("ORBIT_COOKIE"),
                   help="Session cookie string (paste from browser)")
    p.add_argument("--output", choices=["table", "json", "csv", "markdown"],
                   default="table", help="Output format (default: table)")
    p.add_argument("--sort", choices=["age", "cr", "status"],
                   default="age", help="Sort within each target group (default: age)")
    p.add_argument("--max-age", type=int, default=90,
                   help="Highlight CRs older than N days in red (default: 90)")
    p.add_argument("--target", default=None,
                   help="Filter to a specific target product (substring match)")
    p.add_argument("--status", default=None,
                   help="Filter to a specific SW image status (substring match)")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI colour output")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Show HTTP request details")
    return p


def main() -> None:
    global USE_COLOR
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        USE_COLOR = False

    # Build session
    session = _make_session(args.user, args.password, args.cookie)

    # Fetch
    print(f"Fetching Orbit query {args.query_id} from {args.url} ...",
          file=sys.stderr)
    raw_crs = fetch_query(args.url, args.query_id, session, verbose=args.verbose)

    if not raw_crs:
        _die("No CRs returned. Check query ID, auth, and network access.")

    print(f"Fetched {len(raw_crs)} CRs.", file=sys.stderr)

    # Normalise
    crs = [normalise_cr(cr) for cr in raw_crs]

    # Group + sort + filter
    groups = group_and_sort(crs, args.sort, args.target, args.status)

    if not groups:
        print("No CRs match the specified filters.", file=sys.stderr)
        sys.exit(0)

    # Render
    if args.output == "table":
        render_table(groups, args.max_age)
        print_summary(groups, args.max_age)
    elif args.output == "markdown":
        render_markdown(groups, args.max_age)
    elif args.output == "json":
        render_json(groups)
    elif args.output == "csv":
        render_csv_out(groups)


if __name__ == "__main__":
    main()
