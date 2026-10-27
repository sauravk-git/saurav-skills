# Platform Matrix, Bringup Prerequisites & Known Issue Patterns

## Table of Contents
1. Platform capabilities matrix
2. Config 1 bringup prerequisites (per platform)
3. Config 2 bringup prerequisites (per platform)
4. Known bringup issue patterns
5. Known runtime issue patterns
6. Diagnostic command reference

---

## 1. Platform Capabilities Matrix

| Platform | QLI | Config 1 | Config 2 | SSMD | Fluence | BT offload | Compressed | Modem |
|---|---|---|---|---|---|---|---|---|
| IQ615 | 1.x | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| IQ8275-EVK | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| IQ9075 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| RB3-Gen2 | 1.x/2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| QCS6490 | 2.x | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SA8775P | 2.x | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| generic-aarch64 | 1.x | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## 2. Config 1 Bringup Prerequisites (ASoC / ALSA-based)

Config 1 uses the ASoC kernel framework with ALSA as the audio backend.
PipeWire talks to the hardware via the SPA ALSA plugin (spa.alsa).

### Required files and components

| Prerequisite | Where it lives | How to verify |
|---|---|---|
| ASoC topology file | `/lib/firmware/<platform>/<card>-tplg.bin` | `dmesg \| grep tplg` |
| UCM2 config | `/usr/share/alsa/ucm2/<card-name>/` | `ls /usr/share/alsa/ucm2/` |
| ASoC / codec kernel modules | Loaded at boot | `lsmod \| grep snd_soc` |
| ALSA sound card | `/dev/snd/controlC*` | `aplay -l` |
| PipeWire | `pipewire.service` running | `systemctl status pipewire` |
| WirePlumber | `wireplumber.service` running | `systemctl status wireplumber` |
| WirePlumber ALSA monitor | Enabled in `wireplumber.conf` | `wpctl status` shows ALSA devices |
| Audio group membership | User in `audio` group | `id \| grep audio` |

### Platform-specific topology file names

| Platform | Topology file (typical) |
|---|---|
| IQ615 | `sm6115-wcd937x-snd-card-tplg.bin` |
| IQ8275-EVK | `sm8275-<codec>-snd-card-tplg.bin` |
| IQ9075 | `sun-<codec>-snd-card-tplg.bin` |
| RB3-Gen2 | `qcs6490-rb3gen2-<codec>-tplg.bin` |
| QCS6490 | `qcs6490-<codec>-snd-card-tplg.bin` |

> Exact filenames vary by BSP version. Check `/lib/firmware/qcom/` and
> `dmesg | grep tplg` to confirm what is loaded.

### Config 1 bringup — ordered checklist

```bash
# Step 1: Verify kernel loaded ASoC topology
dmesg | grep -i "tplg\|topology\|snd-soc\|codec"
# Expected: "ASoC: Loaded topology file <name>"

# Step 2: Verify ALSA sound card present
aplay -l
# Expected: at least one card listed

# Step 3: Verify UCM2 files present
ls /usr/share/alsa/ucm2/
# Expected: directory named after your sound card

# Step 4: Verify PipeWire and WirePlumber running
systemctl --user status pipewire wireplumber
# or system-level:
systemctl status pipewire wireplumber

# Step 5: Verify WirePlumber sees ALSA devices
wpctl status
# Expected: ALSA devices listed under "Audio"

# Step 6: Verify PipeWire sees nodes
pw-cli ls Node | grep alsa
# Expected: alsa_output.* and alsa_input.* nodes

# Step 7: Test playback
pw-play /usr/share/sounds/alsa/Front_Left.wav
# or:
aplay -D pipewire /usr/share/sounds/alsa/Front_Left.wav
```

---

## 3. Config 2 Bringup Prerequisites (AudioReach / PAL-based)

Config 2 uses the AudioReach framework with PAL as the audio abstraction
layer. PipeWire talks to hardware via pipewire-pal-plugin → PAL → ADSP.

