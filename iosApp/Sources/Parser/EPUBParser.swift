import Foundation
import ZIPFoundation
import SwiftSoup

struct EPUBParser {
    // The in-memory API remains restricted to the original small test fixtures.
    func parse(data: Data, id: String, fallbackTitle: String) throws -> ImportedBook {
        let preflight = try ZIPPreflight(data: data)
        let archive = try Archive(data: data, accessMode: .read)
        var builder = ChapterBuilder(defaultTitle: fallbackTitle)
        let metadata = try parseArchive(archive, preflight: preflight, fallbackTitle: fallbackTitle,
                                        expandedLimit: ImportLimits.expandedBytes) { title, paragraphs in
            try builder.startChapter(title)
            for paragraph in paragraphs { try builder.addParagraph(paragraph) }
        }
        return ImportedBook(id: id, title: metadata.title, author: metadata.author,
                            format: "EPUB", chapters: try builder.finish())
    }

    func parseFile(at url: URL, writer: ChapterFileWriter) throws -> (title: String, author: String) {
        let preflight = try ZIPPreflight(fileURL: url)
        // Crucially this is the URL-backed initializer, not Archive(data:).
        let archive = try Archive(url: url, accessMode: .read)
        return try parseArchive(archive, preflight: preflight, fallbackTitle: url.deletingPathExtension().lastPathComponent,
                                expandedLimit: StreamingImportLimits.expandedBytes) { title, paragraphs in
            try writer.startChapter(title)
            for paragraph in paragraphs { try writer.addParagraph(paragraph) }
        }
    }

    private func parseArchive(_ archive: Archive, preflight: ZIPPreflight, fallbackTitle: String,
                              expandedLimit: Int,
                              emit: (String, [String]) throws -> Void) throws -> (title: String, author: String) {
        var entries: [String: Entry] = [:]
        for entry in archive {
            guard let checked = preflight.records[entry.path], entry.type != .symlink,
                  entry.uncompressedSize == UInt64(checked.uncompressedSize),
                  entry.compressedSize == UInt64(checked.compressedSize),
                  entry.checksum == checked.checksum,
                  (entry.type == .directory) == checked.isDirectory else { throw ImportFailure.malformedEPUB }
            entries[entry.path] = entry
        }
        guard entries.count == preflight.records.count else { throw ImportFailure.malformedEPUB }
        var reader = EntryReader(archive: archive, entries: entries, expandedLimit: expandedLimit)
        let mimetype = try reader.read("mimetype", limit: 64)
        guard String(data: mimetype, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) == "application/epub+zip" else {
            throw ImportFailure.malformedEPUB
        }
        let container = PackageXML(mode: .container)
        try container.parse(try reader.read("META-INF/container.xml", limit: ImportLimits.xmlBytes))
        guard let packageHref = container.rootfiles.first else { throw ImportFailure.malformedEPUB }
        let packagePath = try ArchivePath.resolve(packageHref)
        let package = PackageXML(mode: .package)
        try package.parse(try reader.read(packagePath, limit: ImportLimits.xmlBytes))
        guard !package.fixedLayout else { throw ImportFailure.unsupportedLayout }
        guard !package.spine.isEmpty else { throw ImportFailure.malformedEPUB }
        let title = package.bookTitle.isEmpty ? fallbackTitle : package.bookTitle
        var linear = package.spine.filter { $0.linear }
        // A book with only non-linear entries has no primary reading order.
        if linear.isEmpty { linear = package.spine }
        var seen = Set<String>()
        for reference in linear {
            guard let item = package.manifest[reference.id] else { throw ImportFailure.malformedEPUB }
            guard ["application/xhtml+xml", "text/html"].contains(item.mediaType) else {
                throw ImportFailure.unsupportedLayout
            }
            guard !reference.properties.contains("rendition:layout-pre-paginated") else { throw ImportFailure.unsupportedLayout }
            let path = try ArchivePath.resolve(item.href, relativeTo: packagePath)
            // Duplicate spine references otherwise inflate the output and repeat chapters.
            guard seen.insert(path).inserted else { throw ImportFailure.malformedEPUB }
            // Drain Foundation/SwiftSoup temporaries after EACH document, not
            // after the entire book. The one-document 8MiB ceiling is deliberate.
            try autoreleasepool {
                let chapterData = try reader.read(path, limit: StreamingImportLimits.xhtmlBytes)
                let markup = try TextDecoding.decode(chapterData, allowGB18030: false)
                // Validate depth/node budgets without resolving external DTDs.
                try PackageXML(mode: .content).parse(chapterData)
                let document = try SwiftSoup.parse(markup)
                try document.select("script,style,noscript,iframe,object,embed,svg,math,img,picture,audio,video,canvas,link,template").remove()
                guard let body = document.body() else { throw ImportFailure.empty }
                let heading = try body.select("h1,h2,h3").first()?.text() ?? ""
                let chapterTitle = heading.isEmpty ? "第 \(seen.count) 章" : boundedTitle(heading)
                let visitor = PlainTextVisitor()
                try body.traverse(visitor)
                try emit(chapterTitle, visitor.paragraphs)
            }
        }
        return (boundedTitle(title), package.author)
    }
}

