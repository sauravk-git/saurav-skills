# PipeWire Enhancement Skill — 3-Month Build Roadmap

**Owner:** Saurav Kumar  
**Audience:** Director review  
**Goal:** Build an AI-powered PipeWire Enhancement Engineering assistant for
Qualcomm QLI / AudioReach / PAL stacks — starting from zero, adding capability
incrementally, demonstrating value at every milestone.

---

## The Problem We Are Solving

PipeWire enhancement work on Qualcomm QLI platforms is slow and inconsistent:

- Engineers spend hours mapping a vague issue to the right component and source files
- Every enhancement proposal is written from scratch with no shared structure
- New team members have no fast path to understanding the QLI audio stack
- Knowledge about platform differences (QLI 1.x vs 2.x, Config 1 vs Config 2,
  SSMD, Fluence) lives in people's heads, not in tools

This skill turns that tribal knowledge into a repeatable, AI-assisted workflow.

---

## Milestone Overview

| Milestone | Weeks | Theme | Deliverable |
|---|---|---|---|
| **M1** | 1–2 | Foundation | Issue intake + basic classification |
| **M2** | 3–4 | Structure | Structured proposal output |
| **M3** | 5–6 | Intelligence | Component + platform awareness |
| **M4** | 7–8 | Depth | Architecture notes + implementation plan |
| **M5** | 9–10 | Automation | Diagnostics + test plan generation |
| **M6** | 11–12 | Integration | Full proposal + QGenie skill packaging |

---

## Month 1 — From Zero to First Useful Output

### M1 · Weeks 1–2 · Issue Intake & Classification

**What we build:**
A simple script that accepts a plain-English issue description and classifies it
into one of 13 enhancement types.

**Why it matters:**
The first thing any engineer does with a new issue is ask "what kind of problem
is this?" — routing bug? audio quality? documentation gap? Getting that right
immediately saves 30 minutes of triage per issue.

**Deliverables:**
- `classify.py` — takes `--issue` text, prints matched enhancement type(s)
- Keyword-to-type mapping for all 13 types
- `--list-types` flag to show all categories

**Demo:**
```
$ python3 classify.py --issue "Audio tick at playback start on IQ9075"
→ Type 5: Audio quality improvement
→ Type 10: Debugging / root-cause investigation
```

**Success criteria:** Correctly classifies 10 real issues from the team's backlog.

---

### M2 · Weeks 3–4 · Structured Proposal Skeleton

**What we build:**
Extend the classifier to produce a structured proposal skeleton — not just a
type label, but a filled-in document with the right sections for that type.

**Why it matters:**
Engineers currently write proposals in different formats. A consistent structure
means faster reviews, easier tracking, and nothing gets forgotten.

**Deliverables:**
- 10-section proposal template (Summary, Classification, Affected Components,
  Gap Analysis, Architecture Notes, Implementation Plan, Test Plan, Doc Tasks,
  Risks, Acceptance Criteria)
- Sections auto-populated based on enhancement type
- `--output markdown` flag to save as `.md`

**Demo:**
```
$ python3 analyze_enhancement.py \
    --issue "Audio tick at playback start on IQ9075" \
    --goal  "Eliminate tick without regression"
→ Prints full 10-section proposal
```

**Success criteria:** Proposal covers all 10 sections; team lead says it's
usable as a starting point without manual editing.

---

## Month 2 — Making It Smart

### M3 · Weeks 5–6 · Component & Platform Awareness

**What we build:**
The skill learns which components are affected by which issue types, and which
platforms support which features. It auto-populates the "Affected Components"
section and flags platform-specific constraints.

**Why it matters:**
"Which files do I need to change?" is the second question every engineer asks.
Getting that wrong wastes days. Platform awareness prevents proposals that
suggest features unavailable on the target hardware.

**Deliverables:**
- Component map: issue keywords → affected source files / modules
- Platform matrix: IQ615, IQ8275, IQ9075, RB3-Gen2, QCS6490, SA8775P
- QLI 1.x vs 2.x feature delta (ADSP offload, SSMD, Fluence, Config 2,
  BT offload, modem audio — all QLI 2.x only)
- Auto-detected platform from issue text; explicit `--platform` override

**Demo:**
```
$ python3 analyze_enhancement.py \
    --issue "SSMD not working on IQ9075" \
    --goal  "Enable simultaneous speaker + headphone playback"
→ Affected: PAL (SSMD usecase), AudioReach (topology), WirePlumber (policy)
→ Platform: IQ9075 — QLI 2.x ✓, Config 2 required ✓, SSMD supported ✓
→ Warning: SSMD requires Config 2 topology — confirm it is loaded
```

**Success criteria:** Component list matches what an experienced engineer
would write for 8 out of 10 test cases.

---

### M4 · Weeks 7–8 · Architecture Notes & Implementation Plan

**What we build:**
The skill generates hypothesis-driven architecture notes (root-cause candidates
ranked by probability) and a step-by-step implementation plan with effort
estimates (S/M/L).

**Why it matters:**
This is the hardest part of any proposal to write — and the most valuable.
A ranked hypothesis list focuses investigation. An effort-estimated task list
makes sprint planning possible.

