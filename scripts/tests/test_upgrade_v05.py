"""v0.5 packaging tests, using synthetic local source trees and temp projects.

No final release installer is created. Synthetic material coordinates exercise
configuration, not a choice of a production library or API.
"""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
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


runner = load_tool('leaf_upgrade_v05_runtime', 'upgrade_runner.py')
packer = load_tool('leaf_upgrade_v05_packer', 'make_upgrade.py')
UI = 'top.yukonga.miuix.kmp:miuix-ui:0.9.4'
BLUR = 'top.yukonga.miuix.kmp:miuix-blur:0.9.4'
# Deliberately nonexistent fixture coordinate; never a release dependency.
MATERIAL = 'test.material:fixture-surface:1.2.3'
BUILD = ('// user Gradle configuration\n'
         'repositories { maven("https://mirror.invalid/custom") }\n'
         'commonMain.dependencies {\n'
         '    implementation("' + UI + '") // keep this comment\n'
         '    implementation("user:feature:9")\n}\n')
YML = ('settings:\n  base:\n    PRODUCT_BUNDLE_IDENTIFIER: user.existing.leaf\n'
       '    CUSTOM_BUILD_SETTING: "retain"\n'
       '    MARKETING_VERSION: "0.1.0" # keep this comment\n'
       '    CURRENT_PROJECT_VERSION: "1"\n')


