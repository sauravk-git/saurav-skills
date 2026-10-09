# saurav-skills

Personal QGenie / Codex skill collection by [Saurav Kumar](https://github.com/sauravk-git).

These skills extend the QGenie CLI agent with specialized, domain-specific workflows
for Qualcomm platform and AudioReach development.

---

## Available Skills

| Skill | Description |
|---|---|
| [debian-packager](skills/debian-packager/SKILL.md) | End-to-end Debian packaging skeleton generator for QCOM/AudioReach components — supports Yocto recipes, remote URLs, and local source trees |

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
