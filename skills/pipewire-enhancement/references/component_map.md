# Component Map — QLI 2.x (Config 1 & Config 2)

## Table of Contents
1. Source-file mapping by component
2. Config 1 vs Config 2 feature delta (QLI 2.x)
3. AudioReach graph construction
4. SPA plugin registry

---

## 1. Source-file Mapping

### PipeWire Core
| Sub-component | Key source paths |
|---|---|
| Node/port/link | `src/pipewire/node.c`, `port.c`, `link.c` |
| Format negotiation | `src/pipewire/format.c`, `spa/include/spa/param/` |
| Buffering / scheduling | `src/pipewire/impl-node.c`, `src/modules/module-rt.c` |
| Core protocol | `src/pipewire/core.c`, `src/pipewire/protocol-native.c` |
| Logging | `src/pipewire/log.c`, `PIPEWIRE_DEBUG` env var |

### SPA
| Sub-component | Key source paths |
|---|---|
| spa.alsa | `spa/plugins/alsa/alsa-pcm.c`, `alsa-sink.c`, `alsa-source.c` |
| ALSA controls | `spa/plugins/alsa/alsa-mixer.c` |
| Compressed offload | `spa/plugins/alsa/alsa-compress-offload.c` |
| Device factory | `spa/plugins/alsa/alsa-device.c` |
| Buffer handling | `spa/include/spa/buffer/`, `spa/support/` |

### WirePlumber
| Sub-component | Key source paths |
|---|---|
| Device/node discovery | `lib/wp/device.c`, `modules/module-device-activation.c` |
| Default sink/source | `modules/module-default-nodes.c` |
| Linking policy | `modules/module-si-audio-adapter.c`, `module-si-standard-link.c` |
| Lua config | `/usr/share/wireplumber/`, `/etc/wireplumber/` |
| Startup ordering | `wireplumber.conf`, `main.lua.d/` |

### pipewire-pal-plugin (Qualcomm)
| Sub-component | Key source paths |
|---|---|
| PAL sink/source | `src/modules/module-pal-sink.c`, `module-pal-source.c` |
| PAL API calls | `src/pal/pal_api.cpp` |
| Stream lifecycle | `src/pal/pal_stream.cpp` |
| Device enumeration | `src/pal/pal_device.cpp` |

### PAL / AudioReach
| Sub-component | Key source paths |
|---|---|
| Usecase manager | `Pal.cpp`, `ResourceManager.cpp` |
| Stream open/close | `Stream*.cpp` (StreamPCM, StreamCompress, etc.) |
| Device routing | `Device*.cpp` |
| Graph construction | `AudioReachGraph.cpp`, `AGM*.cpp` |

---

## 2. Config 1 vs Config 2 Feature Delta (QLI 2.x)

Both configs run on QLI 2.x with PipeWire 1.x and WirePlumber 0.5.x.

| Feature | Config 1 | Config 2 |
|---|---|---|
| Audio backend | spa.alsa direct | pipewire-pal-plugin → PAL → AudioReach → ADSP |
| DSP offload | No | Yes (ADSP graph) |
| Compressed offload | No | Full (via PAL compress stream) |
| SSMD | No | Yes |
| Fluence voice processing | No | Yes |
| Always-on audio | No | Yes |
| Modem audio | No | Yes (via remoteproc) |
| BT offload | No | Yes |
| Topology .bin loading | No | Yes |
| pipewire-pal-plugin | No | Yes |

---

## 3. AudioReach Graph Construction

> **Config 2 only.** Config 1 uses spa.alsa directly and does not involve PAL or AudioReach.

```
PipeWire node
    └─► pipewire-pal-plugin
            └─► PAL::StreamPCM::open()
                    └─► ResourceManager::getAudioRoute()
                            └─► AGM::sessionOpen()
                                    └─► ADSP graph (SPF)
                                            └─► Codec / I2S / DMIC
```

Key events that can cause glitches:
- `sessionOpen()` latency before first buffer
- Codec pop on `setVolume()` before ramp
- `sessionClose()` without drain

---

## 4. SPA Plugin Registry

Useful `spa-inspect` commands:

```bash
# List all SPA plugins
spa-inspect /usr/lib/spa-0.2/

# Inspect ALSA plugin
spa-inspect /usr/lib/spa-0.2/alsa/libspa-alsa.so

# List available ALSA nodes
pw-cli ls Node | grep alsa

# Dump full graph
pw-dump | python3 -m json.tool | grep -A5 '"type": "PipeWire:Interface:Node"'
```
