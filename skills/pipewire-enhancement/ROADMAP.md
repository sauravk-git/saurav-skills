# PipeWire Enhancement Skill — 3-Month Roadmap

---

## Overview

Build a PipeWire Enhancement Engineering assistant for Qualcomm QLI /
AudioReach / PAL stacks that grows in capability across three months:

- **Month 1** — Understand and diagnose basic, well-known issues
- **Month 2** — Handle medium-complexity issues; reason about components,
  platforms, and root causes
- **Month 3** — Accept architecture input and produce design proposals;
  deliver guidance for new features end-to-end

Each milestone builds directly on the previous one. Nothing is thrown away.

---

## Milestone Overview

| # | Weeks | Capability level | What the skill can do by end of milestone |
|---|---|---|---|
| M1 | 1–2 | Basic issue intake | Classify any issue into the right type |
| M2 | 3–4 | Basic issue diagnosis | Produce a structured diagnosis for common, known issues |
| M3 | 5–6 | Medium issue — component depth | Identify affected components and source files |
| M4 | 7–8 | Medium issue — platform reasoning | Apply platform constraints; flag QLI 1.x vs 2.x differences |
| M5 | 9–10 | Complex issue — root cause + diagnostics | Rank hypotheses; generate platform-specific diagnostic runbook |
| M6 | 11–12 | New feature — design proposal | Accept architecture input; produce design, implementation plan, test plan |

---

---

# MONTH 1 — Basic Issue Understanding

**Goal:** The skill can read a plain-English issue description, understand
what kind of problem it is, and produce a structured first-pass diagnosis
for the most common, well-understood issue types.

Scope is deliberately narrow — only issues that have clear, known patterns
(audio glitch, device not found, startup race, routing misconfiguration).
No guessing, no architecture reasoning yet.

---

## M1 · Weeks 1–2 · Issue Classification

### What gets built

A classifier that reads a plain-English issue description and maps it to one
or more of 13 enhancement types. This is the entry point for everything that
follows — every subsequent capability depends on knowing the type first.

**The 13 enhancement types:**

| # | Type | What it covers | Example trigger |
|---|---|---|---|
| 1 | New PipeWire feature | Something that doesn't exist yet | *"Add compressed offload support"* |
| 2 | Existing feature enhancement | Something works but needs to work better | *"Improve BT audio quality"* |
| 3 | Performance improvement | Latency, CPU, power, offload efficiency | *"Reduce audio latency on QCS6490"* |
| 4 | Startup / enumeration | Device not showing up, boot ordering race | *"Audio device missing after reboot"* |
| 5 | Audio quality | Glitch, tick, pop, noise, crackle, distortion | *"Tick at playback start on IQ9075"* |
| 6 | Routing / policy | Wrong sink/source, SSMD, device switching | *"Audio goes to wrong output after BT connects"* |
| 7 | Configuration | Config 1/2, topology .bin, Lua, WirePlumber settings | *"Config 2 topology not loading"* |
| 8 | PAL / AudioReach integration | PAL, AudioReach, ADSP, AGM, SPF layer | *"PAL stream open fails after modem restart"* |
| 9 | API / ABI | Interface changes, protocol, ABI compatibility | *"PipeWire API change breaks pal-plugin"* |
| 10 | Debugging / RCA | Unknown root cause — needs investigation first | *"Random audio dropout, no obvious cause"* |
| 11 | Documentation | Something needs to be written or updated | *"No docs for SSMD setup on IQ9075"* |
| 12 | Test / validation | Adding tests, automating validation, CI | *"No automated test for compressed offload"* |
| 13 | Packaging / deployment | Yocto recipes, Debian packages, RPM specs | *"PipeWire Yocto recipe missing PACKAGECONFIG"* |

> Most real issues match 2 types simultaneously — e.g. a playback glitch is
> both Type 5 (audio quality) and Type 10 (debugging). The classifier returns
> a primary type and secondary types; the proposal covers all of them.

**Deliverables:**
- `classify.py` — accepts `--issue` text, returns ranked type list
- `--list-types` flag to print all 13 types
- `--verbose` flag to show which keywords triggered each match
- `references/enhancement_types.md` — full type definitions, keyword lists,
  decision guide for overlapping types
- Test suite: 15 real issues, expected types, pass/fail report

