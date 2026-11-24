#!/usr/bin/env python3
"""Package a built, unsigned iphoneos .app without an App Store export profile."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import stat
import struct
import zipfile


def package(app: Path, output: Path) -> Path:
    app = app.resolve(strict=True)
    if app.suffix != '.app' or not app.is_dir():
        raise ValueError('Expected a built .app directory')
    with (app / 'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    executable = info.get('CFBundleExecutable', '')
    if not executable or '/' in executable or '\\' in executable:
        raise ValueError('Missing or invalid CFBundleExecutable')
    binary = app / executable
    if not binary.is_file():
        raise ValueError('App executable is missing')
    with binary.open('rb') as stream:
        header = stream.read(8)
    # A generic iOS device build is a thin ARM64 Mach-O, not an iOS Simulator binary.
    if len(header) != 8 or struct.unpack('<II', header) != (0xfeedfacf, 0x0100000c):
        raise ValueError('Expected a thin arm64 Mach-O device executable')
    if info.get('CFBundleSupportedPlatforms') != ['iPhoneOS']:
        raise ValueError('Expected an iPhoneOS build, not an iOS Simulator build')
    minimum = tuple(int(part) for part in info.get('MinimumOSVersion', '0').split('.'))
    if minimum[:1] != (16,):
        raise ValueError('Expected an iOS 16.x deployment target')
    output = output.resolve()
    if output == app or app in output.parents:
        raise ValueError('Output must be outside the .app')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.ipa.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(app.rglob('*')):
            relative = Path('Payload') / app.name / path.relative_to(app)
            entry = zipfile.ZipInfo(str(relative) + ('/' if path.is_dir() and not path.is_symlink() else ''))
            entry.create_system = 3
            mode = path.lstat().st_mode
            entry.external_attr = mode << 16
            if path.is_symlink():
                link = os.readlink(path)
                resolved = (path.parent / link).resolve()
                if os.path.isabs(link) or (resolved != app and app not in resolved.parents):
                    raise ValueError('App contains an escaping symlink')
                archive.writestr(entry, link.encode())
            elif path.is_dir():
                entry.external_attr |= 0x10
                archive.writestr(entry, b'')
            else:
                entry.compress_type = zipfile.ZIP_DEFLATED
                with path.open('rb') as source, archive.open(entry, 'w') as target:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)
    temporary.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.ipa.sha256').write_text(f'{digest}  {output.name}\n')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(package(args.app, args.output))
