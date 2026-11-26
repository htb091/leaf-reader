#!/usr/bin/env python3
"""Pack current LeafReader sources into one offline, inspectable Python installer.

Run only after the release freeze:
  python3 tools/make_upgrade.py 0.5 OUTPUT.py

Every payload is UTF-8 round-tripped exactly, including its final-newline state.
All v0.3 payloads remain required. New UI/tests are discovered AND checked against
explicit requirements; missing files abort rather than producing a partial pack.
This program only creates the requested installer, never applies it or builds.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'upgrade_runner.py'

# Historical v0.3 payloads: intentionally retained for v0.1/v0.2/v0.3 upgrades.
FILES = [
    'shared/src/commonMain/kotlin/dev/leaf/reader/Models.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ReaderStore.kt',
    'shared/src/iosMain/kotlin/dev/leaf/reader/ReaderFiles.ios.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderApp.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixAtoms.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixGlyphs.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfScreen.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfWidgets.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingScreen.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingSettings.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/TocSheet.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/Pagination.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ReaderStoreTest.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ManifestStorageTest.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReadingItemsTest.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderPaginationTest.kt',
    'iosApp/Sources/Parser/BookParser.swift',
    'iosApp/Sources/Parser/EPUBParser.swift',
    'iosApp/Sources/Parser/ZIPPreflight.swift',
    'iosApp/Sources/Parser/StreamingImport.swift',
    'iosApp/Sources/Parser/STREAMING_IMPORT.md',
    'iosApp/Sources/Host/DocumentPicker.swift',
    'iosApp/Tests/StreamingImportTests.swift',
    'iosApp/README.md',
    'scripts/build-ios.sh',
    'README.md',
    'VALIDATION.md',
    'UPGRADE-v0.2.md',
    'UPGRADE-v0.3.md',
    'validation-summary.json',
    '.github/workflows/upgrade-v02.yml',
    '.github/workflows/upgrade-v03.yml',
]
REQUIRED_V04_FILES = [
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ContentsScreen.kt',
    'UPGRADE-v0.4.md',
    '.github/workflows/upgrade-v04.yml',
    'scripts/tests/test_upgrade_v04.py',
    'tools/make_upgrade.py',
    'tools/upgrade_runner.py',
]
REQUIRED_V05_FILES = [
    'UPGRADE-v0.5.md',
    '.github/workflows/upgrade-v05.yml',
    'scripts/tests/test_upgrade_v05.py',
]
# Release-approved critical regression files; absence is a packaging error.
# Dynamic discovery supplements, never replaces, these hard checks.
REQUIRED_V05_SOURCE_FILES = [
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderOverlayRegressionTest.kt',
    'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/ReaderHostStructureTest.kt',
]
MATERIAL_DEPENDENCIES_V04 = ('top.yukonga.miuix.kmp:miuix-blur:0.9.4',)
# No new material coordinate is chosen without Lead confirmation.
MATERIAL_DEPENDENCIES_V05 = MATERIAL_DEPENDENCIES_V04
REQUIRED_DIRECTORY_TESTS = [
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ContentsNavigationTest.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderChromeTest.kt',
]
DISCOVER_TREES = (
    'shared/src/commonMain/kotlin/dev/leaf/reader',
    'shared/src/commonTest/kotlin/dev/leaf/reader',
    'shared/src/iosMain/kotlin/dev/leaf/reader',
    'iosApp/Sources',
    'iosApp/Tests',
)
# desktopTest was absent in older source releases; v0.5's explicit mandatory
# ReaderHostStructureTest above guarantees this tree exists for current packing.
OPTIONAL_DISCOVER_TREES = ('shared/src/desktopTest/kotlin/dev/leaf/reader',)
DISCOVER_SUFFIXES = ('.kt', '.swift', '.md')
PATCH_ONLY = {'shared/build.gradle.kts', 'iosApp/project.yml'}


def literal(text):
    """Prefer readable raw triple strings; validate the syntax, not just collision.

    repr is a plain Python string fallback when both delimiters collide or a
    terminal quote/backslash would make a raw literal ambiguous. No encoding or
    compression payload hides source text.
    """
    for quote in ("'''", '"""'):
        if quote in text:
            continue
        candidate = 'r%s%s%s' % (quote, text, quote)
        try:
            if ast.literal_eval(candidate) == text:
                return candidate
        except (SyntaxError, ValueError):
            pass
    candidate = repr(text)
    if ast.literal_eval(candidate) != text:
        raise ValueError('Python source literal failed round-trip')
    return candidate


def release_profile(version):
    if version in ('0.4', '0.4.0'):
        return [], MATERIAL_DEPENDENCIES_V04
    if version in ('0.5', '0.5.0'):
        return REQUIRED_V05_FILES + REQUIRED_V05_SOURCE_FILES, MATERIAL_DEPENDENCIES_V05
    raise ValueError('Supported installer versions: 0.4 and 0.5')


