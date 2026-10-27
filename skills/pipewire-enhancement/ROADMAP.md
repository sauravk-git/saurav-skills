# PipeWire Enhancement Skill — 3-Month Detailed Roadmap

**Owner:** Saurav Kumar
**Audience:** Director review — Call 1
**Horizon:** 12 weeks (3 months)
**Goal:** Build an AI-powered PipeWire Enhancement Engineering assistant for
Qualcomm QLI / AudioReach / PAL stacks — starting from zero, adding capability
every two weeks, with a live demo at each monthly checkpoint.

---

## The Problem We Are Solving

PipeWire enhancement work on Qualcomm QLI platforms is slow and inconsistent:

| Pain point | Current cost |
|---|---|
| Mapping a vague issue to the right component and source files | 1–2 hrs per issue |
| Writing an enhancement proposal from scratch, every time | 2–3 hrs per proposal |
| New engineers learning the QLI 1.x vs 2.x stack differences | Days to weeks |
| Knowing which diagnostic commands to run for a given symptom | 30–60 min per investigation |
| Inconsistent proposal formats making reviews slow | 1+ hr review overhead |

**This skill turns that tribal knowledge into a repeatable, AI-assisted workflow.**
Any engineer — new or experienced — types a plain-English description of their
issue and gets a complete, structured, platform-aware enhancement proposal in
under 60 seconds.

---

## Milestone Overview

| # | Weeks | Theme | One-line outcome |
|---|---|---|---|
| M1 | 1–2 | Issue intake | Classify any issue into the right type instantly |
| M2 | 3–4 | Proposal skeleton | Generate a full 10-section proposal document |
| M3 | 5–6 | Component awareness | Know exactly which files and modules to touch |
| M4 | 7–8 | Platform intelligence | Platform-specific constraints and QLI delta |
| M5 | 9–10 | Architecture depth | Ranked hypotheses + effort-estimated task list |
| M6 | 11–12 | Full automation | Diagnostics, test plan, QGenie integration |

---

---

# MONTH 1 — Foundation: From Zero to First Useful Output

**Theme:** Build the core intake and output pipeline.
By end of Month 1, the skill can accept any PipeWire issue in plain English
and produce a structured, useful document — no manual work required.

---

## M1 · Weeks 1–2 · Issue Intake & Classification Engine

### What we build

A standalone classifier script that reads a plain-English issue description
and maps it to one or more of 13 enhancement types. This is the foundation
everything else builds on.

**The 13 enhancement types — what they mean and what triggers them:**

| # | Type | Plain meaning | Example issue |
|---|---|---|---|
| 1 | **New PipeWire feature** | Something that doesn't exist yet — build from scratch | *"Add compressed offload support in QLI 2.x"* |
| 2 | **Existing feature enhancement** | Something works but needs to work better | *"Improve BT audio quality on IQ9075"* |
| 3 | **Performance improvement** | Latency, CPU usage, power consumption, offload efficiency | *"Reduce audio latency on QCS6490"* |
| 4 | **Startup / enumeration improvement** | Device not showing up, missing sound card, boot ordering race | *"Audio device not detected after reboot"* |
| 5 | **Audio quality improvement** | Glitch, tick, pop, noise, crackle, distortion during playback or capture | *"Tick sound at start of every playback on IQ9075"* |
| 6 | **Routing or policy enhancement** | Wrong sink/source selected, SSMD, device switching, WirePlumber policy | *"Audio goes to wrong output after Bluetooth connects"* |
| 7 | **Configuration enhancement** | Config 1 vs Config 2, topology .bin files, Lua config, WirePlumber settings | *"Config 2 topology not loading on SA8775P"* |
| 8 | **PAL / AudioReach integration** | Anything touching PAL, AudioReach, ADSP, AGM, SPF — the Qualcomm-specific layer | *"PAL stream open fails after modem restart"* |
| 9 | **API or ABI enhancement** | Changes to interfaces between components — protocol, API contract, ABI compatibility | *"PipeWire API change breaks pipewire-pal-plugin"* |
| 10 | **Debugging / root-cause investigation** | Don't know what's wrong yet — need to investigate first | *"Random audio dropout, no obvious cause"* |
| 11 | **Documentation enhancement** | Something needs to be written, updated, or explained | *"No documentation for SSMD setup on IQ9075"* |
| 12 | **Test or validation enhancement** | Adding tests, automating validation, CI coverage | *"No automated test for compressed offload path"* |
| 13 | **Packaging or deployment enhancement** | Yocto recipes, Debian packages, RPM specs, deployment scripts | *"PipeWire Yocto recipe missing PACKAGECONFIG for PAL"* |

