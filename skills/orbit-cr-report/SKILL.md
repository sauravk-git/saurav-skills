---
name: orbit-cr-report
description: >
  Fetch a saved Orbit query (e.g. https://orbit/query/111043), retrieve all CRs,
  group them by "Found on Product" (target device/platform), sort each group by
  age (oldest first), and display the current Software Image Status (Analysis,
  Fixed, Build, Integrated, etc.) for each CR. Supports table, markdown, JSON,
  and CSV output. Handles Orbit's Windows Negotiate/NTLM authentication via
  Kerberos ticket, NTLM credentials, or a browser session cookie.
  Use when asked to: run an Orbit query, show CRs by target, report SW image
  status, list open defects by product, or analyse CR age distribution.
---

# orbit-cr-report Skill

Fetches all CRs from an Orbit saved query and renders a report grouped by
**Found on Product**, sorted by age, with **Software Image Status** highlighted.

---

## Quick Start

```bash
# Kerberos (recommended — get a ticket first)
kinit sauravk@QUALCOMM.COM
pip3 install requests requests-kerberos
python3 scripts/orbit_cr_report.py

# NTLM credentials
python3 scripts/orbit_cr_report.py \
    --user 'QUALCOMM\sauravk' --password 'mypass'

# Browser session cookie (paste from DevTools)
python3 scripts/orbit_cr_report.py \
    --cookie 'ASP.NET_SessionId=abc123; .ASPXAUTH=xyz'
```

---

## Workflow

### Step 1 — Authenticate

Orbit uses Windows Negotiate/NTLM. Pick one method:

| Method | Command |
|---|---|
| Kerberos | `kinit sauravk@QUALCOMM.COM` then run script |
| NTLM | `--user 'DOMAIN\user' --password 'pass'` |
| Cookie | `--cookie '<paste from browser>'` (see `references/orbit_api.md`) |
| Env vars | `ORBIT_USER`, `ORBIT_PASS`, or `ORBIT_COOKIE` |

### Step 2 — Run the report

```bash
# Default: query 111043, table output, sorted by age
python3 scripts/orbit_cr_report.py

# Different query ID
python3 scripts/orbit_cr_report.py --query-id 222099

# Filter to one target product
python3 scripts/orbit_cr_report.py --target QCS9075

# Filter to CRs in Analysis status
python3 scripts/orbit_cr_report.py --status analysis

# Highlight CRs older than 60 days (default: 90)
python3 scripts/orbit_cr_report.py --max-age 60

# Markdown output (for sharing / pasting into docs)
python3 scripts/orbit_cr_report.py --output markdown > cr_report.md

# CSV for spreadsheet
python3 scripts/orbit_cr_report.py --output csv > cr_report.csv

# JSON for further processing
python3 scripts/orbit_cr_report.py --output json > cr_report.json
```

### Step 3 — Read the output

**Table output** (default):

```
════════════════════════════════════════════════════════════════════════
  Orbit CR Report  —  47 CRs across 5 targets
════════════════════════════════════════════════════════════════════════

▶  QCS9075  (12 CRs)
────────────────────────────────────────────────────────────────────────
  CR          Age  SW Image Status   Title
  ──────────────────────────────────────────────────────────────────────
  CR-123456   187d  Analysis         Audio dropout during BT call
  CR-123789   142d  Fixed            Mic not detected after suspend
  CR-124001    45d  Build            Volume control unresponsive
  ...

▶  QCS6490  (8 CRs)
  ...

Summary by target:
  QCS9075                                   12 CRs (3 old)  [Analysis:4, Build:3, Fixed:5]
  QCS6490                                    8 CRs           [Analysis:2, Fixed:6]
```

**Colour coding:**
- 🔴 Red age = older than `--max-age` days
- 🟡 Yellow = Analysis / In Analysis status
- 🟢 Green = Fixed / Fix Ready
- 🔵 Cyan = Build / In Build / Integrated
- 🟣 Magenta = Open / New / Assigned
- Grey = Closed / Duplicate / Not a Bug

---

## Options Reference

```
--query-id  INT     Orbit query ID (default: 111043)
--url       URL     Orbit base URL (default: https://orbit-sd)
--user      STR     DOMAIN\username for NTLM
--password  STR     Password for NTLM
--cookie    STR     Session cookie string
--output    FORMAT  table (default) | json | csv | markdown
--sort      FIELD   age (default) | cr | status
--max-age   DAYS    Highlight CRs older than N days (default: 90)
--target    STR     Filter to a specific target product (substring)
--status    STR     Filter to a specific SW image status (substring)
--no-color          Disable ANSI colour
--verbose           Show HTTP request details
```

---

## Dependencies

```bash
pip3 install requests                  # always required
pip3 install requests-kerberos         # for Kerberos auth
pip3 install requests-ntlm             # for NTLM auth
pip3 install requests-negotiate-sspi   # alternative Negotiate
```

---

## References

- `references/orbit_api.md` — Auth methods, API endpoints, field schema,
  SW Image Status values, query 111043 details, troubleshooting guide.
  Read this when: auth fails, fields are missing, adding new field mappings,
  or debugging endpoint discovery.
