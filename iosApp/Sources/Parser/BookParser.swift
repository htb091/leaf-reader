import Foundation
import CryptoKit
import CoreFoundation

struct ImportedChapter: Codable, Equatable {
    let title: String
    let paragraphs: [String]
}

struct ImportedBook: Codable, Equatable {
    let id: String
    let title: String
    let author: String
    let format: String
    let chapters: [ImportedChapter]

    func validated() throws -> ImportedBook {
        let units = chapters.reduce(title.utf16.count + author.utf16.count) { total, chapter in
            total + chapter.title.utf16.count + chapter.paragraphs.reduce(0) { $0 + $1.utf16.count }
        }
        guard units <= 8 * 1_024 * 1_024 else { throw ImportFailure.oversized }
        return self
    }

    func json() throws -> String {
        _ = try validated()
        let data = try JSONEncoder().encode(self)
        guard let result = String(data: data, encoding: .utf8) else { throw ImportFailure.invalidText }
        return result
    }
}

// Legacy in-memory fixture limits. User-selected file imports instead use
// StreamingImportLimits and never cross the bridge with all chapter text.
enum ImportLimits {
    static let fileBytes = 32 * 1_024 * 1_024
    static let entryBytes = 8 * 1_024 * 1_024
    static let expandedBytes = 64 * 1_024 * 1_024
    static let textBytes = 12 * 1_024 * 1_024
    static let xmlBytes = 1 * 1_024 * 1_024
    static let entries = 4_096
    static let compressionRatio = 200
    static let paragraphUTF16 = 2_000
    static let paragraphs = 50_000
    static let chapters = 2_000
}

enum ImportFailure: Error, LocalizedError {
    case unsupported, unreadable, oversized, invalidText, empty, malformedEPUB
    case encrypted, unsafePath, archiveLimit, unsupportedLayout, complexMarkup

    var errorDescription: String? {
        switch self {
        case .unsupported: return "请选择 TXT 或 EPUB 文件。"
        case .unreadable: return "文件读取失败，请重新从文件 App 选择。"
        case .oversized: return "超过导入上限：TXT 512 MiB、EPUB 1 GiB、章节 50000、段落 2000000；单章正文分块保存。"
        case .invalidText: return "文本编码异常；支持 UTF-8、带 BOM 的 UTF-16 和 GB18030。"
        case .empty: return "文件中没有可阅读的正文。"
        case .malformedEPUB: return "EPUB 结构或校验异常，请检查文件是否完整。"
        case .encrypted: return "此 EPUB 含 DRM 或加密内容，暂不支持。"
        case .unsafePath: return "EPUB 含异常路径或重复条目。"
        case .archiveLimit: return "EPUB 超过解压限制，或使用暂未支持的 ZIP64／多卷格式。"
        case .unsupportedLayout: return "暂不支持固定版式或非文本 EPUB；图像和 CSS 不参与导入。"
        case .complexMarkup: return "EPUB 标记嵌套或节点数量超过导入限制。"
        }
    }
}

struct BookParser {
    // Legacy small-book adapter only. DocumentPicker uses parseFileToManifest.
    @available(*, deprecated, message: "Use parseFileToManifest for document imports")
    func parseFile(at url: URL) throws -> ImportedBook {
        guard url.isFileURL else { throw ImportFailure.unreadable }
        let ext = url.pathExtension.lowercased()
        guard ext == "txt" || ext == "epub" else { throw ImportFailure.unsupported }
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
        guard values.isRegularFile == true else { throw ImportFailure.unreadable }
        if let size = values.fileSize, size > ImportLimits.fileBytes { throw ImportFailure.oversized }
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var data = Data()
        while let chunk = try handle.read(upToCount: 64 * 1_024), !chunk.isEmpty {
            guard chunk.count <= ImportLimits.fileBytes - data.count else { throw ImportFailure.oversized }
            data.append(chunk)
        }
        return try parse(data: data, filename: url.lastPathComponent)
    }

