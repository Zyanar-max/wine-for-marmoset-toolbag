# Wine for Marmoset Toolbag

Fixes for running **Marmoset Toolbag** on Linux in **Bottles**. Install Toolbag in a bottle, run one script, and you're done.

> **I made this for my own setup and I'm sharing it as is. There's no support, so please don't contact me about it.** If it doesn't work on your system, `sh install.sh --uninstall` puts everything back. Use it at your own risk.
>
> Vibe-coded with [Claude](https://claude.com/claude-code) (Claude Code).

| # | Problem | Fix |
|---|---------|-----|
| 1 | Opening an image from Toolbag (e.g. a finished render) does nothing, or opens Wine's Internet Explorer | Images (.png .jpg .gif .tga .exr .psd .tif .hdr) open in your Linux image viewer |
| 2 | No menu entry, or a generic icon | Menu entry with Toolbag's own icon. If you already have one, it's kept and only routed through the launcher |
| 3 | Starting Toolbag a second time freezes Bottles | Only one Toolbag at a time: a second start only shows a notification |
| 4 | Toolbag 5 needs DirectX 12 | Checks that DXVK, VKD3D-Proton and DXVK-NVAPI are on in the bottle |
| 5 | With NVIDIA, Toolbag sometimes won't start after a reboot (`Failed to create Vulkan device, vr -3`) | The launcher checks `/dev/nvidia-uvm` before every start and creates it if it's missing |

## Requirements

- [Bottles](https://usebottles.com) (Flatpak or native)
- Marmoset Toolbag installed in a bottle (tested: Toolbag 5.03), added as a program in Bottles
- An X11 desktop or XWayland. Tested on Rocky Linux 9 with GNOME on X11.

**Tip for the Toolbag installer:** Bottles (Flatpak) can't see your Downloads folder. Put the installer on a drive or in a folder Bottles can see, or copy it into the bottle's `drive_c`.

At the end, the Toolbag installer asks you to restart Windows because of a graphics driver timeout (TDR) setting. Under Wine that setting does nothing; you don't need to restart anything.

## Install

1. Close Toolbag.
2. Run:
   ```sh
   sh install.sh
   ```
   The script finds the bottle that has `toolbag.exe` in it. If you have more than one, use `sh install.sh --bottle NAME`.
3. Start Toolbag from the menu or the dock.

**After a Bottles update**, Bottles sometimes resets the bottle, and images stop opening again. Just run the script again (`sh install.sh --bottle NAME --yes`). You can run it as many times as you like.

### Start Toolbag only once

If you start a second Toolbag while one is already running, Bottles freezes. Bottles (Flatpak) runs every launch in its own sandbox, and the two break each other. The launcher (`~/.local/bin/wine-for-marmoset-toolbag`) prevents this: if Toolbag is already running, or still starting, you only get a notification.

The script looks for menu entries (`.desktop` files in `~/.local/share/applications`) that start Toolbag from this bottle and routes them through the launcher, so your dock icon keeps working. If there's none, it creates a "Marmoset Toolbag" menu entry.

Before it starts the program, the launcher also closes a dead Bottles sandbox of the same bottle, if one was left behind: Wine's services (services.exe, winedevice.exe, ...) still running without a wineserver. Otherwise the next start can hang without a window. It never closes a sandbox that still has a wineserver, a program or the Bottles window in it.

Starting Toolbag with the ▶ button in the Bottles window isn't protected.

The notification is urgent, so GNOME shows it on top of a fullscreen window too. It stays until you close it.

### Toolbag won't start after a reboot (NVIDIA)

The NVIDIA driver needs the device file `/dev/nvidia-uvm` to create a Vulkan device. It disappears on every reboot, and something has to create it again. The Bottles (Flatpak) sandbox can't, so without it Toolbag fails with `Failed to create Vulkan device, vr -3`.

Before every start, the launcher checks for this file and creates it with `nvidia-modprobe`, the NVIDIA driver's own helper. This needs no sudo and changes no driver setting. If it can't create the file, you get a notification with the command to run. Without an NVIDIA driver, the launcher skips this check.

Starting Toolbag with the ▶ button in the Bottles window skips this check too.

## Set these yourself

### UI size (HiDPI / 4K)

Toolbag works fine with Wine's own scaling: in Bottles open the bottle → **Settings → Display → DPI**. 144 is 150%, 192 is 200%. Restart Toolbag afterwards.

### Render output folder

By default Toolbag saves renders to the bottle's own Desktop folder (`drive_c/users/YOU/Desktop`), which is hidden inside the bottle. Set the output path in the render settings to a drive you can see from Linux.

### Viewport speed

If the ray-traced viewport is slow, raise the ray tracing memory budget in Toolbag's preferences.

## Uninstall

```sh
sh install.sh --uninstall
```

This restores the old image file associations and your menu entries, and removes the launcher and the icon.

## What it changes

- In the bottle's `system.reg` (a backup is saved as `system.reg.bak-wine-for-marmoset-toolbag`): the "open" command of Wine's image classes (`pngfile`, `jpegfile`, `pjpegfile`, `giffile`) and a new class `hostimage` for `.tga .exr .psd .tif .tiff .hdr` run `winebrowser.exe "%1"`. Winebrowser hands the file to Linux (`xdg-open`, through the desktop portal in Flatpak), so it opens in your default app.
- `~/.local/bin/wine-for-marmoset-toolbag`: starts Toolbag with `bottles-cli`, unless it's already running in this bottle. With an NVIDIA driver, it first creates `/dev/nvidia-uvm` if it's missing (the file is gone after a reboot).
- Menu entries that start Toolbag from this bottle get `Exec=` pointing to the launcher (a backup is saved next to them as `*.bak-wine-for-marmoset-toolbag`). If there's none: `~/.local/share/applications/wine-for-marmoset-toolbag.desktop`.
- Toolbag's icon, taken from `toolbag.exe`: `~/.local/share/icons/hicolor/256x256/apps/wine-for-marmoset-toolbag.png`.
- The old values are kept in `.wine-for-marmoset-toolbag.json` in the bottle folder, for the uninstall.

## Tested on

**Software**

| | Version |
|---|---|
| Marmoset Toolbag | 5.03 |
| Bottles | 67.5 (Flatpak, GNOME Platform 50 runtime) |
| Wine runner | soda-11.0-10 (Wine 11.0) |
| Bottle | Application environment, Windows 10, DXVK 3.1.1, VKD3D-Proton 3.0.1, DXVK-NVAPI 0.9.2, discrete GPU on, sync: fsync |
| OS | Rocky Linux 9.8, kernel 5.14.0-687 |
| Desktop | GNOME 40.10 on **X11** (Xorg 1.20.11), xdg-desktop-portal-gnome 41.2 |
| GPU driver | NVIDIA 580.178.04 (open kernel module) |

**Hardware**

| | |
|---|---|
| CPU | AMD Ryzen 9 5900X (12 cores / 24 threads) |
| RAM | 128 GB |
| GPU | NVIDIA GeForce RTX 3090 |
| Display | 2 × 4K (3840 × 2160) 60 Hz |

Renders use the GPU fully (100% load; a test scene used about 11 of the 24 GB VRAM), so Wine isn't the bottleneck. AMD/Intel GPUs, Wayland (XWayland), KDE and other distros haven't been tested.

## Known limitations

- Only one Toolbag at a time, and only if you start it through the launcher (see *Start Toolbag only once*).
- Toolbag only sees folders that Bottles has access to (use Flatseal to add more).
