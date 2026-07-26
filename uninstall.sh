#!/usr/bin/env bash
#
# predatorctl - uninstaller. Removes everything install.sh created.
# Usage:  sudo ./uninstall.sh
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Error: run as root  →  sudo ./uninstall.sh" >&2
    exit 1
fi

systemctl disable --now predatorctl-restore.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/predatorctl-restore.service
rm -rf /etc/systemd/system/predatorctl-restore.service.d
systemctl daemon-reload 2>/dev/null || true
rm -f /etc/predatorctl/restore.conf.example

rm -rf /usr/local/lib/predatorctl
rm -f /usr/local/bin/predatorctl
rm -f /usr/share/applications/predatorctl.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/predatorctl.svg
rm -f /etc/polkit-1/rules.d/49-predatorctl.rules

gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo "predatorctl removed from the system."
if [[ -f /etc/predatorctl/restore.conf ]]; then
    echo "Note: /etc/predatorctl/restore.conf was left in place (your saved preferences)."
    echo "Remove it yourself if you don't need it: sudo rm -rf /etc/predatorctl"
fi
