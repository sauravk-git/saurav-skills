#!/usr/bin/env python3
"""
kernel_deb_builder.py — Robust kernel .deb builder and installer for Glymur targets.

Accepts all meaningful inputs explicitly (with smart defaults / auto-detection).
Runs the full pipeline end-to-end: host-tool check, config pull, kernel clone,
patch application, cross-compile, package transfer, dpkg install, EFI boot-entry
update, and reboot.

Stdlib-only.  Python 3.8+.

Quick examples
--------------
  # Interactive — prompts for every input
  python3 kernel_deb_builder.py --interactive

  # Fully explicit
  python3 kernel_deb_builder.py \
      --patch my-fix.patch \
      --branch qcom-next-7.2-20260826 \
      --transport adb \
      --config-from target \
      --dtb glymur-crd.dtb \
      --install

  # SSH target, local config file, patch directory
  python3 kernel_deb_builder.py \
      --patch ./patches/ \
      --branch qcom-next-7.2-20260826 \
      --transport ssh --target-ip 192.168.1.100 --target-user debian \
      --config-from file --config-file ./my.config \
      --dtb glymur-crd.dtb \
      --install

  # Build only (no target needed)
  python3 kernel_deb_builder.py \
      --patch my-fix.patch \
      --branch qcom-next-7.2-20260826 \
      --config-from file --config-file ./my.config \
      --build-only

  # Install previously built packages onto a new target
  python3 kernel_deb_builder.py \
      --install-only \
      --workdir ./kernel-build \
      --transport ssh --target-ip 192.168.1.100 \
      --dtb glymur-crd.dtb

  # Dry-run — print every command, execute nothing
  python3 kernel_deb_builder.py \
      --patch my-fix.patch --branch qcom-next-7.2-20260826 \
      --transport adb --config-from target \
      --dry-run --verbose
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
_TTY = sys.stdout.isatty()

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _TTY else text

def section(msg):
    print(_c("1;34", f"\n━━━  {msg}  "))

def ok(msg):
    print(_c("1;32", f"  ✔  {msg}"))

def info(msg):
    print(f"     {msg}")

def warn(msg):
    print(_c("1;33", f"  ⚠  {msg}"), file=sys.stderr)

def die(msg):
    print(_c("1;31", f"  ✘  {msg}"), file=sys.stderr)
    sys.exit(1)

def ask(prompt, default=None):
    """Prompt the user for input, showing the default."""
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  ? {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default

def ask_yn(prompt, default=True):
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"  ? {prompt} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if not val:
        return default
    return val.startswith("y")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
VERBOSE = False
DRY_RUN = False

# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------

def run(cmd, *, cwd=None, check=True, capture=False, env=None, label=None,
        shell=False):
    display = cmd if shell else " ".join(str(c) for c in cmd)
    if VERBOSE or DRY_RUN:
        print(_c("2", f"     $ {display}"))
    if DRY_RUN:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    kw = dict(cwd=cwd, check=check, env=env or os.environ.copy(), shell=shell)
    if capture:
        kw["stdout"] = subprocess.PIPE
        kw["stderr"] = subprocess.PIPE
        kw["text"]   = True
    r = subprocess.run(cmd, **kw)
    if label and r.returncode == 0:
        ok(label)
    return r

def shell_out(cmd, *, cwd=None, default=""):
    """Run cmd (list or string), return stripped stdout or default on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                           shell=isinstance(cmd, str))
        return r.stdout.strip() if r.returncode == 0 else default
    except Exception:
        return default

# ---------------------------------------------------------------------------
# Target helpers
# ---------------------------------------------------------------------------

def _ssh_base(user, ip):
    return ["ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes", f"{user}@{ip}"]

def on_target(transport, user, ip, remote_cmd, *,
              check=True, capture=False, label=None):
    """Run a shell command on the target via SSH or ADB."""
    if transport == "ssh":
        cmd = _ssh_base(user, ip) + [remote_cmd]
    else:
        cmd = ["adb", "shell", remote_cmd]
    return run(cmd, check=check, capture=capture, label=label)

