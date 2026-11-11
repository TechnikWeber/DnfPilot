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