**Example output:**
```
$ python3 classify.py --issue "Audio tick at playback start on IQ9075 QLI 2.x"
  Primary  : Type 5 — Audio quality improvement
  Secondary: Type 10 — Debugging / root-cause investigation
```

**Done when:** Correctly classifies 13/15 test issues; runs in under 1 second.

---

## M2 · Weeks 3–4 · Basic Issue Diagnosis

### What gets built

Extend the classifier into a full diagnosis tool for basic, well-known issue
types. Given an issue and a goal, it produces a structured 10-section document.
At this stage, sections are populated with known patterns for common issues —
no deep reasoning, no architecture inference yet.

**The 10-section proposal structure:**

| # | Section | Content at this stage |
|---|---|---|
| 1 | Summary | Plain-English restatement of issue + goal |
| 2 | Classification | Matched types from M1 |
| 3 | Affected Components | Placeholder — filled in M3 |
| 4 | Gap Analysis | Missing info: platform, version, logs |
| 5 | Architecture Notes | Known pattern description for this issue type |
| 6 | Implementation Plan | Generic task list for this issue type |
| 7 | Test & Validation Plan | Standard test cases for this issue type |
| 8 | Documentation Tasks | What docs to update based on type |
| 9 | Open Questions & Risks | Standard risks for this issue type |
| 10 | Acceptance Criteria | Measurable done conditions for this type |

**Scope at M2 — issue types handled with real content (not placeholders):**
- Type 4: Startup / enumeration issues
- Type 5: Audio quality issues (glitch, tick, pop)
- Type 6: Routing / policy issues
- Type 10: Debugging / RCA

All other types get a structured skeleton with generic content — to be
enriched in later milestones.

**Deliverables:**
- `analyze_enhancement.py` — extends `classify.py`
- Conversational mode: prompts for issue + goal if no args given
- `--from-file FILE` — read issue (line 1) and goal (line 2) from a text file
- `--no-color` — plain text output for saving to file
- `--output markdown` — save proposal as `.md`

**Example output:**
```
$ python3 analyze_enhancement.py \
    --issue "Audio tick at playback start on IQ9075 QLI 2.x" \
    --goal  "Eliminate the tick without regressing other audio paths"

1. Summary
   Audio tick observed at playback start on IQ9075 QLI 2.x. Goal is to
   eliminate the tick without regressing other audio paths.

2. Classification
   ✓  5. Audio quality improvement
   ✓  10. Debugging / root-cause investigation

3. Affected Components
   [to be filled — component awareness added in M3]

4. Gap Analysis
   ⚠  PipeWire version not specified
   ⚠  No diagnostic logs provided
   ⚠  Whether issue is in both channels not stated

5. Architecture Notes
   Known pattern: tick at playback start is commonly caused by codec pop
   on stream open, SPA/ALSA underrun in first buffer cycle, or WirePlumber
   activating the node before the ADSP graph is stable.

...sections 6–10...
```

**Done when:** Proposal covers all 10 sections for any input; output for
Type 4, 5, 6, 10 issues is specific enough to act on without manual editing.

---

### Month 1 — Capability checkpoint

By end of week 4 the skill can:
- Accept any PipeWire issue in plain English
- Classify it into the right type(s) in under 1 second
- Produce a structured 10-section diagnosis document for common issue types
- Identify what information is missing before work can start

---

---

# MONTH 2 — Medium Issue Handling

**Goal:** The skill moves beyond known patterns and starts reasoning about
the specific issue — which components are actually involved, which source
files to look at, and whether the target platform even supports the requested
feature. Proposals become specific enough to hand to an engineer as a real
starting point.

---

## M3 · Weeks 5–6 · Component & Source File Awareness

### What gets built

The skill learns which components are affected by which issue types and maps
each to its actual source files. Section 3 (Affected Components) goes from
a placeholder to a precise, actionable table.

**Component coverage:**

