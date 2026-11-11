"""The main window: update list, progress bar, fold-out details, buttons."""
from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QSettings, Qt, Signal
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import backend
from .backend import DnfProgress, FlatpakProgress, Job, Package
from .i18n import tr
from .icon import app_icon

STEP_TITLES = {
    "cancel-offline": "Cancelling Discover's offline update",
    "clean": "Reloading package lists",
    "pkcache": "Clearing the PackageKit cache",
    "upgrade": "Updating system packages",
    "upgrade-erase": "Updating system packages",
    "offline-download": "Downloading updates for the next restart",
    "offline-reboot": "Restarting to install updates",
    "flatpak": "Updating Flatpak apps",
}
DNF_STEPS = {"upgrade", "upgrade-erase", "offline-download"}


class Runner(QObject):
    """One child process; emits its output line by line (stdout+stderr merged)."""
    line = Signal(str)
    finished = Signal(int, str)  # exit code, collected output

    def __init__(self, parent: QObject, program: str, args: list[str]):
        super().__init__(parent)
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        for k, v in backend.CMD_ENV.items():
            env.insert(k, v)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.setStandardInputFile(QProcess.nullDevice())
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self.proc.errorOccurred.connect(self._error)
        self.program, self.args = program, args
        self._buf = ""
        self._all: list[str] = []
        self._ended = False

    def start(self):
        self.proc.start(self.program, self.args)

    def running(self) -> bool:
        return self.proc.state() != QProcess.NotRunning

    def _read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._buf += data.replace("\r", "\n")
        *lines, self._buf = self._buf.split("\n")
        for ln in lines:
            if ln.strip():
                self._all.append(ln)
                self.line.emit(ln)

    def _done(self, code: int, _status):
        if self._ended:
            return
        self._read()
        if self._buf.strip():
            self._all.append(self._buf)
            self.line.emit(self._buf)
        self._ended = True
        self.finished.emit(code, "\n".join(self._all))

    def _error(self, err):
        if err == QProcess.FailedToStart and not self._ended:
            self._ended = True
            msg = f"{self.program}: could not be started"
            self.line.emit(msg)
            self.finished.emit(127, msg)


