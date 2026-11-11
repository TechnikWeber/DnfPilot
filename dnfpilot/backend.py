"""Everything that talks to dnf, flatpak and the system -- no Qt widgets here.

The parsing functions are pure so they can be unit-tested against captured
dnf5 output (see tests/).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

# Plain, English, uncoloured output that the parsers below understand.
CMD_ENV = {"LC_ALL": "C", "LANG": "C", "TERM": "dumb", "NO_COLOR": "1"}


@dataclass
class Package:
    name: str
    version: str
    source: str  # dnf repo, or "Flatpak"
    kind: str  # "rpm" or "flatpak"


# ---------------------------------------------------------------- dnf check

_CHECK_ROW = re.compile(r"^(\S+)\.(\S+)\s+(\S+)\s+(\S+)$")


def parse_check_upgrade(text: str) -> list[Package]:
    """Parse `dnf check-upgrade` (dnf5) output into packages.

    Rows look like ``git-core.x86_64   2.56.0-1.fc44   updates``. Repo loading
    lines are indented and warnings start with ``>>>``, so anchoring on a
    non-space first column with exactly four fields is enough.
    """
    pkgs: list[Package] = []
    seen: set[str] = set()
    for line in text.splitlines():
        m = _CHECK_ROW.match(line.rstrip())
        if not m:
            continue
        name, _arch, version, repo = m.groups()
        key = f"{name}.{_arch}"
        if key in seen:
            continue
        seen.add(key)
        pkgs.append(Package(name, version, repo, "rpm"))
    return pkgs


# ---------------------------------------------------------------- flatpak

def parse_flatpak_updates(text: str) -> list[Package]:
    """Parse `flatpak remote-ls --updates --columns=application,name,version,branch`."""
    pkgs: list[Package] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 2 or not cols[0].strip():
            continue
        app = cols[0].strip()
        name = cols[1].strip() or app
        version = cols[2].strip() if len(cols) > 2 else ""
        branch = cols[3].strip() if len(cols) > 3 else ""
        key = (app, branch)
        if key in seen:
            continue
        seen.add(key)
        pkgs.append(Package(name, version or branch, app, "flatpak"))
    return pkgs


# ---------------------------------------------------------------- previews

_SECTION = re.compile(r"^([A-Z][A-Za-z ]+):$")
_TABLE_ROW = re.compile(r"^ (\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+.*$")


def parse_transaction_removals(text: str) -> list[str]:
    """Package names that a previewed dnf transaction would remove or downgrade.

    Reads the dnf5 transaction table (``Removing:``, ``Removing dependent
    packages:``, ``Downgrading:`` ...). ``replacing`` sub-rows are ignored --
    they are the old halves of normal upgrades.
    """
    out: list[str] = []
    section = ""
    for line in text.splitlines():
        sec = _SECTION.match(line.strip()) if not line.startswith(" ") else None
        if sec:
            section = sec.group(1).lower()
            continue
        if not line.startswith(" ") or line.lstrip().startswith("replacing"):
            continue
        if section.startswith("removing") or section.startswith("downgrading"):
            m = _TABLE_ROW.match(line)
            if m:
                out.append(f"{m.group(1)} {m.group(3)}")
    return out


# ---------------------------------------------------------------- progress

# "[ 65/151] Upgrading vim-enhanced-2:9.2. 100% | ..." -- the name column is
# cut to a fixed width, so the only reliable end marker is the percentage.
_COUNTER = re.compile(r"^\[\s*(\d+)/(\d+)\]\s+(.*?)(?:\s+\d+%.*)?$")
_FLATPAK_OP = re.compile(r"^(Updating|Installing|Uninstalling)\s+(\S+)")


@dataclass
class DnfProgress:
    """Turns dnf5 output lines into a 0..1 fraction plus a short label.

    dnf5 numbers every download (``[ 3/78] pkg``) and every transaction step
    (``[ 65/151] Upgrading pkg``). Downloads end with a ``Total`` row; after
    that the counter starts again for the RPM transaction. Downloads count for
    the first 40 %, installing for the rest.
    """
    phase: str = "refresh"  # refresh -> download -> install -> done
    fraction: float = 0.0
    label: str = ""
    _dl_split: float = 0.4

    def feed(self, line: str) -> bool:
        """Feed one line; return True when fraction or label changed."""
        line = line.rstrip()
        if line.startswith("Repositories loaded"):
            self.phase, self.label = "resolve", "resolve"
            return True
        m = _COUNTER.match(line)
        if not m:
            if line.startswith("Complete!"):
                self.phase, self.fraction, self.label = "done", 1.0, "done"
                return True
            return False
        n, total, what = int(m.group(1)), max(int(m.group(2)), 1), m.group(3).strip()
        if what == "Total":
            self.phase, self.fraction = "install", self._dl_split
            self.label = "download-done"
            return True
        if self.phase in ("refresh", "resolve"):
            # first counter: downloads, unless dnf had everything cached and
            # went straight to "Verify package files"
            self.phase = "install" if what.startswith("Verify") else "download"
        if self.phase == "download":
            self.fraction = self._dl_split * n / total
            self.label = f"download {n}/{total}"
        else:
            self.fraction = self._dl_split + (1 - self._dl_split) * n / total
            self.label = f"install {n}/{total} {what}"
        return True


@dataclass
class FlatpakProgress:
    total: int = 0
    done: int = 0
    fraction: float = 0.0
    label: str = ""

    def feed(self, line: str) -> bool:
        m = _FLATPAK_OP.match(line.strip())
        if not m:
            return False
        self.done += 1
        total = max(self.total, self.done)
        self.fraction = (self.done - 1) / total if total else 0.0
        self.label = m.group(2)
        return True


# ---------------------------------------------------------------- jobs

@dataclass
class Step:
    """One unit of work. Root steps are bundled into a single pkexec call."""
    action: str  # helper action, or "flatpak"
    weight: float = 1.0

    @property
    def root(self) -> bool:
        return self.action != "flatpak"


@dataclass
class Job:
    key: str
    steps: list[Step] = field(default_factory=list)
    reboot_after: bool = True  # ask for a restart at the end?
    preview_erase: bool = False  # show what would be removed first


def make_job(key: str, with_flatpak: bool = True) -> Job:
    fp = [Step("flatpak", 2)] if with_flatpak else []
    up = Step("upgrade", 8)
    jobs = {
        "update": Job("update", [up, *fp]),
        "flatpak": Job("flatpak", [Step("flatpak", 1)], reboot_after=False),
        "discover": Job("discover", [Step("cancel-offline", 0.3), Step("clean", 0.3), up, *fp]),
        "clean": Job("clean", [Step("clean", 0.3), up, *fp]),
        "conflict": Job("conflict", [Step("clean", 0.3), Step("upgrade-erase", 8)], preview_erase=True),
        "pkcache": Job("pkcache", [Step("pkcache", 1)], reboot_after=False),
        "offline": Job("offline", [Step("offline-download", 8)], reboot_after=False),
        "offline-reboot": Job("offline-reboot", [Step("offline-reboot", 1)], reboot_after=False),
    }
    return jobs[key]


# ---------------------------------------------------------------- commands

def helper_script() -> str:
    return resources.files(__package__).joinpath("helper.sh").read_text()


def pkexec_command(actions: list[str]) -> tuple[str, list[str]]:
    """pkexec + bash running the bundled helper.

    The helper travels as the ``-c`` argument instead of a file path: root
    cannot read files inside a user's FUSE-mounted AppImage.
    """
    bash = shutil.which("bash") or "/usr/bin/bash"
    return "pkexec", [bash, "-c", helper_script(), "dnfpilot-helper", *actions]


CHECK_DNF = ("dnf", ["check-upgrade", "--refresh", "--assumeno"])
CHECK_FLATPAK = ("flatpak", ["remote-ls", "--updates", "--columns=application,name,version,branch"])
PREVIEW_ERASE = ("dnf", ["upgrade", "--refresh", "--best", "--allowerasing", "--assumeno"])
FLATPAK_UPDATE = ("flatpak", ["update", "-y", "--noninteractive"])
REBOOT = ("systemctl", ["reboot"])


# Packages whose update only takes effect after a restart: dnf's own
# needs-restarting list plus the desktop and graphics stack.
RESTART_PACKAGES = [
    "kernel", "kernel-core", "kernel-rt", "glibc", "linux-firmware", "systemd",
    "dbus", "dbus-broker", "dbus-daemon", "microcode_ctl", "zlib", "zlib-ng-compat",
    "plasma-workspace", "kwin", "kwin-wayland", "gnome-shell", "mutter",
    "mesa-dri-drivers", "mesa-vulkan-drivers", "akmod-nvidia", "xorg-x11-drv-nvidia",
]


def parse_restart_reasons(rpm_output: str, boot_time: int) -> list[str]:
    """Names from `rpm -q --qf '%{INSTALLTIME} %{NAME}\n' ...` installed after boot."""
    names = []
    for line in rpm_output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and int(parts[0]) > boot_time:
            if parts[1] not in names:
                names.append(parts[1])
    return names


def boot_time() -> int:
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("btime "):
            return int(line.split()[1])
    return 0


def restart_reasons() -> list[str]:
    """Core packages updated since the last boot; empty means no restart needed.

    Quicker than `dnf needs-restarting`, which as a normal user reloads every
    repository first.
    """
    if not have("rpm"):
        return []
    try:
        out = subprocess.run(
            ["rpm", "-q", "--qf", "%{INSTALLTIME} %{NAME}\\n", *RESTART_PACKAGES],
            capture_output=True, text=True, env=child_env(), timeout=20,
        ).stdout
        return parse_restart_reasons(out, boot_time())
    except (OSError, subprocess.SubprocessError):
        return []


def have(program: str) -> bool:
    return shutil.which(program) is not None


def offline_update_pending() -> bool:
    """True when Discover/PackageKit (or dnf offline) scheduled an update."""
    return Path("/system-update").exists() or Path("/var/lib/PackageKit/prepared-update").exists()


def is_fedora() -> bool:
    try:
        text = Path("/etc/os-release").read_text()
    except OSError:
        return False
    return bool(re.search(r"^(ID|ID_LIKE)=.*fedora", text, re.M))


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(CMD_ENV)
    return env
