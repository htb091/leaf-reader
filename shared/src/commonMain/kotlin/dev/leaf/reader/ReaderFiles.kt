package dev.leaf.reader

/** App-private storage. writeText must replace atomically or throw without damaging the old file. */
interface ReaderFiles {
    fun readText(name: String): String?
    fun writeText(name: String, value: String)
    fun delete(name: String)
    fun nowMillis(): Long
}

expect fun defaultReaderFiles(): ReaderFiles
