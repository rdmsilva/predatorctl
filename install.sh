#!/usr/bin/env bash
#
# predatorctl - system installer.
#
# Installs the app into a root-owned directory (not user-writable), registers
# the launcher, the icon, the menu entry (.desktop) and the auth_admin_keep
# polkit rule (password once per session — NOT passwordless).
#
# Usage:  sudo ./install.sh [after-unit]
#
#   after-unit  optional systemd unit name, e.g. power-profiles-daemon.service.
#               Some system power-management daemons also own
#               /sys/firmware/acpi/platform_profile and can start (via D-Bus
#               activation) *after* predatorctl-restore.service at boot,
#               overwriting the restored thermal profile with their own
#               default. Passing one here adds a drop-in ordering
#               predatorctl-restore.service after it (Wants=+After=), so it
#               starts first and settles before we write.
#
#               NOT applied unless you ask: Wants= would also *start* that
#               unit, and some of these daemons Conflicts= each other (e.g.
#               power-profiles-daemon conflicts with tlp) -- pulling one in
#               could stop a power-management tool you're already using on
#               purpose. Only pass this if you've hit the race yourself.
#
set -euo pipefail

APP_DIR="/usr/local/lib/predatorctl"
BIN="/usr/local/bin/predatorctl"
DESKTOP="/usr/share/applications/predatorctl.desktop"
ICON="/usr/share/icons/hicolor/scalable/apps/predatorctl.svg"
POLKIT="/etc/polkit-1/rules.d/49-predatorctl.rules"
HELPER="$APP_DIR/helper/predatorctl-helper"
RESTORE_HELPER="$APP_DIR/helper/predatorctl-restore"
RESTORE_UNIT="/etc/systemd/system/predatorctl-restore.service"
RESTORE_ETC="/etc/predatorctl"
RESTORE_DROPIN_DIR="/etc/systemd/system/predatorctl-restore.service.d"

AFTER_UNIT="${1:-}"

SRC="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Error: run as root  →  sudo ./install.sh" >&2
    exit 1
fi

if [[ -n "$AFTER_UNIT" && ! "$AFTER_UNIT" =~ ^[A-Za-z0-9:_.@-]+\.service$ ]]; then
    echo "Error: '$AFTER_UNIT' doesn't look like a systemd unit name (expected *.service)" >&2
    exit 1
fi

echo "==> Installing predatorctl into $APP_DIR"
rm -rf "$APP_DIR"
install -d -m 755 "$APP_DIR"
cp -r "$SRC/src" "$APP_DIR/src"
cp -r "$SRC/helper" "$APP_DIR/helper"
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} +

# everything root-owned; helper executable (invoked directly via pkexec)
chown -R root:root "$APP_DIR"
find "$APP_DIR" -type d -exec chmod 755 {} +
find "$APP_DIR" -type f -exec chmod 644 {} +
chmod 755 "$HELPER"
chmod 755 "$RESTORE_HELPER"

echo "==> Launcher: $BIN"
cat > "$BIN" <<EOF
#!/bin/sh
exec python3 "$APP_DIR/src/main.py" "\$@"
EOF
chmod 755 "$BIN"

echo "==> Icon: $ICON"
install -d -m 755 "$(dirname "$ICON")"
install -m 644 "$SRC/data/icons/predatorctl.svg" "$ICON"

echo "==> Menu entry: $DESKTOP"
install -m 644 "$SRC/data/predatorctl.desktop" "$DESKTOP"

echo "==> Polkit rule (auth_admin_keep): $POLKIT"
install -m 644 "$SRC/data/49-predatorctl.rules" "$POLKIT"

echo "==> Boot-time preference restore (enabled, auto-populated as you use the app): $RESTORE_UNIT"
install -d -m 755 "$RESTORE_ETC"
install -m 644 "$SRC/data/restore.conf.example" "$RESTORE_ETC/restore.conf.example"
install -m 644 "$SRC/data/predatorctl-restore.service" "$RESTORE_UNIT"

rm -rf "$RESTORE_DROPIN_DIR"
if [[ -n "$AFTER_UNIT" ]]; then
    echo "==> Ordering predatorctl-restore.service after: $AFTER_UNIT (opt-in, see install.sh usage)"
    install -d -m 755 "$RESTORE_DROPIN_DIR"
    printf '[Unit]\nAfter=%s\nWants=%s\n' "$AFTER_UNIT" "$AFTER_UNIT" > "$RESTORE_DROPIN_DIR/after.conf"
    chmod 644 "$RESTORE_DROPIN_DIR/after.conf"
fi

systemctl daemon-reload 2>/dev/null || true
# Safe to enable unconditionally: ConditionPathExists=/etc/predatorctl/restore.conf
# in the unit makes this a no-op (successful, RemainAfterExit) until that file
# exists -- which predatorctl-helper creates itself the first time you change
# a setting in the app (see _persist() there). No manual config step needed.
systemctl enable --now predatorctl-restore.service 2>/dev/null || true

# refresh caches (silent if the tools aren't present)
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo
echo "Done. 'Predator Control' is now in your application menu."
echo "You'll be asked for your password once per session (auth_admin_keep, ~5 min)."
echo
echo "linuwu_sense reloads with driver defaults on every reboot. From now on,"
echo "every profile/RGB/battery-limiter/fan change you make in the app is"
echo "automatically saved to $RESTORE_ETC/restore.conf and reapplied at boot"
echo "-- no extra steps needed. See $RESTORE_ETC/restore.conf.example if you"
echo "ever want to add or edit an entry by hand."
if [[ -z "$AFTER_UNIT" ]]; then
    echo
    echo "If your thermal profile reverts shortly after boot, a system"
    echo "power-management daemon (e.g. power-profiles-daemon on GNOME/KDE)"
    echo "may be racing us for /sys/firmware/acpi/platform_profile. Re-run with"
    echo "  sudo ./install.sh power-profiles-daemon.service"
    echo "to fix it -- see install.sh for why this isn't the default."
fi
