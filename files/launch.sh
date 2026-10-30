#!/bin/sh
# Wine for Marmoset Toolbag: starts Toolbag from Bottles, but never a second one.
# Installed by install.sh with the @...@ values filled in.
#
# Bottles Flatpak runs every launch in its own sandbox with its own wineserver. A second launch on
# the same bottle can't see the first one, and the two break each other (Bottles freezes).

CLI='@CLI@'
BOTTLE='@BOTTLE@'
PROGRAM='@PROGRAM@'
PREFIX='@PREFIX@'
EXE='@EXE@'
NAME='@NAME@'
ICON='@ICON@'

# the program itself, in this bottle
running() {
    for p in $(pgrep -f -i -- "$EXE"); do
        tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null | grep -qxF "WINEPREFIX=$PREFIX" && return 0
    done
    return 1
}

# Bottles is still starting it (a launch younger than 90 s; older leftovers don't count)
starting() {
    for b in $(pgrep -f -- "bottles-cli run -b $BOTTLE -p $PROGRAM"); do
        [ "$(ps -o etimes= -p "$b" 2>/dev/null | tr -d ' ')" -lt 90 ] 2>/dev/null && return 0
    done
    return 1
}

# Bottles Flatpak sometimes leaves a dead session behind: Wine's services (services.exe,
# winedevice.exe, ...) keep running in the old sandbox after its wineserver is gone, and the next
# start on the same bottle can hang without a window. Close such a sandbox, but only if it belongs
# to this bottle, its wineserver is gone, and no program and no Bottles window is left in it.
cleanup_stale() {
    case "$CLI" in flatpak*) ;; *) return 0 ;; esac
    for p in /proc/[0-9]*; do
        info="$p/root/.flatpak-info"
        grep -qxF 'name=com.usebottles.bottles' "$info" 2>/dev/null || continue
        inst=$(sed -n 's/^instance-id=//p' "$info" 2>/dev/null)
        [ -n "$inst" ] || continue
        if tr '\0' '\n' < "$p/environ" 2>/dev/null | grep -qxF "WINEPREFIX=$PREFIX"; then mine=1; else mine=0; fi
        case "$(cat "$p/comm" 2>/dev/null)" in
        services.exe|winedevice.exe|plugplay.exe|svchost.exe|rpcss.exe|lsass.exe|explorer.exe|conhost.exe|tabtip.exe|rundll32.exe)
            kind=service ;;
        bwrap|xdg-dbus-proxy|bottles-cli|start.exe|sh|bash)
            kind=other ;;
        *)  kind=busy ;;         # wineserver, a program, the Bottles window ...
        esac
        echo "$inst $kind $mine"
    done | awk '{ if ($2 == "busy") busy[$1] = 1; if ($2 == "service" && $3 == 1) left[$1] = 1 }
                END { for (i in left) if (!(i in busy)) print i }' |
    while read -r inst; do
        flatpak kill "$inst" 2>/dev/null && sleep 1
    done
    return 0
}

# The NVIDIA driver needs /dev/nvidia-uvm to create a Vulkan device. The kernel module can be loaded
# without it, and the Flatpak sandbox can't create it, so Toolbag fails with "Failed to create Vulkan
# device, vr -3". nvidia-modprobe is the driver's own helper for this and doesn't need sudo.
check_nvidia_uvm() {
    [ -e /proc/driver/nvidia/version ] || return 0    # no NVIDIA driver loaded
    [ -e /dev/nvidia-uvm ] && return 0
    nvidia-modprobe -c 0 -u 2>/dev/null
    [ -e /dev/nvidia-uvm ] && return 0
    notify-send -u critical -i "$ICON" "$NAME may not start" \
        "/dev/nvidia-uvm is missing. Run this in a terminal, then start $NAME again: sudo nvidia-modprobe -c 0 -u"
    return 0
}

if running || starting; then
    # urgent, so GNOME shows it on top of a fullscreen window too
    notify-send -u critical -i "$ICON" "$NAME is already running" "Only one $NAME can run at a time."
    exit 0
fi
cleanup_stale
check_nvidia_uvm
exec $CLI run -b "$BOTTLE" -p "$PROGRAM"
