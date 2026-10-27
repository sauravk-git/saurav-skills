# PipeWire Enhancement Skill — 5-Month Roadmap

---

## Overview

Build a PipeWire Enhancement Engineering assistant for Qualcomm QLI /
AudioReach / PAL stacks that grows in capability across five months.

The skill covers both audio backend configurations:

- **Config 1** — ASoC / ALSA-based PipeWire. Audio runs on the HLOS via the
  SPA ALSA plugin (spa.alsa). Requires ASoC topology file, UCM2 files, and
  WirePlumber ALSA monitor. Supported on all QLI platforms.
- **Config 2** — AudioReach / PAL-based PipeWire. Audio offloaded to the ADSP
  via pipewire-pal-plugin → PAL → AudioReach → AGM. Requires ADSP firmware,
  remoteproc, AGM driver, PAL resourcemanager.xml, and pipewire-pal-plugin.
  QLI 2.x only.

The progression follows the natural order of engineering work:

- **Month 1** — Bring PipeWire up on Config 1 (ASoC/ALSA): guided prerequisite
  checklist, bringup sequence, common bringup issue fixes. Issue classifier.
- **Month 2** — Bring PipeWire up on Config 2 (AudioReach/PAL): guided
  prerequisite checklist, bringup sequence, common bringup issue fixes.
  Basic issue diagnosis with config-level fix suggestions.
- **Month 3** — Component depth: identify exact source files per config;
  platform constraints; targeted single-file code changes.
- **Month 4** — Complex issues: root cause hypotheses, diagnostic runbooks,
  multi-file code change suggestions.
- **Month 5** — New features: architecture input, design proposals,
  implementation-ready code scaffolding and full implementation guidance.

Code change suggestions are present from Month 1 and grow in depth at every
milestone.

---

## Milestone Overview

| # | Weeks | Capability | Code suggestion depth |
|---|---|---|---|
| M1 | 1–2 | Config 1 bringup (ASoC/ALSA); issue classifier | Bringup fix commands; config snippets |
| M2 | 3–5 | Config 2 bringup (AudioReach/PAL) | Bringup fix commands; PAL/AGM config snippets |
| M3 | 6–7 | Basic issue diagnosis — both configs | Config-specific snippets; known one-liners per config |
| M4 | 8–9 | Component and source file awareness | Targeted single-file code changes |
| M5 | 10–11 | Platform intelligence and QLI stack reasoning | Platform-conditional code changes |
| M6 | 12–13 | Complex issue — root cause analysis and diagnostics | Per-hypothesis fix code + diagnostic runbook |
| M7 | 14–15 | Complex issue — full multi-file fix delivery | Complete reviewable code changes with test additions |
| M8 | 16–17 | New feature — design and code scaffolding | API stubs, new file skeletons, integration hooks |
| M9 | 18–19 | New feature — full implementation guidance | Complete implementation code with integration plan |
| M10 | 20 | QGenie packaging and skill hardening | — |

---

---

# MONTH 1 — Config 1 Bringup and Issue Classification

**Goal:** Get PipeWire working on Config 1 (ASoC/ALSA). The skill asks for
every prerequisite, checks each one in order, identifies what is missing, and
provides the exact fix. Alongside this, the issue classifier is built — the
foundation every later milestone depends on.

Config 1 bringup is handled first because it is the simpler stack (no ADSP,
no remoteproc, no PAL) and is supported on all QLI platforms. Getting it
right establishes the baseline before tackling Config 2.

---

## M1 · Weeks 1–2 · Config 1 Bringup and Issue Classifier

### What gets built

**1. Config 1 guided bringup**

The skill walks through the Config 1 prerequisite chain in order. For each
item it checks whether it is satisfied and, if not, provides the exact
command to fix it.

*Prerequisites the skill checks (in order):*

