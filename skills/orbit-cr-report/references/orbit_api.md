# Orbit API Reference

## Base URLs

| Alias | Actual host | Notes |
|---|---|---|
| `https://orbit` | Redirects (307) to `https://orbit-sd` | Use `orbit-sd` directly |
| `https://orbit-sd` | Primary API host | All requests go here |

## Authentication

Orbit uses **Windows Negotiate / NTLM** (`WWW-Authenticate: Negotiate, NTLM`).

### Option 1 — Kerberos (recommended on Linux)
```bash
kinit sauravk@QUALCOMM.COM          # get a ticket
pip3 install requests-kerberos
python3 orbit_cr_report.py          # auto-picks up the ticket
```

### Option 2 — NTLM
```bash
pip3 install requests-ntlm
python3 orbit_cr_report.py --user 'QUALCOMM\sauravk' --password 'mypass'
# or via env:
export ORBIT_USER='QUALCOMM\sauravk'
export ORBIT_PASS='mypass'
```

### Option 3 — Browser session cookie (quickest for one-off use)
1. Open `https://orbit/query/111043` in Chrome/Firefox while on VPN
2. DevTools → Application → Cookies → copy `ASP.NET_SessionId` and `.ASPXAUTH`
3. Pass as: `--cookie 'ASP.NET_SessionId=abc; .ASPXAUTH=xyz'`
   or: `export ORBIT_COOKIE='ASP.NET_SessionId=abc; .ASPXAUTH=xyz'`

## Known API Endpoints

Orbit is a Qualcomm-internal CR/defect tracker. The script probes these in order:

| Endpoint | Format | Notes |
|---|---|---|
| `/api/query/{id}/results` | JSON | Primary REST API |
| `/api/v1/query/{id}/results` | JSON | Versioned API |
| `/api/v2/query/{id}/results` | JSON | Newer API version |
| `/query/{id}/export?format=json` | JSON | Export endpoint |
| `/query/{id}/export?format=csv&allFields=true` | CSV | Full CSV export |
| `/query/{id}/export?format=csv` | CSV | Standard CSV export |
| `/query/{id}` | HTML | Fallback HTML scrape |

## CR Field Schema

These are the canonical field names the script uses internally after normalisation.
Orbit may return them under different names (all variants are mapped automatically).

| Canonical field | Common Orbit names | Description |
|---|---|---|
| `cr_id` | CR, CR#, CR Id, Defect Id, Number | CR identifier |
| `title` | Title, Summary, Subject, Description | One-line description |
| `target` | Found on Product, Found_on_Product, Product, Platform | Target product/device |
| `sw_status` | Software Image Status, SW Image Status, Image Status, Build Status | Current SW image state |
| `age_days` | Age, Age (days), Days Open | Days since CR was opened |
| `opened_date` | Opened Date, Created, Submission Date | Date CR was filed |
| `severity` | Severity, Priority | S1/S2/S3/S4 or P1/P2/P3 |
| `state` | State, CR State, Resolution | Open/Closed/Duplicate etc. |
| `assignee` | Assignee, Assigned To, Owner | Current owner |
| `component` | Component, Subsystem, Area, Module | Affected component |

## Software Image Status Values

Common values seen in Orbit for the `Software Image Status` field:

| Status | Meaning | Colour in report |
|---|---|---|
| `Analysis` / `In Analysis` | Under investigation | Yellow |
| `Fixed` / `Fix Ready` | Fix committed | Green |
| `Build` / `In Build` / `Building` | Fix in a build | Cyan |
| `Integrated` | Merged into mainline | Cyan |
| `Open` / `New` / `Assigned` | Not yet triaged | Magenta |
| `Closed` / `Duplicate` / `Not a Bug` | Resolved/closed | Dim |

## Query 111043

This is a saved Orbit query. The script fetches all CRs it returns and:
1. Groups by `Found on Product` (target device/platform)
2. Sorts each group by age (oldest first by default)
3. Shows `Software Image Status` for each CR

To use a different query: `--query-id <N>`

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | No valid auth | Use `--cookie`, `--user/--password`, or `kinit` |
| `No CRs returned` | Wrong endpoint or empty query | Try `--verbose` to see which URLs were tried |
| `target` field shows `Unknown` | Field name not in mapping | Check raw field names with `--output json` and add to `FIELD_MAP` in script |
| `sw_status` all empty | Field name variant not mapped | Same as above |
| `age_days` all 0 | Date format not recognised | Add format to `_days_since()` in script |