    func parse(data: Data, filename: String) throws -> ImportedBook {
        guard data.count <= ImportLimits.fileBytes else { throw ImportFailure.oversized }
        guard !data.isEmpty else { throw ImportFailure.empty }
        let title = String((filename as NSString).deletingPathExtension.prefix(240))
        let id = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        switch (filename as NSString).pathExtension.lowercased() {
        case "txt":
            let text = try TextDecoding.decode(data, allowGB18030: true)
            guard text.utf8.count <= ImportLimits.textBytes else { throw ImportFailure.oversized }
            var builder = ChapterBuilder(defaultTitle: title.isEmpty ? "正文" : title)
            // enumerateLines does not allocate an array containing every line.
            var failure: Error?
            text.enumerateLines { line, stop in
                do {
                    if Self.isChapterHeading(line) {
                        try builder.startChapter(String(line.trimmingCharacters(in: .whitespaces).prefix(240)))
                    } else {
                        try builder.addParagraph(line)
                    }
                } catch { failure = error; stop = true }
            }
            if let failure { throw failure }
            let chapters = try builder.finish()
            return try ImportedBook(id: id, title: title, author: "", format: "TXT", chapters: chapters).validated()
        case "epub":
            return try EPUBParser().parse(data: data, id: id, fallbackTitle: title).validated()
        default: throw ImportFailure.unsupported
        }
    }

    private static func isChapterHeading(_ line: String) -> Bool {
        guard line.utf16.count <= 120 else { return false }
        return line.range(of: #"^\s*(第[零〇一二三四五六七八九十百千万两0-9０-９]+[章节卷部篇回集].*|[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+[0-9IVXivx]+(\s.*|[：:、.．].*|)|序章|序言|前言|楔子|尾声|后记)\s*$"#,
                          options: .regularExpression) != nil
    }
}

enum TextDecoding {
    static func decode(_ data: Data, allowGB18030: Bool) throws -> String {
        let prefix = [UInt8](data.prefix(4))
        // UTF-32 is intentionally not guessed as UTF-16.
        if prefix == [0xff, 0xfe, 0, 0] || prefix == [0, 0, 0xfe, 0xff] { throw ImportFailure.invalidText }
        let result: String?
        if prefix.starts(with: [0xef, 0xbb, 0xbf]) {
            result = String(data: data.dropFirst(3), encoding: .utf8)
        } else if prefix.starts(with: [0xff, 0xfe]) {
            result = String(data: data.dropFirst(2), encoding: .utf16LittleEndian)
        } else if prefix.starts(with: [0xfe, 0xff]) {
            result = String(data: data.dropFirst(2), encoding: .utf16BigEndian)
        } else if let utf8 = String(data: data, encoding: .utf8) {
            result = utf8
        } else if allowGB18030 {
            let cf = CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue)
            let encoding = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(cf))
            result = String(data: data, encoding: encoding)
        } else {
            result = nil
        }
        guard let result, !result.unicodeScalars.contains(where: { $0.value == 0 }) else {
            throw ImportFailure.invalidText
        }
        return result
    }
}

struct ChapterBuilder {
    private var chapters: [ImportedChapter] = []
    private var title: String
    private var paragraphs: [String] = []
    private var paragraphCount = 0
    private var textBytes = 0
    private var explicitHeading = false

    init(defaultTitle: String) { title = String(defaultTitle.prefix(240)) }

    mutating func startChapter(_ newTitle: String) throws {
        // Preserve consecutive headings as empty chapters, not discarded text.
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        title = String(newTitle.prefix(240))
        explicitHeading = true
    }

    mutating func addParagraph(_ source: String) throws {
        var buffer = String.UnicodeScalarView()
        var units = 0
        // Scalar iteration also bounds pathological single grapheme clusters.
        for scalar in source.unicodeScalars {
            if [0x0a, 0x0d, 0x2028, 0x2029].contains(scalar.value) {
                try append(String(buffer))
                buffer = String.UnicodeScalarView()
                units = 0
                continue
            }
            if scalar.value < 0x20 && scalar != "\t" { continue }
            let cost = scalar.value > 0xffff ? 2 : 1
            if units + cost > ImportLimits.paragraphUTF16 {
                try append(String(buffer))
                buffer = String.UnicodeScalarView()
                units = 0
            }
            buffer.append(scalar)
            units += cost
        }
        try append(String(buffer))
    }

    private mutating func append(_ source: String) throws {
        let value = source.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        guard paragraphCount < ImportLimits.paragraphs,
              value.utf8.count <= ImportLimits.textBytes - textBytes else { throw ImportFailure.oversized }
        paragraphCount += 1
        textBytes += value.utf8.count
        paragraphs.append(value)
    }

    private mutating func flushChapter() throws {
        guard chapters.count < ImportLimits.chapters else { throw ImportFailure.oversized }
        chapters.append(ImportedChapter(title: title.isEmpty ? "正文" : title, paragraphs: paragraphs))
        paragraphs = []
    }

    mutating func finish() throws -> [ImportedChapter] {
        if !paragraphs.isEmpty || explicitHeading { try flushChapter() }
        guard paragraphCount > 0 else { throw ImportFailure.empty }
        return chapters
    }
}
