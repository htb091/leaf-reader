import Foundation
import CryptoKit
import CoreFoundation

// File imports never use ImportedBook, all-book Data or all-book JSON.
// Only the current byte buffer, paragraph, chapter and the small index live here.
enum StreamingImportLimits {
    static let txtBytes = 512 * 1_024 * 1_024
    static let epubBytes = 1_024 * 1_024 * 1_024
    static let chunkBytes = 64 * 1_024
    static let chapterUTF16 = 256 * 1_024
    // Raw paragraph UTF-8 only, not JSON syntax/escaping. Encoded chapter JSON
    // can be larger (~1.25MiB for many tiny quoted paragraphs); core allows 4Mi.
    static let chapterBytes = 512 * 1_024
    static let chapterParagraphs = 2_000
    static let paragraphs = 2_000_000
    static let chapters = 50_000
    static let archiveEntries = 50_000
    static let archiveEntryBytes = 64 * 1_024 * 1_024
    static let archiveMetadataBytes = 32 * 1_024 * 1_024
    static let expandedBytes = 2 * 1_024 * 1_024 * 1_024
    static let xhtmlBytes = 8 * 1_024 * 1_024
}

struct ImportedChapterEntry: Codable, Equatable {
    let title: String
    let fileName: String
    let paragraphCount: Int
    let characterCount: Int
}

struct ImportedManifest: Codable, Equatable {
    let schema: Int
    let id: String
    let title: String
    let author: String
    let format: String
    let revision: String
    let chapters: [ImportedChapterEntry]
}

extension BookParser {
    // storageRoot/readSize are injectable for hostless parser tests only.
    // Production uses exactly the shared ReaderFiles Application Support root.
    func parseFileToManifest(at url: URL, storageRoot: URL? = nil,
                             readSize: Int = StreamingImportLimits.chunkBytes) throws -> String {
        guard url.isFileURL, readSize > 0, readSize <= StreamingImportLimits.chunkBytes else {
            throw ImportFailure.unreadable
        }
        let ext = url.pathExtension.lowercased()
        guard ext == "txt" || ext == "epub" else { throw ImportFailure.unsupported }
        let limit = ext == "txt" ? StreamingImportLimits.txtBytes : StreamingImportLimits.epubBytes
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
        guard values.isRegularFile == true else { throw ImportFailure.unreadable }
        guard let size = values.fileSize, size > 0 else { throw ImportFailure.empty }
        guard size <= limit else { throw ImportFailure.oversized }
        let scan = try FileScan.scan(url, limit: limit, detectText: ext == "txt")
        let root: URL
        if let storageRoot { root = storageRoot } else {
            root = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                               appropriateFor: nil, create: true)
                .appendingPathComponent("LeafReader", isDirectory: true)
        }
        let fallback = boundedTitle((url.lastPathComponent as NSString).deletingPathExtension)
        let writer = try ChapterFileWriter(root: root, id: scan.id, defaultTitle: fallback)
        do {
            var title = fallback
            var author = ""
            if ext == "txt" {
                let handle = try FileHandle(forReadingFrom: url)
                defer { try? handle.close() }
                var decoder = IncrementalTextDecoder(encoding: scan.encoding)
                var hasher = SHA256()
                var total = 0
                var skip = scan.bomBytes
                while let bytes = try autoreleasepool(invoking: { try handle.read(upToCount: readSize) }), !bytes.isEmpty {
                    guard bytes.count <= limit - total else { throw ImportFailure.oversized }
                    total += bytes.count
                    hasher.update(data: bytes)
                    let removed = min(skip, bytes.count)
                    skip -= removed
                    try autoreleasepool {
                        try writer.consume(try decoder.decode(Data(bytes.dropFirst(removed))))
                    }
                }
                try writer.consume(try decoder.decode(Data(), final: true))
                guard total == scan.size, FileScan.hex(hasher.finalize()) == scan.id else {
                    throw ImportFailure.unreadable
                }
            } else {
                let metadata = try EPUBParser().parseFile(at: url, writer: writer)
                title = metadata.title
                author = metadata.author
                // Reject a provider changing the source during the transaction.
                let after = try FileScan.scan(url, limit: limit, detectText: false)
                guard after.id == scan.id, after.size == scan.size else { throw ImportFailure.unreadable }
            }
            return try writer.finish(title: title, author: author, format: ext.uppercased())
        } catch {
            writer.rollback()
            throw error
        }
    }
}

