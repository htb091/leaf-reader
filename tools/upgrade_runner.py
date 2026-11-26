#!/usr/bin/env python3
"""Offline LeafReader installer runtime; importable for temporary-project tests.

The packer prepends a literal FILES dictionary and its expected SHA256 map.
Preflight reads/validates EVERY replacement and patch before creating backups or
writing sources. Atomicity is per file; caught apply failures trigger a best-
effort rollback. No network, subprocess, credentials or Git operations are used.
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
import stat
import tempfile
import uuid
import zipfile

INSTALLER_VERSION = globals().get('INSTALLER_VERSION', '0.4')
VERSION_PATCHES = globals().get('VERSION_PATCHES', {
    'MARKETING_VERSION': '0.4.0',
    'CURRENT_PROJECT_VERSION': '4',
})
FILES = globals().get('FILES', {})
EXPECTED_PAYLOAD_SHA256 = globals().get('EXPECTED_PAYLOAD_SHA256', {})
PROJECT_MARKERS = ('settings.gradle.kts', 'iosApp/project.yml')
PATCH_TARGETS = ('iosApp/project.yml', 'shared/build.gradle.kts')
ARCHIVE_DIRS = (
    '.github', 'gradle', 'shared', 'iosApp', 'scripts', 'samples', 'licenses',
    'build-logic', 'tools', 'docs',
)
ARCHIVE_ROOT_FILES = (
    'gradlew', 'gradlew.bat', 'gradle.properties', 'settings.gradle.kts',
    'build.gradle.kts', '.gitignore', '.gitattributes', '.editorconfig',
    'LICENSE', 'NOTICE', 'validation-summary.json',
)
EXCLUDED_DIR_NAMES = {
    'build', '.gradle', '.kotlin', '.git', '__pycache__', '.leaf-upgrade-backup',
    'dist', 'xcuserdata', '.swiftpm', 'DerivedData', '.build', '.idea',
    '.cache', 'cache', 'caches', 'node_modules', '.venv', 'venv',
    'secrets', 'credentials', '.ssh', '.aws', 'backups',
}
EXCLUDED_SUFFIXES = (
    '.ipa', '.pyc', '.pyo', '.zip', '.tmp', '.bak', '.p12', '.pfx', '.pem',
    '.key', '.keystore', '.jks', '.mobileprovision', '.xcuserstate',
)
MIUIX_COORDINATE = 'top.yukonga.miuix.kmp:'


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_relative(rel):
    if (not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel or
            any(ord(char) < 32 or ord(char) == 127 for char in rel)):
        raise ValueError('Unsafe source path: %r' % (rel,))
    parts = rel.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('Unsafe source path: %r' % (rel,))
    pure = PurePosixPath(rel)
    if pure.is_absolute():
        raise ValueError('Absolute source path: %r' % (rel,))
    return pure


def no_symlinks(path):
    """Check the leaf too, including dangling symlinks, without following them."""
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError('Symlink in output/source path: %s' % candidate)


def target_for(project, rel):
    pure = validate_relative(rel)
    target = project.joinpath(*pure.parts)
    no_symlinks(target)
    try:
        target.resolve(strict=False).relative_to(project)
    except ValueError:
        raise ValueError('Target escapes project: %s' % rel)
    if target.exists() and not target.is_file():
        raise ValueError('Expected regular file at %s' % rel)
    for parent in target.parents:
        if parent == project:
            break
        if parent.exists() and not parent.is_dir():
            raise ValueError('Expected source directory at %s' % parent)
    return target


def validate_plist(payload, rel):
    try:
        plistlib.loads(payload)
    except Exception as error:
        raise ValueError('Invalid property list %s: %s' % (rel, error)) from error


def preflight(rel, content):
    data = content.encode('utf-8')
    if rel.endswith('.py'):
        ast.parse(data, filename=rel)
    elif rel.endswith('.json'):
        json.loads(content)
    elif rel.endswith('.plist'):
        validate_plist(data, rel)
    return data


def patch_project_yml(text):
    """Replace exactly two scalar values; preserve ID, comments and line endings."""
    for key, value in VERSION_PATCHES.items():
        pattern = re.compile(
            r'(?m)^([ \t]*' + re.escape(key) + r':[ \t]*)'
            r'("[^"\r\n]*"|\'[^\'\r\n]*\'|[^#\r\n \t]+)'
            r'([ \t]*(?:#[^\r\n]*)?)(\r?)$'
        )
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ValueError('Expected exactly one %s scalar in iosApp/project.yml' % key)
        text = pattern.sub(lambda match: match.group(1) + '"' + value + '"' +
                           match.group(3) + match.group(4), text, count=1)
    return text


def mask_gradle_comments(text):
    """Keep character offsets/newlines while hiding // and nested /* comments.

    Ordinary/triple strings and character literals retain their contents; comment
    markers inside them do not swallow subsequent dependency declarations.
    """
    out = list(text)
    index = 0
    state = 'code'
    depth = 0
    while index < len(text):
        if state == 'line':
            if text[index] in '\r\n':
                state = 'code'
            else:
                out[index] = ' '
            index += 1
        elif state == 'block':
            if text.startswith('/*', index):
                out[index:index + 2] = '  '
                depth += 1
                index += 2
            elif text.startswith('*/', index):
                out[index:index + 2] = '  '
                depth -= 1
                index += 2
                if depth == 0:
                    state = 'code'
            else:
                if text[index] not in '\r\n':
                    out[index] = ' '
                index += 1
        elif state == 'triple':
            if text.startswith('"""', index):
                state = 'code'
                index += 3
            else:
                index += 1
        elif state in ('"', "'"):
            if text[index] == '\\':
                index += 2
            elif text[index] == state:
                state = 'code'
                index += 1
            else:
                index += 1
        elif text.startswith('//', index):
            state = 'line'
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('/*', index):
            state = 'block'
            depth = 1
            out[index:index + 2] = '  '
            index += 2
        elif text.startswith('"""', index):
            state = 'triple'
            index += 3
        elif text[index] in ('"', "'"):
            state = text[index]
            index += 1
        else:
            index += 1
    return ''.join(out)