> Most real issues hit **2 types simultaneously** — e.g. *"tick at playback start"* triggers
> both Type 5 (audio quality) and Type 10 (debugging), because you need to investigate
> before you can fix. The classifier returns a primary type and secondary types, and the
> proposal covers all of them.

### Why it matters to the Director

Every issue that comes in today gets triaged manually — someone reads it,
thinks about it, and decides what kind of problem it is. That takes 20–30
minutes and is inconsistent between engineers. This automates that step
completely and gets it right every time.

### Detailed deliverables

**Script: `classify.py`**
- Accepts `--issue "..."` text on the command line
- Keyword-to-type mapping covering all 13 enhancement types:
  - Audio quality (glitch, tick, pop, noise, crackle)
  - Performance (latency, CPU, power, offload, compress)
  - Startup / enumeration (boot, missing device, not found)
  - Routing / policy (sink, source, default, switch, SSMD)
  - PAL / AudioReach integration (pal, audioreach, adsp, agm, spf)
  - Configuration (Config 1, Config 2, topology, .bin, Lua)
  - WirePlumber (wireplumber, lua, policy)
  - API / ABI (api, abi, interface, protocol)
  - Documentation (doc, guide, readme, wiki)
  - Test / validation (test, validate, CI, automate)
  - Packaging / deployment (yocto, recipe, debian, rpm)
  - New feature (new feature, add support, implement, enable)
  - Existing feature enhancement (improve, enhance, optimise)
- Returns ranked list of matched types (primary + secondary)
- `--list-types` flag: print all 13 types with descriptions
- `--verbose` flag: show which keywords triggered each match

**Knowledge base: `references/enhancement_types.md`**
- Full definition of all 13 types with examples
- Keyword lists per type (used by the classifier)
- Decision guide: when two types overlap, which takes priority

**Test suite: `tests/test_classify.py`**
- 15 real issue descriptions from the team's backlog
- Expected type(s) for each
- Pass/fail report

### Demo for Director

```
$ python3 classify.py --issue "Audio tick at playback start on IQ9075 QLI 2.x"
  Primary  : Type 5 — Audio quality improvement
  Secondary: Type 10 — Debugging / root-cause investigation

$ python3 classify.py --issue "SSMD not working after Config 2 topology load"
  Primary  : Type 6 — Routing or policy enhancement
  Secondary: Type 8 — PAL / AudioReach integration
  Secondary: Type 7 — Configuration enhancement
```

### Success criteria

- Correctly classifies 13 out of 15 test issues (87% accuracy)
- Runs in under 1 second on any issue
- Any team member can run it without setup

---

## M2 · Weeks 3–4 · Structured 10-Section Proposal Generator

### What we build

Extend the classifier into a full proposal generator. Given an issue and a
goal, it produces a complete, consistently structured 10-section document
that an engineer can use as-is or refine.

### Why it matters to the Director

Today every proposal is written from scratch in a different format. Reviews
are slow because reviewers have to hunt for information. This produces a
consistent document every time — same sections, same order, nothing forgotten.
An engineer who used to spend 2–3 hours writing a proposal now spends 10
minutes reviewing and refining one.

### Detailed deliverables

**Script: `analyze_enhancement.py`** (extends `classify.py`)
- Accepts `--issue` and `--goal` as arguments
- Conversational mode: prompts for issue + goal if no args given
- `--from-file FILE`: read issue (line 1) and goal (line 2) from a text file
- `--no-color`: plain text output for saving to file
- `--output markdown`: save proposal as `.md` file

**The 10-section proposal template:**