def push_to_target(transport, user, ip, local_glob, remote_dir):
    """Push files matching local_glob to remote_dir on the target."""
    files = sorted(glob.glob(local_glob))
    if not files:
        die(f"No files matched: {local_glob}")
    info(f"Pushing {len(files)} package(s) to {remote_dir} …")
    if transport == "ssh":
        run(["scp", "-o", "StrictHostKeyChecking=no"] + files +
            [f"{user}@{ip}:{remote_dir}"],
            label="Packages transferred via SCP")
    else:
        run(["adb", "push"] + files + [remote_dir],
            label="Packages transferred via ADB")

# ---------------------------------------------------------------------------
# Host tool management
# ---------------------------------------------------------------------------

# binary → apt package
REQUIRED_TOOLS = {
    "aarch64-linux-gnu-gcc": "gcc-aarch64-linux-gnu",
    "make":                  "make",
    "dpkg-buildpackage":     "dpkg-dev",
    "git":                   "git",
    "bc":                    "bc",
    "bison":                 "bison",
    "flex":                  "flex",
}
EXTRA_PKGS = ["libssl-dev", "libelf-dev", "rsync", "pahole", "dwarves"]

def ensure_host_tools(auto_install):
    section("Checking host build tools")
    missing_bins = [b for b in REQUIRED_TOOLS if not shutil.which(b)]
    if not missing_bins:
        ok("All required host tools present")
        return

    missing_pkgs = [REQUIRED_TOOLS[b] for b in missing_bins] + EXTRA_PKGS
    warn(f"Missing binaries: {', '.join(missing_bins)}")
    install_cmd = (
        f"sudo apt-get install -y --no-install-recommends "
        f"{' '.join(missing_pkgs)}"
    )

    if auto_install:
        info("Auto-installing …")
        run(install_cmd, shell=True, label="Host tools installed")
    else:
        info("Run to install:")
        info(f"  {install_cmd}")
        die("Missing host tools. Add --auto-install-tools to install automatically.")

# ---------------------------------------------------------------------------
# Transport detection
# ---------------------------------------------------------------------------