| # | Prerequisite | Check command | Common fix |
|---|---|---|---|
| 1 | ASoC topology file loaded by kernel | `dmesg \| grep -i tplg` | Copy correct `.bin` to `/lib/firmware/qcom/` |
| 2 | ALSA sound card visible | `aplay -l` | Reload ASoC driver: `modprobe -r snd_soc_<plat> && modprobe snd_soc_<plat>` |
| 3 | UCM2 directory present and named correctly | `ls /usr/share/alsa/ucm2/` | Rename or symlink to match `cat /proc/asound/card*/id` |
| 4 | UCM2 verbs load without error | `alsaucm -c <card> list _verbs` | Fix UCM2 syntax errors in `HiFi.conf` |
| 5 | PipeWire service running | `systemctl --user status pipewire` | `systemctl --user enable --now pipewire` |
| 6 | WirePlumber service running | `systemctl --user status wireplumber` | `systemctl --user enable --now wireplumber` |
| 7 | WirePlumber ALSA monitor enabled | `grep -r alsa /etc/wireplumber/` | Enable ALSA monitor in `wireplumber.conf` |
| 8 | PipeWire sees ALSA nodes | `pw-cli ls Node \| grep alsa` | Restart WirePlumber after card confirmed present |
| 9 | User in audio group | `id \| grep audio` | `sudo usermod -aG audio $USER` then re-login |
| 10 | Basic playback works | `pw-play /usr/share/sounds/alsa/Front_Left.wav` | Check steps 1–9 |

*Platform-specific topology filenames known to the skill:*

| Platform | Topology file (typical) |
|---|---|
| IQ615 | `sm6115-wcd937x-snd-card-tplg.bin` |
| IQ8275-EVK | `sm8275-<codec>-snd-card-tplg.bin` |
| IQ9075 | `sun-<codec>-snd-card-tplg.bin` |
| RB3-Gen2 | `qcs6490-rb3gen2-<codec>-tplg.bin` |
| QCS6490 | `qcs6490-<codec>-snd-card-tplg.bin` |

*Config-level fix suggestions for common Config 1 bringup failures:*

```bash
# UCM2 directory name mismatch — most common Config 1 bringup failure
CARD=$(cat /proc/asound/card0/id)
ls /usr/share/alsa/ucm2/ | grep -i "$CARD"
# If no match — create symlink:
sudo ln -s /usr/share/alsa/ucm2/<existing-dir> /usr/share/alsa/ucm2/$CARD
systemctl --user restart wireplumber
```

```ini
# WirePlumber not starting before ALSA card is ready
# /etc/systemd/system/wireplumber.service.d/override.conf
[Unit]
After=sound.target
Wants=sound.target
```

**2. Issue classifier**

A classifier that reads a plain-English issue description and maps it to one
or more of 13 enhancement types. Every subsequent milestone depends on this.

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
- `--list-types` and `--verbose` flags
- `--bringup --config 1 --platform <name>` — Config 1 guided bringup mode;
  walks through the 10-step checklist; provides fix for each missing item
- `references/enhancement_types.md` — type definitions, keyword lists
- `references/component_map.md` — Config 1 architecture, component source
  paths, bringup checklist
- `references/platform_matrix.md` — per-platform topology filenames,
  Config 1 bringup issue patterns
- Test suite: 15 real issues, expected types, pass/fail report

**Done when:** Config 1 bringup flow correctly identifies missing prerequisites
on at least 3 platforms and provides working fix commands; classifier correctly
classifies 13/15 test issues.

---

### Month 1 — Capability checkpoint

- Guides Config 1 (ASoC/ALSA) bringup end-to-end with prerequisite checklist
- Identifies missing prerequisites and provides exact fix commands
- Knows platform-specific topology filenames and UCM2 requirements
- Classifies any issue into the right type(s) in under 1 second

---

---

# MONTH 2 — Config 2 Bringup and Basic Issue Diagnosis

**Goal:** Get PipeWire working on Config 2 (AudioReach/PAL). Config 2 has
a deeper prerequisite chain than Config 1 — ADSP firmware, remoteproc,
AGM driver, PAL config, and pipewire-pal-plugin all need to be in place
before audio works. The skill handles each layer in order and knows the
failure mode at each step. Basic issue diagnosis is also added this month.

---

## M2 · Weeks 3–5 · Config 2 Bringup (AudioReach / PAL)

### What gets built

