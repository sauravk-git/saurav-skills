---
name: debian-packager
description: >
  End-to-end Debian packaging assistant for Qualcomm / AudioReach / QCOM platform
  components. Generates production-ready debian/ directories, build scripts,
  gbp.conf, watch files, and Debusine hints from three input modes: a Yocto/BitBake
  recipe file, a remote git/tarball URL, or a local source tree. Handles
  source/userspace, prebuilt-tarball, and DKMS kernel-module package types.
  Validates output with lintian and dpkg-buildpackage dry-runs when tooling is
  available.
metadata:
  short-description: Generate Debian packaging from Yocto recipes, URLs, or local trees
  author: Saurav Kumar <sauravk@qti.qualcomm.com>
  version: "1.0"
  tags: [debian, packaging, yocto, dkms, qcom, audioreach]
---

# debian-packager Skill

A comprehensive Debian packaging skill that takes a Yocto recipe, a remote URL,
or a local source/tarball path and produces a fully populated `debian/` directory
tree ready for `gbp buildpackage` or `dpkg-buildpackage`.

---

## Supported Input Modes

| Mode | Example trigger |
|---|---|
| Yocto recipe file | `package audioreach-pal_1.0.2.bb` |
| Remote git URL | `package https://github.com/AudioReach/audioreach-pal` |
| Remote tarball URL | `package https://github.com/AudioReach/audioreach-audio-utils/archive/refs/tags/v1.0.0.tar.gz` |
| Local source tree | `package ./audioreach-pal/` |
| Local tarball | `package ./audioreach-audio-utils_1.0.0_arm64.tar.gz` |

---

## Package Types Detected Automatically

| Type | Detection signals |
|---|---|
| **source/userspace** | git `SRC_URI`, plain source tree, `inherit cmake/autotools/meson` |
| **prebuilt tarball** | tarball `SRC_URI`, `do_compile[noexec]`, `INHIBIT_PACKAGE_STRIP`, `INSANE_SKIP`, direct `.tar.gz` URL/path |
| **DKMS kernel module** | `inherit module`, `--dkms` flag, `obj-m`/`KDIR` in Makefile, `dkms.conf` present |

---

## Workflow

### Step 1 — Parse Input

Run the agent script to parse the input and emit a JSON manifest:

```bash
python3 scripts/debian_packager.py \
    --recipe path/to/recipe.bb \
    --output /tmp/debian-out \
    --maintainer "Saurav Kumar <sauravk@qti.qualcomm.com>"
```

Or from a URL:

```bash
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/debian-out
```

Or from a local path:

```bash
python3 scripts/debian_packager.py \
    --path ./audioreach-pal \
    --output /tmp/debian-out \
    --dkms   # force DKMS mode if auto-detect misses it
```

### Step 2 — Inspect Generated Files

```
/tmp/debian-out/
├── debian/
│   ├── changelog          # DEP-3 format, target: trixie
│   ├── compat             # debhelper compat level 13
│   ├── control            # source + binary stanzas
│   ├── copyright          # DEP-5 machine-readable
│   ├── gbp.conf           # git-buildpackage config
│   ├── rules              # dh $@ with overrides
│   ├── source/
│   │   └── format         # "3.0 (quilt)"
│   ├── watch              # uscan watch file
│   ├── <pkg>.install      # file installation lists
│   ├── <pkg>.dkms         # (DKMS only) dkms.conf wrapper
│   ├── <pkg>.postinst     # (DKMS only) maintainer scripts
│   └── <pkg>.prerm        # (DKMS only) maintainer scripts
├── build.sh               # one-shot build helper
└── debusine.yaml          # Debusine CI hints
```

### Step 3 — Build the Package

**Source/userspace:**

```bash
cd /tmp/debian-out
bash build.sh
# Internally runs:
#   git clone <upstream> src/
#   cp -r debian/ src/
#   cd src && debuild -uc -us -b
```

**Prebuilt tarball:**

```bash
# Option A — let uscan fetch the tarball
bash build.sh

# Option B — supply a local tarball
bash build.sh /path/to/audioreach-audio-utils_1.0.0_arm64.tar.gz

# Option C — supply an already-unpacked directory
bash build.sh /path/to/audioreach-audio-utils-1.0.0/
```

**DKMS:**

```bash
bash build.sh
# Internally runs:
#   dpkg-buildpackage -b --no-sign
# Produces: <pkg>-dkms_<ver>_all.deb
```