| # | Section | What it contains |
|---|---|---|
| 1 | Enhancement Summary | 2–3 sentence plain-English summary of issue + goal |
| 2 | Classification | Matched enhancement types with confidence |
| 3 | Affected Components | Table: component, sub-component, change type |
| 4 | Gap Analysis | What information is missing before work can start |
| 5 | Architecture & Design Notes | How the system works in this area (factual) |
| 6 | Implementation Plan | Ordered task table with area and effort (S/M/L) |
| 7 | Test & Validation Plan | Test cases with pass/fail criteria |
| 8 | Documentation Tasks | What docs need to be created or updated |
| 9 | Open Questions & Risks | Unknowns and risks with mitigations |
| 10 | Acceptance Criteria | Measurable conditions for "done" |

**Section auto-population rules (built into the script):**
- Section 1: always generated from issue + goal text
- Section 2: from classifier output (M1)
- Section 3: placeholder table — "to be filled in M3"
- Section 4: checks for missing platform, version, log info
- Section 5: generic architecture overview for the matched type
- Section 6: generic task list for the matched type
- Section 7: generic test cases for the matched type
- Section 8: doc tasks based on type (new feature → new doc; bug → update troubleshooting)
- Section 9: standard risks for the matched type
- Section 10: measurable criteria based on type

**Output format:**
- Colour-coded terminal output (section headers in cyan, warnings in yellow)
- `--no-color > proposal.md` for file output
- Markdown-compatible formatting throughout

### Demo for Director

```
$ python3 analyze_enhancement.py \
    --issue "Audio tick at playback start on IQ9075 QLI 2.x" \
    --goal  "Eliminate the tick without regressing other audio paths"

══════════════════════════════════════════════════════════════════════
  PipeWire Enhancement Proposal
  Generated: 2026-10-27 14:32
══════════════════════════════════════════════════════════════════════

1. Enhancement Summary
   The request concerns audio tick at playback start on IQ9075 QLI 2.x.
   The desired outcome is to eliminate the tick without regression...

2. Classification
   ✓  5. Audio quality improvement
   ✓  10. Debugging / root-cause investigation

3. Affected Components
   [placeholder — component awareness added in M3]

4. Gap Analysis
   ⚠  PipeWire version not specified
   ⚠  No diagnostic logs provided
   ⚠  Whether issue is in both channels not stated

...all 10 sections...
```

### Success criteria

- Proposal covers all 10 sections for any input
- Team lead reviews output on 3 real issues and says it is a usable starting point
- End-to-end time from typing issue to reading proposal: under 10 seconds

---

### Month 1 Checkpoint — What the Director sees

**Live demo (5 minutes):**
1. Type a real issue from the team's backlog into the terminal
2. Show classification output (M1)
3. Show full 10-section proposal (M2)
4. Show `--no-color > proposal.md` saving to file

**Value delivered:** Any engineer can now go from "I have an issue" to "I have
a structured proposal document" in under 60 seconds. No manual writing.

---

---

# MONTH 2 — Intelligence: Making the Proposals Actually Useful

**Theme:** Replace generic placeholders with real, specific knowledge about
the QLI audio stack — components, source files, platforms, and known patterns.
By end of Month 2, the proposals are specific enough to hand directly to an
engineer as a starting point for implementation.

---

## M3 · Weeks 5–6 · Component & Source File Awareness

### What we build

The skill learns which components are affected by which issue types, and maps
each component to its actual source files and modules in the codebase. Section 3
(Affected Components) goes from a placeholder to a precise, actionable table.

### Why it matters to the Director

"Which files do I need to change?" is the question that wastes the most time
for engineers — especially new ones. Getting it wrong means days of work in
the wrong place. This answers it instantly and correctly.

### Detailed deliverables

**Component map (built into the script + `references/component_map.md`):**

For each issue type, the skill knows:

