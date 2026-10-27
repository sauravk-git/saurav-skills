# Component Map — Config 1 and Config 2

## Table of Contents
1. Config 1 vs Config 2 — architecture overview
2. Config 1 component map (ASoC / ALSA-based)
3. Config 2 component map (AudioReach / PAL-based)
4. Shared components (both configs)
5. QLI 1.x vs QLI 2.x feature delta
6. AudioReach graph construction (Config 2)
7. SPA plugin registry

---

## 1. Config 1 vs Config 2 — Architecture Overview

Config 1 and Config 2 are two distinct audio backend architectures for
Qualcomm QLI platforms. They are mutually exclusive — a platform runs one
or the other, not both simultaneously.

### Config 1 — ASoC / ALSA-based PipeWire

```
Application (pw-play, GStreamer, etc.)
    └─► PipeWire Core
            └─► SPA ALSA plugin (spa.alsa)
                    └─► ALSA PCM / compress API
                            └─► ASoC kernel driver (snd-soc-*)
                                    └─► Codec / I2S / DMIC (hardware)
```

**Key characteristics:**
- Audio processing runs on the HLOS (CPU), not the ADSP
- Topology defined by ASoC topology file (`.bin`) loaded by the kernel driver
- Device configuration via UCM2 (Use Case Manager 2) files
- WirePlumber uses the ALSA monitor to discover devices
- Simpler stack — fewer moving parts, easier to debug
- Supported on all QLI platforms (1.x and 2.x)
- Lower power efficiency than Config 2 (no DSP offload)

**Prerequisites to bring up Config 1:**
- ASoC topology `.bin` file present and loaded by kernel driver
- UCM2 files present in `/usr/share/alsa/ucm2/<card-name>/`
- ALSA sound card visible: `aplay -l` shows the card
- `snd-soc-*` kernel modules loaded
- WirePlumber ALSA monitor enabled in `wireplumber.conf`
- PipeWire and WirePlumber services running

### Config 2 — AudioReach / PAL-based PipeWire

```
Application (pw-play, GStreamer, etc.)
    └─► PipeWire Core
            └─► pipewire-pal-plugin (PAL sink/source nodes)
                    └─► PAL (Platform Abstraction Layer)
                            └─► AudioReach / AGM
                                    └─► ADSP (SPF firmware)
                                            └─► Codec / I2S / DMIC (hardware)
```

**Key characteristics:**
- Audio processing offloaded to the ADSP (DSP)
- Topology defined by AudioReach topology `.bin` file loaded by ADSP firmware
- No UCM2 — device configuration via PAL `resourcemanager.xml`
- WirePlumber discovers PAL nodes exposed by pipewire-pal-plugin
- More complex stack — ADSP, remoteproc, AGM driver, PAL all must be up
- QLI 2.x only (ADSP offload not available on QLI 1.x)
- Higher power efficiency, required for SSMD, Fluence, always-on audio

**Prerequisites to bring up Config 2:**
- ADSP firmware present: `/lib/firmware/qcom/adsp*.mbn` (or `.elf`)
- remoteproc started and ADSP in `running` state
- AGM kernel driver loaded: `lsmod | grep agm`
- AudioReach topology `.bin` loaded by ADSP
- PAL `resourcemanager.xml` present and valid
- `pipewire-pal-plugin` installed and configured
- WirePlumber PAL monitor enabled
- PipeWire and WirePlumber services running

---

## 2. Config 1 Component Map (ASoC / ALSA-based)

### Kernel / ASoC layer
| Sub-component | Key paths |
|---|---|
| ASoC topology file | `/lib/firmware/<platform>/<card>-tplg.bin` |
| UCM2 files | `/usr/share/alsa/ucm2/<card-name>/<card-name>.conf`, `HiFi.conf` |
| ASoC driver | `sound/soc/qcom/` in kernel tree |
| ALSA card | `/dev/snd/controlC*`, `/dev/snd/pcmC*D*` |
| Codec driver | `sound/soc/codecs/` |

### SPA / PipeWire layer
| Sub-component | Key source paths |
|---|---|
| spa.alsa device factory | `spa/plugins/alsa/alsa-device.c` |
| spa.alsa PCM sink | `spa/plugins/alsa/alsa-sink.c` |
| spa.alsa PCM source | `spa/plugins/alsa/alsa-source.c` |
| spa.alsa PCM engine | `spa/plugins/alsa/alsa-pcm.c` |
| ALSA mixer controls | `spa/plugins/alsa/alsa-mixer.c` |
| Compressed offload | `spa/plugins/alsa/alsa-compress-offload.c` |
| UCM2 integration | `spa/plugins/alsa/alsa-ucm.c` |

### WirePlumber layer
| Sub-component | Key paths |
|---|---|
| ALSA monitor | `modules/module-monitor-alsa.c` |
| Device activation | `modules/module-device-activation.c` |
| Default sink/source | `modules/module-default-nodes.c` |
| Lua config | `/usr/share/wireplumber/`, `/etc/wireplumber/` |
| ALSA monitor rules | `/etc/wireplumber/main.lua.d/` |

### Config 1 bringup checklist
```bash
# 1. Verify ASoC topology loaded
dmesg | grep -i "topology\|tplg\|snd-soc"

# 2. Verify UCM2 files present
ls /usr/share/alsa/ucm2/

# 3. Verify ALSA card visible
aplay -l && arecord -l

# 4. Verify PipeWire sees the device
pw-cli ls Device
pw-cli ls Node | grep alsa

# 5. Verify WirePlumber ALSA monitor active
wpctl status

# 6. Test basic playback
pw-play /usr/share/sounds/alsa/Front_Left.wav
```

---

## 3. Config 2 Component Map (AudioReach / PAL-based)

