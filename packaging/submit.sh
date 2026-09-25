#!/bin/sh
# Publishes a package to the AUR. Run it after your SSH key is registered at
# https://aur.archlinux.org/account/  (see README.md in this directory).
#
#   ./submit.sh aur        publishes autotris (tagged release)
#   ./submit.sh aur-git    publishes autotris-git (builds from main)
set -eu

DIR="${1:-aur}"
[ -d "$DIR" ] || { echo "no such package dir: $DIR" >&2; exit 1; }

NAME=$(awk -F' = ' '/^pkgbase/ {print $2}' "$DIR/.SRCINFO")
[ -n "$NAME" ] || { echo "could not read pkgbase from $DIR/.SRCINFO" >&2; exit 1; }

ssh -o BatchMode=yes -T aur@aur.archlinux.org 2>&1 | grep -q "Welcome" || {
    echo "AUR rejected your SSH key. Register it first:" >&2
    echo "  https://aur.archlinux.org/account/  ->  SSH Public Key" >&2
    exit 1
}

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
git clone -q "ssh://aur@aur.archlinux.org/$NAME.git" "$WORK/$NAME" 2>/dev/null || {
    mkdir -p "$WORK/$NAME"
    git -C "$WORK/$NAME" init -q
    git -C "$WORK/$NAME" remote add origin "ssh://aur@aur.archlinux.org/$NAME.git"
}

cp "$DIR/PKGBUILD" "$DIR/.SRCINFO" "$WORK/$NAME/"
cd "$WORK/$NAME"
git add PKGBUILD .SRCINFO
git diff --cached --quiet && { echo "nothing to publish for $NAME"; exit 0; }
git commit -qm "$(awk -F' = ' '/^\tpkgver/ {print $2}' .SRCINFO | head -1)"
git push -q origin HEAD:master
echo "published: https://aur.archlinux.org/packages/$NAME"
