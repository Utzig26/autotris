# Packaging

| directory | package | source |
|-----------|---------|--------|
| `aur/` | `autotris` | the tagged release tarball |
| `aur-git/` | `autotris-git` | whatever is on `main` |

Both install the package to `/usr/lib/autotris` with a launcher in
`/usr/bin/autotris`. There are no build dependencies: the project is pure
Python with no third-party imports, so there is nothing to compile and nothing
to download at build time.

## Building locally

```bash
cd aur && makepkg -f          # builds autotris-1.0.0-1-any.pkg.tar.zst
sudo pacman -U autotris-*.pkg.tar.zst
```

## Installing without the AUR

The AUR is not required. Either of these gives you a proper pacman package:

```bash
cd aur && makepkg -si                    # build and install from source
sudo pacman -U autotris-*.pkg.tar.zst    # or install a prebuilt one
```

A prebuilt package is attached to every GitHub release.

## Publishing to the AUR

> **AUR registration is currently paused** while the Arch team deals with a wave
> of automated account creation. Existing accounts are unaffected — if you
> already have one, skip to step 2. Otherwise this has to wait for registration
> to reopen; it is announced on aur-general and the Arch news feed. Do not
> script retries against the registration page.

One-time setup, and only you can do it: the AUR needs your SSH public key.

1. Create an account at <https://aur.archlinux.org/register> (skip if you have one;
   currently paused, see the note above).
2. Open <https://aur.archlinux.org/account/> → **My Account** → paste the contents
   of `~/.ssh/id_ed25519.pub` into **SSH Public Key** → Save.
3. Check it took:

```bash
ssh -T aur@aur.archlinux.org      # should greet you by username
```

Then publish:

```bash
./submit.sh aur          # autotris
./submit.sh aur-git      # autotris-git
```

## Releasing a new version

```bash
# 1. bump the version
sed -i 's/^version = .*/version = "1.1.0"/' ../pyproject.toml
sed -i 's/^pkgver=.*/pkgver=1.1.0/' aur/PKGBUILD

# 2. tag and publish the GitHub release (the tarball the PKGBUILD fetches)
git tag -a v1.1.0 -m "autotris 1.1.0" && git push --follow-tags
gh release create v1.1.0 --generate-notes

# 3. refresh the checksum and the .SRCINFO, then publish
cd aur && updpkgsums && makepkg --printsrcinfo > .SRCINFO && cd ..
./submit.sh aur
```

`autotris-git` picks up new commits on its own; it only needs republishing when
its PKGBUILD changes.
