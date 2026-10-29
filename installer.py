#!/usr/bin/python3
# Wine for Marmoset Toolbag - fixes for Marmoset Toolbag in Bottles.
#
#   1. Rendered/opened images (.png .jpg .tga .exr .psd .tif .hdr) open in the Linux image viewer
#      instead of Wine's Internet Explorer (or nothing).
#   2. Menu entry with Toolbag's own icon.
#   3. Only one Toolbag at a time (a second launch would freeze Bottles).
#   4. Checks the bottle settings Toolbag needs (DXVK, VKD3D-Proton for DirectX 12, NVAPI).
#
# Run it again after a Bottles update: Bottles sometimes resets the bottle's file associations.
# Undo: sh install.sh --uninstall

import argparse, json, os, re, shutil, struct, subprocess, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = '.wine-for-marmoset-toolbag.json'
TAG = 'wine-for-marmoset-toolbag'
APP_NAME = 'Marmoset Toolbag'
EXE = 'toolbag.exe'
DATA = os.path.expanduser(os.environ.get('XDG_DATA_HOME', '~/.local/share'))
ASSUME_YES = False

OPEN_CMD = '"C:\\windows\\system32\\winebrowser.exe" "%1"'
# Wine's own image classes: their "open" points to Internet Explorer
IMAGE_CLASSES = ('pngfile', 'jpegfile', 'pjpegfile', 'giffile')
# extensions Wine knows nothing about: they get the class "hostimage"
HOST_EXTS = ('.tga', '.exr', '.psd', '.tif', '.tiff', '.hdr')


def say(msg=''):
    print(msg, flush=True)


def ok(msg):
    say('  [ok] ' + msg)


def warn(msg):
    say('  [!]  ' + msg)


def die(msg):
    say('\nERROR: ' + msg)
    sys.exit(1)


def ask(question, default=False):
    if ASSUME_YES:
        return True
    hint = '[Y/n]' if default else '[y/N]'
    ans = input(f'{question} {hint} ').strip().lower()
    return default if not ans else ans in ('y', 'yes', 'i', 'igen')


# ---- Bottles ----------------------------------------------------------------

def find_bottles_root():
    for p in ('~/.var/app/com.usebottles.bottles/data/bottles', '~/.local/share/bottles'):
        p = os.path.expanduser(p)
        if os.path.isdir(os.path.join(p, 'bottles')):
            return p
    die('Bottles was not found (neither Flatpak nor native).')


def find_exe(bdir):
    """Unix path of toolbag.exe in the bottle, or None."""
    for pf in ('Program Files', 'Program Files (x86)'):
        base = os.path.join(bdir, 'drive_c', pf)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, files in os.walk(base):
            if dirpath[len(base):].count(os.sep) >= 3:
                dirs[:] = []
            for f in files:
                if f.lower() == EXE:
                    return os.path.join(dirpath, f)
    return None


def find_app_bottles(root):
    bdir = os.path.join(root, 'bottles')
    return [n for n in sorted(os.listdir(bdir)) if find_exe(os.path.join(bdir, n))]


def find_program(yml):
    """Name of the Toolbag program entry in bottle.yml."""
    text = open(yml, encoding='utf-8').read()
    for block in re.split(r'\n    [0-9a-f-]{36}:\n', text):
        if re.search(r'executable: .*\b%s\s*$' % re.escape(EXE), block, re.I | re.M):
            m = re.search(r'^        name: (.+)$', block, re.M)
            if m:
                return m.group(1).strip().strip("'\"")
    return None


def bottle_param(yml, key):
    m = re.search(r'^Parameters:\n((?:  .*\n)+)', open(yml, encoding='utf-8').read(), re.M)
    if m:
        v = re.search(r'^    %s: (.*)$' % re.escape(key), m.group(1), re.M)
        if v:
            return v.group(1).strip().strip("'\"")
    return None


def bottle_running(bdir):
    """True if any Wine process of this bottle is alive (it would overwrite the registry on exit)."""
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            env = open(f'/proc/{pid}/environ', 'rb').read().split(b'\0')
        except OSError:
            continue
        if ('WINEPREFIX=' + bdir).encode() in env:
            comm = open(f'/proc/{pid}/comm').read().strip()
            if comm == 'wineserver' or comm.lower().endswith('.exe'):
                return True
    return False


# ---- registry (Wine .reg text) -------------------------------------------------