private struct FileScan {
    let id: String
    let size: Int
    let encoding: IncrementalTextDecoder.Encoding
    let bomBytes: Int

    static func hex(_ digest: SHA256.Digest) -> String {
        digest.map { String(format: "%02x", $0) }.joined()
    }

    static func scan(_ url: URL, limit: Int, detectText: Bool) throws -> FileScan {
        let file = try FileHandle(forReadingFrom: url)
        defer { try? file.close() }
        var hash = SHA256()
        var size = 0
        var encoding = IncrementalTextDecoder.Encoding.utf8
        var bom = 0
        if detectText {
            // FileHandle may return a short read even before EOF. Sniff a full
            // four-byte prefix (or EOF) without assuming the first read fills.
            var prefix = Data()
            while prefix.count < 4 {
                guard let bytes = try file.read(upToCount: 4 - prefix.count), !bytes.isEmpty else { break }
                prefix.append(bytes)
            }
            if prefix == Data([0xff, 0xfe, 0, 0]) || prefix == Data([0, 0, 0xfe, 0xff]) {
                throw ImportFailure.invalidText
            }
            if prefix.starts(with: [0xef, 0xbb, 0xbf]) { bom = 3 }
            if prefix.starts(with: [0xff, 0xfe]) { encoding = .utf16LE; bom = 2 }
            if prefix.starts(with: [0xfe, 0xff]) { encoding = .utf16BE; bom = 2 }
            try file.seek(toOffset: 0)
        }
        var skip = bom
        var utf8Valid = true
        var validator = IncrementalTextDecoder(encoding: .utf8)
        while let bytes = try autoreleasepool(invoking: { try file.read(upToCount: StreamingImportLimits.chunkBytes) }), !bytes.isEmpty {
            guard bytes.count <= limit - size else { throw ImportFailure.oversized }
            hash.update(data: bytes)
            if detectText, encoding == .utf8, utf8Valid {
                let removed = min(skip, bytes.count)
                skip -= removed
                do {
                    try autoreleasepool { _ = try validator.decode(Data(bytes.dropFirst(removed))) }
                } catch { utf8Valid = false }
            }
            size += bytes.count
        }
        guard size > 0 else { throw ImportFailure.empty }
        if detectText, encoding == .utf8, utf8Valid {
            do { _ = try validator.decode(Data(), final: true) } catch { utf8Valid = false }
        }
        if detectText, encoding == .utf8, !utf8Valid {
            // A UTF-8 BOM is a declaration, not an encoding guess.
            guard bom == 0 else { throw ImportFailure.invalidText }
            encoding = .gb18030
        }
        return FileScan(id: hex(hash.finalize()), size: size, encoding: encoding, bomBytes: bom)
    }
}

// Strict unit framing retains at most three incomplete bytes between calls.
// Foundation decodes only complete, bounded runs, including GB18030 four-byte
// sequences. No replacement characters, byte loss or split UTF-16 surrogates.
struct IncrementalTextDecoder {
    enum Encoding { case utf8, utf16LE, utf16BE, gb18030 }
    let encoding: Encoding
    private var carry: [UInt8] = []

    init(encoding: Encoding) { self.encoding = encoding }