private struct EntryReader {
    let archive: Archive
    let entries: [String: Entry]
    let expandedLimit: Int
    var consumed = 0

    mutating func read(_ path: String, limit: Int) throws -> Data {
        guard let entry = entries[path], entry.type == .file else { throw ImportFailure.malformedEPUB }
        guard entry.uncompressedSize <= UInt64(limit) else { throw ImportFailure.archiveLimit }
        var data = Data()
        var newConsumed = consumed
        let checksum = try archive.extract(entry, bufferSize: 16 * 1_024, skipCRC32: false) { chunk in
            guard chunk.count <= limit - data.count,
                  chunk.count <= expandedLimit - newConsumed else { throw ImportFailure.archiveLimit }
            newConsumed += chunk.count
            data.append(chunk)
        }
        consumed = newConsumed
        guard checksum == entry.checksum, data.count == Int(entry.uncompressedSize) else {
            throw ImportFailure.malformedEPUB
        }
        return data
    }
}

// An offline, bounded XML metadata reader. No filesystem or URL resolvers.
private final class PackageXML: NSObject, XMLParserDelegate {
    enum Mode { case container, package, content }
    struct ManifestItem { let href: String; let mediaType: String }
    struct SpineItem { let id: String; let linear: Bool; let properties: String }
    let mode: Mode
    var rootfiles: [String] = []
    var manifest: [String: ManifestItem] = [:]
    var spine: [SpineItem] = []
    var bookTitle = ""
    var author = ""
    var fixedLayout = false
    private var stack: [String] = []
    private var capture: String?
    private var captureText = ""
    private var captureDepth = 0
    private var metaProperty = ""
    private var failure: Error?
    private var nodes = 0
    private var root = ""

    init(mode: Mode) { self.mode = mode }

    func parse(_ data: Data) throws {
        let source = try TextDecoding.decode(data, allowGB18030: false)
        guard source.range(of: "<!ENTITY", options: .caseInsensitive) == nil,
              mode == .content || source.range(of: "<!DOCTYPE", options: .caseInsensitive) == nil else {
            throw ImportFailure.malformedEPUB
        }
        let xmlData = mode == .content ? try XHTMLNamedEntities.validationData(data, source: source) : data
        let parser = XMLParser(data: xmlData)
        parser.shouldProcessNamespaces = true
        parser.shouldResolveExternalEntities = false
        parser.externalEntityResolvingPolicy = .never
        parser.delegate = self
        let success = parser.parse()
        if let failure { throw failure }
        guard success, stack.isEmpty else { throw ImportFailure.malformedEPUB }
        if mode == .container && root != "container" { throw ImportFailure.malformedEPUB }
        if mode == .package && root != "package" { throw ImportFailure.malformedEPUB }
        if mode == .content && root != "html" { throw ImportFailure.malformedEPUB }
    }

    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?,
                qualifiedName qName: String?, attributes: [String: String]) {
        nodes += 1
        guard stack.count < 128, nodes <= 100_000 else { fail(parser, ImportFailure.complexMarkup); return }
        let name = elementName.lowercased()
        if stack.isEmpty { root = name }
        stack.append(name)
        if mode == .container, name == "rootfile", attributes["media-type"] == "application/oebps-package+xml",
           let href = attributes["full-path"] { rootfiles.append(href) }
        guard mode == .package else { return }
        if name == "item", stack.dropLast().last == "manifest" {
            guard let id = attributes["id"], !id.isEmpty, manifest[id] == nil,
                  let href = attributes["href"], let media = attributes["media-type"] else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            manifest[id] = ManifestItem(href: href, mediaType: media)
        }
        if name == "itemref", stack.dropLast().last == "spine" {
            guard let id = attributes["idref"], spine.count < StreamingImportLimits.chapters else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            spine.append(SpineItem(id: id, linear: attributes["linear"]?.lowercased() != "no",
                                  properties: attributes["properties"] ?? ""))
        }
        if ["title", "creator", "meta"].contains(name), stack.dropLast().last == "metadata" {
            capture = name; captureText = ""; captureDepth = stack.count
            metaProperty = attributes["property"] ?? ""
            if attributes["name"] == "fixed-layout", attributes["content"] == "true" { fixedLayout = true }
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if capture != nil {
            guard captureText.utf16.count + string.utf16.count <= 4_096 else {
                fail(parser, ImportFailure.malformedEPUB); return
            }
            captureText += string
        }
    }

    func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
        if let captured = capture, captureDepth == stack.count {
            let value = captureText.trimmingCharacters(in: .whitespacesAndNewlines)
            if captured == "title", bookTitle.isEmpty { bookTitle = String(value.prefix(240)) }
            if captured == "creator", author.isEmpty { author = String(value.prefix(240)) }
            if captured == "meta", metaProperty == "rendition:layout", value.lowercased() == "pre-paginated" {
                fixedLayout = true
            }
            capture = nil
        }
        if !stack.isEmpty { stack.removeLast() }
    }

    func parser(_ parser: XMLParser, foundCDATA CDATABlock: Data) {
        if let text = String(data: CDATABlock, encoding: .utf8) { self.parser(parser, foundCharacters: text) }
    }
    func parser(_ parser: XMLParser, resolveExternalEntityName name: String, systemID: String?) -> Data? { nil }
    func parser(_ parser: XMLParser, parseErrorOccurred parseError: Error) {
        if failure == nil { failure = ImportFailure.malformedEPUB }
    }
    func parser(_ parser: XMLParser, validationErrorOccurred validationError: Error) {
        if failure == nil { failure = ImportFailure.malformedEPUB }
    }
    func parser(_ parser: XMLParser, foundInternalEntityDeclarationWithName name: String, value: String?) {
        fail(parser, ImportFailure.malformedEPUB)
    }
    func parser(_ parser: XMLParser, foundExternalEntityDeclarationWithName name: String, publicID: String?, systemID: String?) {
        fail(parser, ImportFailure.malformedEPUB)
    }
    private func fail(_ parser: XMLParser, _ error: Error) { failure = error; parser.abortParsing() }
}

