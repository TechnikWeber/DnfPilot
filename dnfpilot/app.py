"""Entry point: `dnfpilot` opens the window."""
from __future__ import annotations

import argparse
import configparser
import os
import sys
from pathlib import Path

from . import __version__


def _icon_theme_fallback():
    """Inside the AppImage Qt has no KDE/GNOME platform plugin, so it does not
    know the desktop's icon theme. Read it from kdeglobals, else pick one."""
    from PySide6.QtGui import QIcon

    if QIcon.themeName() not in ("", "hicolor"):
        return
    theme = ""
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kdeglobals"
    if cfg.exists():
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(cfg)
            theme = parser.get("Icons", "Theme", fallback="")
        except configparser.Error:
            pass
    for candidate in (theme, "breeze", "Adwaita"):
        if candidate and Path("/usr/share/icons", candidate).is_dir():
            QIcon.setThemeName(candidate)
            return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dnfpilot",
        description="Update Fedora with dnf and Flatpak, without Discover's offline update.",
    )
    parser.add_argument("--version", action="version", version=f"dnfpilot {__version__}")
    parser.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.selftest:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from .window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("dnfpilot")
    app.setApplicationDisplayName("DnfPilot")
    app.setDesktopFileName("dnfpilot")
    app.setApplicationVersion(__version__)
    _icon_theme_fallback()
    win = MainWindow()
    win.show()
    if args.selftest:
        # build the window, let the event loop run once, report and leave
        def report():
            print(f"selftest ok: dnfpilot {__version__}, Qt window built, icon "
                  f"{'ok' if not win.windowIcon().isNull() else 'MISSING'}")
            app.exit(0 if not win.windowIcon().isNull() else 1)
        QTimer.singleShot(500, report)
    return app.exec()
