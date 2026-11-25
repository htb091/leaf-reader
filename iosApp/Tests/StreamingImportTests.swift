import XCTest
import Foundation
import ZIPFoundation

final class StreamingImportTests: XCTestCase {
    private let parser = BookParser()

    private func workspace() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    private func manifest(_ source: URL, _ root: URL, readSize: Int = 64 * 1_024) throws -> ImportedManifest {
        let json = try parser.parseFileToManifest(at: source, storageRoot: root, readSize: readSize)
        return try JSONDecoder().decode(ImportedManifest.self, from: Data(json.utf8))
    }

    private func chapter(_ entry: ImportedChapterEntry, in root: URL) throws -> ImportedChapter {
        // Tests load just one bounded chapter, as the shared storage layer does.
        try JSONDecoder().decode(ImportedChapter.self, from: Data(contentsOf: root.appendingPathComponent(entry.fileName)))
    }

    func testMultibyteDecoderAtEveryByteBoundary() throws {
        let text = "甲😀乙𠀀€文"
        let variants: [(IncrementalTextDecoder.Encoding, Data)] = [
            (.utf8, Data(text.utf8)),
            (.utf16LE, try XCTUnwrap(text.data(using: .utf16LittleEndian))),
            (.utf16BE, try XCTUnwrap(text.data(using: .utf16BigEndian))),
            // U+0080 uses a four-byte GB18030 sequence, beside two-byte Chinese.
            (.gb18030, Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30, 0xce, 0xc4]))
        ]
        for (encoding, bytes) in variants {
            let expected = encoding == .gb18030 ? "中\u{0080}文" : text
            for size in 1...7 {
                var decoder = IncrementalTextDecoder(encoding: encoding)
                var output = ""
                var offset = 0
                while offset < bytes.count {
                    let end = min(offset + size, bytes.count)
                    output += try decoder.decode(bytes.subdata(in: offset..<end))
                    offset = end
                }
                output += try decoder.decode(Data(), final: true)
                XCTAssertEqual(output, expected)
            }
        }
    }

    func testStrictDecoderRejectsTruncationOverlongAndStraySurrogates() {
        let cases: [(IncrementalTextDecoder.Encoding, [UInt8])] = [
            (.utf8, [0xf0, 0x9f, 0x98]), (.utf8, [0xc0, 0xaf]),
            (.utf8, [0xed, 0xa0, 0x80]), (.utf8, [0xf4, 0x90, 0x80, 0x80]),
            (.utf16LE, [0x00, 0xd8]), (.utf16BE, [0xdc, 0x00]),
            (.utf16LE, [0x41]), (.gb18030, [0x81, 0x30, 0x81]),
            (.gb18030, [0x81, 0x30, 0x40, 0x30])
        ]
        for (encoding, bytes) in cases {
            XCTAssertThrowsError(try {
                var decoder = IncrementalTextDecoder(encoding: encoding)
                for byte in bytes { _ = try decoder.decode(Data([byte])) }
                _ = try decoder.decode(Data(), final: true)
            }())
        }
    }

    func testFileBOMAndGBFallbackWithOneByteReads() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let variants: [(Data, String)] = [
            (Data([0xef, 0xbb, 0xbf]) + Data("甲😀乙".utf8), "甲😀乙"),
            (Data([0xff, 0xfe]) + "甲😀乙".data(using: .utf16LittleEndian)!, "甲😀乙"),
            (Data([0xfe, 0xff]) + "甲😀乙".data(using: .utf16BigEndian)!, "甲😀乙"),
            (Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30, 0xce, 0xc4]), "中\u{0080}文")
        ]
        for (index, pair) in variants.enumerated() {
            let source = base.appendingPathComponent("\(index).txt")
            let root = base.appendingPathComponent("store-\(index)", isDirectory: true)
            try pair.0.write(to: source)
            let result = try manifest(source, root, readSize: 1)
            XCTAssertEqual(result.chapters.count, 1)
            XCTAssertEqual(try chapter(result.chapters[0], in: root).paragraphs, [pair.1])
            XCTAssertEqual(result.chapters[0].characterCount, pair.1.utf16.count)
        }
    }

    func testLateGB18030FallbackReplaysPrefixAndCarriesBoundaryBytes() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("late-gb.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        let prefix = String(repeating: "a", count: 65_535)
        try (Data(prefix.utf8) + Data([0xd6, 0xd0, 0x81, 0x30, 0x81, 0x30])).write(to: source)
        let result = try manifest(source, root)
        let paragraphs = try result.chapters.flatMap { try chapter($0, in: root).paragraphs }
        XCTAssertEqual(paragraphs.joined(), prefix + "中\u{0080}")
    }

    func testOriginalFileLimitsBeforeAnyPublication() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        for (ext, limit) in [("txt", StreamingImportLimits.txtBytes), ("epub", StreamingImportLimits.epubBytes)] {
            let source = base.appendingPathComponent("oversized.\(ext)")
            let root = base.appendingPathComponent("store-\(ext)", isDirectory: true)
            XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: nil))
            let file = try FileHandle(forWritingTo: source)
            try file.truncate(atOffset: UInt64(limit) + 1) // Sparse fixture; no giant Data.
            try file.close()
            XCTAssertThrowsError(try manifest(source, root))
            XCTAssertFalse(FileManager.default.fileExists(atPath: root.path))
        }
    }

    func testManifestContractAtomicChaptersAndIndependentRevisions() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("Example.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try Data("abc".utf8).write(to: source)
        let first = try manifest(source, root)
        XCTAssertEqual(first.schema, 2)
        XCTAssertEqual(first.id, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        XCTAssertEqual(first.title, "Example")
        XCTAssertEqual(first.format, "TXT")
        XCTAssertNotNil(first.revision.range(of: "^[0-9a-f]{32}$", options: .regularExpression))
        XCTAssertEqual(first.chapters[0].fileName, "book-\(first.id)-\(first.revision)-c0.json")
        XCTAssertEqual(first.chapters[0].paragraphCount, 1)
        XCTAssertEqual(first.chapters[0].characterCount, 3)
        XCTAssertEqual(try chapter(first.chapters[0], in: root).paragraphs, ["abc"])
        let canonical = root.appendingPathComponent("book-\(first.id).manifest.json")
        XCTAssertFalse(FileManager.default.fileExists(atPath: canonical.path))
        try Data("KOTLIN_OWNS_CANONICAL".utf8).write(to: canonical)
        let second = try manifest(source, root)
        XCTAssertEqual(first.id, second.id)
        XCTAssertNotEqual(first.revision, second.revision)
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent(first.chapters[0].fileName).path))
        XCTAssertEqual(try String(contentsOf: canonical, encoding: .utf8), "KOTLIN_OWNS_CANONICAL")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(second)) as? [String: Any])
        let entries = try XCTUnwrap(object["chapters"] as? [[String: Any]])
        XCTAssertEqual(Set(entries[0].keys), Set(["title", "fileName", "paragraphCount", "characterCount"]))
        XCTAssertNil(entries[0]["paragraphs"])
    }

    func testLargeNoTOCTXTAboveLegacyLimitProducesBoundedChapters() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("large-no-toc.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: nil))
        let output = try FileHandle(forWritingTo: source)
        let line = Data((String(repeating: "文😀", count: 2_048) + "\n").utf8)
        let repeats = 2_400 // >32MiB on disk; never constructs the entire fixture.
        for _ in 0..<repeats { try output.write(contentsOf: line) }
        try output.close()
        XCTAssertGreaterThan(line.count * repeats, ImportLimits.fileBytes)
        let result = try manifest(source, root)
        XCTAssertGreaterThan(result.chapters.count, 1)
        var characters = 0
        for (index, entry) in result.chapters.enumerated() {
            XCTAssertEqual(entry.fileName, "book-\(result.id)-\(result.revision)-c\(index).json")
            let value = try chapter(entry, in: root)
            XCTAssertEqual(entry.paragraphCount, value.paragraphs.count)
            XCTAssertEqual(entry.characterCount, value.paragraphs.reduce(0) { $0 + $1.utf16.count })
            XCTAssertLessThanOrEqual(entry.characterCount, StreamingImportLimits.chapterUTF16)
            XCTAssertLessThanOrEqual(value.paragraphs.reduce(0) { $0 + $1.utf8.count }, StreamingImportLimits.chapterBytes)
            XCTAssertTrue(value.paragraphs.allSatisfy { $0.utf16.count <= ImportLimits.paragraphUTF16 && !$0.contains("�") })
            characters += entry.characterCount
        }
        XCTAssertEqual(characters, 3 * 2_048 * repeats)
    }

    func testConsecutiveHeadingsAndCRLFAcrossChunks() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("chapters.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try Data("序言\r\n第一章开始\r\n正文😀\r\nChapter 2 End\n正文二".utf8).write(to: source)
        let result = try manifest(source, root, readSize: 1)
        XCTAssertEqual(result.chapters.map(\.title), ["序言", "第一章开始", "Chapter 2 End"])
        XCTAssertEqual(try result.chapters.map { try chapter($0, in: root).paragraphs }, [[], ["正文😀"], ["正文二"]])
    }

    func testLongPhysicalLineFragmentIsNeverPromotedToHeading() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("long-line.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        // First 2000-unit fragment trims to a heading, but the line continues.
        let text = String(repeating: " ", count: 1_996) + "第一章A后续正文\n"
        try Data(text.utf8).write(to: source)
        let result = try manifest(source, root, readSize: 7)
        XCTAssertEqual(result.chapters.map(\.title), ["long-line"])
        XCTAssertEqual(try chapter(result.chapters[0], in: root).paragraphs.joined(), "第一章A后续正文")
    }

    func testFailureRollsBackOnlyCurrentRevisionFiles() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("truncated.txt")
        let root = base.appendingPathComponent("store", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let previous = root.appendingPathComponent("book-existing-revision-c0.json")
        try Data("PRESERVE".utf8).write(to: previous)
        XCTAssertTrue(FileManager.default.createFile(atPath: source.path, contents: Data([0xff, 0xfe])))
        let output = try FileHandle(forWritingTo: source)
        try output.seekToEnd()
        let chunk = (String(repeating: "正文😀", count: 8_192) + "\n").data(using: .utf16LittleEndian)!
        for _ in 0..<20 { try output.write(contentsOf: chunk) }
        // Fails only at EOF, after several chapters have already been published.
        try output.write(contentsOf: Data([0x00, 0xd8]))
        try output.close()
        XCTAssertThrowsError(try manifest(source, root))
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: root.path), [previous.lastPathComponent])
        XCTAssertEqual(try String(contentsOf: previous, encoding: .utf8), "PRESERVE")
    }

    func testFileBackedEPUBNoTOCSplitsSingleLogicalChapterAndIgnoresAssets() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("no-nav.epub")
        let root = base.appendingPathComponent("store", isDirectory: true)
        let text = String(repeating: "文😀", count: 180_000)
        try makeEPUB(at: source, body: "<html><body><p>\(text)</p></body></html>", largeAsset: true)
        let preflight = try ZIPPreflight(fileURL: source)
        XCTAssertEqual(preflight.records.count, 5)
        let result = try manifest(source, root)
        XCTAssertEqual(result.title, "文件归档示例")
        XCTAssertEqual(result.author, "测试作者")
        XCTAssertEqual(result.format, "EPUB")
        XCTAssertGreaterThan(result.chapters.count, 1)
        var units = 0
        for entry in result.chapters {
            let value = try chapter(entry, in: root)
            XCTAssertEqual(entry.paragraphCount, value.paragraphs.count)
            XCTAssertEqual(entry.characterCount, value.paragraphs.reduce(0) { $0 + $1.utf16.count })
            XCTAssertLessThanOrEqual(entry.characterCount, StreamingImportLimits.chapterUTF16)
            units += entry.characterCount
        }
        XCTAssertEqual(units, text.utf16.count)
    }

    func testFilePreflightRejectsStoredEntryWithMismatchedSizes() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("stored.zip")
        do {
            let archive = try Archive(url: source, accessMode: .create)
            let payload = Data("hello".utf8)
            try archive.addEntry(with: "stored.txt", type: .file, uncompressedSize: Int64(5), compressionMethod: .none) { offset, size in
                let start = Int(offset)
                return payload.subdata(in: start..<min(start + size, payload.count))
            }
        }
        let file = try FileHandle(forUpdating: source)
        let length = try file.seekToEnd()
        try file.seek(toOffset: length - 22)
        let end = try XCTUnwrap(file.read(upToCount: 22))
        XCTAssertEqual(end.count, 22)
        let directory = UInt64(end[16]) | UInt64(end[17]) << 8 | UInt64(end[18]) << 16 | UInt64(end[19]) << 24
        // Keep original uncompressed size and CRC, shrink only compressed size
        // in both headers. Stored entries must not read past declared ranges.
        try file.seek(toOffset: 18)
        try file.write(contentsOf: Data([4, 0, 0, 0]))
        try file.seek(toOffset: directory + 20)
        try file.write(contentsOf: Data([4, 0, 0, 0]))
        try file.close()
        XCTAssertThrowsError(try ZIPPreflight(fileURL: source))
    }

    func testFileBackedArchiveRetainsBombCRCAndPathChecks() throws {
        let base = try workspace()
        defer { try? FileManager.default.removeItem(at: base) }
        let source = base.appendingPathComponent("bad.epub")
        try makeEPUB(at: source, body: "<html><body><p>正文</p></body></html>")
        let file = try FileHandle(forUpdating: source)
        try file.seek(toOffset: UInt64(30 + "mimetype".utf8.count))
        try file.write(contentsOf: Data([0])) // CRC mismatch in a consumed entry.
        try file.close()
        XCTAssertThrowsError(try manifest(source, base.appendingPathComponent("store")))
        XCTAssertThrowsError(try ArchivePath.validateEntry("../escape"))
        XCTAssertThrowsError(try ArchivePath.resolve("https://example.invalid/a.xhtml"))
        let bomb = base.appendingPathComponent("bomb.epub")
        do {
            let archive = try Archive(url: bomb, accessMode: .create)
            let bytes = Data(repeating: 65, count: 1_024 * 1_024)
            try archive.addEntry(with: "bomb", type: .file, uncompressedSize: Int64(bytes.count), compressionMethod: .deflate) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(start + size, bytes.count))
            }
        }
        XCTAssertThrowsError(try ZIPPreflight(fileURL: bomb))
    }

    private func makeEPUB(at url: URL, body: String, largeAsset: Bool = false) throws {
        let archive = try Archive(url: url, accessMode: .create)
        let entries: [(String, String)] = [
            ("mimetype", "application/epub+zip"),
            ("META-INF/container.xml", "<container><rootfiles><rootfile full-path='OPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles></container>"),
            ("OPS/content.opf", "<package><metadata><title>文件归档示例</title><creator>测试作者</creator></metadata><manifest><item id='a' href='a.xhtml' media-type='application/xhtml+xml'/></manifest><spine><itemref idref='a'/></spine></package>"),
            ("OPS/a.xhtml", body)
        ]
        for (path, text) in entries {
            let bytes = Data(text.utf8)
            // Stored fixtures avoid triggering ratio protection on repeated text.
            try archive.addEntry(with: path, type: .file, uncompressedSize: Int64(bytes.count), compressionMethod: .none) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(start + size, bytes.count))
            }
        }
        if largeAsset {
            // >legacy 32MiB archive, but no giant Data or arbitrary extraction.
            try archive.addEntry(with: "unused-image.bin", type: .file,
                                 uncompressedSize: Int64(33 * 1_024 * 1_024), compressionMethod: .none) { _, size in
                Data(repeating: 7, count: size)
            }
        }
    }
}