def patch_shared_gradle(text):
    """Insert one pinned blur dependency beside miuix-ui, never replace the file.

    An existing pinned implementation is already satisfied. Ambiguous duplicates,
    conflicting versions and an absent ui anchor fail before any project writes.
    """
    active = mask_gradle_comments(text)
    dependency = re.compile(
        r'(?m)^([ \t]*)implementation[ \t]*\([ \t]*"' +
        re.escape(MIUIX_COORDINATE) +
        r'(miuix-ui|miuix-blur):([^"\r\n]+)"[ \t]*\)'
        r'[ \t]*;?[ \t]*(\r?\n|$)'
    )
    declarations = list(dependency.finditer(active))
    blur = [match for match in declarations if match.group(2) == 'miuix-blur']
    if blur:
        if len(blur) != 1 or blur[0].group(3) != '0.9.4':
            raise ValueError('Existing miuix-blur must be one implementation pinned to 0.9.4')
        return text
    # Detect common incompatible dependency spellings rather than silently adding
    # a second blur line. Catalog aliases are not guessed by this offline patcher.
    if MIUIX_COORDINATE + 'miuix-blur:' in active:
        raise ValueError('Unrecognized miuix-blur declaration; review shared/build.gradle.kts')
    anchors = [match for match in declarations if match.group(2) == 'miuix-ui' and match.group(3) == '0.9.4']
    if len(anchors) != 1:
        raise ValueError('Expected exactly one implementation("%smiuix-ui:0.9.4") anchor' % MIUIX_COORDINATE)
    anchor = anchors[0]
    newline = anchor.group(4) or ('\r\n' if '\r\n' in text else '\n')
    addition = anchor.group(1) + 'implementation("%smiuix-blur:0.9.4")' % MIUIX_COORDINATE + newline
    prefix = text[:anchor.end()]
    if not anchor.group(4):
        prefix += newline
    return prefix + addition + text[anchor.end():]


def excluded_name(name):
    lower = name.lower()
    return (name in EXCLUDED_DIR_NAMES or lower in {'local.properties', '.ds_store'} or
            lower == '.env' or lower.startswith('.env.') or
            any(word in lower for word in ('secret', 'credential', 'signing-key')) or
            lower.endswith(EXCLUDED_SUFFIXES))


