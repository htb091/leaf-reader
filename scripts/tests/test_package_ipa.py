import importlib.util
from pathlib import Path
import plistlib
import stat
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('package_ipa', Path(__file__).resolve().parents[1] / 'package_ipa.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageTests(unittest.TestCase):
    def make_app(self, root):
        app = root / 'LeafReader.app'
        app.mkdir()
        executable = app / 'LeafReader'
        executable.write_bytes(struct.pack('<II', 0xfeedfacf, 0x0100000c) + b'fixture, not a real application')
        executable.chmod(0o755)
        with (app / 'Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleExecutable': 'LeafReader', 'CFBundleSupportedPlatforms': ['iPhoneOS'], 'MinimumOSVersion': '16.0'}, stream)
        return app

    def test_payload_and_executable_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.make_app(root)
            output = module.package(app, root / 'out' / 'reader.ipa')
            with zipfile.ZipFile(output) as archive:
                self.assertIn('Payload/LeafReader.app/Info.plist', archive.namelist())
                entry = archive.getinfo('Payload/LeafReader.app/LeafReader')
                self.assertTrue((entry.external_attr >> 16) & stat.S_IXUSR)
                self.assertIsNone(archive.testzip())
            self.assertTrue(output.with_suffix('.ipa.sha256').is_file())

    def test_rejects_simulator_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.make_app(root)
            with (app / 'Info.plist').open('rb') as stream:
                info = plistlib.load(stream)
            info['CFBundleSupportedPlatforms'] = ['iPhoneSimulator']
            with (app / 'Info.plist').open('wb') as stream:
                plistlib.dump(info, stream)
            with self.assertRaises(ValueError):
                module.package(app, root / 'reader.ipa')

    def test_rejects_missing_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.make_app(root)
            (app / 'LeafReader').rename(app / 'not-the-executable')
            with self.assertRaises(ValueError):
                module.package(app, root / 'reader.ipa')

    def test_rejects_escaping_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.make_app(root)
            (app / 'escape').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                module.package(app, root / 'reader.ipa')

    def test_rejects_output_inside_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.make_app(root)
            with self.assertRaises(ValueError):
                module.package(app, app / 'reader.ipa')


if __name__ == '__main__':
    unittest.main()
