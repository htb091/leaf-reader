#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LeafReader v0.3 offline source upgrade (Python 3.8+, standard library only).

Usage: python3 LeafReader-v0.3-upgrade.py --project PATH [--archive PATH]
Review FILES below before use. No network, package installation, subprocess,
credential discovery, Git operation or downloaded-code execution is performed.
It writes the 32 frozen source files plus two version scalars in iosApp/project.yml.
Overwritten files are copied to .leaf-upgrade-backup/<UTC>/ with a change manifest.
Atomicity is per file (same-directory tempfile + os.replace).
Kotlin/Swift compilation and regression tests belong to CI, not this tool.
"""

import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import tempfile
import zipfile

FILES = {
    'shared/src/commonMain/kotlin/dev/leaf/reader/Models.kt': r'''package dev.leaf.reader

import kotlinx.serialization.Serializable

@Serializable
data class BookChapter(val title: String, val paragraphs: List<String>)

/** Legacy import DTO. Opened books now carry titles only; state.chapter owns the loaded body. */
@Serializable
data class BookDocument(val id: String, val title: String, val author: String = "", val format: String = "TXT", val chapters: List<BookChapter>)

@Serializable
data class ChapterEntry(
    val title: String,
    val fileName: String,
    val paragraphCount: Int,
    val characterCount: Int,
    val sourceChapterIndex: Int? = null,
    val sourceParagraphStart: Int = 0,
)

@Serializable
data class BookManifest(
    val schema: Int = 2,
    val id: String,
    val title: String,
    val author: String = "",
    val format: String = "TXT",
    val revision: String,
    val chapters: List<ChapterEntry>,
) {
    fun metadata(): BookDocument = BookDocument(id, title, author, format, chapters.map { BookChapter(it.title, emptyList()) })
    fun paragraphCount(): Int = chapters.sumOf { it.paragraphCount }
    fun characterCount(): Long = chapters.sumOf { it.characterCount.toLong() }
    fun chapterStart(index: Int): Int = chapters.take(index).sumOf { it.paragraphCount + 1 }
    fun totalItems(): Int = paragraphCount() + chapters.size
}

@Serializable
data class ReadingProgress(
    val itemIndex: Int = 0,
    val scrollOffset: Int = 0,
    val chapterIndex: Int = -1,
    val paragraphIndex: Int = 0,
    val characterOffset: Int = 0,
)

@Serializable
data class ShelfBook(
    val id: String,
    val title: String,
    val author: String,
    val format: String,
    val chapterCount: Int,
    val paragraphCount: Int,
    val addedAt: Long,
    val lastOpenedAt: Long = 0,
    val progress: ReadingProgress = ReadingProgress(),
    val characterCount: Long = 0,
)

@Serializable enum class ReaderTheme { SYSTEM, LIGHT, DARK, SEPIA }
@Serializable enum class ReadingMode { SCROLL, SLIDE, INSTANT }
@Serializable enum class ColumnMode { AUTO, SINGLE, DOUBLE }
@Serializable enum class ShelfLayout { GRID, LIST, COMPACT }
@Serializable enum class ReaderFont { SERIF, SANS, MONO }

@Serializable
data class ReaderSettings(
    val fontSize: Float = 20f,
    val lineHeight: Float = 1.7f,
    val theme: ReaderTheme = ReaderTheme.SYSTEM,
    val readingMode: ReadingMode = ReadingMode.SLIDE,
    val columnMode: ColumnMode = ColumnMode.AUTO,
    val shelfLayout: ShelfLayout = ShelfLayout.GRID,
    val fontFamily: ReaderFont = ReaderFont.SERIF,
    val horizontalMargin: Float = 24f,
    val paragraphSpacing: Float = 12f,
    val letterSpacing: Float = 0f,
    val firstLineIndent: Boolean = true,
    val bold: Boolean = false,
    val autoHideControls: Boolean = true,
    val showReadingFooter: Boolean = true,
) {
    fun sanitized() = copy(
        fontSize = fontSize.finiteOr(20f).coerceIn(14f, 40f),
        lineHeight = lineHeight.finiteOr(1.7f).coerceIn(1.2f, 2.4f),
        horizontalMargin = horizontalMargin.finiteOr(24f).coerceIn(8f, 56f),
        paragraphSpacing = paragraphSpacing.finiteOr(12f).coerceIn(0f, 40f),
        letterSpacing = letterSpacing.finiteOr(0f).coerceIn(-0.5f, 3f),
    )
}
private fun Float.finiteOr(fallback: Float): Float = if (isFinite()) this else fallback

data class LibraryState(
    val books: List<ShelfBook> = emptyList(),
    val currentBook: BookDocument? = null,
    val currentProgress: ReadingProgress = ReadingProgress(),
    val settings: ReaderSettings = ReaderSettings(),
    val busy: Boolean = false,
    val error: String? = null,
    val manifest: BookManifest? = null,
    val chapter: BookChapter? = null,
    val chapterIndex: Int = 0,
    val chapterBusy: Boolean = false,
    val chromeVisible: Boolean = false,
)

@Serializable
internal data class LibrarySnapshot(val schema: Int = 2, val books: List<ShelfBook> = emptyList(), val settings: ReaderSettings = ReaderSettings())
internal val documentIdPattern = Regex("[a-f0-9]{64}")
internal val revisionPattern = Regex("[a-f0-9]{32}")
internal const val MAX_CHAPTER_UNITS = 512 * 1024

internal fun BookManifest.validate() {
    require(schema == 2 && documentIdPattern.matches(id) && revisionPattern.matches(revision)) { "书籍索引版本或标识异常。" }
    require(title.isNotBlank() && title.length <= 1000 && author.length <= 2000) { "书籍信息异常。" }
    require(format in setOf("TXT", "EPUB")) { "支持 TXT 和 EPUB。" }
    require(chapters.isNotEmpty() && chapters.size <= 50000) { "章节数量超出范围。" }
    require(chapters.sumOf { it.paragraphCount.toLong() } in 1L..2_000_000L) { "段落数量超出范围。" }
    require(characterCount() in 1L..(512L * 1024 * 1024)) { "正文数量超出范围。" }
    chapters.forEachIndexed { index, chapter ->
        require(chapter.fileName == "book-$id-$revision-c$index.json") { "章节文件标识异常。" }
        require(chapter.title.length <= 1000 && chapter.paragraphCount in 0..100000 && chapter.characterCount in 0..MAX_CHAPTER_UNITS) { "章节信息异常。" }
    }
    if (chapters.any { it.sourceChapterIndex != null }) {
        require(chapters.all { it.sourceChapterIndex != null } && chapters.first().sourceChapterIndex == 0) { "旧章节映射不完整。" }
        var source = 0
        var start = 0
        chapters.forEach { entry ->
            val index = checkNotNull(entry.sourceChapterIndex)
            if (index != source) {
                require(index == source + 1) { "旧章节映射顺序异常。" }
                source = index; start = 0
            }
            require(index == source && index in 0..49999 && entry.sourceParagraphStart == start) { "旧段落映射异常。" }
            start += entry.paragraphCount
        }
    }
}

internal fun BookChapter.validate(entry: ChapterEntry? = null) {
    require(title.length <= 1000 && paragraphs.size <= 100000) { "章节大小异常。" }
    var units = 0L
    paragraphs.forEach { paragraph ->
        require(paragraph.length <= 16000) { "单段文字过长，请重新导入分段。" }
        units += paragraph.length
    }
    require(units <= MAX_CHAPTER_UNITS) { "章节过长，请使用分章导入。" }
    if (entry != null) require(title == entry.title && paragraphs.size == entry.paragraphCount && units == entry.characterCount.toLong()) { "章节文件与索引不一致。" }
}

internal fun BookDocument.validate() {
    require(documentIdPattern.matches(id)) { "书籍标识异常。" }
    require(title.isNotBlank() && title.length <= 1000 && author.length <= 2000) { "书籍信息异常。" }
    require(format in setOf("TXT", "EPUB") && chapters.isNotEmpty() && chapters.size <= 50000)
    require(chapters.sumOf { it.paragraphs.size.toLong() } in 1L..2_000_000L)
    var units = 0L
    var text = false
    chapters.forEach { chapter ->
        require(chapter.title.length <= 1000)
        chapter.paragraphs.forEach { paragraph ->
            require(paragraph.length <= 16000)
            units += paragraph.length
            if (paragraph.isNotBlank()) text = true
        }
    }
    require(text && units <= 24L * 1024 * 1024) { "旧格式导入仅用于兼容；大书请使用新版分章导入。" }
}

internal fun BookDocument.itemCount(): Int = chapters.sumOf { 1 + it.paragraphs.size }
internal fun ReadingProgress.clamp(itemCount: Int): ReadingProgress = copy(itemIndex = itemIndex.coerceIn(0, (itemCount - 1).coerceAtLeast(0)), scrollOffset = scrollOffset.coerceIn(0, 100000))

internal fun BookManifest.normalize(progress: ReadingProgress): ReadingProgress {
    val global = progress.itemIndex.coerceIn(0, totalItems() - 1)
    var chapterIndex = progress.chapterIndex
    var local = progress.paragraphIndex
    if (chapterIndex !in chapters.indices) {
        var offset = global
        chapterIndex = 0
        for ((index, entry) in chapters.withIndex()) {
            chapterIndex = index
            if (offset <= entry.paragraphCount) break
            offset -= entry.paragraphCount + 1
        }
        local = offset
    }
    val entry = chapters[chapterIndex]
    local = local.coerceIn(0, entry.paragraphCount)
    return progress.copy(itemIndex = chapterStart(chapterIndex) + local, chapterIndex = chapterIndex,
        paragraphIndex = local, characterOffset = progress.characterOffset.coerceAtLeast(0), scrollOffset = progress.scrollOffset.coerceIn(0, 100000))
}

internal fun clampUtf16(text: String, offset: Int): Int {
    val result = offset.coerceIn(0, text.length)
    return if (result > 0 && result < text.length && text[result - 1].isHighSurrogate() && text[result].isLowSurrogate()) result - 1 else result
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ReaderStore.kt': r'''package dev.leaf.reader

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.random.Random

/** Main-thread state host. Book bodies are stored and loaded one bounded chapter at a time. */
class ReaderStore(
    private val files: ReaderFiles = defaultReaderFiles(),
    private val scope: CoroutineScope = MainScope(),
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val mutableState = MutableStateFlow(LibraryState())
    val state: StateFlow<LibraryState> = mutableState.asStateFlow()
    private val documentOperations = Mutex()
    private val chapterCache = LinkedHashMap<String, BookChapter>()
    private var saveJob: Job? = null
    private var openGeneration = 0L
    private var chapterGeneration = 0L
    private var persistenceBlocked = false

    init { loadLibrary() }

    private fun loadLibrary() {
        try {
            val raw = files.readText("library.json") ?: return
            val snapshot = json.decodeFromString<LibrarySnapshot>(raw)
            require(snapshot.schema in 1..2) { "书库版本较新，请使用匹配的应用版本。" }
            require(snapshot.books.size <= 10000)
            require(snapshot.books.all {
                documentIdPattern.matches(it.id) && it.title.isNotBlank() && it.chapterCount in 1..50000 &&
                    it.paragraphCount in 1..2_000_000 && it.format in setOf("TXT", "EPUB")
            })
            require(snapshot.books.map { it.id }.distinct().size == snapshot.books.size)
            if (snapshot.schema == 1 && files.readText("library.v1-backup.json") == null) {
                files.writeText("library.v1-backup.json", raw)
            }
            mutableState.value = LibraryState(
                books = snapshot.books.map { it.copy(progress = it.progress.clamp(it.paragraphCount + it.chapterCount)) },
                settings = snapshot.settings.sanitized(),
            )
        } catch (_: Exception) {
            persistenceBlocked = true
            mutableState.value = LibraryState(error = "书库索引读取失败，原文件已保留；已暂停自动覆盖，请先备份应用数据。")
        }
    }

    fun openBook(id: String) {
        if (!documentIdPattern.matches(id) || mutableState.value.books.none { it.id == id }) return
        val generation = ++openGeneration
        ++chapterGeneration
        flush()
        mutableState.value = mutableState.value.copy(busy = true, chapterBusy = false, error = null)
        scope.launch {
            try {
                val oldEntry = mutableState.value.books.firstOrNull { it.id == id } ?: return@launch
                val loaded = withContext(ioDispatcher) {
                    val raw = files.readText(manifestName(id))
                    if (raw != null) {
                        val manifest = json.decodeFromString<BookManifest>(raw).also { it.validate(); require(it.id == id) }
                        manifest to legacyAwareProgress(manifest, oldEntry.progress)
                    } else {
                        val legacy = files.readText("book-$id.json") ?: error("书籍副本缺失，请重新导入。")
                        val document = json.decodeFromString<BookDocument>(legacy).also { it.validate(); require(it.id == id) }
                        val migrated = createChapterFiles(document)
                        files.writeText(manifestName(id), json.encodeToString(migrated))
                        migrated to legacyAwareProgress(migrated, oldEntry.progress)
                    }
                }
                if (generation != openGeneration || mutableState.value.books.none { it.id == id }) return@launch
                val manifest = loaded.first
                val progress = loaded.second
                mutableState.value = mutableState.value.copy(
                    books = mutableState.value.books.map { if (it.id == id) it.copy(lastOpenedAt = files.nowMillis(),
                        chapterCount = manifest.chapters.size, paragraphCount = manifest.paragraphCount(),
                        characterCount = manifest.characterCount(), progress = progress) else it },
                    currentBook = manifest.metadata(), manifest = manifest, chapter = null,
                    chapterIndex = progress.chapterIndex, currentProgress = progress, busy = false,
                    chapterBusy = true, chromeVisible = false,
                )
                persistSnapshot()
                requestChapter(manifest, progress)
            } catch (e: Exception) {
                if (e is CancellationException) throw e
                if (generation == openGeneration) mutableState.value = mutableState.value.copy(busy = false,
                    chapterBusy = false, error = "打开失败：${e.message.orEmpty().take(160)}")
            }
        }
    }

    fun selectChapter(index: Int, atEnd: Boolean = false) {
        val manifest = mutableState.value.manifest ?: return
        if (index !in manifest.chapters.indices) return
        val local = if (atEnd) manifest.chapters[index].paragraphCount else 0
        val target = ReadingProgress(manifest.chapterStart(index) + local, 0, index, local,
            if (atEnd) Int.MAX_VALUE else 0)
        requestChapter(manifest, target)
    }

    private fun requestChapter(manifest: BookManifest, progress: ReadingProgress) {
        val generation = ++chapterGeneration
        val index = progress.chapterIndex.coerceIn(manifest.chapters.indices)
        mutableState.value = mutableState.value.copy(chapter = null, chapterIndex = index,
            currentProgress = progress, chapterBusy = true)
        scope.launch {
            try {
                val entry = manifest.chapters[index]
                val chapter = chapterCache[entry.fileName] ?: withContext(ioDispatcher) { readChapter(entry) }
                if (generation != chapterGeneration || mutableState.value.manifest?.revision != manifest.revision ||
                    mutableState.value.currentBook?.id != manifest.id) return@launch
                cache(entry.fileName, chapter)
                val local = progress.paragraphIndex.coerceIn(0, chapter.paragraphs.size)
                val text = if (local == 0) chapter.title else chapter.paragraphs[local - 1]
                val restored = progress.copy(chapterIndex = index, paragraphIndex = local,
                    itemIndex = manifest.chapterStart(index) + local, characterOffset = clampUtf16(text, progress.characterOffset))
                mutableState.value = mutableState.value.copy(chapter = chapter, chapterBusy = false, currentProgress = restored,
                    books = mutableState.value.books.map { if (it.id == manifest.id) it.copy(progress = restored) else it })
                scheduleSave()
            } catch (e: Exception) {
                if (e is CancellationException) throw e
                if (generation == chapterGeneration) mutableState.value = mutableState.value.copy(chapterBusy = false,
                    error = "章节加载失败：${e.message.orEmpty().take(120)}")
            }
        }
    }

    private fun readChapter(entry: ChapterEntry): BookChapter {
        val raw = files.readText(entry.fileName) ?: error("章节文件缺失，请重新导入这本书。")
        require(raw.length <= 4 * 1024 * 1024) { "章节文件超过分章上限。" }
        return json.decodeFromString<BookChapter>(raw).also { it.validate(entry) }
    }

    private fun cache(name: String, chapter: BookChapter) {
        chapterCache.remove(name)
        chapterCache[name] = chapter
        while (chapterCache.size > 3) chapterCache.remove(chapterCache.keys.first())
    }

    fun closeBook() {
        ++openGeneration; ++chapterGeneration
        flush()
        chapterCache.clear()
        mutableState.value = mutableState.value.copy(currentBook = null, manifest = null, chapter = null,
            busy = false, chapterBusy = false, chromeVisible = false)
    }

    fun setChromeVisible(visible: Boolean) { mutableState.value = mutableState.value.copy(chromeVisible = visible) }

    fun updateChapterProgress(paragraphIndex: Int, characterOffset: Int = 0, scrollOffset: Int = 0) {
        val value = mutableState.value
        val manifest = value.manifest ?: return
        val chapter = value.chapter ?: return
        if (value.chapterBusy || value.busy) return
        val local = paragraphIndex.coerceIn(0, chapter.paragraphs.size)
        val text = if (local == 0) chapter.title else chapter.paragraphs[local - 1]
        val progress = ReadingProgress(manifest.chapterStart(value.chapterIndex) + local,
            scrollOffset.coerceIn(0, 100000), value.chapterIndex, local, clampUtf16(text, characterOffset))
        if (progress == value.currentProgress) return
        mutableState.value = value.copy(currentProgress = progress,
            books = value.books.map { if (it.id == manifest.id) it.copy(progress = progress) else it })
        scheduleSave()
    }

    /** Compatibility for old global flattened coordinates; new renderers use chapter anchors. */
    fun updateProgress(itemIndex: Int, scrollOffset: Int) {
        val manifest = mutableState.value.manifest ?: return
        val progress = manifest.normalize(ReadingProgress(itemIndex, scrollOffset))
        if (progress.chapterIndex != mutableState.value.chapterIndex) {
            requestChapter(manifest, progress)
        } else updateChapterProgress(progress.paragraphIndex, 0, scrollOffset)
    }

    fun updateSettings(settings: ReaderSettings) {
        mutableState.value = mutableState.value.copy(settings = settings.sanitized())
        scheduleSave()
    }

    /** Legacy bridge retained for old callers/tests. Native large-file import uses importManifestJson. */
    fun importBookJson(raw: String) {
        if (persistenceBlocked) { reportError("书库索引异常，已保留旧数据并暂停修改。"); return }
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            documentOperations.withLock {
                try {
                    val manifest = withContext(ioDispatcher) {
                        require(raw.length <= 96 * 1024 * 1024) { "请使用新版分章导入大文件。" }
                        val document = json.decodeFromString<BookDocument>(raw).also { it.validate() }
                        files.writeText("book-${document.id}.json", raw)
                        createChapterFiles(document)
                    }
                    publishManifest(manifest)
                } catch (e: Exception) {
                    importFailure(e)
                }
            }
        }
    }

    /** Only small manifest metadata crosses Swift/Kotlin; chapter bodies already exist on disk. */
    fun importManifestJson(raw: String) {
        if (persistenceBlocked) { reportError("书库索引异常，已保留旧数据并暂停修改。"); return }
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            documentOperations.withLock {
                try {
                    val manifest = withContext(ioDispatcher) {
                        require(raw.length <= 16 * 1024 * 1024) { "书籍目录元数据过大。" }
                        json.decodeFromString<BookManifest>(raw).also { it.validate() }
                    }
                    withContext(ioDispatcher) {
                        readChapter(manifest.chapters.first())
                        if (manifest.chapters.size > 1) readChapter(manifest.chapters.last())
                    }
                    publishManifest(manifest)
                } catch (e: Exception) {
                    importFailure(e)
                }
            }
        }
    }

    private fun publishManifest(manifest: BookManifest): Boolean {
        manifest.validate()
        val name = manifestName(manifest.id)
        val previousRaw = files.readText(name)
        val previousState = mutableState.value
        try {
            files.writeText(name, json.encodeToString(manifest))
            val existing = previousState.books.firstOrNull { it.id == manifest.id }
            val progress = legacyAwareProgress(manifest, existing?.progress ?: ReadingProgress())
            val entry = ShelfBook(manifest.id, manifest.title, manifest.author, manifest.format,
                manifest.chapters.size, manifest.paragraphCount(), existing?.addedAt ?: files.nowMillis(),
                existing?.lastOpenedAt ?: 0, progress, manifest.characterCount())
            mutableState.value = previousState.copy(books = if (existing == null) previousState.books + entry else
                previousState.books.map { if (it.id == manifest.id) entry else it }, busy = false)
            if (!persistSnapshot()) {
                mutableState.value = mutableState.value.copy(books = previousState.books)
                if (previousRaw == null) files.delete(name) else files.writeText(name, previousRaw)
                return false
            }
            return true
        } catch (e: Exception) {
            mutableState.value = previousState.copy(busy = false, error = "导入保存失败，旧书架已保留。")
            if (previousRaw != null) runCatching { files.writeText(name, previousRaw) }
            throw e
        }
    }

    private fun importFailure(e: Exception) {
        if (e is CancellationException) throw e
        mutableState.value = mutableState.value.copy(busy = false, error = "导入失败：${e.message.orEmpty().take(160)}")
    }

    private fun createChapterFiles(document: BookDocument): BookManifest {
        val revision = Random.nextBytes(16).joinToString("") { it.toUByte().toString(16).padStart(2, '0') }
        val entries = mutableListOf<ChapterEntry>()
        document.chapters.forEachIndexed { sourceIndex, source ->
            var part = mutableListOf<String>()
            var units = 0
            var sourceStart = 0
            fun flushPart(force: Boolean = false) {
                if (part.isEmpty() && !force) return
                val title = if (sourceStart == 0) source.title else "${source.title.take(990)}（续）"
                val file = "book-${document.id}-$revision-c${entries.size}.json"
                val chapter = BookChapter(title, part.toList())
                chapter.validate()
                files.writeText(file, json.encodeToString(chapter))
                entries += ChapterEntry(title, file, part.size, units, sourceIndex, sourceStart)
                sourceStart += part.size; part = mutableListOf(); units = 0
            }
            source.paragraphs.forEach { paragraph ->
                if (units + paragraph.length > 256 * 1024 || part.size >= 2000) flushPart()
                part += paragraph; units += paragraph.length
            }
            flushPart(force = source.paragraphs.isEmpty())
        }
        return BookManifest(id = document.id, title = document.title, author = document.author,
            format = document.format, revision = revision, chapters = entries).also { it.validate() }
    }

    /** A manifest may already be durable while cancellation/disk failure left the shelf in v1 coordinates. */
    private fun legacyAwareProgress(manifest: BookManifest, old: ReadingProgress): ReadingProgress {
        if (old.chapterIndex >= 0 || manifest.chapters.any { it.sourceChapterIndex == null }) return manifest.normalize(old)
        val sourceCounts = linkedMapOf<Int, Int>()
        manifest.chapters.forEach { entry ->
            val source = checkNotNull(entry.sourceChapterIndex)
            sourceCounts[source] = (sourceCounts[source] ?: 0) + entry.paragraphCount
        }
        var remaining = old.itemIndex.coerceIn(0, sourceCounts.values.sum() + sourceCounts.size - 1)
        var sourceIndex = 0
        for ((source, count) in sourceCounts) {
            sourceIndex = source
            if (remaining <= count) break
            remaining -= count + 1
        }
        val paragraph = (remaining - 1).coerceAtLeast(0)
        val target = if (remaining == 0) manifest.chapters.indexOfFirst { it.sourceChapterIndex == sourceIndex }
            else manifest.chapters.indexOfLast { it.sourceChapterIndex == sourceIndex && it.sourceParagraphStart <= paragraph }
        check(target >= 0)
        val local = if (remaining == 0) 0 else paragraph - manifest.chapters[target].sourceParagraphStart + 1
        return manifest.normalize(old.copy(itemIndex = manifest.chapterStart(target) + local, chapterIndex = target,
            paragraphIndex = local, characterOffset = 0))
    }

    fun deleteBook(id: String) {
        if (persistenceBlocked || !documentIdPattern.matches(id)) return
        scope.launch {
            documentOperations.withLock {
                val previous = mutableState.value
                if (previous.books.none { it.id == id }) return@withLock
                ++openGeneration; ++chapterGeneration; saveJob?.cancel()
                val removingCurrent = previous.currentBook?.id == id
                mutableState.value = previous.copy(books = previous.books.filterNot { it.id == id },
                    currentBook = previous.currentBook?.takeUnless { it.id == id },
                    manifest = if (removingCurrent) null else previous.manifest,
                    chapter = if (removingCurrent) null else previous.chapter, busy = false, chapterBusy = false)
                if (!persistSnapshot()) { mutableState.value = previous.copy(error = mutableState.value.error); return@withLock }
                try {
                    withContext(ioDispatcher) {
                        val raw = files.readText(manifestName(id))
                        if (raw != null) {
                            val manifest = json.decodeFromString<BookManifest>(raw).also { it.validate(); require(it.id == id) }
                            manifest.chapters.forEach { files.delete(it.fileName) }
                            files.delete(manifestName(id))
                        }
                        files.delete("book-$id.json")
                    }
                    chapterCache.clear()
                } catch (e: Exception) {
                    if (e is CancellationException) throw e
                    reportError("已移出书架，部分缓存仍保留。")
                }
            }
        }
    }

    fun dismissError() { mutableState.value = mutableState.value.copy(error = null) }
    fun reportError(message: String) { mutableState.value = mutableState.value.copy(error = message.take(300)) }
    fun flush() { saveJob?.cancel(); saveJob = null; persistSnapshot() }
    private fun scheduleSave() { saveJob?.cancel(); saveJob = scope.launch { delay(700); persistSnapshot() } }
    private fun persistSnapshot(): Boolean {
        if (persistenceBlocked) return false
        return try {
            val value = mutableState.value
            files.writeText("library.json", json.encodeToString(LibrarySnapshot(books = value.books, settings = value.settings)))
            true
        } catch (_: Exception) { reportError("保存失败，请检查可用存储空间；旧索引未主动清除。"); false }
    }
    private fun manifestName(id: String): String = "book-$id.manifest.json"
}

object ReaderRuntime {
    val store: ReaderStore by lazy { ReaderStore() }
    fun importBook(json: String) { store.importBookJson(json) }
    fun importManifest(json: String) { store.importManifestJson(json) }
    fun reportError(message: String) { store.reportError(message) }
    fun flush() { store.flush() }
}
''',
    'shared/src/iosMain/kotlin/dev/leaf/reader/ReaderFiles.ios.kt': r'''@file:OptIn(kotlinx.cinterop.ExperimentalForeignApi::class)

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
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReaderApp.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.Card
import top.yukonga.miuix.kmp.basic.CircularProgressIndicator
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextButton
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.darkColorScheme
import top.yukonga.miuix.kmp.theme.lightColorScheme

/**
 * Root of the shared UI. The shelf owns its collapsing header and floating dock;
 * the reader owns an immersive viewport with slide-in chrome and its own
 * open/close spring, so this root only resolves theme + overlays.
 */
@Composable
fun ReaderApp(store: ReaderStore, onImportRequested: () -> Unit) {
    val state by store.state.collectAsState()
    val systemDark = isSystemInDarkTheme()
    val colors = when (state.settings.theme) {
        ReaderTheme.SEPIA -> readerColorScheme(ReaderTheme.SEPIA)
        ReaderTheme.LIGHT -> lightColorScheme()
        ReaderTheme.DARK -> darkColorScheme()
        ReaderTheme.SYSTEM -> if (systemDark) darkColorScheme() else lightColorScheme()
    }
    MiuixTheme(colors = colors) {
        val shelfState = rememberSaveableStateHolder()
        Box(Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surface)) {
            val book = state.currentBook
            if (book == null) {
                shelfState.SaveableStateProvider("shelf") {
                    ShelfScreen(state = state, store = store, onImportRequested = onImportRequested)
                }
            } else {
                key(book.id) { ReadingScreen(state = state, store = store) }
            }
            if (state.busy) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.22f))
                        .pointerInput(Unit) {
                            awaitPointerEventScope {
                                while (true) awaitPointerEvent().changes.forEach { it.consume() }
                            }
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Card(insideMargin = PaddingValues(28.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(16.dp),
                        ) {
                            CircularProgressIndicator(size = 26.dp)
                            Text(
                                "正在整理书页…",
                                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                            )
                        }
                    }
                }
            }
            OverlayDialog(
                show = state.error != null,
                title = "暂时未能完成",
                summary = state.error,
                onDismissRequest = store::dismissError,
            ) {
                TextButton(
                    text = "知道了", onClick = store::dismissError,
                    modifier = Modifier.fillMaxWidth(), minHeight = 48.dp,
                    colors = top.yukonga.miuix.kmp.basic.ButtonDefaults.textButtonColorsPrimary(),
                )
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixAtoms.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.tween
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.lightColorScheme
import top.yukonga.miuix.kmp.theme.darkColorScheme

/** Same curves the reference sheets use: open 360ms ease-out, close 280ms ease-in. */
internal val MiuixEaseOut = CubicBezierEasing(0.22f, 1f, 0.36f, 1f)
internal val MiuixEaseIn = CubicBezierEasing(0.4f, 0f, 0.2f, 1f)
internal const val BookOpenMillis = 360
internal const val BookCloseMillis = 280

internal fun <T> bookOpen() = tween<T>(BookOpenMillis, easing = MiuixEaseOut)
internal fun <T> bookClose() = tween<T>(BookCloseMillis, easing = MiuixEaseIn)

/** Touch target spacing from the reference: 12dp between floating controls. */
internal val ControlGap = 12.dp
internal val PageMargin = 20.dp
internal val CircleControlSize = 40.dp

/**
 * Header/backdrop used by the shelf: an opaque-to-transparent vertical wash from the
 * Miuix surface colour, so scrolled content dissolves instead of being cut by a divider.
 * (Gradient-based to stay identical on iOS and desktop; no backdrop-blur shader.)
 */
@Composable
internal fun GradientHeaderScrim(content: @Composable BoxScope.() -> Unit) {
    val surface = MiuixTheme.colorScheme.surface
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(
                    0f to surface,
                    0.55f to surface.copy(alpha = 0.94f),
                    0.82f to surface.copy(alpha = 0.55f),
                    1f to Color.Transparent,
                ),
            ),
    ) {
        content()
    }
}

/** Circular 40dp Miuix floating control (squircle-ish pill, soft shadow, generous gap). */
@Composable
internal fun MiuixCircleButton(
    glyph: Glyph,
    description: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    size: Dp = CircleControlSize,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHigh,
    tint: Color = MiuixTheme.colorScheme.onSurface,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(RoundedCornerShape(size / 2))
            .background(container)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        MiuixGlyph(glyph, if (enabled) tint else tint.copy(alpha = 0.4f), size * 0.55f)
    }
}

/** Pill used by the floating dock rows. */
@Composable
internal fun MiuixDockPill(
    modifier: Modifier = Modifier,
    content: @Composable RowScope.() -> Unit,
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(MiuixTheme.colorScheme.surfaceContainerHigh)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        content = content,
    )
}

/** Selected/unselected pill tab for the bottom dock. */
@Composable
internal fun DockTab(
    glyph: Glyph,
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val container = if (selected) MiuixTheme.colorScheme.primary else Color.Transparent
    val content = if (selected) MiuixTheme.colorScheme.onPrimary else MiuixTheme.colorScheme.onSurfaceVariantSummary
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .clickable(onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 10.dp)
            .semantics { contentDescription = label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        MiuixGlyph(glyph, content, 20.dp)
        Text(label, color = content, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

/** Small rounded count badge (chapter word counts, progress). */
@Composable
internal fun CountPill(
    text: String,
    modifier: Modifier = Modifier,
    container: Color = MiuixTheme.colorScheme.surfaceContainerHighest,
    content: Color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
) {
    Text(
        text = text,
        modifier = modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .padding(horizontal = 10.dp, vertical = 3.dp),
        color = content,
        fontSize = 12.sp,
        fontWeight = FontWeight.Medium,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
}

/** Miuix-coloured reader themes; sepia keeps a warm paper wash over the light scheme. */
@Composable
internal fun readerColorScheme(theme: dev.leaf.reader.ReaderTheme): top.yukonga.miuix.kmp.theme.Colors = when (theme) {
    dev.leaf.reader.ReaderTheme.SEPIA -> lightColorScheme(
        primary = Color(0xFF706044),
        onPrimary = Color(0xFFFFFFFF),
        surface = Color(0xFFF3ECD9),
        onSurface = Color(0xFF473E30),
        surfaceContainer = Color(0xFFFBF5E7),
        surfaceContainerHigh = Color(0xFFEFE5CE),
        surfaceContainerHighest = Color(0xFFE6DAC0),
        onSurfaceVariantSummary = Color(0xFF6B5F4B),
        background = Color(0xFFF3ECD9),
        onBackground = Color(0xFF473E30),
    )
    dev.leaf.reader.ReaderTheme.LIGHT -> lightColorScheme()
    else -> darkColorScheme()
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/MiuixGlyphs.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Small Canvas glyphs used by the floating controls. Miuix 0.9.4 ships only a
 * narrow icon set, so these keep the controls dependency-free instead of pulling
 * an extra icon artifact into the Kotlin/Native framework.
 */
internal enum class Glyph {
    BACK, SEARCH, ADD, TOC, TUNE, CLOSE, SORT, REFRESH, TAG, MORE, BOOK, SHELVES, GEAR, CHEVRON_UP,
}

@Composable
internal fun MiuixGlyph(glyph: Glyph, tint: Color, size: Dp = 22.dp) {
    Canvas(Modifier.size(size)) {
        val unit = this.size.minDimension / 24f
        val stroke = 2f * unit
        fun at(x: Float, y: Float) = Offset(x * unit, y * unit)
        fun line(x1: Float, y1: Float, x2: Float, y2: Float) =
            drawLine(tint, at(x1, y1), at(x2, y2), strokeWidth = stroke, cap = StrokeCap.Round)
        fun dot(x: Float, y: Float, r: Float = 1.35f) = drawCircle(tint, r * unit, at(x, y))
        when (glyph) {
            Glyph.BACK -> {
                line(14.5f, 5f, 7.5f, 12f)
                line(7.5f, 12f, 14.5f, 19f)
            }
            Glyph.SEARCH -> {
                drawCircle(tint, 6.2f * unit, at(10.5f, 10.5f), style = Stroke(stroke))
                line(15.1f, 15.1f, 20f, 20f)
            }
            Glyph.ADD -> {
                line(12f, 6f, 12f, 18f)
                line(6f, 12f, 18f, 12f)
            }
            Glyph.TOC -> {
                dot(5.5f, 6.5f, 1.2f); line(9f, 6.5f, 19f, 6.5f)
                dot(5.5f, 12f, 1.2f); line(9f, 12f, 19f, 12f)
                dot(5.5f, 17.5f, 1.2f); line(9f, 17.5f, 19f, 17.5f)
            }
            Glyph.TUNE -> {
                line(4f, 7f, 20f, 7f); dot(9f, 7f, 2f)
                line(4f, 12f, 20f, 12f); dot(15f, 12f, 2f)
                line(4f, 17f, 20f, 17f); dot(11.5f, 17f, 2f)
            }
            Glyph.CLOSE -> {
                line(6.5f, 6.5f, 17.5f, 17.5f)
                line(17.5f, 6.5f, 6.5f, 17.5f)
            }
            Glyph.SORT -> {
                line(12f, 4.5f, 12f, 19.5f)
                line(8.5f, 8f, 12f, 4.5f)
                line(15.5f, 8f, 12f, 4.5f)
                line(8.5f, 16f, 12f, 19.5f)
                line(15.5f, 16f, 12f, 19.5f)
            }
            Glyph.REFRESH -> {
                drawArc(
                    color = tint, startAngle = -40f, sweepAngle = 280f, useCenter = false,
                    topLeft = at(4f, 4f), size = androidx.compose.ui.geometry.Size(16f * unit, 16f * unit),
                    style = Stroke(stroke, cap = StrokeCap.Round),
                )
                line(17.5f, 3f, 19.5f, 7f)
                line(19.5f, 7f, 15f, 7.5f)
            }
            Glyph.TAG -> {
                line(9f, 4.5f, 7.5f, 19.5f)
                line(16.5f, 4.5f, 15f, 19.5f)
                line(4.5f, 9.5f, 19.5f, 9.5f)
                line(4f, 15f, 19f, 15f)
            }
            Glyph.MORE -> {
                dot(12f, 5.5f); dot(12f, 12f); dot(12f, 18.5f)
            }
            Glyph.BOOK -> {
                val path = Path().apply {
                    moveTo(6f * unit, 4.5f * unit)
                    lineTo(6f * unit, 19.5f * unit)
                    lineTo(18f * unit, 19.5f * unit)
                    lineTo(18f * unit, 6.5f * unit)
                    lineTo(8.5f * unit, 6.5f * unit)
                }
                drawPath(path, tint, style = Stroke(stroke, cap = StrokeCap.Round))
                line(6f, 16.5f, 18f, 16.5f)
                line(9.5f, 10f, 15f, 10f)
            }
            Glyph.SHELVES -> {
                line(4.5f, 7f, 4.5f, 19f)
                line(11.5f, 5f, 11.5f, 19f)
                line(18.5f, 8f, 18.5f, 19f)
                line(3f, 19f, 21f, 19f)
            }
            Glyph.GEAR -> {
                drawCircle(tint, 3.2f * unit, at(12f, 12f), style = Stroke(stroke))
                for (index in 0 until 8) {
                    val angle = index * (Math.PI / 4).toFloat()
                    val inner = 6.2f
                    val outer = 9.2f
                    line(
                        12f + kotlin.math.cos(angle) * inner,
                        12f + kotlin.math.sin(angle) * inner,
                        12f + kotlin.math.cos(angle) * outer,
                        12f + kotlin.math.sin(angle) * outer,
                    )
                }
            }
            Glyph.CHEVRON_UP -> {
                line(7f, 14.5f, 12f, 9.5f)
                line(17f, 14.5f, 12f, 9.5f)
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfScreen.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyGridState
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayDialog
import top.yukonga.miuix.kmp.theme.MiuixTheme

private enum class ShelfOrder(val label: String) {
    RECENT("最近阅读"), ADDED("最近导入"), TITLE("书名"), LENGTH("篇幅"),
}

/** Keeps the floating dock from covering the last row; >= 96dp by contract. */
private val ShelfDockClearance = 104.dp

/** Scroll distance over which the large title folds into the compact top bar. */
private val ShelfCollapseDistance = 72.dp

@Composable
internal fun ShelfScreen(state: LibraryState, store: ReaderStore, onImportRequested: () -> Unit) {
    var panel by rememberSaveable { mutableIntStateOf(0) }
    var query by rememberSaveable { mutableStateOf("") }
    var searching by rememberSaveable { mutableStateOf(false) }
    var orderIndex by rememberSaveable { mutableIntStateOf(0) }
    var deleting by remember { mutableStateOf<ShelfBook?>(null) }
    var headerHeightPx by remember { mutableIntStateOf(0) }
    val gridState = rememberLazyGridState()
    val settingsState = rememberLazyListState()
    val focusManager = LocalFocusManager.current
    val density = LocalDensity.current
    val enabled = !state.busy
    val layout = state.settings.shelfLayout
    val order = ShelfOrder.entries[orderIndex.coerceIn(0, ShelfOrder.entries.lastIndex)]
    val books = remember(state.books, query, order) {
        val keyword = query.trim()
        val filtered = state.books.filter {
            keyword.isEmpty() ||
                it.title.contains(keyword, ignoreCase = true) ||
                it.author.contains(keyword, ignoreCase = true)
        }
        when (order) {
            ShelfOrder.RECENT -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.lastOpenedAt }.thenByDescending { it.addedAt }.thenBy { it.id },
            )
            ShelfOrder.ADDED -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.addedAt }.thenBy { it.id },
            )
            ShelfOrder.TITLE -> filtered.sortedWith(
                compareBy<ShelfBook> { it.title.lowercase() }.thenBy { it.id },
            )
            ShelfOrder.LENGTH -> filtered.sortedWith(
                compareByDescending<ShelfBook> { it.characterCount }
                    .thenByDescending { it.paragraphCount }.thenBy { it.id },
            )
        }
    }
    val continuing = remember(state.books) {
        state.books.filter { it.lastOpenedAt > 0 }.maxByOrNull { it.lastOpenedAt }
    }

    // Collapse follows the active pane: grid index 0 scroll offset, or a full fold once scrolled.
    // Read through a provider so scroll frames only invalidate the header, never the grid itself.
    val collapseDistance = with(density) { ShelfCollapseDistance.toPx() }
    val collapseTarget: () -> Float = remember(collapseDistance) {
        val progress = derivedStateOf {
            val index: Int
            val offset: Int
            if (panel == 0) {
                index = gridState.firstVisibleItemIndex
                offset = gridState.firstVisibleItemScrollOffset
            } else {
                index = settingsState.firstVisibleItemIndex
                offset = settingsState.firstVisibleItemScrollOffset
            }
            if (index > 0) 1f else (offset / collapseDistance).coerceIn(0f, 1f)
        }
        val provider: () -> Float = { progress.value }
        provider
    }
    val contentTopPadding = with(density) { headerHeightPx.toDp() } + 10.dp
    val shelfMode = panel == 0

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MiuixTheme.colorScheme.surface,
        contentWindowInsets = WindowInsets.systemBars.union(WindowInsets.displayCutout),
        floatingToolbarPosition = ToolbarPosition.BottomCenter,
        floatingToolbar = {
            ShelfDock(panel) { next ->
                panel = next
                searching = false
                focusManager.clearFocus()
            }
        },
    ) { insets ->
        Box(Modifier.fillMaxSize().padding(insets).consumeWindowInsets(insets)) {
            if (shelfMode) {
                ShelfGridPane(
                    books = books,
                    continuing = continuing,
                    layout = layout,
                    order = order,
                    query = query,
                    enabled = enabled,
                    topPadding = contentTopPadding,
                    state = gridState,
                    onOpen = { store.openBook(it.id) },
                    onDelete = { deleting = it },
                    onImport = onImportRequested,
                    onClearSearch = { query = ""; focusManager.clearFocus() },
                )
            } else {
                ShelfSettingsPane(
                    state = state,
                    store = store,
                    onImportRequested = onImportRequested,
                    orderIndex = orderIndex,
                    onOrderChange = { orderIndex = it },
                    listState = settingsState,
                    topPadding = contentTopPadding,
                    modifier = Modifier.fillMaxSize(),
                )
            }
            ShelfHeader(
                compactTitle = if (shelfMode) "书架" else "设置",
                largeTitle = if (shelfMode) "书架" else "设置",
                detail = if (shelfMode) "共 ${state.books.size} 本本地书籍" else "你的书架，你的阅读习惯",
                showActions = shelfMode,
                searching = searching,
                query = query,
                enabled = enabled,
                collapseTarget = collapseTarget,
                onHeaderHeight = { height -> if (height != headerHeightPx) headerHeightPx = height },
                onSearchToggle = {
                    if (searching) {
                        searching = false
                        query = ""
                        focusManager.clearFocus()
                    } else {
                        searching = true
                    }
                },
                onImport = onImportRequested,
                onQueryChange = { query = it },
                onCollapseSearch = { query = ""; searching = false; focusManager.clearFocus() },
            )
        }
        OverlayDialog(
            show = deleting != null,
            title = "移出书架？",
            summary = "将移除《${deleting?.title.orEmpty()}》及阅读进度，原始文件保留。",
            onDismissRequest = { deleting = null },
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                TextButton("保留", { deleting = null }, Modifier.weight(1f), minHeight = 48.dp)
                TextButton(
                    "移除书籍",
                    {
                        deleting?.let { store.deleteBook(it.id) }
                        deleting = null
                    },
                    Modifier.weight(1f),
                    enabled = enabled,
                    minHeight = 48.dp,
                    colors = ButtonDefaults.textButtonColorsPrimary(color = MiuixTheme.colorScheme.error),
                )
            }
        }
    }
}

/** Floating dock: Miuix Scaffold placement + FloatingToolbar pill with two dock tabs. */
@Composable
private fun ShelfDock(panel: Int, onSelect: (Int) -> Unit) {
    FloatingToolbar(
        color = MiuixTheme.colorScheme.surfaceContainerHigh,
        cornerRadius = 999.dp,
        outSidePadding = PaddingValues(horizontal = PageMargin, vertical = 12.dp),
        shadowElevation = 8.dp,
        showDivider = true,
    ) {
        MiuixDockPill {
            DockTab(Glyph.SHELVES, "书架", selected = panel == 0, onClick = { onSelect(0) })
            DockTab(Glyph.GEAR, "设置", selected = panel == 1, onClick = { onSelect(1) })
        }
    }
}

/**
 * Collapsing header laid over the list: gradient scrim (no divider), compact title fading in
 * while the large title scales and fades out, then the search row that expands underneath.
 */
@Composable
private fun ShelfHeader(
    compactTitle: String,
    largeTitle: String,
    detail: String,
    showActions: Boolean,
    searching: Boolean,
    query: String,
    enabled: Boolean,
    collapseTarget: () -> Float,
    onHeaderHeight: (Int) -> Unit,
    onSearchToggle: () -> Unit,
    onImport: () -> Unit,
    onQueryChange: (String) -> Unit,
    onCollapseSearch: () -> Unit,
) {
    val collapseProgress = animateFloatAsState(
        targetValue = collapseTarget(),
        animationSpec = tween(140, easing = MiuixEaseOut),
        label = "shelf-collapse",
    )
    val collapse: () -> Float = { collapseProgress.value }
    GradientHeaderScrim {
        Column(Modifier.fillMaxWidth()) {
            Column(Modifier.fillMaxWidth().onSizeChanged { onHeaderHeight(it.height) }) {
                Row(
                    Modifier.fillMaxWidth()
                        .heightIn(min = 48.dp)
                        .padding(start = PageMargin, end = PageMargin, top = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        compactTitle,
                        modifier = Modifier.weight(1f).graphicsLayer {
                            val appear = ((collapse() - 0.55f) / 0.45f).coerceIn(0f, 1f)
                            alpha = appear
                            translationY = (1f - appear) * 6.dp.toPx()
                        },
                        style = MiuixTheme.textStyles.title3,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (showActions) {
                        Row(horizontalArrangement = Arrangement.spacedBy(ControlGap)) {
                            MiuixCircleButton(
                                Glyph.SEARCH, "搜索书架", onSearchToggle,
                                size = CircleControlSize,
                            )
                            MiuixCircleButton(
                                Glyph.ADD, "导入本地书籍", onImport,
                                enabled = enabled,
                                size = CircleControlSize,
                            )
                        }
                    }
                }
                Row(
                    Modifier.fillMaxWidth()
                        .padding(start = PageMargin, end = PageMargin, top = 2.dp, bottom = 14.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    Text(
                        largeTitle,
                        modifier = Modifier.graphicsLayer {
                            val progress = collapse()
                            alpha = (1f - progress * 1.15f).coerceIn(0f, 1f)
                            val scale = 1f - progress * 0.32f
                            scaleX = scale
                            scaleY = scale
                            transformOrigin = TransformOrigin(0f, 0.85f)
                        }.semantics { heading() },
                        style = MiuixTheme.textStyles.title1,
                        fontSize = 32.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Spacer(Modifier.weight(1f))
                    Text(
                        detail,
                        modifier = Modifier.padding(start = 12.dp),
                        style = MiuixTheme.textStyles.footnote1,
                        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
                        textAlign = TextAlign.End,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            AnimatedVisibility(
                visible = searching,
                enter = expandVertically(expandFrom = Alignment.Top) + fadeIn(),
                exit = shrinkVertically(shrinkTowards = Alignment.Top) + fadeOut(),
            ) {
                ShelfSearchRow(
                    query = query,
                    onQueryChange = onQueryChange,
                    onCollapse = onCollapseSearch,
                    modifier = Modifier.padding(start = PageMargin, end = PageMargin, top = 2.dp, bottom = 10.dp),
                )
            }
        }
    }
}

@Composable
private fun ShelfSearchRow(
    query: String,
    onQueryChange: (String) -> Unit,
    onCollapse: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val focusManager = LocalFocusManager.current
    Row(
        modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(ControlGap),
    ) {
        InputField(
            query = query,
            onQueryChange = onQueryChange,
            onSearch = { focusManager.clearFocus() },
            expanded = true,
            onExpandedChange = { },
            modifier = Modifier.weight(1f),
            label = "搜索书名或作者",
            leadingIcon = {
                Box(Modifier.padding(start = 14.dp, end = 8.dp)) {
                    MiuixGlyph(Glyph.SEARCH, MiuixTheme.colorScheme.onSurfaceVariantSummary, 18.dp)
                }
            },
            trailingIcon = {
                if (query.isNotEmpty()) {
                    Box(Modifier.padding(end = 6.dp)) {
                        MiuixCircleButton(
                            Glyph.CLOSE,
                            "清空搜索",
                            { onQueryChange("") },
                            size = 28.dp,
                            container = MiuixTheme.colorScheme.surfaceContainerHighest,
                            tint = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        )
                    }
                }
            },
        )
        MiuixCircleButton(Glyph.CLOSE, "收起搜索", onCollapse, size = CircleControlSize)
    }
}

/** Shelf pane: hero, 3-column cover grid (1-column list/compact), notes. */
@Composable
private fun ShelfGridPane(
    books: List<ShelfBook>,
    continuing: ShelfBook?,
    layout: ShelfLayout,
    order: ShelfOrder,
    query: String,
    enabled: Boolean,
    topPadding: Dp,
    state: LazyGridState,
    onOpen: (ShelfBook) -> Unit,
    onDelete: (ShelfBook) -> Unit,
    onImport: () -> Unit,
    onClearSearch: () -> Unit,
) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val narrow = maxWidth < 360.dp
        LazyVerticalGrid(
            columns = when {
                layout != ShelfLayout.GRID -> GridCells.Fixed(1)
                narrow -> GridCells.Adaptive(96.dp)
                else -> GridCells.Fixed(3)
            },
            state = state,
            modifier = Modifier.fillMaxSize().imePadding(),
            contentPadding = PaddingValues(
                start = PageMargin,
                end = PageMargin,
                top = topPadding,
                bottom = ShelfDockClearance,
            ),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(if (layout == ShelfLayout.COMPACT) 10.dp else 20.dp),
        ) {
            val hero = continuing
            if (query.isBlank() && hero != null) {
                item(key = "continue", span = { GridItemSpan(maxLineSpan) }) {
                    ContinueReadingHero(hero, enabled) { onOpen(hero) }
                }
            }
            item(key = "section", span = { GridItemSpan(maxLineSpan) }) {
                ShelfSectionHeader(
                    title = if (query.isBlank()) "本地藏书" else "搜索结果",
                    detail = if (query.isBlank()) "按${order.label}排序"
                    else "“${query.trim()}” · ${books.size} 本",
                )
            }
            if (books.isEmpty()) {
                item(key = "empty", span = { GridItemSpan(maxLineSpan) }) {
                    ShelfEmptyCard(query.isBlank(), enabled, onImport, onClearSearch)
                }
            }
            items(books, key = { it.id }, contentType = { layout }) { book ->
                when (layout) {
                    ShelfLayout.GRID -> ShelfCoverTile(book, enabled, { onOpen(book) }, { onDelete(book) })
                    ShelfLayout.LIST -> ShelfListRow(book, enabled, false, { onOpen(book) }, { onDelete(book) })
                    ShelfLayout.COMPACT -> ShelfListRow(book, enabled, true, { onOpen(book) }, { onDelete(book) })
                }
            }
            item(key = "local-note", span = { GridItemSpan(maxLineSpan) }) {
                ShelfMuted(
                    "本地存储 · 无需联网阅读\n长按书卡可移除；TXT / 基础 EPUB 纯文本，不还原 EPUB 图片、CSS、脚本、固定版式或 DRM 内容。",
                    Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

/** Settings pane: same grouped Miuix cards as the previous version, re-spaced and re-titled. */
@Composable
private fun ShelfSettingsPane(
    state: LibraryState,
    store: ReaderStore,
    onImportRequested: () -> Unit,
    orderIndex: Int,
    onOrderChange: (Int) -> Unit,
    listState: LazyListState,
    topPadding: Dp,
    modifier: Modifier,
) {
    val settings = state.settings
    val enabled = !state.busy
    LazyColumn(
        modifier = modifier.imePadding(),
        state = listState,
        contentPadding = PaddingValues(
            start = PageMargin,
            end = PageMargin,
            top = topPadding,
            bottom = ShelfDockClearance,
        ),
        verticalArrangement = Arrangement.spacedBy(24.dp),
    ) {
        item(key = "appearance") {
            ShelfSettingGroup("书架外观") {
                ShelfChoice("书架布局", listOf("封面", "列表", "紧凑"), settings.shelfLayout.ordinal) {
                    store.updateSettings(settings.copy(shelfLayout = ShelfLayout.entries[it]))
                }
                ShelfChoice(
                    "排序方式",
                    ShelfOrder.entries.map { it.label },
                    orderIndex.coerceIn(0, ShelfOrder.entries.lastIndex),
                    onOrderChange,
                )
                ShelfChoice("主题", listOf("跟随系统", "浅色", "深色", "纸色"), settings.theme.ordinal) {
                    store.updateSettings(settings.copy(theme = ReaderTheme.entries[it]))
                }
            }
        }
        item(key = "reading") {
            ShelfSettingGroup("默认阅读方式") {
                ShelfChoice("翻页方式", listOf("滚动", "滑动", "即时"), settings.readingMode.ordinal) {
                    store.updateSettings(settings.copy(readingMode = ReadingMode.entries[it]))
                }
                ShelfChoice("分栏", listOf("自动", "单栏", "双栏"), settings.columnMode.ordinal) {
                    store.updateSettings(settings.copy(columnMode = ColumnMode.entries[it]))
                }
                ShelfChoice("字体", listOf("衬线", "无衬线", "等宽"), settings.fontFamily.ordinal) {
                    store.updateSettings(settings.copy(fontFamily = ReaderFont.entries[it]))
                }
                ShelfSliderSetting("字号", settings.fontSize, 14f..40f, 25, "sp") {
                    store.updateSettings(settings.copy(fontSize = it))
                }
                ShelfNote("阅读页的「排版」还可调整行距、页边距、段距、字间距、首行缩进与字重。")
            }
        }
        item(key = "immersive") {
            ShelfSettingGroup("沉浸阅读") {
                ShelfSwitchSetting(
                    "自动收起工具栏",
                    "阅读时自动隐藏；轻点正文中央再次显示",
                    settings.autoHideControls,
                ) { store.updateSettings(settings.copy(autoHideControls = it)) }
                ShelfSwitchSetting(
                    "阅读页脚",
                    "显示当前章节与阅读进度",
                    settings.showReadingFooter,
                ) { store.updateSettings(settings.copy(showReadingFooter = it)) }
            }
        }
        item(key = "library") {
            ShelfSettingGroup("本地书库") {
                BasicComponent(
                    title = "导入书籍",
                    summary = "从「文件」选择 TXT 或 EPUB",
                    insideMargin = PaddingValues(0.dp),
                    onClick = onImportRequested,
                    onClickLabel = "选择本地书籍",
                    enabled = enabled,
                    endActions = {
                        MiuixCircleButton(Glyph.ADD, "导入本地书籍", onImportRequested, enabled = enabled)
                    },
                )
                BasicComponent(
                    title = "${state.books.size} 本藏书",
                    summary = "正文按章节存储，阅读按需加载；进度与偏好保存在本机。",
                    insideMargin = PaddingValues(0.dp),
                )
                BasicComponent(
                    title = "移除与原始文件",
                    summary = "长按书卡或使用列表中的「移除」，确认后只清理应用内副本和阅读进度，原始文件保留。",
                    insideMargin = PaddingValues(0.dp),
                )
                ShelfNote("格式兼容：TXT 与基础 EPUB 纯文本。EPUB 图片、CSS 排版、脚本、固定版式与 DRM 内容不在当前纯文本引擎内。")
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ShelfWidgets.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.ShelfBook
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.utils.PressFeedbackType

/** Uses the store's compatible global anchor, never a chapter-relative index as book progress. */
private fun shelfPercent(book: ShelfBook): Int {
    val last = (book.chapterCount.toLong() + book.paragraphCount - 1).coerceAtLeast(1)
    return ((book.progress.itemIndex.toLong() * 100) / last).coerceIn(0, 100).toInt()
}

private fun readingLabel(book: ShelfBook): String =
    if (book.lastOpenedAt > 0) "已读约 ${shelfPercent(book)}%" else "尚未开始"

private fun lengthLabel(book: ShelfBook): String {
    val count = book.characterCount
    return when {
        count >= 10000 -> "${count / 10000}.${count % 10000 / 1000} 万字"
        count > 0 -> "$count 字"
        else -> "${book.paragraphCount} 段"
    }
}

/** Compact badge text for the cover corner: unread / percent / finished. */
private fun progressBadge(book: ShelfBook): String = when {
    book.lastOpenedAt <= 0 -> "未读"
    shelfPercent(book) >= 100 -> "已读完"
    else -> "${shelfPercent(book)}%"
}

/**
 * "Continue reading" hero: cover, current badge, title, chapter/length metadata and the
 * progress track. The whole card is one reading target; removal is never offered here.
 */
@Composable
internal fun ContinueReadingHero(book: ShelfBook, enabled: Boolean, onOpen: () -> Unit) {
    val primary = MiuixTheme.colorScheme.primary
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "继续阅读《${book.title}》，${readingLabel(book)}"
        },
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer.copy(alpha = if (enabled) 1f else 0.7f),
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) onOpen else null,
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            BookCover(book, Modifier.width(64.dp).aspectRatio(0.75f), small = true)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    CountPill("继续阅读", container = primary.copy(alpha = 0.14f), content = primary)
                    Spacer(Modifier.weight(1f))
                    Text(
                        "${shelfPercent(book)}%",
                        style = MiuixTheme.textStyles.footnote1,
                        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
                        maxLines = 1,
                    )
                }
                Text(
                    book.title,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                MutedLabel(
                    "${book.author.ifBlank { "佚名" }} · ${book.format} · ${book.chapterCount} 章 · ${lengthLabel(book)}",
                    maxLines = 1,
                )
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().padding(top = 2.dp),
                    progress = shelfPercent(book) / 100f,
                    height = 5.dp,
                )
            }
        }
    }
}

/**
 * Grid tile: 3:4 generated cover with a progress badge in the bottom-right corner, then
 * title/author. Long press is the removal affordance so the title keeps its full width.
 */
@Composable
internal fun ShelfCoverTile(book: ShelfBook, enabled: Boolean, onOpen: () -> Unit, onDelete: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "《${book.title}》，${book.author.ifBlank { "佚名" }}，${progressBadge(book)}；长按可移除"
        },
        colors = CardDefaults.defaultColors(
            color = Color.Transparent,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) onOpen else null,
        onLongPress = if (enabled) onDelete else null,
    ) {
        Column(Modifier.fillMaxWidth()) {
            Box(Modifier.fillMaxWidth().aspectRatio(0.75f)) {
                BookCover(book, Modifier.fillMaxSize())
                CountPill(
                    progressBadge(book),
                    Modifier.align(Alignment.BottomEnd).padding(6.dp),
                    container = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.72f),
                    content = MiuixTheme.colorScheme.surface,
                )
            }
            Text(
                book.title,
                modifier = Modifier.fillMaxWidth().padding(start = 2.dp, end = 2.dp, top = 8.dp),
                fontSize = 15.sp,
                lineHeight = 20.sp,
                fontWeight = FontWeight.Medium,
                minLines = 2,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                book.author.ifBlank { "佚名" },
                modifier = Modifier.fillMaxWidth().padding(start = 2.dp, end = 2.dp, top = 2.dp),
                fontSize = 12.sp,
                color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** One-column list / compact row. Removal sits at the trailing edge, never next to the title. */
@Composable
internal fun ShelfListRow(
    book: ShelfBook, enabled: Boolean, compact: Boolean, onOpen: () -> Unit, onDelete: () -> Unit,
) {
    val primary = MiuixTheme.colorScheme.primary
    Card(
        modifier = Modifier.fillMaxWidth().semantics {
            contentDescription = "《${book.title}》，${book.author.ifBlank { "佚名" }}，${readingLabel(book)}"
        },
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
        insideMargin = PaddingValues(0.dp),
        pressFeedbackType = PressFeedbackType.Sink,
        onClick = if (enabled) onOpen else null,
        onLongPress = if (enabled) onDelete else null,
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = if (compact) 10.dp else 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            if (compact) {
                Box(
                    Modifier.width(4.dp).height(34.dp)
                        .background(primary.copy(alpha = 0.55f), RoundedCornerShape(2.dp)),
                )
            } else {
                BookCover(book, Modifier.width(54.dp).aspectRatio(0.75f), small = true)
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(
                    book.title,
                    fontSize = if (compact) 16.sp else 18.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = if (compact) 1 else 2,
                    overflow = TextOverflow.Ellipsis,
                )
                MutedLabel(
                    if (compact) "${book.author.ifBlank { "佚名" }} · ${readingLabel(book)}"
                    else "${book.author.ifBlank { "佚名" }} · ${book.format} · ${book.chapterCount} 章 · ${lengthLabel(book)}",
                    maxLines = 1,
                )
                if (!compact) {
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                        progress = shelfPercent(book) / 100f,
                        height = 3.dp,
                    )
                }
            }
            if (compact) {
                CountPill(progressBadge(book))
            }
            ShelfRemoveAction(book, enabled, onDelete)
        }
    }
}

@Composable
private fun ShelfRemoveAction(book: ShelfBook, enabled: Boolean, onDelete: () -> Unit) {
    TextButton(
        "移除", onDelete,
        enabled = enabled,
        minWidth = 48.dp,
        minHeight = 48.dp,
        insideMargin = PaddingValues(horizontal = 8.dp, vertical = 8.dp),
        textStyle = MiuixTheme.textStyles.footnote1,
        colors = ButtonDefaults.textButtonColors(
            color = Color.Transparent,
            textColor = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
        ),
        modifier = Modifier.semantics { contentDescription = "移除《${book.title}》，打开确认" },
    )
}

/**
 * Section heading above the grid. The count is announced politely when a search narrows it.
 */
@Composable
internal fun ShelfSectionHeader(title: String, detail: String, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().padding(top = 6.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            title,
            modifier = Modifier.weight(1f).semantics { heading() },
            style = MiuixTheme.textStyles.title4,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            detail,
            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            style = MiuixTheme.textStyles.footnote1,
            color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
internal fun ShelfEmptyCard(
    querying: Boolean, enabled: Boolean, onImport: () -> Unit, onClearSearch: () -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        insideMargin = PaddingValues(20.dp),
        colors = CardDefaults.defaultColors(
            color = MiuixTheme.colorScheme.surfaceContainer,
            contentColor = MiuixTheme.colorScheme.onSurface,
        ),
    ) {
        Text(
            if (querying) "还没有找到这本书" else "让第一本书，住进来",
            style = MiuixTheme.textStyles.title4,
            fontWeight = FontWeight.SemiBold,
        )
        MutedLabel(
            if (querying) "换一个书名或作者试试。" else "导入本地 TXT 或 EPUB，下次从上次的位置接着读。",
            modifier = Modifier.padding(top = 8.dp),
        )
        TextButton(
            if (querying) "清空搜索" else "选择本地书籍",
            { if (querying) onClearSearch() else onImport() },
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            enabled = enabled,
            minHeight = 48.dp,
            colors = ButtonDefaults.textButtonColorsPrimary(),
        )
    }
}

/** Typographic covers are generated locally; they do not pretend to be fetched cover artwork. */
@Composable
private fun BookCover(book: ShelfBook, modifier: Modifier, small: Boolean = false) {
    val palette = listOf(
        Color(0xFF355E50), Color(0xFF465B73), Color(0xFF745749),
        Color(0xFF635774), Color(0xFF61613F), Color(0xFF6E4C58),
    )
    val color = palette[(book.id.hashCode() and Int.MAX_VALUE) % palette.size]
    val radius = if (small) 8.dp else 12.dp
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(radius))
            .background(Brush.linearGradient(listOf(color, color.copy(alpha = 0.76f))))
            .clearAndSetSemantics { },
    ) {
        Box(
            Modifier.fillMaxHeight().width(if (small) 4.dp else 7.dp)
                .background(Color.Black.copy(alpha = 0.14f)),
        )
        Column(
            Modifier.fillMaxSize().padding(if (small) 8.dp else 12.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                book.format,
                fontSize = if (small) 8.sp else 9.sp,
                color = Color.White.copy(alpha = 0.72f),
                letterSpacing = 1.sp,
                maxLines = 1,
            )
            Text(
                book.title,
                fontSize = if (small) 15.sp else 18.sp,
                lineHeight = if (small) 19.sp else 23.sp,
                color = Color.White,
                fontWeight = FontWeight.SemiBold,
                maxLines = if (small) 2 else 3,
                overflow = TextOverflow.Ellipsis,
            )
            if (!small) {
                Text(
                    book.author.ifBlank { "叶读 · 本地藏书" },
                    fontSize = 10.sp,
                    color = Color.White.copy(alpha = 0.8f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
internal fun ShelfMuted(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    Text(
        text, modifier,
        fontSize = 13.sp,
        lineHeight = 20.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.65f),
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
    )
}

/** Same muted voice, styled through the shared Miuix type scale. */
@Composable
private fun MutedLabel(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) {
    Text(
        text, modifier,
        style = MiuixTheme.textStyles.footnote1,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
    )
}

@Composable
internal fun ShelfNote(text: String, modifier: Modifier = Modifier) {
    Text(
        text, modifier.fillMaxWidth(),
        fontSize = 12.sp,
        lineHeight = 18.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.55f),
    )
}

/** Grouped settings card: section heading outside, roomy rows inside, no sticky dividers. */
@Composable
internal fun ShelfSettingGroup(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            title,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() },
            style = MiuixTheme.textStyles.subtitle,
            color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(18.dp), content = content)
        }
    }
}

/** Segmented choice with a visible caption, using the contour Miuix tab row. */
@Composable
internal fun ShelfChoice(label: String, options: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MiuixTheme.textStyles.body1)
        TabRowWithContour(
            tabs = options,
            selectedTabIndex = selected.coerceIn(0, options.lastIndex.coerceAtLeast(0)),
            onTabSelected = onSelect,
            modifier = Modifier.fillMaxWidth(),
            minWidth = 56.dp,
            height = 44.dp,
        )
    }
}

@Composable
internal fun ShelfSwitchSetting(
    title: String, summary: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 52.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = MiuixTheme.textStyles.body1)
            MutedLabel(summary, maxLines = 2)
        }
        Spacer(Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onChange,
            modifier = Modifier.semantics { contentDescription = title },
            enabled = enabled,
        )
    }
}

@Composable
internal fun ShelfSliderSetting(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    steps: Int,
    unit: String,
    onChange: (Float) -> Unit,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(label, Modifier.weight(1f), style = MiuixTheme.textStyles.body1)
            CountPill("${value.toInt()}$unit")
        }
        Slider(
            value = value,
            onValueChange = onChange,
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics {
                contentDescription = label
            },
            valueRange = range,
            steps = steps,
        )
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingScreen.kt': r'''package dev.leaf.reader.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalFontFamilyResolver
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.text
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextIndent
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.launch
import kotlinx.coroutines.yield
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayBottomSheet
import top.yukonga.miuix.kmp.theme.MiuixTheme
import kotlin.math.abs
import kotlin.math.roundToInt

/** Only the loaded chapter is measured. currentBook contains chapter titles, never body text. */
@Composable
internal fun ReadingScreen(state: LibraryState, store: ReaderStore) {
    val book = state.currentBook ?: return
    val scope = rememberCoroutineScope()
    var directory by remember(book.id) { mutableStateOf(false) }
    var settingsOpen by remember(book.id) { mutableStateOf(false) }
    var showHint by remember(book.id) { mutableStateOf(true) }
    var interaction by remember { mutableIntStateOf(0) }
    var closing by remember(book.id) { mutableStateOf(false) }
    // One Animatable drives the page entrance: scale 0.94 -> 1 and alpha 0 -> 1.
    // Closing runs it back to 0 for 280ms before the shelf takes over.
    val entry = remember(book.id) { Animatable(0f) }
    LaunchedEffect(book.id) { entry.animateTo(1f, animationSpec = bookOpen()) }
    LaunchedEffect(book.id, state.chapter != null) {
        if (state.chapter != null) {
            delay(4500)
            showHint = false
        }
    }
    LaunchedEffect(state.chromeVisible, state.settings.autoHideControls, directory, settingsOpen, interaction, closing) {
        if (state.chromeVisible && state.settings.autoHideControls && !directory && !settingsOpen && !closing) {
            delay(5000)
            store.setChromeVisible(false)
        }
    }
    val leave: () -> Unit = {
        if (!closing) {
            closing = true
            store.setChromeVisible(false)
            scope.launch {
                entry.animateTo(0f, animationSpec = bookClose())
                store.closeBook()
            }
        }
    }
    BoxWithConstraints(Modifier.fillMaxSize().background(MiuixTheme.colorScheme.surface)) {
        // Sheets never exceed a share of the real window height, so 16:9 phones keep the list scrollable.
        val tocMaxHeight = maxHeight * 0.72f
        val settingsMaxHeight = maxHeight * 0.82f
        Box(
            Modifier.fillMaxSize().graphicsLayer {
                val progress = entry.value
                val scale = 0.94f + 0.06f * progress
                scaleX = scale
                scaleY = scale
                alpha = progress
            },
        ) {
            val chapter = state.chapter
            if (chapter != null && !state.chapterBusy) {
                key(book.id, state.chapterIndex, chapter) {
                    ChapterReader(state, chapter, store, closing,
                        onToggleChrome = { interaction++; store.setChromeVisible(!store.state.value.chromeVisible) },
                        onInteraction = { interaction++ },
                        onDirectory = { directory = true },
                        onSettings = { settingsOpen = true },
                        onClose = leave)
                }
            } else {
                Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    if (state.chapterBusy) {
                        CircularProgressIndicator(size = 28.dp)
                        Text("正在装入章节…")
                    } else {
                        Text("章节尚未载入")
                        TextButton("重试本章", { store.selectChapter(state.chapterIndex) }, minHeight = 48.dp)
                        TextButton("选择其他章节", { directory = true }, minHeight = 48.dp)
                    }
                    TextButton("返回书架", leave, minHeight = 48.dp)
                }
            }
            // Passive hint: no pointer modifier and no place in the measured reading viewport.
            if (showHint && chapter != null && !state.chapterBusy && !state.chromeVisible) {
                Text(if (state.settings.readingMode == ReadingMode.SCROLL)
                    "点击中间显示工具栏 · 上下滑动阅读" else "点击中间显示工具栏 · 左右滑动翻页",
                    modifier = Modifier.align(Alignment.BottomCenter).padding(horizontal = 20.dp, vertical = 64.dp)
                        .background(MiuixTheme.colorScheme.surfaceContainer).padding(12.dp),
                    style = MiuixTheme.textStyles.footnote1)
            }
        }
        // While the page animates out, swallow pointer input so no chrome action can fire twice.
        if (closing) {
            Box(Modifier.fillMaxSize().pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) awaitPointerEvent().changes.forEach { it.consume() }
                }
            })
        }
        OverlayBottomSheet(
            show = directory,
            title = null,
            onDismissRequest = { directory = false },
            cornerRadius = 28.dp,
        ) {
            TocSheet(
                book = book,
                manifest = state.manifest,
                currentChapter = state.chapterIndex,
                progressText = "${(state.chapterIndex + 1).coerceAtLeast(1)} / " +
                    "${(state.manifest?.chapters?.size ?: book.chapters.size).coerceAtLeast(1)}",
                maxHeight = tocMaxHeight,
                onSelectChapter = {
                    if (it != state.chapterIndex) store.selectChapter(it)
                    directory = false
                },
                onDismiss = { directory = false },
            )
        }
        ReadingSettings(settingsOpen, state.settings, store::updateSettings, { settingsOpen = false },
            maxHeight = settingsMaxHeight)
    }
}

private data class ChapterLayout(val pages: List<MeasuredPage>, val paragraphs: List<TextLayoutResult>)
private data class ReadingMetrics(
    val fontSize: Float, val lineHeight: Float, val font: ReaderFont, val bold: Boolean,
    val indent: Boolean, val letterSpacing: Float, val paragraphSpacing: Float,
)

@Composable
private fun ChapterReader(
    state: LibraryState,
    chapter: BookChapter,
    store: ReaderStore,
    closing: Boolean,
    onToggleChrome: () -> Unit,
    onInteraction: () -> Unit,
    onDirectory: () -> Unit,
    onSettings: () -> Unit,
    onClose: () -> Unit,
) {
    val book = state.currentBook ?: return
    val settings = state.settings
    val density = LocalDensity.current
    val resolver = LocalFontFamilyResolver.current
    val textMeasurer = rememberTextMeasurer(cacheSize = 16)
    val texts = remember(chapter) { chapterReadingTexts(chapter, state.chapterIndex) }
    var stableAnchor by remember { mutableStateOf(clampAnchor(texts,
        TextAnchor(state.currentProgress.paragraphIndex, state.currentProgress.characterOffset))) }
    var layout by remember { mutableStateOf<ChapterLayout?>(null) }
    var appliedLayout by remember { mutableStateOf<ChapterLayout?>(null) }
    var appliedMode by remember { mutableStateOf<ReadingMode?>(null) }
    var instantPage by remember { mutableIntStateOf(0) }
    val list = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val previousChapter = state.chapterIndex > 0
    val nextChapter = state.chapterIndex < book.chapters.lastIndex
    val firstPage = if (previousChapter) 1 else 0
    val pager = rememberPagerState(pageCount = {
        (layout?.pages?.size ?: 1) + firstPage + if (nextChapter) 1 else 0
    })
    val metrics = ReadingMetrics(settings.fontSize, settings.lineHeight, settings.fontFamily,
        settings.bold, settings.firstLineIndent, settings.letterSpacing, settings.paragraphSpacing)
    val family = when (settings.fontFamily) {
        ReaderFont.SERIF -> FontFamily.Serif
        ReaderFont.SANS -> FontFamily.SansSerif
        ReaderFont.MONO -> FontFamily.Monospace
    }
    val bodyStyle = TextStyle(fontFamily = family, fontSize = settings.fontSize.sp,
        lineHeight = (settings.fontSize * settings.lineHeight).sp,
        fontWeight = if (settings.bold) FontWeight.Bold else FontWeight.Normal,
        letterSpacing = settings.letterSpacing.sp,
        textIndent = TextIndent(firstLine = if (settings.firstLineIndent) 2.em else 0.em))
    val headingStyle = bodyStyle.copy(fontSize = (settings.fontSize + 6).sp,
        lineHeight = ((settings.fontSize + 6) * 1.5f).sp,
        fontWeight = FontWeight.Bold, textIndent = TextIndent.None)

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val columns = when (settings.columnMode) {
            ColumnMode.SINGLE -> 1
            ColumnMode.DOUBLE -> 2
            ColumnMode.AUTO -> if (maxWidth >= 840.dp) 2 else 1
        }
        val margin = settings.horizontalMargin.dp.coerceAtMost((maxWidth / 5).coerceAtLeast(0.dp))
        val gap = if (columns == 2) 28.dp else 0.dp
        // Chrome and footer never participate in these constraints: toggling them cannot reflow text.
        val pageHeight = (maxHeight - 72.dp).coerceAtLeast(1.dp)
        val columnWidth = with(density) { ((maxWidth - margin * 2 - gap) / columns).roundToPx().coerceAtLeast(1) }
        val columnHeight = with(density) { pageHeight.toPx().coerceAtLeast(1f) }
        val gapPx = with(density) { gap.toPx() }
        val spacingPx = with(density) { settings.paragraphSpacing.dp.toPx() }

        LaunchedEffect(chapter, columnWidth, columnHeight, columns, metrics, density.density, density.fontScale, resolver) {
            appliedLayout = null
            layout = null
            // TextMeasurer stays on the composition dispatcher. Yield between bounded batches so
            // chapter layout can be cancelled on resize/settings changes without measuring a book.
            val measured = ArrayList<TextLayoutResult>(texts.size)
            texts.forEachIndexed { index, text ->
                measured += textMeasurer.measure(AnnotatedString(text),
                    style = if (index == 0) headingStyle else bodyStyle,
                    constraints = Constraints(maxWidth = columnWidth))
                if (index % 12 == 0) yield()
            }
            val pages = paginateChapter(texts, columnWidth, columnHeight, columns, spacingPx) { index, text, _ ->
                val result = measured[index]
                List(result.lineCount) { line ->
                    MeasuredLine(safeTextOffset(text, result.getLineStart(line)),
                        if (line == result.lineCount - 1) text.length
                        else safeTextOffset(text, result.getLineStart(line + 1)),
                        result.getLineTop(line), result.getLineBottom(line))
                }
            }
            layout = ChapterLayout(pages, measured)
        }
        val currentLayout = layout
        val ready = currentLayout != null && appliedLayout === currentLayout && appliedMode == settings.readingMode
        LaunchedEffect(currentLayout, settings.readingMode) {
            appliedLayout = null
            val measured = currentLayout ?: return@LaunchedEffect
            val target = pageForAnchor(measured.pages, clampAnchor(texts, stableAnchor))
            // Never scroll an unattached LazyList/Pager state: it can await first layout forever.
            when (settings.readingMode) {
                ReadingMode.INSTANT -> instantPage = target
                ReadingMode.SLIDE -> pager.scrollToPage(target + firstPage)
                ReadingMode.SCROLL -> list.scrollToItem(target,
                    yForAnchor(measured.pages[target], stableAnchor).roundToInt().coerceAtLeast(0))
            }
            withFrameNanos { }
            appliedMode = settings.readingMode
            appliedLayout = measured
        }
        fun saveAnchor(anchor: TextAnchor, offset: Int = 0) {
            val live = store.state.value
            if (live.currentBook?.id == book.id && live.chapterIndex == state.chapterIndex &&
                !live.chapterBusy && !live.busy) {
                stableAnchor = clampAnchor(texts, anchor)
                store.updateChapterProgress(stableAnchor.paragraphIndex, stableAnchor.characterOffset, offset)
            }
        }
        LaunchedEffect(currentLayout, settings.readingMode) {
            val measured = currentLayout ?: return@LaunchedEffect
            // Ignore the first restored viewport: retain the exact text anchor, not its new page start.
            snapshotFlow {
                if (appliedLayout !== measured || appliedMode != settings.readingMode) null
                else when (settings.readingMode) {
                    ReadingMode.SLIDE -> if (pager.isScrollInProgress) null else pager.settledPage to 0
                    ReadingMode.INSTANT -> instantPage to 0
                    ReadingMode.SCROLL -> list.firstVisibleItemIndex to list.firstVisibleItemScrollOffset
                }
            }.filterNotNull().distinctUntilChanged().drop(1).collect { (rawPage, offset) ->
                if (settings.readingMode == ReadingMode.SLIDE && rawPage < firstPage) {
                    store.selectChapter(state.chapterIndex - 1, atEnd = true)
                } else if (settings.readingMode == ReadingMode.SLIDE && rawPage >= firstPage + measured.pages.size) {
                    store.selectChapter(state.chapterIndex + 1)
                } else {
                    val page = (rawPage - if (settings.readingMode == ReadingMode.SLIDE) firstPage else 0)
                        .coerceIn(0, measured.pages.lastIndex)
                    saveAnchor(if (settings.readingMode == ReadingMode.SCROLL)
                        anchorAtY(measured.pages[page], offset.toFloat()) else measured.pages[page].anchor, offset)
                }
                onInteraction()
            }
        }
        val visiblePage = when (settings.readingMode) {
            ReadingMode.SLIDE -> pager.currentPage - firstPage
            ReadingMode.INSTANT -> instantPage
            ReadingMode.SCROLL -> list.firstVisibleItemIndex
        }.coerceIn(0, (currentLayout?.pages?.lastIndex ?: 0))
        val move: (Int) -> Unit = move@{ direction ->
            if (!ready) return@move
            onInteraction()
            val measured = currentLayout ?: return@move
            val target = visiblePage + direction
            if (target < 0) {
                if (previousChapter) store.selectChapter(state.chapterIndex - 1, atEnd = true)
            } else if (target > measured.pages.lastIndex) {
                if (nextChapter) store.selectChapter(state.chapterIndex + 1)
            } else {
                saveAnchor(measured.pages[target].anchor)
                scope.launch {
                    when (settings.readingMode) {
                        ReadingMode.SLIDE -> pager.animateScrollToPage(target + firstPage)
                        ReadingMode.INSTANT -> instantPage = target
                        ReadingMode.SCROLL -> list.animateScrollToItem(target)
                    }
                }
            }
        }
        val tapModifier = Modifier.pointerInput(settings.readingMode, ready, visiblePage, state.chromeVisible) {
            detectTapGestures { position ->
                if (settings.readingMode == ReadingMode.SCROLL || position.x in size.width * 0.32f..size.width * 0.68f)
                    onToggleChrome()
                else move(if (position.x < size.width / 2f) -1 else 1)
            }
        }
        val accessibility = Modifier.semantics {
            stateDescription = "第 ${state.chapterIndex + 1} 章，第 ${visiblePage + 1} / ${currentLayout?.pages?.size ?: 1} 页"
            customActions = listOf(
                CustomAccessibilityAction("显示或隐藏阅读控制") { onToggleChrome(); true },
                CustomAccessibilityAction("上一页") { move(-1); true },
                CustomAccessibilityAction("下一页") { move(1); true })
        }
        Box(Modifier.fillMaxSize().then(tapModifier).then(accessibility)) {
            if (currentLayout == null) {
                CircularProgressIndicator(Modifier.align(Alignment.Center), size = 28.dp)
            } else {
                val pageModifier = Modifier.fillMaxWidth().height(pageHeight)
                val viewport = Modifier.fillMaxSize().padding(start = margin, end = margin, top = 26.dp, bottom = 46.dp)
                when (settings.readingMode) {
                    ReadingMode.SLIDE -> HorizontalPager(state = pager, modifier = viewport,
                        userScrollEnabled = ready, beyondViewportPageCount = 0) { page ->
                        val index = page - firstPage
                        if (index in currentLayout.pages.indices) {
                            MeasuredSpread(currentLayout.pages[index], currentLayout.paragraphs, texts,
                                columnWidth, gapPx, pageModifier)
                        } else Box(pageModifier, contentAlignment = Alignment.Center) {
                            Text(if (index < 0) "松开进入上一章" else "松开进入下一章")
                        }
                    }
                    ReadingMode.INSTANT -> {
                        var drag by remember { mutableFloatStateOf(0f) }
                        Box(viewport.pointerInput(ready, visiblePage) {
                            detectHorizontalDragGestures(onDragStart = { drag = 0f },
                                onDragEnd = { if (abs(drag) > 48.dp.toPx()) move(if (drag < 0) 1 else -1) },
                                onHorizontalDrag = { change, amount -> change.consume(); drag += amount })
                        }) {
                            MeasuredSpread(currentLayout.pages[visiblePage], currentLayout.paragraphs, texts,
                                columnWidth, gapPx, pageModifier)
                        }
                    }
                    ReadingMode.SCROLL -> LazyColumn(state = list, modifier = viewport, userScrollEnabled = ready) {
                        itemsIndexed(currentLayout.pages, key = { index, _ -> index }) { _, page ->
                            MeasuredSpread(page, currentLayout.paragraphs, texts, columnWidth, gapPx, pageModifier)
                        }
                        item {
                            Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.Center) {
                                TextButton(if (nextChapter) "继续下一章" else "已读至全书末尾", {
                                    if (nextChapter) store.selectChapter(state.chapterIndex + 1)
                                }, enabled = ready && nextChapter, minHeight = 48.dp)
                            }
                        }
                    }
                }
            }
        }
        // The floating dock replaces the footer line while the chrome is up, so they never overlap.
        if (settings.showReadingFooter && !state.chromeVisible) {
            Row(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(horizontal = margin, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MutedText(chapter.title.ifBlank { "正文" }, Modifier.weight(1f), maxLines = 1)
                MutedText("${visiblePage + 1} / ${currentLayout?.pages?.size ?: "…"} · ${state.chapterIndex + 1}/${book.chapters.size}")
            }
        }
        val totalChapters = (state.manifest?.chapters?.size ?: book.chapters.size).coerceAtLeast(1)
        val pageCount = (currentLayout?.pages?.size ?: 1).coerceAtLeast(1)
        val chapterFraction = ((visiblePage + 1).toFloat() / pageCount).coerceIn(0f, 1f)
        val percent = (((state.chapterIndex + chapterFraction) / totalChapters) * 100f).roundToInt().coerceIn(1, 100)
        val progressText = "${(state.chapterIndex + 1).coerceAtMost(totalChapters)} / $totalChapters · $percent%"
        // Immersive chrome: a gradient-scrimmed floating header, never a solid bar or divider.
        AnimatedVisibility(
            visible = state.chromeVisible && !closing,
            enter = slideInVertically(animationSpec = tween(ChromeInMillis, easing = MiuixEaseOut)) { -it } +
                fadeIn(animationSpec = tween(ChromeInMillis)),
            exit = slideOutVertically(animationSpec = tween(ChromeOutMillis, easing = MiuixEaseIn)) { -it } +
                fadeOut(animationSpec = tween(ChromeOutMillis)),
            modifier = Modifier.align(Alignment.TopCenter),
        ) {
            GradientHeaderScrim {
                Row(
                    modifier = Modifier.fillMaxWidth()
                        .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top + WindowInsetsSides.Horizontal))
                        .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    MiuixCircleButton(Glyph.BACK, "返回书架", onClose, size = TouchTarget)
                    Text(chapter.title.ifBlank { "正文" }, Modifier.weight(1f), fontSize = 15.sp,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1,
                        overflow = TextOverflow.Ellipsis)
                    MiuixCircleButton(Glyph.TOC, "打开目录", onDirectory, size = TouchTarget)
                }
            }
        }
        AnimatedVisibility(
            visible = state.chromeVisible && !closing,
            enter = slideInVertically(animationSpec = tween(ChromeInMillis, easing = MiuixEaseOut)) { it } +
                fadeIn(animationSpec = tween(ChromeInMillis)),
            exit = slideOutVertically(animationSpec = tween(ChromeOutMillis, easing = MiuixEaseIn)) { it } +
                fadeOut(animationSpec = tween(ChromeOutMillis)),
            modifier = Modifier.align(Alignment.BottomCenter),
        ) {
            Box(
                Modifier.fillMaxWidth()
                    .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom + WindowInsetsSides.Horizontal))
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                contentAlignment = Alignment.Center,
            ) {
                MiuixDockPill(Modifier.fillMaxWidth()) {
                    DockAction(Glyph.BOOK, "目录", onDirectory)
                    Text(progressText, Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
                        fontSize = 13.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        textAlign = TextAlign.Center, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    DockAction(Glyph.TUNE, "设置", onSettings)
                }
            }
        }
    }
}

/** 44dp minimum touch target; the visible glyph stays small inside it. */
private val TouchTarget = 44.dp
private const val ChromeInMillis = 240
private const val ChromeOutMillis = 200

/** Glyph + label action inside the floating reading dock. */
@Composable
private fun DockAction(glyph: Glyph, label: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = TouchTarget)
            .padding(horizontal = 8.dp)
            .semantics { contentDescription = label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        MiuixGlyph(glyph, MiuixTheme.colorScheme.onSurface, 20.dp)
        Text(label, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1)
    }
}

/** Draw the exact measured paragraphs, clipped by original line bounds; no substring reflow. */
@Composable
private fun MeasuredSpread(page: MeasuredPage, paragraphs: List<TextLayoutResult>, texts: List<String>,
    columnWidth: Int, gap: Float, modifier: Modifier) {
    val color = MiuixTheme.colorScheme.onSurface
    val spoken = remember(page, texts) {
        page.columns.flatMap { it }.joinToString("\n") { texts[it.paragraphIndex].substring(it.start, it.end) }
    }
    Canvas(modifier.clipToBounds().semantics { text = AnnotatedString(spoken) }) {
        page.columns.forEachIndexed { columnIndex, slices ->
            val x = columnIndex * (columnWidth + gap)
            slices.forEach { slice ->
                clipRect(left = x, top = slice.top, right = x + columnWidth, bottom = slice.top + slice.height) {
                    drawText(paragraphs[slice.paragraphIndex], color = color,
                        topLeft = Offset(x, slice.top - slice.sourceTop))
                }
            }
        }
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/ReadingSettings.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.*
import top.yukonga.miuix.kmp.basic.*
import top.yukonga.miuix.kmp.overlay.OverlayBottomSheet
import top.yukonga.miuix.kmp.theme.MiuixTheme

/**
 * Typography sheet. Same bottom-sheet surface as the table of contents so both entry points
 * behave alike; every row keeps a 48dp minimum height and 16dp inside spacing.
 */
@Composable
internal fun ReadingSettings(
    show: Boolean,
    settings: ReaderSettings,
    onChange: (ReaderSettings) -> Unit,
    onDismiss: () -> Unit,
    maxHeight: Dp = 560.dp,
) {
    OverlayBottomSheet(
        show = show,
        title = "排版设置",
        onDismissRequest = onDismiss,
        cornerRadius = 28.dp,
    ) {
        Column(
            Modifier.fillMaxWidth()
                .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom))
                .heightIn(max = maxHeight)
                .verticalScroll(rememberScrollState())
                .padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 20.dp),
            verticalArrangement = Arrangement.spacedBy(22.dp),
        ) {
            SettingsSection("翻页与分栏") {
                Choice("阅读方式", listOf("滑动", "无动画", "滚动"),
                    listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL).indexOf(settings.readingMode)) {
                    onChange(settings.copy(readingMode = listOf(ReadingMode.SLIDE, ReadingMode.INSTANT, ReadingMode.SCROLL)[it]))
                }
                Choice("分栏", listOf("自动", "单栏", "双栏"),
                    listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE).indexOf(settings.columnMode)) {
                    onChange(settings.copy(columnMode = listOf(ColumnMode.AUTO, ColumnMode.SINGLE, ColumnMode.DOUBLE)[it]))
                }
                SettingsNote("自动在宽度达到 840dp 时使用双栏。双栏从左至右阅读；滚动模式按双栏书页连续排列。")
            }
            SettingsSection("文字与留白") {
                Choice("字体", listOf("衬线", "无衬线", "等宽"),
                    listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO).indexOf(settings.fontFamily)) {
                    onChange(settings.copy(fontFamily = listOf(ReaderFont.SERIF, ReaderFont.SANS, ReaderFont.MONO)[it]))
                }
                StepSetting("字号", settings.fontSize, 14f, 40f, 1f, "sp") { onChange(settings.copy(fontSize = it)) }
                StepSetting("行距", settings.lineHeight, 1.2f, 2.4f, 0.1f, "倍") { onChange(settings.copy(lineHeight = it)) }
                StepSetting("页边距", settings.horizontalMargin, 8f, 56f, 4f, "dp") { onChange(settings.copy(horizontalMargin = it)) }
                StepSetting("段间距", settings.paragraphSpacing, 0f, 40f, 2f, "dp") { onChange(settings.copy(paragraphSpacing = it)) }
                StepSetting("字间距", settings.letterSpacing, -0.5f, 3f, 0.25f, "sp") { onChange(settings.copy(letterSpacing = it)) }
                ToggleSetting("首行缩进", settings.firstLineIndent) { onChange(settings.copy(firstLineIndent = it)) }
                ToggleSetting("加粗正文", settings.bold) { onChange(settings.copy(bold = it)) }
            }
            SettingsSection("阅读主题") {
                Choice("纸张", listOf("系统", "明亮", "纸色", "深色"),
                    listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK).indexOf(settings.theme)) {
                    onChange(settings.copy(theme = listOf(ReaderTheme.SYSTEM, ReaderTheme.LIGHT, ReaderTheme.SEPIA, ReaderTheme.DARK)[it]))
                }
            }
            SettingsSection("阅读控制") {
                ToggleSetting("控制栏自动隐藏", settings.autoHideControls) { onChange(settings.copy(autoHideControls = it)) }
                ToggleSetting("显示阅读页脚", settings.showReadingFooter) { onChange(settings.copy(showReadingFooter = it)) }
                SettingsNote("轻点中央显示 / 隐藏控制栏；分页时轻点两侧翻页。字号、分栏或旋转后按文字位置恢复，不存储页码。")
            }
            PrimaryAction("完成", onDismiss, Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
            color = MiuixTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() })
        Card(Modifier.fillMaxWidth(), insideMargin = PaddingValues(18.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(16.dp), content = content)
        }
    }
}

@Composable
private fun Choice(label: String, labels: List<String>, selected: Int, onSelect: (Int) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, style = MiuixTheme.textStyles.body2)
        TabRowWithContour(tabs = labels, selectedTabIndex = selected.coerceAtLeast(0),
            onTabSelected = onSelect, modifier = Modifier.fillMaxWidth(), minWidth = 52.dp)
    }
}

@Composable
private fun StepSetting(label: String, value: Float, minimum: Float, maximum: Float,
    step: Float, unit: String, onChange: (Float) -> Unit) {
    val rounded = (value * 100).toInt() / 100f
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1)
        Text("$rounded$unit", fontSize = 14.sp, maxLines = 1,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        StepButton("−", "减小$label", enabled = value > minimum) {
            onChange((value - step).coerceAtLeast(minimum))
        }
        StepButton("＋", "增大$label", enabled = value < maximum) {
            onChange((value + step).coerceAtMost(maximum))
        }
    }
}

/** 44dp square stepper button; the symbol is text, not an icon dependency. */
@Composable
private fun StepButton(symbol: String, description: String, enabled: Boolean, onClick: () -> Unit) {
    val container = MiuixTheme.colorScheme.surfaceContainerHigh
    Box(
        modifier = Modifier.size(SettingsTouchTarget)
            .clip(RoundedCornerShape(12.dp))
            .background(if (enabled) container else container.copy(alpha = 0.5f))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics {
                role = Role.Button
                contentDescription = description
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(symbol, fontSize = 18.sp, fontWeight = FontWeight.Medium,
            color = if (enabled) MiuixTheme.colorScheme.onSurface
            else MiuixTheme.colorScheme.onSurfaceVariantSummary)
    }
}

@Composable
private fun ToggleSetting(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1)
        Switch(checked = checked, onCheckedChange = onChange,
            modifier = Modifier.semantics { contentDescription = label })
    }
}

@Composable
private fun SettingsNote(text: String) {
    Text(text, fontSize = 12.sp, lineHeight = 18.sp,
        color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f))
}

private val SettingsTouchTarget = 44.dp

@Composable
internal fun PrimaryAction(label: String, action: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) =
    TextButton(label, action, modifier, enabled = enabled, minHeight = 48.dp,
        colors = ButtonDefaults.textButtonColorsPrimary())

@Composable
internal fun MutedText(text: String, modifier: Modifier = Modifier, maxLines: Int = Int.MAX_VALUE) = Text(
    text, modifier, fontSize = 13.sp, lineHeight = 20.sp, maxLines = maxLines,
    overflow = TextOverflow.Ellipsis, color = MiuixTheme.colorScheme.onSurface.copy(alpha = 0.62f),
)

@Composable
internal fun ProgressTrack(progress: Float, modifier: Modifier = Modifier) {
    LinearProgressIndicator(modifier = modifier, progress = progress.coerceIn(0f, 1f), height = 3.dp)
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/TocSheet.kt': r'''package dev.leaf.reader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.leaf.reader.BookDocument
import dev.leaf.reader.BookManifest
import top.yukonga.miuix.kmp.basic.TabRowWithContour
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextField
import top.yukonga.miuix.kmp.basic.TextFieldDefaults
import top.yukonga.miuix.kmp.theme.MiuixTheme

/**
 * Table-of-contents sheet body. It only renders state it is given: chapter titles and the
 * manifest's character counts. Nothing here invents chapters, bookmarks or notes.
 */
@Composable
internal fun TocSheet(
    book: BookDocument,
    manifest: BookManifest?,
    currentChapter: Int,
    progressText: String,
    maxHeight: Dp,
    onSelectChapter: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val total = manifest?.chapters?.size?.takeIf { it > 0 } ?: book.chapters.size
    val current = currentChapter.coerceIn(0, (total - 1).coerceAtLeast(0))
    var tab by remember(book.id) { mutableIntStateOf(TocDirectoryTab) }
    var query by remember(book.id) { mutableStateOf("") }
    var descending by remember(book.id) { mutableStateOf(false) }
    var showCounts by remember(book.id) { mutableStateOf(true) }
    var compact by remember(book.id) { mutableStateOf(false) }
    var pendingScroll by remember(book.id) { mutableStateOf<Int?>(null) }
    val matches = remember(book.chapters, query, descending) {
        val trimmed = query.trim()
        val filtered = if (trimmed.isEmpty()) {
            book.chapters.indices.toList()
        } else {
            book.chapters.indices.filter { index ->
                book.chapters[index].title.ifBlank { "正文" }.contains(trimmed, ignoreCase = true)
            }
        }
        if (descending) filtered.asReversed() else filtered
    }
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = current)
    LaunchedEffect(pendingScroll, matches) {
        val target = pendingScroll ?: return@LaunchedEffect
        pendingScroll = null
        listState.animateScrollToItem(target.coerceIn(0, (matches.size - 1).coerceAtLeast(0)))
    }
    val currentTitle = chapterTitle(book, current)

    Column(
        Modifier.fillMaxWidth()
            .heightIn(max = maxHeight)
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom))
            .padding(bottom = 14.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            TocCover(book, Modifier.width(40.dp).height(54.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(book.title, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { heading() })
                Text(currentTitle, fontSize = 12.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            CountPill(progressText)
        }
        Spacer(Modifier.height(12.dp))
        TabRowWithContour(
            tabs = TocTabs,
            selectedTabIndex = tab,
            onTabSelected = { tab = it },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
                .semantics { contentDescription = "目录分区" },
        )
        Spacer(Modifier.height(12.dp))
        when (tab) {
            TocDirectoryTab -> {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    TextField(
                        value = query,
                        onValueChange = { query = it },
                        modifier = Modifier.weight(1f).heightIn(min = TocButtonSize)
                            .semantics { contentDescription = "搜索章节" },
                        insideMargin = DpSize(12.dp, 8.dp),
                        cornerRadius = 22.dp,
                        label = "搜索章节…",
                        useLabelAsPlaceholder = true,
                        singleLine = true,
                        textStyle = MiuixTheme.textStyles.body2,
                        colors = TextFieldDefaults.textFieldColors(
                            backgroundColor = MiuixTheme.colorScheme.surfaceContainerHigh,
                            labelColor = MiuixTheme.colorScheme.onSurfaceVariantSummary,
                        ),
                        leadingIcon = {
                            Box(Modifier.padding(start = 12.dp, end = 4.dp)) {
                                MiuixGlyph(Glyph.SEARCH, MiuixTheme.colorScheme.onSurfaceVariantSummary, 18.dp)
                            }
                        },
                    )
                    TocIconButton(Glyph.REFRESH, "回到当前章节") {
                        query = ""
                        pendingScroll = if (descending) total - 1 - current else current
                    }
                    TocIconButton(Glyph.TAG,
                        if (showCounts) "隐藏章节字数" else "显示章节字数",
                        highlighted = showCounts) { showCounts = !showCounts }
                    TocIconButton(Glyph.SORT,
                        if (descending) "切换为正序" else "切换为倒序",
                        highlighted = descending) { descending = !descending }
                    TocIconButton(Glyph.MORE,
                        if (compact) "切换为宽松行距" else "切换为紧凑行距",
                        highlighted = compact) { compact = !compact }
                }
                // Very short panels (16:9 landscape) drop the extra card so the list keeps real space.
                val shortPanel = maxHeight < 400.dp
                Spacer(Modifier.height(if (shortPanel) 8.dp else 14.dp))
                if (!shortPanel) {
                    CurrentChapterCard(
                        title = currentTitle,
                        countText = countText(manifest, current),
                        onClick = onDismiss,
                    )
                    Spacer(Modifier.height(8.dp))
                }
                if (matches.isEmpty()) {
                    Text("没有匹配“${query.trim()}”的章节",
                        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 24.dp),
                        fontSize = 14.sp, color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxWidth().weight(1f, fill = false),
                    ) {
                        items(count = matches.size, key = { matches[it] }) { position ->
                            val index = matches[position]
                            TocChapterRow(
                                title = chapterTitle(book, index),
                                countText = if (showCounts) countText(manifest, index) else "",
                                current = index == current,
                                compact = compact,
                                onClick = { onSelectChapter(index) },
                            )
                        }
                    }
                }
            }
            TocInfoTab -> TocInfoPanel(book, total, currentTitle, progressText)
            TocBookmarkTab -> TocPlaceholder("书签功能即将加入", "阅读时长按段落添加书签，之后会集中显示在这里。")
            else -> TocPlaceholder("笔记功能即将加入", "划线摘录与阅读想法会集中显示在这里。")
        }
    }
}

private val TocTabs = listOf("信息", "目录", "书签", "笔记")
private const val TocInfoTab = 0
private const val TocDirectoryTab = 1
private const val TocBookmarkTab = 2
private val TocButtonSize = 44.dp
private val TocButtonVisual = 36.dp

private fun chapterTitle(book: BookDocument, index: Int): String =
    book.chapters.getOrNull(index)?.title?.ifBlank { "正文" } ?: "正文"

/** Character counts come from the manifest; a missing entry shows a dash instead of a guess. */
private fun countText(manifest: BookManifest?, index: Int): String {
    val count = manifest?.chapters?.getOrNull(index)?.characterCount ?: return "—"
    return "${count}字"
}

/** Typographic cover in Miuix colours; the reader ships no artwork, so nothing is fetched. */
@Composable
private fun TocCover(book: BookDocument, modifier: Modifier) {
    val primary = MiuixTheme.colorScheme.primary
    Box(
        modifier.clip(RoundedCornerShape(8.dp))
            .background(primary.copy(alpha = 0.14f))
            .clearAndSetSemantics { },
    ) {
        Box(Modifier.fillMaxHeight().width(4.dp).background(primary.copy(alpha = 0.5f)))
        Text(book.title.take(2), Modifier.align(Alignment.Center).padding(start = 4.dp, end = 3.dp),
            fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = primary, maxLines = 1)
    }
}

/** 44dp touch target with a 36dp rounded-square visual, as in the reference sheet. */
@Composable
private fun TocIconButton(
    glyph: Glyph,
    description: String,
    highlighted: Boolean = false,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier.size(TocButtonSize).clip(RoundedCornerShape(12.dp))
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            modifier = Modifier.size(TocButtonVisual).clip(RoundedCornerShape(11.dp))
                .background(
                    if (highlighted) MiuixTheme.colorScheme.surfaceContainerHighest
                    else MiuixTheme.colorScheme.surfaceContainerHigh,
                ),
            contentAlignment = Alignment.Center,
        ) {
            MiuixGlyph(
                glyph,
                if (highlighted) MiuixTheme.colorScheme.onSurface
                else MiuixTheme.colorScheme.onSurfaceVariantSummary,
                17.dp,
            )
        }
    }
}

@Composable
private fun CurrentChapterCard(title: String, countText: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(MiuixTheme.colorScheme.surfaceContainerHigh)
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = 48.dp)
            .padding(start = 16.dp, end = 14.dp, top = 8.dp, bottom = 8.dp)
            .semantics {
                contentDescription = "返回当前章节：$title"
                stateDescription = "当前章节"
            },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(title, Modifier.weight(1f), fontSize = 15.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
        CountPill(
            text = countText,
            container = MiuixTheme.colorScheme.primaryContainer,
            content = MiuixTheme.colorScheme.onPrimaryContainer,
        )
    }
}

@Composable
private fun TocChapterRow(
    title: String,
    countText: String,
    current: Boolean,
    compact: Boolean,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .then(if (current) Modifier.background(MiuixTheme.colorScheme.surfaceContainerHigh) else Modifier)
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = if (compact) 44.dp else 48.dp)
            .padding(horizontal = 12.dp, vertical = if (compact) 2.dp else 6.dp)
            .then(if (current) Modifier.semantics { stateDescription = "当前章节" } else Modifier),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            title,
            Modifier.weight(1f),
            fontSize = 15.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = if (current) MiuixTheme.colorScheme.onSurfaceVariantSummary
            else MiuixTheme.colorScheme.onSurface,
        )
        if (countText.isNotEmpty()) {
            CountPill(
                text = countText,
                container = if (current) MiuixTheme.colorScheme.primaryContainer
                else MiuixTheme.colorScheme.surfaceContainerHighest,
                content = if (current) MiuixTheme.colorScheme.onPrimaryContainer
                else MiuixTheme.colorScheme.onSurfaceVariantSummary,
            )
        }
    }
}

@Composable
private fun TocInfoPanel(book: BookDocument, total: Int, currentTitle: String, progressText: String) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        TocInfoLine("书名", book.title)
        TocInfoLine("作者", book.author.ifBlank { "佚名" })
        TocInfoLine("格式", book.format)
        TocInfoLine("章数", "$total 章")
        TocInfoLine("当前章", currentTitle)
        TocInfoLine("进度", progressText)
    }
}

@Composable
private fun TocInfoLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(label, Modifier.width(56.dp), fontSize = 13.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary, maxLines = 1)
        Text(value, Modifier.weight(1f), fontSize = 14.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun TocPlaceholder(title: String, detail: String) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(title, fontSize = 15.sp, fontWeight = FontWeight.Medium)
        Text(detail, fontSize = 13.sp, lineHeight = 20.sp,
            color = MiuixTheme.colorScheme.onSurfaceVariantSummary)
    }
}
''',
    'shared/src/commonMain/kotlin/dev/leaf/reader/ui/Pagination.kt': r'''package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter

/** Local item coordinates only: metadata chapters are deliberately not accepted here. */
internal fun chapterReadingTexts(chapter: BookChapter, chapterIndex: Int): List<String> =
    listOf(chapter.title.ifBlank { "第 ${chapterIndex + 1} 章" }) + chapter.paragraphs

/** UTF-16 coordinates in the loaded chapter: heading=0, body paragraphs=1..n. */
internal data class TextAnchor(val paragraphIndex: Int = 0, val characterOffset: Int = 0)

internal data class MeasuredLine(val start: Int, val end: Int, val top: Float, val bottom: Float)
internal data class PageSlice(
    val paragraphIndex: Int,
    val start: Int,
    val end: Int,
    val top: Float,
    val sourceTop: Float,
    val height: Float,
    val lines: List<MeasuredLine>,
)
internal data class MeasuredPage(val columns: List<List<PageSlice>>) {
    val anchor: TextAnchor get() = columns.firstNotNullOfOrNull { column ->
        column.firstOrNull()?.let { TextAnchor(it.paragraphIndex, it.start) }
    } ?: TextAnchor()
}

/** Move a UTF-16 boundary backwards if it would separate a surrogate pair. */
internal fun safeTextOffset(text: String, offset: Int): Int {
    val value = offset.coerceIn(0, text.length)
    return if (value > 0 && value < text.length && text[value].isLowSurrogate() &&
        text[value - 1].isHighSurrogate()) value - 1 else value
}

internal fun clampAnchor(texts: List<String>, anchor: TextAnchor): TextAnchor {
    if (texts.isEmpty()) return TextAnchor()
    val item = anchor.paragraphIndex.coerceIn(0, texts.lastIndex)
    return TextAnchor(item, safeTextOffset(texts[item], anchor.characterOffset))
}

/**
 * Pure chapter-only paginator. The injected callback is the only platform-dependent operation.
 * It measures each item once at the actual column width, not once per candidate substring.
 * Line ranges must cover the original text (including newline characters), without overlaps.
 * Empty paragraphs still occupy a measured line and retain an anchor.
 */
internal fun paginateChapter(
    texts: List<String>,
    columnWidth: Int,
    columnHeight: Float,
    columnCount: Int,
    paragraphSpacing: Float,
    measure: (paragraphIndex: Int, text: String, width: Int) -> List<MeasuredLine>,
): List<MeasuredPage> {
    require(columnWidth > 0 && columnHeight.isFinite() && columnHeight > 0f)
    require(columnCount in 1..2)
    require(paragraphSpacing.isFinite() && paragraphSpacing >= 0f)
    if (texts.isEmpty()) return listOf(MeasuredPage(List(columnCount) { emptyList() }))
    val pages = mutableListOf<MeasuredPage>()
    var columns = MutableList(columnCount) { mutableListOf<PageSlice>() }
    var column = 0
    var y = 0f
    fun advance() {
        y = 0f
        column++
        if (column == columnCount) {
            pages += MeasuredPage(columns.map { it.toList() })
            columns = MutableList(columnCount) { mutableListOf() }
            column = 0
        }
    }
    texts.forEachIndexed { item, text ->
        val lines = measure(item, text, columnWidth)
        require(lines.isNotEmpty()) { "A paragraph must have at least one measured line" }
        var covered = 0
        lines.forEach { line ->
            require(line.start == covered && line.end in line.start..text.length)
            require(safeTextOffset(text, line.start) == line.start && safeTextOffset(text, line.end) == line.end)
            require(line.top.isFinite() && line.bottom.isFinite() && line.bottom > line.top)
            covered = line.end
        }
        require(covered == text.length) { "Measured lines must cover the original text" }
        var first = 0
        while (first < lines.size) {
            if (y >= columnHeight && columns[column].isNotEmpty()) advance()
            val sourceTop = lines[first].top
            val remaining = columnHeight - y
            var until = first
            while (until < lines.size && lines[until].bottom - sourceTop <= remaining + 0.01f) until++
            if (until == first) {
                if (columns[column].isNotEmpty()) {
                    advance()
                    continue
                }
                // Ensure progress even for an oversized accessibility font / tiny viewport.
                until++
            }
            val height = lines[until - 1].bottom - sourceTop
            columns[column] += PageSlice(item, lines[first].start, lines[until - 1].end,
                y, sourceTop, height, lines.subList(first, until).toList())
            y += height
            first = until
            if (first < lines.size) advance()
        }
        y += paragraphSpacing
    }
    if (columns.any { it.isNotEmpty() }) pages += MeasuredPage(columns.map { it.toList() })
    return pages.ifEmpty { listOf(MeasuredPage(List(columnCount) { emptyList() })) }
}

/** Inclusive start, exclusive end: an exact page boundary belongs to the following page. */
internal fun pageForAnchor(pages: List<MeasuredPage>, anchor: TextAnchor): Int {
    pages.forEachIndexed { index, page ->
        page.columns.forEach { column -> column.forEach { slice ->
            if (slice.paragraphIndex == anchor.paragraphIndex &&
                anchor.characterOffset >= slice.start &&
                (anchor.characterOffset < slice.end || slice.start == slice.end)) return index
        } }
    }
    // End-of-paragraph/chapter anchors map to the last fragment of that item.
    return pages.indexOfLast { page -> page.columns.any { column ->
        column.any { it.paragraphIndex <= anchor.paragraphIndex }
    } }.coerceAtLeast(0)
}

internal fun anchorAtY(page: MeasuredPage, y: Float): TextAnchor {
    // In a two-column spread the left column is the reading-order start.
    val slices = page.columns.firstOrNull { it.isNotEmpty() }.orEmpty()
    val slice = slices.lastOrNull { it.top <= y } ?: return page.anchor
    val line = slice.lines.lastOrNull { it.top - slice.sourceTop + slice.top <= y }
    return TextAnchor(slice.paragraphIndex, line?.start ?: slice.start)
}

internal fun yForAnchor(page: MeasuredPage, anchor: TextAnchor): Float =
    page.columns.flatten().firstOrNull { it.paragraphIndex == anchor.paragraphIndex &&
        anchor.characterOffset >= it.start && anchor.characterOffset <= it.end }?.let { slice ->
        val line = slice.lines.lastOrNull { it.start <= anchor.characterOffset }
        slice.top + (line?.top ?: slice.sourceTop) - slice.sourceTop
    } ?: 0f
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ReaderStoreTest.kt': r'''@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.test.assertFailsWith

class ReaderStoreTest {
    private val sample = BookDocument(
        id = "a".repeat(64), title = "测试书", author = "作者", format = "TXT",
        chapters = listOf(BookChapter("第一章", listOf("第一段。", "第二段 😀。")), BookChapter("第二章", listOf("结束。"))),
    )
    private fun BookDocument.encoded() = Json.encodeToString(this)

    @Test fun importsAndReopensWithoutDuplicating() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        store.openBook(sample.id)
        advanceUntilIdle()
        store.updateProgress(3, 42)
        advanceUntilIdle() // The legacy adapter loads a different chapter asynchronously.
        store.importBookJson(sample.encoded())
        advanceUntilIdle()
        assertEquals(1, store.state.value.books.size)
        assertProgress(store.state.value.currentProgress, item = 3, scroll = 42, chapter = 1, paragraph = 0)
    }

    @Test fun positionAndSettingsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 75)
        store.updateSettings(ReaderSettings(fontSize = 25f, theme = ReaderTheme.SEPIA))
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(25f, restored.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restored.state.value.settings.theme)
        restored.openBook(sample.id); advanceUntilIdle()
        assertProgress(restored.state.value.currentProgress, item = 2, scroll = 75, chapter = 0, paragraph = 2)
    }

    @Test fun clampsInvalidProgressToExistingItems() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(9999, -3)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, item = 4, scroll = 0, chapter = 1, paragraph = 1)
    }

    @Test fun closingBeforeOpenFinishesDoesNotReopen() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun deletingDuringOpenDoesNotLeaveLoadingOverlay() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.deleteBook(sample.id)
        advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(store.state.value.currentBook)
        assertFalse(store.state.value.busy)
    }

    @Test fun removesShelfAndDerivedBookButNotOtherFiles() = runTest {
        val files = MemoryFiles()
        files.values["unrelated"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.deleteBook(sample.id); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values["book-${sample.id}.json"])
        assertNull(files.values["book-${sample.id}.manifest.json"])
        assertTrue(files.values.keys.none { it.startsWith("book-${sample.id}-") })
        assertEquals("keep", files.values["unrelated"])
    }

    @Test fun rejectedDocumentDoesNotReachShelf() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.copy(id = "../escape").encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
        assertTrue(files.values.keys.none { it.contains("escape") })
    }

    @Test fun failedIndexWriteRollsBackShelfAndPreservesOldIndex() = runTest {
        val files = MemoryFiles()
        val original = "{\"schema\":1,\"books\":[],\"settings\":{}}"
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failIndexWrite = true
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNotNull(store.state.value.error)
    }

    @Test fun corruptIndexIsNeverSilentlyOverwritten() = runTest {
        val files = MemoryFiles()
        files.values["library.json"] = "corrupt original"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.dismissError()
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.flush()
        assertEquals("corrupt original", files.values["library.json"])
        assertTrue(store.state.value.books.isEmpty())
        assertNotNull(store.state.value.error)
    }

    @Test fun reimportRepairsMissingDerivedFileWithoutLosingProgress() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(2, 7)
        val missingChapter = store.state.value.manifest!!.chapters[0].fileName
        store.closeBook()
        files.values.remove(missingChapter)
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        assertNotNull(store.state.value.currentBook)
        assertProgress(store.state.value.currentProgress, item = 2, scroll = 7, chapter = 0, paragraph = 2)
        assertNotNull(store.state.value.chapter)
    }

    @Test fun rapidOpeningKeepsLatestBook() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        val second = sample.copy(id = "b".repeat(64), title = "另一本")
        store.importBookJson(sample.encoded()); store.importBookJson(second.encoded()); advanceUntilIdle()
        store.openBook(sample.id)
        store.openBook(second.id)
        advanceUntilIdle()
        assertEquals(second.id, store.state.value.currentBook?.id)
    }

    @Test fun debounceSavesAndDismissErrorDoesNotLoseBook() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateProgress(1, 3)
        runCurrent(); advanceUntilIdle()
        assertTrue(files.values.getValue("library.json").contains("\"scrollOffset\":3"))
        store.reportError("测试提示"); store.dismissError()
        assertNull(store.state.value.error)
        assertEquals(sample.id, store.state.value.currentBook?.id)
    }

    @Test fun chapterAnchorsPersistAcrossAsyncNavigationAndRestart() = runTest {
        val files = MemoryFiles()
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.updateChapterProgress(paragraphIndex = 2, characterOffset = 5, scrollOffset = 11)
        // UTF-16 index 5 bisects the emoji and must move back to the high surrogate.
        assertProgress(store.state.value.currentProgress, 2, 11, 0, 2, character = 4)
        store.selectChapter(1)
        assertTrue(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        store.updateChapterProgress(0, 0, 0) // Initial/unmeasured UI saves must be ignored.
        assertProgress(store.state.value.books.single().progress, 2, 11, 0, 2, character = 4)
        advanceUntilIdle()
        assertEquals("第二章", store.state.value.chapter?.title)
        store.updateChapterProgress(1, 2, 9)
        store.flush()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restored.openBook(sample.id); advanceUntilIdle()
        assertEquals(1, restored.state.value.chapterIndex)
        assertFalse(restored.state.value.chapterBusy)
        assertProgress(restored.state.value.currentProgress, 4, 9, 1, 1, character = 2)
        assertProgress(restored.state.value.books.single().progress, 4, 9, 1, 1, character = 2)
    }

    @Test fun previousChapterAtEndClampsSentinelAfterBodyLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1); advanceUntilIdle()
        store.selectChapter(0, atEnd = true)
        assertTrue(store.state.value.chapterBusy)
        assertEquals(Int.MAX_VALUE, store.state.value.currentProgress.characterOffset)
        advanceUntilIdle()
        assertProgress(store.state.value.currentProgress, 2, 0, 0, 2,
            character = sample.chapters[0].paragraphs.last().length)
    }

    @Test fun rapidChapterSelectionAndCloseDiscardObsoleteLoads() = runTest {
        val store = ReaderStore(MemoryFiles(), this, StandardTestDispatcher(testScheduler))
        store.importBookJson(sample.encoded()); advanceUntilIdle()
        store.openBook(sample.id); advanceUntilIdle()
        store.selectChapter(1)
        store.selectChapter(0)
        advanceUntilIdle()
        assertEquals("第一章", store.state.value.chapter?.title)
        assertProgress(store.state.value.currentProgress, 0, 0, 0, 0)
        store.selectChapter(1)
        store.closeBook()
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        assertNull(store.state.value.manifest)
        assertNull(store.state.value.chapter)
        assertFalse(store.state.value.chapterBusy)
        assertFalse(store.state.value.busy)
    }

    @Test fun allReadingAndShelfOptionsSurviveRestart() = runTest {
        val files = MemoryFiles()
        val settings = ReaderSettings(
            fontSize = 27f, lineHeight = 2f, theme = ReaderTheme.DARK,
            readingMode = ReadingMode.INSTANT, columnMode = ColumnMode.DOUBLE,
            shelfLayout = ShelfLayout.COMPACT, fontFamily = ReaderFont.MONO,
            horizontalMargin = 32f, paragraphSpacing = 18f, letterSpacing = 1.5f,
            firstLineIndent = false, bold = true, autoHideControls = false, showReadingFooter = false,
        )
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.updateSettings(settings)
        advanceUntilIdle()
        val restored = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(settings, restored.state.value.settings)
    }

    private fun assertProgress(
        actual: ReadingProgress, item: Int, scroll: Int, chapter: Int, paragraph: Int, character: Int = 0,
    ) {
        assertEquals(item, actual.itemIndex, "global item")
        assertEquals(scroll, actual.scrollOffset, "pixel offset")
        assertEquals(chapter, actual.chapterIndex, "chapter anchor")
        assertEquals(paragraph, actual.paragraphIndex, "chapter-local heading/paragraph")
        assertEquals(character, actual.characterOffset, "UTF-16 text anchor")
    }

    @Test fun settingsAndDocumentLimitsAreEnforced() {
        assertEquals(40f, ReaderSettings(fontSize = 100f).sanitized().fontSize)
        assertEquals(20f, ReaderSettings(fontSize = Float.NaN).sanitized().fontSize)
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = emptyList()).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(format = "PDF").validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf(" ")))).validate() }
        assertFailsWith<IllegalArgumentException> { sample.copy(chapters = listOf(BookChapter("", listOf("x".repeat(16001))))).validate() }
        sample.validate()
    }
}

private class MemoryFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    var failIndexWrite = false
    override fun readText(name: String) = values[name]
    override fun writeText(name: String, value: String) {
        if (failIndexWrite && name == "library.json") error("disk full")
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 1000L
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ManifestStorageTest.kt': r'''@file:OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)

package dev.leaf.reader

import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ManifestStorageTest {
    private val id = "c".repeat(64)
    private val revision = "1".repeat(32)
    private fun canonical(bookId: String = id) = "book-$bookId.manifest.json"

    private data class Fixture(val manifest: BookManifest, val chapters: List<BookChapter>)

    private fun fixture(
        chapters: List<BookChapter> = List(5) { BookChapter("第 ${it + 1} 章", listOf("正文 $it 😀", "尾段 $it")) },
        revision: String = this.revision,
        title: String = "分章书籍",
    ): Fixture = Fixture(
        BookManifest(id = id, title = title, revision = revision, chapters = chapters.mapIndexed { index, chapter ->
            ChapterEntry(chapter.title, "book-$id-$revision-c$index.json", chapter.paragraphs.size,
                chapter.paragraphs.sumOf { it.length })
        }), chapters,
    )

    private fun ManifestFiles.install(fixture: Fixture) {
        fixture.chapters.forEachIndexed { index, chapter ->
            values[fixture.manifest.chapters[index].fileName] = Json.encodeToString(chapter)
        }
    }

    @Test fun chapterUtf16LimitAcceptsExact512KiAndRejectsOneMoreUnit() {
        assertEquals(512 * 1024, MAX_CHAPTER_UNITS)
        fun chapter(units: Int): BookChapter = BookChapter("边界", buildList {
            var remaining = units
            while (remaining > 0) {
                val size = minOf(remaining, 16000)
                add("字".repeat(size))
                remaining -= size
            }
        })
        val exact = chapter(512 * 1024)
        val entry = fixture(listOf(exact)).manifest.chapters.single()
        exact.validate(entry)
        assertEquals(512 * 1024, entry.characterCount)
        assertFailsWith<IllegalArgumentException> { chapter(512 * 1024 + 1).validate() }
        assertFailsWith<IllegalArgumentException> {
            fixture(listOf(exact)).manifest.copy(chapters = listOf(entry.copy(characterCount = 512 * 1024 + 1))).validate()
        }
        // UTF-16 units, not Unicode code points: each emoji occupies two units.
        assertEquals(16000, "😀".repeat(8000).length)
        assertFailsWith<IllegalArgumentException> { BookChapter("段落边界", listOf("😀".repeat(8001))).validate() }
    }

    @Test fun manifestRejectsTraversalAbsoluteAndWrongRevisionOrIndexNames() {
        val valid = fixture().manifest
        valid.validate()
        val name = valid.chapters.first().fileName
        val invalid = listOf(
            "../$name", "/$name", "folder/$name", "folder\\$name", "./$name",
            "book-${"d".repeat(64)}-$revision-c0.json",
            "book-$id-${"2".repeat(32)}-c0.json", "book-$id-$revision-c00.json",
            "book-$id-$revision-c1.json", "$name/..", "$name\u0000",
        )
        invalid.forEach { candidate ->
            assertFailsWith<IllegalArgumentException>(candidate) {
                valid.copy(chapters = valid.chapters.toMutableList().also {
                    it[0] = it[0].copy(fileName = candidate)
                }).validate()
            }
        }
        assertFailsWith<IllegalArgumentException> { valid.copy(schema = 1).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(revision = "A".repeat(32)).validate() }
        assertFailsWith<IllegalArgumentException> { valid.copy(id = "../bad").validate() }
    }

    @Test fun invalidManifestPathIsRejectedBeforeAnyBodyReadOrPublication() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values["unrelated.json"] = "keep"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        val invalid = draft.manifest.copy(chapters = draft.manifest.chapters.toMutableList().also {
            it[1] = it[1].copy(fileName = "../unrelated.json")
        })
        store.importManifestJson(Json.encodeToString(invalid)); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        assertTrue(store.state.value.books.isEmpty())
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertEquals("keep", files.values["unrelated.json"])
    }

    @Test fun paragraphLimitUsesLongArithmeticBeforeSummingManifestMetadata() {
        val counts = List(42949) { 100000 } + 67297 // 2^32 + 1, not one paragraph.
        val manifest = BookManifest(id = id, title = "溢出边界", revision = revision,
            chapters = counts.mapIndexed { index, count ->
                ChapterEntry("章", "book-$id-$revision-c$index.json", count, 1)
            })
        assertEquals(4_294_967_297L, counts.sumOf { it.toLong() })
        assertFailsWith<IllegalArgumentException> { manifest.validate() }
    }

    @Test fun schema1LibraryKeepsBackupAndMigratesSplitChapterProgressLazily() = runTest {
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "字".repeat(10000) }), BookChapter("后记", listOf("尾")),
        ))
        val original = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":2,"paragraphCount":41,"addedAt":10,"lastOpenedAt":20,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{"fontSize":23,"lineHeight":1.8,"theme":"SEPIA"}}"""
        val files = ManifestFiles()
        files.values["library.json"] = original
        val legacyRaw = Json.encodeToString(legacy)
        files.values["book-$id.json"] = legacyRaw
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()]) // Startup does not decode every old book body.
        assertEquals(ReadingMode.SLIDE, store.state.value.settings.readingMode)
        assertEquals(ShelfLayout.GRID, store.state.value.settings.shelfLayout)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        val manifest = assertNotNull(state.manifest)
        assertEquals(3, manifest.chapters.size)
        assertTrue(manifest.chapters.all { it.characterCount <= 512 * 1024 })
        assertEquals(400001L, state.books.single().characterCount)
        assertTrue(state.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals("长章（续）", state.chapter?.title)
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex) // New split heading shifts the legacy global index.
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(0, state.currentProgress.characterOffset)
        assertEquals(legacyRaw, files.values["book-$id.json"])
        store.closeBook()
        assertEquals(2, Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json")).schema)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(1, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(5, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(57, restarted.state.value.currentProgress.scrollOffset)
        assertEquals(original, files.values["library.v1-backup.json"])
        assertEquals(23f, restarted.state.value.settings.fontSize)
        assertEquals(ReaderTheme.SEPIA, restarted.state.value.settings.theme)
    }

    @Test fun canceledLegacyMigrationKeepsOriginalParagraphAnchor() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.openBook(id)
        store.closeBook() // The queued migration can finish I/O but must not publish a wrong anchor.
        advanceUntilIdle()
        assertNull(store.state.value.currentBook)
        store.openBook(id); advanceUntilIdle()
        assertEquals(1, store.state.value.currentProgress.chapterIndex)
        assertEquals(5, store.state.value.currentProgress.paragraphIndex)
        assertEquals(32, store.state.value.currentProgress.itemIndex)
        assertEquals(57, store.state.value.currentProgress.scrollOffset)
        val state = store.state.value
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun migrationIndexWriteFailureRetainsOriginalParagraphAfterRestart() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["book-$id.json"] = Json.encodeToString(legacy)
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        // Initial flush may succeed; every later index write fails once the migrated manifest exists.
        files.blockWrites = { name -> name == "library.json" && canonical() in files.values }
        store.openBook(id); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        val onDisk = Json.decodeFromString<LibrarySnapshot>(files.values.getValue("library.json"))
        assertEquals(-1, onDisk.books.single().progress.chapterIndex)
        assertEquals(31, onDisk.books.single().progress.itemIndex)
        files.blockWrites = { false }
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        val state = restarted.state.value
        assertEquals(1, state.currentProgress.chapterIndex)
        assertEquals(5, state.currentProgress.paragraphIndex)
        assertEquals(32, state.currentProgress.itemIndex)
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun legacyReimportMapsUnmigratedShelfAnchorBeforeFirstOpen() = runTest {
        val files = ManifestFiles()
        val legacy = BookDocument(id = id, title = "旧书", chapters = listOf(
            BookChapter("长章", List(40) { "段${it.toString().padStart(2, '0')}" + "字".repeat(9997) }),
        ))
        files.values["library.json"] = """{"schema":1,"books":[{"id":"$id","title":"旧书","author":"","format":"TXT","chapterCount":1,"paragraphCount":40,"addedAt":10,"progress":{"itemIndex":31,"scrollOffset":57}}],"settings":{}}"""
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importBookJson(Json.encodeToString(legacy)); advanceUntilIdle()
        val saved = store.state.value.books.single().progress
        assertEquals(1, saved.chapterIndex)
        assertEquals(5, saved.paragraphIndex)
        assertEquals(32, saved.itemIndex)
        store.openBook(id); advanceUntilIdle()
        val state = store.state.value
        assertEquals(57, state.currentProgress.scrollOffset)
        assertEquals(legacy.chapters.single().paragraphs[30],
            state.chapter?.paragraphs?.get(state.currentProgress.paragraphIndex - 1))
    }

    @Test fun existingV1BackupIsNeverOverwritten() = runTest {
        val files = ManifestFiles()
        files.values["library.json"] = """{"schema":1,"books":[],"settings":{}}"""
        files.values["library.v1-backup.json"] = "earlier backup"
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.flush()
        assertNull(store.state.value.error)
        assertEquals("earlier backup", files.values["library.v1-backup.json"])
    }

    @Test fun failedV1BackupPreventsOverwritingTheOnlyLegacyIndex() = runTest {
        val files = ManifestFiles()
        val original = """{"schema":1,"books":[],"settings":{"fontSize":22}}"""
        files.values["library.json"] = original
        files.failNextWrites["library.v1-backup.json"] = 1
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        assertNotNull(store.state.value.error)
        store.dismissError()
        store.updateSettings(ReaderSettings(fontSize = 30f))
        advanceUntilIdle()
        store.flush()
        assertEquals(original, files.values["library.json"])
        assertNull(files.values["library.v1-backup.json"])
    }

    @Test fun importSamplesEndpointsAndOpeningLoadsOnlyCurrentChapterBody() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.reads.clear()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        val bodyNames = draft.manifest.chapters.map { it.fileName }.toSet()
        assertEquals(listOf(draft.manifest.chapters.first().fileName, draft.manifest.chapters.last().fileName),
            files.reads.filter { it in bodyNames })
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertEquals(listOf(canonical(), draft.manifest.chapters[0].fileName), files.reads)
        assertEquals(draft.chapters[0], store.state.value.chapter)
        assertTrue(store.state.value.currentBook!!.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(5, store.state.value.currentBook!!.chapters.size)
        assertFalse(files.reads.contains("book-$id.json"))
        files.reads.clear()
        store.selectChapter(2); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[2].fileName), files.reads)
        assertEquals(draft.chapters[2], store.state.value.chapter)
    }

    @Test fun chapterCacheIsBoundedAndCloseDropsCachedBodies() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertTrue(files.reads.isEmpty())
        for (index in 1..3) { store.selectChapter(index); advanceUntilIdle() }
        files.reads.clear()
        store.selectChapter(0); advanceUntilIdle()
        assertEquals(listOf(draft.manifest.chapters[0].fileName), files.reads)
        store.closeBook()
        files.reads.clear()
        store.openBook(id); advanceUntilIdle()
        assertTrue(draft.manifest.chapters[0].fileName in files.reads)
    }

    @Test fun mismatchedMiddleChapterFailsOnDemandAndRetainsLastReadableShelfAnchor() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        files.values[draft.manifest.chapters[1].fileName] = Json.encodeToString(BookChapter("损坏", listOf("不匹配")))
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertNull(store.state.value.error) // Import validates bounded endpoints, not every chapter body.
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 17)
        store.selectChapter(1); advanceUntilIdle()
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.chapterBusy)
        assertNull(store.state.value.chapter)
        val saved = store.state.value.books.single().progress
        assertEquals(0, saved.chapterIndex)
        assertEquals(1, saved.paragraphIndex)
        assertEquals(2, saved.characterOffset)
        assertEquals(17, saved.scrollOffset)
        store.closeBook()
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(draft.chapters[0], restarted.state.value.chapter)
        assertEquals(0, restarted.state.value.currentProgress.chapterIndex)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
    }

    @Test fun newManifestIndexFailureRemovesCanonicalAndAllowsRetry() = runTest {
        val files = ManifestFiles()
        val draft = fixture()
        files.install(draft)
        val original = Json.encodeToString(LibrarySnapshot())
        files.values["library.json"] = original
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertTrue(store.state.value.books.isEmpty())
        assertEquals(original, files.values["library.json"])
        assertNull(files.values[canonical()])
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
        assertTrue(draft.manifest.chapters.all { it.fileName in files.values }) // Draft revision is recoverable.
        store.dismissError()
        store.importManifestJson(Json.encodeToString(draft.manifest)); advanceUntilIdle()
        assertEquals(id, store.state.value.books.single().id)
        assertNotNull(files.values[canonical()])
        assertNull(store.state.value.error)
    }

    @Test fun replacementIndexFailureRestoresPriorManifestShelfAndAnchorThenRecovers() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "新版书名")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        store.openBook(id); advanceUntilIdle()
        store.updateChapterProgress(1, 2, 13)
        store.closeBook()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites["library.json"] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        val restarted = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(old.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertEquals(13, restarted.state.value.currentProgress.scrollOffset)
        restarted.closeBook()
        restarted.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        restarted.openBook(id); advanceUntilIdle()
        assertEquals(replacement.manifest.revision, restarted.state.value.manifest?.revision)
        assertEquals(replacement.manifest.title, restarted.state.value.books.single().title)
        assertEquals(1, restarted.state.value.currentProgress.paragraphIndex)
        assertEquals(2, restarted.state.value.currentProgress.characterOffset)
        assertNull(restarted.state.value.error)
    }

    @Test fun failedAtomicCanonicalWritePreservesPreviouslyPublishedRevision() = runTest {
        val files = ManifestFiles()
        val old = fixture()
        val replacement = fixture(revision = "2".repeat(32), title = "未发布副本")
        files.install(old); files.install(replacement)
        val store = ReaderStore(files, this, StandardTestDispatcher(testScheduler))
        store.importManifestJson(Json.encodeToString(old.manifest)); advanceUntilIdle()
        val oldCanonical = files.values.getValue(canonical())
        val oldIndex = files.values.getValue("library.json")
        files.failNextWrites[canonical()] = 1
        store.importManifestJson(Json.encodeToString(replacement.manifest)); advanceUntilIdle()
        assertEquals(oldCanonical, files.values[canonical()])
        assertEquals(oldIndex, files.values["library.json"])
        assertEquals(old.manifest.title, store.state.value.books.single().title)
        assertNotNull(store.state.value.error)
        assertFalse(store.state.value.busy)
    }
}

