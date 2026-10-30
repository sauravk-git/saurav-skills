# PipeWire Enhancement Skill — Development Roadmap

## Scope & Audio Path Summary

**Scope:** QLI 2.x only — IQ9075, RB3-Gen2, QCS6490, SA8775P.
PipeWire 1.x + WirePlumber 0.5.x on all platforms.

| Config | Audio path | PAL/AudioReach needed? |
|---|---|---|
| Config 1 | PipeWire → spa.alsa → ALSA kernel driver | **No** |
| Config 2 | PipeWire → pipewire-pal-plugin → PAL → AudioReach → ADSP | **Yes** |

## Time Budget

4 hours/week × 4 weeks = **16 hours/month** × 8 months = **128 hours total**

| Month | Phase | Estimated hours |
|---|---|---|
| 1 | Knowledge Base | 16h |
| 2 | Script Foundation + Basic Diagnosis (part 1) | 14h |
| 3 | Basic Diagnosis (part 2) + Config 1 Bringup | 16h |
| 4 | PAL / AudioReach Knowledge Base + Config 2 Bringup | 16h |
| 5 | Complex Issue Investigation (part 1) | 14h |
| 6 | Complex Issue Investigation (part 2) + New Feature Foundation | 16h |
| 7 | New Features + Advanced Workflow Types | 16h |
| 8 | Hardening, CLI Polish, and Full Validation | 13h |
| | **Total** | **121h** (7h buffer) |

---

## Month 1 — Knowledge Base (16h)

**Goal:** Populate all reference docs before writing any code. Everything
built in later months depends on these being accurate and complete.

| Task | Hours | Deliverable |
|---|---|---|
| Platform capabilities matrix (4 platforms, all feature flags) | 2h | `references/platform_matrix.md` §1 |
| Config 1 vs Config 2 audio path distinction | 1h | `references/component_map.md` §2 |
| Component → source-file mapping (PipeWire, SPA, WirePlumber, PAL) | 4h | `references/component_map.md` §1 |
| AudioReach graph construction + AGM session flow (Config 2 only) | 2h | `references/component_map.md` §3 |
| Known issue patterns + diagnostic steps (Config 1 and Config 2) | 3h | `references/platform_matrix.md` §2–3 |
| Worked examples — 3 cases: glitch, missing device, WirePlumber race | 4h | `references/examples.md` |

**Exit criteria:**
- Config 1 (spa.alsa) and Config 2 (PAL path) clearly distinguished in all docs.
- A new contributor can map any described issue to 2–3 source files using only
  the reference docs.
- SA8775P marked as Config 2 only in platform matrix.

---

## Month 2 — Script Foundation + Basic Diagnosis Part 1 (14h)

**Goal:** Stand up `analyze_enhancement.py` with the core loop, CLI, and the
first half of the 13 type detectors. Deliberately scoped to fit 14h — the
remaining detectors and testing move to Month 3.

| Task | Hours | Deliverable |
|---|---|---|
| `analyze_enhancement.py` — core loop, argument parsing, 10-section output engine | 5h | `scripts/analyze_enhancement.py` |
| Enhancement-type detectors — types 1–7 (new feature through config enhancement) | 4h | `scripts/analyze_enhancement.py` |
| Gap-analysis logic — per-type missing-info checks, §4 output | 3h | `scripts/analyze_enhancement.py` |
| Platform lookup — read `platform_matrix.md`, gate features by platform | 2h | `scripts/analyze_enhancement.py` |

**Exit criteria:**
- Script runs end-to-end for any type 1–7 request without crashing.
- §4 gap analysis flags missing version and log info for each type.
- No stdlib import beyond Python 3.8.

---

## Month 3 — Basic Diagnosis Part 2 + Config 1 Bringup (16h)

**Goal:** Complete the remaining type detectors, validate the three baseline
test cases, then add full Config 1 bringup coverage.

### Basic Diagnosis Part 2 (8h)