The skill walks through the Config 2 prerequisite chain in order, layer by
layer from firmware up to PipeWire. Each layer has distinct failure modes
and the skill knows the fix for each.

*Prerequisites the skill checks (in order):*

| # | Layer | Prerequisite | Check command | Common fix |
|---|---|---|---|---|
| 1 | Firmware | ADSP firmware present | `ls /lib/firmware/qcom/adsp*` | Copy firmware from BSP package |
| 2 | Firmware | AudioReach topology present | `ls /lib/firmware/qcom/*tplg*` | Copy topology `.bin` from BSP |
| 3 | remoteproc | ADSP in `running` state | `cat /sys/class/remoteproc/remoteproc*/state` | `echo start > /sys/class/remoteproc/remoteproc<N>/state` |
| 4 | Kernel | AGM driver loaded | `lsmod \| grep agm` | `modprobe agm` or rebuild kernel with `CONFIG_SND_SOC_MSM_QDSP6_AGM=m` |
| 5 | PAL | `resourcemanager.xml` present | `ls /etc/pal/resourcemanager.xml` | Copy from BSP or platform package |
| 6 | PAL | `resourcemanager.xml` valid XML | `xmllint --noout /etc/pal/resourcemanager.xml` | Fix XML syntax errors |
| 7 | PAL | PAL library present | `ldconfig -p \| grep libpal` | Install `libpal` package |
| 8 | pipewire-pal-plugin | Plugin installed | `ls /usr/lib/pipewire-*/libpipewire-module-pal*.so` | Install `pipewire-pal-plugin` package |
| 9 | pipewire-pal-plugin | Plugin listed in `pipewire.conf` | `grep -r pal /etc/pipewire/` | Add PAL module to `pipewire.conf.d/` |
| 10 | WirePlumber | PAL monitor enabled | `wpctl status` shows PAL devices | Enable PAL monitor in WirePlumber config |
| 11 | PipeWire | PAL nodes visible | `pw-cli ls Node \| grep pal` | Restart PipeWire and WirePlumber |
| 12 | End-to-end | Basic playback works | `pw-play /usr/share/sounds/alsa/Front_Left.wav` | Check PAL log: `logcat -s PAL:V AGM:V` |

*Platform-specific firmware filenames known to the skill:*

| Platform | ADSP firmware | AudioReach topology |
|---|---|---|
| IQ9075 | `adsp.mbn` | `sun-adsp-tplg.bin` |
| QCS6490 | `adsp.mbn` | `qcs6490-adsp-tplg.bin` |
| SA8775P | `adsp.mbn` | `sa8775p-adsp-tplg.bin` |
| IQ8275-EVK | `adsp.mbn` | `sm8275-adsp-tplg.bin` |
| RB3-Gen2 | `adsp.mbn` | `qcs6490-rb3gen2-adsp-tplg.bin` |

*Config-level fix suggestions for common Config 2 bringup failures:*

```bash
# remoteproc not starting — most common Config 2 bringup failure
dmesg | grep -i "remoteproc\|adsp\|firmware" | tail -20
# Check firmware path the driver expects:
cat /sys/class/remoteproc/remoteproc<N>/firmware
# Copy firmware to expected path, then:
echo start > /sys/class/remoteproc/remoteproc<N>/state
```

```bash
# PAL nodes not appearing in PipeWire
# Check pipewire.conf has PAL module:
grep -r "pal" /etc/pipewire/ /usr/share/pipewire/
# If missing — add:
cat > /etc/pipewire/pipewire.conf.d/99-pal.conf << 'CONF'
context.modules = [
  { name = libpipewire-module-pal-device }
]
CONF
systemctl --user restart pipewire wireplumber
```

```bash
# PAL stream open failing — check resourcemanager.xml has required usecases
xmllint --noout /etc/pal/resourcemanager.xml && echo "XML valid"
grep -i "PCM_RT_PROXY\|DEEP_BUFFER\|LOW_LATENCY" /etc/pal/resourcemanager.xml
# Check PAL log for specific error:
logcat -s PAL:V AGM:V | grep -i "error\|fail\|open" | head -20
```

