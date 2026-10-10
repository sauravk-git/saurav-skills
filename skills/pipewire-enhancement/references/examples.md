# Worked Examples

## Table of Contents
1. Audio glitch at playback start/end (IQ9075, QLI 2.x)
2. Missing SSMD documentation (IQ9075)
3. Config 1 vs Config 2 documentation

---

## 1. Audio Glitch at Playback Start/End

**Input:**
> Audio glitch/tick sound observed at start and end of playback on IQ9075
> with QLI 2.x (PipeWire + PAL + AudioReach). Observed with both pw-play
> and a GStreamer pipeline.

**Classification:** 5 (Audio quality), 10 (Debug), 8 (PAL integration)

**Affected Components:**

| Component | Sub-component | Change |
|---|---|---|
| PipeWire Core | Node state transitions | Investigate |
| SPA | spa.alsa underrun / pre-roll | Investigate / Modify |
| WirePlumber | Node activation sequencing | Investigate |
| pipewire-pal-plugin | Stream open/close lifecycle | Investigate / Modify |
| PAL | usecase_mgr start/stop ramp | Investigate |
| AudioReach / ADSP | DSP graph ramp, codec pop suppression | Investigate |

**Gap Analysis:**
- PipeWire and WirePlumber versions not provided
- Whether glitch is in both channels or one not stated
- ADSP firmware version required
- `pw-top` graph state logs and ADSP logcat around playback start/end needed

**Architecture Notes:** *(hypothesis)*
The tick is most likely caused by one of:
1. SPA/ALSA underrun during first buffer cycle before DSP graph ramps
2. PAL stream open triggering codec pop without software mute ramp
3. WirePlumber activating node before ADSP graph is stable

**Implementation Plan:**

| Step | Area | Task | Effort |
|---|---|---|---|
| 1 | SPA | Add pre-roll silent buffer in spa.alsa | M |
| 2 | PAL | Enable codec pop-suppression via PAL stream attributes | S |
| 3 | WirePlumber | Add activation delay hook tied to PAL ready event | M |
| 4 | Test | Measure glitch with/without each fix on IQ9075 | S |

**Acceptance Criteria:**
- No audible glitch on pw-play with 48kHz/16-bit stereo WAV on IQ9075
- No regression on GStreamer pipeline
- pw-top shows no underruns during first 500ms of playback

---

## 2. Missing SSMD Documentation

**Input:**
> Missing SSMD (Single Stream Multi Device) playback commands in IQ9075
> Audio Documentation.

**Classification:** 11 (Documentation), 7 (Configuration)

**Affected Components:**

| Component | Sub-component | Change |
|---|---|---|
| AudioReach | SSMD topology configuration | Doc |
| PAL | Multi-device usecase definition | Doc |
| PipeWire | Node/port routing to multiple sinks | Doc |
| IQ9075 Audio Documentation | New SSMD section | New |

**Gap Analysis:**
- Which output device combinations are supported for SSMD on IQ9075?
- Is SSMD enabled in Config 1 or Config 2 only?
- Platform-specific limitations (max simultaneous devices)?

**Documentation Tasks:**
1. New section: "SSMD (Single Stream Multi Device) Playback"
2. Prerequisites: QLI 2.x, Config 2 topology, PAL multi-device usecase
3. Command examples: pw-play with multiple sinks, wpctl routing
4. Topology diagram: PAL → AudioReach SSMD graph
5. Troubleshooting: common SSMD setup errors

**Acceptance Criteria:**
- Documentation section published in IQ9075 Audio Guide
- At least 3 working command examples verified on hardware
- Topology diagram reviewed by AudioReach team

---

## 3. Config 1 vs Config 2 Documentation

**Input:**
> Create a dedicated Audio documentation section explaining Config 1 vs Config 2.

**Classification:** 11 (Documentation), 7 (Configuration)

**Affected Components:**

| Component | Sub-component | Change |
|---|---|---|
| AudioReach | Config 1 / Config 2 topology definitions | Doc |
| PAL | Usecase mapping per config | Doc |
| DragonWing Docs | New dedicated section | New |

**Architecture Notes:**

**Config 1** — Software-decoded audio via HLOS:
- Lower DSP involvement
- Suitable for standard stereo playback/capture
- Simpler topology, easier to customise
- Supported on all QLI platforms

**Config 2** — Hardware-offloaded audio via ADSP:
- Lower CPU utilisation, higher power efficiency
- Required for: Fluence, SSMD, always-on audio, BT offload
- More complex topology (.bin loading required)
- QLI 2.x only

**Documentation Tasks:**
1. New section: "Audio Configuration: Config 1 vs Config 2"
2. Comparison table (features, power, complexity, use-cases)
3. When to choose each config
4. Migration guide: Config 1 → Config 2
5. Platform availability table

**Acceptance Criteria:**
- Section published and linked from main audio guide
- Comparison table reviewed by PAL and AudioReach teams
- Migration guide tested on at least one QLI 2.x platform
