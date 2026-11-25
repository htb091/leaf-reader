package dev.leaf.reader.ui

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