| Issue keyword | Affected components | Key source paths |
|---|---|---|
| glitch / tick / pop | SPA (spa.alsa), PipeWire Core (node state), pipewire-pal-plugin (stream lifecycle), PAL (usecase ramp), AudioReach/ADSP (codec pop) | `spa/plugins/alsa/alsa-pcm.c`, `src/modules/module-pal-sink.c`, `Pal.cpp` |
| startup / enumeration | WirePlumber (device discovery), Yocto (systemd ordering), PAL (remoteproc startup) | `modules/module-device-activation.c`, `wireplumber.conf` |
| latency / performance | PipeWire Core (quantum/scheduling), SPA (buffer tuning), PAL (DSP offload) | `src/pipewire/impl-node.c`, `src/modules/module-rt.c` |
| SSMD / multi-device | PAL (multi-device usecase), AudioReach (SSMD topology), WirePlumber (multi-sink policy), PipeWire Core (port routing) | `ResourceManager.cpp`, `AudioReachGraph.cpp` |
| routing / policy | WirePlumber (default sink/source), PipeWire Core (link management) | `modules/module-default-nodes.c`, `module-si-standard-link.c` |
| Config 1 / Config 2 | PAL (topology selection), AudioReach (.bin loading), Yocto (firmware packaging) | `Pal.cpp`, `/lib/firmware/qcom/` |
| Fluence / voice | AudioReach/ADSP (Fluence graph), PAL (voice usecase), WirePlumber (capture routing) | `AudioReachGraph.cpp`, `resourcemanager.xml` |
| compressed offload | SPA (compress path), PAL (StreamCompress), PipeWire Core (compressed scheduling) | `spa/plugins/alsa/alsa-compress-offload.c`, `StreamCompress.cpp` |

**Component layer map (9 layers, always shown in proposals):**

```
Client & Tools → PipeWire Core → SPA → WirePlumber → PipeWire-Pulse
     → Compressed Offload → Qualcomm PAL → Topology → Yocto/Packaging
```

**Script changes:**
- Section 3 now auto-populated with real component + source file table
- Each component row shows: component name, sub-component, source path, change type
- `--show-components` flag: print full component map for a given issue type

**`references/component_map.md` expanded:**
- Full source-file mapping for all 9 component layers
- AudioReach graph construction chain (PipeWire → PAL → AGM → ADSP → codec)
- SPA plugin registry with `spa-inspect` commands
- WirePlumber Lua config file locations

### Demo for Director

```
3. Affected Components
   Component              Sub-component                    Source path                    Change
   ─────────────────────────────────────────────────────────────────────────────────────────────
   SPA                    spa.alsa pre-roll buffer         spa/plugins/alsa/alsa-pcm.c    Modify
   PipeWire Core          Node state (preparing→running)   src/pipewire/impl-node.c       Investigate
   pipewire-pal-plugin    Stream open/close lifecycle      src/modules/module-pal-sink.c  Modify
   PAL                    usecase_mgr start/stop ramp      Pal.cpp, ResourceManager.cpp   Modify
   AudioReach / ADSP      Codec pop suppression            AudioReachGraph.cpp            Investigate
```

### Success criteria

- Component list matches what an experienced engineer would write for 8/10 test cases
- Source file paths are correct and navigable
- New engineer can find the right file in under 2 minutes using the output

---

## M4 · Weeks 7–8 · Platform Intelligence & QLI Stack Awareness

### What we build

The skill learns the differences between every supported platform and between
QLI 1.x and QLI 2.x. It auto-detects the platform from the issue text, flags
features that are unavailable on that platform, and adjusts the proposal
accordingly.

### Why it matters to the Director

A proposal that suggests enabling SSMD on a QLI 1.x platform is worse than
useless — it sends an engineer down a dead end. Platform awareness prevents
that. It also means the skill can warn about Config 2 requirements, ADSP
firmware dependencies, and modem audio constraints before work starts.

### Detailed deliverables

**Platform matrix (built into script + `references/platform_matrix.md`):**

| Platform | QLI | Config 1 | Config 2 | SSMD | Fluence | BT offload | Compressed | Modem |
|---|---|---|---|---|---|---|---|---|
| IQ615 | 1.x | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| IQ8275-EVK | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| IQ9075 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| RB3-Gen2 | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| QCS6490 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SA8775P | 2.x | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**QLI 1.x vs 2.x feature delta (shown in every proposal):**

| Feature | QLI 1.x | QLI 2.x |
|---|---|---|
| Audio backend | ALSA (spa.alsa direct) | PAL → AudioReach → ADSP |
| DSP offload | No | Yes |
| SSMD | No | Yes |
| Fluence | No | Yes |
| Config 2 | No | Yes |
| Modem audio | No | Yes |
| BT offload | No | Yes |
| WirePlumber | 0.4.x | 0.5.x |
| PipeWire | 0.3.x | 1.x |
| pipewire-pal-plugin | No | Yes |

