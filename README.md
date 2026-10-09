# saurav-skills

Personal QGenie / Codex skill collection by [Saurav Kumar](https://github.com/sauravk-git).

These skills extend the QGenie CLI agent with specialized, domain-specific workflows
for Qualcomm platform and AudioReach development.

---

## Available Skills

| Skill | Description |
|---|---|
| [debian-packager](skills/debian-packager/SKILL.md) | End-to-end Debian packaging skeleton generator for QCOM/AudioReach components — supports Yocto recipes, remote URLs, and local source trees |
| [rpm-packager](skills/rpm-packager/SKILL.md) | End-to-end RPM packaging skeleton generator for CentOS Stream 10 (aarch64) — generates spec files, dist-git sources, and GitHub Actions CI/release workflows modelled on qualcomm-linux/pkg-rpm-audioreach-pal |
| [orbit-cr-report](skills/orbit-cr-report/SKILL.md) | Fetch a saved Orbit query, parse all CRs, group by Found on Product (target), sort by age, and display Software Image Status (Analysis, Fixed, Build, etc.) with colour coding |

---

## Quick Install

### From inside QGenie CLI

```
Install the debian-packager skill from sauravk-git/saurav-skills
```

The agent will use the `skill-installer` skill to fetch and install it automatically.

### Manual install

```bash
# Clone this repo
git clone https://github.com/sauravk-git/saurav-skills.git

# Copy the skill into your QGenie skills directory
cp -r saurav-skills/skills/debian-packager \
      ~/.config/qgenie-cli/agent/skills/

# Restart QGenie to pick up the new skill
```

Or use the installer script directly:

```bash
python3 ~/.config/qgenie-cli/agent/skills/.system/skill-installer/scripts/install-skill-from-github.py \
    --repo sauravk-git/saurav-skills \
    --path skills/debian-packager
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

#### What gets resolved automatically

| Input | Upstream version source | Debian revision logic |
|---|---|---|
| `--url` (GitHub/GitLab) | GitHub/GitLab API → latest semver tag | `1` first time; auto-increments on re-run |
| `--url` (tarball) | Parsed from filename | same |
| `--recipe` | `PV` field; `git`/AUTOINC PV → `<base>+git<YYYYMMDD>` | same |
| `--path` (git clone) | `git describe --tags`; dirty tree → `<ver>+git<YYYYMMDD>` | same |
| `--path` (non-git) | `VERSION` / `version.txt` file | same |
| Fallback | `0+git<YYYYMMDD>` | same |

The Debian revision is auto-bumped when the output directory already
contains a `debian/changelog` for the same upstream version:

```
first run   → 1.0.2-1
second run  → 1.0.2-2   (re-packaging, upstream unchanged)
new upstream→ 1.0.3-1   (upstream changed, revision resets)
```

#### Override flags (only when needed)

```bash
# Fully automatic
python3 skills/debian-packager/scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/audioreach-pal-deb
# → GitHub API finds v1.0.2 → writes 1.0.2-1

# Force a pre-release revision
python3 skills/debian-packager/scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --upstream-version 1.0.3 --debian-revision 0~rc1 \
    --output /tmp/audioreach-pipewire-plugin-deb
# → 1.0.3-0~rc1
```

#### Version format quick reference

| Version | Meaning |
|---|---|
| `1.0.2-1` | First packaging of upstream 1.0.2 |
| `1.0.2-2` | Re-packaging (debian/ fix only) |
| `1.0.3-0~rc1` | Release candidate (sorts before `1.0.3-1`) |
| `0+git20261009-1` | Git snapshot, no upstream tag |
| `1.0.2-1~bpo12+1` | Backport to bookworm |


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

---

## Skill structure

```
skills/debian-packager/
├── SKILL.md                    # Skill definition and workflow
├── scripts/
│   └── debian_packager.py      # Main agent (stdlib-only, Python 3.8+)
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

---

## rpm-packager Skill

### What it does

Generates a complete `pkg-rpm-<name>/` repository skeleton for CentOS Stream 10
(aarch64), modelled exactly on
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

Every generated skeleton includes `build.sh` and `build-tools/Dockerfile`.

```bash
cd /tmp/pkg-rpm-<name>
bash build.sh
```

The script auto-downloads the tarball, updates `sources`, resolves the
builder image, and runs `rpmbuild -ba` inside a CentOS Stream 10 container.

**With Qualcomm-specific deps (not in public repos):**
```bash
# Option A — pre-built dep RPMs
EXTRA_RPMS="spf-devel.rpm kvh2xml-devel.rpm gsl-devel.rpm" bash build.sh

# Option B — internal Artifactory repo
EXTRA_REPO="https://your-artifactory.qualcomm.com/rpm/" bash build.sh
```

**Builder image priority** (automatic):
1. `ghcr.io/qualcomm-linux/rpm-builder:centos10` (official, if accessible)
2. `local/rpm-builder:centos10` built from `build-tools/Dockerfile` (fallback)

**After a successful build:**
```bash
rpm -qlp output/<name>-<version>-1.el10.aarch64.rpm   # inspect
sudo dnf install output/<name>-<version>-1.el10.aarch64.rpm  # install
```

### Push to GitHub for CI

```bash
git checkout -b c10s
git add <name>.spec sources
git push origin c10s
# → build-on-pr.yml triggers automatically on the next PR
```

### Spec structure

Follows the exact real-world reference from `qualcomm-linux/pkg-rpm-audioreach-pal`:
- `%global debug_package %{nil}` and `%global _lto_cflags %{nil}` globals
- `ExclusiveArch: aarch64`
- `Source0: %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz`
- Split `%package devel` with headers + pkgconfig
- `find %{buildroot} -name '*.la' -delete` in `%install`
- `publish-target: staging | prod` choice in release workflow


## Requirements

- Python 3.8+ (stdlib-only, no pip dependencies)
- For building packages: `debhelper`, `devscripts`, `dpkg-dev`, `git`
- For DKMS packages: `dkms`, `linux-headers-$(uname -r)`
- For prebuilt packages: `uscan` (from `devscripts`), `mk-origtargz`

```bash
sudo apt-get install debhelper devscripts dpkg-dev git dkms
```

---

## License

MIT
