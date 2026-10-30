# Platform Matrix & Known Issue Patterns (QLI 2.x)

## Table of Contents
1. Platform capabilities matrix
2. Known issue patterns by symptom
3. Diagnostic command reference

---

## 1. Platform Capabilities Matrix

All platforms run QLI 2.x, PipeWire 1.x, WirePlumber 0.5.x.

| Platform | Config 1 | Config 2 | SSMD | Fluence | BT offload | Compressed | Modem |
|---|---|---|---|---|---|---|---|
| IQ9075 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| RB3-Gen2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| QCS6490 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SA8775P | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 2. Known Issue Patterns

### Audio glitch / tick at playback start or end
**Config 1 (spa.alsa) — likely causes:**
1. SPA/ALSA underrun during first buffer cycle
2. Missing pre-roll silent buffer in spa.alsa
3. WirePlumber activating node before ALSA device is ready

**Config 2 (PAL path) — likely causes:**
1. PAL stream open triggering codec pop without software mute ramp
2. `sessionOpen()` latency causing underrun before first ADSP buffer
3. WirePlumber activating node before ADSP graph is stable

**Diagnostic steps:**
```bash
# Check for underruns
PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i "underrun\|xrun\|error"

# Check node state transitions
pw-dump | grep -A3 '"state"'

# Check WirePlumber activation timing
journalctl -u wireplumber --since "1 min ago" | grep -i "activat\|link\|node"
```

### Device not enumerated / missing sound card
**Likely causes:**
1. remoteproc / modem not started before PipeWire
2. ADSP firmware not loaded
3. Audio group permissions missing
4. D-Bus socket not available at PipeWire startup

**Diagnostic steps:**
```bash
# Check remoteproc state
cat /sys/class/remoteproc/remoteproc*/state

# Check ALSA cards
aplay -l && arecord -l

# Check PipeWire sees the device
pw-cli ls Device

# Check audio group
id | grep audio
ls -la /dev/snd/
```

### WirePlumber enumeration delay / race
**Likely causes:**
1. WirePlumber starts before sound card is available
2. Lua policy retry timeout too short
3. systemd service ordering missing `After=` dependency

**Fix pattern:**
```ini
# /etc/systemd/system/wireplumber.service.d/override.conf
[Unit]
After=sound.target pulseaudio.socket
```

### Config 1 topology not loading (spa.alsa path)
**Audio path:** PipeWire → spa.alsa → ALSA kernel driver (no PAL involved)

**Diagnostic steps:**
```bash
# Check ALSA card is visible to the kernel
aplay -l && arecord -l

# Check PipeWire picked up the ALSA device
pw-cli ls Node | grep alsa

# Check WirePlumber linked the default sink/source
wpctl status

# Check for spa.alsa errors
PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i "error\|warn\|alsa"
```

### Config 2 topology not loading (pipewire-pal-plugin → PAL → AudioReach → ADSP — QLI 2.x only)
**Audio path:** PipeWire → pipewire-pal-plugin → PAL → AudioReach → ADSP

**Diagnostic steps:**
```bash
# Check topology .bin file is present
ls /lib/firmware/qcom/

# Check ADSP / remoteproc is running
cat /sys/class/remoteproc/remoteproc*/state

# Check PAL log for graph construction errors
logcat -s PAL:V AGM:V | head -100

# Check pipewire-pal-plugin loaded
pw-cli ls Module | grep pal
```

### SSMD not working
**Prerequisites:**
- QLI 2.x only
- Config 2 topology required on most platforms
- PAL multi-device usecase must be defined in `resourcemanager.xml`

**Diagnostic steps:**
```bash
# Check PAL supports multi-device
grep -i "SSMD\|multi.*device" /etc/pal/resourcemanager.xml

# Check PipeWire links
pw-dump | python3 -m json.tool | grep -B2 -A10 '"type": "PipeWire:Interface:Link"'
```

---

## 3. Diagnostic Command Reference

### PipeWire
```bash
pw-cli ls Node                    # list all nodes
pw-cli ls Device                  # list all devices
pw-cli ls Link                    # list all links
pw-dump                           # full JSON graph dump
pw-top                            # real-time graph monitor
PIPEWIRE_DEBUG=3 pw-play x.wav    # verbose playback
PIPEWIRE_DEBUG=3 pw-record x.wav  # verbose capture
```

### WirePlumber
```bash
wpctl status                      # device/node/link status
wpctl inspect <id>                # inspect a specific object
journalctl -u wireplumber -f      # live WirePlumber log
G_MESSAGES_DEBUG=all wireplumber  # verbose WirePlumber
```

### ALSA
```bash
aplay -l                          # list playback devices
arecord -l                        # list capture devices
aplay -D hw:0,0 test.wav          # direct ALSA playback
alsamixer                         # mixer controls
amixer contents                   # all mixer controls
```

### AudioReach / PAL (Config 2 only)
```bash
# PAL debug log (Android-style logcat on QLI)
logcat -s PAL:V AGM:V SPF:V

# Check ADSP firmware
ls /lib/firmware/qcom/
cat /sys/kernel/debug/remoteproc/remoteproc*/state

# Check AGM graph
cat /sys/kernel/debug/agm/
```