### Required files and components

| Prerequisite | Where it lives | How to verify |
|---|---|---|
| ADSP firmware | `/lib/firmware/qcom/adsp*.mbn` or `adsp*.elf` | `ls /lib/firmware/qcom/adsp*` |
| AudioReach topology | `/lib/firmware/qcom/<platform>-tplg.bin` | `ls /lib/firmware/qcom/*tplg*` |
| remoteproc | ADSP in `running` state | `cat /sys/class/remoteproc/remoteproc*/state` |
| AGM kernel driver | `agm` module loaded | `lsmod \| grep agm` |
| PAL resourcemanager.xml | `/etc/pal/resourcemanager.xml` | `xmllint --noout /etc/pal/resourcemanager.xml` |
| pipewire-pal-plugin | `/usr/lib/pipewire-*/libpipewire-module-pal-*.so` | `ls /usr/lib/pipewire-*/` |
| PipeWire PAL config | `/etc/pipewire/pipewire.conf.d/` or `pipewire.conf` | PAL module listed |
| WirePlumber PAL monitor | Enabled in WirePlumber config | `wpctl status` shows PAL devices |
| Audio group membership | User in `audio` group | `id \| grep audio` |

### Platform-specific firmware names

| Platform | ADSP firmware (typical) | Topology (typical) |
|---|---|---|
| IQ9075 | `adsp.mbn` | `sun-adsp-tplg.bin` |
| QCS6490 | `adsp.mbn` | `qcs6490-adsp-tplg.bin` |
| SA8775P | `adsp.mbn` | `sa8775p-adsp-tplg.bin` |
| IQ8275-EVK | `adsp.mbn` | `sm8275-adsp-tplg.bin` |
| RB3-Gen2 | `adsp.mbn` | `qcs6490-rb3gen2-adsp-tplg.bin` |

> Exact filenames vary by BSP version. Check `/lib/firmware/qcom/` and
> `cat /sys/kernel/debug/agm/` to confirm what is loaded.

### Config 2 bringup — ordered checklist

```bash
# Step 1: Verify ADSP firmware present
ls -lh /lib/firmware/qcom/adsp*
ls -lh /lib/firmware/qcom/*tplg*

# Step 2: Verify remoteproc started ADSP
cat /sys/class/remoteproc/remoteproc*/state
# Expected: "running"
# If "offline": remoteproc failed to start — check dmesg

# Step 3: Verify AGM driver loaded
lsmod | grep agm
# Expected: agm module listed
# Also check AGM graph state:
ls /sys/kernel/debug/agm/ 2>/dev/null && echo "AGM debug available"

# Step 4: Verify PAL config valid
xmllint --noout /etc/pal/resourcemanager.xml && echo "resourcemanager.xml OK"

# Step 5: Verify pipewire-pal-plugin installed
ls /usr/lib/pipewire-*/libpipewire-module-pal*.so

# Step 6: Verify PipeWire and WirePlumber running
systemctl --user status pipewire wireplumber

# Step 7: Verify PipeWire sees PAL nodes
pw-cli ls Node | grep pal
# Expected: pal_output.* and pal_input.* nodes

# Step 8: Verify WirePlumber sees PAL devices
wpctl status
# Expected: PAL devices listed under "Audio"

# Step 9: Test playback via PAL
pw-play /usr/share/sounds/alsa/Front_Left.wav

# Step 10: Check PAL log for errors
logcat -s PAL:V AGM:V SPF:V 2>/dev/null || \
    journalctl -u pipewire --since "2 min ago" | grep -i "pal\|agm\|adsp"
```

---

## 4. Known Bringup Issue Patterns

### Config 1 — No ALSA sound card after boot

**Symptoms:** `aplay -l` shows no cards; `pw-cli ls Device` empty.

**Likely causes (in order):**
1. ASoC topology file missing or wrong filename
2. Codec kernel module not loaded
3. I2C/SPI bus not initialised before codec driver probes
4. Device tree node for sound card disabled