**Deliverables:**
- `--bringup --config 2 --platform <name>` — Config 2 guided bringup mode;
  walks through the 12-step checklist layer by layer; provides fix for each
  missing item
- `references/component_map.md` updated with Config 2 component map,
  layer-by-layer architecture, and bringup checklist
- `references/platform_matrix.md` updated with Config 2 bringup issue
  patterns (remoteproc failures, AGM not loading, PAL stream open errors,
  pipewire-pal-plugin not appearing)

**Done when:** Config 2 bringup flow correctly identifies missing prerequisites
on at least 3 QLI 2.x platforms and provides working fix commands for each
failure mode.

---

## M3 · Weeks 6–7 · Basic Issue Diagnosis with Config-Level Fix Suggestions

### What gets built

Extend the classifier into a full diagnosis tool for basic, well-known issue
types. Produces a structured 10-section document. Adds config-level fix
suggestions — the first thing to try before any code change.

**The 10-section proposal structure:**

| # | Section | Content at this stage |
|---|---|---|
| 1 | Summary | Plain-English restatement of issue + goal |
| 2 | Classification | Matched types from M1 |
| 3 | Affected Components | Placeholder — filled in M4 |
| 4 | Gap Analysis | Missing info: config, platform, version, logs |
| 5 | Architecture Notes | Known pattern for this issue type and config |
| 6 | Implementation Plan | Task list + config-level fix suggestions |
| 7 | Test & Validation Plan | Standard test cases for this issue type |
| 8 | Documentation Tasks | What docs to update based on type |
| 9 | Open Questions & Risks | Standard risks for this issue type |
| 10 | Acceptance Criteria | Measurable done conditions |

**Config-level fix suggestions — examples:**

*Config 1 — audio glitch, try quantum tuning first:*
```bash
# /etc/pipewire/pipewire.conf.d/99-quantum.conf
context.properties = {
    default.clock.quantum     = 1024
    default.clock.min-quantum = 512
}
```

*Config 2 — topology not loading:*
```bash
ls -lh /lib/firmware/qcom/*tplg*
logcat -s PAL:V | grep -i 'topology\|bin\|load'
```

*Both configs — wrong default sink:*
```bash
wpctl set-default $(wpctl status | grep "IQ9075" | awk '{print $2}' | tr -d '.')
```

*Both configs — WirePlumber startup race:*
```ini
# /etc/systemd/system/wireplumber.service.d/override.conf
[Unit]
After=sound.target
Wants=sound.target
```

**Issue types with real content at M3:**
- Type 4: Startup / enumeration (both configs)
- Type 5: Audio quality — glitch, tick, pop (both configs)
- Type 6: Routing / policy (both configs)
- Type 7: Configuration — topology, UCM2, PAL config (both configs)
- Type 10: Debugging / RCA (both configs)

**Deliverables:**
- `analyze_enhancement.py` — extends `classify.py`
- Conversational mode, `--from-file`, `--no-color`, `--output markdown`
- Config-aware fix suggestions: skill asks which config is running and
  tailors suggestions accordingly

**Done when:** Output for Types 4, 5, 6, 7, 10 includes at least one
actionable config-specific fix suggestion; proposal covers all 10 sections.

---

### Month 2 — Capability checkpoint

- Guides Config 2 (AudioReach/PAL) bringup end-to-end, layer by layer
- Knows firmware, remoteproc, AGM, PAL, and pipewire-pal-plugin failure modes
- Produces structured 10-section diagnosis for common issue types
- Suggests config-specific fix snippets for Types 4, 5, 6, 7, 10

---

---

# MONTH 3 — Component Depth and Targeted Code Changes

**Goal:** The skill identifies the exact components and source files involved
for both Config 1 and Config 2 — recognising that the same symptom has a
different root cause and different fix depending on which config is running.
Applies platform constraints and suggests targeted single-file code changes.

---

## M4 · Weeks 8–9 · Component Awareness and Single-File Code Suggestions

### What gets built

Section 3 (Affected Components) goes from a placeholder to a precise table
with source file paths. Code suggestions grow from config snippets to targeted
single-file changes — exact file, function, before/after diff, rationale.

