---
name: glymur-kernel-deb
description: >
  Build any Linux kernel as Debian (.deb) packages and install them on a Glymur CRD
  target device. Covers capturing the running kernel config, cross-compiling with
  bindeb-pkg, transferring packages via SCP or ADB, installing with dpkg, and
  updating the EFI boot entry to include the Glymur CRD device tree.
source: https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur
license: Proprietary. Internal Qualcomm use only.
---

# Build and Install Kernel .deb — Glymur

## Overview

This skill guides you through building any Linux kernel as Debian (`.deb`) packages
and installing them on a Glymur CRD target device.

**Prerequisites:**
- Shell access to both host and target
- Required build tools installed on the host (`gcc-aarch64-linux-gnu`, `make`, `dpkg-dev`, `libssl-dev`, etc.)
- Access to `adb` **or** `scp`
- Permissions to install packages and edit EFI boot entries on the target

---

## Step-by-Step Instructions

### 1. Save the current kernel config on the target

Capture the running kernel configuration so the new build starts from a known-good baseline.

```bash
zcat /proc/config.gz > kernel.config
```

---

### 2. Pull the config to the host

Copy the saved configuration file from the target to the host working directory.

```bash
adb pull kernel.config ./
```

---

### 3. Clone the kernel source on the host

Clone the Qualcomm kernel branch or `linux-next`, depending on your needs, and enter
the repository.

```bash
git clone https://github.com/qualcomm-linux/kernel.git -b qcom-next-7.2-20260826
cd kernel
```

---

### 4. Apply your kernel changes

Apply any required patches or source changes before building.

```bash
# Apply your kernel changes/patches here
```

---

### 5. Prepare the build output directory

Assuming `kernel.config` is one level above the kernel directory, create the output
directory and seed it with the pulled configuration.

```bash
mkdir -p out-arm64
cp ../kernel.config out-arm64/.config
```

---

### 6. Set the ARM64 build environment

Export the architecture and cross-compiler prefix used for the build.

```bash
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
```

---

### 7. Update the kernel config

Refresh the configuration so any new symbols get their default values.

```bash
make O=out-arm64 olddefconfig
```

> This step keeps the build aligned with the checked-out source tree while preserving
> your existing configuration choices.

---

### 8. Build Debian kernel packages

Build Debian packages for the ARM64 kernel.

```bash
make O=out-arm64 -j$(nproc) bindeb-pkg
```

---

### 9. Check the generated packages on the host

Verify the expected Debian package artifacts were created.

```bash
ls -lh ../linux-*.deb
```

---

### 10. Copy the packages to the target

Use either SCP or ADB to transfer the generated packages.

**SCP:**
```bash
scp ../linux-*.deb debian@<TARGET_IP>:/tmp/
```

**ADB:**
```bash
adb push ../linux-*.deb /tmp/
```

---

### 11. Check the copied packages on the target

Confirm the package files are present in `/tmp`.

```bash
ls -lh /tmp/linux-*.deb
```

---

### 12. Install the kernel packages on the target

Install the transferred Debian packages.

```bash
sudo dpkg -i /tmp/linux-*.deb
```

---

### 13. Check available boot entries

Inspect the EFI loader entries before modifying one.

```bash
ls -lh /boot/efi/loader/entries/
```

---

### 14. Back up the current boot entry

Back up the EFI loader entry for the newly installed kernel version before editing it.

> ⚠️ The entry filename is machine-specific — it usually starts with your machine ID
> and ends with the installed kernel version, e.g. `<MACHINE_ID>-<KERNEL_VERSION>.conf`.
> **Do not blindly reuse the sample filename below.** First identify the correct entry
> for your target using the list from Step 13, then update both the source and `.bak`
> destination paths accordingly.

```bash
sudo cp /boot/efi/loader/entries/f4ea640e4a8842abb315be938ffb8375-7.3.0-rc2-next-20260907.conf \
        /boot/efi/loader/entries/f4ea640e4a8842abb315be938ffb8375-7.3.0-rc2-next-20260907.conf.bak
```

---

### 15. Add the Glymur CRD device tree

Append the device tree line to the selected boot entry.

```bash
echo "devicetree /dtb/qcom/glymur-crd.dtb" | sudo tee -a \
  /boot/efi/loader/entries/f4ea640e4a8842abb315be938ffb8375-7.3.0-rc2-next-20260907.conf
```

---

### 16. Verify the boot entry contents

Open the boot entry and confirm the device tree line is present.

```bash
cat /boot/efi/loader/entries/f4ea640e4a8842abb315be938ffb8375-7.3.0-rc2-next-20260907.conf
```

**Expected line:**
```
devicetree /dtb/qcom/glymur-crd.dtb
```

---

### 17. Reboot the target

Restart the device to boot into the newly installed kernel.

```bash
sync
sudo reboot
```

---

### 18. Verify the new kernel after reboot

Check the running kernel version and build information.

```bash
uname -a
cat /proc/version
```

**✅ Success criteria:**
- The target reboots successfully
- The updated kernel is reported by `uname -a`
- The boot entry includes `devicetree /dtb/qcom/glymur-crd.dtb`

---

## Quick Validation Checklist

- [ ] Pulled `kernel.config` from the running target
- [ ] Built `linux-*.deb` packages successfully
- [ ] Copied packages to `/tmp/` on the target
- [ ] Installed packages with `dpkg -i`
- [ ] Backed up the EFI loader entry before editing
- [ ] Added the Glymur CRD DTB line to the boot entry
- [ ] Verified the new kernel after reboot

---

## References

- Source: [Build and Install Kernel .deb Glymur](<https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur>)
- Kernel repo: [qualcomm-linux/kernel](<https://github.com/qualcomm-linux/kernel>)
