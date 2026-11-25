}

VERSION_PATCHES = {
    'MARKETING_VERSION': '0.2.0',
    'CURRENT_PROJECT_VERSION': '2',
}
PROJECT_MARKERS = ('settings.gradle.kts', 'iosApp/project.yml')
ARCHIVE_DIRS = ('.github', 'gradle', 'shared', 'iosApp', 'scripts', 'samples', 'licenses', 'build-logic')
ARCHIVE_ROOT_FILES = (
    'gradlew', 'gradlew.bat', 'gradle.properties', 'settings.gradle.kts', 'build.gradle.kts',
    '.gitignore', '.gitattributes', 'README.md', 'VALIDATION.md', 'UPGRADE-v0.2.md', 'UPGRADE-v0.3.md',
    'THIRD_PARTY_NOTICES.md', 'LICENSE', 'validation-summary.json',
)
EXCLUDED_DIR_NAMES = {'build', '.gradle', '.kotlin', '.git', '__pycache__', '.leaf-upgrade-backup', 'dist', 'xcuserdata', '.swiftpm', 'DerivedData'}
EXCLUDED_SUFFIXES = ('.ipa', '.pyc')


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_relative(rel):
    if not rel or '\\' in rel or ':' in rel:
        raise SystemExit('Unsafe embedded path: %r' % (rel,))
    pure = PurePosixPath(rel)
    if pure.is_absolute() or any(part in ('', '.', '..') for part in pure.parts):
        raise SystemExit('Unsafe embedded path: %r' % (rel,))
    return pure


def target_for(project, rel):
    pure = validate_relative(rel)
    target = project.joinpath(*pure.parts)
    parent = target.parent
    for ancestor in [parent, *parent.parents]:
        if ancestor.exists() and ancestor.is_symlink():
            raise SystemExit('Refusing to write through symlink: %s' % ancestor)
        if ancestor == project.parent:
            break
    resolved = target.resolve(strict=False)
    project_resolved = project.resolve()
    try:
        resolved.relative_to(project_resolved)
    except ValueError:
        raise SystemExit('Target escapes project: %s' % rel)
    return target


def preflight(rel, content):
    data = content.encode('utf-8')
    if rel.endswith('.py'):
        ast.parse(content, filename=rel)
    elif rel.endswith('.json'):
        json.loads(content)
    elif rel.endswith('Info.plist'):
        plistlib.loads(data)
    return data


def backup_copy(project, backup_root, target):
    if not target.exists():
        return
    relative = target.relative_to(project)
    destination = backup_root.joinpath(*relative.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'rb') as source, open(destination, 'wb') as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def atomic_write(target, payload):
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix='.leaf-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def patch_project_yml(text):
    text, marketing = re.subn(r'MARKETING_VERSION:\s*"[^"]*"', 'MARKETING_VERSION: "%s"' % VERSION_PATCHES['MARKETING_VERSION'], text, count=1)
    text, current = re.subn(r'CURRENT_PROJECT_VERSION:\s*"[^"]*"', 'CURRENT_PROJECT_VERSION: "%s"' % VERSION_PATCHES['CURRENT_PROJECT_VERSION'], text, count=1)
    if marketing != 1 or current != 1:
        raise SystemExit('iosApp/project.yml is missing MARKETING_VERSION or CURRENT_PROJECT_VERSION; refusing a partial version patch.')
    return text


def collect_archive_files(project, archive_output):
    files = []
    for directory in ARCHIVE_DIRS:
        root = project.joinpath(*PurePosixPath(directory).parts)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(project)
            if any(part in EXCLUDED_DIR_NAMES for part in relative.parts):
                continue
            if path.suffix in EXCLUDED_SUFFIXES:
                continue
            if archive_output is not None and path.resolve() == archive_output:
                continue
            files.append(path)
    for name in ARCHIVE_ROOT_FILES:
        path = project / name
        if path.is_file() and not path.is_symlink():
            files.append(path)
    return files


def write_archive(project, archive_path):
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    files = collect_archive_files(project, archive_path.resolve())
    temporary = archive_path.with_suffix(archive_path.suffix + '.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(project).as_posix())
    os.replace(temporary, archive_path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description='Apply the frozen LeafReader v0.2 source upgrade.')
    parser.add_argument('--project', required=True, help='Existing LeafReader repository root')
    parser.add_argument('--archive', help='Optional path for a ZIP of the upgraded whitelisted sources')
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        raise SystemExit('Project directory does not exist: %s' % project)
    for marker in PROJECT_MARKERS:
        if not project.joinpath(*PurePosixPath(marker).parts).is_file():
            raise SystemExit('Missing project marker %s; run from the LeafReader repository root.' % marker)

    prepared = {}
    for rel in sorted(FILES):
        prepared[rel] = preflight(rel, FILES[rel])

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_root = project / '.leaf-upgrade-backup' / timestamp
    changes = []

    for rel in sorted(prepared):
        target = target_for(project, rel)
        payload = prepared[rel]
        before = target.read_bytes() if target.is_file() else None
        backup_copy(project, backup_root, target)
        atomic_write(target, payload)
        changes.append({
            'path': rel,
            'existed': before is not None,
            'sha256_before': sha256_bytes(before) if before is not None else None,
            'sha256_after': sha256_bytes(payload),
            'bytes': len(payload),
            'unchanged': before == payload,
        })
        print('OK %s (%s)' % (rel, 'unchanged' if before == payload else 'updated'))

    project_yml = project / 'iosApp' / 'project.yml'
    original = project_yml.read_text(encoding='utf-8')
    patched = patch_project_yml(original)
    backup_copy(project, backup_root, project_yml)
    atomic_write(project_yml, patched.encode('utf-8'))
    changes.append({
        'path': 'iosApp/project.yml',
        'existed': True,
        'sha256_before': sha256_bytes(original.encode('utf-8')),
        'sha256_after': sha256_bytes(patched.encode('utf-8')),
        'bytes': len(patched.encode('utf-8')),
        'unchanged': original == patched,
        'note': 'version scalars patched only; bundle id and build settings preserved',
    })
    print('OK iosApp/project.yml (%s)' % ('unchanged' if original == patched else 'version patched'))

    manifest = {
        'tool': 'LeafReader-v0.2-upgrade',
        'applied_at_utc': timestamp,
        'project': str(project),
        'file_count': len(FILES),
        'changes': changes,
    }
    manifest_path = backup_root / 'change-manifest.json'
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    print('Backup and manifest: %s' % backup_root)

    for rel in sorted(prepared):
        print('payload_sha256 %s %s' % (rel, sha256_bytes(prepared[rel])))

    if args.archive:
        archive_path = Path(args.archive)
        written = write_archive(project, archive_path)
        print('Archive: %s (%d files, %d bytes)' % (archive_path, len(written), archive_path.stat().st_size))
    print('Upgrade applied. Compile and run tests in CI; this tool does not build or install the app.')


if __name__ == '__main__':
    main()

