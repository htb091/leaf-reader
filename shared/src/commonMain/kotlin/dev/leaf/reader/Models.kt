package dev.leaf.reader

import kotlinx.serialization.Serializable

@Serializable
data class BookChapter(val title: String, val paragraphs: List<String>)

@Serializable
data class BookDocument(
    val id: String,
    val title: String,
    val author: String = "",
    val format: String = "TXT",
    val chapters: List<BookChapter>,
)

@Serializable
data class ReadingProgress(val itemIndex: Int = 0, val scrollOffset: Int = 0)

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
)

@Serializable
enum class ReaderTheme { SYSTEM, LIGHT, DARK, SEPIA }

@Serializable
data class ReaderSettings(
    val fontSize: Float = 20f,
    val lineHeight: Float = 1.7f,
    val theme: ReaderTheme = ReaderTheme.SYSTEM,
) {
    fun sanitized() = copy(
        fontSize = if (fontSize.isFinite()) fontSize.coerceIn(14f, 36f) else 20f,
        lineHeight = if (lineHeight.isFinite()) lineHeight.coerceIn(1.2f, 2.2f) else 1.7f,
    )
}

data class LibraryState(
    val books: List<ShelfBook> = emptyList(),
    val currentBook: BookDocument? = null,
    val currentProgress: ReadingProgress = ReadingProgress(),
    val settings: ReaderSettings = ReaderSettings(),
    val busy: Boolean = false,
    val error: String? = null,
)

@Serializable
internal data class LibrarySnapshot(
    val schema: Int = 1,
    val books: List<ShelfBook> = emptyList(),
    val settings: ReaderSettings = ReaderSettings(),
)

internal val documentIdPattern = Regex("[a-f0-9]{64}")

internal fun BookDocument.validate() {
    require(documentIdPattern.matches(id)) { "书籍标识无效，请重新导入原文件。" }
    require(title.isNotBlank() && title.length <= 1000) { "书名为空或过长。" }
    require(author.length <= 2000) { "作者信息过长。" }
    require(format in setOf("TXT", "EPUB")) { "首版支持 TXT 和基础 EPUB。" }
    require(chapters.isNotEmpty() && chapters.size <= 10000) { "章节数量异常。" }
    var paragraphs = 0L
    var characters = 0L
    var hasText = false
    for (chapter in chapters) {
        require(chapter.title.length <= 1000) { "章节标题过长。" }
        paragraphs += chapter.paragraphs.size
        require(paragraphs <= 200000) { "段落数量超过首版上限。" }
        for (paragraph in chapter.paragraphs) {
            require(paragraph.length <= 16000) { "段落过长，请将原文件分段后导入。" }
            characters += paragraph.length
            if (paragraph.isNotBlank()) hasText = true
            require(characters <= 8L * 1024 * 1024) { "正文超过首版 8M 字符上限。" }
        }
    }
    require(hasText) { "文件没有可阅读的正文。" }
}

internal fun BookDocument.itemCount(): Int = chapters.sumOf { 1 + it.paragraphs.size }

internal fun ReadingProgress.clamp(itemCount: Int) = copy(
    itemIndex = itemIndex.coerceIn(0, (itemCount - 1).coerceAtLeast(0)),
    scrollOffset = scrollOffset.coerceIn(0, 100000),
)
