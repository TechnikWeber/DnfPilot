"""Parser tests against dnf5 output.

check-upgrade.txt and upgrade.txt were captured from a real `dnf upgrade` in a
Fedora 44 container (LC_ALL=C, piped). erase-preview.txt is hand-written in
the same table format, since a real conflict is hard to reproduce on demand.
"""
import unittest
from pathlib import Path

from dnfpilot import backend

DATA = Path(__file__).parent / "data"


def read(name: str) -> str:
    return (DATA / name).read_text()


class CheckUpgrade(unittest.TestCase):
    def test_lists_all_packages(self):
        pkgs = backend.parse_check_upgrade(read("check-upgrade.txt"))
        self.assertEqual(len(pkgs), 71)
        git = next(p for p in pkgs if p.name == "git-core")
        self.assertEqual((git.version, git.source), ("2.56.0-1.fc44", "updates"))

    def test_epoch_and_plus_in_names(self):
        names = {p.name: p for p in backend.parse_check_upgrade(read("check-upgrade.txt"))}
        self.assertEqual(names["openssl"].version, "1:3.5.9-1.fc44")
        self.assertIn("python3-urllib3+socks", names)

    def test_ignores_repo_lines_and_warnings(self):
        text = (
            "Updating and loading repositories:\n"
            " Unity Hub                              100% |   5.7 KiB/s |   2.1 KiB |  00m00s\n"
            ">>> repomd.xml GPG signature verification error: Signing key not found\n"
            "Repositories loaded.\n"
        )
        self.assertEqual(backend.parse_check_upgrade(text), [])


class Flatpak(unittest.TestCase):
    def test_dedupes_branches(self):
        text = (
            "net.thunderbird.Thunderbird\tThunderbird\t158.0\tstable\n"
            "org.fedoraproject.Platform.GL.default\tMesa\t\tf44\n"
            "org.fedoraproject.Platform.GL.default\tMesa\t\tf44\n"
            "org.fedoraproject.Platform.GL.default\tMesa\t\tf43\n"
        )
        pkgs = backend.parse_flatpak_updates(text)
        self.assertEqual([p.name for p in pkgs], ["Thunderbird", "Mesa", "Mesa"])
        self.assertEqual(pkgs[0].version, "158.0")
        self.assertEqual(pkgs[1].version, "f44")


class Removals(unittest.TestCase):
    def test_removing_and_downgrading_only(self):
        rem = backend.parse_transaction_removals(read("erase-preview.txt"))
        self.assertEqual(
            rem,
            ["old-plugin 0:1.0-3.fc43", "old-plugin-extras 0:1.0-3.fc43", "libfoo 0:2.0-1.fc44"],
        )

    def test_plain_upgrade_removes_nothing(self):
        self.assertEqual(backend.parse_transaction_removals(read("upgrade.txt")), [])


class Progress(unittest.TestCase):
    def test_runs_monotonic_to_one(self):
        prog = backend.DnfProgress()
        last = 0.0
        seen_phases = []
        for line in read("upgrade.txt").splitlines():
            if prog.feed(line):
                self.assertGreaterEqual(prog.fraction, last - 1e-9, line)
                last = prog.fraction
                if prog.phase not in seen_phases:
                    seen_phases.append(prog.phase)
        self.assertEqual(seen_phases, ["resolve", "download", "install", "done"])
        self.assertEqual(prog.fraction, 1.0)

    def test_install_label_keeps_package(self):
        prog = backend.DnfProgress(phase="install")
        prog.feed("[ 65/151] Upgrading vim-enhanced-2:9.2. 100% |  87.3 MiB/s |   4.5 MiB |  00m00s")
        self.assertEqual(prog.label, "install 65/151 Upgrading vim-enhanced-2:9.2.")

    def test_flatpak_counts(self):
        prog = backend.FlatpakProgress(total=2)
        self.assertTrue(prog.feed("Updating app/net.thunderbird.Thunderbird/x86_64/stable"))
        self.assertEqual(prog.fraction, 0.0)
        prog.feed("Updating runtime/org.fedoraproject.Platform/x86_64/f44")
        self.assertEqual(prog.fraction, 0.5)


class Restart(unittest.TestCase):
    def test_only_packages_newer_than_boot(self):
        out = (
            "1790838999 glibc\n"
            "1794393823 kernel-core\n"
            "1794393823 kernel-core\n"
            "package kwin is not installed\n"
            "1794152412 mesa-dri-drivers\n"
        )
        self.assertEqual(backend.parse_restart_reasons(out, 1794391255), ["kernel-core"])


class Jobs(unittest.TestCase):
    def test_every_job_uses_known_actions(self):
        helper = backend.helper_script()
        for key in ("update", "flatpak", "discover", "clean", "conflict", "pkcache", "offline", "offline-reboot"):
            for step in backend.make_job(key).steps:
                if step.root:
                    self.assertIn(f"{step.action})", helper, f"{key}: {step.action}")

    def test_without_flatpak(self):
        self.assertEqual([s.action for s in backend.make_job("update", with_flatpak=False).steps], ["upgrade"])


if __name__ == "__main__":
    unittest.main()
