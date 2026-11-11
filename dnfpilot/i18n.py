"""Tiny translation table: English is the key, German follows the system locale.

Set DNFPILOT_LANG=en or =de to override.
"""
from __future__ import annotations

import locale
import os

DE = {
    "Checking for updates…": "Suche nach Updates …",
    "Everything is up to date.": "Alles ist aktuell.",
    "{n} system updates": "{n} System-Updates",
    "1 system update": "1 System-Update",
    "{n} app updates": "{n} App-Updates",
    "1 app update": "1 App-Update",
    "{a} and {b} available.": "{a} und {b} verfügbar.",
    "{a} available.": "{a} verfügbar.",
    "Could not check for updates – see details.": "Suche nach Updates fehlgeschlagen – siehe Details.",
    "Restart recommended.": "Neustart empfohlen.",
    "Available updates ({n})": "Verfügbare Updates ({n})",
    "Include Flatpak apps": "Flatpak-Apps einbeziehen",
    "Name": "Name",
    "New version": "Neue Version",
    "Source": "Quelle",
    "Details": "Details",
    "Check again": "Erneut suchen",
    "Repair": "Reparieren",
    "Restart": "Neu starten",
    "Update now": "Jetzt aktualisieren",
    "Ready.": "Bereit.",
    "Discover has scheduled an offline update. If it keeps failing, cancel it and update here instead.":
        "Discover hat ein Offline-Update vorgemerkt. Wenn es immer wieder fehlschlägt: abbrechen und hier aktualisieren.",
    "Cancel it and update": "Abbrechen und aktualisieren",
    # repair menu
    "Cancel Discover's offline update, then update": "Discover-Offline-Update abbrechen, dann aktualisieren",
    "Reload package lists, then update": "Paketlisten neu laden, dann aktualisieren",
    "Resolve package conflicts (may remove packages)…": "Paketkonflikte lösen (kann Pakete entfernen) …",
    "Clear the Discover/PackageKit cache": "Discover-/PackageKit-Zwischenspeicher leeren",
    "Update Flatpak apps only": "Nur Flatpak-Apps aktualisieren",
    "Download now, install on next restart": "Jetzt herunterladen, beim Neustart installieren",
    # steps
    "Waiting for your password…": "Warte auf dein Passwort …",
    "Cancelling Discover's offline update": "Discover-Offline-Update wird abgebrochen",
    "Reloading package lists": "Paketlisten werden neu geladen",
    "Clearing the PackageKit cache": "PackageKit-Zwischenspeicher wird geleert",
    "Updating system packages": "Systempakete werden aktualisiert",
    "Downloading updates for the next restart": "Updates für den nächsten Neustart werden geladen",
    "Restarting to install updates": "Neustart zum Installieren",
    "Updating Flatpak apps": "Flatpak-Apps werden aktualisiert",
    "Loading repositories": "Paketquellen werden geladen",
    "Resolving dependencies": "Abhängigkeiten werden aufgelöst",
    "Downloading package {n} of {t}": "Lade Paket {n} von {t}",
    "Installing {n} of {t}": "Installiere {n} von {t}",
    "Finishing": "Wird abgeschlossen",
    "Step {i} of {n}: {what}": "Schritt {i} von {n}: {what}",
    "Checking for changes…": "Prüfe Änderungen …",
    # results
    "Done.": "Fertig.",
    "Cancelled – no password was entered.": "Abgebrochen – kein Passwort eingegeben.",
    "Not authorized to update the system.": "Keine Berechtigung, das System zu aktualisieren.",
    "Failed: {what} (exit code {rc}).": "Fehlgeschlagen: {what} (Exit-Code {rc}).",
    "Something went wrong.": "Etwas ist schiefgelaufen.",
    "{what} failed. The details below show dnf's own message.\n\nOften this helps: Repair → “Reload package lists, then update”. For conflicts between packages: Repair → “Resolve package conflicts”.":
        "{what} ist fehlgeschlagen. Die Details unten zeigen die Meldung von dnf.\n\nOft hilft: Reparieren → „Paketlisten neu laden, dann aktualisieren“. Bei Konflikten zwischen Paketen: Reparieren → „Paketkonflikte lösen“.",
    "Updates are installed. Kernel, Plasma, systemd or similar were updated – a restart is recommended.":
        "Die Updates sind installiert. Kernel, Plasma, systemd o. Ä. wurden aktualisiert – ein Neustart wird empfohlen.",
    "Updates are installed. A restart is not strictly needed.":
        "Die Updates sind installiert. Ein Neustart ist nicht unbedingt nötig.",
    "Restart now": "Jetzt neu starten",
    "Later": "Später",
    "Restart the computer now? Save your open work first.":
        "Den Computer jetzt neu starten? Speichere vorher deine offene Arbeit.",
    "All updates are downloaded. Restart now and install them during the restart?":
        "Alle Updates sind heruntergeladen. Jetzt neu starten und beim Neustart installieren?",
    "Restart and install": "Neu starten und installieren",
    "The Discover/PackageKit cache is empty.": "Der Discover-/PackageKit-Zwischenspeicher ist geleert.",
    "Flatpak apps are up to date.": "Die Flatpak-Apps sind aktuell.",
    "Resolve package conflicts": "Paketkonflikte lösen",
    "This update would remove or downgrade these packages:": "Dieses Update würde diese Pakete entfernen oder zurückstufen:",
    "Read the list carefully. Continue?": "Lies die Liste genau. Fortfahren?",
    "dnf would not remove or downgrade any package. Continue with the update?":
        "dnf würde kein Paket entfernen oder zurückstufen. Mit dem Update fortfahren?",
    "The preview failed, so it is unclear what would be removed. Look at the details first. Continue anyway?":
        "Die Vorschau ist fehlgeschlagen, daher ist unklar, was entfernt würde. Schau zuerst in die Details. Trotzdem fortfahren?",
    "Continue": "Fortfahren",
    "Cancel": "Abbrechen",
    "An update is running. Please wait until it has finished – stopping dnf halfway can damage the system.":
        "Ein Update läuft. Bitte warte, bis es fertig ist – dnf mittendrin abzubrechen kann das System beschädigen.",
    "This does not look like Fedora. dnfpilot only knows dnf and Flatpak, so most buttons will not work here.":
        "Das sieht nicht nach Fedora aus. dnfpilot kennt nur dnf und Flatpak, die meisten Knöpfe funktionieren hier nicht.",
    "pkexec is missing (package polkit), so the system cannot be updated from here.":
        "pkexec fehlt (Paket polkit), daher kann das System hier nicht aktualisiert werden.",
    # 0.2.0
    "Include firmware": "Firmware einbeziehen",
    "Update firmware only": "Nur Firmware aktualisieren",
    "Updating firmware": "Firmware wird aktualisiert",
    "Updating Snap apps": "Snap-Apps werden aktualisiert",
    "Downloading the new Fedora version": "Neue Fedora-Version wird heruntergeladen",
    "1 firmware update": "1 Firmware-Update",
    "{n} firmware updates": "{n} Firmware-Updates",
    "Upgrade…": "Upgrade …",
    "Fedora {new} is available – you are on Fedora {cur}. Discover does not show this on Fedora with dnf5.":
        "Fedora {new} ist verfügbar – du nutzt Fedora {cur}. Discover zeigt das unter Fedora mit dnf5 nicht an.",
    "Upgrade to Fedora {new}…": "Auf Fedora {new} upgraden …",
    "Upgrade to Fedora {new}": "Upgrade auf Fedora {new}",
    "How it works:\n\n1. Fedora {cur} is brought fully up to date.\n2. All packages of Fedora {new} are downloaded while you keep working.\n3. After a restart they are installed. That takes 20–60 minutes; do not switch the computer off.\n\nBefore you start: back up important files, plug in the power cable. Third-party repositories (VS Code, Docker, Unity …) sometimes lag behind a new release and can block the download – the details then say which one.":
        "So läuft es ab:\n\n1. Fedora {cur} wird vollständig aktualisiert.\n2. Alle Pakete von Fedora {new} werden heruntergeladen, während du weiterarbeitest.\n3. Nach einem Neustart werden sie installiert. Das dauert 20–60 Minuten; den Computer dabei nicht ausschalten.\n\nVorher: wichtige Dateien sichern, Netzteil anschließen. Fremde Paketquellen (VS Code, Docker, Unity …) hinken einer neuen Version manchmal hinterher und können den Download blockieren – die Details nennen dann die Quelle.",
    "Download Fedora {new}": "Fedora {new} herunterladen",
    "Fedora {new} is downloaded. Restart now to install it? The installation takes 20–60 minutes – do not switch the computer off.":
        "Fedora {new} ist heruntergeladen. Jetzt neu starten und installieren? Die Installation dauert 20–60 Minuten – den Computer dabei nicht ausschalten.",
    "The download stays ready. To install it later, run this in a terminal and restart:\n\nsudo dnf offline reboot":
        "Der Download bleibt bereit. Zum späteren Installieren im Terminal eingeben (startet neu):\n\nsudo dnf offline reboot",
    "The NVIDIA driver is still being built for the new kernel. Restarting now would end with a black screen.":
        "Der NVIDIA-Treiber wird noch für den neuen Kernel gebaut. Ein Neustart jetzt endet mit schwarzem Bildschirm.",
    "Updates are installed. The NVIDIA driver is still being built for the new kernel – the Restart button unlocks as soon as it is ready (usually within 5 minutes).":
        "Die Updates sind installiert. Der NVIDIA-Treiber wird noch für den neuen Kernel gebaut – der Neustart-Knopf wird frei, sobald er fertig ist (meist innerhalb von 5 Minuten).",
    "{what} failed. The details below show the original message.\n\nOften this helps: Repair → “Reload package lists, then update”. For conflicts between packages: Repair → “Resolve package conflicts”.":
        "{what} ist fehlgeschlagen. Die Details unten zeigen die Originalmeldung.\n\nOft hilft: Reparieren → „Paketlisten neu laden, dann aktualisieren“. Bei Konflikten zwischen Paketen: Reparieren → „Paketkonflikte lösen“.",
    "Only {free:.1f} GB are free on the system disk. An upgrade needs at least {need} GB for the download and the installation – free up space first (e.g. old files in ~/Downloads, ~/.cache, unused Flatpaks: flatpak uninstall --unused).":
        "Auf der Systemplatte sind nur {free:.1f} GB frei. Ein Upgrade braucht mindestens {need} GB für Download und Installation – erst Platz schaffen (z. B. alte Dateien in ~/Downloads, ~/.cache, ungenutzte Flatpaks: flatpak uninstall --unused).",
    "Try anyway": "Trotzdem versuchen",
}


def _pick() -> str:
    forced = os.environ.get("DNFPILOT_LANG", "").lower()
    if forced in ("de", "en"):
        return forced
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(var)
        if val:
            return "de" if val.lower().startswith("de") else "en"
    lang = (locale.getlocale()[0] or "").lower()
    return "de" if lang.startswith("de") else "en"


LANG = _pick()


def tr(text: str, **kw) -> str:
    out = DE.get(text, text) if LANG == "de" else text
    return out.format(**kw) if kw else out
