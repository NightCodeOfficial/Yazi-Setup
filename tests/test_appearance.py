import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import appearance
import setup


def archive_bytes(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = argparse.Namespace(dry_run=False, skip_keymap=False,
            skip_launcher=False, install_dependencies=False, install_yazi=False,
            theme='keep', install_font=False, skip_font=False, font_face=None)
        self.installer = setup.Installer(self.args)
        self.installer.home = self.root
        self.installer.config = self.root / 'config'

    def test_download_checksum_is_enforced(self):
        with patch.object(appearance, 'urlopen') as opener:
            opener.return_value.__enter__.return_value.read.return_value = b'payload'
            self.assertEqual(appearance.verified_download('https://example.org', hashlib.sha256(b'payload').hexdigest()), b'payload')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                appearance.verified_download('https://example.org', 'bad')

    def test_theme_changes_preserve_other_customizations_and_create_backup(self):
        path = self.installer.config / 'theme.toml'
        path.parent.mkdir()
        path.write_text('[flavor]\ndark = "old"\nlight = "old"\n\n[mgr]\ncwd = { fg = "red" }\n')
        data = archive_bytes({'repo/flavor.toml': b'[mgr]\ncwd={fg="blue"}',
                              'repo/tmtheme.xml': b'<plist/>', 'repo/LICENSE': b'license'})
        with patch.object(appearance, 'verified_download', return_value=data):
            appearance.install_theme(self.installer, 'tokyo-night')
        parsed = tomllib.loads(path.read_text())
        self.assertEqual(parsed['flavor']['dark'], 'tokyo-night')
        self.assertEqual(parsed['mgr']['cwd']['fg'], 'red')
        self.assertEqual(len(list(path.parent.glob('theme.toml.backup-*'))), 1)
        before = path.read_bytes()
        appearance.install_theme(self.installer, 'keep')
        self.assertEqual(path.read_bytes(), before)
        appearance.install_theme(self.installer, 'default')
        self.assertEqual(tomllib.loads(path.read_text())['flavor']['dark'], '')

    def test_failed_theme_download_does_not_activate_missing_flavor(self):
        path = self.installer.config / 'theme.toml'
        path.parent.mkdir()
        path.write_text('[flavor]\ndark="old"\n')
        with patch.object(appearance, 'verified_download', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                appearance.install_theme(self.installer, 'tokyo-night')
        self.assertEqual(tomllib.loads(path.read_text())['flavor']['dark'], 'old')

    def test_theme_menu_and_dry_run(self):
        with patch('builtins.input', side_effect=['wrong', '2']):
            self.assertEqual(appearance.select_theme('choose'), 'tokyo-night')
        with patch('builtins.input', side_effect=AssertionError('dry run prompted')):
            self.assertEqual(appearance.select_theme('choose', True), 'keep')

    def test_windows_font_and_profile_stay_scoped_to_yazi(self):
        self.installer.windows = True
        payload = archive_bytes({appearance.FONT_FILE: b'\x00\x01\x00\x00fakefont', 'LICENSE': b'license'})
        with patch.dict(os.environ, {'LOCALAPPDATA': str(self.root)}), patch.object(appearance, 'verified_download', return_value=payload), patch.object(appearance, 'register_windows_font') as register:
            face = appearance.install_font(self.installer)
            appearance.terminal_profile(self.installer, face)
            register.assert_called_once()
            path = self.root / 'Microsoft/Windows Terminal/Fragments/YaziSetup/yazi.json'
            profile = json.loads(path.read_text())['profiles'][0]
            self.assertEqual(profile['font']['face'], appearance.FONT_FACE)
            self.assertEqual(profile['name'], 'Yazi Setup')
            self.assertFalse((self.root / 'Microsoft/Windows Terminal/settings.json').exists())
            with patch.object(appearance, 'verified_download', side_effect=AssertionError('redownloaded')):
                appearance.install_font(self.installer)

    def test_linux_kitty_launcher_uses_selected_font(self):
        self.installer.windows = False
        self.installer.font_face = appearance.FONT_FACE
        with patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'data')}), patch.object(setup.shutil, 'which', side_effect=lambda name: '/usr/bin/' + name if name in ('kitty', 'yazi') else None):
            self.installer.launcher()
        text = (self.root / 'data/applications/yazi-launcher.desktop').read_text()
        self.assertIn('Terminal=false', text)
        self.assertIn('font_family=CaskaydiaMono Nerd Font Mono', text)
        self.assertIn('"kitty"', text)

    def test_clean_machine_plans_cover_preview_tools_without_host_dependencies(self):
        self.args.dry_run = True
        self.args.install_yazi = True
        self.args.install_dependencies = True
        self.args.theme = 'tokyo-night'
        for windows in [True, False]:
            self.installer.windows = windows
            manager = 'winget' if windows else 'apt-get'
            with patch.dict(os.environ, {'LOCALAPPDATA': str(self.root)}), patch.object(setup.shutil, 'which', side_effect=lambda name: manager if name == manager else None), patch.object(self.installer, 'find_command', return_value=None), patch.object(setup.os, 'geteuid', return_value=1000, create=True), patch.object(self.installer, 'run') as run, patch.object(appearance, 'verified_download', side_effect=AssertionError('dry run downloaded')):
                self.installer.dependencies()
                self.installer.configure()
                appearance.configure(self.installer)
            commands = [call.args[0] for call in run.call_args_list]
            if windows:
                identifiers = {command[command.index('--id') + 1] for command in commands}
                self.assertTrue({'sxyazi.yazi', 'Git.Git', 'Gyan.FFmpeg', 'oschwartz10612.Poppler', '7zip.7zip', 'Microsoft.WindowsTerminal'}.issubset(identifiers))
                self.assertTrue(all(command[command.index('--source') + 1] == 'winget' for command in commands))
            else:
                self.assertTrue(any({'file', 'ffmpeg', 'poppler-utils', '7zip', 'kitty', 'fontconfig'}.issubset(set(command)) for command in commands))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_old_windows_terminal_is_upgraded_for_image_support(self):
        self.args.dry_run = True
        self.args.install_dependencies = True
        self.installer.windows = True
        with patch.object(setup.shutil, 'which', return_value='winget'), patch.object(self.installer, 'find_command', return_value='present'), patch.object(setup, 'yazi_is_current', return_value=True), patch.object(appearance, 'windows_terminal_version', return_value=(1, 20, 0, 0)), patch.object(self.installer, 'run') as run:
            self.installer.dependencies()
        command = run.call_args.args[0]
        self.assertIn('upgrade', command)
        self.assertIn('Microsoft.WindowsTerminal', command)
        self.assertIn('--source', command)

    def test_font_failure_is_reported_without_claiming_font_was_selected(self):
        self.args.install_font = True
        self.installer.windows = False
        with patch.object(appearance, 'install_font', side_effect=OSError('offline')):
            face = appearance.configure(self.installer)
        self.assertIsNone(face)
        self.assertIn('offline', self.installer.setup_warnings[0])


if __name__ == '__main__':
    unittest.main()
