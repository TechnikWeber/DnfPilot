# Changelog

## [0.1.0] - 2026-11-11

First release.

- Window with the list of available dnf and Flatpak updates, a progress bar
  (downloads and installation counted package by package) and fold-out details
  with the full dnf output.
- One password prompt per update through polkit, no terminal.
- Restart button; after an update it says whether a restart is needed (kernel,
  glibc, systemd, Plasma, Mesa, graphics driver updated since boot).
- Repair menu: cancel Discover's offline update, reload package lists, resolve
  package conflicts with a preview of what would be removed, clear the
  PackageKit cache, Flatpak only, offline update on your own terms.
- Banner when Discover has left an offline update scheduled.
- English and German interface.
- AppImage (Gear Lever / AppImageUpdate compatible), RPM, `install.sh`, and the
  single-file terminal variant.