// EPUB2 frequently uses &nbsp; and other HTML names supplied by an external
// XHTML DTD. Resolve only SwiftSoup's built-in finite table to numeric XML
// references for validation; never load the DTD or accept custom entities.
// Rendering still parses the ORIGINAL markup, so escaped '<' stays text.
private enum XHTMLNamedEntities {
    static func validationData(_ original: Data, source: String) throws -> Data {
        let expression = try NSRegularExpression(pattern: "&([A-Za-z][A-Za-z0-9]{0,31});")
        let ns = source as NSString
        var output = ""
        var cursor = 0
        var count = 0
        var failure: Error?
        expression.enumerateMatches(in: source, range: NSRange(location: 0, length: ns.length)) { match, _, stop in
            guard let match else { return }
            count += 1
            guard count <= 100_000 else {
                failure = ImportFailure.complexMarkup; stop.pointee = true; return
            }
            output += ns.substring(with: NSRange(location: cursor, length: match.range.location - cursor))
            let name = ns.substring(with: match.range(at: 1))
            if ["amp", "lt", "gt", "quot", "apos"].contains(name) {
                output += ns.substring(with: match.range)
            } else if Entities.isNamedEntity(name), let scalars = Entities.codepointsForName(name), scalars.count <= 2 {
                for scalar in scalars { output += "&#x" + String(scalar.value, radix: 16) + ";" }
            } else {
                failure = ImportFailure.malformedEPUB; stop.pointee = true; return
            }
            guard output.utf8.count <= ImportLimits.entryBytes * 2 else {
                failure = ImportFailure.archiveLimit; stop.pointee = true; return
            }
            cursor = NSMaxRange(match.range)
        }
        if let failure { throw failure }
        output += ns.substring(from: cursor)
        guard output.utf8.count <= ImportLimits.entryBytes * 2 else { throw ImportFailure.archiveLimit }
        // Preserve BOM encoding so an existing XML encoding declaration agrees.
        if original.starts(with: [0xff, 0xfe]) {
            guard let encoded = output.data(using: .utf16LittleEndian) else { throw ImportFailure.invalidText }
            return Data([0xff, 0xfe]) + encoded
        }
        if original.starts(with: [0xfe, 0xff]) {
            guard let encoded = output.data(using: .utf16BigEndian) else { throw ImportFailure.invalidText }
            return Data([0xfe, 0xff]) + encoded
        }
        return Data(output.utf8)
    }
}

private final class PlainTextVisitor: NodeVisitor {
    private(set) var paragraphs: [String] = []
    private var current = ""
    private var textBytes = 0
    private var nodes = 0
    private static let blocks: Set<String> = ["p", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "tr", "dt", "dd", "hr"]

    func head(_ node: Node, _ depth: Int) throws {
        nodes += 1
        guard depth <= 128, nodes <= 100_000 else { throw ImportFailure.complexMarkup }
        if let text = node as? TextNode {
            let whole = text.getWholeText()
            guard whole.utf8.count <= ImportLimits.textBytes - textBytes else { throw ImportFailure.oversized }
            textBytes += whole.utf8.count
            current += whole
        } else if let element = node as? Element {
            let tag = element.tagName().lowercased()
            if Self.blocks.contains(tag) || tag == "br" { try flush() }
            if tag == "td" || tag == "th" { current += " " }
        }
    }
    func tail(_ node: Node, _ depth: Int) throws {
        if let element = node as? Element,
           Self.blocks.contains(element.tagName().lowercased()) || depth == 0 { try flush() }
    }
    private func flush() throws {
        let value = current.trimmingCharacters(in: .whitespacesAndNewlines)
        if !value.isEmpty {
            guard paragraphs.count < ImportLimits.paragraphs else { throw ImportFailure.oversized }
            paragraphs.append(value)
        }
        current = ""
    }
}
