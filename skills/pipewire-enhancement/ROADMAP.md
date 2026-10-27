# PipeWire Enhancement Skill — 4-Month Roadmap

---

## Overview

Build a PipeWire Enhancement Engineering assistant for Qualcomm QLI /
AudioReach / PAL stacks that grows in capability across four months.

The progression follows the natural order of engineering work:

- **Month 1** — Understand the issue: classify it, identify what is known,
  produce a structured diagnosis with config-level fix suggestions
- **Month 2** — Go deeper: identify exact components, source files, and
  platform constraints; suggest targeted code changes for known fix patterns
- **Month 3** — Handle complex unknowns: rank root-cause hypotheses, generate
  diagnostic runbooks, produce multi-file code change suggestions
- **Month 4** — New features: accept architecture input, produce full design
  proposals, generate implementation-ready code scaffolding

Code change suggestions are present from Month 1 and grow in depth and
specificity at every milestone.

---

## Milestone Overview

| # | Weeks | Capability | Code suggestion depth |
|---|---|---|---|
| M1 | 1–2 | Issue classification | — |
| M2 | 3–4 | Structured diagnosis for basic issues | Config snippets and known one-line fixes |
| M3 | 5–6 | Component and source file awareness | Targeted single-file code change suggestions |
| M4 | 7–8 | Platform intelligence and QLI stack reasoning | Platform-conditional code changes; QLI 2.x-specific patches |
| M5 | 9–10 | Complex issue — root cause analysis and diagnostics | Multi-file diff suggestions with context and rationale |
| M6 | 11–12 | Complex issue — full fix delivery | Complete, reviewable code changes across all affected files |
| M7 | 13–14 | New feature — design and scaffolding | Architecture-driven code scaffolding and API stubs |
| M8 | 15–16 | New feature — full implementation guidance | End-to-end implementation code with integration plan |

---

---

# MONTH 1 — Issue Understanding and Basic Diagnosis

**Goal:** The skill reads a plain-English issue description, classifies it,
and produces a structured first-pass diagnosis for the most common, well-known
issue types. Code suggestions at this stage are config-level and one-liners —
things that can be applied immediately without deep code knowledge.

---

## M1 · Weeks 1–2 · Issue Classification

### What gets built

A classifier that reads a plain-English issue description and maps it to one
or more of 13 enhancement types. Every subsequent capability depends on
knowing the type first.

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
- `--list-types` flag, `--verbose` flag
- `references/enhancement_types.md` — type definitions, keyword lists,
  decision guide for overlapping types
- Test suite: 15 real issues, expected types, pass/fail report

**Done when:** Correctly classifies 13/15 test issues in under 1 second.

---

## M2 · Weeks 3–4 · Basic Issue Diagnosis with Config-Level Fix Suggestions

### What gets built

Extend the classifier into a full diagnosis tool for basic, well-known issue
types. Produces a structured 10-section document. Adds the first layer of
code change suggestions — config snippets and known one-line fixes that apply
to the most common patterns.

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

**Code suggestion depth at M2 — config snippets and known one-liners:**

For the most common issue types, the skill suggests the first thing to try
before any code change — a config tweak, a WirePlumber Lua setting, or a
known one-line fix that resolves the issue in many cases.

Examples:

*Startup / enumeration race (Type 4):*
```ini
# /etc/systemd/system/wireplumber.service.d/override.conf
# Add ADSP/remoteproc dependency so WirePlumber waits for the sound card
[Unit]
After=sound.target
Wants=sound.target
```

*Audio glitch — try lower quantum first (Type 5):*
```bash
# /etc/pipewire/pipewire.conf.d/99-quantum.conf
context.properties = {
    default.clock.quantum     = 1024
    default.clock.min-quantum = 512
}
```

*Wrong default sink (Type 6):*
```bash
# WirePlumber — set default sink by name
wpctl set-default $(wpctl status | grep "IQ9075" | awk '{print $2}' | tr -d '.')
```

*Config 2 topology not loading (Type 7):*
```bash
# Verify topology .bin is present and readable
ls -lh /lib/firmware/qcom/*.bin
# Check PAL log for topology load errors
logcat -s PAL:V | grep -i 'topology\|bin\|load'
```