/** Faults occur before commit, matching ReaderFiles' atomic-replacement contract. */
private class ManifestFiles : ReaderFiles {
    val values = mutableMapOf<String, String>()
    val reads = mutableListOf<String>()
    val failNextWrites = mutableMapOf<String, Int>()
    var blockWrites: (String) -> Boolean = { false }
    override fun readText(name: String): String? {
        reads += name
        return values[name]
    }
    override fun writeText(name: String, value: String) {
        if (blockWrites(name)) error("injected persistent pre-commit failure")
        val remaining = failNextWrites[name] ?: 0
        if (remaining > 0) {
            failNextWrites[name] = remaining - 1
            error("injected pre-commit write failure")
        }
        values[name] = value
    }
    override fun delete(name: String) { values.remove(name) }
    override fun nowMillis() = 2000L
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReadingItemsTest.kt': r'''package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter
import dev.leaf.reader.BookDocument
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Replaces legacy whole-book flattening tests with the chapter-local coordinate contract. */
class ReadingItemsTest {
    @Test fun headingAndParagraphsKeepExactLocalOrder() {
        val texts = chapterReadingTexts(BookChapter("第一章", listOf("甲", "乙")), 0)
        assertEquals(listOf("第一章", "甲", "乙"), texts)
        assertEquals("甲", texts[TextAnchor(paragraphIndex = 1).paragraphIndex])
    }

