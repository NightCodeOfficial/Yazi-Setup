"""Exercise actual ZIP/unzip keybindings in a temporary Linux Yazi PTY session."""
import argparse
import os
from pathlib import Path
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup


def main():
    if sys.platform != 'linux':
        raise SystemExit('This PTY integration check runs on Linux.')
    import fcntl
    import pty
    import termios
    if not shutil.which('yazi') or not shutil.which('ya'):
        raise SystemExit('Install yazi and ya before running this integration check.')
    with tempfile.TemporaryDirectory(prefix='yazi-keybind-smoke-') as temp:
        root = Path(temp)
        data = root / 'data'
        data.mkdir()
        source = data / 'hello ü.txt'
        source.write_text('archive roundtrip', encoding='utf-8')
        inst = setup.Installer(argparse.Namespace(dry_run=False, skip_keymap=False, merge_keymap=True))
        inst.config = root / 'config'
        inst.home = root / 'home'
        inst.configure()
        env = dict(os.environ, YAZI_CONFIG_HOME=str(inst.config), YAZI_STATE_HOME=str(root / 'state'),
                   TERM='xterm-256color', TERM_PROGRAM='')
        client = str(int(time.time_ns() % 1000000000) + 1000000000)
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 600, 960))
        process = subprocess.Popen(['yazi', '--client-id', client, str(data)],
                                   stdin=slave, stdout=slave, stderr=slave, env=env,
                                   start_new_session=True)
        os.close(slave)
        transcript = bytearray()

        def pump():
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b''
                transcript.extend(chunk)
                # Answer basic terminal probes; no real display or GUI is required.
                for query, answer in [(b'\x1b[6n', b'\x1b[1;1R'),
                                      (b'\x1b[c', b'\x1b[?1;2c'),
                                      (b'\x1b[16t', b'\x1b[6;16;8t')]:
                    if query in chunk:
                        os.write(master, answer)

        def wait_for(predicate, description, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                pump()
                if predicate():
                    return
                if process.poll() is not None:
                    break
            raise AssertionError(description + '\n' + transcript[-6000:].decode('utf-8', errors='replace'))

        try:
            wait_for(lambda: b'hello' in transcript, 'Yazi did not display the source file')
            transcript.clear()
            os.write(master, b'cz')
            wait_for(lambda: b'New ZIP filename:' in transcript, 'ZIP keybinding did not open its filename prompt')
            os.write(master, b'\r')
            output = data / 'archive.zip'
            wait_for(lambda: output.exists(), 'ZIP keybinding did not create its output')
            # Wait until ZIP writing has completed rather than racing the file creation.
            def complete_zip():
                try:
                    with zipfile.ZipFile(output) as archive:
                        return archive.read(source.name) == b'archive roundtrip'
                except (OSError, zipfile.BadZipFile, KeyError):
                    return False
            wait_for(complete_zip, 'ZIP keybinding produced incomplete output')
            source.unlink()
            subprocess.run(['ya', 'emit-to', client, 'reveal', str(output)], env=env, check=True, timeout=10)
            transcript.clear()
            wait_for(lambda: b'archive.zip' in transcript, 'Could not hover the ZIP for extraction')
            os.write(master, b'uz')
            wait_for(source.exists, 'Unzip keybinding did not extract the hovered archive')
            assert source.read_text(encoding='utf-8') == 'archive roundtrip'
            print('Actual Linux Yazi ZIP and unzip keybindings passed, including Unicode paths.')
        finally:
            if process.poll() is None:
                os.write(master, b'\x1bq')
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=3)
            os.close(master)


if __name__ == '__main__':
    main()
