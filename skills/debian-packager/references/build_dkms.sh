#!/usr/bin/env bash
# Reference: build.sh for DKMS kernel module packages
set -euo pipefail

PKG="{{PKG_NAME}}"
CLONE_URL="{{CLONE_URL}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$(mktemp -d /tmp/${PKG}-dkms-build.XXXXXX)"

if [ -n "$CLONE_URL" ]; then
    git clone --depth=1 "$CLONE_URL" "$WORKDIR/src"
else
    cp -r "$SCRIPT_DIR" "$WORKDIR/src"
fi

cp -r "$SCRIPT_DIR/debian" "$WORKDIR/src/"
cd "$WORKDIR/src"
dpkg-checkbuilddeps 2>&1 | grep -oP 'Unmet.*: \K.*' | xargs -r sudo apt-get install -y || true
dpkg-buildpackage -b --no-sign
ls -lh ../*.deb
