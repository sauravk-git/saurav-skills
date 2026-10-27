---
name: glymur-kernel-deb
description: >
  Build a Linux kernel as Debian .deb packages and install them on a Glymur
  (Debian-based) target device. Accepts all meaningful inputs explicitly — patch
  file or directory, kernel branch, target connection (ADB or SSH), config source,
  DTB filename, and more — with smart auto-detection as fallback. Runs the full
  pipeline end-to-end: host-tool check, config pull, kernel clone, patch apply,
  cross-compile, package transfer, dpkg install, EFI boot-entry update, reboot.
source: https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur
license: Proprietary. Internal Qualcomm use only.
metadata:
  author: Saurav Kumar <sauravk@qti.qualcomm.com>
  version: "2.0"
  tags: [kernel, debian, glymur, arm64, cross-compile, deb, efi]
---

# glymur-kernel-deb Skill

End-to-end kernel `.deb` builder and installer for Glymur targets.

The agent collects all meaningful inputs from the user, then runs
`scripts/kernel_deb_builder.py` which handles the full pipeline automatically.

---

## Inputs the agent must collect

Gather these before invoking the script.  Items marked **auto** have smart
defaults — only ask if the user hasn't already provided them or if auto-detection
is likely to fail.

| # | Input | Flag | Default / auto-detect | When to ask explicitly |
|---|---|---|---|---|
| 1 | **Change / patch** | `--patch PATH` | — | Always — what are you building? |
| 2 | **Kernel branch** | `--branch BRANCH` | Auto-detected from target `uname -r` | When user specifies, or auto-detect fails |
| 3 | **Target transport** | `--transport adb\|ssh` | ADB if device connected, else SSH | When user mentions SSH or no ADB device |
| 4 | **Target IP** | `--target-ip IP` | — | Required when transport is SSH |
| 5 | **Config source** | `--config-from target\|file\|defconfig` | `target` (pull from running device) | When user has a local config or wants defconfig |
| 6 | **DTB filename** | `--dtb FILENAME` | `glymur-crd.dtb` | When user mentions a different board variant |
| 7 | **Install on target?** | `--install` / `--build-only` | Ask user | Always clarify intent |

Additional inputs to collect if the user mentions them:

| Input | Flag | Notes |
|---|---|---|
| Local config file | `--config-file PATH` | Required when `--config-from=file` |
| Local kernel tree | `--kernel-src PATH` | Use instead of `--patch` when user has a full tree |
| Cherry-pick commits | `--cherry-pick SHA [SHA …]` | Alternative to patch files |
| Custom version string | `--localversion STRING` | e.g. `-glymur-myfix` |
| SSH username | `--target-user USER` | Default: `debian` |
| Skip reboot | `--no-reboot` | When user wants to reboot manually |
| Build only | `--build-only` | No target needed; requires `--branch` and `--config-from file` |
| Install only | `--install-only` | Re-install from a previous build in `--workdir` |

---

## How to invoke the script

### Recommended: interactive mode (agent runs this when inputs are unclear)

```bash
python3 scripts/kernel_deb_builder.py --interactive
```

The script will prompt for every input with sensible defaults.

---

### Direct invocation (agent constructs the command from collected inputs)

**Most common — patch + ADB-connected target:**
```bash
python3 scripts/kernel_deb_builder.py \
    --patch <PATCH_FILE_OR_DIR> \
    --branch <BRANCH> \
    --transport adb \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Patch + SSH target:**
```bash
python3 scripts/kernel_deb_builder.py \
    --patch <PATCH_FILE_OR_DIR> \
    --branch <BRANCH> \
    --transport ssh --target-ip <IP> --target-user debian \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Local config file (no target needed for config):**
```bash
python3 scripts/kernel_deb_builder.py \
    --patch <PATCH_FILE_OR_DIR> \
    --branch <BRANCH> \
    --transport adb \
    --config-from file --config-file <PATH_TO_CONFIG> \
    --dtb glymur-crd.dtb \
    --install
```

**Local kernel tree with changes already applied:**
```bash
python3 scripts/kernel_deb_builder.py \
    --kernel-src <PATH_TO_KERNEL_TREE> \
    --branch <BRANCH> \
    --transport ssh --target-ip <IP> \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Build only — no target connected yet:**
```bash
python3 scripts/kernel_deb_builder.py \
    --patch <PATCH_FILE_OR_DIR> \
    --branch <BRANCH> \
    --config-from file --config-file <PATH_TO_CONFIG> \
    --build-only
```

**Install previously built packages onto a new target:**
```bash
python3 scripts/kernel_deb_builder.py \
    --install-only \
    --workdir ./kernel-build \
    --transport ssh --target-ip <IP> \
    --dtb glymur-crd.dtb
```

**Dry-run — see every command without executing:**
```bash
python3 scripts/kernel_deb_builder.py \
    --patch <PATCH_FILE_OR_DIR> \
    --branch <BRANCH> \
    --transport adb --config-from target \
    --dry-run --verbose
