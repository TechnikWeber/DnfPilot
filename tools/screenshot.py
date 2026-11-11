"""Renders docs/screenshot.png: the real window, filled with demo data from the
test fixtures (a running update), so the picture does not depend on what the
machine happens to need right now.

    python3 tools/screenshot.py            # needs a running desktop session
"""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dnfpilot import backend, window  # noqa: E402
from dnfpilot.i18n import tr  # noqa: E402

window.MainWindow.check = lambda self: None  # no real dnf calls

app = QApplication(sys.argv[:1])
app.setDesktopFileName("dnfpilot")
win = window.MainWindow()
data = ROOT / "tests" / "data"
win.updates = backend.parse_check_upgrade((data / "check-upgrade.txt").read_text())
win.updates += backend.parse_flatpak_updates(
    "net.thunderbird.Thunderbird\tThunderbird\t158.0\tstable\n"
    "org.fedoraproject.Platform\tFedora Platform\t44\tf44\n"
    "org.sane_project.xsane\tXSane\t0.999\tstable\n"
)
win.updates.append(backend.Package("System Firmware", "0.1.17", "LENOVO", "firmware"))
win._check_failed = False
win.current, win.newest = 44, 45
win._show_updates()
win._busy(True)
win.job = backend.make_job("update")
win.total_weight = sum(s.weight for s in win.job.steps)
win.done_weight = 0
lines = (data / "upgrade.txt").read_text().splitlines()
win._log("$ pkexec dnfpilot-helper upgrade")
prog = backend.DnfProgress()
for ln in lines[:-1]:
    if "Removing perl-Getopt" in ln:
        break
    win._log(ln)
    prog.feed(ln)
win._current("upgrade", win._dnf_label(prog), prog.fraction)
win.log_fold.set_open(True)
win.resize(760, 640)
win.show()


def shoot():
    out = ROOT / "docs" / "screenshot.png"
    win.grab().save(str(out))
    print("saved", out)
    app.quit()


QTimer.singleShot(800, shoot)
app.exec()
