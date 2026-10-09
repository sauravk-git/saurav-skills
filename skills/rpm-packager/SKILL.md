---
name: rpm-packager
description: >
  End-to-end RPM packaging assistant for Qualcomm / AudioReach / QCOM platform
  components targeting CentOS Stream 10 (aarch64). Generates a production-ready
  pkg-rpm-<name> repository skeleton — spec file, dist-git sources file, GitHub
  Actions CI/release workflows, and all .github/ boilerplate — from three input
  modes: a Yocto/BitBake recipe file, a remote git/tarball URL, or a local source
  tree. Follows the exact structure of qualcomm-linux/pkg-rpm-audioreach-pal and
  the qualcomm-linux/qcom-rpm-utils CI pipeline.
metadata:
  short-description: Generate CentOS/RPM spec + dist-git repo from Yocto recipes, URLs, or local trees
  author: Saurav Kumar <sauravk@qti.qualcomm.com>
  version: "1.0"
  tags: [rpm, centos, spec, yocto, qcom, audioreach, dist-git, c10s]
---

# rpm-packager Skill

Generates a complete `pkg-rpm-<name>/` repository skeleton for CentOS Stream 10
(aarch64) builds, following the `qualcomm-linux/qcom-rpm-utils` dist-git CI pipeline.
Works for **any package** — AudioReach, kernel modules, prebuilt binaries, or any
upstream project.

---

## Supported Input Modes

| Mode | Example trigger |
|---|---|
| Yocto recipe file | `rpm package libfoo_1.2.0.bb` |
| Remote git URL | `rpm package https://github.com/org/mypackage` |
| Remote tarball URL | `rpm package https://example.com/mypackage-1.2.0.tar.gz` |
| Local source tree | `rpm package ./mypackage/` |
| Local tarball | `rpm package ./mypackage-1.2.0.tar.gz` |

---

## Package Types Detected Automatically

| Type | Detection signals |
|---|---|
| **source/library** | git `SRC_URI`, plain source tree, `inherit cmake/autotools/meson` |
| **prebuilt tarball** | tarball `SRC_URI`, `do_compile[noexec]`, `INHIBIT_PACKAGE_STRIP`, `INSANE_SKIP` |
| **kernel module** | `inherit module`, `--kmod` flag, `obj-m`/`KDIR` in Makefile |

---

## Workflow

### Step 1 — Generate the skeleton

```bash
python3 scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/pkg-rpm-audioreach-pal \
    --maintainer "Saurav Kumar <sauravk@qti.qualcomm.com>"
```

Or from a Yocto recipe:

```bash
python3 scripts/rpm_packager.py \
    --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb \
    --output /tmp/pkg-rpm-audioreach-pal
```

### Step 2 — Inspect generated files

```
pkg-rpm-<name>/
├── <name>.spec                          # RPM spec (c10s branch)
├── sources                              # SHA-512 dist-git checksum file
├── README.md                            # Package description
├── docs/
│   └── workflows.md                     # CI workflow documentation
└── .github/
    ├── CODEOWNERS
    ├── dependabot.yaml
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    ├── PULL_REQUEST_TEMPLATE/
    │   └── pr_template.md
    └── workflows/
        ├── build-on-pr.yml              # PR build via qcom-rpm-utils
        └── pkg-release.yml             # Manual release to Artifactory
```

### Step 3 — Update sources checksum

The `sources` file is generated with a placeholder. Replace it with the real SHA-512:

```bash
# Download the upstream tarball
wget https://github.com/AudioReach/audioreach-pal/archive/refs/tags/v1.0.2.tar.gz \
     -O audioreach-pal-1.0.2.tar.gz

# Generate the sources line (BSD checksum format)
sha512sum --tag audioreach-pal-1.0.2.tar.gz > sources
```

The `sources` file format (exact dist-git format):
```
SHA512 (audioreach-pal-1.0.2.tar.gz) = <hexdigest>
```

### Step 4 — Push to GitHub on the `c10s` branch

```bash
cd /tmp/pkg-rpm-audioreach-pal
git init
git checkout -b c10s
git add audioreach-pal.spec sources README.md LICENSE.txt
git commit -m "Initial RPM packaging of audioreach-pal 1.0.2"
git remote add origin https://github.com/sauravk-git/pkg-rpm-audioreach-pal.git
git push -u origin c10s
```

