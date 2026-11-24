package dev.leaf.reader.ui

import dev.leaf.reader.BookChapter
import dev.leaf.reader.BookDocument
import dev.leaf.reader.ReadingProgress
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ReadingItemsTest {
    private fun document(vararg chapters: BookChapter) = BookDocument(
        id = "a".repeat(64), title = "测试书籍", chapters = chapters.toList(),
    )

    @Test
    fun headingsAndParagraphsKeepExactSpineOrder() {
        val items = readingItems(document(
            BookChapter("第一章", listOf("甲", "乙")),
            BookChapter("第二章", listOf("丙")),
        ))
        assertEquals(listOf("第一章", "甲", "乙", "第二章", "丙"), items.map { it.text })
        assertEquals(listOf(true, false, false, true, false), items.map { it.isHeading })
        assertEquals(listOf(0, 0, 0, 1, 1), items.map { it.chapterIndex })
    }

    @Test
    fun emptyChapterStillOccupiesOneHeadingIndex() {
        val items = readingItems(document(
            BookChapter("序", emptyList()),
            BookChapter("正文", listOf("段落")),
        ))
        assertEquals(3, items.size)
        assertEquals("正文", items[1].text)
        assertEquals("段落", items[2].text)
        assertTrue(items[0].isHeading)
    }

    @Test
    fun blankTitlesGetReadableFallbackWithoutAddingItems() {
        val items = readingItems(document(BookChapter("  ", listOf("原文"))))
        assertEquals("第 1 章", items[0].text)
        assertEquals(2, items.size)
        assertEquals("原文", items[1].text)
    }

    @Test
    fun blankAndDuplicateParagraphsAreNotDroppedOrMerged() {
        val items = readingItems(document(BookChapter("章", listOf("", "重复", "重复"))))
        assertEquals(listOf("章", "", "重复", "重复"), items.map { it.text })
        assertFalse(items[1].isHeading)
        assertFalse(items[3].isHeading)
    }

    @Test
    fun persistedIndexAddressesSameParagraphAfterFlatteningAgain() {
        val book = document(BookChapter("一", listOf("甲", "乙")), BookChapter("二", listOf("丙")))
        val progress = ReadingProgress(itemIndex = 4, scrollOffset = 48)
        assertEquals("丙", readingItems(book)[progress.itemIndex].text)
        assertEquals(readingItems(book)[progress.itemIndex], readingItems(book.copy())[progress.itemIndex])
    }

    @Test
    fun emptyDocumentProducesNoSyntheticReadingItem() {
        assertTrue(readingItems(document()).isEmpty())
    }
}
