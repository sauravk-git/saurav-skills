#!/usr/bin/env python3
"""
debian_packager.py — Debian packaging skeleton generator
Supports: Yocto recipe, remote URL (git/tarball), local source tree or tarball.
Package types: source/userspace, prebuilt tarball, DKMS kernel module.
Stdlib-only. Python 3.8+.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import urllib.request
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_DISTRO = os.environ.get("DEBIAN_DISTRO", "trixie")
DEFAULT_COMPAT = "13"
DEFAULT_BRANCH = "qcom/debian/trixie/latest"
DEFAULT_UPSTREAM_BRANCH = os.environ.get("UPSTREAM_BRANCH", "qcom/upstream/latest")
DEFAULT_MAINTAINER = os.environ.get(
    "DEBEMAIL_FULL", "Saurav Kumar <sauravk@qti.qualcomm.com>"
)

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
VERBOSE = False


def log(msg: str) -> None:
    if VERBOSE:
        print(f"[debian-packager] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"  {msg}")


def warn(msg: str) -> None:
    print(f"  WARNING: {msg}", file=sys.stderr)


def die(msg: str) -> None:
    print(f"  ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Auto-versioning helpers
# ---------------------------------------------------------------------------

def _fetch_latest_github_tag(owner: str, repo: str) -> Optional[str]:
    """Query the GitHub API for the latest semver tag. Returns bare version string or None."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=20"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json",
                                                    "User-Agent": "debian-packager-skill/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            tags = json.loads(resp.read())
        # Pick the first tag that looks like a semver (v1.2.3 or 1.2.3)
        for tag in tags:
            name = tag.get("name", "")
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", name)
            if m:
                log(f"GitHub latest tag for {owner}/{repo}: {name}")
                return m.group(1)
    except Exception as exc:
        log(f"GitHub tag lookup failed for {owner}/{repo}: {exc}")
    return None


