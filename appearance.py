"""User-scoped fonts, preview tools and Yazi flavors for the combined installer."""
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from urllib.request import urlopen
import uuid
import zipfile

FONT_FACE = 'CaskaydiaMono Nerd Font Mono'
FONT_FILE = 'CaskaydiaMonoNerdFontMono-Regular.ttf'
FONT_URL = 'https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/CascadiaMono.tar.xz'
FONT_SHA = '7c22db8c8460ef62abffbb6d5c7b212507de0798a4a762fa2a005a8bc4c90fc6'
MIN_TERMINAL_VERSION = (1, 22, 10352, 0)
RESVG_ASSETS = {
    'windows': ('resvg-win64.zip', 'a15172d72d72e219b896ef5942a48c1a57b7280d63ef8380d95dee8005549922'),
    'linux': ('resvg-linux-x86_64.tar.gz', '3c1d52850a78bc4ed0e9d05605b53ad21bb5313184f14bf72515d29cb98cda10'),
}
THEMES = {
    'tokyo-night': ('BennyOe/tokyo-night.yazi', '8e6296f14daff24151c736ebd0b9b6cd89b02b03',
                    '3e03592ee940ea7f0fabf97fd21505feb0edf4ae52f2747843385f5b98e23d19', ''),
    'catppuccin-mocha': ('yazi-rs/flavors', '1183892c904f7f0efdf4473e856ed308b7bea98d',
                        'a8346b35da3e88c4f8a7e44417696c951322ffd69d90596fcc123481d7669c1b',
                        'catppuccin-mocha.yazi/'),
}


def windows_terminal_version():
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
            'Get-AppxPackage Microsoft.WindowsTerminal | Select-Object -First 1 -ExpandProperty Version'],
            capture_output=True, text=True, timeout=20)
        match = re.search(r'(?m)^\s*(\d+)\.(\d+)\.(\d+)\.(\d+)\s*$', result.stdout)
        return tuple(map(int, match.groups())) if result.returncode == 0 and match else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def verified_download(url, digest):
    """Download data only; never execute a remotely downloaded script."""
    with urlopen(url, timeout=60) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Download integrity check failed: {url}')
    return data


def tar_files(data):
    """Read regular files without extracting archive paths to the filesystem."""
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
        for entry in archive:
            if entry.isfile():
                with archive.extractfile(entry) as stream:
                    yield entry.name, stream.read()


