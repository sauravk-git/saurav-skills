#!/usr/bin/env python3
"""
rpm_packager.py — RPM packaging skeleton generator for CentOS Stream 10 (aarch64)
Supports: Yocto recipe, remote URL (git/tarball), local source tree or tarball.
Package types: source/library, prebuilt tarball, kernel module.
Follows the Qualcomm dist-git model (qualcomm-linux/qcom-rpm-utils).
Stdlib-only. Python 3.8+.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_DIST        = os.environ.get("RPM_DIST", "el10")
DEFAULT_ARCH        = os.environ.get("RPM_ARCH", "aarch64")
DEFAULT_MAINTAINER  = os.environ.get("RPM_MAINTAINER",
                                     "Saurav Kumar <sauravk@qti.qualcomm.com>")
DEFAULT_STREAM      = "c10s"
QCOM_RPM_UTILS_REF  = "main"
ARTIFACTORY_URL     = "https://qartifactory.qualcomm.com"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
VERBOSE = False

def log(msg):
    if VERBOSE:
        print(f"[rpm-packager] {msg}", file=sys.stderr)

def info(msg):
    print(f"  {msg}")

def die(msg):
    print(f"  ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class RpmManifest:
    def __init__(self):
        self.pkg_name: str          = "unknown"
        self.upstream_version: str  = "0.0.1"
        self.rpm_release: str       = "1"
        self.summary: str           = "No summary available"
        self.description: str       = "No description available."
        self.homepage: str          = ""
        self.license_spdx: str      = "UNKNOWN"
        self.maintainer: str        = DEFAULT_MAINTAINER
        self.arch: str              = DEFAULT_ARCH
        self.source0_url: str       = ""
        self.source0_filename: str  = ""
        self.source0_sha512: str    = "FIXME_RUN_sha512sum_--tag_ON_TARBALL"
        self.buildsystem: str       = ""   # cmake | autotools | meson | ""
        self.pkg_type: str          = "source"  # source | prebuilt | kmod
        self.build_requires: list   = []
        self.requires: list         = []
        self.split_packages: list   = []   # [(subpkg_name, summary, files_glob)]
        self.vcs_url: str           = ""
        self.changelog_entries: list = []  # [(date_str, maintainer, ver_rel, notes)]

    @property
    def full_version(self):
        return f"{self.upstream_version}-{self.rpm_release}"

    @property
    def tarball_name(self):
        if self.source0_filename and "%{version}" not in self.source0_filename:
            return self.source0_filename
        return f"{self.pkg_name}-{self.upstream_version}.tar.gz"

    @property
    def changelog_date(self):
        return datetime.datetime.now().strftime("%a %b %d %Y")

# ---------------------------------------------------------------------------
# Auto-versioning helpers  (mirrors debian_packager.py)
# ---------------------------------------------------------------------------

def _fetch_latest_github_tag(owner: str, repo: str) -> Optional[str]:
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=20"
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github.v3+json",
                          "User-Agent": "rpm-packager-skill/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            tags = json.loads(resp.read())
        for tag in tags:
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", tag.get("name", ""))
            if m:
                log(f"GitHub latest tag for {owner}/{repo}: {tag['name']}")
                return m.group(1)
    except Exception as exc:
        log(f"GitHub tag lookup failed: {exc}")
    return None


def _fetch_latest_gitlab_tag(host: str, owner: str, repo: str) -> Optional[str]:
    try:
        project = urllib.request.quote(f"{owner}/{repo}", safe="")
        url = f"https://{host}/api/v4/projects/{project}/repository/tags?per_page=20&order_by=version"
        req = urllib.request.Request(url, headers={"User-Agent": "rpm-packager-skill/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            tags = json.loads(resp.read())
        for tag in tags:
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", tag.get("name", ""))
            if m:
                log(f"GitLab latest tag for {owner}/{repo}: {tag['name']}")
                return m.group(1)
    except Exception as exc:
        log(f"GitLab tag lookup failed: {exc}")
    return None


def _resolve_version_from_url(url: str) -> Optional[str]:
    m = re.match(r"https?://github\.com/([^/]+)/([^/\.]+)", url)
    if m:
        return _fetch_latest_github_tag(m.group(1), m.group(2))
    m = re.match(r"https?://gitlab\.com/([^/]+)/([^/\.]+)", url)
    if m:
        return _fetch_latest_gitlab_tag("gitlab.com", m.group(1), m.group(2))
    m = re.match(r"https?://([^/]+)/([^/]+)/([^/\.]+)", url)
    if m and m.group(1) not in ("github.com", "gitlab.com"):
        return _fetch_latest_gitlab_tag(m.group(1), m.group(2), m.group(3))
    return None


def _resolve_version_from_local(path: Path) -> Optional[str]:
    if not (path / ".git").exists():
        for vfile in ["VERSION", "version.txt", "version", "VERSION.txt"]:
            vpath = path / vfile
            if vpath.exists():
                raw = vpath.read_text().strip().splitlines()[0].strip()
                m = re.match(r"v?(\d+\.\d+[\.\d]*)", raw)
                if m:
                    log(f"Version from {vfile}: {m.group(1)}")
                    return m.group(1)
        return None
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(path), capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            tag = result.stdout.strip()
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", tag)
            if m:
                return m.group(1)
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)-\d+-g[0-9a-f]+$", tag)
            if m:
                date_str = _git_commit_date(path)
                return f"{m.group(1)}+git{date_str}"
    except Exception as exc:
        log(f"git describe failed: {exc}")
    date_str = _git_commit_date(path)
    return f"0+git{date_str}" if date_str else None


def _git_commit_date(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d"],
            cwd=str(path), capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return datetime.datetime.now().strftime("%Y%m%d")


def _auto_rpm_release(output_dir: str, upstream_version: str) -> str:
    """
    Auto-determine RPM Release:
    - No existing spec → "1"
    - Existing spec, same Version → increment release number
    - Existing spec, different Version → reset to "1"
    """
    spec_files = list(Path(output_dir).glob("*.spec")) if Path(output_dir).exists() else []
    if not spec_files:
        log("No existing spec found — RPM release: 1")
        return "1"
    try:
        spec_text = spec_files[0].read_text()
        ver_m = re.search(r"^Version:\s*(.+)$", spec_text, re.M)
        rel_m = re.search(r"^Release:\s*(\d+)", spec_text, re.M)
        if ver_m and rel_m:
            existing_ver = ver_m.group(1).strip()
            existing_rel = int(rel_m.group(1))
            if existing_ver == upstream_version:
                new_rel = str(existing_rel + 1)
                log(f"Same upstream {upstream_version} at release {existing_rel} → bumping to {new_rel}")
                return new_rel
            else:
                log(f"Upstream changed {existing_ver} → {upstream_version} — resetting release to 1")
                return "1"
    except Exception as exc:
        log(f"Could not read existing spec: {exc}")
    return "1"

# ---------------------------------------------------------------------------
# Yocto recipe parser
# ---------------------------------------------------------------------------
_BB_VAR     = re.compile(r'^([A-Z_][A-Z0-9_:]*)\s*(?:\??=|:=|\.=|=\+|=\.)\s*"(.*)"', re.M)
_BB_INHERIT = re.compile(r'^inherit\s+(.+)', re.M)
_BB_SRC_URI = re.compile(r'SRC_URI\s*(?:\??=|:=|\+=|\.=)\s*"([^"]*)"', re.M | re.S)


def _bb_vars(text):
    return {m.group(1): m.group(2) for m in _BB_VAR.finditer(text)}

def _bb_inherits(text):
    classes = []
    for m in _BB_INHERIT.finditer(text):
        classes.extend(m.group(1).split())
    return classes

def _bb_src_uris(text):
    uris = []
    for m in _BB_SRC_URI.finditer(text):
        uris.extend(m.group(1).split())
    return [u.strip().split(";")[0] for u in uris if u.strip()]


def parse_recipe(recipe_path: str, manifest: RpmManifest) -> None:
    path = Path(recipe_path)
    if not path.exists():
        die(f"Recipe not found: {recipe_path}")
    text = path.read_text(errors="replace")
    vars_ = _bb_vars(text)
    inherits = _bb_inherits(text)
    src_uris = _bb_src_uris(text)

    stem = path.stem
    parts = stem.rsplit("_", 1)
    manifest.pkg_name = parts[0].lower()
    if len(parts) == 2:
        manifest.upstream_version = parts[1].lstrip("v")

    if "PN" in vars_:
        manifest.pkg_name = vars_["PN"].lower()
    if "PV" in vars_:
        raw_pv = vars_["PV"].lstrip("v")
        if re.search(r'git|AUTOINC|AUTOREV', raw_pv):
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            base = re.sub(r'\$\{[^}]+\}|AUTOINC\+|\+?git.*', '', raw_pv).strip("+- ")
            manifest.upstream_version = f"{base}+git{date_str}" if base else f"0+git{date_str}"
        else:
            manifest.upstream_version = raw_pv.replace("+git", "")

    manifest.summary     = vars_.get("SUMMARY", vars_.get("DESCRIPTION", manifest.summary))
    manifest.description = vars_.get("DESCRIPTION", manifest.description)
    manifest.homepage    = vars_.get("HOMEPAGE", "")
    manifest.license_spdx = _map_license(vars_.get("LICENSE", "UNKNOWN"))

    if "cmake" in inherits:
        manifest.buildsystem = "cmake"
        manifest.build_requires.append("cmake")
    elif "autotools" in inherits:
        manifest.buildsystem = "autotools"
        manifest.build_requires.extend(["autoconf", "automake", "libtool"])
    elif "meson" in inherits:
        manifest.buildsystem = "meson"
        manifest.build_requires.extend(["meson", "ninja-build"])

    for dep in vars_.get("DEPENDS", "").split():
        r = _yocto_dep_to_rpm(dep)
        if r and r not in manifest.build_requires:
            manifest.build_requires.append(r)
    for dep in vars_.get("RDEPENDS_" + manifest.pkg_name, vars_.get("RDEPENDS", "")).split():
        r = _yocto_dep_to_rpm(dep)
        if r and r not in manifest.requires:
            manifest.requires.append(r)

    is_prebuilt = (
        "do_compile[noexec]" in text or "INHIBIT_PACKAGE_STRIP" in text
        or "INSANE_SKIP" in text
        or any(re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)', u) for u in src_uris)
    )
    is_kmod = "module" in inherits

    if is_kmod:
        manifest.pkg_type = "kmod"
        manifest.arch = "aarch64"
    elif is_prebuilt:
        manifest.pkg_type = "prebuilt"
        manifest.arch = "aarch64"
        for uri in src_uris:
            if re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz)', uri):
                manifest.source0_url = uri
                manifest.source0_filename = uri.split("/")[-1]
                break
        manifest.source0_sha512 = vars_.get("SRC_URI[sha256sum]", manifest.source0_sha512)
    else:
        manifest.pkg_type = "source"
        for uri in src_uris:
            if uri.startswith(("git://", "gitsm://", "https://github", "https://git")):
                manifest.vcs_url = uri.replace("git://", "https://")
                break

    packages_var = vars_.get("PACKAGES", "")
    for pkg in packages_var.split():
        files_key = f"FILES:{pkg}"
        files_val = vars_.get(files_key, "")
        if files_val:
            manifest.split_packages.append((pkg.lower(), f"Files for {pkg}", files_val))


def parse_url(url: str, manifest: RpmManifest, force_kmod=False, force_prebuilt=False) -> None:
    is_tarball = bool(re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)(\?.*)?$', url))

    if is_tarball or force_prebuilt:
        manifest.pkg_type = "prebuilt"
        manifest.source0_url = url
        basename = url.split("/")[-1].split("?")[0]
        manifest.source0_filename = basename
        _name_version_from_filename(basename, manifest)
    elif force_kmod:
        manifest.pkg_type = "kmod"
        manifest.vcs_url = url
        _name_version_from_url(url, manifest)
    else:
        manifest.pkg_type = "source"
        manifest.vcs_url = url
        _name_version_from_url(url, manifest)

    # Auto-resolve version via API if still default
    if manifest.upstream_version == "0.0.1":
        resolved = _resolve_version_from_url(url)
        if resolved:
            manifest.upstream_version = resolved
            log(f"Auto-resolved version from API: {resolved}")

    # Build Source0 URL for git repos
    if not manifest.source0_url and manifest.vcs_url:
        clean = re.sub(r'\.git$', '', manifest.vcs_url)
        manifest.source0_url = (
            f"{clean}/archive/refs/tags/v%{{version}}.tar.gz"
        )
        manifest.source0_filename = f"{manifest.pkg_name}-%{{version}}.tar.gz"


def parse_local(local_path: str, manifest: RpmManifest, force_kmod=False, force_prebuilt=False) -> None:
    path = Path(local_path)
    if not path.exists():
        die(f"Path not found: {local_path}")

    if path.is_file() and re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)$', path.name):
        manifest.pkg_type = "prebuilt"
        manifest.source0_url = f"https://example.com/{path.name}"
        manifest.source0_filename = path.name
        _name_version_from_filename(path.name, manifest)
        return

    has_dkms = (path / "dkms.conf").exists()
    has_makefile = (path / "Makefile").exists() or (path / "Kbuild").exists()
    is_kmod = force_kmod or has_dkms
    if has_makefile and not is_kmod:
        for mf in ["Makefile", "Kbuild"]:
            mfp = path / mf
            if mfp.exists():
                if re.search(r'\bobj-m\b|\bKDIR\b|/lib/modules/', mfp.read_text(errors="replace")):
                    is_kmod = True
                break

    manifest.pkg_type = "kmod" if is_kmod else ("prebuilt" if force_prebuilt else "source")
    manifest.pkg_name = path.name.rsplit("_", 1)[0].rsplit("-", 1)[0].lower()

    if (path / "CMakeLists.txt").exists():
        manifest.buildsystem = "cmake"
        manifest.build_requires.append("cmake")
    elif (path / "configure.ac").exists() or (path / "configure.in").exists():
        manifest.buildsystem = "autotools"
        manifest.build_requires.extend(["autoconf", "automake", "libtool"])
    elif (path / "meson.build").exists():
        manifest.buildsystem = "meson"
        manifest.build_requires.extend(["meson", "ninja-build"])

    resolved = _resolve_version_from_local(path)
    if resolved:
        manifest.upstream_version = resolved
        log(f"Auto-resolved version from local repo: {resolved}")

# ---------------------------------------------------------------------------
# Spec file generators
# ---------------------------------------------------------------------------

def _build_macros(m: RpmManifest) -> tuple:
    """Return (prep, build, install) macro strings for the detected build system."""
    if m.buildsystem == "cmake":
        return "%cmake", "%cmake_build", "%cmake_install"
    elif m.buildsystem == "meson":
        return "%meson", "%meson_build", "%meson_install"
    else:
        # autotools or plain make
        return "%autosetup\n%configure", "%make_build", "%make_install"


def generate_spec(m: RpmManifest) -> str:
    """
    Generate a .spec file modelled exactly on the real
    qualcomm-linux/pkg-rpm-audioreach-pal reference spec.
    """
    # BuildRequires block
    base_br = ["autoconf", "automake", "libtool", "make", "gcc", "gcc-c++", "pkgconfig"]
    all_br  = list(dict.fromkeys(base_br + m.build_requires))
    br_block = "\n".join(f"BuildRequires:  {r}" for r in all_br)

    # Requires block
    req_block = "\n".join(f"Requires:       {r}" for r in m.requires) if m.requires else ""

    # Build system macros
    if m.buildsystem == "cmake":
        prep_block    = "%prep\n%autosetup -n %{name}-%{version}"
        build_block   = "%build\n%cmake\n%cmake_build"
        install_block = "%install\n%cmake_install\nfind %{buildroot} -name '*.la' -delete"
    elif m.buildsystem == "meson":
        prep_block    = "%prep\n%autosetup -n %{name}-%{version}"
        build_block   = "%build\n%meson\n%meson_build"
        install_block = "%install\n%meson_install"
    else:
        # autotools — matches the real audioreach-pal spec
        prep_block    = "%prep\n%autosetup -n %{name}-%{version}"
        build_block   = "%build\nautoreconf -fi\n%configure \\\n    --with-glib\n\n%make_build"
        install_block = "%install\n%make_install\nfind %{buildroot} -name '*.la' -delete"

    # %files sections
    if m.pkg_type == "kmod":
        files_main  = (
            "%files\n"
            "%license LICENSE\n"
            "/lib/modules/%{kernel_version}/extra/*.ko\n"
            "%{_sysconfdir}/modules-load.d/%{name}.conf"
        )
        files_devel = ""
    elif m.pkg_type == "prebuilt":
        files_main  = "%files\n%license LICENSE\n%doc README.md\n%{_libdir}/*"
        files_devel = ""
    else:
        files_main = (
            "%files\n"
            "%license LICENSE\n"
            f"%{{_libdir}}/lib{m.pkg_name}.so.*\n"
            f"%{{_libdir}}/libstream_*.so\n"
            f"%{{_libdir}}/libsession_*.so\n"
            f"%{{_libdir}}/libdev_*.so\n"
            f"%{{_libdir}}/libplugin_manager.so\n"
            "%config(noreplace) %{_sysconfdir}/*.xml"
        )
        files_devel = (
            "%package        devel\n"
            "Summary:        Development files for %{name}\n"
            "Requires:       %{name}%{?_isa} = %{version}-%{release}\n"
            "\n"
            "%description    devel\n"
            f"Headers and pkg-config files for building applications that use\n"
            f"the {m.summary}.\n"
            "\n"
            "%files devel\n"
            f"%{{_includedir}}/{m.pkg_name}/\n"
            f"%{{_libdir}}/lib{m.pkg_name}.so\n"
            "%{_libdir}/pkgconfig/*.pc"
        )

    # %changelog
    maintainer_name  = re.sub(r"\s*<.*>", "", m.maintainer).strip()
    maintainer_email_m = re.search(r"<(.+)>", m.maintainer)
    maintainer_email = maintainer_email_m.group(1) if maintainer_email_m else m.maintainer
    changelog = (
        f"* {m.changelog_date} {maintainer_name} <{maintainer_email}> "
        f"- {m.upstream_version}-{m.rpm_release}\n"
        f"- Initial RPM packaging of {m.pkg_name} version {m.upstream_version}."
    )

    arch_line = "ExclusiveArch:  aarch64" if m.pkg_type != "kmod" else "BuildArch:      noarch"

    parts = [
        "# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.",
        "# SPDX-License-Identifier: BSD-3-Clause",
        "%global debug_package %{nil}",
        "%global _lto_cflags %{nil}",
        "",
        f"Name:           {m.pkg_name}",
        f"Version:        {m.upstream_version}",
        f"Release:        {m.rpm_release}%{{?dist}}",
        f"Summary:        {m.summary}",
        arch_line,
        "",
        f"License:        {m.license_spdx}",
        f"URL:            {m.homepage or m.vcs_url or 'https://example.com'}",
        "Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz",
        "",
        br_block,
    ]
    if req_block:
        parts.append(req_block)
    parts += [
        "",
        "%description",
        _wrap_rpm_description(m.description),
        "",
    ]
    if files_devel:
        parts += [files_devel, ""]
    parts += [
        prep_block, "",
        build_block, "",
        install_block, "",
        files_main, "",
        "%changelog",
        changelog,
        "",
    ]
    return "\n".join(parts)


def generate_sources(m: RpmManifest) -> str:
    """
    dist-git sources file — exact format used by qualcomm-linux/pkg-rpm-audioreach-pal.
    SHA512 (filename) = hexdigest
    """
    return (
        f"SHA512 ({m.tarball_name}) = "
        f"{m.source0_sha512}\n"
    )


def generate_readme(m: RpmManifest) -> str:
    """README.md modelled on the real pkg-rpm-audioreach-pal README."""
    vcs_link = f"[{m.pkg_name}]({m.vcs_url})" if m.vcs_url else m.pkg_name
    return textwrap.dedent(f"""\
        <!--
        Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
        SPDX-License-Identifier: BSD-3-Clause
        -->
        # pkg-rpm-{m.pkg_name}

        RPM packaging for
        {vcs_link} on
        CentOS Stream 10 (aarch64).

        {m.description.strip()}
        The package is maintained on the CentOS Stream 10 (`c10s`) branch and uses
        the shared GitHub Actions build and release workflow.

        ---

        ## Repository Layout

        The `c10s` branch contains the RPM packaging files:

        | File | Purpose |
        |---|---|
        | `{m.pkg_name}.spec` | Builds the runtime libraries and `-devel` subpackage. |
        | `sources` | SHA-512 checksum for the upstream source archive. |
        | `README.md` | Package and repository documentation. |
        | `LICENSE.txt` | License for the RPM packaging repository. |

        The source archive is not committed to this repository. The spec file's
        `Source0` points to the upstream release, and the checksum in `sources` is
        verified before the RPM is built.

        ---

        ## Packages

        - `{m.pkg_name}`: {m.summary}.
        - `{m.pkg_name}-devel`: Headers and pkg-config files for building
          applications that use {m.summary}.

        ---

        ## Updating the package version

        1. Bump `Version:` in the spec (and the `Source0:` URL if its path changed).
        2. Recompute the checksum for the new tarball:
           ```bash
           sha512sum --tag {m.pkg_name}-<newversion>.tar.gz > sources
           ```
        3. Commit the spec + `sources`, open a PR (build verifies it), merge, then run
           **Release**. The first release fetches the new upstream tarball, verifies it,
           and caches it back to Artifactory automatically.

        ## License

        This project is licensed under the BSD 3-Clause License. See [LICENSE.txt](LICENSE.txt) for the complete license text.

        The upstream {m.pkg_name} source is licensed separately under
        `{m.license_spdx}`, as declared by `{m.pkg_name}.spec`.
    """)


def generate_build_on_pr(m: RpmManifest) -> str:
    """Exact copy of the real build-on-pr.yml from qualcomm-linux/pkg-rpm-audioreach-pal."""
    return textwrap.dedent(f"""\
        # Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
        # SPDX-License-Identifier: BSD-3-Clause
        # =============================================================================
        # Build on PR
        # =============================================================================
        # Builds the package's RPM(s) on every pull request so reviewers can confirm
        # the spec file still builds before merge.
        #
        # All build logic lives in the shared reusable workflow
        # qualcomm-linux/qcom-rpm-utils/.github/workflows/pkg-build-reusable-workflow.yml,
        # which reads the dist-git `sources` file, resolves each tarball from the
        # lookaside cache, verifies its checksum, and runs `rpmbuild` inside the
        # prebuilt `rpm-builder` container image pulled from GHCR.
        #
        # Required configuration:
        #   vars.SRC_TARBALL_CACHE_BASE_URL - Base URL of the lookaside cache (Actions variable).
        #
        # =============================================================================
        name: Build on PR

        on:
          pull_request:
            paths-ignore:
              - '**/*.md'

        permissions:
          contents: read
          packages: read

        # Prevent overlapping runs for the same PR; cancel superseded runs.
        concurrency:
          group: ${{{{ github.workflow }}}}-pr-${{{{ github.event.pull_request.number }}}}
          cancel-in-progress: true

        jobs:
          build:
            uses: qualcomm-linux/qcom-rpm-utils/.github/workflows/pkg-build-reusable-workflow.yml@{QCOM_RPM_UTILS_REF}
            with:
              qcom-rpm-utils-ref: {QCOM_RPM_UTILS_REF}
              cache-base-url: ${{{{ vars.SRC_TARBALL_CACHE_BASE_URL }}}}
    """)


def generate_pkg_release(m: RpmManifest) -> str:
    """Exact copy of the real pkg-release.yml from qualcomm-linux/pkg-rpm-audioreach-pal."""
    return textwrap.dedent(f"""\
        # Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
        # SPDX-License-Identifier: BSD-3-Clause
        # =============================================================================
        # Release
        # =============================================================================
        # Manually-triggered workflow that builds the package's RPM(s) and publishes
        # them to JFrog Artifactory.
        #
        # See the `main` branch's docs/reusable-workflows.md for the full documentation.
        # =============================================================================
        name: Release

        on:
          workflow_dispatch:
            inputs:
              publish-target:
                description: "Artifactory environment to publish to"
                type: choice
                options:
                  - staging
                  - prod
                default: staging

        permissions:
          contents: read
          packages: read

        jobs:
          release:
            uses: qualcomm-linux/qcom-rpm-utils/.github/workflows/pkg-release-reusable-workflow.yml@{QCOM_RPM_UTILS_REF}
            with:
              qcom-rpm-utils-ref: {QCOM_RPM_UTILS_REF}
              publish-target: ${{{{ inputs.publish-target }}}}
            secrets:
              QSC_API_KEY: ${{{{ secrets.QSC_API_KEY }}}}
              ARTIFACTORY_ACCESS_TOKEN: ${{{{ secrets.RPM_ARTIFACTORY_ACCESS_TOKEN }}}}
              PROD_QSC_API_KEY: ${{{{ secrets.PROD_QSC_API_KEY }}}}
              PROD_ARTIFACTORY_ACCESS_TOKEN: ${{{{ secrets.PROD_RPM_ARTIFACTORY_ACCESS_TOKEN }}}}
    """)


def generate_codeowners(m: RpmManifest) -> str:
    """CODEOWNERS — exact format from the real repo."""
    maintainer_handle = re.sub(r"\s*<.*>", "", m.maintainer).strip().lower().replace(" ", "-")
    return textwrap.dedent(f"""\
        # Default reviewers for all changes in entire repository,
        # unless a later match takes precedence
        *  @{maintainer_handle}
    """)


def generate_dependabot() -> str:
    """dependabot.yaml — exact copy from the real repo (daily github-actions updates)."""
    return textwrap.dedent("""\
        # To get started with Dependabot version updates, you'll need to specify which
        # package ecosystems to update and where the package manifests are located.
        # Please see the documentation for all configuration options:
        # https://docs.github.com/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

        version: 2
        updates:
          - package-ecosystem: "github-actions" # See documentation for possible values
            directory: "/" # This points to .github/workflows
            schedule:
              interval: "daily"
    """)


def generate_bug_report() -> str:
    """bug_report.md — exact copy from the real repo."""
    return textwrap.dedent("""\
        ---
        name: Bug report
        about: Create a report to help us improve
        title: ''
        labels: ''
        assignees: ''

        ---

        **Describe the bug**
        A clear and concise description of what the bug is.

        **To Reproduce**
        Steps to reproduce the behavior:
        1. Go to '...'
        2. Click on '....'
        3. Scroll down to '....'
        4. See error

        **Expected behavior**
        A clear and concise description of what you expected to happen.

        **Screenshots**
        If applicable, add screenshots to help explain your problem.

        **Desktop (please complete the following information):**
         - OS: [e.g. iOS]
         - Browser [e.g. chrome, safari]
         - Version [e.g. 22]

        **Smartphone (please complete the following information):**
         - Device: [e.g. iPhone6]
         - OS: [e.g. iOS8.1]
         - Browser [e.g. stock browser, safari]
         - Version [e.g. 22]

        **Additional context**
        Add any other context about the problem here.
    """)


def generate_feature_request() -> str:
    """feature_request.md — exact copy from the real repo."""
    return textwrap.dedent("""\
        ---
        name: Feature request
        about: Suggest an idea for this project
        title: ''
        labels: ''
        assignees: ''

        ---

        **Is your feature request related to a problem? Please describe.**
        A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

        **Describe the solution you'd like**
        A clear and concise description of what you want to happen.

        **Describe alternatives you've considered**
        A clear and concise description of any alternative solutions or features you've considered.

        **Additional context**
        Add any other context or screenshots about the feature request here.
    """)


def generate_pr_template() -> str:
    """pr_template.md — exact copy from the real repo."""
    return textwrap.dedent("""\
        ## Pull Request

        **Description**
        A clear and concise description of what this pull request does.

        **Related Issue**
        Link to the issue that this pull request addresses (e.g., `Fixes #123`).

        **Type of Change**
        Please delete options that are not relevant.
        - Bug fix (non-breaking change which fixes an issue)
        - New feature (non-breaking change which adds functionality)
        - Breaking change (fix or feature that would cause existing functionality to not work as expected)
        - Documentation update

        **Checklist**
        - [ ] My code follows the style guidelines of this project
        - [ ] I have performed a self-review of my own code
        - [ ] I have commented my code, particularly in hard-to-understand areas
        - [ ] I have made corresponding changes to the documentation
        - [ ] My changes generate no new warnings
        - [ ] I have added tests that prove my fix is effective or that my feature works
        - [ ] New and existing unit tests pass locally with my changes
        - [ ] Any dependent changes have been merged and published in downstream modules

        **Additional Context**
        Add any other context or screenshots about the pull request here.
    """)


def generate_workflows_doc(m: RpmManifest) -> str:
    return textwrap.dedent(f"""\
        # CI / Build Workflows

        This repository uses the `qualcomm-linux/qcom-rpm-utils` reusable workflows
        to build and release the `{m.pkg_name}` RPM for CentOS Stream 10 (aarch64).

        ## Workflows

        | Workflow | Trigger | Purpose |
        |---|---|---|
        | `build-on-pr.yml` | Pull request | Build RPM on every PR |
        | `pkg-release.yml` | Manual (`workflow_dispatch`) | Build and publish to Artifactory |

        ## Branch layout

        | Branch | Role |
        |---|---|
        | `main` | Docs and template home |
        | `{DEFAULT_STREAM}` | CentOS Stream 10 packaging branch |

        On `{DEFAULT_STREAM}`:
        ```
        {m.pkg_name}.spec    # RPM spec file
        sources              # SHA-512 checksums of source tarballs
        ```

        ## Updating the package

        1. Bump `Version:` in `{m.pkg_name}.spec`.
        2. Update `sources` with the new tarball checksum:
           ```bash
           sha512sum --tag {m.pkg_name}-<new_version>.tar.gz > sources
           ```
        3. Add a `%changelog` entry.
        4. Open a PR against `{DEFAULT_STREAM}` — the build workflow runs automatically.
        5. After review, trigger the Release workflow to publish to Artifactory.

        ## Required repository configuration

        - **Actions variable**: `SRC_TARBALL_CACHE_BASE_URL` — base URL of the lookaside cache.
        - **Secret**: `RPM_ARTIFACTORY_ACCESS_TOKEN` — Artifactory publish credential.
        - **Environment**: `pkg-release-approval` — add required reviewers for the release gate.
        - **Runner**: `[self-hosted, platform-prd-u2404-arm64-large-od-ephem]` — provided by the reusable workflow.
    """)

# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_skeleton(m: RpmManifest, output_dir: str, dry_run: bool = False,
                   no_workflows: bool = False, no_sources: bool = False) -> None:
    out = Path(output_dir)
    gha = out / ".github"

    files = {}
    files[out / f"{m.pkg_name}.spec"]                                    = generate_spec(m)
    files[out / "README.md"]                                              = generate_readme(m)
    files[out / "docs" / "workflows.md"]                                  = generate_workflows_doc(m)
    files[gha / "CODEOWNERS"]                                             = generate_codeowners(m)
    files[gha / "dependabot.yaml"]                                        = generate_dependabot()
    files[gha / "ISSUE_TEMPLATE" / "bug_report.md"]                      = generate_bug_report()
    files[gha / "ISSUE_TEMPLATE" / "feature_request.md"]                 = generate_feature_request()
    files[gha / "PULL_REQUEST_TEMPLATE" / "pr_template.md"]              = generate_pr_template()

    if not no_sources:
        files[out / "sources"] = generate_sources(m)
    if not no_workflows:
        files[gha / "workflows" / "build-on-pr.yml"] = generate_build_on_pr(m)
        files[gha / "workflows" / "pkg-release.yml"] = generate_pkg_release(m)

    if dry_run:
        print("\n=== DRY RUN — files that would be generated ===")
        for path, content in sorted(files.items()):
            rel = path.relative_to(out)
            print(f"  {rel}  ({content.count(chr(10))} lines)")
        print(f"\nTotal: {len(files)} files")
        print(f"Package type:  {m.pkg_type}")
        print(f"Package name:  {m.pkg_name}")
        print(f"Version:       {m.upstream_version}-{m.rpm_release}")
        print(f"Build system:  {m.buildsystem or '(make)'}")
        return

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        log(f"Wrote {path}")

    info(f"Skeleton written to: {out}")
    info(f"Package type:        {m.pkg_type}")
    info(f"Package name:        {m.pkg_name}")
    info(f"Version:             {m.upstream_version}-{m.rpm_release}%{{?dist}}")
    info(f"Build system:        {m.buildsystem or '(make)'}")
    info("")
    info("Next steps:")
    info(f"  1. Download tarball and update sources:")
    info(f"     sha512sum --tag {m.tarball_name} > {out}/sources")
    info(f"  2. Push to GitHub on the '{DEFAULT_STREAM}' branch:")
    info(f"     cd {out} && git init && git checkout -b {DEFAULT_STREAM}")
    info(f"     git add {m.pkg_name}.spec sources && git push")
    info(f"  3. Open a PR — build-on-pr.yml runs automatically.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _name_version_from_url(url: str, manifest: RpmManifest) -> None:
    path_part = url.rstrip("/").split("/")[-1]
    path_part = re.sub(r'\.git$', '', path_part)
    parts = path_part.rsplit("_", 1)
    manifest.pkg_name = parts[0].lower()
    if len(parts) == 2 and re.match(r'[\d.]+', parts[1]):
        manifest.upstream_version = parts[1].lstrip("v")


def _name_version_from_filename(filename: str, manifest: RpmManifest) -> None:
    name = re.sub(r'\.(tar\.(gz|xz|bz2)|tgz|zip)$', '', filename)
    m = re.match(r'^([a-zA-Z][a-zA-Z0-9._-]+?)[-_](\d[\d.]+)', name)
    if m:
        manifest.pkg_name = m.group(1).lower()
        manifest.upstream_version = m.group(2)
    else:
        manifest.pkg_name = name.lower()


def _map_license(yocto_license: str) -> str:
    mapping = {
        "MIT": "MIT",
        "BSD": "BSD-3-Clause",
        "BSD-2-Clause": "BSD-2-Clause",
        "BSD-3-Clause": "BSD-3-Clause",
        "BSD-3-Clause-Clear": "BSD-3-Clause-Clear",
        "GPL-2.0": "GPL-2.0-only",
        "GPL-2.0-only": "GPL-2.0-only",
        "GPL-2.0-or-later": "GPL-2.0-or-later",
        "GPL-3.0": "GPL-3.0-only",
        "LGPL-2.1": "LGPL-2.1-only",
        "Apache-2.0": "Apache-2.0",
        "Proprietary": "LicenseRef-Qualcomm-Proprietary",
        "CLOSED": "LicenseRef-Qualcomm-Proprietary",
    }
    return mapping.get(yocto_license, yocto_license)


def _yocto_dep_to_rpm(dep: str) -> Optional[str]:
    skip = {"virtual/kernel", "virtual/libc", "virtual/libintl", "virtual/crypt"}
    if dep in skip or dep.startswith("virtual/"):
        return None
    mapping = {
        "libglib-2.0": "glib2-devel",
        "glib-2.0": "glib2-devel",
        "zlib": "zlib-devel",
        "openssl": "openssl-devel",
        "libusb1": "libusb1-devel",
        "libxml2": "libxml2-devel",
        "alsa-lib": "alsa-lib-devel",
        "pulseaudio": "pulseaudio-libs-devel",
        "dbus": "dbus-devel",
        "systemd": "systemd-devel",
        "udev": "libudev-devel",
    }
    return mapping.get(dep, f"{dep}-devel")


def _wrap_rpm_description(description: str, width: int = 72) -> str:
    lines = []
    for para in description.strip().split("\n\n"):
        lines.extend(textwrap.wrap(para.strip(), width=width))
        lines.append("")
    return "\n".join(lines).strip()

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rpm_packager",
        description="Generate an RPM packaging skeleton (spec + dist-git) for CentOS Stream 10.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s --url https://github.com/AudioReach/audioreach-pal
              %(prog)s --url https://github.com/AudioReach/audioreach-pipewire-plugin
              %(prog)s --recipe meta-qcom/recipes-audioreach/audioreach-pal/audioreach-pal_1.0.2.bb
              %(prog)s --path ./audioreach-pal --output /tmp/pkg-rpm-audioreach-pal
              %(prog)s --url https://github.com/AudioReach/audioreach-pal --dry-run --verbose
              %(prog)s --url https://github.com/AudioReach/audioreach-pal --upstream-version 1.0.3 --rpm-release 0.1
        """),
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--recipe", metavar="FILE", help="Yocto .bb recipe file")
    src.add_argument("--url",    metavar="URL",  help="Remote git repo or tarball URL")
    src.add_argument("--path",   metavar="PATH", help="Local source tree or tarball")

    p.add_argument("--output", "-o", metavar="DIR", default="./rpm-out",
                   help="Output directory (default: ./rpm-out)")
    p.add_argument("--maintainer", metavar="STR",
                   help='"Name <email>" for spec %%changelog')
    p.add_argument("--upstream-version", metavar="VER",
                   help="Override upstream version (auto-detected by default)")
    p.add_argument("--rpm-release", metavar="REV",
                   help="Override RPM Release field (auto-detected by default)")
    p.add_argument("--kmod",     action="store_true", help="Force kernel module package type")
    p.add_argument("--prebuilt", action="store_true", help="Force prebuilt package type")
    p.add_argument("--source",   action="store_true", help="Force source/library package type")
    p.add_argument("--split-packages", action="store_true",
                   help="Emit one %%package section per PACKAGES entry")
    p.add_argument("--no-workflows", action="store_true",
                   help="Skip GitHub Actions workflow generation")
    p.add_argument("--no-sources", action="store_true",
                   help="Skip sources file generation")
    p.add_argument("--dry-run",  action="store_true",
                   help="Print what would be generated without writing files")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p