def reg_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _section(text, key):
    m = re.search(r'^\[' + re.escape(key) + r'\][^\n]*\n', text, re.M | re.I)
    if not m:
        return None
    end = text.find('\n\n', m.end())
    return m.end(), (len(text) if end < 0 else end + 1)


def reg_get(text, key, name=None):
    """Raw value (as written in the file) or None."""
    s = _section(text, key)
    if not s:
        return None
    lhs = '@' if name is None else '"%s"' % name
    m = re.search('^' + re.escape(lhs) + '=(.*)$', text[s[0]:s[1]], re.M | re.I)
    return m.group(1) if m else None


def reg_set(text, key, value, name=None):
    """value: raw (e.g. reg_str(...)); None deletes the value."""
    lhs = '@' if name is None else '"%s"' % name
    s = _section(text, key)
    if not s:
        if value is None:
            return text
        return text.rstrip('\n') + f'\n\n[{key}] {int(time.time())}\n{lhs}={value}\n'
    a, b = s
    body = text[a:b]
    pat = re.compile('^' + re.escape(lhs) + '=.*\n', re.M | re.I)
    if value is None:
        body = pat.sub('', body, 1)
    elif pat.search(body):
        body = pat.sub(lambda _: f'{lhs}={value}\n', body, 1)
    else:
        body += f'{lhs}={value}\n'
    return text[:a] + body + text[b:]


def cls_key(c):
    return 'Software\\\\Classes\\\\' + c


def open_key(c):
    return cls_key(c) + '\\\\shell\\\\open\\\\command'


def image_changes():
    """(key, name, new raw value) for fix 1."""
    out = [(open_key(c), None, reg_str(OPEN_CMD)) for c in IMAGE_CLASSES]
    out.append((open_key('hostimage'), None, reg_str(OPEN_CMD)))
    out += [(cls_key(e), None, reg_str('hostimage')) for e in HOST_EXTS]
    return out


# ---- icon from the .exe ----------------------------------------------------------

def exe_icon_png(path):
    """Largest icon of a Windows .exe as PNG bytes (or None)."""
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    opt = pe + 24
    magic = struct.unpack_from('<H', d, opt)[0]
    rsrc_rva = struct.unpack_from('<I', d, opt + (112 if magic == 0x20b else 96) + 2 * 8)[0]
    sec = opt + struct.unpack_from('<H', d, pe + 20)[0]
    for i in range(nsec):
        va, size, raw = struct.unpack_from('<III', d, sec + i * 40 + 12)
        if va <= rsrc_rva < va + max(size, 1):
            base, delta = raw + rsrc_rva - va, va - raw
            break
    else:
        return None

    def entries(off):
        named, ids = struct.unpack_from('<HH', d, base + off + 12)
        for j in range(named + ids):
            name, child = struct.unpack_from('<II', d, base + off + 16 + j * 8)
            yield name, child

    def leaf(child):
        while child & 0x80000000:          # descend to the first language
            child = next(entries(child & 0x7fffffff))[1]
        rva, size = struct.unpack_from('<II', d, base + child)
        return d[rva - delta:rva - delta + size]

    types = dict(entries(0))
    if 14 not in types or 3 not in types:
        return None
    icons = {n: c for n, c in entries(types[3] & 0x7fffffff)}
    group = leaf(next(entries(types[14] & 0x7fffffff))[1])
    best = None
    for j in range(struct.unpack_from('<H', group, 4)[0]):
        w, h, _, _, _, bpp, size, nid = struct.unpack_from('<BBBBHHIH', group, 6 + j * 14)
        key = ((w or 256), bpp)
        if nid in icons and (best is None or key > best[0]):
            best = (key, nid)
    if not best:
        return None
    img = leaf(icons[best[1]])
    if img[:4] == b'\x89PNG':
        return img
    w = best[0][0]
    if struct.unpack_from('<H', img, 14)[0] != 32:
        return None
    px = img[struct.unpack_from('<I', img, 0)[0]:]
    rows = []
    for y in range(w):
        src = px[(w - 1 - y) * w * 4:(w - y) * w * 4]
        row = bytearray(src)
        row[0::4], row[2::4] = src[2::4], src[0::4]
        rows.append(b'\0' + bytes(row))
    chunk = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, w, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b''))


def png_size(png):
    return struct.unpack_from('>I', png, 16)[0]


# ---- menu entry + launcher ---------------------------------------------------------

