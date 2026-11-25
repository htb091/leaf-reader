import Foundation

// ZIPFoundation hides encrypted entries during iteration. Inspect every central
// and local header first. File imports read only the EOCD tail and one bounded
// header/extra field at a time; compressed payloads are never loaded here.
// Narrow ZIP32 only: reject ZIP64, multi-volume and unsigned descriptors.
struct ZIPPreflight {
    struct Record {
        let path: String
        let compressedSize: Int
        let uncompressedSize: Int
        let checksum: UInt32
        let isDirectory: Bool
    }
    let records: [String: Record]

    init(data: Data) throws {
        try self.init(size: data.count, fileLimit: ImportLimits.fileBytes,
                      entryLimit: ImportLimits.entryBytes, expandedLimit: ImportLimits.expandedBytes,
                      entryCountLimit: ImportLimits.entries) { offset, length in
            guard offset >= 0, length >= 0, offset <= data.count, length <= data.count - offset else {
                throw ImportFailure.malformedEPUB
            }
            return data.subdata(in: offset..<offset + length)
        }
    }

    init(fileURL: URL) throws {
        let file = try FileHandle(forReadingFrom: fileURL)
        defer { try? file.close() }
        let length = try file.seekToEnd()
        guard length <= UInt64(StreamingImportLimits.epubBytes) else { throw ImportFailure.oversized }
        try self.init(size: Int(length), fileLimit: StreamingImportLimits.epubBytes,
                      entryLimit: StreamingImportLimits.archiveEntryBytes,
                      expandedLimit: StreamingImportLimits.expandedBytes,
                      entryCountLimit: StreamingImportLimits.archiveEntries) { offset, count in
            guard offset >= 0, count >= 0, offset <= Int(length), count <= Int(length) - offset else {
                throw ImportFailure.malformedEPUB
            }
            try file.seek(toOffset: UInt64(offset))
            var result = Data()
            while result.count < count {
                guard let bytes = try autoreleasepool(invoking: { try file.read(upToCount: count - result.count) }), !bytes.isEmpty else {
                    throw ImportFailure.malformedEPUB
                }
                result.append(bytes)
            }
            return result
        }
    }