class Fold(QWidget):
    """A clickable header that shows or hides one widget below it."""

    def __init__(self, title: str, body: QWidget, open_: bool, extra: QWidget | None = None):
        super().__init__()
        self.body = body
        self.btn = QToolButton(text=title, checkable=True, checked=open_)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.btn.toggled.connect(self._toggle)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.btn)
        head.addStretch()
        if extra:
            head.addWidget(extra)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(head)
        lay.addWidget(body)
        self._toggle(open_)

    def _toggle(self, on: bool):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)

    def set_title(self, title: str):
        self.btn.setText(title)

    def set_open(self, on: bool):
        self.btn.setChecked(on)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("dnfpilot", "dnfpilot")
        self.setWindowTitle(tr("DnfPilot"))
        self.setWindowIcon(app_icon())
        self.resize(720, 560)

        self.runner: Runner | None = None
        self.root_busy = False
        self.in_job = False
        self.updates: list[Package] = []
        self.reboot_needed = False
        self.reboot_reasons: list[str] = []
        self._build()
        self.check()

    # ------------------------------------------------------------ layout
    def _build(self):
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(56, 56))
        self.title = QLabel(tr("DnfPilot"))
        f = self.title.font()
        f.setPointSizeF(f.pointSizeF() * 1.5)
        f.setBold(True)
        self.title.setFont(f)
        self.status = QLabel(tr("Checking for updates…"))
        self.status.setWordWrap(True)
        text = QVBoxLayout()
        text.addWidget(self.title)
        text.addWidget(self.status)
        head = QHBoxLayout()
        head.addWidget(icon)
        head.addSpacing(8)
        head.addLayout(text, 1)

        # warning when Discover left an offline update behind
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        self.banner.setStyleSheet(
            "#banner { background: rgba(246, 116, 0, 0.15); border: 1px solid rgba(246, 116, 0, 0.6); border-radius: 6px; }"
        )
        bl = QHBoxLayout(self.banner)
        msg = QLabel(tr("Discover has scheduled an offline update. If it keeps failing, cancel it and update here instead."))
        msg.setWordWrap(True)
        fix = QPushButton(tr("Cancel it and update"))
        fix.clicked.connect(lambda: self.start_job("discover"))
        bl.addWidget(msg, 1)
        bl.addWidget(fix)
        self.banner_btn = fix
        self.banner.setVisible(backend.offline_update_pending())

        # update list
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Name"), tr("New version"), tr("Source")])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.with_flatpak = QCheckBox(tr("Include Flatpak apps"))
        self.with_flatpak.setChecked(self.settings.value("flatpak", True, type=bool))
        self.with_flatpak.setEnabled(backend.have("flatpak"))
        self.with_flatpak.toggled.connect(self._flatpak_toggled)
        self.list_fold = Fold(tr("Available updates ({n})", n=0), self.tree, True, self.with_flatpak)

        # progress
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.step = QLabel(tr("Ready."))
        self.step.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # details log
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.log.setMaximumBlockCount(20000)
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_fold = Fold(tr("Details"), self.log, False)

        # buttons
        self.btn_check = QPushButton(QIcon.fromTheme("view-refresh"), tr("Check again"))
        self.btn_check.clicked.connect(self.check)
        self.btn_repair = QToolButton(text=tr("Repair"), icon=QIcon.fromTheme("tools-wizard"))
        self.btn_repair.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_repair.setPopupMode(QToolButton.InstantPopup)
        self.btn_repair.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        menu = QMenu(self)
        for key, label in (
            ("discover", "Cancel Discover's offline update, then update"),
            ("clean", "Reload package lists, then update"),
            ("conflict", "Resolve package conflicts (may remove packages)…"),
            ("pkcache", "Clear the Discover/PackageKit cache"),
            (None, None),
            ("flatpak", "Update Flatpak apps only"),
            ("offline", "Download now, install on next restart"),
        ):
            if key is None:
                menu.addSeparator()
                continue
            act = menu.addAction(tr(label))
            act.triggered.connect(lambda _=False, k=key: self.start_job(k))
        self.btn_repair.setMenu(menu)
        self.btn_reboot = QPushButton(QIcon.fromTheme("system-reboot"), tr("Restart"))
        self.btn_reboot.clicked.connect(self.ask_reboot)
        self.btn_update = QPushButton(QIcon.fromTheme("system-software-update"), tr("Update now"))
        self.btn_update.setDefault(True)
        self.btn_update.clicked.connect(lambda: self.start_job("update"))
        foot = QHBoxLayout()
        foot.addWidget(self.btn_check)
        foot.addWidget(self.btn_repair)
        foot.addStretch()
        foot.addWidget(self.btn_reboot)
        foot.addWidget(self.btn_update)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        lay.addLayout(head)
        if not backend.is_fedora():
            lay.addWidget(self._note(tr("This does not look like Fedora. dnfpilot only knows dnf and Flatpak, so most buttons will not work here.")))
        if not backend.have("pkexec"):
            lay.addWidget(self._note(tr("pkexec is missing (package polkit), so the system cannot be updated from here.")))
        lay.addWidget(self.banner)
        lay.addWidget(self.list_fold, 3)
        lay.addWidget(self.bar)
        lay.addWidget(self.step)
        lay.addWidget(self.log_fold, 2)
        lay.addLayout(foot)

    @staticmethod
    def _note(text: str) -> QLabel:
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setStyleSheet("color: palette(placeholder-text);")
        return lab

    # ------------------------------------------------------------ helpers
    def _busy(self, busy: bool):
        for w in (self.btn_check, self.btn_repair, self.btn_reboot, self.btn_update, self.banner_btn, self.with_flatpak):
            w.setEnabled(not busy)
        if not busy:
            self.with_flatpak.setEnabled(backend.have("flatpak"))

    def _log(self, text: str):
        self.log.appendPlainText(text)

    def _run(self, cmd: tuple[str, list[str]], on_line, on_done, show_cmd: str | None = None):
        program, args = cmd
        self._log(f"$ {show_cmd or ' '.join([program, *args])}")
        r = Runner(self, program, args)
        r.line.connect(self._log)
        if on_line:
            r.line.connect(on_line)

        def done(code, out):
            self.runner = None
            r.deleteLater()
            on_done(code, out)

        r.finished.connect(done)
        self.runner = r
        r.start()

    def _set_progress(self, fraction: float | None):
        if fraction is None:
            self.bar.setRange(0, 0)  # busy indicator
        else:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(max(0.0, min(1.0, fraction)) * 1000))

    def _flatpak_toggled(self, on: bool):
        self.settings.setValue("flatpak", on)
        self.check()

    # ------------------------------------------------------------ check
    def check(self):
        if self.runner:
            return
        self._busy(True)
        self.status.setText(tr("Checking for updates…"))
        self.step.setText(tr("Checking for updates…"))
        self._set_progress(None)
        self.banner.setVisible(backend.offline_update_pending())
        self.updates = []
        self._check_failed = False

        def after_flatpak(code, out):
            if code == 0:
                self.updates += backend.parse_flatpak_updates(out)
            self.reboot_reasons = backend.restart_reasons()
            self.reboot_needed = bool(self.reboot_reasons)
            self._show_updates()

        def after_dnf(code, out):
            # check-upgrade: 100 = updates available, 0 = none
            if code in (0, 100):
                self.updates += backend.parse_check_upgrade(out)
            else:
                self._check_failed = True
            if self.with_flatpak.isChecked() and backend.have("flatpak"):
                self._run(backend.CHECK_FLATPAK, None, after_flatpak)
            else:
                after_flatpak(1, "")

        if backend.have("dnf"):
            self._run(backend.CHECK_DNF, None, after_dnf)
        else:
            after_dnf(1, "")

    def _show_updates(self):
        self.tree.clear()
        for p in self.updates:
            QTreeWidgetItem(self.tree, [p.name, p.version, "Flatpak" if p.kind == "flatpak" else p.source])
        rpm = sum(p.kind == "rpm" for p in self.updates)
        fp = sum(p.kind == "flatpak" for p in self.updates)
        self.list_fold.set_title(tr("Available updates ({n})", n=len(self.updates)))
        parts = []
        if rpm:
            parts.append(tr("1 system update") if rpm == 1 else tr("{n} system updates", n=rpm))
        if fp:
            parts.append(tr("1 app update") if fp == 1 else tr("{n} app updates", n=fp))
        if self._check_failed:
            text = tr("Could not check for updates – see details.")
            self.log_fold.set_open(True)
        elif len(parts) == 2:
            text = tr("{a} and {b} available.", a=parts[0], b=parts[1])
        elif parts:
            text = tr("{a} available.", a=parts[0])
        else:
            text = tr("Everything is up to date.")
        if self.reboot_needed:
            text += " " + tr("Restart recommended.") + " (" + ", ".join(self.reboot_reasons[:4]) + ")"
        self.status.setText(text)
        self.step.setText(tr("Ready."))
        self._set_progress(0)
        self._busy(False)
        self._style_reboot()

    def _style_reboot(self):
        self.btn_reboot.setDefault(self.reboot_needed)
        self.btn_update.setDefault(not self.reboot_needed)

    # ------------------------------------------------------------ jobs
    def start_job(self, key: str):
        if self.runner:
            return
        job = backend.make_job(key, with_flatpak=self.with_flatpak.isChecked() and backend.have("flatpak"))
        if key == "flatpak" and not backend.have("flatpak"):
            return
        self._busy(True)
        if job.preview_erase:
            self._preview_erase(job)
        else:
            self._run_job(job)

    def _preview_erase(self, job: Job):
        self.step.setText(tr("Checking for changes…"))
        self._set_progress(None)

        def done(code, out):
            removals = backend.parse_transaction_removals(out)
            # --assumeno ends with "Operation aborted" whenever there was something to do
            if code != 0 and "Operation aborted" not in out:
                text = tr("The preview failed, so it is unclear what would be removed. Look at the details first. Continue anyway?")
                self.log_fold.set_open(True)
            elif removals:
                text = tr("This update would remove or downgrade these packages:") + "\n\n" + \
                    "\n".join(f"  • {r}" for r in removals[:40]) + ("\n  …" if len(removals) > 40 else "") + \
                    "\n\n" + tr("Read the list carefully. Continue?")
            else:
                text = tr("dnf would not remove or downgrade any package. Continue with the update?")
            box = QMessageBox(QMessageBox.Warning, tr("Resolve package conflicts"), text, parent=self)
            go = box.addButton(tr("Continue"), QMessageBox.AcceptRole)
            box.addButton(tr("Cancel"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is go:
                self._run_job(job)
            else:
                self._finish_idle(tr("Ready."))

        self._run(backend.PREVIEW_ERASE, None, done)

    def _run_job(self, job: Job):
        self.job = job
        self.in_job = True
        self.total_weight = sum(s.weight for s in job.steps) or 1
        self.done_weight = 0.0
        self.step_index = 0
        root = [s for s in job.steps if s.root]
        rest = [s for s in job.steps if not s.root]
        self._set_progress(0)
        if root:
            self._run_root(root, rest)
        else:
            self._run_user(rest)

    def _current(self, action: str, sub: str = "", fraction: float = 0.0):
        step = next(s for s in self.job.steps if s.action == action)
        i = self.job.steps.index(step) + 1
        what = tr(STEP_TITLES[action])
        if sub:
            what += " – " + sub
        self.step.setText(tr("Step {i} of {n}: {what}", i=i, n=len(self.job.steps), what=what))
        self._set_progress((self.done_weight + step.weight * fraction) / self.total_weight)

    def _run_root(self, steps, rest):
        self.root_busy = True
        self.step.setText(tr("Waiting for your password…"))
        self._set_progress(None)
        state = {"action": None, "dnf": DnfProgress()}

        def on_line(ln: str):
            if ln.startswith("@@FU "):
                parts = ln.split()
                if parts[1] == "step":
                    state["action"] = parts[2]
                    state["dnf"] = DnfProgress()
                    self._current(parts[2], tr("Loading repositories") if parts[2] in DNF_STEPS else "")
                elif parts[1] == "done":
                    self.done_weight += next(s.weight for s in self.job.steps if s.action == parts[2])
                    self._set_progress(self.done_weight / self.total_weight)
                return
            act = state["action"]
            if act in DNF_STEPS:
                prog: DnfProgress = state["dnf"]
                if prog.feed(ln):
                    self._current(act, self._dnf_label(prog), prog.fraction)

        def done(code, out):
            self.root_busy = False
            if code == 0:
                if rest:
                    self._run_user(rest)
                else:
                    self._job_done()
                return
            if code == 126:
                self._finish_idle(tr("Cancelled – no password was entered."))
            elif code == 127 and "@@FU" not in out:
                self._finish_idle(tr("Not authorized to update the system."))
            else:
                failed = next((ln.split()[2] for ln in out.splitlines() if ln.startswith("@@FU fail")), state["action"])
                self._failed(failed or "upgrade", code)

        actions = [s.action for s in steps]
        self._run(backend.pkexec_command(actions), on_line, done,
                  show_cmd="pkexec dnfpilot-helper " + " ".join(actions))

    @staticmethod
    def _dnf_label(p: DnfProgress) -> str:
        if p.phase == "resolve":
            return tr("Resolving dependencies")
        if p.label.startswith("download "):
            n, t = p.label.split()[1].split("/")
            return tr("Downloading package {n} of {t}", n=n, t=t)
        if p.label.startswith("install "):
            n, t = p.label.split()[1].split("/")
            return tr("Installing {n} of {t}", n=n, t=t)
        return tr("Finishing")

    def _run_user(self, steps):
        # only Flatpak runs without root
        step = steps[0]
        total = sum(p.kind == "flatpak" for p in self.updates)
        prog = FlatpakProgress(total=total)
        self._current(step.action, fraction=0)

        def on_line(ln):
            if prog.feed(ln):
                self._current(step.action, prog.label, prog.fraction)

        def done(code, _out):
            if code != 0:
                self._failed("flatpak", code)
                return
            self.done_weight += step.weight
            self._job_done()

        self._run(backend.FLATPAK_UPDATE, on_line, done)

    def _failed(self, action: str, code: int):
        what = tr(STEP_TITLES.get(action, "upgrade"))
        self.log_fold.set_open(True)
        self._finish_idle(tr("Failed: {what} (exit code {rc}).", what=what, rc=code))
        QMessageBox.critical(self, tr("Something went wrong."), tr(
            "{what} failed. The details below show dnf's own message.\n\nOften this helps: Repair → “Reload package lists, then update”. For conflicts between packages: Repair → “Resolve package conflicts”.",
            what=what))

    def _finish_idle(self, text: str):
        self.in_job = False
        self.step.setText(text)
        self._set_progress(0)
        self._busy(False)

    def _job_done(self):
        self._set_progress(1)
        self.step.setText(tr("Done."))
        key = self.job.key
        if key == "offline":
            box = QMessageBox(QMessageBox.Question, tr("DnfPilot"),
                              tr("All updates are downloaded. Restart now and install them during the restart?"), parent=self)
            go = box.addButton(tr("Restart and install"), QMessageBox.AcceptRole)
            box.addButton(tr("Later"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is go:
                self._run_job(backend.make_job("offline-reboot"))
                return
        elif key == "pkcache":
            QMessageBox.information(self, tr("DnfPilot"), tr("The Discover/PackageKit cache is empty."))
        elif key == "flatpak":
            QMessageBox.information(self, tr("DnfPilot"), tr("Flatpak apps are up to date."))

        if self.job.reboot_after:
            self.reboot_needed = bool(backend.restart_reasons())
            self._offer_reboot()
        else:
            self._refresh_after()

    def _offer_reboot(self):
        text = tr("Updates are installed. Kernel, Plasma, systemd or similar were updated – a restart is recommended.") \
            if self.reboot_needed else tr("Updates are installed. A restart is not strictly needed.")
        box = QMessageBox(QMessageBox.Question if self.reboot_needed else QMessageBox.Information,
                          tr("DnfPilot"), text, parent=self)
        go = box.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        later = box.addButton(tr("Later"), QMessageBox.RejectRole)
        box.setDefaultButton(go if self.reboot_needed else later)
        box.exec()
        if box.clickedButton() is go:
            self.reboot()
        else:
            self._refresh_after()

    def _refresh_after(self):
        self.in_job = False
        self._busy(False)
        self.check()

    # ------------------------------------------------------------ restart
    def ask_reboot(self):
        box = QMessageBox(QMessageBox.Question, tr("Restart"),
                          tr("Restart the computer now? Save your open work first."), parent=self)
        go = box.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancel"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is go:
            self.reboot()

    def reboot(self):
        self.in_job = False
        program, args = backend.REBOOT
        QProcess.startDetached(program, args)

    # ------------------------------------------------------------ closing
    def closeEvent(self, ev):
        if self.root_busy or self.in_job:
            QMessageBox.warning(self, tr("DnfPilot"), tr(
                "An update is running. Please wait until it has finished – stopping dnf halfway can damage the system."))
            ev.ignore()
            return
        if self.runner and self.runner.running():
            self.runner.proc.kill()  # only a check; safe to stop
        ev.accept()
