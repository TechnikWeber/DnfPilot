#!/usr/bin/env bash
# Puts DnfPilot into the application menu (for your user only) and makes
# sure PySide6 is there. Nothing is written outside your home directory.
set -euo pipefail

here="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$here"

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
bin="$HOME/.local/bin"

if python3 -c "import PySide6.QtWidgets" 2>/dev/null; then
    echo "PySide6: already installed."
else
    read -r -p "PySide6 is missing. Install it now with 'sudo dnf install python3-pyside6'? [Y/n] " reply
    case "$reply" in
        [nN]*) echo "Skipped. Install python3-pyside6, then run this script again."; exit 1 ;;
        *)     sudo dnf install -y python3-pyside6 ;;
    esac
fi

mkdir -p "$apps" "$bin" "$icons/scalable/apps" "$icons/256x256/apps"
install -m644 dnfpilot/dnfpilot.svg "$icons/scalable/apps/dnfpilot.svg"
install -m644 share/dnfpilot.png "$icons/256x256/apps/dnfpilot.png"
# the menu does not see ~/.local/bin on every system, so bake in the full path
sed "s|^Exec=.*|Exec=$here/bin/dnfpilot|" share/dnfpilot.desktop > "$apps/dnfpilot.desktop"
chmod 644 "$apps/dnfpilot.desktop"
ln -sf "$here/bin/dnfpilot" "$bin/dnfpilot"

command -v update-desktop-database >/dev/null && update-desktop-database "$apps" 2>/dev/null || true
command -v gtk-update-icon-cache   >/dev/null && gtk-update-icon-cache -qtf "$icons" 2>/dev/null || true
command -v kbuildsycoca6           >/dev/null && kbuildsycoca6 --noincremental 2>/dev/null || true

cat <<MSG

Done.

  * Application menu: search for "DnfPilot".
  * Terminal:         dnfpilot

Remove again with ./uninstall.sh
MSG