def write_binary(path, data, executable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if executable:
        path.chmod(0o755)


def select_theme(choice, dry_run=False):
    if choice != 'choose':
        return choice
    if dry_run:
        print('Theme selection: keep existing (interactive menu skipped for dry run).')
        return 'keep'
    if not sys.stdin.isatty():
        print('Non-interactive install: keeping the existing theme. Pass --theme to choose explicitly.')
        return 'keep'
    choices = ['keep', 'tokyo-night', 'catppuccin-mocha', 'default']
    print('\nYazi theme: 1) Keep existing  2) Tokyo Night  3) Catppuccin Mocha  4) Default')
    while True:
        try:
            answer = input('Choose [1]: ').strip() or '1'
        except EOFError:
            return 'keep'
        if answer in ('1', '2', '3', '4'):
            return choices[int(answer) - 1]
        print('Enter 1, 2, 3 or 4.')


def theme_text(existing, choice):
    parsed = tomllib.loads(existing)
    pattern = r'(?ms)^\[flavor\][^\n]*\n.*?(?=^\s*\[|\Z)'
    if 'flavor' in parsed and not re.search(pattern, existing):
        raise ValueError('Use a [flavor] table in theme.toml before changing themes.')
    remainder = re.sub(pattern, '', existing).lstrip('\r\n')
    flavor = '' if choice == 'default' else choice
    content = '[flavor]\ndark = ' + json.dumps(flavor) + '\nlight = ' + json.dumps(flavor) + '\n\n' + remainder
    tomllib.loads(content)
    return content


def install_theme(installer, choice):
    if choice == 'keep':
        return
    path = installer.config / 'theme.toml'
    existing = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    content = theme_text(existing, choice)
    if choice in THEMES:
        repo, commit, digest, subfolder = THEMES[choice]
        print(f'Install {choice} flavor from {repo}@{commit}')
        if not installer.args.dry_run:
            data = verified_download(f'https://codeload.github.com/{repo}/tar.gz/{commit}', digest)
            files = {}
            for name, payload in tar_files(data):
                relative = name.split('/', 1)[-1]
                if subfolder and not relative.startswith(subfolder):
                    continue
                relative = relative[len(subfolder):]
                if relative in ('flavor.toml', 'tmtheme.xml', 'LICENSE', 'LICENSE-tmtheme', 'README.md'):
                    files[relative] = payload.decode('utf-8')
            if not {'flavor.toml', 'tmtheme.xml'}.issubset(files):
                raise ValueError('The theme download is missing required flavor files')
            tomllib.loads(files['flavor.toml'])
            for name, payload in files.items():
                installer.write(installer.config / 'flavors' / (choice + '.yazi') / name, payload)
    installer.write(path, content)


def register_windows_font(path):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
        winreg.SetValueEx(key, FONT_FACE + ' (TrueType)', 0, winreg.REG_SZ, str(path))
    gdi = ctypes.windll.gdi32
    gdi.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    if not gdi.AddFontResourceExW(str(path), 0, None):
        raise OSError('Windows could not load the Nerd Font. Sign out and retry setup.')
    # Notify existing applications; new Terminal windows can discover the font.
    ctypes.windll.user32.SendNotifyMessageW(0xffff, 0x001d, 0, 0)


def install_font(installer):
    root = (Path(os.environ['LOCALAPPDATA']) / 'Microsoft/Windows/Fonts'
            if installer.windows else installer.home / '.local/share/fonts/YaziSetup')
    path = root / FONT_FILE
    print(f'Install user font: {FONT_FACE} -> {path}')
    if installer.args.dry_run:
        return FONT_FACE
    if not path.is_file():
        files = dict(tar_files(verified_download(FONT_URL, FONT_SHA)))
        font = next((data for name, data in files.items() if PurePosixPath(name).name == FONT_FILE), None)
        if font is None or font[:4] not in (b'\x00\x01\x00\x00', b'OTTO'):
            raise ValueError('Downloaded archive does not contain the expected Nerd Font')
        for name, data in files.items():
            if PurePosixPath(name).name == 'LICENSE':
                write_binary(root / 'YaziSetup-Font-LICENSE.txt', data)
        write_binary(path, font)
    if installer.windows:
        register_windows_font(path)
    elif shutil.which('fc-cache'):
        installer.run(['fc-cache', '-f', str(root)])
    else:
        raise RuntimeError('Install fontconfig (fc-cache) to register the Nerd Font')
    return FONT_FACE


def terminal_profile(installer, font_face=None):
    if not installer.windows or getattr(installer.args, 'skip_launcher', False):
        return
    path = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/Windows Terminal/Fragments/YaziSetup/yazi.json'
    content = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {'profiles': [{
        'guid': '{' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://yazi-setup.local/terminal-profile')) + '}',
        'name': 'Yazi Setup', 'commandline': 'powershell.exe -NoLogo',
        'startingDirectory': str(installer.home),
    }]}
    if font_face:
        content['profiles'][0]['font'] = {'face': font_face}
    installer.write(path, json.dumps(content, indent=2, ensure_ascii=False) + '\n')


def install_resvg(installer):
    if installer.find_command('resvg'):
        return
    machine = platform.machine().lower()
    if machine not in ('amd64', 'x86_64'):
        raise RuntimeError('SVG preview: install resvg for your CPU using your package manager or cargo install resvg --locked')
    target = (Path(os.environ['LOCALAPPDATA']) / 'YaziSetup/bin/resvg.exe'
              if installer.windows else installer.home / '.local/bin/resvg')
    print(f'Install SVG preview tool: {target}')
    if installer.args.dry_run:
        return
    name, digest = RESVG_ASSETS['windows' if installer.windows else 'linux']
    data = verified_download('https://github.com/linebender/resvg/releases/download/v0.45.1/' + name, digest)
    if installer.windows:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            binary = archive.read('resvg.exe')
    else:
        binary = next((payload for name, payload in tar_files(data) if PurePosixPath(name).name == 'resvg'), None)
        if binary is None:
            raise ValueError('The SVG preview download is missing resvg')
    write_binary(target, binary, executable=not installer.windows)


def configure(installer):
    choice = select_theme(getattr(installer.args, 'theme', 'keep'), installer.args.dry_run)
    install_theme(installer, choice)
    font_face = getattr(installer.args, 'font_face', None)
    linux_settings = installer.config / 'setup-appearance.json'
    if not installer.windows and not font_face and linux_settings.exists():
        font_face = json.loads(linux_settings.read_text(encoding='utf-8')).get('font_face')
    wants_font = (getattr(installer.args, 'install_font', False)
                  or getattr(installer.args, 'install_dependencies', False)) and not getattr(installer.args, 'skip_font', False)
    if wants_font:
        try:
            installed_face = install_font(installer)
            font_face = font_face or installed_face
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            installer.setup_warnings.append(f'Nerd Font setup failed: {exc}')
    terminal_profile(installer, font_face)
    if not installer.windows and font_face:
        installer.write(linux_settings, json.dumps({'font_face': font_face}, indent=2) + '\n')
    if getattr(installer.args, 'install_dependencies', False):
        try:
            install_resvg(installer)
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            installer.setup_warnings.append(f'SVG preview setup failed: {exc}')
    return font_face
