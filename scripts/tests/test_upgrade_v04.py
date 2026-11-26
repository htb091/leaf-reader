"""Self-contained installer regression tests. Every mutation is in TemporaryDirectory.

Run: python3 -m unittest discover -s scripts/tests -p test_upgrade_v04.py -v
No Gradle, network, package installer, downloaded code or real project upgrade.
"""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load_tool(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_tool('leaf_upgrade_v04_runtime', 'upgrade_runner.py')
packer = load_tool('leaf_upgrade_v04_packer', 'make_upgrade.py')
UI = 'top.yukonga.miuix.kmp:miuix-ui:0.9.4'
BLUR = 'top.yukonga.miuix.kmp:miuix-blur:0.9.4'
BUILD = ('// user configuration stays verbatim\n'
         'plugins { kotlin("multiplatform") }\n'
         'repositories { maven("https://custom.invalid/maven") }\n'
         'kotlin {\n    sourceSets {\n        commonMain.dependencies {\n'
         '            implementation("' + UI + '") // user comment\n'
         '            implementation("custom:reader-addon:7")\n'
         '        }\n    }\n}\n')
PAYLOAD = {
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderChrome.kt': '// new UI source\n',
    'scripts/new_probe.py': 'VALUE = "😀"\n',
    'README.md': '# LeafReader v0.4\n',
}


class UpgradeV04Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='leaf-v04-test-')
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve() / 'project'
        self.project.mkdir()
        self.put('settings.gradle.kts', 'rootProject.name = "UserLeaf"\n')
        self.put('shared/build.gradle.kts', BUILD)
        self.put('iosApp/project.yml', self.yml('0.3.0', '3'))
        self.put('iosApp/Info.plist', plistlib.dumps({'CFBundleIdentifier': 'user.custom.reader'}))
        self.put('README.md', '# existing user project\n')
        self.put('scripts/existing.py', 'VALUE = 1\n')
        self.files_patch = mock.patch.object(runner, 'FILES', dict(PAYLOAD))
        self.files_patch.start()
        self.addCleanup(self.files_patch.stop)
        self.hash_patch = mock.patch.object(runner, 'EXPECTED_PAYLOAD_SHA256', {
            name: hashlib.sha256(text.encode()).hexdigest() for name, text in PAYLOAD.items()
        })
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    @staticmethod
    def yml(marketing, build):
        return ('name: UserLeaf\nsettings:\n  base:\n'
                '    PRODUCT_BUNDLE_IDENTIFIER: user.custom.reader\n'
                '    CUSTOM_SETTING: "keep-me"\n'
                '    MARKETING_VERSION: "' + marketing + '" # preserve comment\n'
                '    CURRENT_PROJECT_VERSION: "' + build + '"\n')

    def put(self, name, content):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in self.project.rglob('*') if path.is_file() and not path.is_symlink()}

    def apply(self, archive=None):
        arguments = ['--project', str(self.project)]
        if archive:
            arguments += ['--archive', archive]
        with contextlib.redirect_stdout(io.StringIO()):
            runner.main(arguments)

    def assert_preflight_stops_without_writes(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, SyntaxError)):
            self.apply()
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project / '.leaf-upgrade-backup').exists())
        self.assertFalse(list(self.project.rglob('.leaf-*.tmp')))

    def test_blur_is_adjacent_and_user_configuration_is_byte_preserved(self):
        patched = runner.patch_shared_gradle(BUILD)
        self.assertEqual(patched.replace('            implementation("' + BLUR + '")\n', '', 1), BUILD)
        self.assertIn('implementation("' + UI + '") // user comment\n'
                      '            implementation("' + BLUR + '")\n', patched)
        self.assertEqual(runner.patch_shared_gradle(patched), patched)

    def test_existing_blur_dependency_needs_no_insertion(self):
        existing = BUILD.replace('commonMain.dependencies {',
                                 'commonMain.dependencies {\n            implementation("' + BLUR + '")')
        self.assertEqual(runner.patch_shared_gradle(existing), existing)
        self.put('shared/build.gradle.kts', existing)
        self.apply()
        self.assertEqual((self.project / 'shared/build.gradle.kts').read_bytes(), existing.encode())

    def test_crlf_and_final_line_without_newline_are_preserved(self):
        text = BUILD.replace('\n', '\r\n')
        patched = runner.patch_shared_gradle(text)
        self.assertNotIn('\n', patched.replace('\r\n', ''))
        self.assertEqual(patched.replace('            implementation("' + BLUR + '")\r\n', '', 1), text)
        eof = 'implementation("' + UI + '")'
        self.assertEqual(runner.patch_shared_gradle(eof), eof + '\nimplementation("' + BLUR + '")\n')
        yml = self.yml('0.1.0', '1').replace('\n', '\r\n')
        patched_yml = runner.patch_project_yml(yml)
        self.assertEqual(patched_yml, yml.replace('"0.1.0"', '"0.4.0"').replace('"1"', '"4"'))

    def test_upgrades_v01_v02_v03_preserving_bundle_and_build_settings(self):
        for minor in (1, 2, 3):
            original = self.yml('0.%d.0' % minor, str(minor))
            self.put('iosApp/project.yml', original)
            self.put('shared/build.gradle.kts', BUILD)
            self.apply()
            actual = (self.project / 'iosApp/project.yml').read_text()
            expected = original.replace('"0.%d.0"' % minor, '"0.4.0"').replace('"%d"' % minor, '"4"')
            self.assertEqual(actual, expected)
            self.assertIn('user.custom.reader', actual)
            self.assertIn('custom:reader-addon:7', (self.project / 'shared/build.gradle.kts').read_text())

    def test_whole_upgrade_is_idempotent_and_preserves_file_modes(self):
        script = self.put('scripts/new_probe.py', 'VALUE = 0\n')
        script.chmod(0o755)
        self.apply()
        first = {key: value for key, value in self.snapshot().items() if not key.startswith('.leaf-upgrade-backup/')}
        self.apply()
        second = {key: value for key, value in self.snapshot().items() if not key.startswith('.leaf-upgrade-backup/')}
        self.assertEqual(first, second)
        self.assertEqual(script.stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.project / 'shared/build.gradle.kts').read_text().count(BLUR), 1)
        manifests = list((self.project / '.leaf-upgrade-backup').glob('*/change-manifest.json'))
        self.assertEqual(len(manifests), 2)
        latest = sorted(manifests)[-1]
        self.assertTrue(all(item['unchanged'] for item in json.loads(latest.read_text())['changes']))

    def test_missing_anchor_is_detected_before_any_file_or_backup_write(self):
        self.put('shared/build.gradle.kts', BUILD.replace(UI, 'user:another-reader:1'))
        self.assert_preflight_stops_without_writes()

    def test_commented_anchor_does_not_count(self):
        self.put('shared/build.gradle.kts', '/*\nimplementation("' + UI + '")\n*/\n')
        self.assert_preflight_stops_without_writes()

    def test_wrong_or_duplicate_blur_versions_stop_before_writes(self):
        for declaration in ('implementation("' + BLUR.replace('0.9.4', '0.9.3') + '")',
                            'implementation("' + BLUR + '")\nimplementation("' + BLUR + '")'):
            self.put('shared/build.gradle.kts', BUILD + declaration + '\n')
            self.assert_preflight_stops_without_writes()

    def test_missing_version_scalar_stops_before_any_write(self):
        self.put('iosApp/project.yml', self.yml('0.3.0', '3').replace('MARKETING_VERSION', 'USER_VERSION'))
        self.assert_preflight_stops_without_writes()

    def test_invalid_python_or_plist_stops_before_any_write(self):
        self.put('scripts/existing.py', 'def broken(:\n')
        self.assert_preflight_stops_without_writes()
        self.put('scripts/existing.py', 'VALUE = 1\n')
        self.put('iosApp/Info.plist', '<plist><dict>broken</plist>')
        self.assert_preflight_stops_without_writes()

    def test_invalid_late_payload_path_stops_before_any_write(self):
        with mock.patch.object(runner, 'FILES', {**PAYLOAD, 'zz/../../escape.py': 'pass\n'}), \
                mock.patch.object(runner, 'EXPECTED_PAYLOAD_SHA256', {}):
            self.assert_preflight_stops_without_writes()
        for name in ('/absolute', './relative', 'a//b', 'a/../b', 'a\\b', 'C:drive', 'a\x00b'):
            with self.assertRaises(ValueError):
                runner.validate_relative(name)

    def test_symlink_target_stops_without_touching_external_file(self):
        external = Path(self.temporary.name).resolve() / 'external.md'
        external.write_text('keep outside')
        target = self.project / 'README.md'
        target.unlink()
        target.symlink_to(external)
        self.assert_preflight_stops_without_writes()
        self.assertEqual(external.read_text(), 'keep outside')

    def test_invalid_archive_is_preflighted_before_source_write(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply('../outside.zip')
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project / '.leaf-upgrade-backup').exists())

    def test_backup_change_manifest_and_payload_sha_are_complete(self):
        original_yml = (self.project / 'iosApp/project.yml').read_bytes()
        self.apply()
        backup = next((self.project / '.leaf-upgrade-backup').iterdir())
        manifest = json.loads((backup / 'change-manifest.json').read_text())
        self.assertEqual(manifest['status'], 'applied')
        self.assertEqual(manifest['file_count'], len(PAYLOAD))
        self.assertEqual(len(manifest['changes']), len(PAYLOAD) + 2)
        self.assertEqual((backup / 'files/iosApp/project.yml').read_bytes(), original_yml)
        self.assertEqual((backup / 'files/shared/build.gradle.kts').read_bytes(), BUILD.encode())
        hashes = json.loads((backup / 'payload-sha256.json').read_text())
        self.assertEqual(hashes, runner.EXPECTED_PAYLOAD_SHA256)
        for change in manifest['changes']:
            self.assertEqual(change['sha256_after'], hashlib.sha256((self.project / change['path']).read_bytes()).hexdigest())

    def test_apply_failure_rolls_back_replacements_and_new_files(self):
        before = self.snapshot()
        original_write = runner.atomic_write

        def fail_on_new_script(target, payload, mode=0o644):
            if target == self.project / 'scripts/new_probe.py':
                raise OSError('injected write failure')
            return original_write(target, payload, mode)

        with mock.patch.object(runner, 'atomic_write', side_effect=fail_on_new_script):
            with self.assertRaises(OSError):
                self.apply()
        sources = {key: value for key, value in self.snapshot().items() if not key.startswith('.leaf-upgrade-backup/')}
        self.assertEqual(sources, before)
        backup = next((self.project / '.leaf-upgrade-backup').iterdir())
        self.assertEqual(json.loads((backup / 'change-manifest.json').read_text())['status'], 'rolled-back')

    def test_archive_keeps_wrapper_native_tests_icons_tools_original_ci(self):
        keep = ('gradle/wrapper/gradle-wrapper.jar', 'gradle/wrapper/gradle-wrapper.properties',
                'gradlew', 'gradlew.bat', 'iosApp/Tests/BookParserTests.swift',
                'iosApp/Assets.xcassets/AppIcon.appiconset/icon.png',
                'iosApp/Tools/generate_app_icon.py', '.github/workflows/original.yml',
                'tools/upgrade_runner.py', 'LeafReader-v0.4-upgrade.py')
        omit = ('local.properties', '.git/config', 'shared/build/output.bin',
                'iosApp/secret.pem', 'scripts/.env', 'gradle/.gradle/cache.bin',
                'iosApp/credentials/token.txt', 'shared/.cache/file',
                '.leaf-upgrade-backup/old/original.txt')
        for name in keep:
            self.put(name, 'VALUE = 1\n' if name.endswith('.py') else 'source\n')
        for name in omit:
            self.put(name, 'not for archive\n')
        self.apply('dist/source.zip')
        with zipfile.ZipFile(self.project / 'dist/source.zip') as archive:
            names = set(archive.namelist())
        self.assertTrue(set(keep) <= names)
        self.assertFalse(set(omit) & names)
        self.assertNotIn('dist/source.zip', names)
        self.assertFalse(any(name.startswith('.leaf-upgrade-backup/') for name in names))

    def test_python_literal_roundtrip_retains_exact_payload_bytes(self):
        values = ['no final newline', 'ends with slash\\', "has ''' and \"\"\" both",
                  "terminal quote'", 'Swift \\(value) \\.title\n😀\r\n']
        for value in values:
            self.assertEqual(ast.literal_eval(packer.literal(value)), value)

    def test_packer_missing_required_files_is_explicit(self):
        with self.assertRaisesRegex(ValueError, 'Missing/linked source tree|Missing required sources'):
            packer.discover_source_files(self.project)


if __name__ == '__main__':
    unittest.main()
