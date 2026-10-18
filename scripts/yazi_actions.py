"""Cross-platform OS actions for Yazi. Paths are passed as arguments, never shell code."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def copy_file(path):
    source = Path(path).resolve(strict=True)
    uri = source.as_uri() + '\r\n'
    if os.environ.get('WAYLAND_DISPLAY') and shutil.which('wl-copy'):
        command = ['wl-copy', '--type', 'text/uri-list']
    elif os.environ.get('DISPLAY') and shutil.which('xclip'):
        command = ['xclip', '-selection', 'clipboard', '-target', 'text/uri-list']
    else:
        raise RuntimeError('File clipboard needs wl-copy in a Wayland session or xclip in an X11 session.')
    subprocess.run(command, input=uri.encode('utf-8'), check=True)
    return f'Copied file to OS clipboard: {source}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['clipboard'])
    parser.add_argument('path')
    args = parser.parse_args()
    try:
        print(copy_file(args.path))
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