    private init(size: Int, fileLimit: Int, entryLimit: Int, expandedLimit: Int,
                 entryCountLimit: Int, read: (Int, Int) throws -> Data) throws {
        guard size >= 22, size <= fileLimit else { throw ImportFailure.malformedEPUB }
        let tailOffset = max(0, size - 22 - 65_535)
        let tail = try read(tailOffset, size - tailOffset)
        var found: Int?
        for offset in stride(from: tail.count - 22, through: 0, by: -1) {
            if try tail.zipU32(offset) == 0x06054b50,
               offset + 22 + Int(try tail.zipU16(offset + 20)) == tail.count {
                found = offset; break
            }
        }
        guard let endInTail = found else { throw ImportFailure.malformedEPUB }
        let end = tailOffset + endInTail
        let disk = try tail.zipU16(endInTail + 4)
        let directoryDisk = try tail.zipU16(endInTail + 6)
        let diskEntries = Int(try tail.zipU16(endInTail + 8))
        let count = Int(try tail.zipU16(endInTail + 10))
        let directorySize = Int(try tail.zipU32(endInTail + 12))
        let directoryOffset = Int(try tail.zipU32(endInTail + 16))
        guard disk == 0, directoryDisk == 0, diskEntries == count,
              count > 0, count <= entryCountLimit, count != 65_535,
              directoryOffset <= end, directorySize == end - directoryOffset,
              directorySize <= StreamingImportLimits.archiveMetadataBytes else {
            throw ImportFailure.archiveLimit
        }
        var cursor = directoryOffset
        var expandedTotal = 0
        var metadataBytes = 0
        var result: [String: Record] = [:]
        var ranges: [Range<Int>] = []
        for _ in 0..<count {
            guard cursor <= end - 46 else { throw ImportFailure.malformedEPUB }
            let central = try read(cursor, 46)
            guard try central.zipU32(0) == 0x02014b50 else { throw ImportFailure.malformedEPUB }
            let needed = try central.zipU16(6)
            let flags = try central.zipU16(8)
            let method = try central.zipU16(10)
            let crc = try central.zipU32(16)
            let compressed = Int(try central.zipU32(20))
            let uncompressed = Int(try central.zipU32(24))
            let nameSize = Int(try central.zipU16(28))
            let extraSize = Int(try central.zipU16(30))
            let commentSize = Int(try central.zipU16(32))
            let startDisk = try central.zipU16(34)
            let attributes = try central.zipU32(38)
            let localOffset = Int(try central.zipU32(42))
            guard flags & 0x2041 == 0 else { throw ImportFailure.encrypted }
            guard needed < 45, startDisk == 0, method == 0 || method == 8,
                  flags & ~UInt16(0x080e) == 0, method != 0 || compressed == uncompressed,
                  compressed <= fileLimit, uncompressed <= entryLimit,
                  uncompressed <= expandedLimit - expandedTotal,
                  uncompressed <= max(compressed, 1) * ImportLimits.compressionRatio else {
                throw ImportFailure.archiveLimit
            }
            let next = cursor + 46 + nameSize + extraSize + commentSize
            guard nameSize > 0, nameSize <= 1_024, next <= end else { throw ImportFailure.malformedEPUB }
            let nameData = try read(cursor + 46, nameSize)
            guard let path = String(data: nameData, encoding: .utf8) else { throw ImportFailure.unsafePath }
            try ArchivePath.validateEntry(path)
            guard result[path] == nil else { throw ImportFailure.unsafePath }
            let mode = (attributes >> 16) & 0xf000
            guard mode == 0 || mode == 0x8000 || mode == 0x4000 else { throw ImportFailure.unsafePath }
            try Self.validateExtra(try read(cursor + 46 + nameSize, extraSize))
            guard localOffset <= directoryOffset - 30 else { throw ImportFailure.malformedEPUB }
            let local = try read(localOffset, 30)
            guard try local.zipU32(0) == 0x04034b50 else { throw ImportFailure.malformedEPUB }
            let localFlags = try local.zipU16(6)
            guard localFlags & 0x2041 == 0 else { throw ImportFailure.encrypted }
            let localNameSize = Int(try local.zipU16(26))
            let localExtraSize = Int(try local.zipU16(28))
            let contentOffset = localOffset + 30 + localNameSize + localExtraSize
            metadataBytes += 46 + nameSize + extraSize + commentSize + 30 + localNameSize + localExtraSize
            // Entry retains central/local extras. Bound their aggregate as well
            // as individual reads, before ZIPFoundation constructs those objects.
            guard metadataBytes <= StreamingImportLimits.archiveMetadataBytes else { throw ImportFailure.archiveLimit }
            guard localFlags == flags, try local.zipU16(8) == method, try local.zipU16(4) < 45,
                  localNameSize == nameSize, contentOffset <= directoryOffset,
                  compressed <= directoryOffset - contentOffset else { throw ImportFailure.malformedEPUB }
            guard try read(localOffset + 30, localNameSize) == nameData else { throw ImportFailure.malformedEPUB }
            try Self.validateExtra(try read(localOffset + 30 + localNameSize, localExtraSize))
            var contentEnd = contentOffset + compressed
            if flags & 8 != 0 {
                guard contentEnd <= directoryOffset - 16 else { throw ImportFailure.malformedEPUB }
                let descriptor = try read(contentEnd, 16)
                guard try descriptor.zipU32(0) == 0x08074b50, try descriptor.zipU32(4) == crc,
                      Int(try descriptor.zipU32(8)) == compressed,
                      Int(try descriptor.zipU32(12)) == uncompressed else { throw ImportFailure.malformedEPUB }
                contentEnd += 16
            } else {
                guard try local.zipU32(14) == crc, Int(try local.zipU32(18)) == compressed,
                      Int(try local.zipU32(22)) == uncompressed else { throw ImportFailure.malformedEPUB }
            }
            ranges.append(localOffset..<contentEnd)
            expandedTotal += uncompressed
            result[path] = Record(path: path, compressedSize: compressed, uncompressedSize: uncompressed,
                                  checksum: crc, isDirectory: path.hasSuffix("/"))
            cursor = next
        }
        guard cursor == end else { throw ImportFailure.malformedEPUB }
        let sorted = ranges.sorted { $0.lowerBound < $1.lowerBound }
        for index in 1..<sorted.count where sorted[index - 1].upperBound > sorted[index].lowerBound {
            throw ImportFailure.malformedEPUB
        }
        if result.keys.contains(where: {
            ["meta-inf/encryption.xml", "meta-inf/rights.xml", "meta-inf/license.lcpl"].contains($0.lowercased())
        }) { throw ImportFailure.encrypted }
        records = result
    }