def _fetch_latest_gitlab_tag(host: str, owner: str, repo: str) -> Optional[str]:
    """Query a GitLab API for the latest semver tag. Returns bare version string or None."""
    try:
        project = urllib.request.quote(f"{owner}/{repo}", safe="")
        url = f"https://{host}/api/v4/projects/{project}/repository/tags?per_page=20&order_by=version"
        req = urllib.request.Request(url, headers={"User-Agent": "debian-packager-skill/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            tags = json.loads(resp.read())
        for tag in tags:
            name = tag.get("name", "")
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", name)
            if m:
                log(f"GitLab latest tag for {owner}/{repo}: {name}")
                return m.group(1)
    except Exception as exc:
        log(f"GitLab tag lookup failed for {host}/{owner}/{repo}: {exc}")
    return None


def _resolve_version_from_url(url: str) -> Optional[str]:
    """
    Try to resolve the latest release version for a git URL by querying
    the GitHub or GitLab API. Falls back to None if unavailable.
    """
    # GitHub: https://github.com/<owner>/<repo>[.git]
    m = re.match(r"https?://github\.com/([^/]+)/([^/\.]+)", url)
    if m:
        return _fetch_latest_github_tag(m.group(1), m.group(2))

    # GitLab SaaS: https://gitlab.com/<owner>/<repo>[.git]
    m = re.match(r"https?://gitlab\.com/([^/]+)/([^/\.]+)", url)
    if m:
        return _fetch_latest_gitlab_tag("gitlab.com", m.group(1), m.group(2))

    # Self-hosted GitLab (heuristic — path has at least owner/repo)
    m = re.match(r"https?://([^/]+)/([^/]+)/([^/\.]+)", url)
    if m:
        host, owner, repo = m.group(1), m.group(2), m.group(3)
        if host not in ("github.com", "gitlab.com"):
            return _fetch_latest_gitlab_tag(host, owner, repo)

    return None


def _resolve_version_from_local(path: Path) -> Optional[str]:
    """
    Try to resolve the version from a local git clone using git describe,
    then git log for date-based snapshots, then a VERSION/version.txt file.
    Returns a bare version string or None.
    """
    if not (path / ".git").exists():
        # Check for a VERSION or version.txt file
        for vfile in ["VERSION", "version.txt", "version", "VERSION.txt"]:
            vpath = path / vfile
            if vpath.exists():
                raw = vpath.read_text().strip().splitlines()[0].strip()
                m = re.match(r"v?(\d+\.\d+[\.\d]*)", raw)
                if m:
                    log(f"Version from {vfile}: {m.group(1)}")
                    return m.group(1)
        return None

    # git describe --tags --abbrev=0 — exact tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(path), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)$", tag)
            if m:
                log(f"git describe exact tag: {tag}")
                return m.group(1)
            # Annotated tag with distance: v1.0.2-14-gabcdef → 1.0.2+git<date>
            m = re.match(r"^v?(\d+\.\d+[\.\d]*)-\d+-g[0-9a-f]+$", tag)
            if m:
                date_str = _git_commit_date(path)
                ver = f"{m.group(1)}+git{date_str}"
                log(f"git describe with distance → snapshot version: {ver}")
                return ver
    except Exception as exc:
        log(f"git describe failed: {exc}")

    # Fallback: date-based snapshot from latest commit
    date_str = _git_commit_date(path)
    if date_str:
        ver = f"0+git{date_str}"
        log(f"No tag found — using date snapshot: {ver}")
        return ver

    return None


def _git_commit_date(path: Path) -> str:
    """Return YYYYMMDD of the latest commit, or today's date as fallback."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d"],
            cwd=str(path), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return datetime.datetime.now().strftime("%Y%m%d")


def _auto_debian_revision(output_dir: str, upstream_version: str) -> str:
    """
    Determine the correct debian revision automatically:
    - If the output dir does not exist yet → revision 1 (first packaging).
    - If it exists and contains a changelog with the same upstream version
      → increment the existing revision by 1 (re-packaging).
    - If it exists with a different upstream version → reset to 1.
    """
    changelog = Path(output_dir) / "debian" / "changelog"
    if not changelog.exists():
        log("No existing changelog found — debian revision: 1")
        return "1"

    try:
        first_line = changelog.read_text().splitlines()[0]
        # e.g. "audioreach-pal (1.0.2-3) trixie; urgency=medium"
        m = re.match(r"^\S+\s+\(([^)]+)\)", first_line)
        if not m:
            return "1"
        existing_full = m.group(1)          # e.g. "1.0.2-3"
        parts = existing_full.rsplit("-", 1)
        existing_upstream = parts[0]
        existing_rev = parts[1] if len(parts) == 2 else "1"

        if existing_upstream == upstream_version:
            # Same upstream — bump revision
            try:
                new_rev = str(int(existing_rev) + 1)
            except ValueError:
                # Non-numeric revision (e.g. 0~rc1) — append .1
                new_rev = existing_rev + ".1"
            log(f"Same upstream {upstream_version} already packaged at rev {existing_rev} → bumping to {new_rev}")
            return new_rev
        else:
            log(f"Upstream changed {existing_upstream} → {upstream_version} — resetting revision to 1")
            return "1"
    except Exception as exc:
        log(f"Could not read existing changelog: {exc}")
        return "1"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class PackageManifest:
    """Holds all metadata needed to render the debian/ skeleton."""

    def __init__(self):
        self.pkg_name: str = "unknown"
        self.upstream_version: str = "0.0.1"
        self.debian_revision: str = "1"
        self.summary: str = "No summary available"
        self.description: str = "No description available."
        self.homepage: str = ""
        self.license_name: str = "UNKNOWN"
        self.license_text: str = ""
        self.maintainer: str = DEFAULT_MAINTAINER
        self.distro: str = DEFAULT_DISTRO
        self.architecture: str = "any"
        self.build_depends: list = ["debhelper-compat (= 13)"]
        self.depends: list = ["${shlibs:Depends}", "${misc:Depends}"]
        self.vcs_git: str = ""
        self.vcs_browser: str = ""
        self.upstream_url: str = ""
        self.tarball_url: str = ""
        self.tarball_sha256: str = ""
        self.buildsystem: str = ""  # cmake, autoconf, meson, ""
        self.pkg_type: str = "source"  # source | prebuilt | dkms
        self.split_packages: list = []  # [(name, files_glob)]
        self.install_rules: list = []  # [(src, dest)]
        self.dkms_module_name: str = ""
        self.dkms_module_version: str = ""
        self.source_format: str = "3.0 (quilt)"

    @property
    def full_version(self) -> str:
        return f"{self.upstream_version}-{self.debian_revision}"

    @property
    def source_name(self) -> str:
        return self.pkg_name

    def to_dict(self) -> dict:
        return self.__dict__


# ---------------------------------------------------------------------------
# Yocto recipe parser
# ---------------------------------------------------------------------------
_BB_VAR = re.compile(r'^([A-Z_][A-Z0-9_:]*)\s*(?:\??=|:=|\.=|=\+|=\.)\s*"(.*)"', re.M)
_BB_INHERIT = re.compile(r'^inherit\s+(.+)', re.M)
_BB_SRC_URI = re.compile(r'SRC_URI\s*(?:\??=|:=|\+=|\.=)\s*"([^"]*)"', re.M | re.S)
_BB_SRC_URI_CONT = re.compile(r'SRC_URI\s*\+=\s*"([^"]*)"', re.M | re.S)


def _bb_vars(text: str) -> dict:
    """Extract all variable assignments from a .bb file into a flat dict."""
    result = {}
    for m in _BB_VAR.finditer(text):
        result[m.group(1)] = m.group(2)
    return result


def _bb_inherits(text: str) -> list:
    classes = []
    for m in _BB_INHERIT.finditer(text):
        classes.extend(m.group(1).split())
    return classes


def _bb_src_uris(text: str) -> list:
    uris = []
    for m in _BB_SRC_URI.finditer(text):
        uris.extend(m.group(1).split())
    return [u.strip().split(";")[0] for u in uris if u.strip()]


def parse_recipe(recipe_path: str, manifest: PackageManifest) -> None:
    """Populate manifest from a Yocto .bb recipe file."""
    path = Path(recipe_path)
    if not path.exists():
        die(f"Recipe not found: {recipe_path}")

    text = path.read_text(errors="replace")
    vars_ = _bb_vars(text)
    inherits = _bb_inherits(text)
    src_uris = _bb_src_uris(text)

    log(f"Recipe vars: {list(vars_.keys())}")
    log(f"Inherits: {inherits}")
    log(f"SRC_URIs: {src_uris}")

    # Package name from filename: foo_1.0.bb → foo
    stem = path.stem  # e.g. fastrpc_1.0.6
    parts = stem.rsplit("_", 1)
    manifest.pkg_name = _sanitize_pkg_name(parts[0])
    if len(parts) == 2:
        manifest.upstream_version = parts[1].lstrip("v")

    # Override with recipe vars
    if "PN" in vars_:
        manifest.pkg_name = _sanitize_pkg_name(vars_["PN"])
    if "PV" in vars_:
        raw_pv = vars_["PV"].lstrip("v")
        # Normalise Yocto git/AUTOINC PV patterns to a usable version
        # e.g. "1.0+git${AUTOREV}" → "1.0+git<today>", "git" → "0+git<today>"
        if re.search(r'git|AUTOINC|AUTOREV', raw_pv):
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            base = re.sub(r'\$\{[^}]+\}|AUTOINC\+|\+?git.*', '', raw_pv).strip("+- ")
            manifest.upstream_version = f"{base}+git{date_str}" if base else f"0+git{date_str}"
            log(f"Normalised git PV '{raw_pv}' → '{manifest.upstream_version}'")
        else:
            manifest.upstream_version = raw_pv.replace("+git", "")

    manifest.summary = vars_.get("SUMMARY", vars_.get("DESCRIPTION", manifest.summary))
    manifest.description = vars_.get("DESCRIPTION", manifest.description)
    manifest.homepage = vars_.get("HOMEPAGE", "")
    manifest.license_name = _map_license(vars_.get("LICENSE", "UNKNOWN"))

    # Build system
    if "cmake" in inherits:
        manifest.buildsystem = "cmake"
        manifest.build_depends.append("cmake")
    elif "autotools" in inherits:
        manifest.buildsystem = "autoconf"
        manifest.build_depends.append("autoconf")
        manifest.build_depends.append("automake")
    elif "meson" in inherits:
        manifest.buildsystem = "meson"
        manifest.build_depends.append("meson")
        manifest.build_depends.append("ninja-build")

    # DEPENDS → Build-Depends
    for dep in vars_.get("DEPENDS", "").split():
        deb_dep = _yocto_dep_to_deb(dep)
        if deb_dep and deb_dep not in manifest.build_depends:
            manifest.build_depends.append(deb_dep)

    # RDEPENDS → Depends
    for dep in vars_.get("RDEPENDS_" + manifest.pkg_name, vars_.get("RDEPENDS", "")).split():
        deb_dep = _yocto_dep_to_deb(dep)
        if deb_dep and deb_dep not in manifest.depends:
            manifest.depends.append(deb_dep)

    # Detect package type
    is_prebuilt = (
        "do_compile[noexec]" in text
        or "INHIBIT_PACKAGE_STRIP" in text
        or "INSANE_SKIP" in text
        or any(re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)', u) for u in src_uris)
    )
    is_dkms = "module" in inherits

    if is_dkms:
        manifest.pkg_type = "dkms"
        manifest.architecture = "all"
        manifest.dkms_module_name = manifest.pkg_name
        manifest.dkms_module_version = manifest.upstream_version
        manifest.build_depends.extend(["dkms", "linux-headers-generic"])
    elif is_prebuilt:
        manifest.pkg_type = "prebuilt"
        manifest.architecture = "arm64"
        # Find tarball URI
        for uri in src_uris:
            if re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz)', uri):
                manifest.tarball_url = uri
                break
        manifest.tarball_sha256 = vars_.get("SRC_URI[sha256sum]", "")
    else:
        manifest.pkg_type = "source"
        # Find git URI
        for uri in src_uris:
            if uri.startswith(("git://", "gitsm://", "https://github", "https://git")):
                manifest.upstream_url = uri.replace("git://", "https://")
                manifest.vcs_git = manifest.upstream_url
                manifest.vcs_browser = re.sub(r'\.git$', '', manifest.upstream_url)
                break

    # Split packages
    packages_var = vars_.get("PACKAGES", "")
    for pkg in packages_var.split():
        files_key = f"FILES:{pkg}"
        files_val = vars_.get(files_key, "")
        if files_val:
            manifest.split_packages.append((_sanitize_pkg_name(pkg), files_val))

    log(f"Detected type: {manifest.pkg_type}")


# ---------------------------------------------------------------------------
# URL input handler
# ---------------------------------------------------------------------------
def parse_url(url: str, manifest: PackageManifest, force_dkms: bool = False,
              force_prebuilt: bool = False) -> None:
    """Populate manifest from a remote URL (git repo or tarball)."""
    is_tarball = bool(re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)(\?.*)?$', url))

    if is_tarball or force_prebuilt:
        manifest.pkg_type = "prebuilt"
        manifest.architecture = "arm64"
        manifest.tarball_url = url
        # Derive name/version from URL basename
        basename = url.split("/")[-1].split("?")[0]
        _name_version_from_filename(basename, manifest)
    elif force_dkms:
        manifest.pkg_type = "dkms"
        manifest.architecture = "all"
        manifest.upstream_url = url
        manifest.vcs_git = url
        _name_version_from_url(url, manifest)
        if manifest.upstream_version == "0.0.1":
            resolved = _resolve_version_from_url(url)
            if resolved:
                manifest.upstream_version = resolved
                log(f"Auto-resolved upstream version from API (dkms): {resolved}")
        manifest.dkms_module_name = manifest.pkg_name
        manifest.dkms_module_version = manifest.upstream_version
        manifest.build_depends.extend(["dkms", "linux-headers-generic"])
    else:
        manifest.pkg_type = "source"
        manifest.upstream_url = url
        manifest.vcs_git = url
        manifest.vcs_browser = re.sub(r'\.git$', '', url)
        _name_version_from_url(url, manifest)
        # Auto-resolve version from GitHub/GitLab API if not found in URL
        if manifest.upstream_version == "0.0.1":
            resolved = _resolve_version_from_url(url)
            if resolved:
                manifest.upstream_version = resolved
                log(f"Auto-resolved upstream version from API: {resolved}")


def _name_version_from_url(url: str, manifest: PackageManifest) -> None:
    """Derive package name and version from a git URL."""
    path_part = url.rstrip("/").split("/")[-1]
    path_part = re.sub(r'\.git$', '', path_part)
    parts = path_part.rsplit("_", 1)
    manifest.pkg_name = _sanitize_pkg_name(parts[0])
    if len(parts) == 2 and re.match(r'[\d.]+', parts[1]):
        manifest.upstream_version = parts[1].lstrip("v")


def _name_version_from_filename(filename: str, manifest: PackageManifest) -> None:
    """Derive package name and version from a tarball filename."""
    # Strip extensions
    name = re.sub(r'\.(tar\.(gz|xz|bz2)|tgz|zip)$', '', filename)
    # Try foo_1.2_arch or foo-1.2
    m = re.match(r'^([a-zA-Z][a-zA-Z0-9._-]+?)[-_](\d[\d.]+)', name)
    if m:
        manifest.pkg_name = _sanitize_pkg_name(m.group(1))
        manifest.upstream_version = m.group(2)
    else:
        manifest.pkg_name = _sanitize_pkg_name(name)


# ---------------------------------------------------------------------------
# Local path handler
# ---------------------------------------------------------------------------
def parse_local(local_path: str, manifest: PackageManifest, force_dkms: bool = False,
                force_prebuilt: bool = False) -> None:
    """Populate manifest from a local source tree or tarball."""
    path = Path(local_path)
    if not path.exists():
        die(f"Path not found: {local_path}")

    if path.is_file() and re.search(r'\.(tar\.gz|tar\.xz|tar\.bz2|tgz|zip)$', path.name):
        manifest.pkg_type = "prebuilt"
        manifest.architecture = "arm64"
        _name_version_from_filename(path.name, manifest)
        manifest.tarball_url = f"file://{path.resolve()}"
        return

    # It's a directory — detect type
    has_dkms_conf = (path / "dkms.conf").exists()
    has_makefile = (path / "Makefile").exists() or (path / "Kbuild").exists()
    is_dkms = force_dkms or has_dkms_conf
    if has_makefile and not is_dkms:
        makefile_text = ""
        for mf in ["Makefile", "Kbuild"]:
            mfp = path / mf
            if mfp.exists():
                makefile_text = mfp.read_text(errors="replace")
                break
        if re.search(r'\bobj-m\b|\bKDIR\b|/lib/modules/', makefile_text):
            is_dkms = True

    if is_dkms or force_dkms:
        manifest.pkg_type = "dkms"
        manifest.architecture = "all"
        manifest.build_depends.extend(["dkms", "linux-headers-generic"])
        manifest.dkms_module_name = manifest.pkg_name
        manifest.dkms_module_version = manifest.upstream_version
    elif force_prebuilt:
        manifest.pkg_type = "prebuilt"
        manifest.architecture = "arm64"
    else:
        manifest.pkg_type = "source"

    # Try to read name from directory
    manifest.pkg_name = _sanitize_pkg_name(path.name.rsplit("_", 1)[0].rsplit("-", 1)[0])

    # Auto-resolve version from git describe / VERSION file
    resolved = _resolve_version_from_local(path)
    if resolved:
        manifest.upstream_version = resolved
        log(f"Auto-resolved upstream version from local repo: {resolved}")

    # Detect build system
    if (path / "CMakeLists.txt").exists():
        manifest.buildsystem = "cmake"
        manifest.build_depends.append("cmake")
    elif (path / "configure.ac").exists() or (path / "configure.in").exists():
        manifest.buildsystem = "autoconf"
        manifest.build_depends.extend(["autoconf", "automake"])
    elif (path / "meson.build").exists():
        manifest.buildsystem = "meson"
        manifest.build_depends.extend(["meson", "ninja-build"])


# ---------------------------------------------------------------------------
# File generators
# ---------------------------------------------------------------------------

def generate_control(m: PackageManifest) -> str:
    bd = ", ".join(sorted(set(m.build_depends)))
    deps = ", ".join(sorted(set(m.depends)))
    vcs_lines = ""
    if m.vcs_git:
        vcs_lines = f"Vcs-Git: {m.vcs_git}\n"
    if m.vcs_browser:
        vcs_lines += f"Vcs-Browser: {m.vcs_browser}\n"
    homepage_line = f"Homepage: {m.homepage}\n" if m.homepage else ""

    source_stanza = textwrap.dedent(f"""\
        Source: {m.source_name}
        Section: libs
        Priority: optional
        Maintainer: {m.maintainer}
        Build-Depends: {bd}
        Standards-Version: 4.6.2
        Rules-Requires-Root: no
        {homepage_line}{vcs_lines}
    """).rstrip()

    desc_wrapped = _wrap_description(m.summary, m.description)

    if m.pkg_type == "dkms":
        binary_stanza = textwrap.dedent(f"""\
            Package: {m.pkg_name}-dkms
            Architecture: {m.architecture}
            Depends: {deps}, dkms
            Description: {desc_wrapped}
        """).rstrip()
    elif m.split_packages:
        binary_stanzas = []
        for pkg, _ in m.split_packages:
            binary_stanzas.append(textwrap.dedent(f"""\
                Package: {pkg}
                Architecture: {m.architecture}
                Depends: {deps}
                Description: {desc_wrapped}
            """).rstrip())
        binary_stanza = "\n\n".join(binary_stanzas)
    else:
        binary_stanza = textwrap.dedent(f"""\
            Package: {m.pkg_name}
            Architecture: {m.architecture}
            Depends: {deps}
            Description: {desc_wrapped}
        """).rstrip()

    return source_stanza + "\n\n" + binary_stanza + "\n"


def generate_changelog(m: PackageManifest) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    return textwrap.dedent(f"""\
        {m.source_name} ({m.full_version}) {m.distro}; urgency=medium

          * Initial Debian packaging.

         -- {m.maintainer}  {date_str}
    """)


def generate_copyright(m: PackageManifest) -> str:
    year = datetime.datetime.now().year
    upstream_url_line = f"Source: {m.upstream_url or m.tarball_url or 'https://example.com'}"
    return textwrap.dedent(f"""\
        Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
        Upstream-Name: {m.pkg_name}
        {upstream_url_line}

        Files: *
        Copyright: {year} Qualcomm Technologies, Inc.
        License: {m.license_name}

        Files: debian/*
        Copyright: {year} {m.maintainer}
        License: {m.license_name}

        License: {m.license_name}
         {m.license_text or 'See upstream source for full license text.'}
    """)


def generate_rules(m: PackageManifest) -> str:
    bs_line = ""
    if m.buildsystem:
        bs_line = f" --buildsystem={m.buildsystem}"

    if m.pkg_type == "prebuilt":
        return textwrap.dedent(f"""\
            #!/usr/bin/make -f
            %:
            \tdh $@{bs_line}

            override_dh_auto_build:
            \t# Prebuilt package — no compilation step
            \t:

            override_dh_auto_test:
            \t:
        """)
    elif m.pkg_type == "dkms":
        return textwrap.dedent(f"""\
            #!/usr/bin/make -f
            %:
            \tdh $@ --with dkms{bs_line}

            override_dh_auto_build:
            \t:

            override_dh_auto_test:
            \t:
        """)
    else:
        return textwrap.dedent(f"""\
            #!/usr/bin/make -f
            %:
            \tdh $@{bs_line}
        """)


def generate_gbp_conf(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        [DEFAULT]
        debian-branch = {DEFAULT_BRANCH}
        upstream-branch = {DEFAULT_UPSTREAM_BRANCH}
        upstream-tag = upstream/%(version)s
        sign-tags = False
        pristine-tar = True

        [buildpackage]
        export-dir = ../build-area/

        [import-orig]
        merge-mode = replace
    """)


def generate_watch(m: PackageManifest) -> str:
    if m.pkg_type == "prebuilt" and m.tarball_url:
        url = m.tarball_url
        return textwrap.dedent(f"""\
            version=4
            opts="mode=http,pgpmode=none" \\
            {url} .*/{m.pkg_name}[-_]([\d.]+).*\\.tar\\.gz
        """)
    elif m.vcs_browser:
        browser = m.vcs_browser.rstrip("/")
        return textwrap.dedent(f"""\
            version=4
            opts="mode=git,pgpmode=none" \\
            {browser} refs/tags/v?([\d.]+)
        """)
    else:
        return textwrap.dedent(f"""\
            version=4
            # TODO: configure watch URL for {m.pkg_name}
            # opts="mode=http" https://example.com/downloads/{m.pkg_name}[-_]([\d.]+)\\.tar\\.gz
        """)


def generate_source_format(m: PackageManifest) -> str:
    return m.source_format + "\n"


def generate_compat(m: PackageManifest) -> str:
    return DEFAULT_COMPAT + "\n"


def generate_install(m: PackageManifest, pkg_name: str, files_glob: str) -> str:
    lines = []
    for glob in files_glob.split():
        lines.append(glob)
    return "\n".join(lines) + "\n"


def generate_dkms_conf(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        PACKAGE_NAME="{m.dkms_module_name}"
        PACKAGE_VERSION="{m.dkms_module_version}"
        BUILT_MODULE_NAME[0]="{m.dkms_module_name}"
        DEST_MODULE_LOCATION[0]="/updates/dkms"
        AUTOINSTALL="yes"
        MAKE[0]="make -C ${{kernel_source_dir}} M=${{dkms_tree}}/${{PACKAGE_NAME}}/${{PACKAGE_VERSION}}/build"
        CLEAN="make -C ${{kernel_source_dir}} M=${{dkms_tree}}/${{PACKAGE_NAME}}/${{PACKAGE_VERSION}}/build clean"
    """)


def generate_postinst(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        #!/bin/sh
        set -e
        case "$1" in
            configure)
                dkms add -m {m.dkms_module_name} -v {m.dkms_module_version} --rpm_safe_upgrade || true
                dkms build -m {m.dkms_module_name} -v {m.dkms_module_version} || true
                dkms install -m {m.dkms_module_name} -v {m.dkms_module_version} --force || true
                ;;
        esac
        #DEBHELPER#
    """)


def generate_prerm(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        #!/bin/sh
        set -e
        case "$1" in
            remove|upgrade|deconfigure)
                dkms remove -m {m.dkms_module_name} -v {m.dkms_module_version} --all || true
                ;;
        esac
        #DEBHELPER#
    """)