**Issue types with real content at M2:**
- Type 4: Startup / enumeration
- Type 5: Audio quality (glitch, tick, pop)
- Type 6: Routing / policy
- Type 7: Configuration
- Type 10: Debugging / RCA

**Deliverables:**
- `analyze_enhancement.py` — extends `classify.py`
- Conversational mode, `--from-file`, `--no-color`, `--output markdown`
- Config snippet suggestions embedded in Section 6 for Types 4, 5, 6, 7, 10

**Done when:** Output for Types 4, 5, 6, 7, 10 includes at least one
actionable config-level fix suggestion; proposal covers all 10 sections.

---

### Month 1 — Capability checkpoint

- Classifies any issue into the right type(s) in under 1 second
- Produces a structured 10-section diagnosis for common issue types
- Suggests config-level fixes and known one-liners for Types 4, 5, 6, 7, 10
- Identifies what information is missing before work can start

---

---

# MONTH 2 — Component Depth and Targeted Code Changes

**Goal:** The skill identifies the exact components and source files involved,
applies platform constraints, and suggests targeted single-file code changes
for known fix patterns — specific enough for an engineer to open the file,
find the location, and apply the change.

---

## M3 · Weeks 5–6 · Component Awareness and Single-File Code Suggestions

### What gets built

Section 3 (Affected Components) goes from a placeholder to a precise table
with source file paths. Code suggestions grow from config snippets to targeted
single-file changes — showing the exact function, the change needed, and why.

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

**Code suggestion depth at M3 — targeted single-file changes:**

For each known fix pattern, the skill shows the exact location in the source
file and the change to make.

*Audio glitch — add pre-roll silent buffer in spa.alsa:*
```c
/* spa/plugins/alsa/alsa-pcm.c — in alsa_pcm_start() */

/* Before: start DMA immediately */
snd_pcm_start(state->hndl);

/* After: write one period of silence before starting */
spa_zero(state->silence_buf);
snd_pcm_writei(state->hndl, state->silence_buf, state->period_frames);
snd_pcm_start(state->hndl);
```

*Startup race — add device-ready wait in WirePlumber:*
```lua
-- /etc/wireplumber/main.lua.d/51-device-wait.lua
-- Wait for ALSA card to appear before activating nodes
rule = {
  matches = { { { "device.name", "matches", "alsa_card.*" } } },
  apply_properties = {
    ["device.disabled"] = false,
  },
}
table.insert(alsa_monitor.rules, rule)
```

**Deliverables:**
- Section 3 auto-populated: component, sub-component, source path, change type
- Section 6 includes single-file code change suggestions with file path,
  function name, before/after diff, and rationale
- `--show-components` flag
- `references/component_map.md` expanded: full source-file mapping,
  AudioReach graph chain, SPA plugin registry, WirePlumber Lua locations

**Done when:** Code suggestions point to the correct file and function for
8/10 test cases; an engineer can apply the suggestion without additional research.

---

## M4 · Weeks 7–8 · Platform Intelligence and Platform-Conditional Code Changes

### What gets built

The skill learns platform capabilities and QLI 1.x vs 2.x differences.
Code suggestions become platform-conditional — the right fix for IQ9075
(QLI 2.x, PAL path) is different from the right fix for IQ615 (QLI 1.x,
spa.alsa direct path).

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

**Code suggestion depth at M4 — platform-conditional changes:**

The skill generates the correct fix for the detected platform, not a generic one.

*Audio glitch fix — QLI 1.x (spa.alsa direct path):*
```c
/* spa/plugins/alsa/alsa-pcm.c */
/* Fix: add pre-roll silent buffer before DMA start */
memset(state->buffer, 0, state->period_size);
snd_pcm_writei(state->hndl, state->buffer, state->period_frames);
snd_pcm_start(state->hndl);
```

*Audio glitch fix — QLI 2.x (PAL path, different root cause):*
```cpp
/* PAL/src/Pal.cpp — in pal_stream_start() */
/* Fix: apply mute before codec ramp to suppress pop */
pal_stream_set_mute(stream_handle, true);
status = rm->getAudioRoute(stream_handle);
/* Allow codec ramp to settle (platform-specific delay) */
usleep(IQ9075_CODEC_RAMP_US);
pal_stream_set_mute(stream_handle, false);
```

