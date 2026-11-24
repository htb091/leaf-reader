#!/usr/bin/env python3
"""Offline structural checks; these do not replace Kotlin/Xcode compilation."""
from pathlib import Path
import hashlib
import plistlib
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'gradlew', 'gradlew.bat', 'gradle/wrapper/gradle-wrapper.jar',
    'gradle/wrapper/gradle-wrapper.properties', 'settings.gradle.kts',
    'shared/build.gradle.kts', 'iosApp/project.yml', 'iosApp/Info.plist',
    'iosApp/Sources/Host/LeafReaderApp.swift', 'iosApp/Sources/Parser/BookParser.swift',
    '.github/workflows/ios-ipa.yml', 'scripts/build-ios.sh', 'scripts/test-ios.sh',
    'scripts/package_ipa.py',
]
for name in REQUIRED:
    if not (ROOT / name).is_file():
        raise SystemExit(f'Missing required source file: {name}')
wrapper = ROOT / 'gradle/wrapper/gradle-wrapper.jar'
expected = '7a9ce74cff467ca1bf60a4fcd9f05185acceda4d0f382434d393e17864262c5d'
if hashlib.sha256(wrapper.read_bytes()).hexdigest() != expected:
    raise SystemExit('Gradle wrapper checksum differs from the pinned source release')
if not zipfile.is_zipfile(wrapper):
    raise SystemExit('Gradle wrapper is not a valid JAR')
properties = (ROOT / 'gradle/wrapper/gradle-wrapper.properties').read_text()
if not re.search(r'^distributionSha256Sum=[a-f0-9]{64}$', properties, re.M):
    raise SystemExit('Missing Gradle distribution checksum')
with (ROOT / 'iosApp/Info.plist').open('rb') as stream:
    info = plistlib.load(stream)
if info.get('CFBundleExecutable') != '$(EXECUTABLE_NAME)':
    raise SystemExit('Unexpected app executable plist setting')
if info.get('CADisableMinimumFrameDurationOnPhone') is not True:
    raise SystemExit('Missing Compose iOS frame-duration plist setting')
project = (ROOT / 'iosApp/project.yml').read_text()
for required in ('"16.0"', 'embed: false', 'ParserTests', 'exactVersion: 0.9.19', 'exactVersion: 2.7.7'):
    if required not in project:
        raise SystemExit(f'Missing pinned project setting: {required}')
print(f'Project structure OK: {len(REQUIRED)} required files, wrapper checksum, plist, deployment and dependency pins.')