### ADSP / firmware layer
| Sub-component | Key paths |
|---|---|
| ADSP firmware | `/lib/firmware/qcom/adsp*.mbn` or `adsp*.elf` |
| AudioReach topology | `/lib/firmware/qcom/<platform>-tplg.bin` |
| remoteproc state | `/sys/class/remoteproc/remoteproc*/state` |
| AGM debug | `/sys/kernel/debug/agm/` |

### PAL layer
| Sub-component | Key source paths |
|---|---|
| Usecase manager | `Pal.cpp`, `ResourceManager.cpp` |
| Resource config | `/etc/pal/resourcemanager.xml` |
| Stream PCM | `StreamPCM.cpp` |
| Stream compress | `StreamCompress.cpp` |
| Device routing | `Device*.cpp` |
| AGM interface | `AGM*.cpp` |

### pipewire-pal-plugin layer
| Sub-component | Key source paths |
|---|---|
| PAL sink node | `src/modules/module-pal-sink.c` |
| PAL source node | `src/modules/module-pal-source.c` |
| PAL API bridge | `src/pal/pal_api.cpp` |
| Stream lifecycle | `src/pal/pal_stream.cpp` |
| Device enumeration | `src/pal/pal_device.cpp` |

### WirePlumber layer (Config 2)
| Sub-component | Key paths |
|---|---|
| PAL monitor | WirePlumber PAL monitor module |
| Node activation | Triggered by PAL device enumeration |
| Lua config | `/etc/wireplumber/` — PAL-specific rules |

### Config 2 bringup checklist
```bash
# 1. Verify ADSP firmware present
ls /lib/firmware/qcom/adsp*

# 2. Verify remoteproc started ADSP
cat /sys/class/remoteproc/remoteproc*/state
# Expected: "running"

# 3. Verify AGM driver loaded
lsmod | grep agm
cat /sys/kernel/debug/agm/  # AGM graph state

# 4. Verify PAL resourcemanager.xml present
ls /etc/pal/resourcemanager.xml
# Quick sanity check
xmllint --noout /etc/pal/resourcemanager.xml && echo "XML valid"

# 5. Verify pipewire-pal-plugin installed
ls /usr/lib/pipewire-*/libpipewire-module-pal-*.so

# 6. Verify PipeWire sees PAL nodes
pw-cli ls Node | grep pal

# 7. Verify WirePlumber PAL monitor active
wpctl status

# 8. Test basic playback via PAL
pw-play /usr/share/sounds/alsa/Front_Left.wav

# 9. Check PAL log for errors
logcat -s PAL:V AGM:V SPF:V 2>/dev/null || \
    journalctl -u pipewire --since "1 min ago" | grep -i pal
```

---

## 4. Shared Components (Both Configs)

### PipeWire Core
| Sub-component | Key source paths |
|---|---|
| Node / port / link | `src/pipewire/node.c`, `port.c`, `link.c` |
| Format negotiation | `src/pipewire/format.c`, `spa/include/spa/param/` |
| Buffering / scheduling | `src/pipewire/impl-node.c`, `src/modules/module-rt.c` |
| Core protocol | `src/pipewire/core.c`, `protocol-native.c` |
| Logging | `src/pipewire/log.c`, `PIPEWIRE_DEBUG` env var |

### WirePlumber Core
| Sub-component | Key source paths |
|---|---|
| Linking policy | `modules/module-si-audio-adapter.c`, `module-si-standard-link.c` |
| Default nodes | `modules/module-default-nodes.c` |
| Startup ordering | `wireplumber.conf`, `main.lua.d/` |

### Systemd services
| Service | Purpose |
|---|---|
| `pipewire.service` | PipeWire daemon |
| `pipewire-pulse.service` | PulseAudio compatibility layer |
| `wireplumber.service` | Session / policy manager |

---

## 5. QLI 1.x vs QLI 2.x Feature Delta

| Feature | QLI 1.x | QLI 2.x |
|---|---|---|
| Config 1 (ASoC/ALSA) | ✓ | ✓ |
| Config 2 (AudioReach/PAL) | ✗ | ✓ |
| pipewire-pal-plugin | ✗ | ✓ |
| ADSP audio offload | ✗ | ✓ |
| SSMD | ✗ | ✓ |
| Fluence voice processing | ✗ | ✓ |
| Always-on audio | ✗ | ✓ |
| Compressed offload (full) | ✗ | ✓ |
| BT offload | ✗ | ✓ |
| Modem audio | ✗ | ✓ |
| WirePlumber version | 0.4.x | 0.5.x |
| PipeWire version | 0.3.x | 1.x |

---

## 6. AudioReach Graph Construction (Config 2)

```
PipeWire node
    └─► pipewire-pal-plugin
            └─► PAL::StreamPCM::open()
                    └─► ResourceManager::getAudioRoute()
                            └─► AGM::sessionOpen()
                                    └─► ADSP graph (SPF)
                                            └─► Codec / I2S / DMIC
```

Key events that can cause issues:
- `sessionOpen()` latency before first buffer → glitch at start
- Codec pop on `setVolume()` before ramp → tick at start
- `sessionClose()` without drain → glitch at end
- remoteproc not ready when PAL opens → stream open failure

---

## 7. SPA Plugin Registry

```bash
# List all SPA plugins
spa-inspect /usr/lib/spa-0.2/

# Inspect ALSA plugin (Config 1)
spa-inspect /usr/lib/spa-0.2/alsa/libspa-alsa.so

# List available ALSA nodes (Config 1)
pw-cli ls Node | grep alsa

# List available PAL nodes (Config 2)
pw-cli ls Node | grep pal

# Dump full graph (both configs)
pw-dump | python3 -m json.tool | grep -A5 '"type": "PipeWire:Interface:Node"'
```