    @Test fun titleOnlyMetadataNeverSuppliesBodyText() {
        val metadata = BookDocument(id = "a".repeat(64), title = "测试书籍", chapters =
            listOf(BookChapter("第一章", emptyList()), BookChapter("第二章", emptyList())))
        val loaded = BookChapter("第二章", listOf("当前章正文"))
        val texts = chapterReadingTexts(loaded, 1)
        assertEquals(listOf("第二章", "当前章正文"), texts)
        assertTrue(metadata.chapters.all { it.paragraphs.isEmpty() })
        assertEquals(TextAnchor(1, 2), clampAnchor(texts, TextAnchor(1, 2)))
    }

    @Test fun emptyChapterStillOccupiesOneHeadingIndex() {
        assertEquals(listOf("序"), chapterReadingTexts(BookChapter("序", emptyList()), 0))
    }

    @Test fun blankTitlesGetReadableFallbackWithoutAddingItems() {
        val texts = chapterReadingTexts(BookChapter("  ", listOf("原文")), 7)
        assertEquals(listOf("第 8 章", "原文"), texts)
    }

    @Test fun blankAndDuplicateParagraphsAreNotDroppedOrMerged() {
        assertEquals(listOf("章", "", "重复", "重复"),
            chapterReadingTexts(BookChapter("章", listOf("", "重复", "重复")), 0))
    }