class UpgradeV05Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='leaf-v05-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve() / 'project'
        self.project.mkdir()
        self.put('settings.gradle.kts', 'rootProject.name = "Fixture"\n')
        self.put('shared/build.gradle.kts', BUILD)
        self.put('iosApp/project.yml', YML)
        self.put('iosApp/Info.plist', plistlib.dumps({'CFBundleIdentifier': 'user.existing.leaf'}))
        for tree in packer.DISCOVER_TREES:
            (self.project / tree).mkdir(parents=True, exist_ok=True)
        self.patch('INSTALLER_VERSION', '0.5')
        self.patch('VERSION_PATCHES', {'MARKETING_VERSION': '0.5.0', 'CURRENT_PROJECT_VERSION': '5'})
        self.patch('REQUIRED_MATERIAL_DEPENDENCIES', (BLUR, MATERIAL))
        self.patch('FILES', {'README.md': '# v0.5 fixture\n', 'scripts/new.py': 'VALUE = 5\n'})
        self.patch('EXPECTED_PAYLOAD_SHA256', {})

    def patch(self, name, value):
        patcher = mock.patch.object(runner, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def put(self, name, content):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
        return path

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in self.project.rglob('*') if path.is_file()}

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runner.main(['--project', str(self.project)])

    def source_fixture(self, version='0.5'):
        extra, _ = packer.release_profile(version)
        names = set(packer.FILES + packer.REQUIRED_V04_FILES + packer.REQUIRED_DIRECTORY_TESTS + extra)
        for name in names:
            content = '{}\n' if name.endswith('.json') else ('VALUE = 1\n' if name.endswith('.py') else '// fixture\n')
            self.put(name, content)
        self.put('tools/upgrade_runner.py', (ROOT / 'tools/upgrade_runner.py').read_bytes())
        return names

    def test_configurable_materials_are_adjacent_preserving_user_config(self):
        result = runner.patch_shared_gradle(BUILD)
        added = '    implementation("' + BLUR + '")\n    implementation("' + MATERIAL + '")\n'
        self.assertIn(' // keep this comment\n' + added, result)
        self.assertEqual(result.replace(added, '', 1), BUILD)
        self.assertEqual(runner.patch_shared_gradle(result), result)

    def test_existing_blur_adds_only_the_new_material(self):
        existing = BUILD + 'implementation("' + BLUR + '")\n'
        result = runner.patch_shared_gradle(existing)
        self.assertEqual(result.count(BLUR), 1)
        self.assertEqual(result.count(MATERIAL), 1)
        self.assertEqual(result.replace('    implementation("' + MATERIAL + '")\n', '', 1), existing)

    def test_any_material_conflict_prevents_all_project_writes(self):
        self.put('shared/build.gradle.kts', BUILD + 'implementation("' + MATERIAL.replace('1.2.3', '1.0.0') + '")\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'pinned'):
            self.apply()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.project / '.leaf-upgrade-backup').exists())

    def test_example_raw_string_is_not_a_dependency_anchor(self):
        raw = 'val example = """\nimplementation("' + UI + '")\n"""\n'
        with self.assertRaisesRegex(ValueError, 'anchor'):
            runner.patch_shared_gradle(raw)
        real = raw + BUILD
        patched = runner.patch_shared_gradle(real)
        self.assertTrue(patched.startswith(raw))
        self.assertEqual(patched.count(MATERIAL), 1)

    def test_bad_material_specs_or_duplicate_requirements_are_preflight_errors(self):
        for requirements in (('not-a-coordinate',), (BLUR, BLUR), ('group:artifact:1.+',)):
            with self.assertRaises(ValueError):
                runner.patch_shared_gradle(BUILD, requirements)

    def test_all_old_versions_keep_bundle_settings_and_upgrade_idempotently(self):
        for minor in (1, 2, 3, 4):
            original = YML.replace('0.1.0', '0.%d.0' % minor).replace('"1"', '"%d"' % minor)
            self.put('iosApp/project.yml', original)
            self.put('shared/build.gradle.kts', BUILD)
            self.apply()
            self.apply()
            self.assertEqual((self.project / 'iosApp/project.yml').read_text(),
                             original.replace('0.%d.0' % minor, '0.5.0').replace('"%d"' % minor, '"5"'))
            result = (self.project / 'shared/build.gradle.kts').read_text()
            self.assertEqual(result.count(MATERIAL), 1)
            self.assertIn('user:feature:9', result)
        manifests = list((self.project / '.leaf-upgrade-backup').glob('*/change-manifest.json'))
        self.assertEqual(len(manifests), 8)
        manifest = json.loads(sorted(manifests)[-1].read_text())
        self.assertTrue(all(change['unchanged'] for change in manifest['changes']))
        self.assertEqual(manifest['material_dependencies'], [BLUR, MATERIAL])

    def test_profile_retains_v04_and_v05_explicit_payloads(self):
        self.source_fixture('0.5')
        legacy = set(packer.discover_source_files(self.project, '0.4'))
        current = set(packer.discover_source_files(self.project, '0.5'))
        self.assertTrue(legacy <= current)
        self.assertTrue(set(packer.REQUIRED_V05_FILES) <= current)
        self.assertNotIn('shared/build.gradle.kts', current)
        self.assertNotIn('iosApp/project.yml', current)

    def test_dynamic_sources_and_confirmed_critical_files_are_never_omitted(self):
        self.source_fixture()
        new = ('iosApp/Sources/FixtureMaterial.swift',
               'shared/src/commonTest/kotlin/dev/leaf/reader/ui/FixtureMaterialTest.kt',
               'shared/src/desktopTest/kotlin/dev/leaf/reader/ui/FixtureHostTest.kt',
               'shared/src/commonMain/kotlin/dev/leaf/reader/FixtureState.kt')
        for name in new:
            self.put(name, '// new fixture\n')
        self.assertTrue(set(new) <= set(packer.discover_source_files(self.project)))
        critical = 'shared/src/commonMain/kotlin/dev/leaf/reader/ui/LeadConfirmedFixture.kt'
        with mock.patch.object(packer, 'REQUIRED_V05_SOURCE_FILES', [critical]):
            with self.assertRaisesRegex(ValueError, 'LeadConfirmedFixture'):
                packer.discover_source_files(self.project)

    def test_generated_fixture_has_exact_payloads_version_and_material_profile(self):
        self.source_fixture()
        exact = 'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ExactFixture.kt'
        self.put(exact, b'// no trailing newline; backslash \\')
        with mock.patch.object(packer, 'MATERIAL_DEPENDENCIES_V05', (BLUR, MATERIAL)):
            source, hashes = packer.assemble_installer(self.project)
        namespace = {'__name__': 'local_fixture_not_main'}
        # Execute only the locally generated fixture runtime, never downloaded code.
        exec(compile(source, '<local-v05-fixture>', 'exec'), namespace)
        self.assertEqual(namespace['VERSION_PATCHES'], {'MARKETING_VERSION': '0.5.0', 'CURRENT_PROJECT_VERSION': '5'})
        self.assertEqual(namespace['REQUIRED_MATERIAL_DEPENDENCIES'], (BLUR, MATERIAL))
        self.assertEqual(namespace['FILES'][exact].encode(), (self.project / exact).read_bytes())
        self.assertEqual(namespace['EXPECTED_PAYLOAD_SHA256'], hashes)
        for name, text in namespace['FILES'].items():
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), hashes[name])
        with contextlib.redirect_stdout(io.StringIO()):
            namespace['main'](['--project', str(self.project), '--archive', 'dist/fixture.zip'])
            namespace['main'](['--project', str(self.project)])
        self.assertIn('user.existing.leaf', (self.project / 'iosApp/project.yml').read_text())
        with zipfile.ZipFile(self.project / 'dist/fixture.zip') as archive:
            self.assertIn('tools/upgrade_runner.py', archive.namelist())
            self.assertIn('scripts/tests/test_upgrade_v05.py', archive.namelist())
            for name in packer.REQUIRED_V05_SOURCE_FILES:
                self.assertIn(name, archive.namelist())
                self.assertIn(name, namespace['FILES'])
            # Host structure regressions inspect these source paths. Preserve the
            # package layout under shared/src for old repositories and source ZIPs.
            for filename in ('ReaderApp.kt', 'ReaderChrome.kt', 'ReadingScreen.kt'):
                self.assertIn('shared/src/commonMain/kotlin/dev/leaf/reader/ui/' + filename,
                              archive.namelist())
            self.assertIn('UPGRADE-v0.5.md', archive.namelist())
            self.assertFalse(any(name.startswith('.leaf-upgrade-backup/') for name in archive.namelist()))

    def test_v04_generation_still_embeds_v04_version_and_dependency_profile(self):
        self.source_fixture('0.4')
        source, _ = packer.assemble_installer(self.project, '0.4')
        tree = ast.parse(source)
        values = {target.id: ast.literal_eval(node.value)
                  for node in tree.body if isinstance(node, ast.Assign)
                  for target in node.targets if isinstance(target, ast.Name) and
                  target.id in ('VERSION_PATCHES', 'REQUIRED_MATERIAL_DEPENDENCIES') and
                  isinstance(node.value, (ast.Dict, ast.Tuple))}
        self.assertEqual(values['VERSION_PATCHES'], {'MARKETING_VERSION': '0.4.0', 'CURRENT_PROJECT_VERSION': '4'})
        self.assertEqual(values['REQUIRED_MATERIAL_DEPENDENCIES'], packer.MATERIAL_DEPENDENCIES_V04)

    def test_workflow_orders_source_kotlin_ipa_upload_and_swift_tests(self):
        text = (ROOT / '.github/workflows/upgrade-v05.yml').read_text()
        source = text.index('name: Upload complete upgraded source')
        kotlin = text.index('name: Compile shared UI')
        ios = text.index('name: Build and package device IPA')
        ipa = text.index('name: Upload IPA before native')
        swift = text.index('name: Run native streaming importer tests')
        self.assertLess(source, kotlin)
        self.assertLess(kotlin, ios)
        self.assertLess(ios, ipa)
        self.assertLess(ipa, swift)
        self.assertIn('LeafReader-v0.5-upgrade.py', text)
        self.assertIn('persist-credentials: false', text)
        self.assertNotIn('git push', text)


if __name__ == '__main__':
    unittest.main()
