import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('actions', Path(__file__).resolve().parents[1] / 'scripts/yazi_actions.py')
actions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(actions)


class LinuxClipboardTests(unittest.TestCase):
    def test_wayland_clipboard_uses_escaped_file_uri_and_direct_stdin(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file ü space.txt'
            path.write_text('clipboard')
            with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}, clear=True), patch.object(actions.shutil, 'which', return_value='/bin/wl-copy'), patch.object(actions.subprocess, 'run') as run:
                actions.copy_file(path)
            self.assertEqual(run.call_args.args[0], ['wl-copy', '--type', 'text/uri-list'])
            uri = run.call_args.kwargs['input'].decode()
            self.assertIn('%20', uri)
            self.assertIn('%C3%BC', uri)
            self.assertEqual(uri, path.resolve().as_uri() + '\r\n')

    def test_x11_clipboard_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file.txt'
            path.write_text('clipboard')
            with patch.dict(os.environ, {'DISPLAY': ':0'}, clear=True), patch.object(actions.shutil, 'which', return_value='/bin/xclip'), patch.object(actions.subprocess, 'run') as run:
                actions.copy_file(path)
            self.assertEqual(run.call_args.args[0], ['xclip', '-selection', 'clipboard', '-target', 'text/uri-list'])

    def test_no_graphical_clipboard_reports_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file.txt'
            path.write_text('clipboard')
            with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'Wayland'):
                actions.copy_file(path)


if __name__ == '__main__':
    unittest.main()
