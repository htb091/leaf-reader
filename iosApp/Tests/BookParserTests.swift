import XCTest
import Foundation
import ZIPFoundation

final class BookParserTests: XCTestCase {
    private let parser = BookParser()

    func testOriginalByteSHA256AndJSONContract() throws {
        let book = try parser.parse(data: Data("abc".utf8), filename: "Example.TXT")
        XCTAssertEqual(book.id, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        XCTAssertEqual(book.title, "Example")
        XCTAssertEqual(book.format, "TXT")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(book.json().utf8)) as? [String: Any])
        XCTAssertEqual(Set(object.keys), Set(["id", "title", "author", "format", "chapters"]))
        XCTAssertEqual(book.chapters[0].paragraphs, ["abc"])
    }

    func testBOMAwareDecodingAndGB18030() throws {
        let expected = "中文正文"
        let variants: [Data] = [
            Data([0xef, 0xbb, 0xbf]) + Data(expected.utf8),
            Data([0xff, 0xfe]) + expected.data(using: .utf16LittleEndian)!,
            Data([0xfe, 0xff]) + expected.data(using: .utf16BigEndian)!,
            Data([0xd6, 0xd0, 0xce, 0xc4, 0xd5, 0xfd, 0xce, 0xc4])
        ]
        for bytes in variants {
            XCTAssertEqual(try parser.parse(data: bytes, filename: "编码.txt").chapters[0].paragraphs, [expected])
        }
        XCTAssertNotEqual(try parser.parse(data: variants[0], filename: "a.txt").id,
                          try parser.parse(data: Data(expected.utf8), filename: "a.txt").id)
    }

    func testLongLinesAndSingleGraphemeAreBoundedWithoutTextLoss() throws {
        for source in [String(repeating: "文", count: 10_001), "a" + String(repeating: "\u{0301}", count: 10_001)] {
            let book = try parser.parse(data: Data(source.utf8), filename: "long.txt")
            let paragraphs = book.chapters.flatMap(\.paragraphs)
            XCTAssertTrue(paragraphs.allSatisfy { $0.utf16.count <= ImportLimits.paragraphUTF16 })
            XCTAssertEqual(paragraphs.joined(), source)
        }
    }

    func testChapterSplittingPreservesConsecutiveHeadings() throws {
        let source = "序言\n第一章开始\n正文一\r\n\r\nChapter 2 End\n正文二"
        let book = try parser.parse(data: Data(source.utf8), filename: "chapters.txt")
        XCTAssertEqual(book.chapters.map(\.title), ["序言", "第一章开始", "Chapter 2 End"])
        XCTAssertEqual(book.chapters.map(\.paragraphs), [[], ["正文一"], ["正文二"]])
    }

    func testEmptyBinaryUTF32AndOversizedTextAreRejected() {
        for bytes in [Data(), Data([0, 1, 2]), Data([0xff, 0xfe, 0, 0, 65, 0, 0, 0]), Data(" \n\t".utf8)] {
            XCTAssertThrowsError(try parser.parse(data: bytes, filename: "bad.txt"))
        }
        XCTAssertThrowsError(try parser.parse(data: Data(repeating: 65, count: ImportLimits.fileBytes + 1), filename: "big.txt"))
        XCTAssertThrowsError(try parser.parse(data: Data(repeating: 65, count: 8 * 1_024 * 1_024 + 1), filename: "big.txt"))
    }

    func testEPUBMetadataSpineOrderNonLinearAndNoActiveContent() throws {
        let book = try parser.parse(data: EPUBFixture.book(), filename: "fallback.epub")
        XCTAssertEqual(book.title, "原创示例")
        XCTAssertEqual(book.author, "测试作者")
        XCTAssertEqual(book.format, "EPUB")
        XCTAssertEqual(book.chapters.map(\.title), ["第二章", "第一章"])
        let text = book.chapters.flatMap(\.paragraphs).joined(separator: " ")
        XCTAssertTrue(text.contains("第二章乙正文"))
        XCTAssertTrue(text.contains("甲正文 inline"))
        XCTAssertFalse(text.contains("SCRIPT_SENTINEL"))
        XCTAssertFalse(text.contains("STYLE_SENTINEL"))
        XCTAssertFalse(text.contains("NONLINEAR_SENTINEL"))
        XCTAssertFalse(text.contains("IMAGE_SENTINEL"))
    }

    func testDeflatedArchiveUsesSameTextAndSpine() throws {
        let source = try Archive(data: EPUBFixture.book(), accessMode: .read)
        let compressed = try Archive(data: Data(), accessMode: .create)
        for entry in source {
            var bytes = Data()
            _ = try source.extract(entry) { bytes.append($0) }
            try compressed.addEntry(with: entry.path, type: .file, uncompressedSize: Int64(bytes.count),
                                    compressionMethod: entry.path == "mimetype" ? .none : .deflate) { offset, size in
                let start = Int(offset)
                return bytes.subdata(in: start..<min(bytes.count, start + size))
            }
        }
        let book = try parser.parse(data: XCTUnwrap(compressed.data), filename: "compressed.epub")
        XCTAssertEqual(book.chapters.map(\.title), ["第二章", "第一章"])
    }

    func testSignedZIP32DataDescriptor() throws {
        let data = EPUBFixture.book(extra: [.init("unused.txt", bytes: Data("plain".utf8), flags: 8)])
        XCTAssertEqual(try parser.parse(data: data, filename: "descriptor.epub").title, "原创示例")
    }

    func testArchiveEncryptionDRMTraversalDuplicatesAndSymlinksAreRejected() {
        let cases: [[ZIPFixture.Item]] = [
            [.init("unused.bin", bytes: Data([1]), flags: 1)],
            [.init("META-INF/encryption.xml", text: "<encryption/>")],
            [.init("META-INF/rights.xml", text: "rights")],
            [.init("../escape.txt", text: "no")],
            [.init("/absolute.txt", text: "no")],
            [.init("a\\escape.txt", text: "no")],
            [.init("%2e%2e/escape.txt", text: "no")],
            [.init("mimetype", text: "duplicate")],
            [.init("link", text: "target", unixMode: 0xa000)]
        ]
        for extra in cases {
            XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(extra: extra), filename: "bad.epub"))
        }
    }

    func testBadCRCAndTruncatedArchiveAreRejected() {
        var bytes = EPUBFixture.book()
        // First entry's data follows its 30-byte local header and UTF-8 name.
        bytes[30 + "mimetype".utf8.count] ^= 1
        XCTAssertThrowsError(try parser.parse(data: bytes, filename: "bad.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book().dropLast(10), filename: "bad.epub"))
    }

    func testDeclaredEntryTotalAndCompressionRatioLimits() {
        let tooBig = ZIPFixture.make([.init("big", bytes: Data([1]), declaredSize: ImportLimits.entryBytes + 1)])
        XCTAssertThrowsError(try ZIPPreflight(data: tooBig))
        let ratio = ZIPFixture.make([.init("bomb", bytes: Data([1]), declaredSize: 100_000)])
        XCTAssertThrowsError(try ZIPPreflight(data: ratio))
        let entries = (0..<10).map { ZIPFixture.Item("\($0)", bytes: Data(repeating: 0, count: 45_000),
                                                 declaredSize: ImportLimits.entryBytes, method: 8) }
        XCTAssertThrowsError(try ZIPPreflight(data: ZIPFixture.make(entries)))
        XCTAssertThrowsError(try ZIPPreflight(data: ZIPFixture.make((0...ImportLimits.entries).map {
            .init("\($0)", text: "a")
        })))
    }

    func testPathResolutionRejectsRootEscapeAndRemoteResources() throws {
        XCTAssertEqual(try ArchivePath.resolve("../Text/a%20b.xhtml#part", relativeTo: "OPS/Packages/content.opf"), "OPS/Text/a b.xhtml")
        for href in ["../../escape.xhtml", "https://example.org/x", "//example.org/x", "%2e%2e/%2e%2e/x", "a%00b"] {
            XCTAssertThrowsError(try ArchivePath.resolve(href, relativeTo: "OPS/content.opf"))
        }
    }

    func testFixedLayoutDTDAndMissingSpineAreRejected() {
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(fixed: true), filename: "fixed.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(spineContent: ""), filename: "spine.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(href: "../../escape.xhtml"), filename: "path.epub"))
        let entity = "<!DOCTYPE html [<!ENTITY secret 'value'>]><html><body><p>&secret;</p></body></html>"
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody: entity), filename: "entity.epub"))
        let deep = "<html><body>" + String(repeating: "<div>", count: 130) + "text" + String(repeating: "</div>", count: 130) + "</body></html>"
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody: deep), filename: "depth.epub"))
    }

    func testEPUB2NamedEntitiesDoNotRequireExternalDTD() throws {
        let body = """
        <?xml version='1.0' encoding='UTF-8'?>
        <!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'https://example.invalid/never-fetch.dtd'>
        <html xmlns='http://www.w3.org/1999/xhtml'><body><p>A&nbsp;B &mdash; &copy; &fjlig; &lt;script&gt;literal&lt;/script&gt;</p></body></html>
        """
        let book = try parser.parse(data: EPUBFixture.book(firstBody: body), filename: "epub2.epub")
        let paragraph = try XCTUnwrap(book.chapters[1].paragraphs.first)
        XCTAssertTrue(paragraph.contains("A\u{00a0}B"))
        XCTAssertTrue(paragraph.contains("— © fj"))
        XCTAssertTrue(paragraph.contains("<script>literal</script>"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody:
            "<html><body><p>&unknownCustomEntity;</p></body></html>"), filename: "unknown.epub"))
        XCTAssertThrowsError(try parser.parse(data: EPUBFixture.book(firstBody:
            "<html><body><p>" + String(repeating: "&nbsp;", count: 100_001) + "</p></body></html>"), filename: "entities.epub"))
    }

    func testParagraphsIncludingNestedBlocksAreNotDuplicatedOrLost() throws {
        let body = "<html><body>leading<div>outer<p>inner <b>bold</b></p>tail</div>ending<br/>after</body></html>"
        let book = try parser.parse(data: EPUBFixture.book(firstBody: body), filename: "nested.epub")
        XCTAssertEqual(book.chapters[1].paragraphs, ["leading", "outer", "inner bold", "tail", "ending", "after"])
    }
}

