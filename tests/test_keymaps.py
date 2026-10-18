import argparse
import io
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import keymaps
import setup


def entries(text, layer='prepend_keymap'):
    return tomllib.loads(text).get('mgr', {}).get(layer, [])


class KeymapTests(unittest.TestCase):
    def test_adds_missing_and_preserves_conflicts_and_comments(self):
        existing = '# personal shortcuts\n[[mgr.prepend_keymap]]\non=["g","c"]\nrun="cd ~/custom-code"\n'
        proposed = setup.keymap(False, Path('/tmp/yazi-config'))
        plan = keymaps.plan_merge(existing, proposed, 'linux')
        self.assertTrue(plan.content.startswith(existing.strip()))
        self.assertEqual(entries(plan.content)[0]['run'], 'cd ~/custom-code')
        self.assertEqual(len(plan.conflicts), 1)
        self.assertEqual(plan.conflicts[0]['keys'], ['g', 'c'])
        self.assertIn('custom-code', keymaps.conflict_report(plan)[0])
        again = keymaps.plan_merge(plan.content, proposed, 'linux')
        self.assertEqual(again.content, plan.content)
        self.assertEqual(again.added, [])

    def test_inline_arrays_are_supported_without_rewriting_user_entries(self):
        existing = '# mine\n[mgr]\nprepend_keymap = [\n# keep comment\n {on="X",run="quit"},\n]\n\n[input]\nkeymap=[{on="a",run="move 1"}]\n'
        plan = keymaps.plan_merge(existing, setup.keymap(False, Path('/tmp/config')), 'linux')
        parsed = tomllib.loads(plan.content)
        self.assertIn('# keep comment', plan.content)
        self.assertEqual(parsed['input'], tomllib.loads(existing)['input'])
        self.assertEqual(parsed['mgr']['prepend_keymap'][-1], {'on': 'X', 'run': 'quit'})
        self.assertTrue(any(entry['on'] == ['u', 'z'] for entry in parsed['mgr']['prepend_keymap']))

    def test_custom_full_keymap_and_append_keymap_are_respected(self):
        for layer in ['keymap', 'append_keymap']:
            original = f'[mgr]\n{layer}=[{{on=["c","z"],run="custom"}}]\n'
            plan = keymaps.plan_merge(original, setup.keymap(True, Path('C:/config')), 'windows')
            self.assertEqual(entries(plan.content, layer), entries(original, layer))
            self.assertFalse(any(entry['on'] == ['c', 'z'] for entry in plan.added))
            self.assertTrue(any(c['keys'] == ['c', 'z'] for c in plan.conflicts))

    def test_os_specific_and_prefix_conflicts(self):
        original = '[[mgr.prepend_keymap]]\non=["g","c"]\nfor="windows"\nrun="custom"\n'
        self.assertEqual(keymaps.plan_merge(original, setup.keymap(False, Path('/tmp/c')), 'linux').conflicts, [])
        original += '[[mgr.prepend_keymap]]\non="u"\nrun="custom-prefix"\n'
        plan = keymaps.plan_merge(original, setup.keymap(False, Path('/tmp/c')), 'linux')
        self.assertTrue(any(c['keys'] == ['u', 'z'] for c in plan.conflicts))
        self.assertFalse(any(e['on'] == ['u', 'z'] for e in plan.added))

    def test_same_command_with_scalar_key_is_not_a_conflict(self):
        original = '[[mgr.prepend_keymap]]\non="R"\nrun="rename --empty=stem --cursor=start"\n'
        plan = keymaps.plan_merge(original, setup.keymap(False, Path('/tmp/c')), 'linux')
        self.assertEqual(plan.conflicts, [])
        self.assertTrue(any(e['on'] == ['R'] for e in plan.unchanged))

    def test_installer_asks_and_preserves_declined_keymap_byte_for_byte(self):
        for answer in ['n', 'y']:
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path = root / 'keymap.toml'
                original = '# custom\n[[mgr.prepend_keymap]]\non=["u","z"]\nrun="my-extractor"\n'
                path.write_text(original)
                args = argparse.Namespace(dry_run=False, skip_keymap=False, merge_keymap=False)
                inst = setup.Installer(args)
                inst.windows = False
                inst.config = root
                inst.home = root / 'home'
                with patch('builtins.input', return_value=answer) as question, patch.object(sys.stdin, 'isatty', return_value=True):
                    inst.configure()
                question.assert_called_once()
                if answer == 'n':
                    self.assertEqual(path.read_text(), original)
                else:
                    self.assertTrue(any(e['on'] == ['c', 'z'] for e in entries(path.read_text())))
                self.assertIn('my-extractor', inst.keymap_conflicts[0])

    def test_noninteractive_install_never_blocks_for_input(self):
        plan = keymaps.MergePlan('', added=[{'on': ['c', 'z'], 'run': 'zip'}])
        with patch.object(sys.stdin, 'isatty', return_value=False), patch('builtins.input', side_effect=AssertionError('prompted')):
            self.assertFalse(keymaps.confirm_merge(plan))
            self.assertTrue(keymaps.confirm_merge(plan, assume_merge=True))

    def test_both_platforms_have_archives_and_requested_navigation(self):
        for windows in (True, False):
            bindings = {tuple(e['on']): e['run'] for e in entries(setup.keymap(windows, Path('/tmp/config')))}
            self.assertEqual(bindings[('u', 'z')], 'shell -- ya pub extract --list %h')
            self.assertEqual(bindings[('c', 'z')], 'plugin setup-archive -- zip')
            self.assertIn(('g', 'a'), bindings)
            self.assertIn(('g', 'c'), bindings)
            self.assertIn((',', 'd'), bindings)
            if not windows:
                self.assertEqual(bindings[('<Enter>',)], 'plugin code-enter')


if __name__ == '__main__':
    unittest.main()