**Component map — Config 1 vs Config 2 for the same symptom:**

| Symptom | Config 1 components | Config 2 components |
|---|---|---|
| Glitch / tick / pop | `spa/plugins/alsa/alsa-pcm.c` (pre-roll), `alsa-sink.c` (underrun) | `Pal.cpp` (mute ramp), `module-pal-sink.c` (stream lifecycle) |
| Device not found | `modules/module-device-activation.c`, `wireplumber.conf` | `ResourceManager.cpp`, remoteproc state |
| Latency / performance | `src/pipewire/impl-node.c` (quantum), `alsa-pcm.c` (period size) | `src/pipewire/impl-node.c`, `StreamPCM.cpp` (ADSP buffer) |
| Routing / policy | `modules/module-default-nodes.c`, WirePlumber Lua | `modules/module-default-nodes.c`, WirePlumber Lua |
| Config / topology | `/usr/share/alsa/ucm2/`, ASoC topology `.bin` | `/etc/pal/resourcemanager.xml`, AudioReach topology `.bin` |

**Single-file code suggestion examples:**

*Config 1 — audio glitch, add pre-roll buffer:*
```c
/* spa/plugins/alsa/alsa-pcm.c — alsa_pcm_start() */
- snd_pcm_start(state->hndl);
+ spa_zero(state->silence_buf);
+ snd_pcm_writei(state->hndl, state->silence_buf, state->period_frames);
+ snd_pcm_start(state->hndl);
```

*Config 2 — audio glitch, add PAL mute ramp:*
```cpp
/* PAL/src/Pal.cpp — pal_stream_start() */
- status = rm->getAudioRoute(stream_handle);
+ pal_stream_set_mute(stream_handle, true);
+ status = rm->getAudioRoute(stream_handle);
+ usleep(IQ9075_CODEC_RAMP_US);
+ pal_stream_set_mute(stream_handle, false);
```

*Config 1 — WirePlumber startup race:*
```lua
-- /etc/wireplumber/main.lua.d/51-device-wait.lua
rule = {
  matches = { { { "device.name", "matches", "alsa_card.*" } } },
  apply_properties = { ["device.disabled"] = false },
}
table.insert(alsa_monitor.rules, rule)
```

**Deliverables:**
- Section 3 auto-populated: component, sub-component, source path, change type
- Section 6 includes single-file code change suggestions with file path,
  function, before/after diff, and rationale
- Config-aware: different components and code shown for Config 1 vs Config 2
- `--show-components` flag

**Done when:** Code suggestions point to the correct file and function for
8/10 test cases; Config 1 and Config 2 fixes are distinct where root cause differs.

---

## M5 · Weeks 10–11 · Platform Intelligence and Platform-Conditional Code Changes

### What gets built

The skill learns platform capabilities and QLI 1.x vs 2.x differences.
Code suggestions become platform-conditional — the right fix for IQ9075
(QLI 2.x, Config 2) is different from IQ615 (QLI 1.x, Config 1 only).

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
| Config 1 (ASoC/ALSA) | ✓ | ✓ |
| Config 2 (AudioReach/PAL) | ✗ | ✓ |
| ADSP audio offload | ✗ | ✓ |
| SSMD | ✗ | ✓ |
| Fluence | ✗ | ✓ |
| Always-on audio | ✗ | ✓ |
| BT offload | ✗ | ✓ |
| Modem audio | ✗ | ✓ |
| WirePlumber | 0.4.x | 0.5.x |
| PipeWire | 0.3.x | 1.x |

**Platform-conditional code suggestion example:**

*Same symptom (audio glitch), different fix per platform + config:*

```
IQ615 (QLI 1.x, Config 1 only):
  Fix in: spa/plugins/alsa/alsa-pcm.c
  Root cause: SPA/ALSA underrun — no ADSP involved

IQ9075 (QLI 2.x, Config 1):
  Fix in: spa/plugins/alsa/alsa-pcm.c
  Root cause: same as IQ615

IQ9075 (QLI 2.x, Config 2):
  Fix in: PAL/src/Pal.cpp
  Root cause: codec pop on PAL stream open — different fix entirely
```