| Issue keyword | Affected components | Key source paths |
|---|---|---|
| glitch / tick / pop | SPA (spa.alsa), PipeWire Core (node state), pipewire-pal-plugin (stream lifecycle), PAL (usecase ramp), AudioReach/ADSP (codec pop) | `spa/plugins/alsa/alsa-pcm.c`, `src/modules/module-pal-sink.c`, `Pal.cpp` |
| startup / enumeration | WirePlumber (device discovery), Yocto (systemd ordering), PAL (remoteproc startup) | `modules/module-device-activation.c`, `wireplumber.conf` |
| latency / performance | PipeWire Core (quantum/scheduling), SPA (buffer tuning), PAL (DSP offload) | `src/pipewire/impl-node.c`, `src/modules/module-rt.c` |
| SSMD / multi-device | PAL (multi-device usecase), AudioReach (SSMD topology), WirePlumber (multi-sink policy) | `ResourceManager.cpp`, `AudioReachGraph.cpp` |
| routing / policy | WirePlumber (default sink/source), PipeWire Core (link management) | `modules/module-default-nodes.c`, `module-si-standard-link.c` |
| Config 1 / Config 2 | PAL (topology selection), AudioReach (.bin loading), Yocto (firmware packaging) | `Pal.cpp`, `/lib/firmware/qcom/` |
| Fluence / voice | AudioReach/ADSP (Fluence graph), PAL (voice usecase), WirePlumber (capture routing) | `AudioReachGraph.cpp`, `resourcemanager.xml` |
| compressed offload | SPA (compress path), PAL (StreamCompress), PipeWire Core (compressed scheduling) | `spa/plugins/alsa/alsa-compress-offload.c`, `StreamCompress.cpp` |

**9 component layers always shown in proposals:**
```
Client & Tools → PipeWire Core → SPA → WirePlumber → PipeWire-Pulse
     → Compressed Offload → Qualcomm PAL → Topology → Yocto/Packaging
```

**Deliverables:**
- Section 3 auto-populated: component, sub-component, source path, change type
- `--show-components` flag: print full component map for a given issue type
- `references/component_map.md` expanded with full source-file mapping,
  AudioReach graph construction chain, SPA plugin registry, WirePlumber
  Lua config file locations

**Example output:**
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

**Done when:** Component list matches what an experienced engineer would
write for 8/10 test cases; source file paths are correct and navigable.

---

## M4 · Weeks 7–8 · Platform Intelligence & QLI Stack Awareness

### What gets built

The skill learns the differences between every supported platform and between
QLI 1.x and QLI 2.x. It auto-detects the platform from the issue text, flags
features unavailable on that platform, and adjusts the proposal accordingly.

**Platform capability matrix:**

| Platform | QLI | Config 1 | Config 2 | SSMD | Fluence | BT offload | Compressed | Modem |
|---|---|---|---|---|---|---|---|---|
| IQ615 | 1.x | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| IQ8275-EVK | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| IQ9075 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| RB3-Gen2 | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| QCS6490 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SA8775P | 2.x | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**QLI 1.x vs 2.x feature delta:**

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

**Deliverables:**
- Auto-detect platform from issue text; `--platform` flag for explicit override
- Platform constraint warnings in Section 4:
  - *"SSMD requires QLI 2.x — IQ615 does not support this"*
  - *"Config 2 required for Fluence — confirm topology is loaded"*
  - *"Modem audio only available on QCS6490 and SA8775P"*
- Platform context block appended to every proposal
- `--list-platforms` flag: print full platform matrix
- `references/platform_matrix.md` expanded: known issue patterns per platform,
  firmware dependency notes, Config 1 vs Config 2 switching procedure

**Example output:**
```
$ python3 analyze_enhancement.py \
    --issue "SSMD not working on IQ615" \
    --goal  "Enable simultaneous speaker + headphone playback"

4. Gap Analysis
   ⚠  SSMD is NOT supported on IQ615 (QLI 1.x) — requires QLI 2.x
   ⚠  Consider targeting IQ9075, QCS6490, or RB3-Gen2 instead

Platform context:
   Platform : IQ615  |  Stack: QLI 1.x  |  SSMD: ✗  |  Config 2: ✗
```

**Done when:** Platform auto-detected correctly in 9/10 cases; constraint
warnings prevent at least one dead-end investigation.

---

### Month 2 — Capability checkpoint

By end of week 8 the skill can:
- Identify the exact components and source files involved in any issue
- Apply platform constraints and QLI 1.x vs 2.x differences automatically
- Produce proposals specific enough to hand to an engineer as a starting point
- Prevent proposals that suggest features unavailable on the target platform

---

---