    mutating func decode(_ data: Data, final: Bool = false) throws -> String {
        var bytes = carry
        bytes.append(contentsOf: data)
        var index = 0
        scanUnits: while index < bytes.count {
            let first = bytes[index]
            let length: Int
            switch encoding {
            case .utf8:
                if first <= 0x7f { length = 1 }
                else if (0xc2...0xdf).contains(first) { length = 2 }
                else if (0xe0...0xef).contains(first) { length = 3 }
                else if (0xf0...0xf4).contains(first) { length = 4 }
                else { throw ImportFailure.invalidText }
                if bytes.count - index >= length {
                    for offset in 1..<length where !(0x80...0xbf).contains(bytes[index + offset]) {
                        throw ImportFailure.invalidText
                    }
                    if length >= 3 {
                        let second = bytes[index + 1]
                        if first == 0xe0 && second < 0xa0 || first == 0xed && second >= 0xa0 ||
                            first == 0xf0 && second < 0x90 || first == 0xf4 && second >= 0x90 {
                            throw ImportFailure.invalidText
                        }
                    }
                }
            case .utf16LE, .utf16BE:
                guard bytes.count - index >= 2 else { break scanUnits }
                let unit = utf16Unit(bytes, index)
                if (0xd800...0xdbff).contains(unit) {
                    length = 4
                    if bytes.count - index >= 4, !(0xdc00...0xdfff).contains(utf16Unit(bytes, index + 2)) {
                        throw ImportFailure.invalidText
                    }
                } else {
                    guard !(0xdc00...0xdfff).contains(unit) else { throw ImportFailure.invalidText }
                    length = 2
                }
            case .gb18030:
                if first <= 0x7f { length = 1 } else {
                    guard (0x81...0xfe).contains(first) else { throw ImportFailure.invalidText }
                    guard bytes.count - index >= 2 else { break scanUnits }
                    let second = bytes[index + 1]
                    if (0x30...0x39).contains(second) {
                        length = 4
                        if bytes.count - index >= 4 {
                            guard (0x81...0xfe).contains(bytes[index + 2]),
                                  (0x30...0x39).contains(bytes[index + 3]) else { throw ImportFailure.invalidText }
                        }
                    } else {
                        guard (0x40...0xfe).contains(second), second != 0x7f else { throw ImportFailure.invalidText }
                        length = 2
                    }
                }
            }
            if bytes.count - index < length { break }
            index += length
        }
        carry = Array(bytes[index...])
        guard carry.count <= 3, !final || carry.isEmpty else { throw ImportFailure.invalidText }
        guard index > 0 else { return "" }
        let stringEncoding: String.Encoding
        switch encoding {
        case .utf8: stringEncoding = .utf8
        case .utf16LE: stringEncoding = .utf16LittleEndian
        case .utf16BE: stringEncoding = .utf16BigEndian
        case .gb18030:
            stringEncoding = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(
                CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue)))
        }
        guard let result = String(data: Data(bytes[..<index]), encoding: stringEncoding),
              !result.unicodeScalars.contains(where: { $0.value == 0 }) else { throw ImportFailure.invalidText }
        return result
    }

    private func utf16Unit(_ bytes: [UInt8], _ index: Int) -> UInt16 {
        if encoding == .utf16LE { return UInt16(bytes[index]) | UInt16(bytes[index + 1]) << 8 }
        return UInt16(bytes[index]) << 8 | UInt16(bytes[index + 1])
    }
}

func boundedTitle(_ source: String) -> String {
    var result = String.UnicodeScalarView()
    var units = 0
    for scalar in source.unicodeScalars {
        let cost = scalar.value > 0xffff ? 2 : 1
        if units + cost > 240 { break }
        result.append(scalar)
        units += cost
    }
    let title = String(result).trimmingCharacters(in: .whitespacesAndNewlines)
    return title.isEmpty ? "正文" : title
}

final class ChapterFileWriter {
    private let root: URL
    private let id: String
    private let revision = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    private var entries: [ImportedChapterEntry] = []
    private var published: [URL] = []
    private var title: String
    private var paragraphs: [String] = []
    private var chapterUnits = 0
    private var chapterBytes = 0
    private var paragraphTotal = 0
    private var explicitHeading = false
    private var part = 1
    private var line = String.UnicodeScalarView()
    private var lineUnits = 0
    private var continuedLine = false
    private var previousCR = false

    init(root: URL, id: String, defaultTitle: String) throws {
        self.root = root
        self.id = id
        title = boundedTitle(defaultTitle)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }

    func startChapter(_ heading: String) throws {
        try flushLine()
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        title = boundedTitle(heading)
        part = 1
        explicitHeading = true
    }

