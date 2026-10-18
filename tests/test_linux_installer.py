import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == 'linux', 'Native Linux shell wrapper checks')
class LinuxWrapperTests(unittest.TestCase):
    def test_default_config_only_and_read_only_modes(self):
        for arguments, full in [([], True), (['--theme', 'tokyo-night'], True),
                                (['--configure-only', '--merge-keymap'], False),
                                (['--check-previews'], False)]:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                python = root / 'python3'
                python.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nprintf "%s\\n" "$@" > "$YAZI_TEST_ARGUMENTS"\n')
                python.chmod(0o755)
                output = root / 'arguments'
                env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'], YAZI_TEST_ARGUMENTS=str(output))
                subprocess.run(['sh', str(ROOT / 'install.sh'), *arguments], env=env, check=True)
                recorded = output.read_text().splitlines()
                self.assertEqual(recorded[0], str(ROOT / 'setup.py'))
                self.assertEqual('--install-yazi' in recorded, full)
                self.assertEqual('--install-dependencies' in recorded, full)
                self.assertNotIn('--configure-only', recorded)
                if full:
                    self.assertIn('choose', recorded)


if __name__ == '__main__':
    unittest.main()