**Script changes:**
- Auto-detect platform from issue text (IQ9075, QCS6490, SA8775P, RB3, etc.)
- `--platform PLATFORM` flag for explicit override
- Platform constraint warnings in Section 4 (Gap Analysis):
  - "SSMD requires QLI 2.x — IQ615 does not support this"
  - "Config 2 required for Fluence — confirm topology is loaded"
  - "Modem audio only available on QCS6490 and SA8775P"
- Platform context block appended to every proposal
- `--list-platforms` flag: print full platform matrix

**`references/platform_matrix.md` expanded:**
- Known issue patterns per platform (IQ9075 codec pop, QCS6490 modem startup race, etc.)
- Firmware dependency notes per platform
- Config 1 vs Config 2 availability and switching procedure

### Demo for Director

```
$ python3 analyze_enhancement.py \
    --issue "SSMD not working on IQ615" \
    --goal  "Enable simultaneous speaker + headphone playback"

4. Gap Analysis
   ⚠  SSMD is NOT supported on IQ615 (QLI 1.x) — this feature requires QLI 2.x
   ⚠  Consider targeting IQ9075, QCS6490, or RB3-Gen2 instead

Platform context:
   Platform : IQ615
   Stack    : QLI 1.x
   SSMD     : ✗ Not supported
   Config 2 : ✗ Not supported
```

### Success criteria

- Platform auto-detected correctly from issue text in 9/10 cases
- Platform constraint warnings prevent at least one dead-end investigation
- `--list-platforms` output used by a new engineer to choose the right target

---

### Month 2 Checkpoint — What the Director sees

**Live demo (5 minutes):**
1. Run the same issue as Month 1 — show how Section 3 now has real source files
2. Run an SSMD issue on IQ615 — show the platform constraint warning
3. Run an issue on QCS6490 — show modem audio awareness
4. Show `--list-platforms` output

**Value delivered:** Proposals are now specific enough to hand to an engineer
as a real starting point. No more "which file do I change?" or "does this
platform support this feature?" — the skill answers both instantly.

---

---

# MONTH 3 — Depth & Automation: The Full Engineering Assistant

**Theme:** Add the hardest and most valuable content — ranked root-cause
hypotheses, effort-estimated implementation plans, ready-to-run diagnostic
commands, and a complete test plan. Then package everything as a production
QGenie skill any engineer can install and use.

---

## M5 · Weeks 9–10 · Architecture Depth, Hypotheses & Diagnostic Runbook

### What we build

Two things that currently take the most engineering time:
1. **Root-cause hypotheses** — ranked by probability, drawn from known patterns
2. **Diagnostic runbook** — exact shell commands to run, in the right order,
   platform-specific

### Why it matters to the Director

These are the two things that separate a senior engineer from a junior one on
a new issue. The senior engineer knows "for a playback glitch on QLI 2.x, check
the PAL stream open timing first, then spa.alsa underruns, then WirePlumber
activation order." The junior engineer doesn't. This skill gives every engineer
that senior-level starting point.

### Detailed deliverables

**Architecture & Design Notes (Section 5) — fully generated:**

For each issue type + platform combination, the skill generates:
- How the relevant part of the audio stack works (factual, not hypothesis)
- AudioReach graph construction chain where relevant
- 2–4 ranked root-cause hypotheses, each labelled *(hypothesis)*
- Proposed investigation order (highest probability first)

Example for audio glitch on QLI 2.x:
```
How it works:
  PipeWire node → pipewire-pal-plugin → PAL::StreamPCM::open()
  → ResourceManager::getAudioRoute() → AGM::sessionOpen()
  → ADSP graph (SPF) → Codec / I2S

Root-cause hypotheses (ranked):
  1. [HIGH] PAL stream open triggers codec pop without mute ramp
             → Check: logcat -s PAL:V | grep 'setVolume\|mute'
  2. [MED]  SPA/ALSA underrun during first buffer cycle
             → Check: PIPEWIRE_DEBUG=3 pw-play x.wav | grep xrun
  3. [LOW]  WirePlumber activates node before ADSP graph is stable
             → Check: journalctl -u wireplumber | grep 'activat'
```