    @Test fun localAnchorStillAddressesSameTextAfterRecreatingChapter() {
        val chapter = BookChapter("第二章", listOf("甲乙", "丙丁😀"))
        val anchor = TextAnchor(paragraphIndex = 2, characterOffset = 2)
        val before = chapterReadingTexts(chapter, 1)
        val after = chapterReadingTexts(chapter.copy(paragraphs = chapter.paragraphs.toList()), 1)
        assertEquals(before[anchor.paragraphIndex].substring(anchor.characterOffset),
            after[anchor.paragraphIndex].substring(anchor.characterOffset))
        assertEquals("😀", after[anchor.paragraphIndex].substring(anchor.characterOffset))
    }

    @Test fun endOfChapterRequestClampsAfterBodyLoad() {
        val texts = chapterReadingTexts(BookChapter("章", listOf("尾😀")), 0)
        assertEquals(TextAnchor(1, 3), clampAnchor(texts, TextAnchor(Int.MAX_VALUE, Int.MAX_VALUE)))
    }
}
''',
    'shared/src/commonTest/kotlin/dev/leaf/reader/ui/ReaderPaginationTest.kt': r'''package dev.leaf.reader.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ReaderPaginationTest {
    /** Fake monospace measurement: width is code points per line; height is always ten. */
    private fun measure(index: Int, text: String, width: Int): List<MeasuredLine> {
        if (text.isEmpty()) return listOf(MeasuredLine(0, 0, 0f, 10f))
        val lines = mutableListOf<MeasuredLine>()
        var offset = 0
        while (offset < text.length) {
            val start = offset
            var count = 0
            while (offset < text.length && count < width) {
                offset += if (text[offset].isHighSurrogate() && offset + 1 < text.length &&
                    text[offset + 1].isLowSurrogate()) 2 else 1
                count++
                if (text[offset - 1] == '\n') break
            }
            lines += MeasuredLine(start, offset, lines.size * 10f, (lines.size + 1) * 10f)
        }
        return lines
    }

    @Test fun everyCharacterAppearsExactlyOnceAcrossColumnsAndPages() {
        val texts = listOf("Heading", "中文 mixed 😀 text\nnext line", "", "尾段".repeat(53))
        val pages = paginateChapter(texts, 5, 32f, 2, 4f, ::measure)
        assertTrue(pages.size > 1)
        texts.forEachIndexed { index, expected ->
            val slices = pages.flatMap { it.columns.flatten() }.filter { it.paragraphIndex == index }
            assertEquals(expected, slices.joinToString("") { expected.substring(it.start, it.end) })
            assertEquals(0, slices.first().start)
            assertEquals(expected.length, slices.last().end)
            slices.zipWithNext().forEach { (a, b) -> assertEquals(a.end, b.start) }
        }
    }

    @Test fun surrogateBoundariesAndAnchorClamping() {
        val text = "a😀b𠀀c"
        assertEquals(1, safeTextOffset(text, 2))
        assertEquals(4, safeTextOffset(text, 5))
        assertEquals(TextAnchor(1, 1), clampAnchor(listOf("Title", text), TextAnchor(1, 2)))
        assertEquals(TextAnchor(1, text.length), clampAnchor(listOf("Title", text), TextAnchor(Int.MAX_VALUE, Int.MAX_VALUE)))
        val pages = paginateChapter(listOf(text), 1, 10f, 1, 0f, ::measure)
        pages.flatMap { it.columns.flatten() }.forEach {
            assertEquals(it.start, safeTextOffset(text, it.start))
            assertEquals(it.end, safeTextOffset(text, it.end))
        }
    }

    @Test fun pageStartAnchorsRoundTrip() {
        val texts = listOf("Heading", "abc😀def".repeat(90), "last")
        for (columns in 1..2) {
            val pages = paginateChapter(texts, 7, 30f, columns, 2f, ::measure)
            pages.forEachIndexed { index, page -> assertEquals(index, pageForAnchor(pages, page.anchor)) }
        }
    }

    @Test fun textAnchorSurvivesReflow() {
        val texts = listOf("Heading", "中文😀abcdef".repeat(50))
        val narrow = paginateChapter(texts, 4, 30f, 1, 6f, ::measure)
        val wide = paginateChapter(texts, 11, 60f, 2, 12f, ::measure)
        val anchor = narrow[narrow.size / 2].anchor
        val page = wide[pageForAnchor(wide, anchor)]
        assertTrue(page.columns.flatten().any { it.paragraphIndex == anchor.paragraphIndex &&
            anchor.characterOffset in it.start until it.end })
    }

    @Test fun exactBoundaryBelongsToNextPageAndEndBelongsToLast() {
        val pages = paginateChapter(listOf("abcdef"), 2, 10f, 1, 0f, ::measure)
        assertEquals(1, pageForAnchor(pages, TextAnchor(0, 2)))
        assertEquals(2, pageForAnchor(pages, TextAnchor(0, 6)))
    }

    @Test fun oversizedLineAlwaysAdvancesAndEmptyParagraphsRemain() {
        val pages = paginateChapter(listOf("", "😀", ""), 1, 1f, 1, 0f, ::measure)
        assertEquals(3, pages.size)
        assertEquals(listOf(0, 1, 2), pages.map { it.anchor.paragraphIndex })
        assertEquals(listOf(MeasuredPage(listOf(emptyList()))),
            paginateChapter(emptyList(), 10, 10f, 1, 0f, ::measure))
    }

    @Test fun scrollLineCoordinatesRoundTrip() {
        val pages = paginateChapter(listOf("abcdefghi"), 3, 50f, 1, 0f, ::measure)
        assertEquals(TextAnchor(0, 3), anchorAtY(pages.single(), 12f))
        assertEquals(10f, yForAnchor(pages.single(), TextAnchor(0, 3)))
    }
}
''',
    'iosApp/Sources/Parser/BookParser.swift': r'''import Foundation
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
''',
    'iosApp/Sources/Parser/EPUBParser.swift': r'''import Foundation
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
''',
    'iosApp/Sources/Parser/ZIPPreflight.swift': r'''import Foundation

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
''',
    'iosApp/Sources/Parser/StreamingImport.swift': r'''import Foundation
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
''',
    'iosApp/Sources/Parser/STREAMING_IMPORT.md': r'''# Native file import (schema 2)

`DocumentPicker` uses `BookParser.parseFileToManifest(at:)`, then calls
`ReaderRuntime.shared.importManifest(json:)` on the main queue. The bridge carries
only the chapter index, never all chapter text. `parse(data:filename:)` and the
deprecated `parseFile(at:)` remain small-book/fixture compatibility APIs with their
original in-memory limits; they are not used for user-selected imports.

## Transaction and storage

- SHA256 is computed incrementally over original bytes, including any BOM.
- TXT: first bounded pass hashes and validates UTF-8 to select the encoding;
  second pass incrementally decodes and writes chapters. A second hash confirms
  that the source has not changed. No full decoded String is constructed.
- EPUB: hash, bounded file-based ZIP preflight, ZIPFoundation `Archive(url:)`,
  bounded extraction of each selected XHTML, then a final source hash check.
  Assets are not extracted. No archive-sized Data preflight is used.
- Chapters are atomically written under Application Support/LeafReader as
  `book-{sha256}-{lowercaseUUIDWithoutDashes}-c{index}.json`.
- Native code never writes the canonical manifest. Kotlin validates the completed
  index and publishes it together with the shelf entry.
- On native failure, only the exact chapter paths successfully written by this
  writer/revision are removed. Source files, earlier revisions and canonical
  manifests are left untouched. Kotlin validation failures and process death can
  leave unreferenced revision files; storage-layer cleanup owns that lifecycle.

## Limits and memory envelope

- Original TXT: 512 MiB; original EPUB: 1 GiB, inclusive.
- Byte reads: at most 64 KiB; incomplete decoder carry: at most 3 bytes.
- Paragraphs: at most 2000 UTF-16 units, split on Unicode scalar boundaries.
- Stored chapter text: at most 256 Ki UTF-16 units AND 512 KiB raw paragraph UTF-8.
  The byte target is **text**, not the physical JSON file: delimiters, escaped
  quotes/backslashes and many tiny paragraphs can make chapter JSON around
  1–1.25 MiB. The shared reader's 4 Mi-character JSON envelope covers that.
- Whole-book index: at most 50,000 chapters and 2,000,000 paragraphs. Counts are
  exact; characterCount excludes chapter titles and counts UTF-16 paragraph units.
- EPUB: 50,000 ZIP entries; per-entry expansion at most 64 MiB; aggregate declared
  expansion at most 2 GiB; compression ratio at most 200:1; central/local header
  metadata together at most 32 MiB. These also bound retained ZIPFoundation Entry
  extras/comments. Preflight reads an EOCD tail of at most 65,557 bytes and one
  bounded central/local header/name/extra field at a time.
- One XHTML at a time, at most 8 MiB uncompressed; metadata XML at most 1 MiB.
  SwiftSoup, validation markup and paragraphs are document-scoped, not book-scoped.
  Foundation temporaries are drained per byte chunk/document. One XHTML may
  produce multiple stored chapters; an XHTML larger than 8 MiB is rejected rather
  than parsed unboundedly.
- Existing per-document markup depth 128, node budget 100,000 and entity budget
  100,000 remain in force. Large indexes/metadata have a bounded but nonconstant
  cost within their explicit entry/chapter ceilings.

## Encoding and compatibility

UTF-8 (optional BOM), UTF-16 LE/BE with BOM, and GB18030 are supported for TXT.
Without a BOM, a full-file bounded UTF-8 validation pass precedes GB18030 fallback;
this handles a late non-UTF8 byte without guessing from only the first buffer.
GB18030 decoding uses Foundation's GB_18030_2000 converter on strictly framed
1/2/4-byte units. Invalid/unavailable conversions fail explicitly. Strict UTF-8
decoding rejects malformed sequences; a no-BOM file can instead be valid GB18030.
UTF-32, stray/truncated UTF-16 surrogates and incomplete final sequences in the
selected encoding are rejected. A UTF-8 BOM is authoritative and is not silently
reinterpreted as GB18030.

Long physical TXT lines are fragmented before a chapter buffer grows. Fragments
are never independently recognized as chapter headings. Consecutive actual short
headings remain empty chapters; books with no TOC/headings get bounded sequential
chapters. Paragraph normalization trims boundary whitespace and skips low control
characters, as the legacy parser does; it is not a byte-for-byte text exporter.

EPUB imports retain metadata/spine order and finite built-in named entities;
external DTD/entity resolution and remote resources are never loaded. Images,
CSS, script, audio/video, SVG and other non-text content are omitted. ZIP64,
multi-volume archives, encrypted/DRM entries, symlinks, unsafe/duplicate paths,
unsupported ZIP flags/methods, unsigned data descriptors, fixed layout, non-text
spines and non-XML HTML are outside this text importer. This is not full Legado
EPUB/rendering compatibility. Large asset-heavy EPUBs work subject to the limits
above; raising the original-file ceiling does not remove archive-bomb limits.

## Tests

`StreamingImportTests.swift` adds strict multibyte tests at every 1–7-byte chunk
size (UTF8/UTF16/GB18030), one-byte BOM/file reads, late GB fallback across the
64KiB boundary, file-size rejection with sparse fixtures, schema/id/revision and
atomic chapter publication checks, independent reimports, long-line heading
regression, failure rollback isolation, a generated >32MiB no-TOC TXT, a URL-backed
EPUB with a >32MiB unused asset and a split logical chapter, malformed stored-entry
size, CRC and bomb checks.
The existing BookParserTests fixtures remain supported.

These tests and Swift compilation have **not been run in the current Android /
Ubuntu session**: its shell/glob executors return ENOENT and no Xcode/Swift test
runner was available through the permitted tools. Source was statically reviewed;
run the ParserTests scheme on a macOS/Xcode runner before release. No claimed
512MiB/1GiB end-to-end device performance measurement has been made.
''',
    'iosApp/Sources/Host/DocumentPicker.swift': r'''import SwiftUI
import UIKit
import UniformTypeIdentifiers
import Shared

@MainActor
struct DocumentPicker: UIViewControllerRepresentable {
    let onSelection: ([URL]) -> Void
    let onCancel: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let epub = UTType(filenameExtension: "epub") ?? UTType(importedAs: "org.idpf.epub-container")
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.plainText, epub], asCopy: true)
        picker.allowsMultipleSelection = true
        picker.delegate = context.coordinator
        return picker
    }
    func updateUIViewController(_ controller: UIDocumentPickerViewController, context: Context) {}

    final class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DocumentPicker
        init(parent: DocumentPicker) { self.parent = parent }
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            parent.onSelection(urls)
        }
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) { parent.onCancel() }
    }
}

