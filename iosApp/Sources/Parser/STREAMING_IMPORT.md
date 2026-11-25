# Native file import (schema 2)

`DocumentPicker` uses `BookParser.parseFileToManifest(at:)`, then calls
`ReaderRuntime.shared.importManifest(json:)` on the main queue. The bridge carries
only the chapter index, never all chapter text. `parse(data:filename:)` and the
deprecated `parseFile(at:)` remain small-book/fixture compatibility APIs with their
original in-memory limits; they are not used for user-selected imports.

## Transaction and storage

- SHA256 is computed incrementally over original bytes, including any BOM.
- TXT: first bounded pass hashes and validates UTF-8 to select the encoding;
  second pass incrementally decodes and writes chapters. A second hash confirms
  that the source has not changed. No full decoded String is constructed.
- EPUB: hash, bounded file-based ZIP preflight, ZIPFoundation `Archive(url:)`,
  bounded extraction of each selected XHTML, then a final source hash check.
  Assets are not extracted. No archive-sized Data preflight is used.
- Chapters are atomically written under Application Support/LeafReader as
  `book-{sha256}-{lowercaseUUIDWithoutDashes}-c{index}.json`.
- Native code never writes the canonical manifest. Kotlin validates the completed
  index and publishes it together with the shelf entry.
- On native failure, only the exact chapter paths successfully written by this
  writer/revision are removed. Source files, earlier revisions and canonical
  manifests are left untouched. Kotlin validation failures and process death can
  leave unreferenced revision files; storage-layer cleanup owns that lifecycle.

## Limits and memory envelope

- Original TXT: 512 MiB; original EPUB: 1 GiB, inclusive.
- Byte reads: at most 64 KiB; incomplete decoder carry: at most 3 bytes.
- Paragraphs: at most 2000 UTF-16 units, split on Unicode scalar boundaries.
- Stored chapter text: at most 256 Ki UTF-16 units AND 512 KiB raw paragraph UTF-8.
  The byte target is **text**, not the physical JSON file: delimiters, escaped
  quotes/backslashes and many tiny paragraphs can make chapter JSON around
  1–1.25 MiB. The shared reader's 4 Mi-character JSON envelope covers that.
- Whole-book index: at most 50,000 chapters and 2,000,000 paragraphs. Counts are
  exact; characterCount excludes chapter titles and counts UTF-16 paragraph units.
- EPUB: 50,000 ZIP entries; per-entry expansion at most 64 MiB; aggregate declared
  expansion at most 2 GiB; compression ratio at most 200:1; central/local header
  metadata together at most 32 MiB. These also bound retained ZIPFoundation Entry
  extras/comments. Preflight reads an EOCD tail of at most 65,557 bytes and one
  bounded central/local header/name/extra field at a time.
- One XHTML at a time, at most 8 MiB uncompressed; metadata XML at most 1 MiB.
  SwiftSoup, validation markup and paragraphs are document-scoped, not book-scoped.
  Foundation temporaries are drained per byte chunk/document. One XHTML may
  produce multiple stored chapters; an XHTML larger than 8 MiB is rejected rather
  than parsed unboundedly.
- Existing per-document markup depth 128, node budget 100,000 and entity budget
  100,000 remain in force. Large indexes/metadata have a bounded but nonconstant
  cost within their explicit entry/chapter ceilings.

## Encoding and compatibility

UTF-8 (optional BOM), UTF-16 LE/BE with BOM, and GB18030 are supported for TXT.
Without a BOM, a full-file bounded UTF-8 validation pass precedes GB18030 fallback;
this handles a late non-UTF8 byte without guessing from only the first buffer.
GB18030 decoding uses Foundation's GB_18030_2000 converter on strictly framed
1/2/4-byte units. Invalid/unavailable conversions fail explicitly. Strict UTF-8
decoding rejects malformed sequences; a no-BOM file can instead be valid GB18030.
UTF-32, stray/truncated UTF-16 surrogates and incomplete final sequences in the
selected encoding are rejected. A UTF-8 BOM is authoritative and is not silently
reinterpreted as GB18030.

Long physical TXT lines are fragmented before a chapter buffer grows. Fragments
are never independently recognized as chapter headings. Consecutive actual short
headings remain empty chapters; books with no TOC/headings get bounded sequential
chapters. Paragraph normalization trims boundary whitespace and skips low control
characters, as the legacy parser does; it is not a byte-for-byte text exporter.

EPUB imports retain metadata/spine order and finite built-in named entities;
external DTD/entity resolution and remote resources are never loaded. Images,
CSS, script, audio/video, SVG and other non-text content are omitted. ZIP64,
multi-volume archives, encrypted/DRM entries, symlinks, unsafe/duplicate paths,
unsupported ZIP flags/methods, unsigned data descriptors, fixed layout, non-text
spines and non-XML HTML are outside this text importer. This is not full Legado
EPUB/rendering compatibility. Large asset-heavy EPUBs work subject to the limits
above; raising the original-file ceiling does not remove archive-bomb limits.

## Tests

`StreamingImportTests.swift` adds strict multibyte tests at every 1–7-byte chunk
size (UTF8/UTF16/GB18030), one-byte BOM/file reads, late GB fallback across the
64KiB boundary, file-size rejection with sparse fixtures, schema/id/revision and
atomic chapter publication checks, independent reimports, long-line heading
regression, failure rollback isolation, a generated >32MiB no-TOC TXT, a URL-backed
EPUB with a >32MiB unused asset and a split logical chapter, malformed stored-entry
size, CRC and bomb checks.
The existing BookParserTests fixtures remain supported.

These tests and Swift compilation have **not been run in the current Android /
Ubuntu session**: its shell/glob executors return ENOENT and no Xcode/Swift test
runner was available through the permitted tools. Source was statically reviewed;
run the ParserTests scheme on a macOS/Xcode runner before release. No claimed
512MiB/1GiB end-to-end device performance measurement has been made.
