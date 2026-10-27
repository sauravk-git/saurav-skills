---
name: glymur-kernel-deb
description: >
  Build any Linux kernel as Debian (.deb) packages and install them on a Glymur
  (Debian-based) target device. Covers installing host build tools, capturing the
  running kernel config, cross-compiling with bindeb-pkg, transferring packages via
  SCP or ADB, installing with dpkg, and updating the EFI boot entry to include the
  Glymur CRD device tree.
source: https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur
license: Proprietary. Internal Qualcomm use only.
---

# Build and Install Kernel .deb — Glymur

## Overview

This skill guides you through building any Linux kernel as Debian (`.deb`) packages
and installing them on a **Glymur** target device (Debian-based).

The workflow is generic — no step is tied to a specific kernel version, machine ID,
or branch name. Substitute the placeholders (shown as `<LIKE_THIS>`) with the values
that apply to your environment.

**Prerequisites:**
- Shell access to both host and target (SSH and/or ADB)
- An x86-64 Linux host with `sudo` access for installing build tools
- Permissions to install packages and edit EFI boot entries on the target

---

## Step 0 — Install host build tools

Install the cross-compilation toolchain and kernel packaging dependencies on the host.

```bash
sudo apt-get install -y \
    gcc-aarch64-linux-gnu \
    make \
    dpkg-dev \
    libssl-dev \
    libelf-dev \
    bc \
    bison \
    flex \
    git
```

---

## Step-by-Step Instructions

### 1. Save the current kernel config on the target

Capture the running kernel configuration so the new build starts from a known-good
baseline.

```bash
# On the target
zcat /proc/config.gz > kernel.config
```

---

### 2. Pull the config to the host

Copy the saved configuration file from the target to the host working directory.
Use whichever transport is available:

**ADB:**
```bash
adb pull kernel.config ./
```

**SCP:**
```bash
scp <USER>@<TARGET_IP>:~/kernel.config ./
```

> `<USER>` is typically `debian` or `root` on a Glymur device.

---

### 3. Clone the kernel source on the host

Clone the desired kernel branch and enter the repository.

```bash
git clone https://github.com/qualcomm-linux/kernel.git -b <BRANCH_NAME>
cd kernel
```

> Replace `<BRANCH_NAME>` with the branch you want to build, e.g.
> `qcom-next-7.2-20260826` or `linux-next`. Check
> [qualcomm-linux/kernel](https://github.com/qualcomm-linux/kernel) for available
> branches.

---

### 4. Apply your kernel changes

Apply any required patches or source changes before building.

```bash
# Apply your kernel changes/patches here, e.g.:
# git am 0001-my-fix.patch
# patch -p1 < my-change.patch
```

> Skip this step if you are building the upstream tree unmodified.

---

### 5. (Optional) Customise the kernel config

If you need to enable or disable specific options, run menuconfig before building.

```bash
make O=out-arm64 ARCH=arm64 menuconfig
```

---

### 6. Prepare the build output directory

Create the output directory and seed it with the pulled configuration.

```bash
mkdir -p out-arm64
cp ../kernel.config out-arm64/.config
```

> `kernel.config` is assumed to be one level above the kernel source directory
> (i.e. where you ran `git clone`).

---

### 7. Set the ARM64 build environment

Export the architecture and cross-compiler prefix used for the build.

```bash
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
```

---

### 8. Update the kernel config

Refresh the configuration so any new Kconfig symbols introduced since the config was
captured get their default values.

```bash
make O=out-arm64 olddefconfig
```

---

### 9. Build Debian kernel packages

Build Debian packages for the ARM64 kernel. The `.deb` files are written to the
directory **one level above** the kernel source tree (i.e. the parent of where you
ran `git clone`).

```bash
make O=out-arm64 -j$(nproc) bindeb-pkg
```

---

### 10. Check the generated packages on the host

Verify the expected Debian package artifacts were created.

```bash
ls -lh ../linux-*.deb
```

> The packages land in `../` relative to the kernel source directory because
> `bindeb-pkg` always writes to the parent of the source tree, regardless of the
> `O=` output directory.

---

### 11. Copy the packages to the target

Use either SCP or ADB to transfer the generated packages.

**SCP:**
```bash
scp ../linux-*.deb <USER>@<TARGET_IP>:/tmp/
```

**ADB:**
```bash
adb push ../linux-*.deb /tmp/
```

---

### 12. Check the copied packages on the target

Confirm the package files are present in `/tmp`.

```bash
# On the target
ls -lh /tmp/linux-*.deb
```

---

### 13. Install the kernel packages on the target

Install the transferred Debian packages.

```bash
# On the target
sudo dpkg -i /tmp/linux-*.deb
```

---

### 14. Check available boot entries

Inspect the EFI loader entries to identify the one for the newly installed kernel.

```bash
# On the target
ls -lh /boot/efi/loader/entries/
```

> Entry filenames follow the pattern `<MACHINE_ID>-<KERNEL_VERSION>.conf`.
> Identify the entry that matches the kernel version you just installed before
> proceeding.

---

### 15. Back up the current boot entry

Back up the EFI loader entry for the newly installed kernel before editing it.

```bash
# On the target — substitute the actual filename from Step 14
sudo cp /boot/efi/loader/entries/<MACHINE_ID>-<KERNEL_VERSION>.conf \
        /boot/efi/loader/entries/<MACHINE_ID>-<KERNEL_VERSION>.conf.bak
```

---

### 16. Add the Glymur CRD device tree

Append the device tree line to the selected boot entry so the bootloader loads the
correct DTB for the Glymur CRD hardware.

```bash
# On the target — substitute the actual filename from Step 14
echo "devicetree /dtb/qcom/glymur-crd.dtb" | sudo tee -a \
  /boot/efi/loader/entries/<MACHINE_ID>-<KERNEL_VERSION>.conf
```

---

### 17. Verify the boot entry contents

Confirm the device tree line is present in the entry.

```bash
# On the target
cat /boot/efi/loader/entries/<MACHINE_ID>-<KERNEL_VERSION>.conf
```

**Expected line:**
```
devicetree /dtb/qcom/glymur-crd.dtb
```

---

### 18. Reboot the target

Restart the device to boot into the newly installed kernel.

```bash
# On the target
sync
sudo reboot
```

---

### 19. Verify the new kernel after reboot

Check the running kernel version and build information.

```bash
# On the target
uname -a
cat /proc/version
```

**✅ Success criteria:**
- The target reboots successfully
- `uname -a` reports the newly built kernel version
- The boot entry includes `devicetree /dtb/qcom/glymur-crd.dtb`

---

## Quick Validation Checklist

- [ ] Installed host build tools (Step 0)
- [ ] Pulled `kernel.config` from the running target
- [ ] Cloned the correct kernel branch
- [ ] Applied patches / changes (if any)
- [ ] Built `linux-*.deb` packages successfully
- [ ] Copied packages to `/tmp/` on the target
- [ ] Installed packages with `dpkg -i`
- [ ] Identified the correct EFI boot entry filename
- [ ] Backed up the EFI loader entry before editing
- [ ] Added the Glymur CRD DTB line to the boot entry
- [ ] Verified the new kernel after reboot

---

## References

- Source: [Build and Install Kernel .deb Glymur](https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur)
- Kernel repo: [qualcomm-linux/kernel](https://github.com/qualcomm-linux/kernel)