def menu_entries(bottle, program):
    """Existing .desktop files (yours or Bottles') that start this program from this bottle."""
    apps = os.path.join(DATA, 'applications')
    found = []
    if not os.path.isdir(apps):
        return found
    for f in sorted(os.listdir(apps)):
        p = os.path.join(apps, f)
        if not f.endswith('.desktop') or f == TAG + '.desktop' or not os.path.isfile(p):
            continue
        m = re.search(r'^Exec=(.*)$', open(p, encoding='utf-8', errors='replace').read(), re.M)
        if not m:
            continue
        ex = m.group(1)
        if (re.search(r'(-b|--bottle)\s+["\']?%s["\']?(\s|$)' % re.escape(bottle), ex) and
                re.search(r'(-p|--program)\s+["\']?%s["\']?(\s|$)' % re.escape(program), ex)) or \
                ex.strip() == os.path.expanduser('~/.local/bin/' + TAG):
            found.append(p)
    return found


def install_launcher(root, bottle, bdir, program, exe, state):
    flatpak = '/.var/app/com.usebottles.bottles/' in root
    cli = 'flatpak run --command=bottles-cli com.usebottles.bottles' if flatpak else 'bottles-cli'

    png = exe_icon_png(exe)
    icon = TAG
    if png:
        size = png_size(png)
        d = os.path.join(DATA, 'icons', 'hicolor', f'{size}x{size}', 'apps')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, TAG + '.png'), 'wb').write(png)
        subprocess.run(['gtk-update-icon-cache', '-f', '-t', os.path.join(DATA, 'icons', 'hicolor')],
                       capture_output=True)
    else:
        icon = 'applications-graphics'

    launcher = os.path.expanduser('~/.local/bin/' + TAG)
    os.makedirs(os.path.dirname(launcher), exist_ok=True)
    script = open(os.path.join(HERE, 'files', 'launch.sh')).read()
    for key, value in (('CLI', cli), ('BOTTLE', bottle), ('PROGRAM', program), ('PREFIX', bdir),
                       ('EXE', os.path.basename(exe)), ('NAME', APP_NAME), ('ICON', icon)):
        script = script.replace('@%s@' % key, value.replace("'", "'\\''"))
    with open(launcher, 'w') as f:
        f.write(script)
    os.chmod(launcher, 0o755)

    apps = os.path.join(DATA, 'applications')
    os.makedirs(apps, exist_ok=True)
    own = os.path.join(apps, TAG + '.desktop')
    existing = menu_entries(bottle, program)
    if existing:
        # keep the user's entry (and its place in the dock), only route it through the launcher
        for p in existing:
            text = open(p, encoding='utf-8').read()
            if not os.path.exists(p + '.bak-' + TAG):
                shutil.copy2(p, p + '.bak-' + TAG)
            state.setdefault('menu', [])
            if p not in state['menu']:
                state['menu'].append(p)
            text = re.sub(r'^Exec=.*$', 'Exec=' + launcher, text, count=1, flags=re.M)
            open(p, 'w', encoding='utf-8').write(text)
            ok('menu entry %s now starts Toolbag through the launcher' % os.path.basename(p))
        if os.path.exists(own):
            os.unlink(own)
    else:
        with open(own, 'w') as f:
            f.write('[Desktop Entry]\nType=Application\nName=Marmoset Toolbag\n'
                    f'Comment=Marmoset Toolbag ({bottle} bottle)\nExec={launcher}\n'
                    f'Icon={icon}\nCategories=Graphics;3DGraphics;\nStartupNotify=true\n'
                    'StartupWMClass=steam_proton\n')
        ok('menu entry "Marmoset Toolbag" created (with Toolbag\'s own icon)')
    subprocess.run(['update-desktop-database', apps], capture_output=True)
    ok('a second Toolbag can\'t be started by accident (you get a notification instead)')


def uninstall_launcher(state):
    for p in state.get('menu', []):
        if os.path.exists(p + '.bak-' + TAG):
            shutil.move(p + '.bak-' + TAG, p)
            ok('menu entry %s restored' % os.path.basename(p))
    for p in (os.path.join(DATA, 'applications', TAG + '.desktop'), os.path.expanduser('~/.local/bin/' + TAG)):
        if os.path.exists(p):
            os.unlink(p)
    for d in os.listdir(os.path.join(DATA, 'icons', 'hicolor')) if os.path.isdir(os.path.join(DATA, 'icons', 'hicolor')) else ():
        p = os.path.join(DATA, 'icons', 'hicolor', d, 'apps', TAG + '.png')
        if os.path.exists(p):
            os.unlink(p)
    subprocess.run(['update-desktop-database', os.path.join(DATA, 'applications')], capture_output=True)
    ok('launcher and icon removed')


