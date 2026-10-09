#!/usr/bin/env bash
# Reference: build.sh for prebuilt tarball packages
set -euo pipefail

PKG="{{PKG_NAME}}"
VERSION="{{UPSTREAM_VERSION}}"
EXPECTED_SHA256="{{SHA256}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$(mktemp -d /tmp/${PKG}-build.XXXXXX)"

if [ $# -eq 0 ]; then
    uscan --force-download --destdir "$WORKDIR" --package "$PKG" \
          --upstream-version "$VERSION" --watchfile "$SCRIPT_DIR/debian/watch"
    TARBALL=$(ls "$WORKDIR"/*.tar.* | head -1)
elif [ -d "$1" ]; then
    UNPACK_DIR="$1"
    TARBALL=""
else
    TARBALL="$1"
fi

if [ -n "${TARBALL:-}" ]; then
    [ -n "$EXPECTED_SHA256" ] && echo "$EXPECTED_SHA256  $TARBALL" | sha256sum -c
    mkdir -p "$WORKDIR/$PKG-$VERSION"
    tar -xf "$TARBALL" -C "$WORKDIR/$PKG-$VERSION" --strip-components=1
    UNPACK_DIR="$WORKDIR/$PKG-$VERSION"
fi

cp -r "$SCRIPT_DIR/debian" "$UNPACK_DIR/"
cd "$UNPACK_DIR"
dpkg-buildpackage -b --no-sign
ls -lh ../*.deb
