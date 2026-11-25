package dev.leaf.reader

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