**Deliverables:**
- Auto-detect platform from issue text; `--platform` flag for override
- Platform constraint warnings in Section 4
- Platform context block in every proposal
- Code suggestions in Section 6 are platform-specific — different fix shown
  for QLI 1.x vs QLI 2.x for the same symptom
- `--list-platforms` flag
- `references/platform_matrix.md` expanded: known issue patterns per platform,
  firmware dependency notes, Config 1 vs Config 2 switching procedure

**Done when:** Platform auto-detected in 9/10 cases; code suggestions are
correct for the detected platform; QLI 1.x and QLI 2.x fixes are distinct
where the root cause differs.

---

### Month 2 — Capability checkpoint

- Identifies exact components and source files for any issue
- Applies platform constraints and QLI 1.x vs 2.x differences automatically
- Suggests targeted single-file code changes with file path, function, and diff
- Generates platform-specific fixes — different code for QLI 1.x vs QLI 2.x

---

---

# MONTH 3 — Complex Issues and Multi-File Fix Delivery

**Goal:** The skill handles issues where the root cause is unknown. It ranks
hypotheses, generates a platform-specific diagnostic runbook, and — once the
root cause is confirmed — produces multi-file code change suggestions covering
all affected files with full context and rationale.

---

## M5 · Weeks 9–10 · Root Cause Analysis, Diagnostics, and Hypothesis-Driven Code Suggestions

### What gets built

For issues where the root cause is unknown (Type 10) or multi-causal
(Types 5, 4, 6), the skill generates ranked hypotheses and a diagnostic
runbook. Each hypothesis comes with the code change that would fix it —
so once the engineer confirms the root cause, the fix is already there.

**Root-cause hypothesis generation:**

For each issue type + platform, the skill produces:
- How the relevant part of the stack works (factual)
- AudioReach graph construction chain where relevant
- 2–4 ranked hypotheses, each labelled *(hypothesis)*
- Per-hypothesis: the diagnostic command to confirm it, and the code change to fix it

*Example — audio glitch on IQ9075 (QLI 2.x):*
```
5. Architecture Notes

  Stack path:
    PipeWire node → pipewire-pal-plugin → PAL::StreamPCM::open()
    → ResourceManager::getAudioRoute() → AGM::sessionOpen()
    → ADSP graph (SPF) → Codec / I2S

  Hypotheses (ranked):

  1. [HIGH] PAL stream open triggers codec pop without mute ramp
     Confirm: logcat -s PAL:V | grep 'setVolume\|mute'
     Fix:
       /* PAL/src/Pal.cpp — pal_stream_start() */
       pal_stream_set_mute(stream_handle, true);
       status = rm->getAudioRoute(stream_handle);
       usleep(IQ9075_CODEC_RAMP_US);   /* ~10ms ramp */
       pal_stream_set_mute(stream_handle, false);

  2. [MED] SPA/ALSA underrun during first buffer cycle
     Confirm: PIPEWIRE_DEBUG=3 pw-play x.wav | grep xrun
     Fix:
       /* spa/plugins/alsa/alsa-pcm.c — alsa_pcm_start() */
       memset(state->buffer, 0, state->period_size);
       snd_pcm_writei(state->hndl, state->buffer, state->period_frames);
       snd_pcm_start(state->hndl);

  3. [LOW] WirePlumber activates node before ADSP graph is stable
     Confirm: journalctl -u wireplumber | grep 'activat'
     Fix:
       -- /etc/wireplumber/main.lua.d/52-pal-ready.lua
       -- Delay node activation until PAL signals ready
       alsa_monitor.properties["alsa.reserve-device"] = true
```

**Diagnostic runbook — platform-specific, copy-paste ready:**
```
  Step 1: $ PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i 'underrun|xrun'
          Look for: xrun count > 0  →  points to hypothesis 2

  Step 2: $ pw-top
          Look for: xrun counter in first 500ms  →  confirms hypothesis 2

  Step 3: $ journalctl -u wireplumber --since "1 min ago" | grep 'activat'
          Look for: activation before PAL open  →  points to hypothesis 3

  Step 4: $ logcat -s PAL:V AGM:V | grep 'setVolume\|mute'  [QLI 2.x only]
          Look for: volume set before mute ramp  →  confirms hypothesis 1
```