@MainActor
final class ImportCoordinator: ObservableObject {
    @Published var pickerPresented = false
    @Published private(set) var pending = 0
    private let queue = DispatchQueue(label: "dev.leaf.reader.import", qos: .userInitiated)
    private let batchLimit = 16

    func presentPicker() {
        guard pending == 0 else { return }
        pickerPresented = true
    }

    func importFiles(_ urls: [URL]) {
        pickerPresented = false
        guard !urls.isEmpty else { return }
        guard pending + urls.count <= batchLimit else {
            ReaderRuntime.shared.reportError(message: "每批最多导入 16 本，请等待当前任务结束。")
            return
        }
        pending += urls.count
        for url in urls {
            // Obtain the scope while the document-picker callback is active.
            // asCopy URLs inside our container commonly return false, which is fine.
            let scoped = url.startAccessingSecurityScopedResource()
            queue.async { [weak self] in
                let result: Result<String, Error> = autoreleasepool {
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    return Result { try BookParser().parseFileToManifest(at: url) }
                }
                DispatchQueue.main.async {
                    switch result {
                    case .success(let json): ReaderRuntime.shared.importManifest(json: json)
                    case .failure(let error):
                        // Never send OS errors, archive paths, or book text to logs/UI.
                        let message = (error as? ImportFailure)?.errorDescription ?? "导入失败：文件结构异常或读取中断。"
                        ReaderRuntime.shared.reportError(message: message)
                    }
                    self?.pending -= 1
                }
            }
        }
    }
}
''',
    'iosApp/Tests/StreamingImportTests.swift': r'''import XCTest
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
''',
    'iosApp/README.md': r'''# LeafReader iOS host