def main() -> None:
    global VERBOSE
    parser = build_parser()
    args = parser.parse_args()
    VERBOSE = args.verbose

    manifest = RpmManifest()
    if args.maintainer:
        manifest.maintainer = args.maintainer

    if args.recipe:
        info(f"Parsing Yocto recipe: {args.recipe}")
        parse_recipe(args.recipe, manifest)
    elif args.url:
        info(f"Parsing URL: {args.url}")
        parse_url(args.url, manifest, force_kmod=args.kmod, force_prebuilt=args.prebuilt)
    elif args.path:
        info(f"Parsing local path: {args.path}")
        parse_local(args.path, manifest, force_kmod=args.kmod, force_prebuilt=args.prebuilt)

    # Type overrides
    if args.source:
        manifest.pkg_type = "source"
    elif args.kmod and manifest.pkg_type != "kmod":
        manifest.pkg_type = "kmod"
    elif args.prebuilt and manifest.pkg_type != "prebuilt":
        manifest.pkg_type = "prebuilt"

    # Version overrides (CLI wins)
    if args.upstream_version:
        manifest.upstream_version = args.upstream_version.lstrip("v")
        log(f"Upstream version overridden: {manifest.upstream_version}")

    # Auto or explicit RPM release
    if args.rpm_release:
        manifest.rpm_release = args.rpm_release
        log(f"RPM release explicitly set: {manifest.rpm_release}")
    else:
        manifest.rpm_release = _auto_rpm_release(args.output, manifest.upstream_version)
        log(f"Auto RPM release: {manifest.rpm_release}")

    out = Path(args.output)
    if out.exists() and not args.dry_run:
        die(f"Output directory already exists: {out}\nRemove it or choose a different --output path.")

    write_skeleton(manifest, args.output,
                   dry_run=args.dry_run,
                   no_workflows=args.no_workflows,
                   no_sources=args.no_sources)


if __name__ == "__main__":
    main()
