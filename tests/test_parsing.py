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
    def test_parse_rpm_last_kernel(self):
        # newest_kernel() reads `rpm -q --last kernel-core`; the format is checked here
        line = "kernel-core-7.3.3-200.fc44.x86_64          Mi 11 Nov 2026 09:12:01 CET"
        self.assertEqual(line.split()[0].removeprefix("kernel-core-"), "7.3.3-200.fc44.x86_64")

    def test_only_packages_newer_than_boot(self):
        out = (
            "1790838999 glibc\n"
            "1794393823 kernel-core\n"
            "1794393823 kernel-core\n"
            "package kwin is not installed\n"
            "1794152412 mesa-dri-drivers\n"
        )
        self.assertEqual(backend.parse_restart_reasons(out, 1794391255), ["kernel-core"])


class Firmware(unittest.TestCase):
    def test_fwupd_json(self):
        text = """{
          "Devices": [
            {"Name": "System Firmware", "Vendor": "LENOVO", "Version": "0.1.15",
             "Releases": [{"Version": "0.1.17", "Summary": "UEFI"}, {"Version": "0.1.16"}]},
            {"Name": "SSD", "Vendor": "Samsung", "Releases": []}
          ]
        }"""
        pkgs = backend.parse_fwupd_updates(text)
        self.assertEqual([(p.name, p.version, p.source, p.kind) for p in pkgs],
                         [("System Firmware", "0.1.17", "LENOVO", "firmware"), ("SSD", "", "Samsung", "firmware")])

    def test_fwupd_empty_or_garbage(self):
        self.assertEqual(backend.parse_fwupd_updates('{"Devices": []}'), [])
        self.assertEqual(backend.parse_fwupd_updates("No updatable devices"), [])


class Snap(unittest.TestCase):
    def test_refresh_list(self):
        text = ("Name     Version   Rev   Size   Publisher   Notes\n"
                "firefox  145.0-1   7310  280MB  mozilla✓    -\n"
                "core22   20261101  2100  77MB   canonical✓  base\n")
        self.assertEqual([(p.name, p.version) for p in backend.parse_snap_refresh(text)],
                         [("firefox", "145.0-1"), ("core22", "20261101")])

    def test_up_to_date(self):
        self.assertEqual(backend.parse_snap_refresh("All snaps up to date."), [])


class Releases(unittest.TestCase):
    def test_newest_final_release(self):
        text = """[
          {"version": "44", "arch": "x86_64", "variant": "KDE"},
          {"version": "45", "arch": "x86_64", "variant": "Everything"},
          {"version": "46 Beta", "arch": "x86_64", "variant": "Everything"}
        ]"""
        self.assertEqual(backend.parse_newest_release(text), 45)

    def test_offline(self):
        self.assertEqual(backend.parse_newest_release(""), 0)


class Jobs(unittest.TestCase):
    def test_every_job_uses_known_actions(self):
        helper = backend.helper_script()
        for key in ("update", "flatpak", "firmware", "discover", "clean", "conflict", "pkcache",
                    "offline", "offline-reboot", "sysup"):
            for step in backend.make_job(key, with_firmware=True, with_snap=True, release=45).steps:
                if step.root:
                    pattern = f"{step.base}:*)" if ":" in step.action else f"{step.action})"
                    self.assertIn(pattern, helper, f"{key}: {step.action}")

    def test_update_order(self):
        steps = backend.make_job("update", with_firmware=True, with_snap=True).steps
        self.assertEqual([s.action for s in steps], ["upgrade", "snap", "firmware", "flatpak"])

    def test_sysup(self):
        self.assertEqual([s.action for s in backend.make_job("sysup", release=45).steps],
                         ["upgrade", "sysup-download:45"])

    def test_download_only_progress_reaches_one_before_install(self):
        prog = backend.DnfProgress(dl_split=1.0)
        prog.feed("[ 1/2] a-1.0 100% | 1 MiB/s | 1 MiB | 00m01s")
        prog.feed("[ 2/2] b-1.0 100% | 1 MiB/s | 1 MiB | 00m01s")
        self.assertEqual(prog.fraction, 1.0)

    def test_without_flatpak(self):
        self.assertEqual([s.action for s in backend.make_job("update", with_flatpak=False).steps], ["upgrade"])


if __name__ == "__main__":
    unittest.main()