    func consume(_ text: String) throws {
        for scalar in text.unicodeScalars {
            if scalar.value == 0x0a, previousCR { previousCR = false; continue }
            previousCR = scalar.value == 0x0d
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try flushLine()
                continuedLine = false
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if lineUnits + cost > ImportLimits.paragraphUTF16 {
                // This is a fragment of a longer physical line, never a heading.
                continuedLine = true
                try flushLine()
            }
            line.append(scalar)
            lineUnits += cost
        }
    }

    // EPUB block boundaries are intentional paragraphs, not TXT headings.
    func addParagraph(_ text: String) throws {
        var buffer = String.UnicodeScalarView()
        var units = 0
        for scalar in text.unicodeScalars {
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try appendParagraph(String(buffer)); buffer = String.UnicodeScalarView(); units = 0
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if units + cost > ImportLimits.paragraphUTF16 {
                try appendParagraph(String(buffer)); buffer = String.UnicodeScalarView(); units = 0
            }
            buffer.append(scalar)
            units += cost
        }
        try appendParagraph(String(buffer))
    }

    private func flushLine() throws {
        let sourceUnits = lineUnits
        let value = String(line).trimmingCharacters(in: .whitespacesAndNewlines)
        line = String.UnicodeScalarView()
        lineUnits = 0
        if !continuedLine, sourceUnits <= 120,
           value.range(of: #"^\s*(第[零〇一二三四五六七八九十百千万两0-9０-９]+[章节卷部篇回集].*|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+[0-9IVXivx]+(\s.*|[：:、.．].*|)|序章|序言|前言|楔子|尾声|后记)\s*$"#,
                       options: .regularExpression) != nil {
            // The line buffer is already empty; no recursive reprocessing.
            try startChapter(value)
        } else { try appendParagraph(value) }
    }

    private func appendParagraph(_ source: String) throws {
        let value = source.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        let units = value.utf16.count
        let bytes = value.utf8.count
        guard paragraphTotal < StreamingImportLimits.paragraphs,
              units <= ImportLimits.paragraphUTF16 else { throw ImportFailure.oversized }
        if paragraphs.count >= StreamingImportLimits.chapterParagraphs ||
            chapterUnits + units > StreamingImportLimits.chapterUTF16 ||
            chapterBytes + bytes > StreamingImportLimits.chapterBytes {
            try flushChapter()
            part += 1
        }
        paragraphs.append(value)
        chapterUnits += units
        chapterBytes += bytes
        paragraphTotal += 1
    }

    private func flushChapter() throws {
        guard entries.count < StreamingImportLimits.chapters else { throw ImportFailure.oversized }
        let chapterTitle = part == 1 ? title : boundedTitle("\(title) · \(part)")
        let name = "book-\(id)-\(revision)-c\(entries.count).json"
        let path = root.appendingPathComponent(name, isDirectory: false)
        let chapter = ImportedChapter(title: chapterTitle, paragraphs: paragraphs)
        // JSONEncoder only sees one bounded chapter, never the complete book.
        try JSONEncoder().encode(chapter).write(to: path, options: .atomic)
        published.append(path)
        entries.append(ImportedChapterEntry(title: chapterTitle, fileName: name,
                                            paragraphCount: paragraphs.count, characterCount: chapterUnits))
        paragraphs = []
        chapterUnits = 0
        chapterBytes = 0
    }

    func finish(title: String, author: String, format: String) throws -> String {
        try flushLine()
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        guard paragraphTotal > 0 else { throw ImportFailure.empty }
        let manifest = ImportedManifest(schema: 2, id: id, title: boundedTitle(title),
                                        author: author.isEmpty ? "" : boundedTitle(author), format: format,
                                        revision: revision, chapters: entries)
        let data = try JSONEncoder().encode(manifest)
        guard let json = String(data: data, encoding: .utf8) else { throw ImportFailure.invalidText }
        // Canonical manifest and shelf publication belong exclusively to Kotlin.
        return json
    }

    func rollback() {
        // Only paths created by this exact id/revision transaction are touched.
        for path in published { try? FileManager.default.removeItem(at: path) }
        published = []
    }
}
