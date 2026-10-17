"""Install the combined Yazi configuration and launcher (Windows / Linux)."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
START = '# >>> Yazi Setup keybindings >>>'
END = '# <<< Yazi Setup keybindings <<<'
OLD_START = '# >>> Yazi Windows Scripts keybindings >>>'
OLD_END = '# <<< Yazi Windows Scripts keybindings <<<'
WINDOWS_PACKAGES = {
    'yazi': 'sxyazi.yazi', '7z': '7zip.7zip', 'git': 'Git.Git',
    'wt': 'Microsoft.WindowsTerminal', 'ffmpeg': 'Gyan.FFmpeg',
    'jq': 'jqlang.jq', 'pdftoppm': 'oschwartz10612.Poppler',
    'fd': 'sharkdp.fd', 'rg': 'BurntSushi.ripgrep.MSVC',
    'fzf': 'junegunn.fzf', 'zoxide': 'ajeetdsouza.zoxide',
    'magick': 'ImageMagick.ImageMagick',
}
LINUX_PACKAGES = {
    'apt-get': ['file', '7zip', 'unzip', 'zip', 'ffmpeg', 'jq', 'poppler-utils',
                'fd-find', 'ripgrep', 'fzf', 'zoxide', 'imagemagick', 'xdg-utils', 'xclip', 'wl-clipboard'],
    'dnf': ['file', '7zip', 'unzip', 'zip', 'ffmpeg-free', 'jq', 'poppler-utils',
            'fd-find', 'ripgrep', 'fzf', 'zoxide', 'ImageMagick', 'xdg-utils', 'xclip', 'wl-clipboard'],
    'pacman': ['file', '7zip', 'unzip', 'zip', 'ffmpeg', 'jq', 'poppler',
               'fd', 'ripgrep', 'fzf', 'zoxide', 'imagemagick', 'resvg', 'xdg-utils', 'xclip', 'wl-clipboard'],
}


def yazi_is_current():
    if not shutil.which('yazi'):
        return False
    result = subprocess.run(['yazi', '--version'], capture_output=True, text=True)
    version = re.search(r'(?:Version:\s*|yazi\s+)(\d+)\.(\d+)\.(\d+)', result.stdout, re.I)
    return bool(version and tuple(map(int, version.groups())) >= (26, 9, 1))


def merge_keymap(existing, snippet):
    """Replace only complete managed blocks; leave user configuration intact."""
    for start, end in [(START, END), (OLD_START, OLD_END)]:
        if existing.count(start) != existing.count(end) or existing.count(start) > 1:
            raise ValueError('Incomplete/duplicate managed keymap block; repair keymap.toml first')
        if start in existing:
            if existing.index(start) > existing.index(end):
                raise ValueError('Managed keymap markers are out of order')
            existing = re.sub(re.escape(start) + r'.*?' + re.escape(end), '',
                              existing, flags=re.S)
    return snippet.strip() + '\n\n' + existing.lstrip('\r\n')


def binding(keys, command, description):
    # JSON basic string quoting is compatible with these TOML strings.
    return ('[[mgr.prepend_keymap]]\non = ' + json.dumps(keys) + '\nrun = '
            + json.dumps(command) + '\ndesc = ' + json.dumps(description) + '\n')


def keymap(windows, config):
    items = [
        (['g', 'd'], 'cd ~/Downloads', 'Go to Downloads'),
        (['g', 'z'], 'cd ~/Documents', 'Go to Documents'),
        (['R'], 'rename --empty=stem --cursor=start', 'Rename filename, keeping extension'),
        (['u', 'z'], 'plugin setup-archive extract', 'Extract hovered ZIP into new folder'),
        (['c', 'z'], 'plugin setup-archive zip', 'ZIP selected files (or hovered file)'),
    ]
    # Yazi command parsing needs doubled backslashes inside double quotes.
    config_arg = str(config).replace('\\', '\\\\').replace('"', '\\"')
    items.append((['g', 's'], f'cd "{config_arg}"', 'Go to Yazi settings'))
    if windows:
        items += [(['g', 'p'], 'cd ~/Scripts', 'Go to helper scripts'),
                  (['c', 'a'], 'plugin setup-archive clipboard', 'Copy hovered file to Windows clipboard'),
                  (['u', 'o'], 'shell -- explorer .', 'Open directory in Explorer')]
        for key, ext in [('x', 'xlsx'), ('w', 'docx'), ('p', 'pptx')]:
            items.append((['n', key], 'shell --block -- powershell.exe -NoProfile '
                          '-ExecutionPolicy Bypass -File "%USERPROFILE%\\Scripts\\new-office-file.ps1" '
                          f'-Type {ext}', f'Create {ext} from Office template'))
    else:
        items.append((['u', 'o'], 'shell -- xdg-open .', 'Open directory in desktop file manager'))
    return START + '\n' + '\n'.join(binding(*item) for item in items) + END + '\n'


class Installer:
    def __init__(self, args):
        self.args = args
        self.windows = sys.platform == 'win32'
        self.home = Path.home()
        self.config = Path(os.environ.get('YAZI_CONFIG_HOME') or (
            str(Path(os.environ['APPDATA']) / 'yazi/config') if self.windows else
            str(Path(os.environ.get('XDG_CONFIG_HOME', self.home / '.config')) / 'yazi')))

    def run(self, command, input_data=None):
        print('Run: ' + subprocess.list2cmdline(list(map(str, command))), flush=True)
        if not self.args.dry_run:
            subprocess.run(list(map(str, command)), check=True, input=input_data,
                           stdout=subprocess.DEVNULL if input_data is not None else None)

    def write(self, path, content, executable=False):
        path = Path(path)
        print(f'Write: {path}')
        if self.args.dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content.encode('utf-8'):
            backup = path.with_name(path.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            shutil.copy2(path, backup)
        path.write_text(content, encoding='utf-8', newline='\n')
        if executable:
            path.chmod(0o755)

    def dependencies(self):
        if self.windows:
            packages = dict(WINDOWS_PACKAGES) if self.args.install_dependencies else {}
            if self.args.install_yazi:
                packages['yazi'] = WINDOWS_PACKAGES['yazi']
            if packages and not shutil.which('winget'):
                raise RuntimeError('Install Microsoft App Installer (winget) to install dependencies')
            for command, package in packages.items():
                present = shutil.which(command)
                upgrade = command == 'yazi' and present and not yazi_is_current()
                if not present or upgrade:
                    self.run(['winget', 'upgrade' if upgrade else 'install', '--id', package, '-e', '--source', 'winget',
                              '--accept-source-agreements', '--accept-package-agreements'])
            if packages and not self.args.dry_run:
                import winreg
                for hive, key in [(winreg.HKEY_CURRENT_USER, 'Environment'),
                                  (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')]:
                    with winreg.OpenKey(hive, key) as env_key:
                        value, _ = winreg.QueryValueEx(env_key, 'Path')
                        os.environ['PATH'] += ';' + os.path.expandvars(value)
            return
        manager = next((p for p in LINUX_PACKAGES if shutil.which(p)), None)
        if (self.args.install_dependencies or self.args.install_yazi) and not manager:
            raise RuntimeError('Automatic packages support apt-get, dnf and pacman. Install manually, then rerun without install flags.')
        prefix = [] if os.geteuid() == 0 else ['sudo']
        if manager == 'apt-get':
            install = prefix + ['apt-get', 'install', '-y']
        elif manager == 'dnf':
            install = prefix + ['dnf', 'install', '-y']
        else:
            install = prefix + ['pacman', '-S', '--needed', '--noconfirm']
        if manager == 'apt-get' and (self.args.install_dependencies or self.args.install_yazi):
            self.run(prefix + ['apt-get', 'update'])
        if self.args.install_dependencies:
            packages = list(LINUX_PACKAGES[manager])
            # Older Debian/Ubuntu repositories call their 7-Zip package p7zip-full.
            if manager == 'apt-get' and not self.args.dry_run:
                probe = subprocess.run(['apt-cache', 'show', '7zip'], capture_output=True)
                if probe.returncode:
                    packages[packages.index('7zip')] = 'p7zip-full'
            self.run(install + packages)
        if self.args.install_yazi and not yazi_is_current():
            if manager == 'apt-get':
                print('Configure the official Yazi stable APT repository (amd64/arm64).')
                key_url = 'https://yazi-rs.github.io/builds/yazi-keyring.gpg'
                key = b''
                if not self.args.dry_run:
                    with urlopen(key_url, timeout=60) as response:
                        key = response.read()
                self.run(prefix + ['mkdir', '-p', '/usr/share/keyrings'], input_data=None)
                self.run(prefix + ['tee', '/usr/share/keyrings/yazi-keyring.gpg'], input_data=key)
                repo = b'deb [signed-by=/usr/share/keyrings/yazi-keyring.gpg] https://yazi-rs.github.io/builds/ stable main\n'
                self.run(prefix + ['tee', '/etc/apt/sources.list.d/yazi.list'], input_data=repo)
                self.run(prefix + ['apt-get', 'update'])
                self.run(install + ['yazi'])
            else:
                self.run(install + ['yazi'])

    def windows_environment(self):
        sevenzip = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / '7-Zip'
        git_file = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/usr/bin/file.exe'
        # Persist only the values managed here; retain the user's other PATH entries.
        import winreg
        access = winreg.KEY_READ if self.args.dry_run else winreg.KEY_READ | winreg.KEY_WRITE
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, access) as env_key:
            if (sevenzip / '7z.exe').exists() and not shutil.which('7z'):
                try:
                    current, _ = winreg.QueryValueEx(env_key, 'Path')
                except FileNotFoundError:
                    current = ''
                if str(sevenzip).lower() not in [p.lower().rstrip('\\') for p in current.split(';')]:
                    print(f'Add to user PATH: {sevenzip}')
                    if not self.args.dry_run:
                        winreg.SetValueEx(env_key, 'Path', 0, winreg.REG_EXPAND_SZ,
                                          current.rstrip(';') + ';' + str(sevenzip))
                if not self.args.dry_run:
                    os.environ['PATH'] += ';' + str(sevenzip)
            if git_file.exists() and not os.environ.get('YAZI_FILE_ONE'):
                print(f'Set YAZI_FILE_ONE: {git_file}')
                if not self.args.dry_run:
                    winreg.SetValueEx(env_key, 'YAZI_FILE_ONE', 0, winreg.REG_SZ, str(git_file))
                    os.environ['YAZI_FILE_ONE'] = str(git_file)

    def configure(self):
        plugin = self.config / 'plugins/setup-archive.yazi'
        script = plugin / 'yazi_archive.py'
        self.write(script, (ROOT / 'scripts/yazi_archive.py').read_text(encoding='utf-8'))
        runtime = ('{ python = ' + json.dumps(sys.executable, ensure_ascii=False)
                   + ', script = ' + json.dumps(str(script), ensure_ascii=False)
                   + ', clipboard = ' + json.dumps(str(self.home / 'Scripts/yazi-copy-actual-file.ps1'), ensure_ascii=False) + ' }')
        self.write(plugin / 'main.lua', (ROOT / 'yazi-config/plugins/setup-archive.yazi/main.lua').read_text().replace('__RUNTIME__', runtime))
        if not self.args.skip_keymap:
            path = self.config / 'keymap.toml'
            existing = path.read_text(encoding='utf-8-sig') if path.exists() else ''
            self.write(path, merge_keymap(existing, keymap(self.windows, self.config)))
        if self.windows:
            for source in (ROOT / 'scripts').glob('*.ps1'):
                self.write(self.home / 'Scripts' / source.name, source.read_text(encoding='utf-8-sig'))
            readme = self.home / 'User-Templates/README.txt'
            if not readme.exists():
                self.write(readme, (ROOT / 'templates/README.txt').read_text())
        else:
            # Debian's fd-find installs fdfind, while Yazi invokes fd.
            if not shutil.which('fd') and shutil.which('fdfind'):
                self.write(self.home / '.local/bin/fd', '#!/bin/sh\nexec ' + shlex.quote(shutil.which('fdfind')) + ' "$@"\n', True)

    def launcher(self):
        if self.args.skip_launcher:
            return
        if self.windows:
            self.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                      '-File', ROOT / 'launcher/windows/setup.ps1', '-NoLaunch'])
        else:
            executable = shutil.which('yazi') or str(self.home / '.cargo/bin/yazi')
            launcher = self.home / '.local/bin/yazi-launcher'
            self.write(launcher, '#!/bin/sh\nexport PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"\nexec '
                       + shlex.quote(executable) + ' "$@"\n', True)
            data = Path(os.environ.get('XDG_DATA_HOME', self.home / '.local/share'))
            # Desktop Exec is not a shell: quote according to the desktop entry spec.
            escaped = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
            self.write(data / 'applications/yazi-launcher.desktop',
                       '[Desktop Entry]\nType=Application\nName=Yazi Launcher\n'
                       f'Exec="{escaped}"\nTerminal=true\nIcon=system-file-manager\n'
                       'Categories=System;FileTools;FileManager;\n')

    def status(self):
        commands = list(WINDOWS_PACKAGES) + ['ya', 'resvg'] if self.windows else ['yazi', 'ya', 'file', '7z', 'ffmpeg', 'jq', 'pdftoppm', 'fd', 'rg', 'fzf', 'zoxide', 'magick', 'resvg']
        print('\nDependency status (new installations may require a fresh terminal):')
        for command in commands:
            found = shutil.which(command)
            if command == '7z':
                found = found or shutil.which('7zz')
            print(f'  {command}: {found or "missing"}')
        print(f'\nConfiguration: {self.config}')
        print('ZIP creation/extraction uses the Python standard library; no pip packages needed.')
        if not yazi_is_current():
            print('WARNING: Yazi 26.9.1+ is required for these bindings. Rerun with --install-yazi or upgrade it manually.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-yazi', action='store_true')
    parser.add_argument('--install-dependencies', action='store_true')
    parser.add_argument('--skip-keymap', action='store_true')
    parser.add_argument('--skip-launcher', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ is required')
    if sys.platform not in ('win32', 'linux'):
        parser.error('Supported platforms: Windows and Linux')
    try:
        installer = Installer(args)
        installer.dependencies()
        if installer.windows:
            installer.windows_environment()
        installer.configure()
        installer.launcher()
        installer.status()
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Setup failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