def generate_build_sh_source(m: PackageManifest) -> str:
    clone_url = m.upstream_url or m.vcs_git or "https://example.com/FIXME.git"
    return textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # build.sh — source/userspace package builder for {m.pkg_name}
        set -euo pipefail

        PKG="{m.pkg_name}"
        VERSION="{m.upstream_version}"
        CLONE_URL="{clone_url}"
        BRANCH="{DEFAULT_UPSTREAM_BRANCH}"
        WORKDIR="$(mktemp -d /tmp/${{PKG}}-build.XXXXXX)"

        echo "[build] Working directory: $WORKDIR"
        echo "[build] Cloning $CLONE_URL ..."
        git clone --depth=1 --branch "$BRANCH" "$CLONE_URL" "$WORKDIR/src" 2>/dev/null \\
            || git clone --depth=1 "$CLONE_URL" "$WORKDIR/src"

        echo "[build] Overlaying debian/ ..."
        cp -r "$(dirname "$0")/debian" "$WORKDIR/src/"

        echo "[build] Installing build dependencies ..."
        cd "$WORKDIR/src"
        dpkg-checkbuilddeps 2>&1 | grep -oP 'Unmet.*: \\K.*' | xargs -r sudo apt-get install -y || true

        echo "[build] Building package ..."
        debuild -uc -us -b

        echo "[build] Done. Packages in $WORKDIR/"
        ls -lh "$WORKDIR"/*.deb 2>/dev/null || ls -lh ../*.deb
    """)


def generate_build_sh_prebuilt(m: PackageManifest) -> str:
    sha256_check = ""
    if m.tarball_sha256:
        sha256_check = textwrap.dedent(f"""\
            EXPECTED_SHA256="{m.tarball_sha256}"
            ACTUAL_SHA256=$(sha256sum "$TARBALL" | awk '{{print $1}}')
            if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
                echo "[build] ERROR: SHA-256 mismatch!"
                echo "  expected: $EXPECTED_SHA256"
                echo "  actual:   $ACTUAL_SHA256"
                exit 1
            fi
            echo "[build] SHA-256 verified OK"
        """)

    return textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # build.sh — prebuilt tarball package builder for {m.pkg_name}
        # Usage:
        #   ./build.sh                          — fetch via uscan
        #   ./build.sh /path/to/tarball.tar.gz  — use local tarball
        #   ./build.sh /path/to/unpacked-dir    — use unpacked directory
        set -euo pipefail

        PKG="{m.pkg_name}"
        VERSION="{m.upstream_version}"
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        WORKDIR="$(mktemp -d /tmp/${{PKG}}-build.XXXXXX)"

        echo "[build] Working directory: $WORKDIR"
        cp -r "$SCRIPT_DIR/debian" "$WORKDIR/"

        if [ $# -eq 0 ]; then
            echo "[build] Fetching tarball via uscan ..."
            cd "$WORKDIR"
            cp -r "$SCRIPT_DIR/debian" .
            uscan --force-download --destdir "$WORKDIR" --package "$PKG" \\
                  --upstream-version "$VERSION" --watchfile "$SCRIPT_DIR/debian/watch"
            TARBALL=$(ls "$WORKDIR"/*.tar.* 2>/dev/null | head -1)
        elif [ -d "$1" ]; then
            echo "[build] Using unpacked directory: $1"
            TARBALL=""
            UNPACK_DIR="$1"
        else
            TARBALL="$1"
            echo "[build] Using local tarball: $TARBALL"
        fi

        if [ -n "${{TARBALL:-}}" ]; then
            {sha256_check}
            echo "[build] Repacking tarball with canonical top-level ..."
            mkdir -p "$WORKDIR/$PKG-$VERSION"
            tar -xf "$TARBALL" -C "$WORKDIR/$PKG-$VERSION" --strip-components=1
            UNPACK_DIR="$WORKDIR/$PKG-$VERSION"
        fi

        echo "[build] Overlaying debian/ ..."
        cp -r "$WORKDIR/debian" "$UNPACK_DIR/"

        echo "[build] Building package ..."
        cd "$UNPACK_DIR"
        dpkg-buildpackage -b --no-sign

        echo "[build] Done."
        ls -lh "$WORKDIR"/*.deb 2>/dev/null || ls -lh ../*.deb
    """)


def generate_build_sh_dkms(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        #!/usr/bin/env bash
        # build.sh — DKMS package builder for {m.pkg_name}
        set -euo pipefail

        PKG="{m.pkg_name}"
        VERSION="{m.upstream_version}"
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        WORKDIR="$(mktemp -d /tmp/${{PKG}}-dkms-build.XXXXXX)"

        echo "[build] Working directory: $WORKDIR"

        if [ -n "{m.upstream_url}" ]; then
            echo "[build] Cloning source ..."
            git clone --depth=1 "{m.upstream_url}" "$WORKDIR/src"
        else
            echo "[build] Copying local source ..."
            cp -r "$SCRIPT_DIR" "$WORKDIR/src"
        fi

        cp -r "$SCRIPT_DIR/debian" "$WORKDIR/src/"

        echo "[build] Installing build dependencies ..."
        cd "$WORKDIR/src"
        dpkg-checkbuilddeps 2>&1 | grep -oP 'Unmet.*: \\K.*' | xargs -r sudo apt-get install -y || true

        echo "[build] Building DKMS package ..."
        dpkg-buildpackage -b --no-sign

        echo "[build] Done."
        ls -lh "$WORKDIR"/*.deb 2>/dev/null || ls -lh ../*.deb
    """)


def generate_debusine_yaml(m: PackageManifest) -> str:
    return textwrap.dedent(f"""\
        # Debusine CI hints for {m.pkg_name}
        ---
        package: {m.pkg_name}
        version: {m.full_version}
        distribution: {m.distro}
        architectures:
          - {m.architecture}
        build:
          type: {"dkms" if m.pkg_type == "dkms" else "binary"}
          sign: false
        tests:
          - autopkgtest
        upload:
          queue: default
    """)


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_skeleton(m: PackageManifest, output_dir: str, dry_run: bool = False) -> None:
    out = Path(output_dir)
    debian = out / "debian"
    source_dir = debian / "source"

    files: dict = {}

    files[debian / "control"] = generate_control(m)
    files[debian / "changelog"] = generate_changelog(m)
    files[debian / "copyright"] = generate_copyright(m)
    files[debian / "rules"] = generate_rules(m)
    files[debian / "compat"] = generate_compat(m)
    files[debian / "gbp.conf"] = generate_gbp_conf(m)
    files[debian / "watch"] = generate_watch(m)
    files[source_dir / "format"] = generate_source_format(m)
    files[out / "debusine.yaml"] = generate_debusine_yaml(m)

    # Build script
    if m.pkg_type == "prebuilt":
        files[out / "build.sh"] = generate_build_sh_prebuilt(m)
    elif m.pkg_type == "dkms":
        files[out / "build.sh"] = generate_build_sh_dkms(m)
        files[debian / f"{m.pkg_name}-dkms.dkms"] = generate_dkms_conf(m)
        files[debian / f"{m.pkg_name}-dkms.postinst"] = generate_postinst(m)
        files[debian / f"{m.pkg_name}-dkms.prerm"] = generate_prerm(m)
    else:
        files[out / "build.sh"] = generate_build_sh_source(m)

    # Split package .install files
    for pkg, files_glob in m.split_packages:
        files[debian / f"{pkg}.install"] = generate_install(m, pkg, files_glob)

    if dry_run:
        print("\n=== DRY RUN — files that would be generated ===")
        for path, content in sorted(files.items()):
            rel = path.relative_to(out)
            lines = content.count("\n")
            print(f"  {rel}  ({lines} lines)")
        print(f"\nTotal: {len(files)} files")
        print(f"Package type: {m.pkg_type}")
        print(f"Package name: {m.pkg_name}")
        print(f"Version:      {m.full_version}")
        return

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        log(f"Wrote {path}")

    # Make rules and build.sh executable
    (debian / "rules").chmod(0o755)
    (out / "build.sh").chmod(0o755)
    if m.pkg_type == "dkms":
        (debian / f"{m.pkg_name}-dkms.postinst").chmod(0o755)
        (debian / f"{m.pkg_name}-dkms.prerm").chmod(0o755)

    info(f"Skeleton written to: {out}")
    info(f"Package type:        {m.pkg_type}")
    info(f"Package name:        {m.pkg_name}")
    info(f"Version:             {m.full_version}")
    info(f"Architecture:        {m.architecture}")
    info(f"Build system:        {m.buildsystem or '(default dh)'}")
    info("")
    info("Next steps:")
    info(f"  cd {out} && bash build.sh")
    info(f"  lintian ../*.deb")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_pkg_name(name: str) -> str:
    """Convert a name to a valid Debian package name (lowercase, hyphens)."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9.+-]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name or "unknown"


def _map_license(yocto_license: str) -> str:
    mapping = {
        "MIT": "MIT",
        "BSD": "BSD-3-clause",
        "BSD-2-Clause": "BSD-2-clause",
        "BSD-3-Clause": "BSD-3-clause",
        "GPL-2.0": "GPL-2",
        "GPL-2.0-only": "GPL-2",
        "GPL-2.0-or-later": "GPL-2+",
        "GPL-3.0": "GPL-3",
        "LGPL-2.1": "LGPL-2.1",
        "Apache-2.0": "Apache-2.0",
        "Proprietary": "LicenseRef-Qualcomm-Proprietary",
        "CLOSED": "LicenseRef-Qualcomm-Proprietary",
    }
    return mapping.get(yocto_license, yocto_license)


def _yocto_dep_to_deb(dep: str) -> Optional[str]:
    """Best-effort mapping of a Yocto dependency name to a Debian package name."""
    skip = {"virtual/kernel", "virtual/libc", "virtual/libintl", "virtual/crypt"}
    if dep in skip or dep.startswith("virtual/"):
        return None
    mapping = {
        "libglib-2.0": "libglib2.0-dev",
        "glib-2.0": "libglib2.0-dev",
        "zlib": "zlib1g-dev",
        "openssl": "libssl-dev",
        "libusb1": "libusb-1.0-0-dev",
        "libxml2": "libxml2-dev",
        "libpcre": "libpcre3-dev",
        "libpng": "libpng-dev",
        "libjpeg-turbo": "libjpeg-dev",
        "alsa-lib": "libasound2-dev",
        "pulseaudio": "libpulse-dev",
        "dbus": "libdbus-1-dev",
        "systemd": "libsystemd-dev",
        "udev": "libudev-dev",
    }
    return mapping.get(dep, f"lib{dep}-dev")


def _wrap_description(summary: str, description: str) -> str:
    """Format a Debian-style description (first line summary, wrapped long desc)."""
    summary = summary.strip().rstrip(".")
    lines = [summary]
    if description and description.strip() != summary.strip():
        lines.append(" .")
        for para in description.strip().split("\n\n"):
            for line in textwrap.wrap(para.strip(), width=72):
                lines.append(f" {line}")
            lines.append(" .")
        lines.pop()  # remove trailing " ."
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="debian_packager",
        description="Generate a Debian packaging skeleton from a Yocto recipe, URL, or local path.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s --recipe meta-qcom/recipes-support/fastrpc/fastrpc_1.0.6.bb
              %(prog)s --url https://github.com/qualcomm/fastrpc
              %(prog)s --url https://example.com/libfoo_1.2_arm64.tar.gz
              %(prog)s --path ./my-driver --dkms
              %(prog)s --recipe kgsl_git.bb --output /tmp/kgsl-deb --dry-run
              %(prog)s --url https://github.com/AudioReach/audioreach-pal --upstream-version 1.0.2 --debian-revision 1
              %(prog)s --url https://github.com/AudioReach/audioreach-pal --upstream-version 1.0.3 --debian-revision 0~rc1
        """),
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--recipe", metavar="FILE", help="Yocto .bb recipe file")
    src.add_argument("--url", metavar="URL", help="Remote git repo or tarball URL")
    src.add_argument("--path", "--local", metavar="PATH", help="Local source tree or tarball")

    p.add_argument("--output", "-o", metavar="DIR", default="./debian-out",
                   help="Output directory (default: ./debian-out)")
    p.add_argument("--maintainer", metavar="STR",
                   help='"Name <email>" for changelog/control')
    p.add_argument("--upstream-version", metavar="VER",
                   help="Override upstream version (e.g. 1.0.2). Overrides value parsed from recipe/URL/path.")
    p.add_argument("--debian-revision", metavar="REV", default="1",
                   help="Debian revision suffix appended to upstream version (default: 1). "
                        "Increment for re-packaging the same upstream release (e.g. 2, 3). "
                        "Use 0~<qualifier> for pre-releases (e.g. 0~rc1).")
    p.add_argument("--dkms", action="store_true", help="Force DKMS package type")
    p.add_argument("--prebuilt", action="store_true", help="Force prebuilt package type")
    p.add_argument("--source", action="store_true", help="Force source/userspace package type")
    p.add_argument("--split-packages", action="store_true",
                   help="Emit one binary stanza per PACKAGES entry")
    p.add_argument("--no-watch", action="store_true", help="Skip watch file generation")
    p.add_argument("--no-gbp", action="store_true", help="Skip gbp.conf generation")
    p.add_argument("--no-debusine", action="store_true", help="Skip debusine.yaml generation")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be generated without writing files")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p


def main() -> None:
    global VERBOSE
    parser = build_parser()
    args = parser.parse_args()
    VERBOSE = args.verbose

    manifest = PackageManifest()
    if args.maintainer:
        manifest.maintainer = args.maintainer

    # Parse input
    if args.recipe:
        info(f"Parsing Yocto recipe: {args.recipe}")
        parse_recipe(args.recipe, manifest)
    elif args.url:
        info(f"Parsing URL: {args.url}")
        parse_url(args.url, manifest, force_dkms=args.dkms, force_prebuilt=args.prebuilt)
    elif args.path:
        info(f"Parsing local path: {args.path}")
        parse_local(args.path, manifest, force_dkms=args.dkms, force_prebuilt=args.prebuilt)

    # Apply version overrides (CLI takes precedence over parsed values)
    if args.upstream_version:
        manifest.upstream_version = args.upstream_version.lstrip("v")
        log(f"Upstream version overridden to: {manifest.upstream_version}")

    # Auto-determine debian revision unless explicitly provided by the user
    _explicit_revision = (args.debian_revision != "1")  # "1" is the argparse default
    if _explicit_revision:
        manifest.debian_revision = args.debian_revision
        log(f"Debian revision explicitly set to: {manifest.debian_revision}")
    else:
        manifest.debian_revision = _auto_debian_revision(args.output, manifest.upstream_version)
        log(f"Auto debian revision: {manifest.debian_revision}")

    # Override type flags
    if args.source:
        manifest.pkg_type = "source"
        manifest.architecture = "any"
    elif args.dkms and manifest.pkg_type != "dkms":
        manifest.pkg_type = "dkms"
        manifest.architecture = "all"
    elif args.prebuilt and manifest.pkg_type != "prebuilt":
        manifest.pkg_type = "prebuilt"
        manifest.architecture = "arm64"

    # Validate output dir
    out = Path(args.output)
    if out.exists() and not args.dry_run:
        die(f"Output directory already exists: {out}\nRemove it first or choose a different --output path.")

    write_skeleton(manifest, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