**Deliverables:**
- Root-cause hypothesis generation per issue type (drawn from known patterns)
- Implementation plan: ordered tasks, component owner, effort (S/M/L)
- Gap analysis: what information is missing before work can start
- All hypotheses labelled *(hypothesis)* — no false certainty

**Demo:**
```
Architecture Notes (hypothesis):
  1. [HIGH] PAL stream open triggers codec pop without mute ramp
  2. [MED]  SPA/ALSA underrun during first buffer cycle
  3. [LOW]  WirePlumber activates node before ADSP graph is stable

Implementation Plan:
  Step 1 | PAL       | Enable codec pop-suppression via stream attributes | S
  Step 2 | SPA       | Add pre-roll silent buffer in spa.alsa             | M
  Step 3 | WirePlumber | Add activation delay tied to PAL ready event    | M
  Step 4 | Test      | Measure glitch with/without each fix on IQ9075    | S
```

**Success criteria:** Implementation plan is accepted by team lead as a
valid starting point for sprint planning without major rework.

---

## Month 3 — Full Automation & Integration

### M5 · Weeks 9–10 · Diagnostics & Test Plan Generation

**What we build:**
The skill generates ready-to-run diagnostic commands for the reported issue,
and a test/validation plan with exact commands and pass/fail criteria.

**Why it matters:**
Diagnostic commands are currently copy-pasted from memory or old tickets.
A generated, issue-specific diagnostic runbook saves 1–2 hours per investigation.
A test plan with exact commands means validation is reproducible.

**Deliverables:**
- Diagnostic runbook: exact shell commands to run first, ordered by likelihood
- Test plan: before/after test commands, expected output, pass criteria
- Platform-specific commands (e.g. `logcat` for QLI 2.x, `journalctl` for QLI 1.x)
- `--platform` flag routes to the right command set

**Demo:**
```
Diagnostic Runbook:
  1. PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i 'underrun|xrun|error'
  2. pw-top  # watch for xruns in real time
  3. journalctl -u wireplumber --since '1 min ago' | grep -i 'activat|link'
  4. logcat -s PAL:V AGM:V | grep -i 'stream\|open\|close'  [QLI 2.x only]

Test Plan:
  TC-1: pw-play 48kHz/16-bit stereo WAV — no audible glitch, 0 xruns in pw-top
  TC-2: GStreamer pipeline — same criteria
  TC-3: Regression: all existing audio paths pass on IQ9075
```

**Success criteria:** Diagnostic runbook is used by an engineer on a real
issue and saves measurable time vs. manual lookup.

---

### M6 · Weeks 11–12 · Full Skill + QGenie Integration

**What we build:**
Package everything as a production QGenie skill — natural language trigger,
conversational intake, full proposal output, installable from GitHub in one
command.

**Why it matters:**
This is the difference between a script and a skill. Any engineer on the team
can now type a plain-English request into QGenie and get a complete, structured
enhancement proposal in under 60 seconds — without knowing any of the
underlying commands.

**Deliverables:**
- `SKILL.md` with trigger phrases, input collection rules, output format
- Conversational mode: agent asks issue + goal, produces full proposal
- `--interactive` mode in the script for direct use
- Installable: `Install the pipewire-enhancement skill from sauravk-git/saurav-skills`
- README with usage examples, all flags, worked examples
- 3 reference documents: component map, platform matrix, worked examples

**Demo (QGenie prompt):**
```
Audio glitch at playback start on IQ9075 QLI 2.x — help me plan the fix
```
→ Agent asks: "What is your goal — eliminate the glitch entirely, or reduce it?"
→ Produces full 10-section proposal in < 60 seconds

**Success criteria:**
- Any team member can install and use the skill without help
- Proposal quality rated ≥ 4/5 by 3 engineers on real issues
- Director demo: live end-to-end in under 2 minutes

---

## Cumulative Value at Each Milestone

| After | What the team can do | Time saved per issue |
|---|---|---|
| M1 | Instantly classify any issue into the right type | ~30 min |
| M2 | Get a structured proposal skeleton in seconds | ~2 hrs |
| M3 | Know exactly which components and files to touch | ~1 hr |
| M4 | Start sprint planning from a generated task list | ~2 hrs |
| M5 | Run a generated diagnostic runbook immediately | ~1–2 hrs |
| M6 | Do all of the above from a single QGenie prompt | ~6–7 hrs total |

---

## What Is NOT in Scope (for this 3 months)

- Automatically writing code changes (out of scope — proposals only)
- Integration with Orbit / JIRA ticket creation (future milestone)
- Real-time log analysis (future milestone)
- Support for non-Qualcomm PipeWire platforms (future milestone)

---

## Risks

| Risk | Mitigation |
|---|---|
| Keyword matching too shallow for complex issues | Add worked examples as test cases; iterate on keyword map |
| Platform matrix goes stale as new platforms ship | Keep matrix in a separate `.md` file, easy to update |
| Team doesn't adopt the skill | Demo on a real issue from the backlog at M2 review |
| Director wants faster results | M2 already produces a full proposal — can demo at week 4 |

