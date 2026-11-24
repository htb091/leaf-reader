import Foundation

// ZIPFoundation deliberately hides encryption flags and stops iteration on an
// encrypted entry. Inspect every central + local header before using its API.
// This is a narrow ZIP32 validator, not an alternative decompressor.
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
        guard data.count >= 22, data.count <= ImportLimits.fileBytes else { throw ImportFailure.malformedEPUB }
        let first = max(0, data.count - 22 - 65_535)
        var end: Int?
        for offset in stride(from: data.count - 22, through: first, by: -1) {
            if try data.zipU32(offset) == 0x06054b50,
               offset + 22 + Int(try data.zipU16(offset + 20)) == data.count {
                end = offset; break
            }
        }
        guard let end else { throw ImportFailure.malformedEPUB }
        let disk = try data.zipU16(end + 4)
        let directoryDisk = try data.zipU16(end + 6)
        let diskEntries = try data.zipU16(end + 8)
        let count = Int(try data.zipU16(end + 10))
        let directorySize = Int(try data.zipU32(end + 12))
        let directoryOffset = Int(try data.zipU32(end + 16))
        guard disk == 0, directoryDisk == 0, Int(diskEntries) == count,
              count > 0, count <= ImportLimits.entries, count != 65_535,
              directoryOffset <= end, directorySize == end - directoryOffset else {
            throw ImportFailure.archiveLimit
        }
        var cursor = directoryOffset
        var expandedTotal = 0
        var result: [String: Record] = [:]
        var ranges: [Range<Int>] = []
        for _ in 0..<count {
            guard cursor <= end - 46, try data.zipU32(cursor) == 0x02014b50 else { throw ImportFailure.malformedEPUB }
            let needed = try data.zipU16(cursor + 6)
            let flags = try data.zipU16(cursor + 8)
            let method = try data.zipU16(cursor + 10)
            let crc = try data.zipU32(cursor + 16)
            let compressed = Int(try data.zipU32(cursor + 20))
            let uncompressed = Int(try data.zipU32(cursor + 24))
            let nameSize = Int(try data.zipU16(cursor + 28))
            let extraSize = Int(try data.zipU16(cursor + 30))
            let commentSize = Int(try data.zipU16(cursor + 32))
            let startDisk = try data.zipU16(cursor + 34)
            let attributes = try data.zipU32(cursor + 38)
            let local = Int(try data.zipU32(cursor + 42))
            guard flags & 0x2041 == 0 else { throw ImportFailure.encrypted } // traditional/strong/masked
            guard needed < 45, startDisk == 0, method == 0 || method == 8,
                  compressed <= ImportLimits.fileBytes,
                  uncompressed <= ImportLimits.entryBytes,
                  uncompressed <= ImportLimits.expandedBytes - expandedTotal,
                  uncompressed <= max(compressed, 1) * ImportLimits.compressionRatio else {
                throw ImportFailure.archiveLimit
            }
            let next = cursor + 46 + nameSize + extraSize + commentSize
            guard nameSize > 0, nameSize <= 1_024, next <= end else { throw ImportFailure.malformedEPUB }
            let nameData = data.subdata(in: cursor + 46..<cursor + 46 + nameSize)
            // EPUB mandates UTF-8 entry names; ASCII names work with or without bit 11.
            guard let path = String(data: nameData, encoding: .utf8) else { throw ImportFailure.unsafePath }
            try ArchivePath.validateEntry(path)
            guard result[path] == nil else { throw ImportFailure.unsafePath }
            let mode = (attributes >> 16) & 0xf000
            guard mode == 0 || mode == 0x8000 || mode == 0x4000 else { throw ImportFailure.unsafePath }
            try Self.validateExtra(data, start: cursor + 46 + nameSize, length: extraSize)
            guard local >= 0, local <= directoryOffset - 30,
                  try data.zipU32(local) == 0x04034b50 else { throw ImportFailure.malformedEPUB }
            let localFlags = try data.zipU16(local + 6)
            guard localFlags & 0x2041 == 0 else { throw ImportFailure.encrypted }
            let localNameSize = Int(try data.zipU16(local + 26))
            let localExtraSize = Int(try data.zipU16(local + 28))
            let contentOffset = local + 30 + localNameSize + localExtraSize
            guard localFlags == flags, try data.zipU16(local + 8) == method,
                  try data.zipU16(local + 4) < 45, localNameSize == nameSize,
                  contentOffset <= directoryOffset, compressed <= directoryOffset - contentOffset,
                  data.subdata(in: local + 30..<local + 30 + localNameSize) == nameData else {
                throw ImportFailure.malformedEPUB
            }
            try Self.validateExtra(data, start: local + 30 + localNameSize, length: localExtraSize)
            var contentEnd = contentOffset + compressed
            if flags & 8 != 0 {
                // Only signed ZIP32 descriptors are supported; reject ambiguous records.
                guard contentEnd <= directoryOffset - 16,
                      try data.zipU32(contentEnd) == 0x08074b50,
                      try data.zipU32(contentEnd + 4) == crc,
                      Int(try data.zipU32(contentEnd + 8)) == compressed,
                      Int(try data.zipU32(contentEnd + 12)) == uncompressed else {
                    throw ImportFailure.malformedEPUB
                }
                contentEnd += 16
            } else {
                guard try data.zipU32(local + 14) == crc,
                      Int(try data.zipU32(local + 18)) == compressed,
                      Int(try data.zipU32(local + 22)) == uncompressed else { throw ImportFailure.malformedEPUB }
            }
            ranges.append(local..<contentEnd)
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

    private static func validateExtra(_ data: Data, start: Int, length: Int) throws {
        var offset = start
        let end = start + length
        guard end <= data.count else { throw ImportFailure.malformedEPUB }
        while offset < end {
            guard offset <= end - 4 else { throw ImportFailure.malformedEPUB }
            let kind = try data.zipU16(offset)
            let size = Int(try data.zipU16(offset + 2))
            guard kind != 0x0001 else { throw ImportFailure.archiveLimit } // ZIP64
            guard kind != 0x9901 else { throw ImportFailure.encrypted } // WinZip AES
            offset += 4 + size
            guard offset <= end else { throw ImportFailure.malformedEPUB }
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
            // Do not accept encoded separators, traversal components or control bytes.
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
