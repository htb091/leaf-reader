package dev.leaf.reader.ui

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