**Deliverables:**
- Auto-detect platform from issue text; `--platform` flag for override
- Platform constraint warnings (e.g. "SSMD requires QLI 2.x and Config 2")
- Code suggestions are platform + config specific
- `--list-platforms` flag

**Done when:** Platform auto-detected in 9/10 cases; code suggestions are
correct for the detected platform and config combination.

---

### Month 3 — Capability checkpoint

- Identifies exact components and source files for any issue on either config
- Suggests targeted single-file code changes with file path, function, diff
- Applies platform constraints and QLI 1.x vs 2.x differences
- Generates different fixes for Config 1 vs Config 2 for the same symptom

---

---

# MONTH 4 — Complex Issues and Multi-File Fix Delivery

**Goal:** The skill handles issues where the root cause is unknown. It ranks
hypotheses per config, generates platform-specific diagnostic runbooks, and
produces complete multi-file code changes once the root cause is confirmed.

---

## M6 · Weeks 12–13 · Root Cause Analysis, Diagnostics, and Hypothesis-Driven Code Suggestions

### What gets built

For issues where the root cause is unknown (Type 10) or multi-causal
(Types 5, 4, 6), the skill generates ranked hypotheses. Each hypothesis
includes the diagnostic command to confirm it and the code change to fix it.

*Example — audio glitch on IQ9075, Config 2 (QLI 2.x):*
```
5. Architecture Notes

  Stack path (Config 2):
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
       usleep(IQ9075_CODEC_RAMP_US);
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
       alsa_monitor.properties["alsa.reserve-device"] = true
```

*Diagnostic runbook — platform-specific, copy-paste ready:*
```
  Step 1: $ PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i 'underrun|xrun'
          Look for: xrun count > 0  →  hypothesis 2

  Step 2: $ pw-top
          Look for: xrun counter in first 500ms  →  confirms hypothesis 2

  Step 3: $ journalctl -u wireplumber --since "1 min ago" | grep 'activat'
          Look for: activation before PAL open  →  hypothesis 3

  Step 4: $ logcat -s PAL:V AGM:V | grep 'setVolume\|mute'  [Config 2 only]
          Look for: volume set before mute ramp  →  confirms hypothesis 1
```

**Deliverables:**
- Section 5: ranked hypotheses with confirm command + fix code per hypothesis
- Section 7: diagnostic runbook (Config-specific and platform-specific)
- `references/platform_matrix.md` — known issue patterns expanded with
  per-config, per-platform root causes and fix references

**Done when:** Hypothesis #1 is correct in 6/10 real cases; each hypothesis
includes a code fix that resolves the issue when confirmed.

---

## M7 · Weeks 14–15 · Full Multi-File Fix Delivery

### What gets built

Once the root cause is confirmed, the skill produces a complete, reviewable
set of code changes across all affected files — primary fix, guard conditions,
test additions, and documentation updates.

*Example — Config 2 audio glitch, hypothesis 1 confirmed (PAL mute ramp):*
```
6. Code Changes

  File 1: PAL/src/Pal.cpp — pal_stream_start()
  - status = rm->getAudioRoute(stream_handle);
  + pal_stream_set_mute(stream_handle, true);
  + status = rm->getAudioRoute(stream_handle);
  + if (status == PAL_EOK) {
  +     usleep(platform_get_codec_ramp_us(stream_handle));
  +     pal_stream_set_mute(stream_handle, false);
  + }

  File 2: PAL/inc/PalDefs.h
  + #define IQ9075_CODEC_RAMP_US   10000
  + #define QCS6490_CODEC_RAMP_US  8000

  File 3: PAL/src/ResourceManager.cpp — platform_get_codec_ramp_us()
  + uint32_t ResourceManager::platform_get_codec_ramp_us(...) {
  +     switch (rm->getPlatformId()) {
  +         case PLATFORM_IQ9075:  return IQ9075_CODEC_RAMP_US;
  +         case PLATFORM_QCS6490: return QCS6490_CODEC_RAMP_US;
  +         default:               return 0;
  +     }
  + }

  File 4: test/pal_stream_test.cpp
  + TEST(PalStreamTest, NoPopOnStreamStart) {
  +     EXPECT_CALL(mock_codec, setMute(true)).Times(1);
  +     EXPECT_CALL(mock_codec, setMute(false)).Times(1);
  +     pal_stream_start(stream);
  + }
```

