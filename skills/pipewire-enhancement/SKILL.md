---
name: pipewire-enhancement
description: >
  PipeWire Enhancement Engineer for Qualcomm QLI, AudioReach, PAL, ADSP/DSP,
  WirePlumber, and Yocto-based audio stacks. Accepts a natural-language description
  of an issue and a goal, then produces a complete structured 10-section
  implementation proposal — no template-filling required.
  Use when asked to: analyse a PipeWire enhancement, investigate an audio issue,
  propose a feature for QLI/AudioReach/PAL, improve audio quality, fix a glitch,
  add SSMD/Fluence/compressed-offload support, improve WirePlumber policy, update
  audio documentation, or plan packaging/deployment changes.
  Triggers on: pipewire, wireplumber, pw-record, pw-play, spa.alsa, audioreach,
  pipewire-pal, QLI, SSMD, Fluence, Config 1, Config 2, audio glitch, audio
  routing, audio enhancement, IQ9075, QCS6490, SA8775P, RB3.
---

# PipeWire Enhancement Skill

You are a **PipeWire Enhancement Engineer** specialising in upstream PipeWire,
Qualcomm QLI (1.x / 2.x), PipeWire-PAL, AudioReach, ADSP/DSP integration,
WirePlumber policy, and Yocto-based embedded Linux audio stacks.

---

## How to Use

### Option 1 — Conversational (recommended)

Just run the script and answer two questions:

```bash
python3 scripts/analyze_enhancement.py
```

```
▶ What issue are you seeing?
  Audio glitch and tick at playback start on IQ9075 QLI 2.x

▶ What do you want to build / achieve?
  Eliminate the tick without regressing other audio paths
```

→ Full 10-section proposal printed immediately.

### Option 2 — One-liner

```bash
python3 scripts/analyze_enhancement.py \
    --issue "Audio glitch at playback start on IQ9075 QLI 2.x with pw-play" \
    --goal  "Eliminate the tick without regressing other audio paths"
```

### Option 3 — From a file

```
# my_issue.txt
Audio glitch at playback start on IQ9075 QLI 2.x with pw-play
Eliminate the tick without regressing other audio paths
```

```bash
python3 scripts/analyze_enhancement.py --from-file my_issue.txt
```

### Save to file

```bash
python3 scripts/analyze_enhancement.py \
    --issue "..." --goal "..." \
    --no-color > proposal.md
```

---

## What the Proposal Contains

Every proposal produced from your input covers all 10 sections:

| # | Section | What it gives you |
|---|---|---|
| 1 | **Enhancement Summary** | Plain-English summary of issue + goal |
| 2 | **Classification** | Which of 13 enhancement types apply |
| 3 | **Affected Components** | Component table with change type |
| 4 | **Gap Analysis** | Missing info you need to provide |
| 5 | **Architecture & Design Notes** | Root-cause hypotheses + proposed approach |
| 6 | **Implementation Plan** | Step-by-step task table with effort (S/M/L) |
| 7 | **Test & Validation Plan** | Exact test commands + diagnostic hints |
| 8 | **Documentation Tasks** | Pages/sections to create or update |
| 9 | **Open Questions & Risks** | Risks with mitigations |
| 10 | **Acceptance Criteria** | Measurable completion conditions |

---

## Enhancement Types Detected Automatically

The script detects the type from your issue + goal text — no manual selection needed.

| # | Type | Trigger keywords |
|---|---|---|
| 1 | New PipeWire feature | "new feature", "add support", "implement" |
| 2 | Existing feature enhancement | "improve", "enhance", "better" |
| 3 | Performance improvement | "latency", "cpu", "power", "offload" |
| 4 | Startup / enumeration improvement | "startup", "boot", "missing device" |
| 5 | Audio quality improvement | "glitch", "tick", "pop", "noise", "quality" |
| 6 | Routing or policy enhancement | "routing", "policy", "sink", "source", "ssmd" |
| 7 | Configuration enhancement | "config 1", "config 2", "topology", "lua" |
| 8 | PAL / AudioReach integration | "pal", "audioreach", "adsp", "agm" |
| 9 | API or ABI enhancement | "api", "abi", "interface", "protocol" |
| 10 | Debugging / root-cause investigation | "debug", "rca", "investigate" |
| 11 | Documentation enhancement | "document", "doc", "guide" |
| 12 | Test or validation enhancement | "test", "validate", "ci" |
| 13 | Packaging or deployment enhancement | "package", "yocto", "debian", "rpm" |

---

## Component Layers

| Layer | Key components |
|---|---|
| **Client & Tools** | pw-cli, pw-dump, pw-top, pw-record, pw-play, pw-cat, pw-jack, wpctl, arecord/aplay, GStreamer |
| **PipeWire Core** | Nodes, ports, links, devices, metadata, format negotiation, buffering, scheduling, RT graph |
| **SPA** | spa.alsa, device/node factories, buffer & format handling, ALSA controls, custom SPA plugins |
| **WirePlumber** | Device/node discovery, object linking, default sink/source policy, Lua config, startup ordering |
| **PipeWire-Pulse** | Compatibility layer — compare pw-record/pw-play vs arecord/aplay vs PulseAudio clients |
| **Compressed offload** | spa.alsa compressed path, ALSA compress API, offload scheduling |
| **Qualcomm PAL** | pipewire-pal-plugin → PAL → AudioReach → ADSP/DSP, modem/remoteproc startup |
| **Topology** | Config 1 / Config 2, .bin loading, SSMD, Fluence, always-on audio |
| **Yocto** | pipewire/wireplumber recipes, PACKAGECONFIG, systemd ordering, audio group, D-Bus |
| **Debian/RPM** | debian/ metadata, Debusine APT pipeline, RPM spec, build scripts |

---

## Style Rules (when generating proposals in chat)

- Tables wherever structure helps clarity.
- Speculation labelled: *(hypothesis)* or *(to be confirmed)*.
- No raw log dumps — summarise findings, reference line numbers.
- All version references explicit (e.g. PipeWire 1.2.x, not "latest").
- Respond in the same language as the user's request.

---

## References

- `references/component_map.md` — component→source-file mapping, QLI 1.x vs 2.x
  feature delta, AudioReach graph construction details, SPA plugin registry.
  Read when: mapping a request to specific source files or APIs.

- `references/platform_matrix.md` — per-platform constraints, supported audio
  paths, known issue patterns, firmware dependencies, Config 1/2 availability.
  Read when: request mentions a specific platform or topology.

- `references/examples.md` — three full worked examples (audio glitch, SSMD
  documentation, Config 1 vs Config 2). Read when: user asks for an example
  or the request closely matches one of these patterns.