# ---- install / uninstall -------------------------------------------------------------

def install(root, bottle):
    bdir = os.path.join(root, 'bottles', bottle)
    yml = os.path.join(bdir, 'bottle.yml')
    state_path = os.path.join(bdir, STATE)
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    exe = find_exe(bdir)
    program = find_program(yml)

    say('\n1. Images open in your Linux image viewer')
    system_reg = os.path.join(bdir, 'system.reg')
    text = open(system_reg, encoding='utf-8', errors='surrogateescape').read()
    if not os.path.exists(system_reg + '.bak-' + TAG):
        shutil.copy2(system_reg, system_reg + '.bak-' + TAG)
    old = state.setdefault('registry', {})
    changed = 0
    for key, name, value in image_changes():
        cur = reg_get(text, key, name)
        if cur != value:
            old.setdefault(key, cur)
            text = reg_set(text, key, value, name)
            changed += 1
    open(system_reg, 'w', encoding='utf-8', errors='surrogateescape').write(text)
    ok(('set: ' if changed else 'already set: ') + '.png .jpg .gif ' + ' '.join(HOST_EXTS) +
       ' -> Linux default app')

    say('\n2-3. Menu entry, icon, only one Toolbag at a time')
    if not program:
        warn('Toolbag is not added as a program in this bottle, skipped.')
        warn('In Bottles: open the bottle -> Programs -> "..." -> Add program -> toolbag.exe, then run this again.')
    else:
        install_launcher(root, bottle, bdir, program, exe, state)

    say('\n4. Bottle settings')
    for key, label, why in (('dxvk', 'DXVK', 'DirectX 11'),
                            ('vkd3d', 'VKD3D-Proton', 'DirectX 12, Toolbag 5\'s renderer'),
                            ('dxvk_nvapi', 'DXVK-NVAPI', 'NVIDIA features (DLSS, RTX); NVIDIA only')):
        if bottle_param(yml, key) == 'true':
            ok(f'{label} is on')
        else:
            warn(f'{label} is off ({why}). In Bottles: bottle -> Settings -> Display/Components -> turn it on.')

    json.dump(state, open(state_path, 'w'), indent=1)
    say('\nDone. Start Toolbag from the menu or the dock.')
    say('After a Bottles update, run this script again if images stop opening.')


def uninstall(root, bottle):
    bdir = os.path.join(root, 'bottles', bottle)
    state_path = os.path.join(bdir, STATE)
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    system_reg = os.path.join(bdir, 'system.reg')
    text = open(system_reg, encoding='utf-8', errors='surrogateescape').read()
    for key, value in state.get('registry', {}).items():
        text = reg_set(text, key, value)
    open(system_reg, 'w', encoding='utf-8', errors='surrogateescape').write(text)
    ok('image file associations restored')
    uninstall_launcher(state)
    if os.path.exists(state_path):
        os.unlink(state_path)
    say('\nDone.')


def main():
    global ASSUME_YES
    ap = argparse.ArgumentParser(description='Wine for Marmoset Toolbag fixes for Bottles')
    ap.add_argument('--bottle', help='bottle name (default: the one with toolbag.exe)')
    ap.add_argument('--uninstall', action='store_true')
    ap.add_argument('--yes', action='store_true', help='answer yes to questions')
    a = ap.parse_args()
    ASSUME_YES = a.yes

    say('Wine for Marmoset Toolbag')
    root = find_bottles_root()
    bottle = a.bottle
    if not bottle:
        found = find_app_bottles(root)
        if not found:
            die('no bottle with toolbag.exe found. Install Toolbag in a Bottles bottle first, or use --bottle NAME.')
        if len(found) > 1:
            die('several Toolbag bottles found: %s. Choose one with --bottle NAME.' % ', '.join(found))
        bottle = found[0]
    bdir = os.path.join(root, 'bottles', bottle)
    if not os.path.isfile(os.path.join(bdir, 'bottle.yml')):
        die(f'bottle "{bottle}" not found in {root}/bottles')
    if not a.uninstall and not find_exe(bdir):
        die(f'toolbag.exe was not found in bottle "{bottle}".')
    say(f'Bottle: {bottle}  ({root})')
    if bottle_running(bdir):
        die('Toolbag (or something else in this bottle) is running. Close it and run this again.')
    if not a.uninstall and not ask('Apply the fixes to this bottle?', True):
        say('Nothing was changed.')
        return
    (uninstall if a.uninstall else install)(root, bottle)


if __name__ == '__main__':
    main()