# MONTH 3 — Complex Issues, Architecture Input & New Feature Delivery

**Goal:** The skill handles the hardest class of problems — unknown root
causes requiring investigation, and new features requiring design. For
complex issues it generates ranked hypotheses and a ready-to-run diagnostic
runbook. For new features it accepts architecture input (component descriptions,
data flow, constraints) and produces a full design proposal with implementation
plan and test plan.

---

## M5 · Weeks 9–10 · Complex Issue — Root Cause Analysis & Diagnostics

### What gets built

For issues where the root cause is unknown (Type 10) or where the symptom
could have multiple causes (Type 5, 4, 6), the skill generates:

1. **Ranked root-cause hypotheses** — drawn from known patterns in the
   platform matrix, ordered by probability for the given platform and issue type
2. **Diagnostic runbook** — exact shell commands to run, in the right order,
   platform-specific, each annotated with what to look for

**Root-cause hypothesis generation:**

For each issue type + platform combination, the skill produces:
- How the relevant part of the stack works (factual)
- AudioReach graph construction chain where relevant
- 2–4 ranked hypotheses, each labelled *(hypothesis)*
- Proposed investigation order (highest probability first)
- Per-hypothesis: the one command most likely to confirm or rule it out

**Example — audio glitch on IQ9075 (QLI 2.x):**
```
5. Architecture Notes

  How it works:
    PipeWire node → pipewire-pal-plugin → PAL::StreamPCM::open()
    → ResourceManager::getAudioRoute() → AGM::sessionOpen()
    → ADSP graph (SPF) → Codec / I2S

  Root-cause hypotheses (ranked):
    1. [HIGH] PAL stream open triggers codec pop without mute ramp
               → Confirm: logcat -s PAL:V | grep 'setVolume\|mute'
    2. [MED]  SPA/ALSA underrun during first buffer cycle
               → Confirm: PIPEWIRE_DEBUG=3 pw-play x.wav | grep xrun
    3. [LOW]  WirePlumber activates node before ADSP graph is stable
               → Confirm: journalctl -u wireplumber | grep 'activat'
```

**Diagnostic runbook — platform-specific, copy-paste ready:**

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

**Deliverables:**
- Section 5 fully generated with ranked hypotheses per issue type + platform
- Diagnostic runbook added to Section 7 (platform-specific: `logcat` for
  QLI 2.x, `journalctl` for QLI 1.x)
- `references/platform_matrix.md` — known issue patterns section expanded
  with per-platform root causes and diagnostic steps

**Done when:** Hypothesis ranked #1 is correct in 6/10 real cases; diagnostic
runbook is used on a real issue and saves measurable investigation time.

---

## M6 · Weeks 11–12 · New Feature — Architecture Input & Design Proposal

### What gets built

The skill gains the ability to handle new feature requests (Types 1, 2, 3, 8,
9) — but only when sufficient architecture context is provided. It accepts
architecture input (component descriptions, data flow diagrams, constraints,
existing API details) and uses that to produce a full design proposal.

Without architecture input, the skill asks for it rather than guessing.

**Architecture input modes:**

| Mode | How to provide | When to use |
|---|---|---|
| `--arch-file FILE` | Markdown or text file describing the architecture | When you have existing design docs |
| `--component-desc TEXT` | Free-text description of the relevant component | For targeted feature additions |
| `--data-flow TEXT` | Description of the data flow to be modified | For pipeline or routing changes |
| Conversational | Agent asks structured questions about the architecture | When starting from scratch |

**What the skill produces for a new feature request:**

| Section | Content for new features |
|---|---|
| 5. Architecture Notes | How the existing stack works in the relevant area; where the new feature fits; interface points; constraints |
| 6. Implementation Plan | Ordered tasks: design → prototype → integrate → test → document; effort (S/M/L); dependencies |
| 7. Test & Validation Plan | Unit tests, integration tests, regression tests, stress tests — with exact commands |
| 8. Documentation Tasks | New API docs, integration guide, example code, changelog entry |
| 9. Risks | API compatibility, performance impact, platform availability, firmware dependency |
| 10. Acceptance Criteria | Measurable conditions: functional, performance, regression, documentation |

