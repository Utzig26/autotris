#!/bin/sh
# autotris installer: copies the package into a prefix and drops a launcher.
#   curl -fsSL https://raw.githubusercontent.com/Utzig26/autotris/main/install.sh | sh
set -eu

REPO="https://github.com/Utzig26/autotris"
PREFIX="${PREFIX:-$HOME/.local}"
LIBDIR="$PREFIX/lib/autotris"
BINDIR="$PREFIX/bin"

die() { printf '%s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "autotris needs python3 (3.10 or newer)"
python3 - <<'PY' || die "autotris needs python 3.10 or newer"
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY

if [ -d "$(dirname "$0")/autotris" ] && [ -f "$(dirname "$0")/pyproject.toml" ]; then
    SRC="$(cd "$(dirname "$0")" && pwd)"
    CLEANUP=""
else
    command -v git >/dev/null 2>&1 || die "autotris needs git to fetch the source"
    SRC="$(mktemp -d)"
    CLEANUP="$SRC"
    printf 'fetching autotris...\n'
    git clone --depth 1 -q "$REPO" "$SRC"
fi

printf 'installing to %s\n' "$LIBDIR"
rm -rf "$LIBDIR"
mkdir -p "$LIBDIR" "$BINDIR"
cp -r "$SRC/autotris" "$LIBDIR/"

cat > "$BINDIR/autotris" <<LAUNCHER
#!/bin/sh
exec python3 -c 'import sys; sys.path.insert(0, "$LIBDIR"); from autotris.cli import main; main()' "\$@"
LAUNCHER
chmod +x "$BINDIR/autotris"
[ -n "$CLEANUP" ] && rm -rf "$CLEANUP"

printf 'installed: %s/autotris\n' "$BINDIR"
case ":$PATH:" in
    *":$BINDIR:"*) printf 'run it with: autotris\n' ;;
    *) printf 'add %s to your PATH, then run: autotris\n' "$BINDIR" ;;
esac
