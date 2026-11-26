"""0.5.1 release packing regression tests; all installers/projects are temp fixtures.

No production release artifact is emitted. Apple compilation and gesture/device
verification are deliberately outside these Python packaging tests.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load_module('leaf_v051_fixture_helpers', ROOT / 'scripts/tests/test_upgrade_v05.py')
packer = load_module('leaf_v051_packer', ROOT / 'tools/make_upgrade.py')
CROSS_SOURCE_FILES = (
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/FixtureReduceMotion.kt',
    'shared/src/iosMain/kotlin/dev/leaf/reader/ui/FixtureReduceMotion.ios.kt',
    'shared/src/desktopMain/kotlin/dev/leaf/reader/ui/FixtureReduceMotion.desktop.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/FixtureReduceMotionTest.kt',
    'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/FixtureReduceMotionHostTest.kt',
    'shared/src/iosTest/kotlin/dev/leaf/reader/ui/FixtureReduceMotionNativeTest.kt',
)
REQUIRED_AUDIT_FILES = (
    'shared/src/commonMain/kotlin/dev/leaf/reader/ReduceMotion.kt',
    'shared/src/iosMain/kotlin/dev/leaf/reader/ReduceMotion.ios.kt',
    'shared/src/desktopMain/kotlin/dev/leaf/reader/ReduceMotion.desktop.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ReduceMotionTest.kt',
    'shared/src/desktopTest/kotlin/dev/leaf/reader/ReduceMotionDesktopTest.kt',
    'shared/src/iosTest/kotlin/dev/leaf/reader/ReduceMotionIosTest.kt',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderGestureContractTest.kt',
)


class UpgradeV051Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.UpgradeV05Tests('test_configurable_materials_are_adjacent_preserving_user_config')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.project = self.fixture.project

    def source_fixture(self):
        names = self.fixture.source_fixture('0.5.1')
        for name in CROSS_SOURCE_FILES:
            self.fixture.put(name, '// exact cross-source-set fixture\n')
        return names

    @staticmethod
    def literal_assignments(source):
        tree = ast.parse(source)
        return {target.id: ast.literal_eval(node.value)
                for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name) and
                isinstance(node.value, (ast.Constant, ast.Dict, ast.Tuple))}

    def test_version_051_defaults_to_build_six_and_accepts_higher(self):
        self.source_fixture()
        for build, expected in ((None, '6'), (7, '7'), (42, '42')):
            source, _ = packer.assemble_installer(self.project, '0.5.1', build)
            values = self.literal_assignments(source)
            self.assertEqual(values['INSTALLER_VERSION'], '0.5.1')
            self.assertEqual(values['VERSION_PATCHES'], {'MARKETING_VERSION': '0.5.1', 'CURRENT_PROJECT_VERSION': expected})
            self.assertEqual(values['REQUIRED_MATERIAL_DEPENDENCIES'], (legacy.BLUR,))

    def test_build_below_six_is_rejected_before_emitting_anything(self):
        before = self.fixture.snapshot()
        for build in (0, 1, 5, -1):
            with self.assertRaises(ValueError):
                packer.assemble_installer(self.project, '0.5.1', build)
        self.assertEqual(self.fixture.snapshot(), before)

    def test_all_platform_sources_and_tests_are_discovered_and_roundtrip(self):
        self.source_fixture()
        source, hashes = packer.assemble_installer(self.project, '0.5.1')
        payload = self.literal_assignments(source)['FILES']
        for name in CROSS_SOURCE_FILES + REQUIRED_AUDIT_FILES:
            self.assertIn(name, hashes)
            self.assertEqual(payload[name].encode(), (self.project / name).read_bytes())
        self.assertIn('scripts/tests/test_upgrade_v05.py', payload)
        self.assertIn('scripts/tests/test_upgrade_v051.py', payload)
        self.assertIn('UPGRADE-v0.5.1.md', payload)
        self.assertIn('.github/workflows/upgrade-v051.yml', payload)

    def test_missing_critical_051_source_stops_packing_instead_of_omitting(self):
        self.source_fixture()
        critical = 'shared/src/desktopMain/kotlin/dev/leaf/reader/ui/RequiredPlatformFixture.kt'
        with mock.patch.object(packer, 'REQUIRED_V051_SOURCE_FILES', [critical]):
            with self.assertRaisesRegex(ValueError, 'RequiredPlatformFixture'):
                packer.discover_source_files(self.project, '0.5.1')

    def test_each_audit_counterpart_and_gesture_regression_is_mandatory(self):
        self.source_fixture()
        self.assertTrue(set(REQUIRED_AUDIT_FILES) <= set(packer.REQUIRED_V051_SOURCE_FILES))
        for name in REQUIRED_AUDIT_FILES:
            path = self.project / name
            content = path.read_bytes()
            path.unlink()
            try:
                with self.assertRaisesRegex(ValueError, 'Missing required sources'):
                    packer.discover_source_files(self.project, '0.5.1')
            finally:
                path.write_bytes(content)

    def test_older_v04_v05_profiles_keep_their_version_build_defaults(self):
        self.source_fixture()
        for version, marketing, build in (('0.4', '0.4.0', '4'), ('0.5', '0.5.0', '5')):
            source, _ = packer.assemble_installer(self.project, version)
            self.assertEqual(self.literal_assignments(source)['VERSION_PATCHES'],
                             {'MARKETING_VERSION': marketing, 'CURRENT_PROJECT_VERSION': build})

    def generated_runtime(self):
        self.source_fixture()
        source, hashes = packer.assemble_installer(self.project, '0.5.1')
        namespace = {'__name__': 'local_v051_fixture_not_main'}
        exec(compile(source, '<local-v051-fixture>', 'exec'), namespace)
        self.assertEqual(namespace['EXPECTED_PAYLOAD_SHA256'], hashes)
        return namespace

    def old_project(self):
        target = self.project.parent / 'old-project'
        target.mkdir()
        files = {
            'settings.gradle.kts': 'rootProject.name = "ExistingReader"\n',
            'shared/build.gradle.kts': legacy.BUILD,
            'iosApp/project.yml': legacy.YML,
            'iosApp/Info.plist': plistlib.dumps({'CFBundleIdentifier': 'user.existing.leaf'}),
            'gradle/wrapper/gradle-wrapper.properties': 'distributionUrl=preserve-custom-mirror\n',
            'user-data/settings.json': '{"fontSize":27,"lastBook":"keep"}\n',
        }
        for name, content in files.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return target

    def test_installer_applies_to_old_repo_preserves_settings_and_zips_platform_files(self):
        namespace = self.generated_runtime()
        target = self.old_project()
        with contextlib.redirect_stdout(io.StringIO()):
            namespace['main'](['--project', str(target), '--archive', 'dist/fixture-source.zip'])
            namespace['main'](['--project', str(target)])
        yml = (target / 'iosApp/project.yml').read_text()
        self.assertEqual(yml, legacy.YML.replace('"0.1.0"', '"0.5.1"').replace('"1"', '"6"'))
        self.assertEqual((target / 'shared/build.gradle.kts').read_text().count(legacy.BLUR), 1)
        self.assertEqual((target / 'user-data/settings.json').read_text(), '{"fontSize":27,"lastBook":"keep"}\n')
        self.assertIn('preserve-custom-mirror', (target / 'gradle/wrapper/gradle-wrapper.properties').read_text())
        with zipfile.ZipFile(target / 'dist/fixture-source.zip') as archive:
            for name in CROSS_SOURCE_FILES + REQUIRED_AUDIT_FILES:
                self.assertEqual(archive.read(name), (self.project / name).read_bytes())
            self.assertIn('tools/upgrade_runner.py', archive.namelist())
            self.assertIn('scripts/tests/test_upgrade_v051.py', archive.namelist())
            self.assertNotIn('user-data/settings.json', archive.namelist())
            self.assertFalse(any(name.startswith('.leaf-upgrade-backup/') for name in archive.namelist()))
        manifests = sorted((target / '.leaf-upgrade-backup').glob('*/change-manifest.json'))
        self.assertEqual(len(manifests), 2)
        self.assertTrue(all(item['unchanged'] for item in json.loads(manifests[-1].read_text())['changes']))

    def test_missing_anchor_is_all_or_nothing_in_generated_051_installer(self):
        namespace = self.generated_runtime()
        target = self.old_project()
        (target / 'shared/build.gradle.kts').write_text('// no matching dependency\n')
        before = {path.relative_to(target).as_posix(): path.read_bytes()
                  for path in target.rglob('*') if path.is_file()}
        with self.assertRaisesRegex(ValueError, 'anchor'):
            namespace['main'](['--project', str(target)])
        after = {path.relative_to(target).as_posix(): path.read_bytes()
                 for path in target.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((target / '.leaf-upgrade-backup').exists())

    def test_workflow_uploads_source_before_tests_and_ipa_before_swift(self):
        text = (ROOT / '.github/workflows/upgrade-v051.yml').read_text()
        source = text.index('name: Upload complete upgraded source')
        scripts = text.index('name: Verify project scripts')
        kotlin = text.index('name: Compile shared UI')
        build = text.index('name: Build and package device IPA')
        ipa = text.index('name: Upload IPA before native')
        swift = text.index('name: Run native streaming importer tests')
        self.assertEqual([source, scripts, kotlin, build, ipa, swift], sorted([source, scripts, kotlin, build, ipa, swift]))
        self.assertIn('LeafReader-v0.5.1-upgrade.py', text)
        self.assertIn('persist-credentials: false', text)

    def test_native_simulator_tests_are_arch_gated_and_after_ipa_upload(self):
        text = (ROOT / '.github/workflows/upgrade-v051.yml').read_text()
        native = text.index('name: Run Kotlin Native reduced-motion simulator tests')
        self.assertLess(text.index('name: Upload IPA before native'), native)
        self.assertLess(text.index('name: Run native streaming importer tests'), native)
        self.assertLess(native, text.index('name: Upload all test reports'))
        self.assertIn("steps.upload_ipa.outcome == 'success'", text)
        self.assertIn('always() && !cancelled()', text)
        self.assertIn('"$(uname -m)" != arm64', text)
        self.assertIn('no available iPhone simulator/runtime', text)
        self.assertIn('task.device.set', text)
        self.assertIn(':shared:iosSimulatorArm64Test -PenableApple=true', text)
        self.assertIn('timeout-minutes: 30', text)
        self.assertNotIn('continue-on-error: true', text)


if __name__ == '__main__':
    unittest.main()
