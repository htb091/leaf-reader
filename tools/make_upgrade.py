#!/usr/bin/env python3
"""Generate the single-file LeafReader upgrade installer from the current sources.

The runtime half of the installer lives in tools/upgrade_runner.py. This packer
only verifies that every embedded file round-trips byte-for-byte and that the
chosen raw-string delimiter does not collide with the content.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'upgrade_runner.py'

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


def literal(text):
    for quote in ("'''", '"""'):
        if quote not in text and not text.endswith('\\'):
            return 'r%s%s%s' % (quote, text, quote)
    raise SystemExit('No safe raw-string delimiter for content; refusing to emit lossy literal')


def main(argv):
    version = argv[1] if len(argv) > 1 else '0.3'
    marketing = version if version.count('.') >= 2 else version + '.0'
    output = Path(argv[2]) if len(argv) > 2 else Path('/sdcard/Download/DSH-Go/LeafReader-v%s-upgrade.py' % version)
    runner = RUNNER.read_text()
    marketing = version if version.count(".") >= 2 else version + ".0"
    runner = runner.replace("'MARKETING_VERSION': '0.2.0'", "'MARKETING_VERSION': '%s'" % marketing)
    runner = runner.replace("'CURRENT_PROJECT_VERSION': '2'", "'CURRENT_PROJECT_VERSION': '3'")

    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit('Missing sources: %s' % ', '.join(missing))

    parts = []
    digest = {}
    for name in FILES:
        raw = (ROOT / name).read_bytes()
        text = raw.decode('utf-8')
        if not text.endswith('\n'):
            text += '\n'
            print('note: %s lacked a trailing newline; embedded with one' % name)
        digest[name] = hashlib.sha256(text.encode('utf-8')).hexdigest()
        parts.append("    '%s': %s,\n" % (name, literal(text)))

    header = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LeafReader v%s offline source upgrade (Python 3.8+, standard library only).

Usage: python3 LeafReader-v%s-upgrade.py --project PATH [--archive PATH]
Review FILES below before use. No network, package installation, subprocess,
credential discovery, Git operation or downloaded-code execution is performed.
It writes the %d frozen source files plus two version scalars in iosApp/project.yml.
Overwritten files are copied to .leaf-upgrade-backup/<UTC>/ with a change manifest.
Atomicity is per file (same-directory tempfile + os.replace).
Kotlin/Swift compilation and regression tests belong to CI, not this tool.
"""

import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import tempfile
import zipfile

FILES = {
''' % (version, version, len(FILES))

    output.write_text(header + ''.join(parts) + runner)
    generated = output.read_bytes()
    check = compile(output.read_text(), str(output), 'exec')
    del check

    # Verify every payload appears verbatim in the generated file.
    for name in FILES:
        text = (ROOT / name).read_text()
        if text not in generated.decode('utf-8'):
            raise SystemExit('Payload verification failed for %s' % name)
    print('Wrote %s (%d files, %d bytes, sha256=%s)' % (
        output, len(FILES), len(generated), hashlib.sha256(generated).hexdigest()))
    print('Payload sha256:')
    for name in FILES:
        print('  %s  %s' % (digest[name], name))


if __name__ == '__main__':
    main(sys.argv)