> v0.2 UPDATE: user-selected files now use the file-backed streaming importer and chapter manifest bridge. See [the current importer contract](<Sources/Parser/STREAMING_IMPORT.md>) and [upgrade notes](<../UPGRADE-v0.2.md>). The small in-memory limits/API descriptions below are retained as v0.1 fixture history, not the user-facing v0.2 file limits. Apple compilation and v0.2 tests are pending CI.

Original Swift host and generated test fixtures for the project contract. No Legado code or book content is copied.

## Build requirements

- macOS with the Xcode version supported by the pinned Kotlin/Native toolchain (the root workflow selects macOS 26 / Xcode 26.4; project language mode is Swift 5), selected via DEVELOPER_DIR or xcode-select, accepted Xcode license, iOS SDK, and an installed simulator runtime for tests. The iOS16 deployment target does not imply that an old Xcode can compile the shared framework.
- XcodeGen **2.38.0+** (`brew install xcodegen`). No Gradle script/build phase is generated in the Xcode project.
- Shared must already be built as the **static iOS ARM64 release framework**, at `../shared/build/bin/iosArm64/releaseFramework/Shared.framework` relative to this folder. Lead/CI owns generating it, e.g. `./gradlew :shared:linkReleaseFrameworkIosArm64` from project root.
- App target/scheme **LeafReader**, bundle identifier `dev.leaf.reader`, iOS deployment target **16.0**, iPhone/iPad, device-only. The framework is linked with `embed: false`; never add it to Embed Frameworks.
- First SPM resolution requires network access. Both package versions are exact, released, non-prerelease pins, verified from upstream release APIs and tagged manifests:
  - [ZIPFoundation 0.9.19 release](https://github.com/weichsel/ZIPFoundation/releases/tag/0.9.19), [tagged Package.swift](https://github.com/weichsel/ZIPFoundation/blob/0.9.19/Package.swift).
  - [SwiftSoup 2.7.7 release](https://github.com/scinfu/SwiftSoup/releases/tag/2.7.7), [tagged Package.swift](https://github.com/scinfu/SwiftSoup/blob/2.7.7/Package.swift).

Run from `iosApp` after building Shared externally:

```sh
xcodegen generate --spec project.yml
xcodebuild -resolvePackageDependencies \
  -project LeafReader.xcodeproj -scheme LeafReader
xcodebuild -project LeafReader.xcodeproj -scheme LeafReader \
  -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
```

The unsigned app is `build/Build/Products/Release-iphoneos/LeafReader.app`. IPA assembly/signing/install and TrollStore device/OS compatibility are Lead responsibilities; this host does not claim a tested IPA. No commit or push is performed.

## Parser tests without a Shared simulator framework

`ParserTests` is a **hostless XCTest bundle** that compiles `Sources/Parser` directly. It does not link Shared, depend on LeafReader, or require an app test host. Its separate scheme is suitable for simulator CI even while the app framework is device-only. Do not substitute scheme LeafReader for simulator testing.

```sh
xcodegen generate --spec project.yml
xcrun simctl list devices available
# Choose an available iOS simulator UDID; CI can select one dynamically.
xcodebuild -project LeafReader.xcodeproj -scheme ParserTests \
  -destination 'platform=iOS Simulator,id=SIMULATOR_UDID' \
  -derivedDataPath build-tests \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO test
```

Fixtures are generated in memory by the test code; no filesystem extraction or downloaded books. Cases cover byte SHA-256/JSON shape, UTF-8/UTF-16 BOM/GB18030, consecutive TXT headings, oversized and pathological single-line/grapheme text, EPUB metadata/spine/nonlinear selection, deflate and signed ZIP32 data descriptors, active-content removal, nested block text, CRC/truncation, encryption/DRM, traversal/remote references, duplicates/symlinks, declared entry/total/ratio/count limits, fixed layout, entities and XML nesting.

## Host and import behavior

- SwiftUI embeds `MainViewControllerKt.MainViewController(onImportRequested:)` through `UIViewControllerRepresentable`. The Kotlin import action opens a `UIDocumentPickerViewController` with TXT/EPUB, **asCopy: true**, multi-select. Files/Open-In uses the same importer.
- A serial user-initiated background queue reads/parses/hashes/encodes one book at a time. Security-scoped access starts in the picker callback and ends after parsing. Up to 16 pending books; autorelease pools bound per-file temporary objects.
- Only on the main queue, call `ReaderRuntime.shared.importBook(json:)` or `ReaderRuntime.shared.reportError(message:)`. Flush on inactive/background. Neither book text nor raw OS/archive errors are logged.
- SHA-256 is computed over the exact original bytes (including BOM/ZIP representation), before decoding.
- TXT: strict BOM-aware UTF-8/UTF-16 LE/BE, then UTF-8, then GB18030. UTF-32/NUL-bearing input is rejected. Chinese/English chapter headings are recognized; consecutive headings survive as empty chapters. Nonempty paragraphs are split at 2,000 UTF-16 units, including pathological single grapheme clusters.
- EPUB: validate ZIP central/local headers, then read only `mimetype`, container XML, OPF, and text spine documents through ZIPFoundation's chunk consumer. Resolve container/OPF references within the archive; never extract paths to disk. OPF title/first creator and primary linear spine order are used; if every spine entry is nonlinear, use that declared order. Duplicate spine references are rejected.
- Text-only XHTML is validated before offline SwiftSoup parsing. Scripts, styles, embedded assets/media/SVG/math are discarded; nothing executes or fetches resources. Block text is traversed once, so nested blocks are not duplicated or dropped. Headings remain in body text to avoid silent content removal (a chapter heading may consequently appear both as its title and first paragraph).

## Limits and deliberate compatibility tradeoffs

| Item | Limit |
| --- | --- |
| Original file | 32 MiB |
| ZIP entry (every entry, including unused assets) | 8 MiB uncompressed |
| All ZIP entries / actual consumed decompression | 64 MiB |
| Archive entries / compression ratio | 4,096 / 200:1 |
| Container / OPF XML | 1 MiB each |
| Readable body UTF-8 | 12 MiB |
| Total imported UTF-16, including metadata/headings | 8 × 1,024 × 1,024 units (Shared contract) |
| Chapters / paragraphs / one paragraph | 2,000 / 50,000 / 2,000 UTF-16 units |
| XML nesting / elements; parsed body nodes | 128 / 100,000; 100,000 |

- **Images and CSS are unsupported**; fixed layout, DRM, any `encryption.xml` (including font obfuscation), rights/license entries, ZIP encryption flags/AES extras, symlinks and unsafe/duplicate archive paths are rejected.
- Narrow ZIP32 support: stored/deflate, UTF-8 names (non-ASCII requires ZIP UTF-8 flag), optional **signed** ZIP32 data descriptors. ZIP64, multi-volume, unsigned/ambiguous data descriptors and excessive compression ratios are intentionally rejected, even for otherwise benign books.
- Content is required to be well-formed UTF-8 or BOM-tagged UTF-16 XHTML. Container/OPF DTDs and all custom entity declarations are rejected. XHTML external doctypes are never resolved. Standard HTML names such as `&nbsp;` are converted, only for XML validation, into numeric references using SwiftSoup's built-in finite table (at most 100,000 references, at most 16 MiB validation output). Original markup is used for text parsing, preserving escaped angle brackets as text. Unknown/custom names and malformed HTML are rejected. No CSS-hidden-text semantics, image alt rendering, cover extraction, NCX/nav TOC, font styling, ruby/MathML/SVG layout, or encoding guessing beyond the stated codecs.
- A book is bounded, but import still holds original bytes, decompressed chapter, DOM, text and JSON temporarily. Older iOS devices may experience memory pressure near limits. JSON persistence on the Kotlin main thread can briefly affect responsiveness; queueing prevents simultaneous large imports.
- File-provider scope, background interruption, real device presentation, Kotlin export header linkage, actual XcodeGen output, Apple compilation and XCTest execution require Apple CI/device verification.

## Original app icon

`Assets.xcassets/AppIcon.appiconset` contains 13 opaque RGB PNGs for all 18 standard iPhone/iPad/marketing slots, including 1024 px marketing art. The open-book/leaf design is generated from original vector geometry; no external artwork or image library. `ASSETCATALOG_COMPILER_APPICON_NAME` is `AppIcon`. To reproduce the assets, run `python3 Tools/generate_app_icon.py` from this folder (Python standard library only).

## Validation performed in the implementation environment

The delegated Linux/Android environment has no Swift compiler, XcodeGen, Apple SDK, or xcodebuild. `Info.plist` was parsed with Python plistlib and `project.yml` with PyYAML; target/package pins/static-link structure were asserted. Dependencies' release status and APIs were checked online. Swift/XCTest has **not been executed here**; no successful Apple build is implied.
''',
    'scripts/build-ios.sh': r'''#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != Darwin ]]; then
  printf 'This build requires macOS and Xcode. Use the GitHub Actions Build iOS IPA workflow.\n' >&2
  exit 1
fi
python3 scripts/check_project.py
bash ./gradlew :shared:linkReleaseFrameworkIosArm64 -PenableApple=true --stacktrace
(cd iosApp && xcodegen generate)
xcodebuild \
  -project iosApp/LeafReader.xcodeproj \
  -scheme LeafReader \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build/ios \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' DEVELOPMENT_TEAM='' \
  build
APP="$ROOT/build/ios/Build/Products/Release-iphoneos/LeafReader.app"
test -f "$APP/LeafReader"
plutil -lint "$APP/Info.plist"
ARCHS="$(xcrun lipo -archs "$APP/LeafReader")"
case "$ARCHS" in
  *arm64*) printf 'Architectures: %s\n' "$ARCHS" ;;
  *) printf 'Expected a thin arm64 binary, got: %s\n' "$ARCHS" >&2; exit 1 ;;
