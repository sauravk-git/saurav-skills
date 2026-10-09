#!/usr/bin/env bash
# Reference: build.sh for source/userspace packages
# Variables substituted by debian_packager.py at generation time.
set -euo pipefail

PKG="{{PKG_NAME}}"
VERSION="{{UPSTREAM_VERSION}}"
CLONE_URL="{{CLONE_URL}}"
BRANCH="{{UPSTREAM_BRANCH}}"
WORKDIR="$(mktemp -d /tmp/${PKG}-build.XXXXXX)"

echo "[build] Cloning $CLONE_URL ..."
git clone --depth=1 --branch "$BRANCH" "$CLONE_URL" "$WORKDIR/src" 2>/dev/null \
    || git clone --depth=1 "$CLONE_URL" "$WORKDIR/src"

cp -r "$(dirname "$0")/debian" "$WORKDIR/src/"
cd "$WORKDIR/src"
dpkg-checkbuilddeps 2>&1 | grep -oP 'Unmet.*: \K.*' | xargs -r sudo apt-get install -y || true
debuild -uc -us -b
ls -lh "$WORKDIR"/*.deb 2>/dev/null || ls -lh ../*.deb
