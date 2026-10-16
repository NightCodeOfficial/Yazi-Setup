import argparse
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup

spec = importlib.util.spec_from_file_location('archive', setup.ROOT / 'scripts/yazi_archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_roundtrip_files_directories_empty_and_unicode(self):
        source = self.root / 'source space & ü'
        (source / 'empty').mkdir(parents=True)
        (source / "quote' & %.txt").write_text('hello ü', encoding='utf-8')
        extra = self.root / '-second.txt'
        extra.write_bytes(b'\x00\xff')
        output = self.root / 'result.zip'
        archive.create_zip(output, [source, extra])
        extracted = self.root / 'out'
        archive.extract_zip(output, extracted)
        self.assertEqual((extracted / source.name / "quote' & %.txt").read_text(encoding='utf-8'), 'hello ü')
        self.assertTrue((extracted / source.name / 'empty').is_dir())
        self.assertEqual((extracted / extra.name).read_bytes(), b'\x00\xff')

    def test_refuses_overwrite_and_output_inside_source(self):
        source = self.root / 'source'
        source.mkdir()
        output = self.root / 'archive.zip'
        archive.create_zip(output, [source])
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            archive.create_zip(output, [source])
        self.assertEqual(output.read_bytes(), before)
        with self.assertRaises(ValueError):
            archive.create_zip(source / 'recursive.zip', [source])
        with self.assertRaises(FileExistsError):
            archive.extract_zip(output, source)

    def test_rejects_unsafe_members_before_creating_folder(self):
        for name in ['../escape', '/absolute', 'C:/escape', '..\\escape']:
            with self.subTest(name=name):
                output = self.root / 'bad.zip'
                with zipfile.ZipFile(output, 'w') as z:
                    z.writestr(name, 'bad')
                with self.assertRaises(ValueError):
                    archive.extract_zip(output, self.root / 'out')
                self.assertFalse((self.root / 'out').exists())

    def test_rejects_symlink_member(self):
        output = self.root / 'bad.zip'
        info = zipfile.ZipInfo('link')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(output, 'w') as z:
            z.writestr(info, '../escape')
        with self.assertRaises(ValueError):
            archive.extract_zip(output, self.root / 'out')

    def test_corrupt_archive_cleanup(self):
        output = self.root / 'bad.zip'
        output.write_bytes(b'not a ZIP')
        with self.assertRaises(zipfile.BadZipFile):
            archive.extract_zip(output, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())


class SetupTests(unittest.TestCase):
    def test_keymap_migration_idempotence_and_user_bindings(self):
        custom = '[[mgr.prepend_keymap]]\non = "X"\nrun = "quit"\n'
        old = custom + setup.OLD_START + '\nold bindings\n' + setup.OLD_END
        snippet = setup.keymap(True, Path('C:/config space'))
        merged = setup.merge_keymap(old, snippet)
        self.assertIn(custom, merged)
        self.assertNotIn('old bindings', merged)
        self.assertEqual(setup.merge_keymap(merged, snippet), merged)
        self.assertEqual(len(tomllib.loads(merged)['mgr']['prepend_keymap']), 13)

    def test_partial_markers_refused(self):
        for existing in [setup.START, setup.OLD_END, setup.END + setup.START]:
            with self.assertRaises(ValueError):
                setup.merge_keymap(existing, '')

    def test_both_platform_configurations_and_repeat_install(self):
        for windows in [False, True]:
            with self.subTest(windows=windows), tempfile.TemporaryDirectory() as temp:
                args = argparse.Namespace(dry_run=False, skip_keymap=False, skip_launcher=True)
                inst = setup.Installer(args)
                inst.windows = windows
                inst.home = Path(temp)
                inst.config = Path(temp) / 'config ü'
                inst.configure()
                keymap = (inst.config / 'keymap.toml').read_text()
                self.assertIn('mgr', tomllib.loads(keymap))
                plugin = (inst.config / 'plugins/setup-archive.yazi/main.lua').read_text(encoding='utf-8')
                self.assertNotIn('__RUNTIME__', plugin)
                inst.configure()
                self.assertEqual(keymap, (inst.config / 'keymap.toml').read_text())
                self.assertEqual(list(inst.config.glob('*.backup-*')), [])

    def test_linux_launcher_and_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            args = argparse.Namespace(dry_run=True, skip_keymap=False, skip_launcher=False)
            inst = setup.Installer(args)
            inst.windows = False
            inst.home = Path(temp)
            inst.config = Path(temp) / 'config'
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(Path(temp) / 'data')}):
                inst.configure()
                inst.launcher()
                self.assertEqual(list(Path(temp).iterdir()), [])
                args.dry_run = False
                inst.launcher()
                self.assertTrue((Path(temp) / 'data/applications/yazi-launcher.desktop').exists())
                self.assertIn('exec ', (Path(temp) / '.local/bin/yazi-launcher').read_text())

    def test_linux_package_plans(self):
        for manager in ['apt-get', 'dnf', 'pacman']:
            with self.subTest(manager=manager):
                args = argparse.Namespace(dry_run=True, install_dependencies=True, install_yazi=True)
                inst = setup.Installer(args)
                inst.windows = False
                with patch.object(setup.shutil, 'which', side_effect=lambda p: '/bin/' + p if p == manager else None), patch.object(setup.os, 'geteuid', return_value=1000, create=True), patch.object(inst, 'run') as run:
                    inst.dependencies()
                commands = [call.args[0] for call in run.call_args_list]
                self.assertTrue(all(c[0] == 'sudo' for c in commands))
                self.assertTrue(any('yazi' in c for c in commands))
                self.assertTrue(any('unzip' in c for c in commands))

    def test_windows_package_plan_skips_existing_commands(self):
        args = argparse.Namespace(dry_run=True, install_dependencies=True, install_yazi=True)
        inst = setup.Installer(args)
        inst.windows = True
        with patch.object(setup.shutil, 'which', side_effect=lambda p: None if p in ['yazi', '7z'] else p), patch.object(inst, 'run') as run:
            inst.dependencies()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertTrue(any('sxyazi.yazi' in c for c in commands))
        self.assertTrue(any('7zip.7zip' in c for c in commands))


if __name__ == '__main__':
    unittest.main()