**Deliverables:**
- Section 6: complete multi-file diff — file path, function, before/after,
  rationale for each change
- Section 7: regression test additions alongside functional tests
- `--confirmed-hypothesis N` flag: skip diagnostics, go straight to full fix
- `--fix-only` flag: output code changes only

**Done when:** Multi-file fix is complete and self-consistent; engineer can
apply it directly; includes test additions.

---

### Month 4 — Capability checkpoint

- Ranks root-cause hypotheses with confirm commands and per-hypothesis fix code
- Generates Config-specific and platform-specific diagnostic runbooks
- Produces complete multi-file code changes once root cause is confirmed
- Includes regression test additions alongside every fix

---

---

# MONTH 5 — New Feature Design and Full Implementation Guidance

**Goal:** The skill handles new feature requests. It accepts architecture
input, produces a full design proposal with code scaffolding, and then
delivers complete implementation guidance. QGenie packaging is completed
this month.

---

## M8 · Weeks 16–17 · New Feature Design and Code Scaffolding

### What gets built

For new feature requests (Types 1, 2, 3, 8, 9), the skill accepts
architecture input and produces a design proposal with code scaffolding —
the skeleton an engineer fills in. Without architecture input, the skill
asks structured questions rather than guessing.

**Architecture input modes:**

| Mode | How to provide |
|---|---|
| `--arch-file FILE` | Markdown or text file describing the existing architecture |
| `--component-desc TEXT` | Free-text description of the component to be modified |
| `--data-flow TEXT` | Description of the data flow to be changed |
| Conversational | Skill asks structured questions about the architecture |

*Example — always-on audio on IQ9075 (Config 2), scaffolding:*
```
  File 1: PAL/inc/PalDefs.h
  + typedef enum {
  +     PAL_STREAM_ALWAYS_ON_CAPTURE = 0x100,
  + } pal_stream_type_ext_t;

  File 2: PAL/src/StreamAlwaysOn.cpp  [new file]
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

  File 3: src/modules/module-pal-source.c
  + static const struct spa_dict_item always_on_props[] = {
  +     { PW_KEY_NODE_NAME,   "pal.always_on.source" },
  +     { PW_KEY_MEDIA_CLASS, "Audio/Source/AlwaysOn" },
  + };  /* TODO: register node */

  File 4: /etc/wireplumber/main.lua.d/53-always-on.lua
  + -- TODO: policy to keep always-on source active
  + table.insert(alsa_monitor.rules, {
  +     matches = { { { "node.name", "matches", "pal.always_on.*" } } },
  +     apply_properties = { ["node.autoconnect"] = false },
  + })
```

**Deliverables:**
- Section 5: architecture notes — existing stack, where feature fits,
  interface points, constraints
- Section 6: code scaffolding — new files, types, API stubs, integration
  hooks, all `TODO`-marked where implementation is needed
- `--arch-file`, `--component-desc`, `--data-flow` flags

**Done when:** Scaffolding is syntactically valid; engineer can fill in
TODOs without needing to understand the full codebase from scratch.

---

## M9 · Weeks 18–19 · Full New Feature Implementation Guidance

### What gets built

Complete implementation code (not just scaffolding), step-by-step integration
plan with effort estimates and dependencies, full test plan, and documentation
tasks.

