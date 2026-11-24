# LeafReader iOS host

Original Swift host and generated test fixtures for the project contract. No Legado code or book content is copied.

## Build requirements

- macOS with the Xcode version supported by the pinned Kotlin/Native toolchain (the root workflow selects macOS 26 / Xcode 26.4; project language mode is Swift 5), selected via DEVELOPER_DIR or xcode-select, accepted Xcode license, iOS SDK, and an installed simulator runtime for tests. The iOS16 deployment target does not imply that an old Xcode can compile the shared framework.
- XcodeGen **2.38.0+** (`brew install xcodegen`). No Gradle script/build phase is generated in the Xcode project.
- Shared must already be built as the **static iOS ARM64 release framework**, at `../shared/build/bin/iosArm64/releaseFramework/Shared.framework` relative to this folder. Lead/CI owns generating it, e.g. `./gradlew :shared:linkReleaseFrameworkIosArm64` from project root.
- App target/scheme **LeafReader**, bundle identifier `dev.leaf.reader`, iOS deployment target **16.0**, iPhone/iPad, device-only. The framework is linked with `embed: false`; never add it to Embed Frameworks.
- First SPM resolution requires network access. Both package versions are exact, released, non-prerelease pins, verified from upstream release APIs and tagged manifests:
  - [ZIPFoundation 0.9.19 release](https://github.com/weichsel/ZIPFoundation/releases/tag/0.9.19), [tagged Package.swift](https://github.com/weichsel/ZIPFoundation/blob/0.9.19/Package.swift).
  - [SwiftSoup 2.7.7 release](https://github.com/scinfu/SwiftSoup/releases/tag/2.7.7), [tagged Package.swift](https://github.com/scinfu/SwiftSoup/blob/2.7.7/Package.swift).

Run from `iosApp` after building Shared externally:

```sh
xcodegen generate --spec project.yml
xcodebuild -resolvePackageDependencies \
  -project LeafReader.xcodeproj -scheme LeafReader
xcodebuild -project LeafReader.xcodeproj -scheme LeafReader \
  -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
```

The unsigned app is `build/Build/Products/Release-iphoneos/LeafReader.app`. IPA assembly/signing/install and TrollStore device/OS compatibility are Lead responsibilities; this host does not claim a tested IPA. No commit or push is performed.

## Parser tests without a Shared simulator framework

`ParserTests` is a **hostless XCTest bundle** that compiles `Sources/Parser` directly. It does not link Shared, depend on LeafReader, or require an app test host. Its separate scheme is suitable for simulator CI even while the app framework is device-only. Do not substitute scheme LeafReader for simulator testing.

```sh
xcodegen generate --spec project.yml
xcrun simctl list devices available
# Choose an available iOS simulator UDID; CI can select one dynamically.
xcodebuild -project LeafReader.xcodeproj -scheme ParserTests \
  -destination 'platform=iOS Simulator,id=SIMULATOR_UDID' \
  -derivedDataPath build-tests \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO test
```

Fixtures are generated in memory by the test code; no filesystem extraction or downloaded books. Cases cover byte SHA-256/JSON shape, UTF-8/UTF-16 BOM/GB18030, consecutive TXT headings, oversized and pathological single-line/grapheme text, EPUB metadata/spine/nonlinear selection, deflate and signed ZIP32 data descriptors, active-content removal, nested block text, CRC/truncation, encryption/DRM, traversal/remote references, duplicates/symlinks, declared entry/total/ratio/count limits, fixed layout, entities and XML nesting.

## Host and import behavior

- SwiftUI embeds `MainViewControllerKt.MainViewController(onImportRequested:)` through `UIViewControllerRepresentable`. The Kotlin import action opens a `UIDocumentPickerViewController` with TXT/EPUB, **asCopy: true**, multi-select. Files/Open-In uses the same importer.
- A serial user-initiated background queue reads/parses/hashes/encodes one book at a time. Security-scoped access starts in the picker callback and ends after parsing. Up to 16 pending books; autorelease pools bound per-file temporary objects.
- Only on the main queue, call `ReaderRuntime.shared.importBook(json:)` or `ReaderRuntime.shared.reportError(message:)`. Flush on inactive/background. Neither book text nor raw OS/archive errors are logged.
- SHA-256 is computed over the exact original bytes (including BOM/ZIP representation), before decoding.
- TXT: strict BOM-aware UTF-8/UTF-16 LE/BE, then UTF-8, then GB18030. UTF-32/NUL-bearing input is rejected. Chinese/English chapter headings are recognized; consecutive headings survive as empty chapters. Nonempty paragraphs are split at 2,000 UTF-16 units, including pathological single grapheme clusters.
- EPUB: validate ZIP central/local headers, then read only `mimetype`, container XML, OPF, and text spine documents through ZIPFoundation's chunk consumer. Resolve container/OPF references within the archive; never extract paths to disk. OPF title/first creator and primary linear spine order are used; if every spine entry is nonlinear, use that declared order. Duplicate spine references are rejected.
- Text-only XHTML is validated before offline SwiftSoup parsing. Scripts, styles, embedded assets/media/SVG/math are discarded; nothing executes or fetches resources. Block text is traversed once, so nested blocks are not duplicated or dropped. Headings remain in body text to avoid silent content removal (a chapter heading may consequently appear both as its title and first paragraph).

## Limits and deliberate compatibility tradeoffs

| Item | Limit |
| --- | --- |
| Original file | 32 MiB |
| ZIP entry (every entry, including unused assets) | 8 MiB uncompressed |
| All ZIP entries / actual consumed decompression | 64 MiB |
| Archive entries / compression ratio | 4,096 / 200:1 |
| Container / OPF XML | 1 MiB each |
| Readable body UTF-8 | 12 MiB |
| Total imported UTF-16, including metadata/headings | 8 × 1,024 × 1,024 units (Shared contract) |
| Chapters / paragraphs / one paragraph | 2,000 / 50,000 / 2,000 UTF-16 units |
| XML nesting / elements; parsed body nodes | 128 / 100,000; 100,000 |

- **Images and CSS are unsupported**; fixed layout, DRM, any `encryption.xml` (including font obfuscation), rights/license entries, ZIP encryption flags/AES extras, symlinks and unsafe/duplicate archive paths are rejected.
- Narrow ZIP32 support: stored/deflate, UTF-8 names (non-ASCII requires ZIP UTF-8 flag), optional **signed** ZIP32 data descriptors. ZIP64, multi-volume, unsigned/ambiguous data descriptors and excessive compression ratios are intentionally rejected, even for otherwise benign books.
- Content is required to be well-formed UTF-8 or BOM-tagged UTF-16 XHTML. Container/OPF DTDs and all custom entity declarations are rejected. XHTML external doctypes are never resolved. Standard HTML names such as `&nbsp;` are converted, only for XML validation, into numeric references using SwiftSoup's built-in finite table (at most 100,000 references, at most 16 MiB validation output). Original markup is used for text parsing, preserving escaped angle brackets as text. Unknown/custom names and malformed HTML are rejected. No CSS-hidden-text semantics, image alt rendering, cover extraction, NCX/nav TOC, font styling, ruby/MathML/SVG layout, or encoding guessing beyond the stated codecs.
- A book is bounded, but import still holds original bytes, decompressed chapter, DOM, text and JSON temporarily. Older iOS devices may experience memory pressure near limits. JSON persistence on the Kotlin main thread can briefly affect responsiveness; queueing prevents simultaneous large imports.
- File-provider scope, background interruption, real device presentation, Kotlin export header linkage, actual XcodeGen output, Apple compilation and XCTest execution require Apple CI/device verification.

## Original app icon

`Assets.xcassets/AppIcon.appiconset` contains 13 opaque RGB PNGs for all 18 standard iPhone/iPad/marketing slots, including 1024 px marketing art. The open-book/leaf design is generated from original vector geometry; no external artwork or image library. `ASSETCATALOG_COMPILER_APPICON_NAME` is `AppIcon`. To reproduce the assets, run `python3 Tools/generate_app_icon.py` from this folder (Python standard library only).

## Validation performed in the implementation environment

The delegated Linux/Android environment has no Swift compiler, XcodeGen, Apple SDK, or xcodebuild. `Info.plist` was parsed with Python plistlib and `project.yml` with PyYAML; target/package pins/static-link structure were asserted. Dependencies' release status and APIs were checked online. Swift/XCTest has **not been executed here**; no successful Apple build is implied.
