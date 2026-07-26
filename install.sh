#!/usr/bin/env bash
#
# predatorctl - system installer.
#
# Installs the app into a root-owned directory (not user-writable), registers
# the launcher, the icon, the menu entry (.desktop) and the auth_admin_keep
# polkit rule (password once per session — NOT passwordless).
#
# Usage:  sudo ./install.sh
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

SRC="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Error: run as root  →  sudo ./install.sh" >&2
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

echo "==> Boot-time preference restore (enabled, inert until configured): $RESTORE_UNIT"
install -d -m 755 "$RESTORE_ETC"
install -m 644 "$SRC/data/restore.conf.example" "$RESTORE_ETC/restore.conf.example"
install -m 644 "$SRC/data/predatorctl-restore.service" "$RESTORE_UNIT"
systemctl daemon-reload 2>/dev/null || true
# Safe to enable unconditionally: ConditionPathExists=/etc/predatorctl/restore.conf
# in the unit makes this a no-op (successful, RemainAfterExit) until that
# root-only-writable file exists — see CLAUDE.md.
systemctl enable --now predatorctl-restore.service 2>/dev/null || true

# refresh caches (silent if the tools aren't present)
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo
echo "Done. 'Predator Control' is now in your application menu."
echo "You'll be asked for your password once per session (auth_admin_keep, ~5 min)."
echo
echo "linuwu_sense reloads with driver defaults on every reboot, so your last"
echo "profile/RGB/battery-limiter settings are lost until you reopen the app."
echo "predatorctl-restore.service is enabled but does nothing until you opt in:"
echo "  sudo cp $RESTORE_ETC/restore.conf.example $RESTORE_ETC/restore.conf"
echo "  sudo \$EDITOR $RESTORE_ETC/restore.conf"
echo "  sudo systemctl restart predatorctl-restore.service   # apply now, or just reboot"
