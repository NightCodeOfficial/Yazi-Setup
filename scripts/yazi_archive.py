"""ZIP operations used by the bundled Yazi plugin. No third-party modules."""
import argparse
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile


def create_zip(output, sources):
    output = Path(output).absolute()
    sources = [Path(p).absolute() for p in sources]
    if not sources:
        raise ValueError("Select at least one file or directory")
    entries = {}
    for source in sources:
        if not source.exists() or source.is_symlink():
            raise ValueError(f"Missing file or symbolic link: {source}")
        paths = [source] + (sorted(source.rglob('*')) if source.is_dir() else [])
        for path in paths:
            if path.is_symlink():
                raise ValueError(f"Symbolic links are not supported: {path}")
            if path == output:
                raise ValueError("The output ZIP cannot be inside a selected directory")
            name = path.relative_to(source.parent).as_posix()
            if name in entries and entries[name] != path:
                raise ValueError(f"Duplicate archive name: {name}")
            entries[name] = path
    if any(s.is_dir() and output.is_relative_to(s) for s in sources):
        raise ValueError("The output ZIP cannot be inside a selected directory")
    # Exclusive creation prevents accidentally updating or replacing an existing ZIP.
    with output.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, path in entries.items():
                    archive.write(path, name)
        except BaseException:
            stream.close()
            output.unlink()
            raise
    return output


def extract_zip(source, output):
    source, output = Path(source), Path(output).absolute()
    # Extract into a new folder only, with no existing symlinks or overwrite prompts.
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        for member in members:
            name = member.filename.replace('\\', '/')
            path = PurePosixPath(name)
            mode = member.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or ':' in name
                    or '\x00' in name or stat.S_ISLNK(mode)):
                raise ValueError(f"Unsafe archive entry: {member.filename}")
            if not (output / name).resolve().is_relative_to(output.resolve()):
                raise ValueError(f"Unsafe archive entry: {member.filename}")
        output.mkdir()  # Refuse existing destinations, including dangling symlinks.
        try:
            archive.extractall(output)
        except BaseException:
            shutil.rmtree(output)
            raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['zip', 'extract'])
    parser.add_argument('output', help='New ZIP filename or new extraction folder')
    parser.add_argument('sources', nargs='+')
    args = parser.parse_args()
    try:
        if args.action == 'zip':
            result = create_zip(args.output, args.sources)
        else:
            if len(args.sources) != 1:
                raise ValueError('Extract one ZIP at a time')
            result = extract_zip(args.sources[0], args.output)
        print(f"Created {result}")
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
