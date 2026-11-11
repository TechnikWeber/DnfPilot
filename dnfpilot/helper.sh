#!/usr/bin/env bash
# Root helper for dnfpilot. Runs through pkexec, so there is exactly one
# password prompt per job. Every argument is one action, executed in order.
# The GUI reads the "@@FU" marker lines to follow along; everything else is
# plain dnf output for the details view.
#
# Actions:
#   cancel-offline   cancel an offline update that Discover/PackageKit scheduled
#   clean            dnf clean all
#   pkcache          empty /var/cache/PackageKit
#   upgrade          dnf upgrade --refresh
#   upgrade-erase    dnf upgrade --refresh --best --allowerasing
#   offline-download dnf offline download --refresh
#   offline-reboot   dnf offline reboot
#   firmware         fwupdmgr refresh + update (no reboot prompt; the GUI asks)
#   snap             snap refresh
#   sysup-download:N dnf system-upgrade download --releasever=N
#   sysup-download-erase:N  the same with --allowerasing (after the user saw the list)

export LC_ALL=C LANG=C
# keep dnf off the terminal-only progress bars and colours
export TERM=dumb NO_COLOR=1

marker() { printf '@@FU %s\n' "$*"; }

run_action() {
    case "$1" in
        cancel-offline)
            # PackageKit says "no offline update" with a non-zero code; that is fine
            pkcon offline-cancel </dev/null || echo "(no offline update was scheduled)"
            ;;
        clean)            dnf clean all </dev/null ;;
        pkcache)          rm -rf /var/cache/PackageKit/* ;;
        upgrade)          dnf upgrade --refresh -y </dev/null ;;
        upgrade-erase)    dnf upgrade --refresh --best --allowerasing -y </dev/null ;;
        offline-download) dnf offline download --refresh -y </dev/null ;;
        offline-reboot)   dnf offline reboot -y </dev/null ;;
        firmware)
            fwupdmgr refresh --force </dev/null || true
            # exit code 2 means "nothing to do"
            fwupdmgr update -y --no-reboot-check --no-unreported-check </dev/null
            local fw=$?
            [ "$fw" -eq 2 ] && fw=0
            return "$fw"
            ;;
        snap)             snap refresh </dev/null ;;
        sysup-download:*)
            ver="${1#*:}"
            case "$ver" in
                ''|*[!0-9]*) echo "bad release: $ver" >&2; return 2 ;;
            esac
            dnf system-upgrade download --releasever="$ver" -y </dev/null
            ;;
        sysup-download-erase:*)
            ver="${1#*:}"
            case "$ver" in
                ''|*[!0-9]*) echo "bad release: $ver" >&2; return 2 ;;
            esac
            dnf system-upgrade download --releasever="$ver" --allowerasing -y </dev/null
            ;;
        *)                echo "unknown action: $1" >&2; return 2 ;;
    esac
}

for action in "$@"; do
    marker "step $action"
    run_action "$action" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        marker "fail $action $rc"
        exit "$rc"
    fi
    marker "done $action"
done
marker "finished"