**Deliverables:**
- Section 5: ranked hypotheses, each with confirm command + fix code snippet
- Section 7: diagnostic runbook (platform-specific commands, ordered by probability)
- `references/platform_matrix.md` — known issue patterns expanded with
  per-platform root causes, diagnostic steps, and fix references

**Done when:** Hypothesis #1 is correct in 6/10 real cases; each hypothesis
includes a code fix that resolves the issue when the hypothesis is confirmed.

---

## M6 · Weeks 11–12 · Full Multi-File Fix Delivery

### What gets built

Once the root cause is known (either from M5 diagnostics or from the user
confirming a hypothesis), the skill produces a complete, reviewable set of
code changes across all affected files — not just the primary fix but also
the guard conditions, test additions, and documentation updates.

**Code suggestion depth at M6 — complete multi-file changes:**

*Example — audio glitch fix confirmed as hypothesis 1 (PAL mute ramp):*

```
6. Code Changes

  File 1: PAL/src/Pal.cpp
  ─────────────────────────────────────────────────────────────────
  Function: pal_stream_start()
  Change: Add mute ramp around codec enable

  - status = rm->getAudioRoute(stream_handle);
  + pal_stream_set_mute(stream_handle, true);
  + status = rm->getAudioRoute(stream_handle);
  + if (status == PAL_EOK) {
  +     usleep(platform_get_codec_ramp_us(stream_handle));
  +     pal_stream_set_mute(stream_handle, false);
  + }

  File 2: PAL/inc/PalDefs.h
  ─────────────────────────────────────────────────────────────────
  Change: Add platform-specific ramp constant

  + #define IQ9075_CODEC_RAMP_US   10000   /* 10ms — from codec datasheet */
  + #define QCS6490_CODEC_RAMP_US  8000    /* 8ms */

  File 3: PAL/src/ResourceManager.cpp
  ─────────────────────────────────────────────────────────────────
  Function: platform_get_codec_ramp_us()
  Change: New helper — returns platform-specific ramp delay

  + uint32_t ResourceManager::platform_get_codec_ramp_us(pal_stream_handle_t *sh) {
  +     switch (rm->getPlatformId()) {
  +         case PLATFORM_IQ9075:  return IQ9075_CODEC_RAMP_US;
  +         case PLATFORM_QCS6490: return QCS6490_CODEC_RAMP_US;
  +         default:               return 0;
  +     }
  + }

  File 4: test/pal_stream_test.cpp
  ─────────────────────────────────────────────────────────────────
  Change: Add regression test for mute ramp on stream start

  + TEST(PalStreamTest, NoPopOnStreamStart) {
  +     auto stream = pal_stream_open(PAL_STREAM_PCM_OFFLOAD, ...);
  +     EXPECT_CALL(mock_codec, setMute(true)).Times(1);
  +     EXPECT_CALL(mock_codec, setMute(false)).Times(1);
  +     pal_stream_start(stream);
  + }
```

**Deliverables:**
- Section 6 produces complete multi-file diff with: file path, function,
  before/after diff, rationale for each change
- Section 7 includes regression test additions alongside functional tests
- `--confirmed-hypothesis N` flag: skip diagnostic section, go straight to
  full fix for hypothesis N
- `--fix-only` flag: output only the code changes, no proposal boilerplate

**Done when:** Multi-file fix is complete and self-consistent; an engineer
can apply it directly without additional research; includes test additions.

---

### Month 3 — Capability checkpoint

- Ranks root-cause hypotheses with confirm commands and per-hypothesis fix code
- Generates platform-specific diagnostic runbook
- Produces complete multi-file code changes once root cause is confirmed
- Includes regression test additions alongside every fix

---

---

# MONTH 4 — New Feature Design and Implementation Guidance

**Goal:** The skill handles new feature requests. It accepts architecture
input, produces a full design proposal, and generates implementation-ready
code scaffolding — API stubs, data structure definitions, integration hooks,
and a complete implementation plan with effort estimates and dependencies.

