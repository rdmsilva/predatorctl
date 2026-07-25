#!/usr/bin/env bash
#
# predatorctl — OPTIONAL installer for the linuwu_sense module via DKMS.
#
# predatorctl does NOT install kernel code: linuwu_sense is an environment
# prerequisite (https://github.com/0x7375646F/Linuwu-Sense). This script is a
# convenience for installing it the recommended way — registered with DKMS,
# so the module is rebuilt automatically on every kernel update (the
# upstream's manual install silently breaks when the kernel updates).
#
# What it does (read it — it's short):
#   1. copies the Linuwu-Sense source to /usr/src/linuwu_sense-<ver>
#      (from a local checkout passed as argument, or by cloning upstream);
#   2. registers/builds/installs via `dkms install`;
#   3. blacklists acer_wmi (conflicts: same WMI GUIDs) and configures
#      linuwu_sense to load at boot;
#   4. installs the upstream linuwu_sense.service (unloads at shutdown);
#   5. loads the module now.
#
# Usage:  sudo ./install-linuwu-dkms.sh [path-to-local-checkout]
#         sudo ./install-linuwu-dkms.sh --uninstall
#
set -euo pipefail

REPO_URL="https://github.com/0x7375646F/Linuwu-Sense.git"
MODNAME="linuwu_sense"
VERSION="1.0"
SRC_DST="/usr/src/${MODNAME}-${VERSION}"
BLACKLIST="/etc/modprobe.d/blacklist-acer_wmi.conf"
MODLOAD="/etc/modules-load.d/${MODNAME}.conf"
SERVICE="/etc/systemd/system/${MODNAME}.service"

die() { echo "Error: $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "run as root  →  sudo $0"

# ── uninstall ──────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    modprobe -r "$MODNAME" 2>/dev/null || true
    dkms remove "${MODNAME}/${VERSION}" --all 2>/dev/null || true
    systemctl disable --now "${MODNAME}.service" 2>/dev/null || true
    rm -f "$SERVICE" "$MODLOAD" "$BLACKLIST"
    rm -rf "$SRC_DST"
    systemctl daemon-reload
    echo "linuwu_sense removed. The native acer_wmi returns on next boot."
    exit 0
fi

# ── prerequisites ──────────────────────────────────────────────────────────
command -v dkms >/dev/null || die "install the 'dkms' package first
  Arch/Manjaro: pacman -S dkms | Debian/Ubuntu: apt install dkms | Fedora: dnf install dkms"

[[ -e "/lib/modules/$(uname -r)/build/Makefile" ]] || die "kernel headers for $(uname -r) missing
  Arch/Manjaro: pacman -S linux-headers (for YOUR kernel series, e.g. linux618-headers)
  Debian/Ubuntu: apt install linux-headers-\$(uname -r) | Fedora: dnf install kernel-devel"

# ── source: local checkout (arg 1) or clone upstream ───────────────────────
SRC="${1:-}"
if [[ -n "$SRC" ]]; then
    [[ -f "$SRC/src/${MODNAME}.c" ]] || die "'$SRC' doesn't look like a Linuwu-Sense checkout"
else
    command -v git >/dev/null || die "install 'git' (or pass a local checkout as argument)"
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    SRC="$TMP/Linuwu-Sense"
    echo "==> Cloning $REPO_URL (temporary staging; the permanent source lives in $SRC_DST)"
    git clone --depth 1 "$REPO_URL" "$SRC"
fi

# ── copy to /usr/src and write the dkms.conf ───────────────────────────────
echo "==> DKMS source: $SRC_DST"
rm -rf "$SRC_DST"
mkdir -p "$SRC_DST/src"
cp "$SRC/Makefile" "$SRC_DST/"
cp "$SRC/src/${MODNAME}.c" "$SRC_DST/src/"
[[ -f "$SRC/${MODNAME}.service" ]] && cp "$SRC/${MODNAME}.service" "$SRC_DST/"

cat > "$SRC_DST/dkms.conf" <<EOF
PACKAGE_NAME="$MODNAME"
PACKAGE_VERSION="$VERSION"
MAKE[0]="make -C \${kernel_source_dir} M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build modules"
CLEAN="rm -f src/*.o src/*.ko src/*.mod src/*.mod.c src/*.mod.o"
BUILT_MODULE_NAME[0]="$MODNAME"
BUILT_MODULE_LOCATION[0]="src"
DEST_MODULE_LOCATION[0]="/kernel/drivers/platform/x86"
AUTOINSTALL="yes"
EOF

# ── DKMS: idempotent reinstall ─────────────────────────────────────────────
dkms remove "${MODNAME}/${VERSION}" --all 2>/dev/null || true
echo "==> dkms install ${MODNAME}/${VERSION}"
dkms install "${MODNAME}/${VERSION}"

# ── swap acer_wmi → linuwu_sense (at boot and right now) ───────────────────
echo "blacklist acer_wmi" > "$BLACKLIST"
echo "$MODNAME" > "$MODLOAD"
if [[ -f "$SRC_DST/${MODNAME}.service" ]]; then
    cp "$SRC_DST/${MODNAME}.service" "$SERVICE"
    systemctl daemon-reload
    systemctl enable "${MODNAME}.service" 2>/dev/null || true
fi

modprobe -r acer_wmi 2>/dev/null || true
modprobe "$MODNAME"

# ── verification ───────────────────────────────────────────────────────────
if [[ -e /sys/firmware/acpi/platform_profile ]]; then
    echo
    echo "OK. Module loaded — platform_profile: $(cat /sys/firmware/acpi/platform_profile)"
    echo "From now on DKMS rebuilds the module on every kernel update"
    echo "(keep your kernel series' headers package installed)."
else
    echo
    echo "Module installed, but platform_profile did not appear — unsupported hardware?"
    echo "See: https://github.com/0x7375646F/Linuwu-Sense#supported-models"
fi