**Diagnostic Runbook (Section 7 addition) — platform-specific commands:**

For each issue type, the skill generates an ordered list of diagnostic commands:
- Ordered by "most likely to reveal the root cause first"
- Platform-specific: `logcat` commands for QLI 2.x, `journalctl` for QLI 1.x
- Each command annotated with what to look for in the output
- Copy-paste ready — no editing needed

Example for audio glitch on IQ9075 (QLI 2.x):
```
Diagnostic Runbook — run in this order:

  Step 1: Check for xruns during playback
    $ PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i 'underrun|xrun|error'
    Look for: any xrun count > 0

  Step 2: Watch real-time graph state
    $ pw-top
    Look for: xrun counter incrementing in first 500ms

  Step 3: Check WirePlumber activation timing
    $ journalctl -u wireplumber --since "1 min ago" | grep -i 'activat|link|node'
    Look for: node activated before PAL stream open completes

  Step 4: Check PAL stream lifecycle  [QLI 2.x only]
    $ logcat -s PAL:V AGM:V | grep -i 'stream|open|close|volume|mute'
    Look for: setVolume called before mute ramp completes
```

**`references/platform_matrix.md` — known issue patterns section expanded:**
- Per-platform known issue patterns with diagnostic steps
- Common root causes per symptom type
- Links to relevant source files for each pattern

### Success criteria

- Diagnostic runbook used by an engineer on a real issue and saves > 1 hour
- Root-cause hypothesis ranked #1 is correct in 6/10 real cases
- Architecture notes are factually accurate (reviewed by a senior engineer)

---

## M6 · Weeks 11–12 · Implementation Plan, Test Plan & QGenie Integration

### What we build

Complete the proposal quality (implementation plan + test plan with real
commands), then package everything as a production QGenie skill — installable
in one command, usable by any engineer in plain English.

### Why it matters to the Director

This is the difference between a useful script and a team-wide tool. After M6,
any engineer on the team — including new joiners — can type a plain-English
description of their issue into QGenie and get a complete, actionable proposal
in under 60 seconds. No setup, no commands to remember, no documentation to read.

### Detailed deliverables

**Implementation Plan (Section 6) — fully generated:**

For each issue type + component combination, the skill generates:
- Ordered task list (investigation → fix → test → document)
- Component owner for each task (SPA, PAL, WirePlumber, etc.)
- Effort estimate: S (< 1 day), M (2–3 days), L (1+ week)
- Dependencies between tasks (task 3 requires task 1 to be complete)

Example for audio glitch:
```
6. Implementation Plan

  Step  Area           Task                                          Effort  Depends on
  ────────────────────────────────────────────────────────────────────────────────────
  1     Investigation  Run diagnostic runbook, collect logs          S       —
  2     PAL            Enable codec pop-suppression stream attr      S       1
  3     SPA            Add pre-roll silent buffer in spa.alsa        M       1
  4     WirePlumber    Add PAL-ready activation delay hook           M       1
  5     Test           Measure glitch with/without each fix          S       2,3,4
  6     Documentation  Update troubleshooting guide                  S       5
```

**Test Plan (Section 7) — exact commands with pass/fail criteria:**

For each issue type + platform, the skill generates:
- Numbered test cases with exact commands
- Expected output / pass criteria for each
- Regression test cases (existing paths must not break)
- Stress test cases (stability over time)

Example for audio glitch on IQ9075:
```
7. Test & Validation Plan

  TC-1: Basic playback — no glitch
    $ pw-play /usr/share/sounds/alsa/Front_Left.wav
    Pass: no audible tick at start or end

  TC-2: pw-top xrun check
    $ pw-top  (observe during TC-1)
    Pass: xrun counter = 0 during first 500ms

  TC-3: GStreamer pipeline
    $ gst-launch-1.0 audiotestsrc freq=1000 num-buffers=100 ! pipewiresink
    Pass: no glitch, no xruns

  TC-4: Regression — arecord/aplay direct ALSA
    $ arecord -d 5 /tmp/test.wav && aplay /tmp/test.wav
    Pass: clean recording and playback, no regression

  TC-5: Stress — 100 play/stop cycles
    $ for i in $(seq 100); do pw-play test.wav; done
    Pass: no xruns in any cycle
```

