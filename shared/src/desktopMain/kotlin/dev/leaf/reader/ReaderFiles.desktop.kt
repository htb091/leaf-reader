package dev.leaf.reader

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption

actual fun defaultReaderFiles(): ReaderFiles = DesktopReaderFiles(
    Path.of(System.getProperty("leaf.reader.home", System.getProperty("user.home") + "/.leaf-reader")),
)

private class DesktopReaderFiles(private val root: Path) : ReaderFiles {
    init { Files.createDirectories(root) }
    private fun path(name: String): Path {
        require(Regex("[a-zA-Z0-9_.-]+").matches(name))
        return root.resolve(name)
    }
    override fun readText(name: String): String? = path(name).let { if (Files.exists(it)) Files.readString(it) else null }
    override fun writeText(name: String, value: String) {
        val target = path(name)
        val temporary = path("$name.tmp")
        Files.writeString(temporary, value)
        Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }
    override fun delete(name: String) { Files.deleteIfExists(path(name)) }
    override fun nowMillis(): Long = System.currentTimeMillis()
}