---

## M7 · Weeks 13–14 · New Feature Design and Code Scaffolding

### What gets built

For new feature requests (Types 1, 2, 3, 8, 9), the skill accepts architecture
input and produces a design proposal with code scaffolding — the skeleton of
the implementation that an engineer fills in, not a complete implementation.

Without architecture input, the skill asks structured questions rather than
guessing.

**Architecture input modes:**

| Mode | How to provide |
|---|---|
| `--arch-file FILE` | Markdown or text file describing the existing architecture |
| `--component-desc TEXT` | Free-text description of the component to be modified |
| `--data-flow TEXT` | Description of the data flow to be changed |
| Conversational | Skill asks structured questions about the architecture |

**Code suggestion depth at M7 — scaffolding and API stubs:**

*Example — new feature: always-on audio on IQ9075:*
```
6. Code Scaffolding

  File 1: PAL/inc/PalDefs.h
  ─────────────────────────────────────────────────────────────────
  + typedef enum {
  +     PAL_STREAM_ALWAYS_ON_CAPTURE = 0x100,  /* new stream type */
  + } pal_stream_type_ext_t;

  File 2: PAL/src/StreamAlwaysOn.cpp  [new file]
  ─────────────────────────────────────────────────────────────────
  + class StreamAlwaysOn : public Stream {
  + public:
  +     int32_t open(struct pal_stream_attributes *attr) override;
  +     int32_t start() override;
  +     int32_t stop() override;
  +     int32_t close() override;
  +     /* TODO: implement ADSP island mode handshake */
  + private:
  +     bool adsp_island_active_ = false;
  + };

  File 3: src/modules/module-pal-source.c  (pipewire-pal-plugin)
  ─────────────────────────────────────────────────────────────────
  + /* TODO: add always-on source node type */
  + static const struct spa_dict_item always_on_props[] = {
  +     { PW_KEY_NODE_NAME,        "pal.always_on.source" },
  +     { PW_KEY_MEDIA_CLASS,      "Audio/Source/AlwaysOn" },
  +     { "pal.stream.type",       "always_on_capture" },
  + };

  File 4: /etc/wireplumber/main.lua.d/53-always-on.lua
  ─────────────────────────────────────────────────────────────────
  + -- TODO: policy to keep always-on source active and suspend HLOS nodes
  + alsa_monitor.rules = alsa_monitor.rules or {}
  + table.insert(alsa_monitor.rules, {
  +     matches = { { { "node.name", "matches", "pal.always_on.*" } } },
  +     apply_properties = { ["node.autoconnect"] = false },
  + })
```

**Deliverables:**
- Section 5: architecture notes — how the existing stack works, where the
  new feature fits, interface points, constraints
- Section 6: code scaffolding — new files, new types, API stubs, integration
  hooks, all marked `TODO` where implementation is needed
- Section 9: risks — API compatibility, performance impact, platform
  availability, firmware dependency
- `--arch-file`, `--component-desc`, `--data-flow` flags

**Done when:** Scaffolding compiles (or is syntactically valid); an engineer
can fill in the TODOs without needing to understand the full codebase from scratch.

---

## M8 · Weeks 15–16 · Full New Feature Implementation Guidance

### What gets built

The skill produces end-to-end implementation guidance for a new feature —
complete code changes (not just scaffolding), a step-by-step integration
plan with effort estimates and dependencies, a full test plan with exact
commands, and documentation tasks.

**Code suggestion depth at M8 — complete implementation:**