### Step 5 — CI/CD

- **PR build**: every pull request triggers `build-on-pr.yml` automatically via
  `qualcomm-linux/qcom-rpm-utils`.
- **Release**: Actions → Release → Run workflow → choose `staging` or `prod`
  (requires `pkg-release-approval` environment gate).

---

## Spec File Structure

The generated spec follows the exact structure of the real
`qualcomm-linux/pkg-rpm-audioreach-pal` reference:

```spec
%global debug_package %{nil}
%global _lto_cflags %{nil}

Name:           mypackage
Version:        1.2.0
Release:        1%{?dist}
Summary:        One-line summary of mypackage
ExclusiveArch:  aarch64

License:        BSD-3-Clause
URL:            https://github.com/org/mypackage
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  libtool
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig
# <extra BuildRequires auto-populated from recipe DEPENDS or --build-requires>

%description
Full description of mypackage.

%package        devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description    devel
Headers and pkg-config files for building against %{name}.

%prep
%autosetup -n %{name}-%{version}

%build
autoreconf -fi
%configure

%make_build

%install
%make_install
find %{buildroot} -name '*.la' -delete

%files
%license LICENSE
%{_libdir}/libmypackage.so.*

%files devel
%{_includedir}/mypackage/
%{_libdir}/libmypackage.so
%{_libdir}/pkgconfig/*.pc

%changelog
* Fri Oct 09 2026 Saurav Kumar <sauravk@qti.qualcomm.com> - 1.2.0-1
- Initial RPM packaging of mypackage version 1.2.0.
``````

---

## Versioning

Versioning is **fully automatic** — no flags needed for normal use.

| Input mode | Version source |
|---|---|
| `--url` (GitHub/GitLab) | GitHub/GitLab API → latest semver tag |
| `--url` (tarball) | Parsed from filename |
| `--recipe` | `PV` field; git/AUTOINC PV → `0+git<YYYYMMDD>` |
| `--path` (git clone) | `git describe --tags`; dirty → `<ver>+git<YYYYMMDD>` |
| `--path` (non-git) | `VERSION` / `version.txt` file |
| Fallback | `0+git<YYYYMMDD>` |

**RPM Release counter** — auto-determined by reading an existing spec in the output dir:

| Situation | Release |
|---|---|
| First packaging | `1%{?dist}` |
| Re-packaging (spec fix, same upstream) | `2%{?dist}`, `3%{?dist}`, ... |
| New upstream version | reset to `1%{?dist}` |

Override flags (only when needed):

```bash
# Pin a specific version
python3 scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --upstream-version 1.0.2 --rpm-release 2 \
    --output /tmp/pkg-rpm-audioreach-pal