```

---

## What the script does automatically

The user never needs to know about these internals:

| Phase | What happens |
|---|---|
| **Host tools** | Checks for `gcc-aarch64-linux-gnu`, `make`, `dpkg-dev`, `bc`, `bison`, `flex`, `git`, `libssl-dev`, `libelf-dev`. Installs automatically with `--auto-install-tools`. |
| **Transport check** | Verifies ADB device state or SSH reachability before proceeding. |
| **Config pull** | Runs `zcat /proc/config.gz` on target, pulls file to host. Caches it; re-pull with `--force-config`. |
| **Branch detection** | Reads `uname -r` from target, matches against `qualcomm-linux/kernel` branches. Falls back to latest `qcom-next`. |
| **Clone** | Shallow-clones the kernel repo (`--depth 1` for speed). Reuses existing clone. `--fetch-latest` to reset to remote. |
| **Patch apply** | `git am --3way` for single file or sorted directory of `.patch` files. |
| **Configure** | Copies pulled config → `out-arm64/.config`, runs `olddefconfig`. Writes `localversion` file if `--localversion` set. |
| **Build** | `make -j$(nproc) bindeb-pkg ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-`. Packages land in parent of kernel source dir. |
| **Transfer** | ADB push or SCP of `linux-*.deb` to `/tmp/` on target. |
| **Install** | `sudo dpkg -i /tmp/linux-*.deb` on target. |
| **Boot entry** | Uses `dpkg-query` to find installed kernel version, locates matching EFI loader entry, backs it up, appends `devicetree /dtb/qcom/<DTB>` if not already present. Falls back to newest entry if version match fails. |
| **Reboot** | `sync && sudo reboot`. Skipped with `--no-reboot`. |

---

## All flags reference

```
Interactive:
  --interactive, -i     Guided prompts for all inputs

Change / source:
  --patch PATH          Patch file (.patch) or directory of .patch files
  --cherry-pick SHA…    Git commit SHA(s) to cherry-pick onto the branch
  --kernel-src PATH     Local kernel tree with changes already applied

Target:
  --transport adb|ssh   Connection transport (default: auto-detect)
  --target-ip IP        Target IP address (required for SSH)
  --target-user USER    SSH username (default: debian)
  --dtb FILENAME        DTB for EFI boot entry (default: glymur-crd.dtb)
  --no-reboot           Skip automatic reboot after install

Kernel config:
  --config-from         target|file|defconfig  (default: target)
  --config-file PATH    Local .config (required when --config-from=file)
  --force-config        Re-pull config from target even if cached
  --menuconfig          Open interactive menuconfig before building

Kernel source:
  --kernel-repo URL     Repo URL (default: qualcomm-linux/kernel)
  --branch BRANCH       Branch or tag (auto-detected if omitted)
  --clone-depth N       Git clone depth (default: 1)
  --fetch-latest        Reset existing clone to latest remote state

Build:
  --workdir PATH        Working directory (default: ./kernel-build)
  --jobs N              Parallel build jobs (default: nproc)
  --localversion STR    Append to kernel version string (e.g. -glymur-myfix)
  --auto-install-tools  Auto-install missing host tools via apt-get

Modes:
  --install             Build then install on target
  --build-only          Build packages, do not install
  --install-only        Skip build; install from --workdir onto target

Misc:
  --dry-run             Print every command without executing
  --verbose             Print commands as they run
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No ADB device found` | Device not connected or not authorised | Connect via USB, accept authorisation prompt on device, or use `--transport ssh --target-ip <IP>` |
| `Cannot SSH to …` | Wrong IP, user, or SSH key not set up | Verify with `ssh debian@<IP>` manually; check `~/.ssh/authorized_keys` on target |
| `Missing host tools` | Cross-compiler or build deps not installed | Add `--auto-install-tools` |
| `No .patch files found` | Wrong path or files not named `.patch` | Check path; files must end in `.patch` |
| `git am failed` | Patch doesn't apply cleanly to the branch | Try `--clone-depth 0` for full history, or rebase the patch |
| `Cannot determine kernel branch` | Target unreachable or no matching branch | Pass `--branch <BRANCH>` explicitly |
| `No EFI entry found for kernel` | Entry filename doesn't contain the version string | Script falls back to newest entry; check manually with `ls /boot/efi/loader/entries/` |
| Build takes too long | Default `nproc` may be low on some hosts | Pass `--jobs N` to tune |
| Want to rebuild without re-cloning | Clone already exists in `--workdir` | Script reuses it automatically; use `--fetch-latest` to update |

---

## References

- Source: [Build and Install Kernel .deb Glymur](https://qualcomm-confluence.atlassian.net/wiki/spaces/LinuxAudio/pages/3610140392/Build+and+Install+Kernel+.deb+Glymur)
- Kernel repo: [qualcomm-linux/kernel](https://github.com/qualcomm-linux/kernel)