*Example — always-on audio, full implementation:*
```
6. Implementation

  Step  File                          Change                              Effort  Depends on
  ──────────────────────────────────────────────────────────────────────────────────────────
  1     PAL/inc/PalDefs.h             Add PAL_STREAM_ALWAYS_ON_CAPTURE    S       —
  2     PAL/src/StreamAlwaysOn.cpp    Implement StreamAlwaysOn class       L       1
  3     PAL/src/ResourceManager.cpp   Add always-on usecase routing        M       2
  4     resourcemanager.xml           Add always-on usecase definition     S       2
  5     module-pal-source.c           Add always-on source node type       M       3
  6     53-always-on.lua              Add WirePlumber suspend policy       M       5
  7     test/always_on_test.cpp       Unit + integration tests             M       2,5
  8     docs/always-on-audio.md       New documentation section            S       7

  Full code for Step 2 (StreamAlwaysOn::start):
  ─────────────────────────────────────────────
  int32_t StreamAlwaysOn::start() {
      /* 1. Request ADSP island mode via AGM */
      status = agm_session_set_config(session_id_,
                   AGM_SESSION_CONFIG_ISLAND_MODE, true);
      if (status != AGM_EOK) return PAL_ERR_ADSP_ISLAND;

      /* 2. Open capture graph on ADSP */
      status = agm_session_start(session_id_);
      if (status != AGM_EOK) return PAL_ERR_GRAPH_START;

      adsp_island_active_ = true;
      PAL_DBG(LOG_TAG, "Always-on capture started, ADSP island active");
      return PAL_EOK;
  }
```

**QGenie skill packaging (completed in M8):**
- `SKILL.md` updated with all capabilities and trigger phrases
- `agents/openai.yaml` updated
- Conversational mode handles all 8 milestone capabilities
- Installable: `Install the pipewire-enhancement skill from sauravk-git/saurav-skills`
- README updated with all usage examples and worked examples
- `references/examples.md` — 4 full worked examples:
  1. Audio glitch (IQ9075, QLI 2.x) — complex issue, multi-file fix
  2. SSMD not working (IQ9075) — medium issue, platform-conditional fix
  3. Startup enumeration race — basic issue, config + code fix
  4. Always-on audio (IQ9075) — new feature, full implementation

**Done when:** Implementation guidance is complete and self-consistent;
a senior engineer reviews it and accepts it as a valid starting point
for a sprint without major rework; all 13 enhancement types handled
with real, specific content including code suggestions.

---

### Month 4 — Capability checkpoint

- Accepts architecture input and produces design proposals for new features
- Generates code scaffolding (API stubs, new files, integration hooks)
- Produces complete implementation code for new features with effort estimates
- Handles all 13 enhancement types end-to-end with code change suggestions

---

---

# Capability and Code Suggestion Growth

| Milestone | Capability | Code suggestion depth |
|---|---|---|
| M1 (wk 2) | Classify any issue | None |
| M2 (wk 4) | Diagnose basic issues | Config snippets, known one-liners |
| M3 (wk 6) | Component + source file awareness | Single-file targeted changes with file path and function |
| M4 (wk 8) | Platform intelligence | Platform-conditional fixes — different code for QLI 1.x vs 2.x |
| M5 (wk 10) | Root cause hypotheses + diagnostics | Per-hypothesis fix code alongside confirm command |
| M6 (wk 12) | Full complex issue fix | Complete multi-file diff with test additions |
| M7 (wk 14) | New feature design | Code scaffolding — new files, API stubs, TODOs |
| M8 (wk 16) | New feature implementation | Complete implementation code with integration plan |

---

# Out of Scope

| Item | Reason |
|---|---|
| Automatically applying code changes to the repo | Suggestions only — engineer reviews and applies |
| Orbit / JIRA ticket creation | Future integration |
| Real-time log analysis | Requires log streaming infrastructure |
| Non-Qualcomm PipeWire platforms | Out of domain |
| Automated hardware-in-loop testing | Requires lab infrastructure |
| Compiling or running the suggested code | Suggestions are for review, not auto-execution |

---

# Risks

| Risk | Mitigation |
|---|---|
| Keyword matching too shallow for complex issues | Build test suite at M1; iterate on keyword map each sprint |
| Platform matrix goes stale as new platforms ship | Matrix in a separate `.md` file — updatable in 30 min |
| Code suggestions are wrong or incomplete | Label all suggestions clearly as starting points; engineer reviews before applying |
| Root-cause hypotheses are incorrect | Label all hypotheses; validate with a senior engineer |
| Architecture input quality varies | Skill asks structured clarifying questions when input is insufficient |
| New feature scope creep beyond M8 | M8 produces implementation guidance — actual coding is the engineer's responsibility |
