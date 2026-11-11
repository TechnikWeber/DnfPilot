# Changelog

## [0.2.1] - 2026-11-11

- Corrected the reason given for Discover not offering a new Fedora release:
  it is not the dnf5 backend, but Fedora's AppStream metadata, which kept
  Fedora 45 marked as "development" after its release
  ([bug 2568647](https://bugzilla.redhat.com/show_bug.cgi?id=2568647)). The
  upgrade banner no longer names a cause.

## [0.2.0] - 2026-11-11

- **New Fedora release:** a banner says when the next Fedora is out and
  upgrades with `dnf system-upgrade` (download while you work, install on
  restart). Discover does not report new releases on Fedora with the dnf5
  PackageKit backend, so this reads fedoraproject.org/releases.json itself.
  Warns first when less than 6 GB are free on the system disk.
- **Firmware:** fwupd updates appear in the list and are installed with the
  rest (switch off with "Include firmware"); Repair → "Update firmware only".
- **NVIDIA:** the Restart button stays locked while akmods builds the driver
  module for a new kernel – restarting earlier ends with a black screen.
- **Snap:** if snapd is installed, Snap updates are listed and installed too.
- Restart detection uses rpm install times instead of `dnf needs-restarting`.
- A collapsed Details section no longer leaves an empty gap.

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