def discover_source_files(root, version='0.5'):
    release_files, _ = release_profile(version)
    names = set(FILES + REQUIRED_V04_FILES + REQUIRED_DIRECTORY_TESTS + release_files)
    for tree in DISCOVER_TREES + OPTIONAL_DISCOVER_TREES:
        directory = root / tree
        if tree in OPTIONAL_DISCOVER_TREES and not directory.exists() and not directory.is_symlink():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Missing/linked source tree: %s' % tree)
        for current, directories, files in os.walk(str(directory), followlinks=False):
            current = Path(current)
            for name in directories:
                if (current / name).is_symlink():
                    raise ValueError('Linked source directory: %s' % (current / name))
            directories.sort()
            for name in sorted(files):
                if name.endswith(DISCOVER_SUFFIXES):
                    path = current / name
                    if path.is_symlink():
                        raise ValueError('Linked source file: %s' % path)
                    names.add(path.relative_to(root).as_posix())
    missing = [name for name in sorted(names) if not (root / name).is_file()]
    if missing:
        raise ValueError('Missing required sources (no partial installer emitted): %s' % ', '.join(missing))
    directory_tests = [name for name in names if '/commonTest/' in name and
                       re.search(r'(Contents|Toc|Directory).*Test\.kt$', Path(name).name, re.IGNORECASE)]
    if not directory_tests:
        raise ValueError('Missing v0.4 contents/directory regression test; confirm its exact filename before packing')
    if names & PATCH_ONLY:
        raise ValueError('Build configuration must be patched, not embedded whole')
    for name in names:
        path = root / name
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink():
                raise ValueError('Linked payload path: %s' % name)
            if ancestor == root:
                break
    return sorted(names)


def assemble_installer(root, version='0.5', build_number=None):
    if not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?', version):
        raise ValueError('Use a numeric version, for example 0.5 or 0.5.0')
    marketing = version if version.count('.') == 2 else version + '.0'
    build_number = str(build_number) if build_number is not None else str(int(version.split('.')[1]))
    if not re.fullmatch(r'[1-9][0-9]*', build_number):
        raise ValueError('Build number must be a positive integer')
    _, material_dependencies = release_profile(version)
    names = discover_source_files(root, version)
    runner_path = root / 'tools' / 'upgrade_runner.py'
    runner = runner_path.read_bytes().decode('utf-8')
    ast.parse(runner, filename=str(runner_path))
    payloads = {}
    hashes = {}
    parts = []
    for name in names:
        raw = (root / name).read_bytes()
        text = raw.decode('utf-8')
        if text.encode('utf-8') != raw:
            raise ValueError('UTF-8 round-trip failure: %s' % name)
        payloads[name] = raw
        hashes[name] = hashlib.sha256(raw).hexdigest()
        parts.append('    %r: %s,\n' % (name, literal(text)))
    header = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LeafReader v%s offline source upgrade (Python 3.8+, standard library only).

Usage: python3 LeafReader-v%s-upgrade.py --project PATH [--archive PATH]
Plain FILES payloads are reviewable. No network, installs, subprocess or Git.
Embeds %d complete source files; preserves the user's Gradle configuration and
Bundle ID by patching only approved material dependencies and Xcode version scalars.
All target, Python AST, plist, anchor and payload checks precede source writes.
Backups, change manifest and payload SHA map live in .leaf-upgrade-backup/.
Kotlin/Swift compilation and tests remain CI/device verification tasks.
"""
INSTALLER_VERSION = %r
VERSION_PATCHES = %r
REQUIRED_MATERIAL_DEPENDENCIES = %r
FILES = {
''' % (version, version, len(names), version, {
        'MARKETING_VERSION': marketing, 'CURRENT_PROJECT_VERSION': build_number,
    }, tuple(material_dependencies))
    source = header + ''.join(parts) + '}\nEXPECTED_PAYLOAD_SHA256 = ' + json.dumps(hashes, indent=4, sort_keys=True) + '\n\n' + runner
    tree = ast.parse(source, filename='LeafReader-upgrade.py')
    assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
                   any(isinstance(target, ast.Name) and target.id == 'FILES' for target in node.targets) and
                   isinstance(node.value, ast.Dict)]
    if len(assignments) != 1:
        raise ValueError('Expected exactly one literal FILES dictionary')
    recovered = ast.literal_eval(assignments[0].value)
    if set(recovered) != set(payloads):
        raise ValueError('Payload filename round-trip failure')
    for name in names:
        if recovered[name].encode('utf-8') != payloads[name]:
            raise ValueError('Payload byte round-trip failure: %s' % name)
    return source, hashes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', nargs='?', default='0.5')
    parser.add_argument('output', nargs='?')
    parser.add_argument('--build-number', type=int)
    args = parser.parse_args(argv)
    output = Path(args.output) if args.output else Path('/sdcard/Download/DSH-Go/LeafReader-v%s-upgrade.py' % args.version)
    source, hashes = assemble_installer(ROOT, args.version, args.build_number)
    output = output.expanduser().absolute()
    for path in (output, *output.parents):
        if path.is_symlink():
            raise ValueError('Linked output path: %s' % path)
    try:
        output.relative_to(ROOT)
    except ValueError:
        pass
    else:
        if output.relative_to(ROOT).as_posix() in set(hashes) | PATCH_ONLY:
            raise ValueError('Installer output collides with a source file')
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(output.parent), prefix='.leaf-pack-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(source.encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Wrote %s (%d files, %d bytes, sha256=%s)' % (
        output, len(hashes), output.stat().st_size,
        hashlib.sha256(output.read_bytes()).hexdigest()))
    print('Payload SHA256: ' + json.dumps(hashes, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError) as error:
        raise SystemExit('Packing stopped: %s' % error)
