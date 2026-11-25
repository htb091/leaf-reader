package dev.leaf.reader

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