### Step 4 — Validate

```bash
# Lint the generated package
lintian --pedantic ../*.deb

# Dry-run build check (no actual compilation)
dpkg-buildpackage --dry-run -b --no-sign

# Verify watch file
uscan --no-download --verbose
```

---

## Yocto Recipe Field Mapping

| Yocto field | Debian output |
|---|---|
| `SUMMARY` | Short description in `control` |
| `DESCRIPTION` | Long description in `control` |
| `LICENSE` + `LIC_FILES_CHKSUM` | DEP-5 `copyright` file |
| `HOMEPAGE` | `Homepage:` in `control` |
| `SRC_URI` (git) | `Vcs-Git:`, `watch` file |
| `SRC_URI` (tarball) | `watch` + `build.sh` uscan target |
| `SRC_URI[sha256sum]` | SHA-256 verification in `build.sh` |
| `PV` | Upstream version in `changelog` |
| `DEPENDS` | `Build-Depends:` in `control` |
| `RDEPENDS` | `Depends:` in binary stanza |
| `inherit cmake` | `--buildsystem=cmake` in `rules` |
| `inherit autotools` | `--buildsystem=autoconf` in `rules` |
| `inherit meson` | `--buildsystem=meson` in `rules` |
| `inherit module` | DKMS mode trigger |
| `PACKAGES` + `FILES:*` | Split binary packages + `.install` files |
| `do_install()` | Translated prebuilt install rules |

---

## Debian Defaults

| Attribute | Value |
|---|---|
| Target distribution | `trixie` |
| debhelper compat | `13` |
| Source format | `3.0 (quilt)` |
| Default branch | `qcom/debian/trixie/latest` |
| Upstream branch | `qcom/upstream/latest` |
| Maintainer fallback | `$DEBEMAIL_FULL` env var or `--maintainer` flag |
| Architecture | `arm64` (prebuilt), `any` (source), `all` (DKMS) |

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DEBEMAIL_FULL` | `"Name <email>"` used as maintainer when `--maintainer` is omitted |
| `DEBIAN_DISTRO` | Override target distribution (default: `trixie`) |
| `DEB_BUILD_OPTIONS` | Standard dpkg build options forwarded to `build.sh` |
| `UPSTREAM_BRANCH` | Override upstream git branch name |

---

## Versioning Guidelines

Versioning is **fully automatic** — the skill resolves both the upstream
version and the Debian revision without any manual input. You only need
the override flags when auto-detection cannot reach the right answer.

### How versions are resolved automatically

#### Upstream version

The skill tries each source in order, stopping at the first hit:

| Input mode | Resolution strategy |
|---|---|
| Yocto recipe (`--recipe`) | `PV` field; git/AUTOINC PV normalised to `<base>+git<YYYYMMDD>` |
| Git URL (`--url`) | GitHub / GitLab API → latest semver tag |
| Tarball URL (`--url`) | Parsed from the filename (e.g. `foo_1.2.tar.gz` → `1.2`) |
| Local git clone (`--path`) | `git describe --tags --abbrev=0`; falls back to `<ver>+git<YYYYMMDD>` for dirty trees |
| Local non-git dir (`--path`) | Reads `VERSION` / `version.txt` file if present |
| Fallback | `0+git<YYYYMMDD>` (always produces a valid, sortable version) |

#### Debian revision

| Situation | Auto-selected revision |
|---|---|
| Output directory does not exist yet | `1` (first packaging) |
| Output dir exists, same upstream version | existing revision + 1 (re-packaging) |
| Output dir exists, different upstream version | `1` (new upstream, reset) |

### Override flags (when you need them)

| Flag | When to use |
|---|---|
| `--upstream-version VER` | API unreachable, private repo, or you want to pin a specific version |
| `--debian-revision REV` | Force a specific revision (e.g. `0~rc1`, `0~git20261009`, backport suffix) |

```bash
# Fully automatic — version and revision resolved without any flags
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/audioreach-pal-deb
# → queries GitHub API → finds v1.0.2 → writes 1.0.2-1

# Run again on the same output dir (re-packaging)
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/audioreach-pal-deb
# → same upstream 1.0.2 already in changelog → writes 1.0.2-2

# Local git clone — uses git describe
python3 scripts/debian_packager.py \
    --path ./audioreach-pal \
    --output /tmp/audioreach-pal-deb
# → git describe → v1.0.2 → writes 1.0.2-1