**Example — new feature with architecture input:**
```
$ python3 analyze_enhancement.py \
    --issue "Add always-on audio support for IQ9075 QLI 2.x" \
    --goal  "Enable low-power always-on capture via ADSP without waking HLOS" \
    --arch-file ./always_on_arch.md

5. Architecture Notes
   Always-on audio requires the ADSP to run a capture graph independently
   of the HLOS. On IQ9075 (QLI 2.x), this is supported via PAL's
   AUDIO_USECASE_RECORD_VOIP_CALL usecase with the ADSP in island mode.

   Integration point: PAL → AGM → ADSP island mode graph.
   New component needed: WirePlumber policy to suspend HLOS-side nodes
   while ADSP capture is active.

   Constraints:
   - Requires Config 2 topology (ADSP island mode not available in Config 1)
   - Firmware: adsp_island.mbn must be present in /lib/firmware/qcom/
   - Not available on QLI 1.x platforms

6. Implementation Plan
   Step  Area           Task                                        Effort  Depends on
   ──────────────────────────────────────────────────────────────────────────────────
   1     Investigation  Verify ADSP island mode on IQ9075           S       —
   2     PAL            Add always-on usecase to resourcemanager.xml M      1
   3     AGM            Configure island mode graph in topology .bin L      2
   4     WirePlumber    Add HLOS suspend policy for always-on mode   M      2
   5     pipewire-pal   Add always-on stream type in pal-plugin      M      3
   6     Test           Verify capture without HLOS wakeup           M      4,5
   7     Documentation  New section: Always-on audio on IQ9075       S      6
```

**QGenie skill packaging (also completed in M6):**
- `SKILL.md` updated with new capabilities and trigger phrases
- `agents/openai.yaml` updated
- Conversational mode handles all 6 milestone capabilities
- Installable: `Install the pipewire-enhancement skill from sauravk-git/saurav-skills`
- README updated with all usage examples and 3 worked examples
- `references/examples.md` — 3 full worked examples:
  1. Audio glitch at playback start (IQ9075, QLI 2.x) — complex issue
  2. SSMD not working (IQ9075) — medium issue with platform constraints
  3. Always-on audio (IQ9075) — new feature with architecture input

**Done when:** Skill produces a usable design proposal for a new feature
when architecture input is provided; proposal reviewed and accepted by a
senior engineer without major rework.

---

### Month 3 — Capability checkpoint

By end of week 12 the skill can:
- Diagnose complex issues with unknown root causes
- Generate a platform-specific, copy-paste-ready diagnostic runbook
- Accept architecture input and produce a full design proposal for new features
- Deliver an end-to-end implementation plan with effort estimates and dependencies
- Handle all 13 enhancement types with real, specific content

---

---

# Capability Growth Summary

| Milestone | Capability added | Issue complexity handled |
|---|---|---|
| M1 (wk 2) | Classify any issue into the right type(s) | All types — classification only |
| M2 (wk 4) | Structured diagnosis for common known issues | Basic: Type 4, 5, 6, 10 |
| M3 (wk 6) | Identify affected components and source files | Basic + medium |
| M4 (wk 8) | Apply platform constraints; QLI 1.x vs 2.x delta | Basic + medium, platform-aware |
| M5 (wk 10) | Ranked hypotheses; platform-specific diagnostic runbook | Complex / unknown root cause |
| M6 (wk 12) | Accept architecture input; design proposal for new features | New features (Types 1, 2, 3, 8, 9) |

---

# Out of Scope (this 3 months)

| Item | Reason |
|---|---|
| Automatically writing code changes | Proposals and design only — code generation is a separate capability |
| Orbit / JIRA ticket creation | Future integration |
| Real-time log analysis | Requires log streaming infrastructure |
| Non-Qualcomm PipeWire platforms | Out of domain |
| Automated hardware-in-loop testing | Requires lab infrastructure |

---

# Risks

| Risk | Mitigation |
|---|---|
| Keyword matching too shallow for complex issues | Build test suite at M1; iterate on keyword map each sprint |
| Platform matrix goes stale as new platforms ship | Matrix in a separate `.md` file — updatable in 30 min |
| Root-cause hypotheses are wrong | Label all hypotheses clearly; validate with a senior engineer before relying on them |
| Architecture input quality varies | Skill asks structured clarifying questions when input is insufficient |
| New feature scope creep | M6 only produces design proposals — implementation is out of scope |