    private static func validateExtra(_ data: Data) throws {
        var offset = 0
        while offset < data.count {
            guard offset <= data.count - 4 else { throw ImportFailure.malformedEPUB }
            let kind = try data.zipU16(offset)
            let size = Int(try data.zipU16(offset + 2))
            guard kind != 0x0001 else { throw ImportFailure.archiveLimit }
            guard kind != 0x9901 else { throw ImportFailure.encrypted }
            offset += 4 + size
            guard offset <= data.count else { throw ImportFailure.malformedEPUB }
        }
    }
}

enum ArchivePath {
    static func validateEntry(_ path: String) throws {
        guard !path.isEmpty, !path.hasPrefix("/"), !path.contains("\\"), !path.contains(":"),
              !path.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            throw ImportFailure.unsafePath
        }
        let body = path.hasSuffix("/") ? String(path.dropLast()) : path
        let parts = body.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.contains(where: { $0.isEmpty || $0 == "." || $0 == ".." }) else { throw ImportFailure.unsafePath }
        if let decoded = path.removingPercentEncoding, decoded != path {
            guard !decoded.contains("\\"), !decoded.contains(":"),
                  decoded.split(separator: "/", omittingEmptySubsequences: false).count == path.split(separator: "/", omittingEmptySubsequences: false).count,
                  !decoded.split(separator: "/").contains(where: { $0 == "." || $0 == ".." }),
                  !decoded.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
                throw ImportFailure.unsafePath
            }
        }
    }

    static func resolve(_ href: String, relativeTo file: String = "") throws -> String {
        let reference = String(href.prefix { $0 != "#" && $0 != "?" })
        guard let decoded = reference.removingPercentEncoding, !decoded.isEmpty,
              !decoded.hasPrefix("/"), !decoded.contains("\\"), !decoded.contains(":"),
              !decoded.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) else {
            throw ImportFailure.unsafePath
        }
        var parts = file.split(separator: "/").dropLast().map(String.init)
        for part in decoded.split(separator: "/", omittingEmptySubsequences: false) {
            if part == ".." {
                guard !parts.isEmpty else { throw ImportFailure.unsafePath }
                parts.removeLast()
            } else if part != "." {
                guard !part.isEmpty else { throw ImportFailure.unsafePath }
                parts.append(String(part))
            }
        }
        let path = parts.joined(separator: "/")
        try validateEntry(path)
        return path
    }
}

private extension Data {
    func zipU16(_ offset: Int) throws -> UInt16 {
        guard offset >= 0, offset <= count - 2 else { throw ImportFailure.malformedEPUB }
        return UInt16(self[offset]) | (UInt16(self[offset + 1]) << 8)
    }
    func zipU32(_ offset: Int) throws -> UInt32 {
        guard offset >= 0, offset <= count - 4 else { throw ImportFailure.malformedEPUB }
        return UInt32(self[offset]) | (UInt32(self[offset + 1]) << 8)
            | (UInt32(self[offset + 2]) << 16) | (UInt32(self[offset + 3]) << 24)
    }
}
