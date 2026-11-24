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

/** Public methods are called on the UI thread. Large document I/O is kept off that thread. */
class ReaderStore(
    private val files: ReaderFiles = defaultReaderFiles(),
    private val scope: CoroutineScope = MainScope(),
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val mutableState = MutableStateFlow(LibraryState())
    val state: StateFlow<LibraryState> = mutableState.asStateFlow()
    private val documentOperations = Mutex()
    private var saveJob: Job? = null
    private var openGeneration = 0L
    private var persistenceBlocked = false

    init { loadLibrary() }

    private fun loadLibrary() {
        try {
            val raw = files.readText("library.json") ?: return
            val snapshot = json.decodeFromString<LibrarySnapshot>(raw)
            require(snapshot.schema == 1) { "书库版本较新，请使用匹配的应用版本。" }
            require(snapshot.books.size <= 10000)
            require(snapshot.books.all {
                documentIdPattern.matches(it.id) && it.title.isNotBlank() &&
                    it.chapterCount in 1..10000 && it.paragraphCount in 1..200000 &&
                    it.format in setOf("TXT", "EPUB")
            })
            require(snapshot.books.map { it.id }.distinct().size == snapshot.books.size)
            mutableState.value = LibraryState(
                books = snapshot.books.map { it.copy(progress = it.progress.clamp(it.paragraphCount + it.chapterCount)) },
                settings = snapshot.settings.sanitized(),
            )
        } catch (e: Exception) {
            persistenceBlocked = true
            mutableState.value = LibraryState(error = "书库索引读取失败，原文件已保留；请备份应用数据后检查。${e.message.orEmpty().take(120)}")
        }
    }

    fun openBook(id: String) {
        if (!documentIdPattern.matches(id)) return
        if (mutableState.value.books.none { it.id == id }) return
        val generation = ++openGeneration
        flush()
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            try {
                val document = withContext(ioDispatcher) {
                    val raw = files.readText("book-$id.json") ?: error("书籍文件缺失，请重新导入。")
                    json.decodeFromString<BookDocument>(raw).also { it.validate(); require(it.id == id) }
                }
                if (generation != openGeneration) return@launch
                val entry = mutableState.value.books.firstOrNull { it.id == id } ?: return@launch
                val progress = entry.progress.clamp(document.itemCount())
                mutableState.value = mutableState.value.copy(
                    books = mutableState.value.books.map { if (it.id == id) it.copy(lastOpenedAt = files.nowMillis(), progress = progress) else it },
                    currentBook = document,
                    currentProgress = progress,
                    busy = false,
                )
                persistSnapshot()
            } catch (e: Exception) {
                if (e is CancellationException) throw e
                if (generation == openGeneration) {
                    mutableState.value = mutableState.value.copy(busy = false, error = "打开失败：${e.message.orEmpty().take(160)}")
                }
            }
        }
    }

    fun closeBook() {
        ++openGeneration
        flush()
        mutableState.value = mutableState.value.copy(currentBook = null, busy = false)
    }

    fun updateProgress(itemIndex: Int, scrollOffset: Int) {
        val document = mutableState.value.currentBook ?: return
        val progress = ReadingProgress(itemIndex, scrollOffset).clamp(document.itemCount())
        if (progress == mutableState.value.currentProgress) return
        mutableState.value = mutableState.value.copy(
            currentProgress = progress,
            books = mutableState.value.books.map { if (it.id == document.id) it.copy(progress = progress) else it },
        )
        scheduleSave()
    }

    fun updateSettings(settings: ReaderSettings) {
        mutableState.value = mutableState.value.copy(settings = settings.sanitized())
        scheduleSave()
    }

    fun importBookJson(raw: String) {
        if (persistenceBlocked) {
            reportError("书库索引异常，已暂停修改以保留原数据。请先备份并检查应用数据。")
            return
        }
        mutableState.value = mutableState.value.copy(busy = true, error = null)
        scope.launch {
            documentOperations.withLock {
                try {
                    val document = withContext(ioDispatcher) {
                        require(raw.length <= 30 * 1024 * 1024) { "导入数据超过首版上限。" }
                        json.decodeFromString<BookDocument>(raw).also { it.validate() }
                    }
                    // A reimport also repairs missing/corrupt derived content while preserving the shelf position.
                    withContext(ioDispatcher) { files.writeText("book-${document.id}.json", json.encodeToString(document)) }
                    if (mutableState.value.books.any { it.id == document.id }) {
                        mutableState.value = mutableState.value.copy(busy = false, error = "这本书已在书架中，已更新本地副本并保留阅读位置。")
                        return@withLock
                    }
                    val entry = ShelfBook(
                        id = document.id, title = document.title, author = document.author,
                        format = document.format, chapterCount = document.chapters.size,
                        paragraphCount = document.chapters.sumOf { it.paragraphs.size }, addedAt = files.nowMillis(),
                    )
                    val previous = mutableState.value
                    mutableState.value = previous.copy(books = previous.books + entry, busy = false)
                    if (!persistSnapshot()) {
                        mutableState.value = mutableState.value.copy(books = previous.books)
                    }
                } catch (e: Exception) {
                    if (e is CancellationException) throw e
                    mutableState.value = mutableState.value.copy(busy = false, error = "导入失败：${e.message.orEmpty().take(160)}")
                }
            }
        }
    }

    fun deleteBook(id: String) {
        if (persistenceBlocked || !documentIdPattern.matches(id)) return
        scope.launch {
            documentOperations.withLock {
                val previous = mutableState.value
                if (previous.books.none { it.id == id }) return@withLock
                ++openGeneration // Invalidate an in-flight open even before currentBook has been installed.
                saveJob?.cancel()
                mutableState.value = previous.copy(
                    books = previous.books.filterNot { it.id == id },
                    currentBook = previous.currentBook?.takeUnless { it.id == id },
                    busy = false,
                )
                if (!persistSnapshot()) {
                    mutableState.value = mutableState.value.copy(books = previous.books, currentBook = previous.currentBook)
                    return@withLock
                }
                try { withContext(ioDispatcher) { files.delete("book-$id.json") } }
                catch (e: Exception) {
                    if (e is CancellationException) throw e
                    reportError("已移出书架，残留缓存将在后续维护时清理。")
                }
            }
        }
    }

    fun dismissError() { mutableState.value = mutableState.value.copy(error = null) }
    fun reportError(message: String) { mutableState.value = mutableState.value.copy(error = message.take(300)) }

    /** Called when leaving the reader or receiving the native background lifecycle event. */
    fun flush() { saveJob?.cancel(); saveJob = null; persistSnapshot() }

    private fun scheduleSave() {
        saveJob?.cancel()
        saveJob = scope.launch { delay(700); persistSnapshot() }
    }

    private fun persistSnapshot(): Boolean {
        if (persistenceBlocked) return false
        return try {
            val value = mutableState.value
            files.writeText("library.json", json.encodeToString(LibrarySnapshot(books = value.books, settings = value.settings)))
            true
        } catch (e: Exception) {
            mutableState.value = mutableState.value.copy(error = "保存失败，请检查可用存储空间。${e.message.orEmpty().take(100)}")
            false
        }
    }
}

object ReaderRuntime {
    val store: ReaderStore by lazy { ReaderStore() }
    fun importBook(json: String) { store.importBookJson(json) }
    fun reportError(message: String) { store.reportError(message) }
    fun flush() { store.flush() }
}