**Diagnostic steps:**
```bash
dmesg | grep -i "tplg\|topology\|snd\|codec\|i2c\|spi" | tail -30
lsmod | grep snd_soc
cat /proc/asound/cards
```

**Fix pattern:**
```bash
# Verify topology file name matches what the driver expects
dmesg | grep "ASoC: No topology" | head -5
# Copy correct topology file if missing:
cp <correct-tplg.bin> /lib/firmware/qcom/
# Reload driver:
modprobe -r snd_soc_<platform> && modprobe snd_soc_<platform>
```

---

### Config 1 — WirePlumber does not see ALSA device

**Symptoms:** `aplay -l` shows card; `wpctl status` shows nothing under Audio.

**Likely causes:**
1. WirePlumber ALSA monitor not enabled in config
2. WirePlumber started before ALSA card was ready
3. Audio group permissions missing

**Fix pattern:**
```bash
# Check WirePlumber ALSA monitor is enabled
grep -r "alsa" /usr/share/wireplumber/ /etc/wireplumber/

# Restart WirePlumber after card is confirmed present
systemctl --user restart wireplumber

# Fix audio group
sudo usermod -aG audio $USER
# Then log out and back in
```

---

### Config 1 — UCM2 not found / wrong profile

**Symptoms:** PipeWire nodes appear but playback fails; `alsamixer` shows
wrong controls; `aplay` works but `pw-play` does not.

**Likely causes:**
1. UCM2 directory name does not match ALSA card name
2. UCM2 `HiFi.conf` missing verb or device definitions
3. Wrong UCM2 version for the topology

**Diagnostic steps:**
```bash
# Check ALSA card name
cat /proc/asound/card*/id

# Check UCM2 directory name matches
ls /usr/share/alsa/ucm2/
# Directory name must match card name exactly

# Check UCM2 loads without error
alsaucm -c <card-name> list _verbs
```

---

### Config 2 — ADSP not starting (remoteproc offline)

**Symptoms:** `cat /sys/class/remoteproc/remoteproc*/state` shows `offline`.

**Likely causes:**
1. ADSP firmware file missing or wrong path
2. Firmware signing mismatch (secure boot)
3. remoteproc driver not loaded
4. Power domain not enabled before remoteproc probe

**Diagnostic steps:**
```bash
dmesg | grep -i "remoteproc\|adsp\|firmware\|rproc" | tail -30
ls /lib/firmware/qcom/adsp*
cat /sys/class/remoteproc/remoteproc*/firmware
```

**Fix pattern:**
```bash
# Manually trigger remoteproc start
echo start > /sys/class/remoteproc/remoteproc<N>/state
# Check result:
cat /sys/class/remoteproc/remoteproc<N>/state
dmesg | tail -20
```

---

### Config 2 — AGM driver not loaded

**Symptoms:** remoteproc running but `lsmod | grep agm` empty; PAL fails
to open streams.

**Likely causes:**
1. AGM kernel module not built or not in initramfs
2. AGM driver probe failed (check dmesg)
3. Wrong kernel config (`CONFIG_SND_SOC_MSM_QDSP6_AGM` not set)

**Diagnostic steps:**
```bash
dmesg | grep -i "agm\|qdsp\|q6" | tail -20
modinfo agm 2>/dev/null || echo "AGM module not found"
```

---

### Config 2 — PAL fails to open stream

**Symptoms:** `pw-play` fails; PAL log shows stream open error.

**Likely causes:**
1. `resourcemanager.xml` missing usecase for the requested stream type
2. AudioReach topology not loaded by ADSP
3. AGM session limit reached (too many open streams)
4. remoteproc crashed after initial start

**Diagnostic steps:**
```bash
# Check PAL log
logcat -s PAL:V AGM:V | grep -i "error\|fail\|open" | head -20

# Check remoteproc still running
cat /sys/class/remoteproc/remoteproc*/state

# Check AGM session state
cat /sys/kernel/debug/agm/ 2>/dev/null

# Validate resourcemanager.xml
xmllint --noout /etc/pal/resourcemanager.xml
grep -i "PCM_RT_PROXY\|DEEP_BUFFER\|LOW_LATENCY" /etc/pal/resourcemanager.xml | head -10
```