// Small generated, original fixtures: no downloaded books and no bundled text.
private enum EPUBFixture {
    static func book(extra: [ZIPFixture.Item] = [], fixed: Bool = false,
                     href: String = "a.xhtml", firstBody: String? = nil, spineContent: String? = nil) -> Data {
        let fixedMeta = fixed ? "<meta property='rendition:layout'>pre-paginated</meta>" : ""
        let spine = spineContent ?? "<itemref idref='b'/><itemref idref='n' linear='no'/><itemref idref='a'/>"
        let container = "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'><rootfiles><rootfile full-path='OPS/content.opf' media-type='application/oebps-package+xml'/></rootfiles></container>"
        let opf = """
        <package xmlns='http://www.idpf.org/2007/opf' version='3.0'>
        <metadata xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:title>原创示例</dc:title><dc:creator>测试作者</dc:creator>\(fixedMeta)</metadata>
        <manifest><item id='a' href='\(href)' media-type='application/xhtml+xml'/><item id='b' href='b.xhtml' media-type='application/xhtml+xml'/><item id='n' href='n.xhtml' media-type='application/xhtml+xml'/></manifest>
        <spine>\(spine)</spine>
        </package>
        """
        let a = firstBody ?? "<html xmlns='http://www.w3.org/1999/xhtml'><head><style>STYLE_SENTINEL</style></head><body><h1>第一章</h1><p>甲正文 <b>inline</b></p><script>SCRIPT_SENTINEL</script><img src='https://example.org/no-fetch' alt='IMAGE_SENTINEL'/></body></html>"
        return ZIPFixture.make([
            .init("mimetype", text: "application/epub+zip"),
            .init("META-INF/container.xml", text: container),
            .init("OPS/content.opf", text: opf),
            .init("OPS/a.xhtml", text: a),
            .init("OPS/b.xhtml", text: "<html><body><h1>第二章</h1><p>第二章乙正文</p></body></html>"),
            .init("OPS/n.xhtml", text: "<html><body><p>NONLINEAR_SENTINEL</p></body></html>")
        ] + extra)
    }
}

