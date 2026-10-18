"""Exercise preview tools using temporary sample files; never modifies Yazi config."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import tempfile
import zipfile
import zlib


def find_tool(name):
    if name == 'file' and os.environ.get('YAZI_FILE_ONE'):
        path = Path(os.environ['YAZI_FILE_ONE'])
        if path.is_file():
            return str(path)
    found = shutil.which(name)
    if found:
        return found
    if name == 'file' and shutil.which('git'):
        path = Path(shutil.which('git')).parent.parent / 'usr/bin/file.exe'
        if path.is_file():
            return str(path)
    candidates = []
    if name == '7z':
        found = shutil.which('7zz')
        if found:
            return found
        candidates += [Path(os.environ[v]) / '7-Zip/7z.exe'
                       for v in ('ProgramW6432', 'ProgramFiles', 'ProgramFiles(x86)') if v in os.environ]
    if name == 'resvg':
        candidates += [Path.home() / '.local/bin/resvg']
        if os.environ.get('LOCALAPPDATA'):
            candidates += [Path(os.environ['LOCALAPPDATA']) / 'YaziSetup/bin/resvg.exe']
    return next((str(path) for path in candidates if path.is_file()), None)


def sample_pdf():
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Resources << >> /Contents 4 0 R >>',
               b'<< /Length 0 >>\nstream\n\nendstream']
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{index} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref = len(data)
    data += b'xref\n0 5\n0000000000 65535 f \n'
    for offset in offsets[1:]:
        data += f'{offset:010} 00000 n \n'.encode()
    data += f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return bytes(data)


def check_previews():
    results = []
    with tempfile.TemporaryDirectory(prefix='yazi-previews-') as folder:
        root = Path(folder)
        (root / 'text.txt').write_text('Yazi preview test\n', encoding='utf-8')
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 32, 32, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress((b'\x00' + b'\xff\x00\x00' * 32) * 32)) + chunk(b'IEND', b''))
        (root / 'image.png').write_bytes(png)
        (root / 'image.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="red"/></svg>')
        (root / 'document.pdf').write_bytes(sample_pdf())
        with zipfile.ZipFile(root / 'archive.zip', 'w') as archive:
            archive.write(root / 'text.txt', 'text.txt')

        def exercise(label, tool, args, validate, optional=False):
            executable = find_tool(tool)
            if not executable:
                results.append({'preview': label, 'tool': tool, 'ok': False,
                                'optional': optional, 'detail': 'Missing tool'})
                return
            try:
                result = subprocess.run([executable, *args], cwd=root, capture_output=True, timeout=30)
                ok = result.returncode == 0 and validate(result)
                detail = 'Passed' if ok else (result.stderr.decode('utf-8', errors='replace')[-1200:] or 'Output validation failed')
            except (OSError, subprocess.TimeoutExpired) as error:
                ok, detail = False, str(error)
            results.append({'preview': label, 'tool': tool, 'ok': ok,
                            'optional': optional, 'detail': detail})

        exercise('Text MIME detection', 'file', ['--mime-type', '-b', 'text.txt'], lambda r: b'text/plain' in r.stdout)
        exercise('Image MIME detection', 'file', ['--mime-type', '-b', 'image.png'], lambda r: b'image/png' in r.stdout)
        exercise('PDF thumbnail', 'pdftoppm', ['-f', '1', '-singlefile', '-scale-to', '32', '-png', 'document.pdf', 'pdf'], lambda r: (root / 'pdf.png').is_file())
        exercise('Video decoding', 'ffmpeg', ['-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=32x32:d=0.2', '-c:v', 'mpeg4', 'video.mp4'], lambda r: (root / 'video.mp4').is_file())
        exercise('Video metadata', 'ffprobe', ['-v', 'error', '-show_entries', 'format=format_name', '-of', 'json', 'video.mp4'], lambda r: b'format_name' in r.stdout)
        exercise('Video thumbnail', 'ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', 'video.mp4', '-frames:v', '1', 'video.jpg'], lambda r: (root / 'video.jpg').is_file())
        exercise('Archive listing', '7z', ['l', 'archive.zip'], lambda r: b'text.txt' in r.stdout)
        exercise('SVG thumbnail', 'resvg', ['image.svg', 'svg.png'], lambda r: (root / 'svg.png').is_file())
        exercise('Additional image formats', 'magick', ['identify', 'image.png'], lambda r: b'PNG' in r.stdout, optional=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    results = check_previews()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print(f'{"PASS" if result["ok"] else "FAIL"}: {result["preview"]} ({result["tool"]}): {result["detail"]}')
        print('This checks MIME detection and rendering tools. Displaying images also needs a supported terminal; use ya env inside Yazi to inspect its detected adapter.')
    return 1 if any(not r['ok'] and not r['optional'] for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