*Example — always-on audio, full implementation plan:*
```
  Step  File                       Change                              Effort  Depends on
  ──────────────────────────────────────────────────────────────────────────────────────
  1     PAL/inc/PalDefs.h          Add PAL_STREAM_ALWAYS_ON_CAPTURE    S       —
  2     PAL/src/StreamAlwaysOn.cpp Implement StreamAlwaysOn class       L       1
  3     PAL/src/ResourceManager.cpp Add always-on usecase routing       M       2
  4     resourcemanager.xml        Add always-on usecase definition     S       2
  5     module-pal-source.c        Add always-on source node type       M       3
  6     53-always-on.lua           Add WirePlumber suspend policy       M       5
  7     test/always_on_test.cpp    Unit + integration tests             M       2,5
  8     docs/always-on-audio.md    New documentation section            S       7

  Full code for Step 2 (StreamAlwaysOn::start):
  int32_t StreamAlwaysOn::start() {
      status = agm_session_set_config(session_id_,
                   AGM_SESSION_CONFIG_ISLAND_MODE, true);
      if (status != AGM_EOK) return PAL_ERR_ADSP_ISLAND;
      status = agm_session_start(session_id_);
      if (status != AGM_EOK) return PAL_ERR_GRAPH_START;
      adsp_island_active_ = true;
      return PAL_EOK;
  }
```

**Deliverables:**
- Section 6: complete implementation code with integration plan
- Section 7: unit tests, integration tests, regression tests, stress tests
- Section 8: documentation tasks — new API docs, integration guide, changelog

**Done when:** Implementation guidance accepted by a senior engineer as a
valid sprint starting point without major rework.

---

## M10 · Week 20 · QGenie Packaging and Skill Hardening

### What gets built

Package everything as a production QGenie skill and harden the knowledge base.

**Deliverables:**
- `SKILL.md` updated with all capabilities and trigger phrases
- `agents/openai.yaml` updated
- Conversational mode handles all 10 milestone capabilities
- Installable: `Install the pipewire-enhancement skill from sauravk-git/saurav-skills`
- README updated with all usage examples
- `references/examples.md` — 5 full worked examples:
  1. Config 1 bringup — UCM2 mismatch diagnosis and fix
  2. Config 2 bringup — PAL nodes not appearing
  3. Audio glitch (IQ9075, Config 2) — complex issue, multi-file fix
  4. SSMD not working (IQ9075) — medium issue, platform-conditional fix
  5. Always-on audio (IQ9075) — new feature, full implementation
- Knowledge base review: platform matrix, component map, examples validated
  against real hardware

**Done when:** Any engineer can install and use the skill from a single
QGenie prompt; all 13 enhancement types handled end-to-end.

---

### Month 5 — Capability checkpoint

- Accepts architecture input and produces design proposals for new features
- Generates code scaffolding and complete implementation guidance
- Handles all 13 enhancement types end-to-end with code change suggestions
- Packaged as a production QGenie skill, installable in one command

---

---

# Capability and Code Suggestion Growth

| Milestone | Weeks | Capability | Code suggestion depth |
|---|---|---|---|
| M1 | 1–2 | Config 1 bringup; issue classifier | Bringup fix commands; config snippets |
| M2 | 3–5 | Config 2 bringup | PAL/AGM/remoteproc fix commands |
| M3 | 6–7 | Basic issue diagnosis — both configs | Config-specific snippets; known one-liners |
| M4 | 8–9 | Component + source file awareness | Single-file targeted changes |
| M5 | 10–11 | Platform intelligence | Platform-conditional fixes |
| M6 | 12–13 | Root cause hypotheses + diagnostics | Per-hypothesis fix code + diagnostic runbook |
| M7 | 14–15 | Full complex issue fix | Complete multi-file diff with test additions |
| M8 | 16–17 | New feature design | Code scaffolding — API stubs, new files, TODOs |
| M9 | 18–19 | New feature implementation | Complete implementation code with integration plan |
| M10 | 20 | QGenie packaging + hardening | — |

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
| Config 2 bringup more complex than estimated | 3 weeks allocated (M2); scope limited to known failure modes |
| Keyword matching too shallow for complex issues | Build test suite at M1; iterate on keyword map each sprint |
| Platform matrix goes stale as new platforms ship | Matrix in a separate `.md` file — updatable in 30 min |
| Code suggestions are wrong or incomplete | Label all suggestions as starting points; engineer reviews before applying |
| Root-cause hypotheses are incorrect | Label all hypotheses; validate with a senior engineer |
| Architecture input quality varies | Skill asks structured clarifying questions when input is insufficient |