| Task | Hours | Deliverable |
|---|---|---|
| Enhancement-type detectors — types 8–13 (PAL integration through packaging) | 4h | `scripts/analyze_enhancement.py` |
| Test + fix: audio glitch proposal (Config 1, IQ9075) | 2h | `references/examples.md` §1 |
| Test + fix: device not enumerated (Config 1, QCS6490) | 1h | regression test |
| Test + fix: WirePlumber enumeration race (Config 1, RB3-Gen2) | 1h | regression test |

### Config 1 Bringup (8h)

| Task | Hours | Deliverable |
|---|---|---|
| Config 1 bringup steps — spa.alsa bring-up sequence, systemd ordering | 2h | `references/platform_matrix.md` §Config-1 |
| Config 1 diagnostic commands | 1h | `references/platform_matrix.md` §3 |
| Config 1 worked example | 2h | `references/examples.md` §3 |
| Detect "Config 1" / "bringup" / "topology" in type 7; generate §6 bringup plan | 2h | `scripts/analyze_enhancement.py` |
| Validate on IQ9075 and RB3-Gen2 | 1h | integration test |

**Exit criteria:**
- Complete 10-section proposal for all three baseline test cases.
- Config 1 bringup proposals list zero PAL or AudioReach components in §3.
- Validated on IQ9075 and RB3-Gen2.

---

## Month 4 — PAL / AudioReach Knowledge Base + Config 2 Bringup (16h)

**Goal:** Build PAL/AudioReach reference knowledge (first half of month) then
immediately apply it to Config 2 bringup (second half). The two halves are
sequenced within the month — docs first, script changes second.

### PAL / AudioReach Knowledge Base (Week 1–2, 12h)

| Task | Hours | Deliverable |
|---|---|---|
| PAL stream lifecycle — open / start / stop / close with source refs | 3h | `references/component_map.md` §PAL |
| AudioReach graph construction + AGM session flow (detailed) | 3h | `references/component_map.md` §3 |
| remoteproc / ADSP firmware startup ordering | 2h | `references/platform_matrix.md` §ADSP |
| Fluence + SSMD PAL usecase definitions | 2h | `references/component_map.md` §Qualcomm |
| Modem audio + remoteproc ordering | 1h | `references/platform_matrix.md` §Modem |
| PAL-specific diagnostic commands | 1h | `references/platform_matrix.md` §3 |

### Config 2 Bringup (Week 3–4, 4h — uses docs just written)

| Task | Hours | Deliverable |
|---|---|---|
| Config 2 topology + .bin loading docs | 1h | `references/platform_matrix.md` §Config-2 |
| Config 2 / PAL path trigger detection; full PAL stack in §3 | 1h | `scripts/analyze_enhancement.py` |
| SSMD + Fluence usecase detection; compressed-offload bringup steps | 1h | `scripts/analyze_enhancement.py` |
| Config 2 worked example (SSMD) + validate on SA8775P and QCS6490 | 1h | `references/examples.md` §2 |

**Exit criteria:**
- PAL stream lifecycle documented end-to-end with source file references.
- Config 2 proposals include full PAL path in §3 and ADSP startup in §6.
- SA8775P proposals never suggest Config 1.
- SSMD and Fluence gated by platform matrix lookup.

---

## Month 5 — Complex Issue Investigation Part 1 (14h)

**Goal:** Build the root cause hypothesis engine and diagnostic runbooks.
The heavier multi-file code change logic moves to Month 6 to keep this month
within budget.

| Task | Hours | Deliverable |
|---|---|---|
| Root cause hypothesis engine — ranked hypotheses with source file pointers and evidence checklist, per issue type | 5h | §5 Architecture & Design Notes |
| Diagnostic runbooks — exact command sequences per symptom pattern, Config 1 and Config 2 paths | 4h | `references/platform_matrix.md` §runbooks |
| Compound request handling — types 6 + 7 + 8 together without contradiction | 3h | `scripts/analyze_enhancement.py` |
| Compound worked example (routing policy + Config 2 topology + PAL glitch) | 2h | `references/examples.md` §compound |

