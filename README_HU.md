# Wine for Marmoset Toolbag

Javítások ahhoz, hogy a **Marmoset Toolbag** Linuxon, **Bottles**-ben rendesen működjön. Telepítsd a Toolbaget egy bottle-be, futtass le egy szkriptet, és kész.

> **Ezt a saját gépemre készítettem, és úgy osztom meg, ahogy van. Támogatást nem adok hozzá, kérlek, ne keress meg vele.** Ha nálad nem működik, a `sh install.sh --uninstall` mindent visszaállít. Csak saját felelősségre használd.
>
> Vibe coding, [Claude](https://claude.com/claude-code)-dal (Claude Code) készült.

| # | Probléma | Megoldás |
|---|----------|----------|
| 1 | Ha a Toolbagből megnyitsz egy képet (pl. egy kész renderet), nem történik semmi, vagy a Wine Internet Explorere jön fel | A képek (.png .jpg .gif .tga .exr .psd .tif .hdr) a Linuxos képnézegetődben nyílnak meg |
| 2 | Nincs menüpont, vagy általános ikonja van | Menüpont a Toolbag saját ikonjával. Ha már van menüpontod, az marad, csak az indítón keresztül indul |
| 3 | Ha másodszor is elindítod a Toolbaget, a Bottles lefagy | Egyszerre csak egy Toolbag: a második indítás csak értesítést ad |
| 4 | A Toolbag 5-nek DirectX 12 kell | Ellenőrzi, hogy a DXVK, a VKD3D-Proton és a DXVK-NVAPI be van-e kapcsolva a bottle-ben |

## Ami kell hozzá

- [Bottles](https://usebottles.com) (Flatpak vagy natív)
- Egy bottle-be telepített Marmoset Toolbag (kipróbálva: Toolbag 5.03), programként felvéve a Bottlesben
- X11 asztal vagy XWayland. Kipróbálva: Rocky Linux 9, GNOME, X11.

**Tipp a Toolbag telepítőjéhez:** a Bottles (Flatpak) nem látja a Letöltések mappát. A telepítőt tedd olyan meghajtóra vagy mappába, amit a Bottles lát, vagy másold a bottle `drive_c` mappájába.

A Toolbag telepítője a végén újraindítást kér egy videókártya-időtúllépési (TDR) beállítás miatt. Wine alatt ez a beállítás nem csinál semmit, semmit nem kell újraindítani.

## Telepítés

1. Zárd be a Toolbaget.
2. Futtasd:
   ```sh
   sh install.sh
   ```
   Magától megkeresi azt a bottle-t, amelyikben a `toolbag.exe` van. Ha több ilyen van: `sh install.sh --bottle NÉV`.
3. Indítsd a Toolbaget a menüből vagy a dokkról.

**Bottles-frissítés után** a Bottles néha visszaállítja a bottle-t, és a képek megint nem nyílnak meg. Ilyenkor csak futtasd újra a szkriptet (`sh install.sh --bottle NÉV --yes`). Akárhányszor lefuttathatod.

### Egyszerre csak egy Toolbag

Ha elindítasz egy második Toolbaget, miközben egy már fut, a Bottles lefagy. A Bottles (Flatpak) minden indítást külön dobozban futtat, és a kettő összeakad. Az indító (`~/.local/bin/wine-for-marmoset-toolbag`) ezt megakadályozza: ha a Toolbag már fut vagy éppen indul, csak egy értesítést kapsz.

A szkript megkeresi azokat a menübejegyzéseket (`.desktop` fájlok a `~/.local/share/applications` mappában), amelyek ebből a bottle-ből indítják a Toolbaget, és átirányítja őket az indítóra, így a dokkon lévő ikonod is így működik. Ha nincs ilyen, létrehoz egy „Marmoset Toolbag” menüpontot.

Indítás előtt az indító bezárja ugyanennek a bottle-nek az esetleg bent maradt, halott Bottles dobozát is: amikor a Wine szolgáltatásai (services.exe, winedevice.exe …) még futnak, de a wineserver már nem. Enélkül a következő indítás ablak nélkül beragadhat. Olyan dobozt soha nem zár be, amiben még fut a wineserver, egy program vagy a Bottles ablaka.

Ha a Bottles ablakában a ▶ gombbal indítod a Toolbaget, az nincs védve.

Az értesítés sürgős, így a GNOME a teljes képernyős ablakok fölött is megmutatja. Addig marad kint, amíg be nem zárod.

## Ezeket magadnak kell beállítani

### Felületméret (HiDPI / 4K)

A Toolbag jól működik a Wine saját méretezésével: a Bottlesben nyisd meg a bottle-t → **Settings → Display → DPI**. A 144 150%, a 192 200%. Utána indítsd újra a Toolbaget.

### Render kimeneti mappa

A Toolbag alapból a bottle saját Asztal mappájába menti a rendereket (`drive_c/users/FELHASZNÁLÓ/Desktop`), ami a bottle-ön belül rejtve van. A render beállításaiban állíts be olyan kimeneti mappát, amit Linuxról is látsz.

### Nézetablak sebessége

Ha a sugárkövetéses nézetablak lassú, a Toolbag beállításaiban emeld meg a ray tracing memóriakeretét.

## Eltávolítás

```sh
sh install.sh --uninstall
```

Visszaállítja a képek régi társításait és a menübejegyzéseidet, és törli az indítót és az ikont.

## Mit változtat

- A bottle `system.reg` fájljában (mentés: `system.reg.bak-wine-for-marmoset-toolbag`): a Wine képosztályainak (`pngfile`, `jpegfile`, `pjpegfile`, `giffile`) megnyitó parancsa, valamint egy új `hostimage` osztály a `.tga .exr .psd .tif .tiff .hdr` fájloknak a `winebrowser.exe "%1"` parancsot futtatja. A winebrowser átadja a fájlt a Linuxnak (`xdg-open`, Flatpakban az asztali portálon keresztül), így az alapértelmezett programodban nyílik meg.
- `~/.local/bin/wine-for-marmoset-toolbag`: a `bottles-cli`-vel indítja a Toolbaget, kivéve, ha már fut ebben a bottle-ben.
- Azok a menübejegyzések, amelyek ebből a bottle-ből indítják a Toolbaget, az indítóra mutató `Exec=` sort kapnak (mentés mellettük: `*.bak-wine-for-marmoset-toolbag`). Ha nincs ilyen: `~/.local/share/applications/wine-for-marmoset-toolbag.desktop`.
- A Toolbag ikonja a `toolbag.exe`-ből: `~/.local/share/icons/hicolor/256x256/apps/wine-for-marmoset-toolbag.png`.
- A régi értékek az eltávolításhoz a bottle mappájában, a `.wine-for-marmoset-toolbag.json` fájlban maradnak meg.

## Tesztgép

**Szoftver**

| | Verzió |
|---|---|
| Marmoset Toolbag | 5.03 |
| Bottles | 67.5 (Flatpak, GNOME Platform 50 runtime) |
| Wine runner | soda-11.0-10 (Wine 11.0) |
| Bottle | Application környezet, Windows 10, DXVK 3.1.1, VKD3D-Proton 3.0.1, DXVK-NVAPI 0.9.2, dedikált GPU bekapcsolva, sync: fsync |
| Rendszer | Rocky Linux 9.8, kernel 5.14.0-687 |
| Asztal | GNOME 40.10, **X11** (Xorg 1.20.11), xdg-desktop-portal-gnome 41.2 |
| Videókártya-meghajtó | NVIDIA 580.178.04 (open kernel module) |

**Hardver**

| | |
|---|---|
| Processzor | AMD Ryzen 9 5900X (12 mag / 24 szál) |
| Memória | 128 GB |
| Videókártya | NVIDIA GeForce RTX 3090 |
| Kijelző | 2 × 4K (3840 × 2160), 60 Hz |

Rendereléskor a Toolbag teljesen kihasználja a videókártyát (100%, egy tesztjelenetben ~11 GB VRAM), tehát nem a Wine a szűk keresztmetszet. AMD/Intel videókártyával, Waylanddel (XWayland), KDE-vel és más disztribúciókkal nincs kipróbálva.

## Ismert korlátok

- Egyszerre csak egy Toolbag futhat, és ez csak akkor van védve, ha az indítón keresztül indítod (lásd *Egyszerre csak egy Toolbag*).
- A Toolbag csak azokat a mappákat látja, amelyekhez a Bottlesnek van hozzáférése (továbbiakat a Flatseallel adhatsz hozzá).
