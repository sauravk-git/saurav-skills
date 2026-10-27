# saurav-skills

Personal QGenie / Codex skill collection by [Saurav Kumar](https://github.com/sauravk-git).

These skills extend the QGenie CLI agent with specialised, domain-specific workflows
for Qualcomm platform and AudioReach development.

---

## Available Skills

| Skill | Description |
|---|---|
| [debian-packager](skills/debian-packager/SKILL.md) | End-to-end Debian packaging skeleton generator for QCOM/AudioReach components — supports Yocto recipes, remote URLs, and local source trees |
| [rpm-packager](skills/rpm-packager/SKILL.md) | End-to-end RPM packaging skeleton generator for CentOS Stream 10 (aarch64) — generates spec files, dist-git sources, and GitHub Actions CI/release workflows |
| [orbit-cr-report](skills/orbit-cr-report/SKILL.md) | Fetch a saved Orbit query, group CRs by target product, sort by age, and display Software Image Status with colour coding — supports table, markdown, JSON, and CSV output |
| [pipewire-enhancement](skills/pipewire-enhancement/SKILL.md) | PipeWire Enhancement Engineer for Qualcomm QLI/AudioReach/PAL/ADSP — classifies requests across 13 enhancement types and produces structured 10-section implementation proposals |
| [glymur-kernel-deb](skills/glymur-kernel-deb/SKILL.md) | End-to-end kernel `.deb` builder and installer for Glymur targets — accepts patch, branch, transport, config source, and DTB; runs the full pipeline automatically |

---

## Quick Install

### From inside QGenie CLI

```
Install the <skill-name> skill from sauravk-git/saurav-skills
```

The agent uses the built-in `skill-installer` skill to fetch and install it automatically.

Examples:
```
Install the glymur-kernel-deb skill from sauravk-git/saurav-skills
Install the debian-packager skill from sauravk-git/saurav-skills
Install the orbit-cr-report skill from sauravk-git/saurav-skills
```

### Manual install (any skill)

```bash
# Clone this repo
git clone https://github.com/sauravk-git/saurav-skills.git

# Copy the skill you want into your QGenie skills directory
cp -r saurav-skills/skills/<skill-name> \
      ~/.config/qgenie-cli/agent/skills/

# Restart QGenie to pick up the new skill
```

### Using the installer script directly

```bash
python3 ~/.config/qgenie-cli/agent/skills/.system/skill-installer/scripts/install-skill-from-github.py \
    --repo sauravk-git/saurav-skills \
    --path skills/<skill-name>
```

Examples:
```bash
# glymur-kernel-deb
python3 ~/.config/qgenie-cli/agent/skills/.system/skill-installer/scripts/install-skill-from-github.py \
    --repo sauravk-git/saurav-skills --path skills/glymur-kernel-deb

# debian-packager
python3 ~/.config/qgenie-cli/agent/skills/.system/skill-installer/scripts/install-skill-from-github.py \
    --repo sauravk-git/saurav-skills --path skills/debian-packager

# orbit-cr-report
python3 ~/.config/qgenie-cli/agent/skills/.system/skill-installer/scripts/install-skill-from-github.py \
    --repo sauravk-git/saurav-skills --path skills/orbit-cr-report
```

---

## glymur-kernel-deb Skill

### What it does

End-to-end kernel `.deb` builder and installer for Glymur (Debian-based) targets.
Accepts all meaningful inputs explicitly — patch file or directory, kernel branch,
target connection (ADB or SSH), config source, DTB filename — with smart
auto-detection as fallback for each. Runs the full pipeline without any manual steps.

### How to use with QGenie

Tell the agent what you want to build. It collects any missing inputs and runs
everything automatically:

```
Apply my-fix.patch to the Glymur kernel and install it on my ADB-connected device
Build kernel branch qcom-next-7.2-20260826 with ./patches/ and install via SSH to 192.168.1.100
Build only — no target connected yet, use my local config at ./my.config
```

### Direct script usage

**Interactive — guided through every input:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py --interactive
```

**Patch + ADB-connected target (most common):**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --patch my-fix.patch \
    --branch qcom-next-7.2-20260826 \
    --transport adb \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Patch + SSH target:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --patch ./patches/ \
    --branch qcom-next-7.2-20260826 \
    --transport ssh --target-ip 192.168.1.100 --target-user debian \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Local config file, build only (no target needed):**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --patch my-fix.patch \
    --branch qcom-next-7.2-20260826 \
    --config-from file --config-file ./my.config \
    --build-only
```

**Local kernel tree with changes already applied:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --kernel-src ./my-kernel-tree \
    --transport ssh --target-ip 192.168.1.100 \
    --config-from target \
    --dtb glymur-crd.dtb \
    --install
```

**Cherry-pick commits instead of a patch file:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --cherry-pick abc1234 def5678 \
    --branch qcom-next-7.2-20260826 \
    --transport adb --config-from target \
    --install
```

**Install previously built packages onto a new target:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --install-only \
    --workdir ./kernel-build \
    --transport ssh --target-ip 192.168.1.100 \
    --dtb glymur-crd.dtb
```

**Dry-run — see every command without executing:**
```bash
python3 skills/glymur-kernel-deb/scripts/kernel_deb_builder.py \
    --patch my-fix.patch \
    --branch qcom-next-7.2-20260826 \
    --transport adb --config-from target \
    --dry-run --verbose
```

### All flags

```
Interactive:
  --interactive, -i       Guided prompts for all inputs

Change / source:
  --patch PATH            Patch file (.patch) or directory of .patch files
  --cherry-pick SHA…      Git commit SHA(s) to cherry-pick onto the branch
  --kernel-src PATH       Local kernel tree with changes already applied

Target:
  --transport adb|ssh     Connection transport (default: auto-detect)
  --target-ip IP          Target IP address (required for SSH)
  --target-user USER      SSH username (default: debian)
  --dtb FILENAME          DTB for EFI boot entry (default: glymur-crd.dtb)
  --no-reboot             Skip automatic reboot after install

Kernel config:
  --config-from           target|file|defconfig  (default: target)
  --config-file PATH      Local .config (required when --config-from=file)
  --force-config          Re-pull config from target even if cached
  --menuconfig            Open interactive menuconfig before building

Kernel source:
  --kernel-repo URL       Repo URL (default: qualcomm-linux/kernel)
  --branch BRANCH         Branch or tag (auto-detected from target if omitted)
  --clone-depth N         Git clone depth (default: 1)
  --fetch-latest          Reset existing clone to latest remote state

Build:
  --workdir PATH          Working directory (default: ./kernel-build)
  --jobs N                Parallel build jobs (default: nproc)
  --localversion STRING   Append to kernel version (e.g. -glymur-myfix)
  --auto-install-tools    Auto-install missing host tools via apt-get

Modes:
  --install               Build then install on target
  --build-only            Build packages, do not install
  --install-only          Skip build; install from --workdir onto target

Misc:
  --dry-run               Print every command without executing
  --verbose               Print commands as they run
```

### What gets automated

| Phase | What the script does |
|---|---|
| Host tools | Checks for `gcc-aarch64-linux-gnu`, `make`, `dpkg-dev`, `bc`, `bison`, `flex`, `git`, `libssl-dev`, `libelf-dev`. Installs with `--auto-install-tools`. |
| Transport check | Verifies ADB device state or SSH reachability before proceeding |
| Config pull | `zcat /proc/config.gz` from target; cached — re-pull with `--force-config` |
| Branch detect | Reads `uname -r` from target, matches against `qualcomm-linux/kernel` branches |
| Clone | Shallow-clones kernel repo; reuses existing clone automatically |
| Patch apply | `git am --3way` for single file or sorted directory of `.patch` files |
| Configure | Copies config → `out-arm64/.config`, runs `olddefconfig` |
| Build | `make -j$(nproc) bindeb-pkg ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-` |
| Transfer | ADB push or SCP of `linux-*.deb` to `/tmp/` on target |
| Install | `sudo dpkg -i /tmp/linux-*.deb` |
| Boot entry | Uses `dpkg-query` to find installed kernel, locates EFI entry, backs it up, appends `devicetree /dtb/qcom/<DTB>` |
| Reboot | `sync && sudo reboot` (skip with `--no-reboot`) |

### Troubleshooting

| Symptom | Fix |
|---|---|
| `No ADB device found` | Connect via USB and accept authorisation, or use `--transport ssh --target-ip <IP>` |
| `Cannot SSH to …` | Verify with `ssh debian@<IP>` manually; check SSH keys |
| `Missing host tools` | Add `--auto-install-tools` |
| `No .patch files found` | Files must end in `.patch`; check the path |
| `git am failed` | Try `--clone-depth 0` for full history, or rebase the patch |
| `Cannot determine kernel branch` | Pass `--branch <BRANCH>` explicitly |
| `No EFI entry found` | Script falls back to newest entry; check manually with `ls /boot/efi/loader/entries/` |

### Skill structure

```
skills/glymur-kernel-deb/
├── SKILL.md
└── scripts/
    └── kernel_deb_builder.py   # Main script (stdlib-only, Python 3.8+)
```

---

## debian-packager Skill

### What it does

Generates a production-ready `debian/` directory tree, `build.sh`, `gbp.conf`,
`watch` file, and `debusine.yaml` from three input modes:

| Input | Example |
|---|---|
| Yocto `.bb` recipe | `audioreach-pal_1.0.2.bb` |
| Remote git or tarball URL | `https://github.com/AudioReach/audioreach-pal` |
| Local source tree or tarball | `./audioreach-pal/` or `./audioreach-audio-utils_1.0.0_arm64.tar.gz` |

Automatically detects and handles three package types:

- **source/userspace** — standard `debuild` flow with cmake/autotools/meson support
- **prebuilt tarball** — `uscan`-based fetch with SHA-256 verification
- **DKMS kernel module** — full DKMS packaging with maintainer scripts and triggers

### Usage

```bash
# From a Yocto recipe
python3 skills/debian-packager/scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --output /tmp/audioreach-pal-deb

# From a git URL
python3 skills/debian-packager/scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --output /tmp/audioreach-pipewire-plugin-deb

# From a prebuilt tarball URL
python3 skills/debian-packager/scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-audio-utils/archive/refs/tags/v1.0.0.tar.gz \
    --output /tmp/audioreach-audio-utils-deb

# From a local DKMS driver tree
python3 skills/debian-packager/scripts/debian_packager.py \
    --path ./audioreach-kernel \
    --dkms \
    --output /tmp/audioreach-kernel-deb

# Dry-run preview (no files written)
python3 skills/debian-packager/scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --dry-run --verbose
```

### Generated output

```
debian-out/
├── debian/
│   ├── changelog          # DEP-3 format, target: trixie
│   ├── compat             # debhelper compat 13
│   ├── control            # source + binary stanzas
│   ├── copyright          # DEP-5 machine-readable
│   ├── gbp.conf           # git-buildpackage config
│   ├── rules              # dh $@ with overrides
│   ├── source/format      # "3.0 (quilt)"
│   ├── watch              # uscan watch file
│   ├── <pkg>.install      # (split packages) file lists
│   ├── <pkg>-dkms.dkms    # (DKMS) dkms.conf wrapper
│   ├── <pkg>-dkms.postinst# (DKMS) maintainer script
│   └── <pkg>-dkms.prerm   # (DKMS) maintainer script
├── build.sh               # one-shot build helper
└── debusine.yaml          # Debusine CI hints
```

### Versioning

Versioning is **fully automatic** — no flags needed for normal use.

| Input | Upstream version source | Debian revision logic |
|---|---|---|
| `--url` (GitHub/GitLab) | GitHub/GitLab API → latest semver tag | `1` first time; auto-increments on re-run |
| `--url` (tarball) | Parsed from filename | same |
| `--recipe` | `PV` field; `git`/AUTOINC PV → `<base>+git<YYYYMMDD>` | same |
| `--path` (git clone) | `git describe --tags`; dirty tree → `<ver>+git<YYYYMMDD>` | same |
| `--path` (non-git) | `VERSION` / `version.txt` file | same |
| Fallback | `0+git<YYYYMMDD>` | same |

```
first run   → 1.0.2-1
second run  → 1.0.2-2   (re-packaging, upstream unchanged)
new upstream→ 1.0.3-1   (upstream changed, revision resets)
```

Override when needed:
```bash
python3 skills/debian-packager/scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --upstream-version 1.0.3 --debian-revision 0~rc1 \
    --output /tmp/audioreach-pipewire-plugin-deb
```

### Build the package

```bash
cd /tmp/audioreach-pal-deb
bash build.sh

# Validate
lintian ../*.deb
uscan --no-download --verbose
dpkg-buildpackage --dry-run -b --no-sign
```

### Yocto field mapping

| Yocto field | Debian output |
|---|---|
| `SUMMARY` / `DESCRIPTION` | `Description:` in control |
| `LICENSE` + `LIC_FILES_CHKSUM` | DEP-5 copyright |
| `HOMEPAGE` | `Homepage:` in control |
| `SRC_URI` (git) | `Vcs-Git:`, watch file |
| `SRC_URI` (tarball) | watch + build.sh uscan target |
| `SRC_URI[sha256sum]` | SHA-256 verification in build.sh |
| `PV` | Upstream version in changelog |
| `DEPENDS` | `Build-Depends:` |
| `RDEPENDS` | `Depends:` |
| `inherit cmake/autotools/meson` | debhelper buildsystem flag |
| `inherit module` | DKMS mode |
| `PACKAGES` + `FILES:*` | Split binary packages + .install files |

### Defaults

| Attribute | Value |
|---|---|
| Target distribution | `trixie` |
| debhelper compat | `13` |
| Source format | `3.0 (quilt)` |
| Debian branch | `qcom/debian/trixie/latest` |
| Upstream branch | `qcom/upstream/latest` |
| Architecture | `arm64` (prebuilt), `any` (source), `all` (DKMS) |

### Environment variables

| Variable | Purpose |
|---|---|
| `DEBEMAIL_FULL` | `"Name <email>"` used as maintainer when `--maintainer` is omitted |
| `DEBIAN_DISTRO` | Override target distribution (default: `trixie`) |
| `DEB_BUILD_OPTIONS` | Standard dpkg build options forwarded to `build.sh` |
| `UPSTREAM_BRANCH` | Override upstream git branch name |

### Skill structure

```
skills/debian-packager/
├── SKILL.md
├── scripts/
│   └── debian_packager.py      # Main script (stdlib-only, Python 3.8+)
├── references/
│   ├── control.tmpl
│   ├── changelog.tmpl
│   ├── copyright.tmpl
│   ├── rules.tmpl
│   ├── gbp_conf.tmpl
│   ├── watch.tmpl
│   ├── debusine.tmpl
│   ├── build_source.sh
│   ├── build_prebuilt.sh
│   └── build_dkms.sh
└── templates/
    ├── dkms.conf.tmpl
    ├── postinst.tmpl
    └── prerm.tmpl
```

---

## rpm-packager Skill

### What it does

Generates a complete `pkg-rpm-<name>/` repository skeleton for CentOS Stream 10
(aarch64), modelled on
[qualcomm-linux/pkg-rpm-audioreach-pal](https://github.com/qualcomm-linux/pkg-rpm-audioreach-pal).

| Input | Example |
|---|---|
| Yocto `.bb` recipe | `audioreach-pal_1.0.2.bb` |
| Remote git or tarball URL | `https://github.com/AudioReach/audioreach-pal` |
| Local source tree or tarball | `./audioreach-pal/` |

### Usage

```bash
# AudioReach PAL — version auto-detected via GitHub API
python3 skills/rpm-packager/scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/pkg-rpm-audioreach-pal

# AudioReach PipeWire plugin
python3 skills/rpm-packager/scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --output /tmp/pkg-rpm-audioreach-pipewire-plugin

# From a Yocto recipe
python3 skills/rpm-packager/scripts/rpm_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --output /tmp/pkg-rpm-audioreach-pal

# Dry-run preview
python3 skills/rpm-packager/scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --dry-run --verbose
```

### Generated output

```
pkg-rpm-<name>/
├── <name>.spec                    spec file (Version, Release, BuildRequires, %files)
├── sources                        SHA-512 dist-git checksum file
├── README.md                      package description
├── docs/workflows.md              CI workflow documentation
└── .github/
    ├── CODEOWNERS
    ├── dependabot.yaml
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE/
    └── workflows/
        ├── build-on-pr.yml        PR build via qcom-rpm-utils
        └── pkg-release.yml        manual release to Artifactory (staging/prod)
```

### Build the RPM locally

```bash
cd /tmp/pkg-rpm-<name>
bash build.sh
```

The script auto-downloads the tarball, updates `sources`, resolves the builder
image, and runs `rpmbuild -ba` inside a CentOS Stream 10 container.

**With Qualcomm-specific deps:**
```bash
# Option A — pre-built dep RPMs
EXTRA_RPMS="spf-devel.rpm kvh2xml-devel.rpm gsl-devel.rpm" bash build.sh

# Option B — internal Artifactory repo
EXTRA_REPO="https://your-artifactory.qualcomm.com/rpm/" bash build.sh
```

**After a successful build:**
```bash
rpm -qlp output/<name>-<version>-1.el10.aarch64.rpm   # inspect
sudo dnf install output/<name>-<version>-1.el10.aarch64.rpm
```

### Push to GitHub for CI

```bash
git checkout -b c10s
git add <name>.spec sources
git push origin c10s
# → build-on-pr.yml triggers automatically on the next PR
```

### Spec structure highlights

- `%global debug_package %{nil}` and `%global _lto_cflags %{nil}` globals
- `ExclusiveArch: aarch64`
- `Source0: %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz`
- Split `%package devel` with headers + pkgconfig
- `find %{buildroot} -name '*.la' -delete` in `%install`
- `publish-target: staging | prod` choice in release workflow

### Skill structure

```
skills/rpm-packager/
├── SKILL.md
├── scripts/
│   └── rpm_packager.py         # Main script (stdlib-only, Python 3.8+)
└── references/
```

---

## orbit-cr-report Skill

### What it does

Fetches all CRs from an Orbit saved query and renders a report grouped by
**Found on Product** (target device/platform), sorted by age (oldest first),
with **Software Image Status** colour-coded. Supports table, markdown, JSON,
and CSV output. Handles Orbit's Windows Negotiate/NTLM authentication via
Kerberos, NTLM credentials, or a browser session cookie.

### Usage

```bash
# Kerberos (recommended — get a ticket first)
kinit sauravk@QUALCOMM.COM
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py

# NTLM credentials
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py \
    --user 'QUALCOMM\sauravk' --password 'mypass'

# Browser session cookie (paste from DevTools → Network → Cookie header)
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py \
    --cookie 'ASP.NET_SessionId=abc123; .ASPXAUTH=xyz'

# Different query ID
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --query-id 222099

# Filter to one target product
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --target QCS9075

# Filter to CRs in Analysis status
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --status analysis

# Highlight CRs older than 60 days (default: 90)
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --max-age 60

# Markdown output (for sharing / pasting into docs)
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --output markdown > cr_report.md

# CSV for spreadsheet
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --output csv > cr_report.csv

# JSON for further processing
python3 skills/orbit-cr-report/scripts/orbit_cr_report.py --output json > cr_report.json
```

### Sample output

```
════════════════════════════════════════════════════════════════
  Orbit CR Report  —  47 CRs across 5 targets
════════════════════════════════════════════════════════════════

▶  QCS9075  (12 CRs)
────────────────────────────────────────────────────────────────
  CR          Age   SW Image Status   Title
  ──────────────────────────────────────────────────────────────
  CR-123456   187d  Analysis          Audio dropout during BT call
  CR-123789   142d  Fixed             Mic not detected after suspend
  CR-124001    45d  Build             Volume control unresponsive

Summary:
  QCS9075   12 CRs (3 old)  [Analysis:4, Build:3, Fixed:5]
  QCS6490    8 CRs           [Analysis:2, Fixed:6]
```

**Colour coding:** 🔴 Red = older than `--max-age` · 🟡 Yellow = Analysis ·
🟢 Green = Fixed · 🔵 Cyan = Build/Integrated · 🟣 Magenta = Open/New

### Authentication methods

| Method | How |
|---|---|
| Kerberos | `kinit <user>@QUALCOMM.COM` then run script (no extra flags) |
| NTLM | `--user 'DOMAIN\user' --password 'pass'` |
| Cookie | `--cookie '<paste from browser DevTools>'` |
| Env vars | `ORBIT_USER` + `ORBIT_PASS`, or `ORBIT_COOKIE` |

### All flags

```
--query-id  INT     Orbit query ID (default: 111043)
--url       URL     Orbit base URL (default: https://orbit-sd)
--user      STR     DOMAIN\username for NTLM
--password  STR     Password for NTLM
--cookie    STR     Session cookie string
--output    FORMAT  table (default) | json | csv | markdown
--sort      FIELD   age (default) | cr | status
--max-age   DAYS    Highlight CRs older than N days (default: 90)
--target    STR     Filter to a specific target product (substring match)
--status    STR     Filter to a specific SW image status (substring match)
--no-color          Disable ANSI colour
--verbose           Show HTTP request details
```

### Dependencies

```bash
pip3 install requests                  # always required
pip3 install requests-kerberos         # for Kerberos auth
pip3 install requests-ntlm             # for NTLM auth
```

### Skill structure

```
skills/orbit-cr-report/
├── SKILL.md
├── scripts/
│   └── orbit_cr_report.py      # Main script
└── references/
    └── orbit_api.md            # Auth methods, API endpoints, field schema, troubleshooting
```

---

## pipewire-enhancement Skill

### What it does

Acts as a **PipeWire Enhancement Engineer** for Qualcomm QLI, AudioReach, PAL,
ADSP/DSP, WirePlumber, and Yocto-based audio stacks.

Describe your issue and what you want to build — it produces a complete
10-section implementation proposal. No template-filling, no manual classification.

### Usage

**Conversational (recommended) — just run and answer two questions:**

```bash
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py
```

```
▶ What issue are you seeing?
  Audio glitch and tick at playback start on IQ9075 QLI 2.x

▶ What do you want to build / achieve?
  Eliminate the tick without regressing other audio paths
```

**One-liner:**

```bash
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py \
    --issue "Audio glitch at playback start on IQ9075 QLI 2.x with pw-play" \
    --goal  "Eliminate the tick without regressing other audio paths"
```

**From a file** (`my_issue.txt` — first line = issue, second = goal):

```bash
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py \
    --from-file my_issue.txt
```

**Save proposal to markdown:**

```bash
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py \
    --issue "..." --goal "..." --no-color > proposal.md
```

**List known platforms and enhancement types:**

```bash
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py --list-platforms
python3 skills/pipewire-enhancement/scripts/analyze_enhancement.py --list-types
```

### What you get back

| # | Section | Content |
|---|---|---|
| 1 | Enhancement Summary | Plain-English summary of issue + goal |
| 2 | Classification | Which of 13 enhancement types apply |
| 3 | Affected Components | Component table with change type |
| 4 | Gap Analysis | Missing info you need to provide |
| 5 | Architecture & Design Notes | Root-cause hypotheses + proposed approach |
| 6 | Implementation Plan | Step-by-step tasks with effort (S/M/L) |
| 7 | Test & Validation Plan | Exact test commands + diagnostic hints |
| 8 | Documentation Tasks | Pages/sections to create or update |
| 9 | Open Questions & Risks | Risks with mitigations |
| 10 | Acceptance Criteria | Measurable completion conditions |

### Skill structure

```
skills/pipewire-enhancement/
├── SKILL.md
├── scripts/
│   └── analyze_enhancement.py  # Main script (stdlib-only, Python 3.8+)
├── references/
│   ├── component_map.md        # Source-file mapping, QLI 1.x vs 2.x delta
│   ├── platform_matrix.md      # Per-platform capabilities, known issues
│   └── examples.md             # Three full worked examples
└── agents/
```

---

## Requirements

### glymur-kernel-deb

```bash
# Cross-compilation toolchain and kernel build deps (host)
sudo apt-get install -y \
    gcc-aarch64-linux-gnu make dpkg-dev \
    libssl-dev libelf-dev bc bison flex git

# ADB (for ADB transport)
sudo apt-get install -y android-tools-adb
```

Python 3.8+ (stdlib-only, no pip dependencies).

### debian-packager / rpm-packager

```bash
sudo apt-get install debhelper devscripts dpkg-dev git dkms
```

Python 3.8+ (stdlib-only, no pip dependencies).

### orbit-cr-report

```bash
pip3 install requests requests-kerberos requests-ntlm
```

### pipewire-enhancement

Python 3.8+ (stdlib-only, no pip dependencies).

---

## License

MIT