**Exit criteria:**
- §5 of every complex issue proposal has at least two ranked hypotheses,
  each with source file pointer and evidence needed to confirm.
- Diagnostic runbooks cover all known issue patterns in `platform_matrix.md`
  for both Config 1 and Config 2.
- Compound requests produce a coherent, non-contradictory proposal.

---

## Month 6 — Complex Issues Part 2 + New Feature Foundation (16h)

**Goal:** Complete multi-file code change suggestions (overflow from Month 5),
then start new feature support with architecture input and design proposals.

### Complex Issues Part 2 (6h)

| Task | Hours | Deliverable |
|---|---|---|
| Multi-file code change suggestions — diff-level guidance with exact file paths and function names across spa.alsa, WirePlumber Lua, PAL, pipewire-pal-plugin | 5h | §6 Implementation Plan |
| Validate §6 file paths + function names against component_map.md | 1h | review pass |

### New Feature Foundation (10h)

| Task | Hours | Deliverable |
|---|---|---|
| Architecture input generation — component interaction, data flow, sequencing in §5 | 3h | §5 Architecture & Design Notes |
| Design proposals — two alternatives with explicit trade-off analysis in §5 | 4h | §5 Architecture & Design Notes |
| New-feature worked example (new SPA plugin or WirePlumber policy hook) | 2h | `references/examples.md` §4 |
| Full implementation guidance — exact file paths, APIs, error handling, test hooks in §6 | 1h | §6 Implementation Plan (foundation) |

**Exit criteria:**
- §6 for complex issues includes specific file paths and function names —
  not just component names.
- §5 for new features includes at least two design alternatives with explicit
  trade-offs stated.

---

## Month 7 — New Features Complete + Advanced Workflow Types (16h)

**Goal:** Complete code scaffolding and full implementation guidance for new
features, then add the advanced workflow type templates.

### New Feature Completion (10h)

| Task | Hours | Deliverable |
|---|---|---|
| Implementation-ready code scaffolding — stub files, function signatures, header changes, Makefile/meson edits across all affected repos | 6h | §6 Implementation Plan |
| Full implementation guidance — step-by-step with APIs to call, error handling, test hooks (complete) | 4h | §6 Implementation Plan |

### Advanced Workflow Types (6h)

| Task | Hours | Deliverable |
|---|---|---|
| API/ABI change workflow — symbol versioning, ABI checker, downstream impact | 2h | type 9 template |
| Yocto recipe + Debian/RPM packaging proposals | 2h | types 12–13 template |
| CI/test enhancement workflow — test matrix, GTest stubs, CI yaml | 2h | type 12 template |

**Exit criteria:**
- New feature proposals include code scaffolding in §6 with file paths,
  function signatures, and build system changes.
- All 13 enhancement types produce a complete, non-generic proposal.

---

## Month 8 — Hardening, CLI Polish, and Full Validation (13h)

**Goal:** End-to-end validation across all 13 types × both configs, CLI
completion, reference doc gap-fill, and final skill sign-off. 3h buffer
built in for any rework found during validation.

| Task | Hours | Deliverable |
|---|---|---|
| `--from-file` batch mode | 1h | `scripts/analyze_enhancement.py` |
| `--list-platforms` and `--list-types` flags | 1h | `scripts/analyze_enhancement.py` |
| `--no-color` flag | 0.5h | `scripts/analyze_enhancement.py` |
| End-to-end regression — one request per type × both configs (26 runs) | 5h | full regression pass |
| Platform matrix constraint validation — check every proposal against matrix | 2h | validation pass |
| Reference doc gap-fill from regression findings | 3h | all `references/` files |
| `quick_validate.py` clean pass | 0.5h | CI gate |

**Exit criteria:**
- All 13 enhancement types produce a complete, non-generic proposal for both
  Config 1 and Config 2 inputs.
- `--from-file`, `--list-platforms`, `--list-types`, and `--no-color` all work.
- No platform constraint violations in any generated proposal.
- `quick_validate.py` passes with no warnings.
- **Skill is ready for delivery.**