---

### Config 2 — pipewire-pal-plugin nodes not appearing

**Symptoms:** PipeWire running but `pw-cli ls Node | grep pal` empty.

**Likely causes:**
1. pipewire-pal-plugin not loaded in `pipewire.conf`
2. PAL library not found (missing `libpal.so`)
3. PAL initialisation failed silently

**Diagnostic steps:**
```bash
# Check pipewire.conf loads PAL module
grep -r "pal" /etc/pipewire/ /usr/share/pipewire/

# Check PAL library present
ldconfig -p | grep libpal

# Check PipeWire log for PAL errors
PIPEWIRE_DEBUG=3 pipewire 2>&1 | grep -i "pal\|error" | head -20
```

---

## 5. Known Runtime Issue Patterns

### Audio glitch / tick at playback start or end

**Config 1 likely causes:**
1. SPA/ALSA underrun during first buffer cycle
2. Missing pre-roll silent buffer in spa.alsa
3. UCM2 verb transition causing codec pop

**Config 2 likely causes:**
1. PAL stream open triggering codec pop without mute ramp
2. WirePlumber activating node before ADSP graph is stable
3. AGM `sessionOpen()` latency before first buffer

**Diagnostic steps:**
```bash
# Config 1
PIPEWIRE_DEBUG=3 pw-play test.wav 2>&1 | grep -i "underrun\|xrun\|error"
pw-top  # watch for xruns

# Config 2
logcat -s PAL:V AGM:V | grep -i "stream\|open\|volume\|mute"
journalctl -u wireplumber --since "1 min ago" | grep -i "activat\|link"
```

---

### SSMD not working (Config 2 only)

**Prerequisites:**
- QLI 2.x platform
- Config 2 topology loaded
- PAL multi-device usecase defined in `resourcemanager.xml`

**Diagnostic steps:**
```bash
grep -i "SSMD\|multi.*device" /etc/pal/resourcemanager.xml
pw-dump | python3 -m json.tool | grep -B2 -A10 '"type": "PipeWire:Interface:Link"'
```

---

## 6. Diagnostic Command Reference

### PipeWire (both configs)
```bash
pw-cli ls Node                    # list all nodes
pw-cli ls Device                  # list all devices
pw-cli ls Link                    # list all links
pw-dump                           # full JSON graph dump
pw-top                            # real-time graph monitor
PIPEWIRE_DEBUG=3 pw-play x.wav    # verbose playback
PIPEWIRE_DEBUG=3 pw-record x.wav  # verbose capture
```

### WirePlumber (both configs)
```bash
wpctl status                      # device/node/link status
wpctl inspect <id>                # inspect a specific object
journalctl -u wireplumber -f      # live WirePlumber log
G_MESSAGES_DEBUG=all wireplumber  # verbose WirePlumber
```

### ALSA / Config 1
```bash
aplay -l                          # list playback devices
arecord -l                        # list capture devices
aplay -D hw:0,0 test.wav          # direct ALSA playback (bypass PipeWire)
alsamixer                         # mixer controls
amixer contents                   # all mixer controls
alsaucm -c <card> list _verbs     # UCM2 verbs
cat /proc/asound/card*/id         # ALSA card names
dmesg | grep -i tplg              # topology load status
```

### AudioReach / PAL / Config 2
```bash
logcat -s PAL:V AGM:V SPF:V       # PAL/AGM/ADSP log
cat /sys/class/remoteproc/remoteproc*/state   # ADSP state
ls /lib/firmware/qcom/            # firmware files
cat /sys/kernel/debug/agm/        # AGM graph state
lsmod | grep agm                  # AGM driver loaded
xmllint --noout /etc/pal/resourcemanager.xml  # PAL config valid
```