esac
APP_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Info.plist")"
python3 scripts/package_ipa.py --app "$APP" --output "$ROOT/dist/LeafReader-${APP_VERSION}-unsigned.ipa"
''',
    'README.md': r'''# 叶读 · Leaf Reader v0.3

面向 iOS16+ 的本地小说阅读器，Kotlin Multiplatform / Compose Multiplatform / Miuix 0.9.4。使用 GitHub Actions 构建未签名 ARM64 IPA，交给兼容设备上的 TrollStore 安装。

## v0.3 视觉与动效

- 书架与设置改为 Miuix 悬浮底栏（`Scaffold.floatingToolbar` + `FloatingToolbar`），不再占用布局高度。
- 顶栏去掉实心条与分割线：渐变遮罩，内容滚动时溶入；上滑时「书架」大标题缩放淡出、紧凑标题淡入。
- 搜索与导入为两个等大 40dp 圆形按钮（放大镜 / 加号）并排；搜索在下方展开 Miuix 搜索行。
- 书籍打开/关闭使用 360ms/280ms 弹性缩放淡入淡出；返回按钮为悬浮圆形按钮。
- 阅读页顶/底栏默认隐藏，点屏幕中央从顶部/底部滑出；底栏右侧为「设置」，中间显示章节进度。
- 目录改为 Miuix 底部面板：书封+书名+进度、四段 tab、搜索行、当前章高亮、每章字数（来自 manifest）。
- 控件间距：页面边距 20dp、控件间距 12dp、触控目标 ≥44dp。

## 与 v0.1 的区别

- 真正 Miuix 折叠大标题、搜索、分组设置、分段选项、Switch 和 Slider。
- 网格 / 列表 / 紧凑三种书架。
- 横向滑动分页 / 瞬翻 / 纵向滚动，单栏 / 双栏 / 自动分栏。
- 阅读顶底栏可点击收起、可自动隐藏；叠层不挤压分页尺寸。
- 字体、字号、行距、段距、字距、边距、首行缩进、粗体、主题。
- 实际字体行测量和文字锚点；不是固定字数分页或整章一页。
- 大书文件流导入、正文按章存储、按章读取。TXT 输入上限512MiB，EPUB输入上限1GiB；这些数值是校验上限，不是真机跑满的承诺。
- 兼容旧索引/正文的渐进迁移；保留已修好的 POSIX 存储和 lipo -archs 构建链。

详细范围与限制见 [v0.3 说明](<UPGRADE-v0.3.md>)、[v0.2 说明](<UPGRADE-v0.2.md>)、[验证记录](<VALIDATION.md>)。

## GitHub Actions

已有工程：把下载的 `LeafReader-v0.3-upgrade.py` 放到仓库根目录，把 `upgrade-v03.yml` 放到 `.github/workflows/`，手动运行 **Build LeafReader v0.3**。升级器明文可审阅、标准库、自包含；备份被覆盖的源码，不读取凭据，不自动提交或推送。

工作流会应用升级、运行共享测试、构建静态 Shared.framework / iOS App、上传 IPA 和完整升级源码，再跑原生导入测试。升级后的源码 artifact 可作为以后直接维护的仓库内容，不需要永久依赖补丁升级器。

已有完整 v0.2 源码时，原有构建工作流继续可用：

```bash
bash ./gradlew :shared:desktopTest -PenableApple=false
bash scripts/build-ios.sh
bash scripts/test-ios.sh
```

macOS 构建仍需兼容 Kotlin2.4.20 的 Xcode，CI 优先 Xcode26.4；最低运行版本 iOS16 与构建SDK分别管理。

## 数据

覆盖升级请保持已有 Bundle ID，不要先卸载。书库位于应用私有 Application Support/LeafReader。旧 v1 索引备份为 library.v1-backup.json；旧整书 JSON 首次打开分章迁移并保留原副本。原始导入文件不修改。备份/导出仍未提供，请自行保存原书。