def collect_archive_files(project, archive_output=None):
    """Source allowlist only. Prune ignored/symlink directories before traversal."""
    result = set()
    for directory in ARCHIVE_DIRS:
        root = project / directory
        if root.is_symlink() or not root.is_dir():
            continue
        for current, directories, filenames in os.walk(str(root), followlinks=False):
            current = Path(current)
            directories[:] = sorted(name for name in directories if not excluded_name(name)
                                    and not (current / name).is_symlink()
                                    and not name.endswith(('.xcodeproj', '.xcworkspace')))
            for name in sorted(filenames):
                path = current / name
                if excluded_name(name) or path.is_symlink() or not path.is_file():
                    continue
                if archive_output is not None and path.resolve() == archive_output:
                    continue
                result.add(path)
    for path in project.iterdir():
        if path.is_symlink() or not path.is_file() or excluded_name(path.name):
            continue
        if (path.name in ARCHIVE_ROOT_FILES or path.suffix.lower() == '.md' or
                re.fullmatch(r'LeafReader-v[0-9.]+-upgrade\.py', path.name)):
            if archive_output is None or path.resolve() != archive_output:
                result.add(path)
    return sorted(result)


def atomic_write(target, payload, mode=0o644):
    no_symlinks(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix='.leaf-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        no_symlinks(target)
        os.replace(temporary, str(target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode('utf-8') + b'\n')


def archive_destination(project, argument):
    output = Path(argument).expanduser()
    if not output.is_absolute():
        output = project / output
    # Reject user traversal spellings too, before resolve normalizes them.
    if '..' in output.parts:
        raise ValueError('Archive path contains traversal')
    no_symlinks(output)
    output = output.resolve(strict=False)
    if output.suffix.lower() != '.zip':
        raise ValueError('--archive must end in .zip')
    if output.exists() and not output.is_file():
        raise ValueError('Archive output is not a regular file')
    for ancestor in output.parents:
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError('Archive parent is not a directory: %s' % ancestor)
    try:
        relative = output.relative_to(project)
    except ValueError:
        relative = None
    if relative and any(part in EXCLUDED_DIR_NAMES - {'dist'} for part in relative.parts[:-1]):
        raise ValueError('Archive output inside a cache/backup directory')
    return output


def write_archive(project, output):
    files = collect_archive_files(project, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(output.parent), prefix='.leaf-archive-', suffix='.tmp')
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                no_symlinks(path)
                archive.write(path, path.relative_to(project).as_posix())
        no_symlinks(output)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return files


def prepare_upgrade(project, archive_path=None):
    """Read-only phase. No mkdir, temporary file, backup or replacement here."""
    for marker in PROJECT_MARKERS:
        if not target_for(project, marker).is_file():
            raise ValueError('Missing LeafReader project marker: %s' % marker)
    if not FILES:
        raise ValueError('No embedded files; run tools/make_upgrade.py to create an installer')
    if any(rel in FILES for rel in PATCH_TARGETS):
        raise ValueError('Patch-only targets must not be embedded as full replacements')
    if EXPECTED_PAYLOAD_SHA256 and set(EXPECTED_PAYLOAD_SHA256) != set(FILES):
        raise ValueError('Payload SHA map does not match FILES')
    prepared = {}
    for rel, text in sorted(FILES.items()):
        target_for(project, rel)
        payload = preflight(rel, text)
        expected = EXPECTED_PAYLOAD_SHA256.get(rel)
        if expected and sha256_bytes(payload) != expected:
            raise ValueError('Embedded payload SHA mismatch: %s' % rel)
        prepared[rel] = payload
    patches = (
        ('iosApp/project.yml', patch_project_yml),
        ('shared/build.gradle.kts', patch_shared_gradle),
    )
    for rel, patch in patches:
        target = target_for(project, rel)
        if not target.is_file():
            raise ValueError('Missing patch target: %s' % rel)
        original = target.read_bytes()
        prepared[rel] = patch(original.decode('utf-8')).encode('utf-8')
    # Validate all source Python and XML/binary property lists, without executing
    # Python or invoking a compiler. Generated/cache/secret trees are not scanned.
    checked = {'python': [], 'plist': []}
    for path in collect_archive_files(project, archive_path):
        rel = path.relative_to(project).as_posix()
        payload = prepared.get(rel)
        if path.suffix not in ('.py', '.plist'):
            continue
        if payload is None:
            payload = path.read_bytes()
        if path.suffix == '.py':
            ast.parse(payload, filename=rel)
            checked['python'].append(rel)
        else:
            validate_plist(payload, rel)
            checked['plist'].append(rel)
    entries = []
    for rel, payload in sorted(prepared.items()):
        target = target_for(project, rel)
        if archive_path is not None and target.resolve(strict=False) == archive_path:
            raise ValueError('Archive collides with source target')
        before = target.read_bytes() if target.is_file() else None
        mode = stat.S_IMODE(target.stat().st_mode) if before is not None else (0o755 if rel.endswith('.sh') else 0o644)
        entries.append({'path': rel, 'target': target, 'before': before, 'after': payload, 'mode': mode})
    # Preflight backup path as well; no writes through a user-supplied symlink.
    backup_parent = project / '.leaf-upgrade-backup'
    no_symlinks(backup_parent)
    if backup_parent.exists() and not backup_parent.is_dir():
        raise ValueError('Backup root is not a directory')
    return entries, checked


def apply_upgrade(project, entries, checked):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup_root = project / '.leaf-upgrade-backup' / (timestamp + '-' + uuid.uuid4().hex[:8])
    manifest = {
        'tool': 'LeafReader-v%s-upgrade' % INSTALLER_VERSION,
        'applied_at_utc': timestamp, 'file_count': len(FILES), 'status': 'prepared',
        'verification': checked, 'changes': [],
        'note': 'Only version scalars and the missing pinned blur dependency are patched in build configuration.',
    }
    # All originals are backed up before replacing even the first source.
    for entry in entries:
        rel, before, after = entry['path'], entry['before'], entry['after']
        if before is not None and before != after:
            destination = backup_root / 'files' / rel
            atomic_write(destination, before, entry['mode'])
        manifest['changes'].append({
            'path': rel, 'existed': before is not None, 'unchanged': before == after,
            'sha256_before': sha256_bytes(before) if before is not None else None,
            'sha256_after': sha256_bytes(after), 'bytes': len(after),
            'backup': 'files/' + rel if before is not None and before != after else None,
        })
    manifest_path = backup_root / 'change-manifest.json'
    write_json(manifest_path, manifest)
    payload_sha = {rel: sha256_bytes(text.encode('utf-8')) for rel, text in sorted(FILES.items())}
    write_json(backup_root / 'payload-sha256.json', payload_sha)
    applied = []
    try:
        for entry in entries:
            target = target_for(project, entry['path'])
            current = target.read_bytes() if target.is_file() else None
            if current != entry['before']:
                raise ValueError('Source changed since preflight: %s' % entry['path'])
            if current != entry['after']:
                atomic_write(target, entry['after'], entry['mode'])
                applied.append(entry)
            if target.read_bytes() != entry['after']:
                raise ValueError('Post-write verification failed: %s' % entry['path'])
        manifest['status'] = 'applied'
        write_json(manifest_path, manifest)
    except BaseException:
        failures = []
        for entry in reversed(applied):
            try:
                target = target_for(project, entry['path'])
                if entry['before'] is None:
                    target.unlink()
                else:
                    atomic_write(target, entry['before'], entry['mode'])
            except (OSError, ValueError) as error:
                failures.append('%s: %s' % (entry['path'], error))
        manifest['status'] = 'rollback-incomplete' if failures else 'rolled-back'
        manifest['rollback_errors'] = failures
        write_json(manifest_path, manifest)
        raise
    return backup_root


def main(argv=None):
    parser = argparse.ArgumentParser(description='Apply the offline LeafReader v%s source upgrade.' % INSTALLER_VERSION)
    parser.add_argument('--project', required=True, help='Existing LeafReader repository root')
    parser.add_argument('--archive', help='Optional ZIP path, relative to project unless absolute')
    args = parser.parse_args(argv)
    requested = Path(args.project).expanduser().absolute()
    no_symlinks(requested)
    project = requested.resolve()
    if not project.is_dir():
        raise ValueError('Project directory does not exist: %s' % project)
    archive_path = archive_destination(project, args.archive) if args.archive else None
    entries, checked = prepare_upgrade(project, archive_path)
    backup_root = apply_upgrade(project, entries, checked)
    print('Applied %d embedded files and two scoped configuration patches.' % len(FILES))
    print('Backup/change manifest/payload SHA: %s' % backup_root)
    if archive_path:
        written = write_archive(project, archive_path)
        print('Archive: %s (%d files)' % (archive_path, len(written)))
    print('Kotlin/Swift build, tests and device verification remain CI/device tasks.')
    return 0


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError, plistlib.InvalidFileException) as error:
        raise SystemExit('Upgrade stopped: %s' % error)