**QGenie skill packaging:**
- `SKILL.md` with trigger phrases, input collection rules, output format
- `agents/openai.yaml` updated with new capabilities
- Conversational mode: agent asks issue + goal, produces full proposal
- `--interactive` mode in the script for direct terminal use
- Installable from GitHub:
  ```
  Install the pipewire-enhancement skill from sauravk-git/saurav-skills
  ```
- README updated with all usage examples, flags, and 3 worked examples

**3 worked examples in `references/examples.md`:**
1. Audio glitch at playback start/end (IQ9075, QLI 2.x) — full proposal
2. SSMD not working (IQ9075) — full proposal with platform constraints
3. Config 1 vs Config 2 documentation — full proposal

### Demo for Director (end of Month 3)

```
[QGenie CLI]

User: Audio glitch at playback start on IQ9075 QLI 2.x — help me plan the fix

Agent: I'll generate a full enhancement proposal. One question:
       What is your goal — eliminate the glitch entirely, or reduce it to
       an acceptable level?

User: Eliminate it completely without regressing other audio paths

Agent: [produces full 10-section proposal in < 5 seconds]
       — Section 3: exact source files to change
       — Section 5: 3 ranked hypotheses with diagnostic commands
       — Section 6: 6-step implementation plan with effort estimates
       — Section 7: 5 test cases with exact commands and pass criteria
       — Section 9: platform constraints for IQ9075 QLI 2.x
```

### Success criteria

- Any team member installs and uses the skill without help
- Proposal quality rated ≥ 4/5 by 3 engineers on real issues
- Director demo: live end-to-end in under 2 minutes
- At least 2 real enhancement proposals generated and used by the team

---

---

# Summary: What the Director Sees at Each Monthly Review

| Review | Date | What you demo | Value delivered |
|---|---|---|---|
| **Month 1** | End of week 4 | Type issue → get 10-section proposal in 10 seconds | 2–3 hrs saved per proposal |
| **Month 2** | End of week 8 | Real source files, platform constraints, QLI delta | 1–2 hrs saved per investigation |
| **Month 3** | End of week 12 | Full QGenie skill, diagnostic runbook, test plan | 6–7 hrs total saved per issue |

---

# Cumulative Capability Growth

| After | Capability added | Time saved per issue |
|---|---|---|
| M1 (wk 2) | Classify any issue into the right type | ~30 min |
| M2 (wk 4) | Generate full 10-section proposal skeleton | ~2 hrs |
| M3 (wk 6) | Know exactly which source files to touch | ~1 hr |
| M4 (wk 8) | Platform constraints, QLI 1.x vs 2.x delta | ~1 hr |
| M5 (wk 10) | Ranked hypotheses + ready-to-run diagnostics | ~1–2 hrs |
| M6 (wk 12) | Full QGenie skill, test plan, worked examples | ~1 hr |
| **Total** | | **~6–7 hrs per issue** |

---

# What Is NOT in Scope (this 3 months)

| Out of scope | Why / future milestone |
|---|---|
| Writing code changes automatically | Proposals only — code generation is a separate skill |
| Orbit / JIRA ticket creation | Future integration milestone |
| Real-time log analysis | Requires log streaming infrastructure |
| Non-Qualcomm PipeWire platforms | Out of domain for this skill |
| Automated hardware-in-loop testing | Requires lab infrastructure |

---

# Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Keyword matching too shallow for complex issues | Medium | Medium | Build test suite at M1; iterate on keyword map each sprint |
| Platform matrix goes stale as new platforms ship | Low | Medium | Matrix in a separate `.md` file — easy to update in 30 min |
| Team doesn't adopt the skill | Low | High | Demo on a real issue from the backlog at M2 review |
| Director wants faster results | Low | Low | M2 already produces a full proposal — can demo at week 4 |
| Root-cause hypotheses are wrong | Medium | Medium | Label all hypotheses clearly; validate with senior engineer |