```

---

## Yocto Recipe Field Mapping

| Yocto field | RPM spec output |
|---|---|
| `SUMMARY` | `Summary:` |
| `DESCRIPTION` | `%description` body |
| `LICENSE` | `License:` (SPDX mapped) |
| `HOMEPAGE` | `URL:` |
| `SRC_URI` (git) | `Source0:` archive URL |
| `SRC_URI` (tarball) | `Source0:` direct URL |
| `SRC_URI[sha256sum]` | Embedded in `sources` file |
| `PV` | `Version:` |
| `DEPENDS` | `BuildRequires:` |
| `RDEPENDS` | `Requires:` |
| `inherit cmake` | `%cmake` / `%cmake_build` / `%cmake_install` |
| `inherit autotools` | `%configure` / `%make_build` / `%make_install` |
| `inherit meson` | `%meson` / `%meson_build` / `%meson_install` |
| `inherit module` | kernel module spec |
| `PACKAGES` + `FILES:*` | Split `%package` + `%files` sections |

---

## RPM Defaults

| Attribute | Value |
|---|---|
| Target distribution | CentOS Stream 10 (`%{?dist}` = `.el10`) |
| Architecture | `aarch64` (`ExclusiveArch: aarch64`) |
| Global flags | `%global debug_package %{nil}`, `%global _lto_cflags %{nil}` |
| Source0 URL pattern | `%{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz` |
| sources format | `SHA512 (filename) = hexdigest` |
| CI reusable workflow | `qualcomm-linux/qcom-rpm-utils@main` |
| Release workflow target | `staging` (default) or `prod` |

---

## dist-git `sources` File

Follows the exact Fedora/CentOS dist-git format used by the real repo:

```
SHA512 (audioreach-pal-1.0.2.tar.gz) = 45cad5f1595e05d19623eeb7d88a90403f4cdb...
```

Generate with:
```bash
sha512sum --tag audioreach-pal-1.0.2.tar.gz > sources
```

---

## Required Repository Configuration

After pushing to GitHub, configure:

| Setting | Value |
|---|---|
| Actions variable | `SRC_TARBALL_CACHE_BASE_URL` — base URL of the lookaside cache |
| Secret | `RPM_ARTIFACTORY_ACCESS_TOKEN` — Artifactory publish credential |
| Secret | `QSC_API_KEY` — optional QSC API key |
| Secret | `PROD_RPM_ARTIFACTORY_ACCESS_TOKEN` — prod Artifactory credential |
| Environment | `pkg-release-approval` — add required reviewers for the release gate |
| Runner | `[self-hosted, platform-prd-u2404-arm64-large-od-ephem]` |

---

## Advanced Options

```
--recipe FILE           Parse a Yocto .bb recipe file
--url URL               Remote git repo or tarball URL
--path DIR              Local source tree or tarball
--output DIR            Output directory (default: ./rpm-out)
--maintainer STR        "Name <email>" for spec %changelog
--upstream-version VER  Override upstream version (auto-detected by default)
--rpm-release REV       Override RPM Release field (auto-detected by default)
--kmod                  Force kernel module package type
--prebuilt              Force prebuilt package type
--source                Force source/library package type
--split-packages        Emit one %package section per PACKAGES entry
--no-workflows          Skip GitHub Actions workflow generation
--no-sources            Skip sources file generation
--dry-run               Print what would be generated without writing files
--verbose               Verbose logging
```

---

## Example Invocations

```bash
# Any package from a git URL (version auto-detected via GitHub API)
python3 scripts/rpm_packager.py \
    --url https://github.com/org/mypackage \
    --output /tmp/pkg-rpm-mypackage

# From a Yocto recipe
python3 scripts/rpm_packager.py \
    --recipe meta-layer/recipes-foo/mypackage/mypackage_1.2.0.bb \
    --output /tmp/pkg-rpm-mypackage

# From a local source tree
python3 scripts/rpm_packager.py \
    --path ./mypackage \
    --output /tmp/pkg-rpm-mypackage

# Kernel module
python3 scripts/rpm_packager.py \
    --path ./my-kernel-driver \
    --kmod \
    --output /tmp/pkg-rpm-my-kernel-driver

# Prebuilt tarball
python3 scripts/rpm_packager.py \
    --url https://example.com/mypackage-1.2.0_aarch64.tar.gz \
    --output /tmp/pkg-rpm-mypackage

# Dry-run preview (no files written)
python3 scripts/rpm_packager.py \
    --url https://github.com/org/mypackage \
    --dry-run --verbose

# AudioReach examples
python3 scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pal \
    --output /tmp/pkg-rpm-audioreach-pal

python3 scripts/rpm_packager.py \
    --url https://github.com/AudioReach/audioreach-pipewire-plugin \
    --output /tmp/pkg-rpm-audioreach-pipewire-plugin
```

---

## Trigger Phrases

- `create RPM spec for <url/recipe/path>`
- `generate RPM packaging for <name>`
- `rpm package <url/recipe/path>`
- `make spec file for <name>`
- `centos packaging for <name>`
- `pkg-rpm for <name>`
- `create spec and sources for <name>`

---

## Scripts

- `scripts/rpm_packager.py` — main agent (stdlib-only, Python 3.8+)

## References

- `references/spec_source.tmpl`  — spec template for source/library packages
- `references/sources.tmpl`      — dist-git sources file template
- `references/build_on_pr.yml`   — exact build-on-pr.yml from real repo
- `references/pkg_release.yml`   — exact pkg-release.yml from real repo