v0.2 进度为章节、局部段落、UTF-16 文字位置，按本地字体尺寸定位；不承诺与任意第三方引擎 CFI 兼容。WebDAV、朗读、书源、PDF、仿真翻页、完整 EPUB CSS/图片仍后置。

## 验证状态

v0.3 在本机用 Gradle 8.14.3 + JDK 17 完整编译 `:shared:desktopTest` 并通过（47 项 Kotlin 测试，含分页/锚点/存储回归）。Apple 侧编译、Swift 测试与真机安装仍需 GitHub Actions 与 iOS16 设备验证；本地 JVM 通过不等于 iOS 通过。

## 许可

本项目为独立实现，未复制 Legado 代码。源码使用 [MIT](<LICENSE>)，依赖保持各自许可，见 [第三方说明](<THIRD_PARTY_NOTICES.md>)。
''',
    'VALIDATION.md': r'''# v0.3 验证状态

日期：2026-11-25。

## 本轮实际执行（本机，真实运行）

```text
gradle :shared:desktopTest   → BUILD SUCCESSFUL, 47 tests, 0 failures
```

环境：Linux aarch64 / OpenJDK 17 / 缓存 Gradle 8.14.3。覆盖 Miuix 0.9.4 + CMP 1.12.0 的全部共享 UI 源码，包括本版新增的 `MiuixAtoms.kt`、`MiuixGlyphs.kt`、`TocSheet.kt` 与重写的书架/阅读/设置页。分页、文字锚点、分章存储的回归测试全部通过。

升级器同样在本机做了端到端演练：对临时模拟仓库执行 `LeafReader-v0.3-upgrade.py --project … --archive …`，31 个源文件写入、`project.yml` 版本改为 0.3.0/3、备份目录与 change-manifest 生成、归档包含 TocSheet/UPGRADE-v0.3/工作流，二次运行全部 unchanged（幂等）。

## 本轮未执行

- macOS 上的 Kotlin/Native iOS framework 编译、Swift 编译、Xcode 链接、IPA 打包。
- iOS16 真机运行与巨魔安装；手势、动画帧率、刘海/16:9 实际观感。
- 真实文件提供器导入与后台中断。

## v0.2 及更早记录

## 本轮实际完成

- 读取用户附带的编译复盘，以及现有 POSIX 文件写入、lipo -archs、Xcode 选择和产物上传顺序修复；未恢复已失效的 NSString.writeToFile 或 lipo -verify_arch。
- 阅读器、书架、分章存储、Swift 流式导入的源码实现与逐文件静态复核。
- Miuix 0.9.4 使用的组件 API 对照对应 tag 的真实源码核实。
- 新增/更新回归测试源码：Kotlin 书库/manifest 33 例、分页/章节 14 例；原生流式导入新增13例，原15例导入测试保留。
- 静态审查发现并修复总段数 Int 求和溢出、取消旧库迁移后索引偏移、索引写入失败后重启定位、未挂载滚动 state 等待首帧等问题，保留回归用例。

## 本轮未执行

执行器首次调用返回 `spawn bash ENOENT`；glob/ripgrep 子进程也失败。read/edit/write 可用。本轮没有重复尝试损坏的执行器，没有运行 Gradle、Swift/XCTest、打包或真机安装。测试用例数量不是通过数量。

v0.1 的成功构建和19项本地通过记录只适用于旧版本，不作为 v0.2 成功证明。v0.2 未产出现成 IPA。

## Actions 必须验证

1. 标准库升级器可解析、路径预检、源码备份和全量源码 ZIP 生成。
2. JVM 共享 UI 编译和全部 Kotlin 回归测试。
3. Apple iOS 源集/静态框架编译、Swift 编译、App 链接与 IPA 封装。
4. 28 项原生导入测试（原15+新增13，实际数量以 XCTest 报告为准）。
5. IPA 产物在原生测试之前上传；测试失败仍应保留已成功构建的 IPA，但工作流会标记失败。

## iOS16 真机验收

- 覆盖安装、保留 Bundle ID，不先卸载；旧书库进度与分章迁移保持原文位置。
- Miuix书架折叠大标题、搜索、网格/列表/紧凑布局、设置切换保存。
- 横滑/瞬翻/滚动、单栏/双栏/旋转、目录和前后章连续性。
- 中央点击显示/收起工具栏，5秒自动隐藏可关闭，叠层不改分页。
- 字体/字号/行距改变后的文字锚点恢复，辅助字号、emoji、空章、极长段落。
- 大于32MiB TXT实测内存与导入时间；512MiB/1GiB是校验上限，不等于已通过该体积压力测试。
- 来回切换应用、导入过程中停止/空间不足、损坏中间章节、重启后状态恢复。

## 已知边界

EPUB仍是纯文本导入，不保留完整CSS/图片；ZIP64、DRM、过大单个XHTML和不规范HTML有明确兼容限制。过程终止或索引提交失败可能留下未被当前索引引用的章节修订副本；有效草稿保留便于重试，尚无完整磁盘垃圾回收界面。Canvas辅助朗读、字体fallback与真机触控待验收。
''',
    'UPGRADE-v0.2.md': r'''# 叶读 v0.2：从打开小说到实际阅读

## 这次针对的具体问题

上一版只做了纵向段落列表，Miuix 组件使用零散、阅读顶底栏常驻、整本书经 JSON 传递、32MiB 文件限制偏低。v0.2 不是只改配色和数字上限，而是更换阅读布局与存储/导入主链。

### 界面

- 采用实际 Miuix 大标题折叠 TopAppBar、SearchBar/InputField、TabRowWithContour、BasicComponent、Switch/Slider 和分组设置。
- 书架有网格、详细列表、紧凑列表；布局选择持久化。
- 最近阅读入口、书名/作者搜索与排序。

### 阅读

- 横向滑动分页、无动画瞬翻、纵向滚动三种模式。
- 单栏、双栏、宽屏自动双栏；当前自动阈值为 840dp。
- 字体、字号、行距、字距、段距、左右边距、首行缩进、粗体、主题。
- 中央点击显示/收起顶底工具栏，左右区域翻页；可选5秒自动收起。
- 工具栏是覆盖层，不参与正文分页尺寸，显示/隐藏不强制重排。
- 按实际字体测量的行分页，不把整章伪装成一页，也不按固定字符数切页。
- 仅排版当前章节；位置保存为章节、段落、UTF-16 文字偏移，而不是设备页码。

### 大书

- 文件流入口：TXT 上限 512MiB，EPUB 上限 1GiB。此为输入校验上限，不是上述体积的真机性能承诺。
- TXT 64KiB 字节块读取，流式哈希和有 carry 的 UTF-8/UTF-16/GB18030 解码。
- EPUB 使用文件 URL 归档，中央目录/本地头有界读取，单个 XHTML 解析仍有8MiB边界。
- 正文分章写入；目标每个持久章节不超过256Ki UTF-16 / 512KiB文本，核心允许512Ki UTF-16的兼容上限。
- Swift/Kotlin 之间只传较小目录元数据，不再传整本正文 JSON。
- 打开、翻章只读取当前章节，有限缓存，不把全书正文 flatten 为 UI 列表。
- 正常书籍也可能遇到 ZIP64、加密、极大单 XHTML、复杂原书排版等兼容边界。完整图片/CSS 渲染不在本轮。

## 旧书库

- 保留 Bundle ID 与 AppSupport/LeafReader 路径，建议覆盖安装，不先卸载。
- v1 索引首次加载时保存 library.v1-backup.json。
- 旧单文件正文首次打开迁移为按章文件；旧原始 JSON 保留。
- 旧全局段落索引转换到章节/局部段落；长章拆分记录来源位置。
- 新索引发布使用同目录 POSIX 临时文件+fsync+rename，保留此前已修好的新 SDK 兼容。
- 该迁移与覆盖升级尚需 iOS16 真机验证；请保留原始书籍。

## 构建

本机执行工具当前返回 `spawn bash ENOENT`，glob/ripgrep 子进程也失败。文件编辑仍可用。本轮只完成源码与静态复核，未执行新版本编译或测试，不沿用 v0.1 的通过数作为 v0.2 证据。

交付两个文件：

1. LeafReader-v0.2-upgrade.py：明文、标准库、自包含源码升级器，应用前备份被覆盖文件；可生成完整升级源码 ZIP。
2. upgrade-v02.yml：放进现有仓库的 .github/workflows/，手动运行；它应用升级、执行共享测试、构建 IPA、运行原生导入测试，并上传源码与 IPA。

升级器不会提交或推送 Git，不读取账号/密钥，不改 Bundle ID，不重置 wrapper/镜像配置。工作流沿用已验证方向：POSIX 文件存储、lipo -archs，以及产物上传先于原生测试。

## 尚未声称完成

- 本轮未实际构建或安装 v0.2 IPA。
- 未声称视觉与 Legado 全量功能/动画等价；没有仿真翻页、EPUB 原书 CSS/图片兼容。
- 大文件上限、分页手势、旋转重排、Canvas 无障碍和迁移必须由 CI 与真机验收。
''',
    'UPGRADE-v0.3.md': r'''# 叶读 v0.3：Miuix 视觉与动效补齐

v0.3 不是功能版本，只针对 v0.2 的界面反馈逐条落地。阅读/分页/分章存储引擎保持原样。

## 九条反馈的落点

| 反馈 | 实现 |
|---|---|
| 书架设置做成悬浮底栏 | `Scaffold(floatingToolbar = … , BottomCenter)` + Miuix `FloatingToolbar`，里面是「书架 / 设置」两枚胶囊 `DockTab`，底栏不占布局高度，列表底部留 104dp 避免遮挡 |
| 顶栏不要一刀切 | 去掉 `TopAppBar` 实心条与分割线，改为 `GradientHeaderScrim`（surface→透明四段渐变），内容在其下滚动溶入 |
| 打开/关闭动画 | 阅读页入口 `Animatable` 0→1：scale 0.94→1 + alpha，360ms `cubic-bezier(0.22,1,0.36,1)`；返回时先 280ms 反向再真正关闭，期间吞掉点击 |
| 返回按钮悬浮圆形 | 顶栏内 `MiuixCircleButton(Glyph.BACK)`，40dp 圆形、Miuix 容器色 |
| 控件间距 | `PageMargin=20dp`、`ControlGap=12dp`，dock 内 16dp/8dp，设置分组 24dp，触控目标 44dp |
| 目录仿截图 | `OverlayBottomSheet(cornerRadius=28dp)`：自带拖拽条、书封+书名+当前章+进度胶囊、`TabRowWithContour` 四段（信息/目录/书签/笔记）、搜索行 + 4 个方形小按钮、当前章高亮卡 + 蓝色字数胶囊、列表行左标题右字数（数据来自 manifest.characterCount） |
| 导入按钮变小圆形加号 | `MiuixCircleButton(Glyph.ADD, size=40dp)`，与搜索按钮同尺寸并排 |
| 上滑标题缩放 | 由 `LazyGridState` 滚动量驱动：大标题 scale 1→0.68 + 淡出，紧凑标题反向淡入，140ms 补间，仅头部重组 |
| 搜索改按钮+放大镜 | 顶栏右侧 40dp 圆形放大镜按钮，点开在下方展开 Miuix `InputField` 搜索行（带清空/收起圆钮） |

另：阅读顶/底栏默认不显示，点屏幕中央唤出，分别从顶部/底部 `slideInVertically` 滑入、滑出；底栏右侧为「设置」（排版设置），中间显示「章 / 总章 · 百分比」。

## 有意保留的取舍

- 渐变遮罩是**渐变色**而非真实 background blur（Compose 无跨平台 backdrop-blur，miuix-blur 的 LayerBackdrop 属于实验路径）。iOS 16 上表现一致、无掉帧风险。
- 目录面板的「信息 / 书签 / 笔记」为占位空态，不伪造数据；书签/笔记功能后续版本再加。
- 点当前章不重置阅读位置（只收起面板），避免丢锚点。
- 打开动画是整页 scale+fade，不是真正的 shared-element（书封飞到顶部）；后者需要 `LookaheadScope` + 共享 bounds，风险较高，留作后续。

## 验证

- 本机 `gradle :shared:desktopTest` 编译通过，47 项 Kotlin 测试全部通过（分页/锚点/存储回归未受影响）。
- 未在 iOS 真机跑过；Miuix 组件 API 均对照 0.9.4 tag 源码核对。
- 16:9/刘海：使用 `WindowInsets.safeDrawing` 与 `BoxWithConstraints` 分档，面板高度上限 72% 屏高，未写死像素。

## 升级方式

沿用同一套离线安装器：`LeafReader-v0.3-upgrade.py` 会写入 30 个源码文件并把 `iosApp/project.yml` 的版本号改为 0.3.0 / 3，其余构建配置（Bundle ID、静态框架路径、镜像设置）保持不变。备份和变更清单写在 `.leaf-upgrade-backup/<UTC>/`。
''',
    'validation-summary.json': r'''{
  "version": "0.2.0",
  "date": "2026-11-25",
  "local_execution": "unavailable: spawn bash ENOENT; read/edit/write work",
  "shared_ui_compilation": "not executed for v0.2",
  "kotlin_test_cases_in_source": 47,
  "kotlin_test_results": null,
  "swift_streaming_cases_added": 13,
  "swift_previous_cases_retained": 15,
  "swift_test_results": null,
  "ipa_build": "not executed for v0.2; use upgrade-v02 workflow",
  "github_workflow_dispatch": "not performed",
  "known_build_fixes_preserved": ["POSIX storage", "lipo -archs", "Xcode selection", "IPA upload before native tests"]
}
''',
    '.github/workflows/upgrade-v02.yml': r'''name: Build LeafReader v0.2

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v02-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.2-upgrade.py
          python3 LeafReader-v0.2-upgrade.py --project . --archive dist/LeafReader-v0.2-source.zip
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Upload complete upgraded source
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-complete-source
          path: dist/LeafReader-v0.2-source.zip
          if-no-files-found: error
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before optional native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.2-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.2' >> "$GITHUB_STEP_SUMMARY"
          echo 'Full upgraded source is published separately. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify migration and pagination on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
    '.github/workflows/upgrade-v03.yml': r'''name: Build LeafReader v0.3

on:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: leaf-v03-${{ github.ref }}
  cancel-in-progress: true

jobs:
  upgrade-and-build:
    runs-on: macos-26
    timeout-minutes: 90
    env:
      PREFERRED_XCODE: /Applications/Xcode_26.4.app/Contents/Developer
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Apply readable source upgrade and archive sources
        run: |
          python3 -m py_compile LeafReader-v0.3-upgrade.py
          python3 LeafReader-v0.3-upgrade.py --project . --archive dist/LeafReader-v0.3-source.zip
          python3 scripts/check_project.py
          python3 -m unittest discover -s scripts/tests -v
          bash -n scripts/build-ios.sh scripts/test-ios.sh
      - name: Upload complete upgraded source
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-complete-source
          path: dist/LeafReader-v0.3-source.zip
          if-no-files-found: error
      - name: Compile shared UI and run regression tests
        run: bash ./gradlew :shared:desktopTest -PenableApple=false --stacktrace
      - name: Select Xcode
        run: |
          set -euo pipefail
          if [ -d "$PREFERRED_XCODE" ]; then
            echo "DEVELOPER_DIR=$PREFERRED_XCODE" >> "$GITHUB_ENV"
          else
            python3 - <<'PY'
          import os, pathlib, re
          apps = list(pathlib.Path('/Applications').glob('Xcode*.app'))
          if not apps:
              raise SystemExit('No Xcode application found')
          apps.sort(key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)))
          with open(os.environ['GITHUB_ENV'], 'a') as out:
              out.write('DEVELOPER_DIR=' + str(apps[-1] / 'Contents/Developer') + '\n')
          PY
          fi
      - name: Inspect Apple tools and install XcodeGen
        run: |
          xcodebuild -version
          xcrun --sdk iphoneos --show-sdk-version
          brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
          xcodegen --version
      - name: Build and package device IPA
        run: bash scripts/build-ios.sh
      - name: Upload IPA before optional native test execution
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-iOS16-arm64-unsigned
          path: |
            dist/*.ipa
            dist/*.ipa.sha256
          if-no-files-found: error
          retention-days: 14
      - name: Run native streaming importer tests
        run: bash scripts/test-ios.sh
      - name: Upload all test reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: LeafReader-v0.3-test-reports
          path: |
            shared/build/reports/tests/
            build/ParserTests.xcresult
          if-no-files-found: ignore
      - name: Summary
        if: always()
        run: |
          echo '### LeafReader v0.3' >> "$GITHUB_STEP_SUMMARY"
          echo 'Full upgraded source is published separately. IPA is available only if the build step succeeded.' >> "$GITHUB_STEP_SUMMARY"
          echo 'Keep the existing Bundle ID and install over the prior version to retain the local library. Verify migration and pagination on your iOS16 device.' >> "$GITHUB_STEP_SUMMARY"
''',
}

VERSION_PATCHES = {
    'MARKETING_VERSION': '0.3.0',
    'CURRENT_PROJECT_VERSION': '3',
}
PROJECT_MARKERS = ('settings.gradle.kts', 'iosApp/project.yml')
ARCHIVE_DIRS = ('.github', 'gradle', 'shared', 'iosApp', 'scripts', 'samples', 'licenses', 'build-logic')
ARCHIVE_ROOT_FILES = (
    'gradlew', 'gradlew.bat', 'gradle.properties', 'settings.gradle.kts', 'build.gradle.kts',
    '.gitignore', '.gitattributes', 'README.md', 'VALIDATION.md', 'UPGRADE-v0.2.md', 'UPGRADE-v0.3.md',
    'THIRD_PARTY_NOTICES.md', 'LICENSE', 'validation-summary.json',
)
EXCLUDED_DIR_NAMES = {'build', '.gradle', '.kotlin', '.git', '__pycache__', '.leaf-upgrade-backup', 'dist', 'xcuserdata', '.swiftpm', 'DerivedData'}
EXCLUDED_SUFFIXES = ('.ipa', '.pyc')


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_relative(rel):
    if not rel or '\\' in rel or ':' in rel:
        raise SystemExit('Unsafe embedded path: %r' % (rel,))
    pure = PurePosixPath(rel)
    if pure.is_absolute() or any(part in ('', '.', '..') for part in pure.parts):
        raise SystemExit('Unsafe embedded path: %r' % (rel,))
    return pure


def target_for(project, rel):
    pure = validate_relative(rel)
    target = project.joinpath(*pure.parts)
    parent = target.parent
    for ancestor in [parent, *parent.parents]:
        if ancestor.exists() and ancestor.is_symlink():
            raise SystemExit('Refusing to write through symlink: %s' % ancestor)
        if ancestor == project.parent:
            break
    resolved = target.resolve(strict=False)
    project_resolved = project.resolve()
    try:
        resolved.relative_to(project_resolved)
    except ValueError:
        raise SystemExit('Target escapes project: %s' % rel)
    return target


def preflight(rel, content):
    data = content.encode('utf-8')
    if rel.endswith('.py'):
        ast.parse(content, filename=rel)
    elif rel.endswith('.json'):
        json.loads(content)
    elif rel.endswith('Info.plist'):
        plistlib.loads(data)
    return data


def backup_copy(project, backup_root, target):
    if not target.exists():
        return
    relative = target.relative_to(project)
    destination = backup_root.joinpath(*relative.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'rb') as source, open(destination, 'wb') as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def atomic_write(target, payload):
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix='.leaf-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(target))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def patch_project_yml(text):
    text, marketing = re.subn(r'MARKETING_VERSION:\s*"[^"]*"', 'MARKETING_VERSION: "%s"' % VERSION_PATCHES['MARKETING_VERSION'], text, count=1)
    text, current = re.subn(r'CURRENT_PROJECT_VERSION:\s*"[^"]*"', 'CURRENT_PROJECT_VERSION: "%s"' % VERSION_PATCHES['CURRENT_PROJECT_VERSION'], text, count=1)
    if marketing != 1 or current != 1:
        raise SystemExit('iosApp/project.yml is missing MARKETING_VERSION or CURRENT_PROJECT_VERSION; refusing a partial version patch.')
    return text


def collect_archive_files(project, archive_output):
    files = []
    for directory in ARCHIVE_DIRS:
        root = project.joinpath(*PurePosixPath(directory).parts)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(project)
            if any(part in EXCLUDED_DIR_NAMES for part in relative.parts):
                continue
            if path.suffix in EXCLUDED_SUFFIXES:
                continue
            if archive_output is not None and path.resolve() == archive_output:
                continue
            files.append(path)
    for name in ARCHIVE_ROOT_FILES:
        path = project / name
        if path.is_file() and not path.is_symlink():
            files.append(path)
    return files


def write_archive(project, archive_path):
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    files = collect_archive_files(project, archive_path.resolve())
    temporary = archive_path.with_suffix(archive_path.suffix + '.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(project).as_posix())
    os.replace(temporary, archive_path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description='Apply the frozen LeafReader v0.2 source upgrade.')
    parser.add_argument('--project', required=True, help='Existing LeafReader repository root')
    parser.add_argument('--archive', help='Optional path for a ZIP of the upgraded whitelisted sources')
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        raise SystemExit('Project directory does not exist: %s' % project)
    for marker in PROJECT_MARKERS:
        if not project.joinpath(*PurePosixPath(marker).parts).is_file():
            raise SystemExit('Missing project marker %s; run from the LeafReader repository root.' % marker)

    prepared = {}
    for rel in sorted(FILES):
        prepared[rel] = preflight(rel, FILES[rel])

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_root = project / '.leaf-upgrade-backup' / timestamp
    changes = []

    for rel in sorted(prepared):
        target = target_for(project, rel)
        payload = prepared[rel]
        before = target.read_bytes() if target.is_file() else None
        backup_copy(project, backup_root, target)
        atomic_write(target, payload)
        changes.append({
            'path': rel,
            'existed': before is not None,
            'sha256_before': sha256_bytes(before) if before is not None else None,
            'sha256_after': sha256_bytes(payload),
            'bytes': len(payload),
            'unchanged': before == payload,
        })
        print('OK %s (%s)' % (rel, 'unchanged' if before == payload else 'updated'))

    project_yml = project / 'iosApp' / 'project.yml'
    original = project_yml.read_text(encoding='utf-8')
    patched = patch_project_yml(original)
    backup_copy(project, backup_root, project_yml)
    atomic_write(project_yml, patched.encode('utf-8'))
    changes.append({
        'path': 'iosApp/project.yml',
        'existed': True,
        'sha256_before': sha256_bytes(original.encode('utf-8')),
        'sha256_after': sha256_bytes(patched.encode('utf-8')),
        'bytes': len(patched.encode('utf-8')),
        'unchanged': original == patched,
        'note': 'version scalars patched only; bundle id and build settings preserved',
    })
    print('OK iosApp/project.yml (%s)' % ('unchanged' if original == patched else 'version patched'))

    manifest = {
        'tool': 'LeafReader-v0.2-upgrade',
        'applied_at_utc': timestamp,
        'project': str(project),
        'file_count': len(FILES),
        'changes': changes,
    }
    manifest_path = backup_root / 'change-manifest.json'
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    print('Backup and manifest: %s' % backup_root)

    for rel in sorted(prepared):
        print('payload_sha256 %s %s' % (rel, sha256_bytes(prepared[rel])))

    if args.archive:
        archive_path = Path(args.archive)
        written = write_archive(project, archive_path)
        print('Archive: %s (%d files, %d bytes)' % (archive_path, len(written), archive_path.stat().st_size))
    print('Upgrade applied. Compile and run tests in CI; this tool does not build or install the app.')


if __name__ == '__main__':
    main()