def detect_transport(args):
    """
    Determine (transport, user, ip) from args.
    - If --transport=ssh is set, --target-ip is required.
    - If --transport=adb is set, use ADB.
    - If --transport is not set, probe ADB first, then require --target-ip for SSH.
    Returns (transport, user, ip).  ip is None for ADB.
    """
    transport = args.transport  # 'adb', 'ssh', or None

    if transport == "ssh" or (transport is None and args.target_ip):
        if not args.target_ip:
            die("--target-ip is required when using SSH transport")
        user = args.target_user
        ip   = args.target_ip
        # Quick connectivity check
        section("Verifying SSH connectivity")
        r = subprocess.run(
            _ssh_base(user, ip) + ["echo ok"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            die(f"Cannot SSH to {user}@{ip}: {r.stderr.strip()}")
        ok(f"SSH reachable: {user}@{ip}")
        return "ssh", user, ip

    if transport == "adb" or transport is None:
        if not shutil.which("adb"):
            die("adb not found in PATH. Install android-tools-adb or pass --transport ssh --target-ip <IP>")
        section("Checking ADB connection")
        r = subprocess.run(["adb", "get-state"], capture_output=True, text=True)
        if r.returncode == 0 and "device" in r.stdout:
            ok("ADB device connected")
            return "adb", None, None
        else:
            die(
                "No ADB device found (state: " + r.stdout.strip() + ").\n"
                "     Connect a device via USB, or use --transport ssh --target-ip <IP>"
            )

    die(f"Unknown transport: {transport}")

# ---------------------------------------------------------------------------
# Config acquisition
# ---------------------------------------------------------------------------

def acquire_config(args, transport, user, ip, workdir):
    """
    Return Path to kernel.config on the host.
    config_from choices:
      target  — pull zcat /proc/config.gz from the connected target (default)
      file    — use a local file supplied via --config-file
      defconfig — use kernel's make defconfig (no file needed)
    """
    section("Acquiring kernel config")
    dest = workdir / "kernel.config"

    source = args.config_from  # 'target', 'file', 'defconfig'

    if source == "file":
        if not args.config_file:
            die("--config-file PATH is required when --config-from=file")
        src = Path(args.config_file)
        if not src.exists():
            die(f"Config file not found: {src}")
        if not DRY_RUN:
            shutil.copy2(src, dest)
        ok(f"Config copied from {src}")
        return dest

    if source == "defconfig":
        info("Will use 'make defconfig' — no config file needed")
        return None  # signal to configure phase

    # source == 'target' (default)
    if dest.exists() and not args.force_config:
        ok(f"Reusing cached config: {dest}  (pass --force-config to re-pull)")
        return dest

    tmp = "/data/local/tmp/kernel.config" if transport == "adb" else "/tmp/kernel.config"
    on_target(transport, user, ip,
              f"zcat /proc/config.gz > {tmp}",
              label="Config saved on target")

    if transport == "adb":
        run(["adb", "pull", tmp, str(dest)], label=f"Config pulled → {dest.name}")
    else:
        run(["scp", "-o", "StrictHostKeyChecking=no",
             f"{user}@{ip}:{tmp}", str(dest)],
            label=f"Config pulled → {dest.name}")

    return dest

# ---------------------------------------------------------------------------
# Branch resolution
# ---------------------------------------------------------------------------

KERNEL_REPO_DEFAULT = "https://github.com/qualcomm-linux/kernel.git"

def resolve_branch(args, transport, user, ip):
    """
    Return the kernel branch to build.
    Priority: --branch flag > auto-detect from target uname -r > latest qcom-next.
    """
    if args.branch:
        ok(f"Branch: {args.branch}  (explicit)")
        return args.branch

    section("Detecting kernel branch from target")
    uname = shell_out(
        ["adb", "shell", "uname -r"] if transport == "adb"
        else _ssh_base(user, ip) + ["uname -r"]
    )
    if not uname:
        warn("Could not read uname -r from target")
    else:
        info(f"Target running: {uname}")

    # Fetch available branches from the repo
    info(f"Fetching branch list from {args.kernel_repo} …")
    ls_raw = shell_out(["git", "ls-remote", "--heads", args.kernel_repo])
    if not ls_raw:
        warn("Could not reach kernel repo — cannot auto-detect branch")
        die("Pass --branch explicitly, e.g. --branch qcom-next-7.2-20260826")

    all_branches = [
        line.split("\t")[1].replace("refs/heads/", "")
        for line in ls_raw.splitlines()
        if "\t" in line
    ]

    # Try to match the running kernel version to a branch
    if uname:
        base = re.sub(r"[+~-].*$", "", uname).strip()   # e.g. "6.12.0"
        major_minor = ".".join(base.split(".")[:2])       # e.g. "6.12"
        candidates = [b for b in all_branches
                      if major_minor in b and "qcom" in b]
        if candidates:
            branch = sorted(candidates)[-1]  # latest matching
            ok(f"Auto-selected branch: {branch}  (matched {major_minor})")
            return branch

    # Fallback: latest qcom-next
    qcom_next = sorted([b for b in all_branches if "qcom-next" in b], reverse=True)
    if qcom_next:
        branch = qcom_next[0]
        warn(f"Could not match running kernel — using latest qcom-next: {branch}")
        return branch

    die(
        "Cannot determine kernel branch automatically.\n"
        "     Pass --branch explicitly, e.g.:\n"
        "       --branch qcom-next-7.2-20260826"
    )

# ---------------------------------------------------------------------------
# Kernel source
# ---------------------------------------------------------------------------

def prepare_kernel_source(args, workdir):
    """Clone or reuse kernel source. Returns Path to kernel dir."""
    section("Preparing kernel source")

    if args.kernel_src:
        src = Path(args.kernel_src).resolve()
        if not src.exists():
            die(f"--kernel-src path not found: {src}")
        ok(f"Using local kernel tree: {src}")
        return src

    kernel_dir = workdir / "kernel"
    if kernel_dir.exists():
        ok(f"Reusing existing clone: {kernel_dir}")
        # Optionally fetch latest
        if args.fetch_latest:
            info("Fetching latest changes …")
            run(["git", "fetch", "--depth", str(args.clone_depth),
                 "origin", args.branch],
                cwd=str(kernel_dir), label="Fetched latest")
            run(["git", "reset", "--hard", f"origin/{args.branch}"],
                cwd=str(kernel_dir), label="Reset to latest")
        return kernel_dir

    info(f"Cloning {args.kernel_repo}  branch={args.branch} …")
    run(["git", "clone",
         "--depth", str(args.clone_depth),
         "--branch", args.branch,
         args.kernel_repo,
         str(kernel_dir)],
        label=f"Cloned {args.branch}")
    return kernel_dir

# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------

def apply_patches(args, kernel_dir):
    """Apply --patch (file or directory) or --cherry-pick commits."""
    if not args.patch and not args.cherry_pick:
        info("No patches supplied — building tree as-is")
        return

    section("Applying changes")

    if args.patch:
        patch_path = Path(args.patch).resolve()
        if not patch_path.exists():
            die(f"Patch path not found: {patch_path}")

        if patch_path.is_dir():
            patch_files = sorted(patch_path.glob("*.patch"))
            if not patch_files:
                die(f"No .patch files found in {patch_path}")
            info(f"Applying {len(patch_files)} patch(es) from {patch_path} …")
            for pf in patch_files:
                run(["git", "am", "--3way", str(pf)],
                    cwd=str(kernel_dir), label=f"Applied {pf.name}")
        else:
            run(["git", "am", "--3way", str(patch_path)],
                cwd=str(kernel_dir), label=f"Applied {patch_path.name}")

    if args.cherry_pick:
        for commit in args.cherry_pick:
            run(["git", "cherry-pick", "-x", commit],
                cwd=str(kernel_dir), label=f"Cherry-picked {commit}")

# ---------------------------------------------------------------------------
# Kernel configuration
# ---------------------------------------------------------------------------

def configure_kernel(args, kernel_dir, config_path):
    """Set up .config and run olddefconfig/defconfig. Returns out_dir Path."""
    section("Configuring kernel")
    out_dir = kernel_dir / "out-arm64"
    build_env = {**os.environ,
                 "ARCH": "arm64",
                 "CROSS_COMPILE": "aarch64-linux-gnu-"}

    if not DRY_RUN:
        out_dir.mkdir(parents=True, exist_ok=True)

    if config_path is None:
        # defconfig
        run(["make", f"O={out_dir}", "defconfig"],
            cwd=str(kernel_dir), env=build_env, label="defconfig applied")
    else:
        if not DRY_RUN:
            shutil.copy2(config_path, out_dir / ".config")
        ok(f"Seeded .config from {config_path.name}")
        run(["make", f"O={out_dir}", "olddefconfig"],
            cwd=str(kernel_dir), env=build_env, label="olddefconfig done")

    if args.localversion:
        # Append a custom local version string (e.g. "-glymur-myfix")
        lv_file = out_dir / "localversion"
        if not DRY_RUN:
            lv_file.write_text(args.localversion + "\n")
        ok(f"LOCALVERSION set to: {args.localversion}")

    if args.menuconfig:
        section("menuconfig  (interactive — make your changes, then save & exit)")
        run(["make", f"O={out_dir}", "menuconfig"],
            cwd=str(kernel_dir), env=build_env)

    return out_dir

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_debs(args, kernel_dir, out_dir):
    """Cross-compile and produce .deb packages. Returns deb_dir Path."""
    section("Building Debian kernel packages  (may take 30–90 min …)")
    jobs = str(args.jobs or os.cpu_count() or 4)
    build_env = {**os.environ,
                 "ARCH": "arm64",
                 "CROSS_COMPILE": "aarch64-linux-gnu-"}
    if args.localversion:
        build_env["LOCALVERSION"] = args.localversion

    info(f"Jobs: {jobs}  |  Out: {out_dir}")
    run(["make", f"O={out_dir}", f"-j{jobs}", "bindeb-pkg"],
        cwd=str(kernel_dir), env=build_env, label="bindeb-pkg complete")

    # bindeb-pkg writes .deb files one level above the kernel source dir
    deb_dir = kernel_dir.parent
    debs = sorted(glob.glob(str(deb_dir / "linux-*.deb")))
    if not DRY_RUN and not debs:
        die(f"No linux-*.deb files found in {deb_dir} after build")
    for d in debs:
        ok(f"Package: {Path(d).name}")
    return deb_dir

# ---------------------------------------------------------------------------
# Install on target
# ---------------------------------------------------------------------------

def install_on_target(args, transport, user, ip, deb_dir):
    """Transfer, install, update boot entry, reboot."""
    section("Transferring packages to target")
    push_to_target(transport, user, ip, str(deb_dir / "linux-*.deb"), "/tmp/")

    section("Installing kernel packages on target")
    on_target(transport, user, ip,
              "sudo dpkg -i /tmp/linux-*.deb",
              label="dpkg install complete")

    section("Updating EFI boot entry")
    _update_boot_entry(transport, user, ip, args.dtb)

    section("Rebooting target")
    if args.no_reboot:
        info("--no-reboot set — skipping. Run on target:  sync && sudo reboot")
    else:
        on_target(transport, user, ip, "sync && sudo reboot", check=False)
        ok("Reboot triggered — wait for device, then verify:")
        info("  uname -a")
        info("  cat /proc/version")

# ---------------------------------------------------------------------------
# EFI boot entry update
# ---------------------------------------------------------------------------

def _update_boot_entry(transport, user, ip, dtb):
    if DRY_RUN:
        ok(f"[DRY] Would add 'devicetree /dtb/qcom/{dtb}' to EFI boot entry")
        return

    # 1. Find the newly installed kernel version via dpkg-query (more reliable)
    r = on_target(transport, user, ip,
                  "dpkg-query -W -f='${Package}\\n' 'linux-image-*' "
                  "| sort -V | tail -1",
                  capture=True, check=False)
    pkg = (r.stdout or "").strip()
    kver = pkg.replace("linux-image-", "").strip()

    if not kver:
        warn("Could not determine installed kernel version via dpkg-query")
        _boot_entry_manual_hint(dtb)
        return

    info(f"Installed kernel package: {pkg}  (version: {kver})")

    # 2. Find the matching EFI loader entry
    r2 = on_target(transport, user, ip,
                   f"ls /boot/efi/loader/entries/ 2>/dev/null | grep -- '{kver}' | head -1",
                   capture=True, check=False)
    entry_file = (r2.stdout or "").strip()

    if not entry_file:
        # Fallback: find the newest .conf entry
        r3 = on_target(transport, user, ip,
                       "ls -t /boot/efi/loader/entries/*.conf 2>/dev/null | head -1",
                       capture=True, check=False)
        newest = (r3.stdout or "").strip()
        if newest:
            entry_file = Path(newest).name
            warn(f"No entry matched kernel version — using newest entry: {entry_file}")
        else:
            warn("No EFI loader entries found — boot entry not updated")
            _boot_entry_manual_hint(dtb)
            return

    entry = f"/boot/efi/loader/entries/{entry_file}"
    info(f"Boot entry: {entry}")

    # 3. Backup
    on_target(transport, user, ip,
              f"sudo cp {entry} {entry}.bak",
              label="Boot entry backed up")

    # 4. Add DTB line only if not already present
    chk = on_target(transport, user, ip,
                    f"grep -q 'devicetree' {entry}", check=False)
    if chk.returncode == 0:
        ok("devicetree line already present — no change needed")
    else:
        on_target(transport, user, ip,
                  f'echo "devicetree /dtb/qcom/{dtb}" | sudo tee -a {entry}',
                  label=f"Added: devicetree /dtb/qcom/{dtb}")

    # 5. Verify
    on_target(transport, user, ip, f"grep devicetree {entry}", check=False)

def _boot_entry_manual_hint(dtb):
    info("To update the boot entry manually on the target:")
    info("  ls /boot/efi/loader/entries/")
    info("  sudo cp /boot/efi/loader/entries/<ENTRY>.conf \\")
    info("          /boot/efi/loader/entries/<ENTRY>.conf.bak")
    info(f'  echo "devicetree /dtb/qcom/{dtb}" | \\')
    info("      sudo tee -a /boot/efi/loader/entries/<ENTRY>.conf")

# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_collect(args):
    """
    Walk the user through all inputs conversationally.
    Fills in args in-place.  Only called when --interactive is set.
    """
    print(_c("1;34", "\n  glymur-kernel-deb — interactive setup\n"))

    # --- Change / source ---
    print(_c("1", "  [1/7] Change / kernel source"))
    info("Options:")
    info("  patch      — apply a .patch file or directory of patches")
    info("  kernel-src — use a local kernel tree with changes already applied")
    info("  none       — build a branch as-is (no changes)")
    choice = ask("Change type", default="patch")

    if choice == "patch":
        args.patch = ask("Path to .patch file or directory of patches")
        args.kernel_src = None
    elif choice == "kernel-src":
        args.kernel_src = ask("Path to local kernel source tree")
        args.patch = None
    else:
        args.patch = None
        args.kernel_src = None

    args.cherry_pick = None

    # --- Branch ---
    print(_c("1", "\n  [2/7] Kernel branch"))
    info("Leave blank to auto-detect from the target's running kernel.")
    info("Example: qcom-next-7.2-20260826")
    args.branch = ask("Branch", default="") or None

    # --- Target connection ---
    print(_c("1", "\n  [3/7] Target connection"))
    info("Options:  adb  (USB-connected device)  |  ssh  (network)")
    transport = ask("Transport", default="adb").lower()
    args.transport = transport if transport in ("adb", "ssh") else "adb"

    if args.transport == "ssh":
        args.target_ip   = ask("Target IP address")
        args.target_user = ask("SSH username", default="debian")
    else:
        args.target_ip   = None
        args.target_user = "debian"

    # --- Config source ---
    print(_c("1", "\n  [4/7] Kernel config source"))
    info("Options:")
    info("  target    — pull /proc/config.gz from the connected target (recommended)")
    info("  file      — use a local .config file")
    info("  defconfig — use the kernel's default config for arm64")
    cfg_src = ask("Config source", default="target").lower()
    args.config_from = cfg_src if cfg_src in ("target", "file", "defconfig") else "target"

    if args.config_from == "file":
        args.config_file = ask("Path to local .config file")
    else:
        args.config_file = None

    # --- DTB ---
    print(_c("1", "\n  [5/7] Device tree blob (DTB)"))
    info("The DTB filename added to the EFI boot entry.")
    info("Default for Glymur CRD: glymur-crd.dtb")
    args.dtb = ask("DTB filename", default="glymur-crd.dtb")

    # --- Install ---
    print(_c("1", "\n  [6/7] Install on target"))
    args.install      = ask_yn("Install packages on target after build?", default=True)
    args.build_only   = not args.install
    args.install_only = False
    if args.install:
        args.no_reboot = not ask_yn("Reboot target automatically after install?", default=True)
    else:
        args.no_reboot = True

    # --- Advanced ---
    print(_c("1", "\n  [7/7] Advanced options (press Enter to skip each)"))
    lv = ask("Custom LOCALVERSION string (e.g. -glymur-myfix)", default="")
    args.localversion = lv if lv else None
    args.menuconfig   = ask_yn("Open menuconfig before building?", default=False)
    args.auto_install_tools = ask_yn("Auto-install missing host tools if needed?", default=True)

    print()
    info("─" * 60)
    info("Summary:")
    info(f"  Change      : {args.patch or args.kernel_src or '(none)'}")
    info(f"  Branch      : {args.branch or '(auto-detect)'}")
    info(f"  Transport   : {args.transport}"
         + (f" → {args.target_user}@{args.target_ip}" if args.transport == "ssh" else ""))
    info(f"  Config from : {args.config_from}"
         + (f" ({args.config_file})" if args.config_from == "file" else ""))
    info(f"  DTB         : {args.dtb}")
    info(f"  Install     : {'yes' if args.install else 'no'}")
    info(f"  Reboot      : {'yes' if not args.no_reboot else 'no'}")
    if args.localversion:
        info(f"  LOCALVERSION: {args.localversion}")
    info("─" * 60)
    print()

    if not ask_yn("Proceed?", default=True):
        info("Aborted.")
        sys.exit(0)

# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="kernel_deb_builder.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            Robust kernel .deb builder and installer for Glymur targets.

            All inputs are explicit with smart defaults.
            Use --interactive to be guided through every option.
        """),
        epilog=textwrap.dedent("""\
            Examples:
              # Interactive — guided through all inputs
              python3 kernel_deb_builder.py --interactive

              # Fully explicit, ADB target
              python3 kernel_deb_builder.py \\
                  --patch my-fix.patch \\
                  --branch qcom-next-7.2-20260826 \\
                  --transport adb \\
                  --config-from target \\
                  --dtb glymur-crd.dtb \\
                  --install

              # SSH target, local config, patch directory
              python3 kernel_deb_builder.py \\
                  --patch ./patches/ \\
                  --branch qcom-next-7.2-20260826 \\
                  --transport ssh --target-ip 192.168.1.100 \\
                  --config-from file --config-file ./my.config \\
                  --dtb glymur-crd.dtb \\
                  --install

              # Build only (no target)
              python3 kernel_deb_builder.py \\
                  --patch my-fix.patch \\
                  --branch qcom-next-7.2-20260826 \\
                  --config-from file --config-file ./my.config \\
                  --build-only

              # Install previously built packages onto a target
              python3 kernel_deb_builder.py \\
                  --install-only \\
                  --workdir ./kernel-build \\
                  --transport ssh --target-ip 192.168.1.100 \\
                  --dtb glymur-crd.dtb

              # Dry-run
              python3 kernel_deb_builder.py \\
                  --patch my-fix.patch \\
                  --branch qcom-next-7.2-20260826 \\
                  --transport adb --config-from target \\
                  --dry-run --verbose
        """),
    )

    p.add_argument("--interactive", "-i", action="store_true",
                   help="Interactive mode — guided prompts for all inputs")

    # --- Change / source ---
    chg = p.add_argument_group("Change / source")
    chg.add_argument("--patch", metavar="PATH",
                     help="Patch file (.patch) or directory of .patch files to apply")
    chg.add_argument("--cherry-pick", metavar="SHA", nargs="+",
                     help="One or more git commit SHAs to cherry-pick onto the branch")
    chg.add_argument("--kernel-src", metavar="PATH",
                     help="Local kernel source tree with changes already applied "
                          "(skips clone; use with --build-only or --install)")

    # --- Target ---
    tgt = p.add_argument_group("Target")
    tgt.add_argument("--transport", choices=["adb", "ssh"],
                     help="Connection transport (default: auto-detect ADB, else SSH)")
    tgt.add_argument("--target-ip", metavar="IP",
                     help="Target IP address (required for SSH)")
    tgt.add_argument("--target-user", default="debian", metavar="USER",
                     help="SSH username on target (default: debian)")
    tgt.add_argument("--dtb", default="glymur-crd.dtb", metavar="FILENAME",
                     help="DTB filename for EFI boot entry (default: glymur-crd.dtb)")
    tgt.add_argument("--no-reboot", action="store_true",
                     help="Skip automatic reboot after install")

    # --- Config ---
    cfg = p.add_argument_group("Kernel config")
    cfg.add_argument("--config-from",
                     choices=["target", "file", "defconfig"],
                     default="target",
                     help="Config source: pull from target (default), local file, or defconfig")
    cfg.add_argument("--config-file", metavar="PATH",
                     help="Local .config file path (required when --config-from=file)")
    cfg.add_argument("--force-config", action="store_true",
                     help="Re-pull config from target even if a cached copy exists")
    cfg.add_argument("--menuconfig", action="store_true",
                     help="Open interactive menuconfig before building")

    # --- Kernel source ---
    src = p.add_argument_group("Kernel source")
    src.add_argument("--kernel-repo", default=KERNEL_REPO_DEFAULT, metavar="URL",
                     help=f"Kernel git repo URL (default: qualcomm-linux/kernel)")
    src.add_argument("--branch", metavar="BRANCH",
                     help="Branch or tag to build (auto-detected from target if omitted)")
    src.add_argument("--clone-depth", type=int, default=1, metavar="N",
                     help="Git clone depth (default: 1; use 0 for full history)")
    src.add_argument("--fetch-latest", action="store_true",
                     help="Fetch and reset an existing clone to the latest remote state")

    # --- Build ---
    bld = p.add_argument_group("Build")
    bld.add_argument("--workdir", default="./kernel-build", metavar="PATH",
                     help="Working directory for clone and build artefacts (default: ./kernel-build)")
    bld.add_argument("--jobs", type=int, metavar="N",
                     help="Parallel build jobs (default: nproc)")
    bld.add_argument("--localversion", metavar="STRING",
                     help="Append a custom string to the kernel version "
                          "(e.g. -glymur-myfix → 6.12.0-glymur-myfix)")
    bld.add_argument("--auto-install-tools", action="store_true",
                     help="Auto-install missing host build tools via apt-get")

    # --- Modes ---
    mode = p.add_argument_group("Modes")
    mode.add_argument("--install", action="store_true",
                      help="Transfer and install packages on target after building")
    mode.add_argument("--build-only", action="store_true",
                      help="Build packages but do not install on target")
    mode.add_argument("--install-only", action="store_true",
                      help="Skip build; install packages from --workdir onto target")

    # --- Misc ---
    misc = p.add_argument_group("Misc")
    misc.add_argument("--dry-run", action="store_true",
                      help="Print every command without executing")
    misc.add_argument("--verbose", action="store_true",
                      help="Print commands as they run")

    return p

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    global VERBOSE, DRY_RUN
    VERBOSE = args.verbose
    DRY_RUN = args.dry_run

    if DRY_RUN:
        warn("DRY-RUN mode — no commands will be executed")

    # Interactive mode fills in all args before we proceed
    if args.interactive:
        interactive_collect(args)

    # Validate mode flags
    modes = [args.build_only, args.install_only,
             getattr(args, "install", False)]
    if sum(bool(m) for m in modes) > 1:
        die("--build-only, --install-only, and --install are mutually exclusive")

    workdir = Path(args.workdir).resolve()
    if not DRY_RUN:
        workdir.mkdir(parents=True, exist_ok=True)

    info(f"Work directory : {workdir}")

    # ── 1. Host tools ────────────────────────────────────────────────────────
    ensure_host_tools(args.auto_install_tools)

    # ── install-only short-circuit ───────────────────────────────────────────
    if args.install_only:
        transport, user, ip = detect_transport(args)
        deb_dir = workdir / "kernel"
        # debs land in workdir (parent of kernel/)
        deb_dir = workdir
        debs = sorted(glob.glob(str(workdir / "linux-*.deb")))
        if not DRY_RUN and not debs:
            die(f"No linux-*.deb found in {workdir}. Run a build first.")
        install_on_target(args, transport, user, ip, workdir)
        section("All done ✔")
        return

    # ── 2. Target connection (skip for build-only) ───────────────────────────
    if args.build_only:
        transport, user, ip = None, None, None
        if not args.branch:
            die("--branch is required with --build-only (no target to detect from)")
        if args.config_from == "target":
            die("--config-from=target requires a connected target. "
                "Use --config-from=file or --config-from=defconfig with --build-only")
    else:
        transport, user, ip = detect_transport(args)

    # ── 3. Config ────────────────────────────────────────────────────────────
    config_path = acquire_config(args, transport, user, ip, workdir)

    # ── 4. Branch ────────────────────────────────────────────────────────────
    if not args.build_only:
        args.branch = resolve_branch(args, transport, user, ip)
    section(f"Branch: {args.branch}")

    # ── 5. Kernel source ─────────────────────────────────────────────────────
    kernel_dir = prepare_kernel_source(args, workdir)

    # ── 6. Apply changes ─────────────────────────────────────────────────────
    apply_patches(args, kernel_dir)

    # ── 7. Configure ─────────────────────────────────────────────────────────
    out_dir = configure_kernel(args, kernel_dir, config_path)

    # ── 8. Build ─────────────────────────────────────────────────────────────
    deb_dir = build_debs(args, kernel_dir, out_dir)

    section("Build complete")
    ok(f"Packages in: {deb_dir}/")

    # ── 9. Install ───────────────────────────────────────────────────────────
    if args.build_only:
        info("--build-only: packages ready, not installed on target")
        info("To install later:")
        info(f"  python3 kernel_deb_builder.py --install-only \\")
        info(f"      --workdir {workdir} \\")
        info(f"      --transport adb   # or --transport ssh --target-ip <IP>")
    else:
        install_on_target(args, transport, user, ip, deb_dir)

    section("All done ✔")

if __name__ == "__main__":
    main()