# git recipe with AUTOINC PV — normalised to date snapshot
python3 scripts/debian_packager.py \
    --recipe audioreach-kernel_git.bb \
    --output /tmp/audioreach-kernel-deb
# → PV="git" → 0+git20261009-1

# Override only when needed (private repo, no API access)
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --upstream-version 1.0.3 --debian-revision 0~rc1 \
    --output /tmp/audioreach-pipewire-plugin-deb
# → 1.0.3-0~rc1
```

### Version format reference

```
<upstream_version>-<debian_revision>

1.0.2-1          first packaging of upstream 1.0.2
1.0.2-2          re-packaging (debian/ fix, upstream unchanged)
1.0.3-0~rc1      release candidate  (sorts before 1.0.3-1)
1.0.3-0~beta2    beta               (sorts before 1.0.3-0~rc1)
0+git20261009-1  git snapshot with no tag
1.0.2-1~bpo12+1  backport to bookworm
```

> `0~` and `0+git` prefixes sort *before* the bare release in
> `dpkg --compare-versions`, so snapshots and pre-releases never
> accidentally supersede a final release.


---

## Advanced Options

```
--recipe FILE        Parse a Yocto .bb recipe file
--url URL            Remote git repo or tarball URL
--path DIR           Local source tree
--local FILE/DIR     Alias for --path (accepts file or directory)
--output DIR         Where to write the debian/ skeleton (default: ./debian-out)
--maintainer STR     "Name <email>" string for changelog/control
--upstream-version VER  Override upstream version (e.g. 1.0.2)
--debian-revision REV   Debian revision suffix (default: 1; use 0~rc1 for pre-releases)
--dkms               Force DKMS package type
--prebuilt           Force prebuilt package type
--source             Force source/userspace package type
--split-packages     Emit one binary stanza per PACKAGES entry
--no-watch           Skip watch file generation
--no-gbp             Skip gbp.conf generation
--no-debusine        Skip debusine.yaml generation
--dry-run            Print what would be generated without writing files
--verbose            Verbose logging
```

---

## Example Invocations

```bash
# AudioReach PAL from Yocto recipe
python3 scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --output /tmp/audioreach-pal-deb

# AudioReach audio-utils prebuilt
python3 scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-audio-utils/audioreach-audio-utils_1.0.0.bb \
    --output /tmp/audioreach-audio-utils-deb

# AudioReach kernel module (DKMS) from recipe
python3 scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-kernel/audioreach-kernel_git.bb \
    --output /tmp/audioreach-kernel-deb

# Source package from git URL
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --output /tmp/audioreach-pipewire-plugin-deb

# Prebuilt from tarball URL
python3 scripts/debian_packager.py \
    --url https://github.com/AudioReach/audioreach-audio-utils/archive/refs/tags/v1.0.0.tar.gz \
    --output /tmp/audioreach-audio-utils-deb

# AudioReach kernel module from local tree
python3 scripts/debian_packager.py \
    --path ./audioreach-kernel \
    --dkms \
    --output /tmp/audioreach-kernel-deb

# Dry-run to preview without writing
python3 scripts/debian_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --dry-run --verbose
```

---

## Trigger Phrases

This skill activates when the user says things like:

- `create debian skeleton for recipe <path>`
- `generate debian packaging for <url>`
- `package <local-path> as debian`
- `deb skel for <recipe/url/path>`
- `debian-packager <input>`
- `make debian package from <recipe>`
- `create deb metadata for prebuilt <recipe>`
- `DKMS debian packaging for <recipe/path>`

---

## Scripts

- `scripts/debian_packager.py` — main agent (stdlib-only, Python 3.8+)

## References

- `references/control.tmpl`     — control file template
- `references/changelog.tmpl`   — changelog template
- `references/copyright.tmpl`   — DEP-5 copyright template
- `references/rules.tmpl`       — debian/rules template
- `references/gbp_conf.tmpl`    — gbp.conf template
- `references/watch.tmpl`       — uscan watch template
- `references/build_source.sh`  — build.sh for source packages
- `references/build_prebuilt.sh`— build.sh for prebuilt tarballs
- `references/build_dkms.sh`    — build.sh for DKMS packages
- `references/debusine.tmpl`    — debusine.yaml template

## Templates

- `templates/dkms.conf.tmpl`    — upstream dkms.conf template
- `templates/postinst.tmpl`     — DKMS postinst maintainer script
- `templates/prerm.tmpl`        — DKMS prerm maintainer script