private enum ZIPFixture {
    struct Item {
        let name: String
        let bytes: Data
        var flags: UInt16 = 0
        var unixMode: UInt32 = 0x8000
        var declaredSize: Int? = nil
        var method: UInt16 = 0
        init(_ name: String, bytes: Data, flags: UInt16 = 0, unixMode: UInt32 = 0x8000,
             declaredSize: Int? = nil, method: UInt16 = 0) {
            self.name = name; self.bytes = bytes; self.flags = flags; self.unixMode = unixMode
            self.declaredSize = declaredSize; self.method = method
        }
        init(_ name: String, text: String, unixMode: UInt32 = 0x8000) {
            self.init(name, bytes: Data(text.utf8), unixMode: unixMode)
        }
    }

    static func make(_ items: [Item]) -> Data {
        var local = Data()
        var central = Data()
        for item in items {
            let name = Data(item.name.utf8)
            let offset = UInt32(local.count)
            let crc = crc32(item.bytes)
            let size = UInt32(item.declaredSize ?? item.bytes.count)
            local.le32(0x04034b50); local.le16(20); local.le16(item.flags); local.le16(item.method)
            local.le16(0); local.le16(0); local.le32(crc); local.le32(UInt32(item.bytes.count)); local.le32(size)
            local.le16(UInt16(name.count)); local.le16(0); local.append(name); local.append(item.bytes)
            if item.flags & 8 != 0 {
                local.le32(0x08074b50); local.le32(crc); local.le32(UInt32(item.bytes.count)); local.le32(size)
            }
            central.le32(0x02014b50); central.le16(0x0314); central.le16(20); central.le16(item.flags)
            central.le16(item.method); central.le16(0); central.le16(0); central.le32(crc)
            central.le32(UInt32(item.bytes.count)); central.le32(size); central.le16(UInt16(name.count))
            central.le16(0); central.le16(0); central.le16(0); central.le16(0)
            central.le32(item.unixMode << 16); central.le32(offset); central.append(name)
        }
        let centralOffset = UInt32(local.count)
        local.append(central)
        local.le32(0x06054b50); local.le16(0); local.le16(0)
        local.le16(UInt16(items.count)); local.le16(UInt16(items.count))
        local.le32(UInt32(central.count)); local.le32(centralOffset); local.le16(0)
        return local
    }

    private static func crc32(_ bytes: Data) -> UInt32 {
        var value: UInt32 = 0xffffffff
        for byte in bytes {
            value ^= UInt32(byte)
            for _ in 0..<8 { value = (value >> 1) ^ ((value & 1) == 1 ? 0xedb88320 : 0) }
        }
        return value ^ 0xffffffff
    }
}

private extension Data {
    mutating func le16(_ value: UInt16) { append(UInt8(truncatingIfNeeded: value)); append(UInt8(truncatingIfNeeded: value >> 8)) }
    mutating func le32(_ value: UInt32) {
        for shift in stride(from: 0, to: 32, by: 8) { append(UInt8(truncatingIfNeeded: value >> shift)) }
    }
}
