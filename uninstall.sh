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

rm -rf /usr/local/lib/predatorctl
rm -f /usr/local/bin/predatorctl
rm -f /usr/share/applications/predatorctl.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/predatorctl.svg
rm -f /etc/polkit-1/rules.d/49-predatorctl.rules

gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo "predatorctl removed from the system."
