@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

package dev.leaf.reader

import kotlinx.cinterop.addressOf
import kotlinx.cinterop.usePinned
import platform.Foundation.NSApplicationSupportDirectory
import platform.Foundation.NSFileManager
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSString
import platform.Foundation.NSUserDomainMask
import platform.Foundation.NSUTF8StringEncoding
import platform.Foundation.create
import platform.posix.fclose
import platform.posix.fflush
import platform.posix.fileno
import platform.posix.fopen
import platform.posix.fsync
import platform.posix.fwrite
import platform.posix.remove
import platform.posix.rename
import kotlin.time.Clock

actual fun defaultReaderFiles(): ReaderFiles = IosReaderFiles()

private class IosReaderFiles : ReaderFiles {
    private val manager = NSFileManager.defaultManager
    private val root: String = (NSSearchPathForDirectoriesInDomains(
        NSApplicationSupportDirectory, NSUserDomainMask, true,
    ).first() as String) + "/LeafReader"

    init { check(manager.createDirectoryAtPath(root, true, null, null)) { "建立本地书库目录失败。" } }

    private fun path(name: String): String {
        require(Regex("[a-zA-Z0-9_.-]+").matches(name))
        return "$root/$name"
    }

    override fun readText(name: String): String? {
        val file = path(name)
        if (!manager.fileExistsAtPath(file)) return null
        return (NSString.create(contentsOfFile = file, encoding = NSUTF8StringEncoding, error = null) as String?)
            ?: error("读取本地书库文件失败。")
    }

    /** Preserve the working POSIX bridge, but write a sibling then atomically rename over the old file. */
    override fun writeText(name: String, value: String) {
        val file = path(name)
        val temporary = "$file.tmp"
        val bytes = value.encodeToByteArray()
        val stream = fopen(temporary, "wb") ?: error("建立临时书库文件失败。")
        var closed = false
        var published = false
        try {
            if (bytes.isNotEmpty()) {
                val written = bytes.usePinned { pinned -> fwrite(pinned.addressOf(0), 1uL, bytes.size.toULong(), stream) }
                check(written.toLong() == bytes.size.toLong()) { "写入本地书库失败。" }
            }
            check(fflush(stream) == 0 && fsync(fileno(stream)) == 0) { "同步本地书库失败。" }
            val closeResult = fclose(stream)
            closed = true
            check(closeResult == 0) { "关闭书库文件失败。" }
            check(rename(temporary, file) == 0) { "提交书库文件失败，旧文件已保留。" }
            published = true
        } finally {
            if (!closed) fclose(stream)
            if (!published) remove(temporary)
        }
    }

    override fun delete(name: String) {
        val file = path(name)
        if (manager.fileExistsAtPath(file)) check(manager.removeItemAtPath(file, null)) { "清理书籍文件失败。" }
    }
    override fun nowMillis(): Long = Clock.System.now().toEpochMilliseconds()
}
